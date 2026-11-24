"""JARVIS Voice Interaction Subsystem (Unified Single-Capture Architecture).

Coordinates wake detection, speech recognition, state transitions, command execution,
and text-to-speech with deterministic barge-in interruption.

State Flow:
    SLEEPING -> (wake word) -> LISTENING -> (command captured) -> PROCESSING -> (routed) -> SPEAKING -> SLEEPING
    Interrupted: SPEAKING -> (stop/cancel) -> SLEEPING
"""

from __future__ import annotations

import asyncio
from enum import Enum
import logging
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from config import PermissionType, Settings
from security.permission_manager import PermissionManager
from voice.speech_to_text import BaseSTT, create_stt_engine
from voice.text_to_speech import BaseTTS, create_tts_engine
from voice.wake_word import WakeWordDetector

logger = logging.getLogger("jarvis.voice.manager")


class VoiceState(str, Enum):
    """Voice interaction lifecycle states."""
    INITIALIZING = "INITIALIZING"
    AWAKE = "AWAKE"
    SLEEP = "SLEEP"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    EXECUTING = "EXECUTING"
    MIC_DISABLED = "MIC_DISABLED"
    ERROR = "ERROR"

    # Backward compatibility aliases
    SLEEPING = "SLEEP"
    PROCESSING = "THINKING"


VoiceStateCallback = Callable[[VoiceState, VoiceState], None]


# Supported interruption patterns
INTERRUPT_PATTERNS = [
    r"^(?:jzt\s+|just\s+|hey\s+)?jarvis[\s,]+stop[\.\!\?]*$",
    r"^(?:jzt\s+|just\s+|hey\s+)?jarvis[\s,]+cancel[\.\!\?]*$",
    r"^cancel[\.\!\?]*$",
    r"^stop[\.\!\?]*$",
    r"^stop\s+(?:it|speaking|talking|please)[\.\!\?]*$",
    r"^please\s+stop[\.\!\?]*$",
    r"^shut\s+up[\.\!\?]*$",
    r"^quiet[\.\!\?]*$",
    r"^pause[\.\!\?]*$",
]


class VoiceManager:
    """Central coordinator for voice interaction, state transitions, and audio I/O."""

    def __init__(
        self,
        settings: Settings,
        permission_manager: PermissionManager,
        command_handler: Callable[[str], asyncio.Future[str]],
        stt_engine: Optional[BaseSTT] = None,
        tts_engine: Optional[BaseTTS] = None,
    ):
        self.settings = settings
        self.permissions = permission_manager
        self.command_handler = command_handler

        # Subsystems
        self.wake_detector = WakeWordDetector(settings)
        self.stt = stt_engine or create_stt_engine(settings)
        self.tts = tts_engine or create_tts_engine(settings)

        # State tracking
        self._state = VoiceState.INITIALIZING
        self._is_active = False
        self._is_muted = False
        self._loop_task: Optional[asyncio.Task] = None
        self._sleep_monitor_task: Optional[asyncio.Task] = None
        self._state_listeners: List[VoiceStateCallback] = []

        # 60-second inactivity sleep timer
        self.inactivity_timeout_seconds: float = float(
            getattr(settings, "inactivity_timeout_seconds", 60.0)
        )
        self._last_activity_time: float = time.time()

        # Interruption tracking
        self._interrupted = False
        self._current_speak_task: Optional[asyncio.Task] = None

        # Set initial resting state based on mic permissions
        if not self.permissions.is_allowed(PermissionType.MICROPHONE):
            self._set_state(VoiceState.MIC_DISABLED)
        else:
            self._set_state(VoiceState.SLEEP)

    def _sync_permission_state(self) -> None:
        """Keep voice state in sync with permission and manual mute state."""
        has_perm = self.permissions.is_allowed(PermissionType.MICROPHONE)
        if self._is_muted or not has_perm:
            if self._state not in (VoiceState.SPEAKING, VoiceState.EXECUTING, VoiceState.THINKING):
                if self._state != VoiceState.MIC_DISABLED:
                    self._set_state(VoiceState.MIC_DISABLED)
        else:
            if self._state == VoiceState.MIC_DISABLED:
                self._set_state(VoiceState.SLEEP)

    @property
    def state(self) -> VoiceState:
        self._sync_permission_state()
        return self._state

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def is_muted(self) -> bool:
        return self._is_muted

    @property
    def seconds_until_sleep(self) -> float:
        if self._state != VoiceState.AWAKE:
            return 0.0
        elapsed = time.time() - self._last_activity_time
        return max(0.0, round(self.inactivity_timeout_seconds - elapsed, 1))

    def reset_activity(self) -> None:
        """Reset the 60-second inactivity timer."""
        self._last_activity_time = time.time()
        # If in SLEEP mode and interaction occurs (e.g. text command or UI click), wake up to AWAKE
        if self._state == VoiceState.SLEEP and not self.is_muted:
            self._set_state(VoiceState.AWAKE)

    def wake_up(self) -> bool:
        """Transition from SLEEP to AWAKE mode."""
        if self._is_muted or not self.permissions.is_allowed(PermissionType.MICROPHONE):
            self._set_state(VoiceState.MIC_DISABLED)
            return False
        self.reset_activity()
        if self._state in (VoiceState.SLEEP, VoiceState.INITIALIZING):
            self._set_state(VoiceState.AWAKE)
        return True

    def sleep(self) -> None:
        """Transition from AWAKE or active state to SLEEP mode."""
        if self._state not in (VoiceState.SLEEP, VoiceState.MIC_DISABLED):
            logger.info(f"VoiceState transition: {self._state.value} -> SLEEP")
            print(f"\n[Voice] Inactivity timer elapsed ({self.inactivity_timeout_seconds}s). Entering SLEEP mode.", flush=True)
            self._set_state(VoiceState.SLEEP)

    def mute(self) -> None:
        """Mute microphone: completely halt audio capture and wake detection."""
        self._is_muted = True
        logger.info("Microphone manually muted.")
        self._set_state(VoiceState.MIC_DISABLED)

    def unmute(self) -> bool:
        """Unmute microphone: resumes listening in SLEEP mode if permitted."""
        self._is_muted = False
        logger.info("Microphone manually unmuted.")
        if not self.permissions.is_allowed(PermissionType.MICROPHONE):
            self._set_state(VoiceState.MIC_DISABLED)
            return False
        self._set_state(VoiceState.SLEEP)
        if not self._is_active:
            self.start_listening()
        return True

    def toggle_mute(self) -> bool:
        """Toggle microphone mute."""
        if self.is_muted:
            self.unmute()
            return False
        else:
            self.mute()
            return True

    @staticmethod
    def is_interrupt_phrase(text: str) -> bool:
        """Determine if spoken or typed input is an explicit interruption command."""
        if not text:
            return False
        clean = text.strip().lower()
        clean_no_punct = re.sub(r'^[^\w]+|[^\w]+$', '', clean)
        clean_words = clean_no_punct.split()
        if not clean_words:
            return False

        # Direct single-word interrupts: "stop", "cancel", "pause", "quiet", "halt"
        if clean_no_punct in ("stop", "cancel", "pause", "quiet", "halt", "hush"):
            return True

        # "jarvis stop", "jzt jarvis stop", "just jarvis stop", "hey jarvis stop", "jarvis cancel"
        if re.search(r'\b(?:jzt\s+|just\s+|hey\s+)?jarvis\s+(?:stop|cancel)\b', clean_no_punct):
            return True

        # Multi-word stop commands
        if any(p in clean_no_punct for p in (
            "stop it", "stop speaking", "stop talking", "please stop", "stop please",
            "shut up", "cut it out", "never mind", "nevermind"
        )):
            return True

        # Trailing stop or cancel
        if clean_words[-1] in ("stop", "cancel"):
            return True

        # Regex patterns as fallback
        for pattern in INTERRUPT_PATTERNS:
            if re.search(pattern, clean):
                return True

        return False

    def add_state_listener(self, callback: VoiceStateCallback) -> None:
        """Register listener for voice state changes."""
        self._state_listeners.append(callback)

    def _set_state(self, new_state: VoiceState) -> None:
        """Update state and notify observers."""
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            logger.info(f"VoiceState transition: {old_state.value} -> {new_state.value}")
            for listener in self._state_listeners:
                try:
                    listener(old_state, new_state)
                except Exception as e:
                    logger.warning(f"Error in voice state listener: {e}")

    # =========================================================================
    # Listening Lifecycle Controls
    # =========================================================================

    def start_listening(self) -> bool:
        """Engage the background voice listener loop and sleep monitor."""
        if self._is_muted or not self.permissions.is_allowed(PermissionType.MICROPHONE):
            logger.warning("Cannot start listening: Microphone permission is BLOCKED or microphone is MUTED.")
            self._set_state(VoiceState.MIC_DISABLED)
            return False

        if not self.stt.is_available():
            logger.warning("Cannot start listening: STT engine or microphone hardware is unavailable.")
            self._set_state(VoiceState.ERROR)
            return False

        if not self._is_active:
            self._is_active = True
            self._is_muted = False
            self._set_state(VoiceState.SLEEP)
            self._loop_task = asyncio.create_task(self._listen_loop())
            self._sleep_monitor_task = asyncio.create_task(self._sleep_monitor_loop())
            logger.info("Voice listener loop and 60-second sleep monitor engaged.")
            return True
        return True

    def stop_listening(self) -> None:
        """Disengage the voice listener and cancel active capture."""
        self._is_active = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            self._loop_task = None
        if self._sleep_monitor_task and not self._sleep_monitor_task.done():
            self._sleep_monitor_task.cancel()
            self._sleep_monitor_task = None
        self._set_state(VoiceState.SLEEP)
        logger.info("Voice listener loop disengaged.")

    def interrupt(self) -> bool:
        """Programmatically halt any active voice output immediately."""
        self._interrupted = True
        was_speaking = (self._state == VoiceState.SPEAKING) or (self._current_speak_task is not None)
        self.tts.stop()
        if self._current_speak_task and not self._current_speak_task.done():
            self._current_speak_task.cancel()
        if self._is_active and not self.is_muted:
            self.reset_activity()
            self._set_state(VoiceState.AWAKE)
        else:
            self._set_state(VoiceState.SLEEP)
        return was_speaking

    # =========================================================================
    # Unified Background Listen Loop (Single Controlled Mic Path)
    # =========================================================================

    async def _sleep_monitor_loop(self) -> None:
        """Background 60-second inactivity monitor transitioning AWAKE -> SLEEP."""
        while self._is_active:
            try:
                await asyncio.sleep(0.5)
                if self._state == VoiceState.AWAKE and not self.is_muted:
                    elapsed = time.time() - self._last_activity_time
                    if elapsed >= self.inactivity_timeout_seconds:
                        self.sleep()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Error in sleep monitor: {e}")
                await asyncio.sleep(1.0)

    async def _listen_loop(self) -> None:
        """Background continuous listen loop respecting permissions, mute, and sleep states."""
        while self._is_active:
            try:
                # 1. Check microphone permission and manual mute state
                if self._is_muted or not self.permissions.is_allowed(PermissionType.MICROPHONE):
                    if self._state != VoiceState.MIC_DISABLED:
                        self._set_state(VoiceState.MIC_DISABLED)
                    await asyncio.sleep(0.5)
                    continue

                # 2. Check inactivity timer if in AWAKE mode
                if self._state == VoiceState.AWAKE:
                    if (time.time() - self._last_activity_time) >= self.inactivity_timeout_seconds:
                        self.sleep()
                        continue

                # 3. SLEEP MODE: Lightweight local wake-word detection for 'Jarvis'
                if self._state == VoiceState.SLEEP:
                    heard_text = await self.stt.listen(
                        timeout=min(self.settings.wake_timeout_seconds, 3.0),
                        phrase_time_limit=self.settings.wake_timeout_seconds,
                        is_command=False,
                    )
                    if not heard_text:
                        await asyncio.sleep(0.05)
                        continue

                    is_wake, inline_cmd = self.wake_detector.match(heard_text)
                    if not is_wake:
                        await asyncio.sleep(0.05)
                        continue

                    # Wake word detected! Transition to AWAKE
                    logger.info(f"Wake word recognized: '{heard_text}'")
                    print(f"\n[Voice] Wake word detected: \"{heard_text}\". Transitioning to AWAKE.", flush=True)
                    self.wake_up()

                    # Inline command: 'Jarvis, open Notepad'
                    if inline_cmd:
                        self.reset_activity()
                        print(f"[Voice] Command captured: '{inline_cmd}'", flush=True)
                        await self._process_command(inline_cmd)
                        continue

                    # Standalone wake phrase: prompt user and capture command
                    self.reset_activity()
                    self._set_state(VoiceState.LISTENING)
                    await self.tts.speak("Yes?")
                    await asyncio.sleep(0.1)

                    print(f"[Voice] Command listening started ({self.settings.command_timeout_seconds}s timeout)", flush=True)
                    cmd_text = await self.stt.listen(
                        timeout=self.settings.command_timeout_seconds,
                        phrase_time_limit=self.settings.command_timeout_seconds,
                        is_command=True,
                    )

                    if not cmd_text:
                        print("[Voice] No speech detected after wake-up. Remaining AWAKE (60s timer).", flush=True)
                        self.reset_activity()
                        if self._state != VoiceState.MIC_DISABLED:
                            self._set_state(VoiceState.AWAKE)
                        continue

                    self.reset_activity()
                    print(f"[Voice] Command captured: '{cmd_text}'", flush=True)
                    await self._process_command(cmd_text)
                    continue

                # 4. AWAKE MODE: User can speak commands directly or with wake word
                if self._state == VoiceState.AWAKE:
                    listen_slice = min(3.0, self.inactivity_timeout_seconds)
                    heard_text = await self.stt.listen(
                        timeout=listen_slice,
                        phrase_time_limit=self.settings.command_timeout_seconds,
                        is_command=False,
                    )
                    if not heard_text:
                        continue

                    clean_lower = heard_text.strip().lower()
                    if clean_lower in ("sleep", "go to sleep", "jarvis sleep", "jarvis go to sleep", "stop listening"):
                        self.sleep()
                        await self.tts.speak("Going to sleep.")
                        continue

                    self.reset_activity()
                    is_wake, inline_cmd = self.wake_detector.match(heard_text)
                    cmd_to_run = inline_cmd if (is_wake and inline_cmd) else heard_text

                    if is_wake and not inline_cmd:
                        self._set_state(VoiceState.LISTENING)
                        await self.tts.speak("Yes?")
                        await asyncio.sleep(0.1)
                        next_cmd = await self.stt.listen(
                            timeout=self.settings.command_timeout_seconds,
                            phrase_time_limit=self.settings.command_timeout_seconds,
                            is_command=True,
                        )
                        if next_cmd:
                            self.reset_activity()
                            await self._process_command(next_cmd)
                        else:
                            if self._state != VoiceState.MIC_DISABLED:
                                self._set_state(VoiceState.AWAKE)
                        continue

                    print(f"[Voice] Command captured in AWAKE mode: '{cmd_to_run}'", flush=True)
                    await self._process_command(cmd_to_run)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in voice loop: {e}")
                self._set_state(VoiceState.ERROR)
                await asyncio.sleep(1.0)

    # =========================================================================
    # Voice Pipeline Execution (Simulated or Real)
    # =========================================================================

    async def process_voice_input(self, spoken_text: str) -> str:
        """Execute a complete voice interaction turn from raw text transcript.

        Used for voice loop, CLI testing ('voice simulate'), and automated unit tests.
        """
        # 1. If currently speaking, check for immediate interruption
        if (self._state == VoiceState.SPEAKING or self._current_speak_task is not None) and self.is_interrupt_phrase(spoken_text):
            logger.info(f"Interruption received via process_voice_input: '{spoken_text}'")
            print(f"\n[Voice: Interrupted: '{spoken_text}']", flush=True)
            self._interrupted = True
            self.tts.stop()
            if self._current_speak_task and not self._current_speak_task.done():
                self._current_speak_task.cancel()
            self._set_state(VoiceState.SLEEP)
            return "Playback interrupted."

        self._sync_permission_state()

        # 2. Permission and mute check
        if self.is_muted or not self.permissions.is_allowed(PermissionType.MICROPHONE):
            logger.warning("Voice processing rejected: Microphone permission is BLOCKED or microphone is MUTED.")
            self._set_state(VoiceState.MIC_DISABLED)
            return "Microphone permission is disabled or microphone is muted. Run 'allow microphone' or unmute to enable voice control."

        # 3. Check for local voice listening controls
        clean_input = spoken_text.strip().lower()
        if clean_input in ("stop listening", "voice stop", "go to sleep", "sleep"):
            self.sleep()
            self._set_state(VoiceState.SPEAKING)
            msg = "Going to sleep."
            await self._safe_speak(msg)
            self._set_state(VoiceState.SLEEP)
            return msg

        # 4. Check wake phrase
        is_wake, inline_cmd = self.wake_detector.match(spoken_text)

        # If in SLEEP mode (or INITIALIZING): wake phrase is required to transition to AWAKE
        if self._state in (VoiceState.SLEEP, VoiceState.INITIALIZING):
            if not is_wake:
                logger.debug(f"Input '{spoken_text}' did not match wake phrase while in SLEEP mode.")
                return "Wake phrase not detected."

            # Wake word matched! Transition to AWAKE
            self.wake_up()

            target_command = inline_cmd
            if not target_command:
                # Standalone wake phrase
                self._set_state(VoiceState.LISTENING)
                await self._safe_speak("Yes?")
                return "Awaiting command."

            return await self._process_command(target_command)

        # If in AWAKE mode: direct command or prefixed command accepted
        self.reset_activity()
        target_command = inline_cmd if (is_wake and inline_cmd) else spoken_text
        if is_wake and not inline_cmd:
            self._set_state(VoiceState.LISTENING)
            await self._safe_speak("Yes?")
            return "Awaiting command."

        return await self._process_command(target_command)

    async def _process_command(self, command: str) -> str:
        """Dispatch command through command router, generate concise response, and speak."""
        self.reset_activity()
        clean_cmd = command.strip()
        cmd_lower = clean_cmd.lower()

        # Handle local sleep controls directly
        if cmd_lower in ("stop listening", "go to sleep", "sleep"):
            self.sleep()
            self._set_state(VoiceState.SPEAKING)
            msg = "Going to sleep."
            await self._safe_speak(msg)
            self._set_state(VoiceState.SLEEP)
            return msg

        if cmd_lower in ("cancel", "stop", "nevermind", "cancel command"):
            self._set_state(VoiceState.SPEAKING)
            msg = "Cancelled."
            await self._safe_speak(msg)
            if self._is_active and not self.is_muted:
                self._set_state(VoiceState.AWAKE)
            else:
                self._set_state(VoiceState.SLEEP)
            return msg

        # Routing through existing assistant CommandRouter / AI Brain
        self._set_state(VoiceState.THINKING)
        print("[Voice] Processing started", flush=True)

        try:
            # Check if this command executes a tool action
            is_action_tool = any(clean_cmd.lower().startswith(p) for p in (
                "open", "launch", "run", "search", "create", "delete", "copy", "move", "rename"
            ))
            if is_action_tool:
                self._set_state(VoiceState.EXECUTING)

            raw_response = await self.command_handler(clean_cmd)
            concise_speech = self._format_concise_spoken_response(clean_cmd, raw_response)
        except Exception as e:
            logger.error(f"Error processing command '{clean_cmd}': {e}")
            concise_speech = "I encountered an error processing your command."

        # Speak response with real-time barge-in interruption detection
        self._set_state(VoiceState.SPEAKING)
        print(f"[Voice: Responding: \"{concise_speech}\"]", flush=True)
        completed = await self._safe_speak(concise_speech)

        if self._interrupted:
            self._set_state(VoiceState.SLEEP)
            return "Playback interrupted."

        # Return to AWAKE mode with active 60s sleep countdown
        if self._is_active and not self.is_muted:
            self.reset_activity()
            self._set_state(VoiceState.AWAKE)
        else:
            self._set_state(VoiceState.SLEEP)

        return concise_speech

    def _format_concise_spoken_response(self, command: str, full_response: str) -> str:
        """Format a natural, spoken TTS response rather than reading raw CLI tables."""
        if not full_response:
            return "Done."

        resp_lower = full_response.lower()

        # Permission errors
        if "permission denied" in resp_lower or "permission is currently blocked" in resp_lower or (
            resp_lower.startswith("could not start") and "permission is blocked" in resp_lower
        ):
            return "Permission is disabled."

        # Application / tool failures
        if "is not in the approved application allowlist" in resp_lower or (
            "not approved" in resp_lower and any(w in resp_lower for w in ("application", "tool", "access denied"))
        ):
            return "That application is not approved."
        if full_response.startswith("Failed:") and "could not locate executable" in resp_lower:
            return "I couldn't find that."
        if full_response.startswith("Failed:") or full_response.startswith("Tool Execution Failed:"):
            return "I was unable to complete that request."

        # App launcher success
        if "opened successfully" in resp_lower or "launched via" in resp_lower:
            cmd_clean = re.sub(r'[\.\?\!\,\;]+$', '', command).strip()
            cmd_parts = cmd_clean.split()
            target = cmd_parts[1].capitalize() if len(cmd_parts) > 1 else "Application"
            return f"Opening {target}."

        # Folder launcher success
        if ("opened" in resp_lower and "folder" in resp_lower) or "opened in file explorer" in resp_lower:
            cmd_clean = re.sub(r'[\.\?\!\,\;]+$', '', command).strip()
            cmd_parts = cmd_clean.split()
            target = cmd_parts[1].capitalize() if len(cmd_parts) > 1 else "folder"
            return f"Opening {target}."

        # File search
        if full_response.startswith("=== Found") and "file" in resp_lower:
            first_line = full_response.splitlines()[0]
            clean_line = first_line.replace("=", "").strip()
            return clean_line

        # Administrative CLI tables / banner dumps (e.g. status, permissions, audit)
        if full_response.startswith("=== "):
            first_line = full_response.splitlines()[0].replace("=", "").strip()
            return first_line

        # Tool execution summary prefix
        if full_response.startswith("Tool Execution Succeeded:"):
            for line in full_response.splitlines()[1:]:
                if line.startswith("Message:"):
                    return line.replace("Message:", "").strip()
            return "Action completed successfully."

        # Normal AI answer: clean markdown and return actual answer
        return self._clean_text_for_speech(full_response)

    def _clean_text_for_speech(self, text: str) -> str:
        """Prepare text for TTS audio synthesis by removing markdown syntax and noisy markup."""
        if not text:
            return ""
        # 1. Remove code blocks
        cleaned = re.sub(r'```[\s\S]*?```', '', text)
        # 2. Remove markdown links [text](url) -> text
        cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', cleaned)
        # 3. Remove header hashes at start of lines (e.g. # Title -> Title)
        cleaned = re.sub(r'(?m)^#{1,6}\s*', '', cleaned)
        # 4. Remove bold / italics
        cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)
        cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)
        cleaned = re.sub(r'__([^_]+)__', r'\1', cleaned)
        cleaned = re.sub(r'_([^_]+)_', r'\1', cleaned)
        # 5. Clean bullet points at start of lines
        cleaned = re.sub(r'(?m)^[\*\-\+]\s+', '', cleaned)
        # 6. Remove HTML tags if any
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        # 7. Collapse whitespace
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        return " ".join(lines)

    async def _safe_speak(self, text: str) -> bool:
        """Safely synthesize and speak text with real-time barge-in interruption detection.

        Returns True if speech completed normally, or False if interrupted.
        """
        if not text or not text.strip():
            return True

        self._interrupted = False
        old_state = self._state
        self._set_state(VoiceState.SPEAKING)
        speak_task = asyncio.create_task(self.tts.speak(text))
        self._current_speak_task = speak_task

        # Check if microphone hardware/permissions are available to monitor for interruption
        # Only attach barge-in monitor to longer spoken answers (> 4 words), not short prompts
        can_monitor = (
            self.permissions.is_allowed(PermissionType.MICROPHONE)
            and self.stt.is_available()
            and len(text.strip().split()) > 4
        )

        try:
            if not can_monitor:
                try:
                    await speak_task
                    return True
                except asyncio.CancelledError:
                    return False
                except Exception as e:
                    logger.warning(f"TTS audio synthesis error: {e}")
                    return False

            # Single persistent microphone stream for barge-in monitoring
            stop_event = threading.Event()
            interrupt_task = asyncio.create_task(
                self.stt.listen_for_interrupt(stop_event, self.is_interrupt_phrase)
            )

            try:
                while not speak_task.done():
                    done, pending = await asyncio.wait(
                        [speak_task, interrupt_task],
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    if interrupt_task in done:
                        try:
                            heard = interrupt_task.result()
                        except Exception:
                            heard = None

                        if heard and self.is_interrupt_phrase(heard):
                            logger.info(f"Barge-in interrupt recognized: '{heard}'")
                            print(f"\n[Voice: Interrupted: '{heard}']", flush=True)
                            self._interrupted = True
                            self.tts.stop()
                            if not speak_task.done():
                                speak_task.cancel()
                            break
                        else:
                            # Interrupt listener completed without an interrupt phrase.
                            # Allow speak_task to continue speaking smoothly to completion.
                            await speak_task
                            break

                    if speak_task in done:
                        break

                stop_event.set()

                for task in [speak_task, interrupt_task]:
                    if not task.done():
                        task.cancel()
                        try:
                            await task
                        except (asyncio.CancelledError, Exception):
                            pass

                return not self._interrupted
            except asyncio.CancelledError:
                stop_event.set()
                self.tts.stop()
                if not speak_task.done():
                    speak_task.cancel()
                return False
            except Exception as e:
                stop_event.set()
                logger.warning(f"Error during monitored speech: {e}")
                return False
        finally:
            self._current_speak_task = None
            if old_state == VoiceState.LISTENING and not self._interrupted:
                self._set_state(VoiceState.LISTENING)
            elif self._interrupted:
                self._set_state(VoiceState.SLEEP)
            elif self._is_active and not self.is_muted:
                self._set_state(VoiceState.AWAKE)
            else:
                self._set_state(VoiceState.SLEEP)

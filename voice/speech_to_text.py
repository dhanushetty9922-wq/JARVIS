"""JARVIS Speech-to-Text (STT) Subsystem.

Unified, non-blocking audio capture and speech recognition:
- BaseSTT: Abstract speech recognition interface
- LocalSpeechToText: Thread-safe microphone capture via SpeechRecognition and Google Web STT
- SimulatedSTT: In-memory simulation engine for tests and CLI simulation
- Persistent-stream interrupt listening: Opens mic ONCE during speech, zero sound card thrashing
- Single-capture lock: Strict mutual exclusion ensuring listeners never fight over the microphone
- Exact 8.0s command timeout support with clean diagnostic timing logs
- Throttled console output: Prevents high-frequency log flooding in PowerShell
- Zero raw audio persistence to disk
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Callable, Optional
from config import Settings

logger = logging.getLogger("jarvis.voice.stt")

try:
    import speech_recognition as sr
    HAS_SR = True
except ImportError:
    sr = None
    HAS_SR = False


class BaseSTT(ABC):
    """Abstract Base Class for Speech-to-Text engines."""

    @abstractmethod
    async def listen(
        self,
        timeout: float = 8.0,
        phrase_time_limit: Optional[float] = None,
        is_command: bool = False,
    ) -> Optional[str]:
        """Listen for speech on the microphone and return transcribed text."""
        pass

    @abstractmethod
    async def listen_for_interrupt(
        self,
        stop_event: threading.Event,
        check_interrupt_fn: Callable[[str], bool],
    ) -> Optional[str]:
        """Persistent-stream barge-in interrupt listener during active speech playback."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the microphone and STT backend are available."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of the STT provider."""
        pass


class LocalSpeechToText(BaseSTT):
    """Thread-safe microphone capture and speech recognition engine.

    Guarantees:
    - Single active microphone stream: protected by an internal threading Lock.
    - True 8.0s listening timeout without hidden smaller limits.
    - Safe ambient noise thresholding without discarding initial user speech.
    - Persistent-stream interrupt listening: zero audio buffer underruns during speech.
    - Throttled console output: logs essential milestones without console flooding.
    - No audio recordings saved to disk.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._recognizer: Optional[sr.Recognizer] = None
        self._mic_lock = threading.Lock()
        self._available = False
        self._init_engine()

    def _init_engine(self) -> None:
        """Initialize speech recognizer with safe, deterministic thresholds."""
        if not HAS_SR:
            logger.warning("speech_recognition library is not installed; running in simulated STT mode.")
            self._available = False
            return

        try:
            r = sr.Recognizer()
            # Clean baseline threshold to avoid measuring user speech as background noise
            r.energy_threshold = 300
            r.dynamic_energy_threshold = True
            r.dynamic_energy_adjustment_damping = 0.15
            r.pause_threshold = 0.8
            r.phrase_threshold = 0.3
            r.non_speaking_duration = 0.5

            # Test microphone presence without holding stream open
            with sr.Microphone() as source:
                pass

            self._recognizer = r
            self._available = True
            logger.info("LocalSpeechToText initialized successfully with available audio hardware.")
        except Exception as e:
            logger.warning(f"Audio capture hardware or driver unavailable: {e}")
            self._available = False

    def is_available(self) -> bool:
        return self._available

    def get_provider_name(self) -> str:
        return "local_speech_recognition"

    async def listen(
        self,
        timeout: float = 8.0,
        phrase_time_limit: Optional[float] = None,
        is_command: bool = False,
    ) -> Optional[str]:
        """Capture microphone audio and transcribe to text asynchronously."""
        if not self.is_available() or self._recognizer is None:
            logger.warning("Microphone is not available for speech recognition.")
            return None

        effective_phrase_limit = phrase_time_limit if phrase_time_limit is not None else timeout
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self._listen_sync,
            timeout,
            effective_phrase_limit,
            is_command,
        )

    def _listen_sync(
        self,
        timeout: float,
        phrase_time_limit: float,
        is_command: bool,
    ) -> Optional[str]:
        """Synchronous audio capture and STT executed in dedicated executor thread."""
        with self._mic_lock:
            start_time = time.time()
            logger.info("microphone opened")
            logger.info("command listener started")

            if is_command:
                print("[Voice] Listening started", flush=True)

            try:
                with sr.Microphone() as source:
                    try:
                        audio = self._recognizer.listen(
                            source,
                            timeout=timeout,
                            phrase_time_limit=phrase_time_limit,
                        )
                    except sr.WaitTimeoutError:
                        elapsed = time.time() - start_time
                        logger.info("timeout")
                        if is_command:
                            print("[Voice] Timeout", flush=True)
                            print(f"[Voice] Listening elapsed: {elapsed:.2f}s", flush=True)
                        return None

                # Speech audio was successfully captured
                logger.info("audio received")
                logger.info("speech detected")
                if is_command:
                    print("[Voice] Speech detected", flush=True)
                    print("[Voice] Recognition started", flush=True)
                logger.info("STT started")

                # Transcribe audio via Google Speech Recognition
                try:
                    transcript = self._recognizer.recognize_google(audio)
                    elapsed_total = time.time() - start_time
                    clean_text = transcript.strip()
                    logger.info(f"transcript produced: '{clean_text}'")
                    if is_command:
                        print("[Voice] Recognition completed", flush=True)
                        print(f"[Voice] Transcript: \"{clean_text}\"", flush=True)
                        print(f"[Voice] Listening elapsed: {elapsed_total:.2f}s", flush=True)
                    return clean_text
                except sr.UnknownValueError:
                    # Silence or unrecognizable sound
                    elapsed_total = time.time() - start_time
                    logger.info("Speech received but could not be understood.")
                    if is_command:
                        print(f"[Voice] Listening elapsed: {elapsed_total:.2f}s", flush=True)
                    return None
                except sr.RequestError as e:
                    logger.warning(f"recognition error: STT service unreachable: {e}")
                    if is_command:
                        print(f"[Voice] Recognition error: {e}", flush=True)
                    return None

            except Exception as e:
                logger.warning(f"Microphone capture error: {e}")
                return None
            finally:
                if self._recognizer:
                    self._recognizer.pause_threshold = 0.8

    async def listen_for_interrupt(
        self,
        stop_event: threading.Event,
        check_interrupt_fn: Callable[[str], bool],
    ) -> Optional[str]:
        """Persistent-stream barge-in interrupt listener during active speech playback."""
        if not self.is_available() or self._recognizer is None:
            return None
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self._listen_for_interrupt_sync,
            stop_event,
            check_interrupt_fn,
        )

    def _listen_for_interrupt_sync(
        self,
        stop_event: threading.Event,
        check_interrupt_fn: Callable[[str], bool],
    ) -> Optional[str]:
        """Persistent single-stream microphone capture specifically for barge-in interruption.

        Opens the microphone hardware stream ONCE and keeps it open while speech plays.
        Zero PortAudio stream renegotiation, zero sound card audio buffer thrashing.
        """
        with self._mic_lock:
            try:
                with sr.Microphone() as source:
                    orig_thresh = self._recognizer.energy_threshold
                    # Elevate threshold slightly while laptop speakers are actively playing
                    self._recognizer.energy_threshold = max(600, int(orig_thresh * 1.5))
                    self._recognizer.pause_threshold = 0.4
                    try:
                        while not stop_event.is_set():
                            try:
                                audio = self._recognizer.listen(
                                    source,
                                    timeout=0.4,
                                    phrase_time_limit=1.2,
                                )
                                try:
                                    text = self._recognizer.recognize_google(audio)
                                    if text and check_interrupt_fn(text):
                                        return text.strip()
                                except (sr.UnknownValueError, sr.RequestError):
                                    pass
                            except sr.WaitTimeoutError:
                                continue
                    finally:
                        self._recognizer.energy_threshold = orig_thresh
                        self._recognizer.pause_threshold = 0.8
            except Exception as e:
                logger.debug(f"Interrupt listener stream error: {e}")
                return None
        return None


class SimulatedSTT(BaseSTT):
    """In-memory simulated STT engine for tests and CLI simulation."""

    def __init__(self, responses: Optional[list[str]] = None):
        self._responses: list[str] = responses or []
        self._index: int = 0

    def enqueue_speech(self, text: str) -> None:
        """Queue a simulated speech input."""
        self._responses.append(text)

    def is_available(self) -> bool:
        return True

    def get_provider_name(self) -> str:
        return "simulated_stt"

    async def listen(
        self,
        timeout: float = 8.0,
        phrase_time_limit: Optional[float] = None,
        is_command: bool = False,
    ) -> Optional[str]:
        logger.info("command listener started")
        if is_command:
            print("[Voice] Listening started", flush=True)

        if self._index < len(self._responses):
            res = self._responses[self._index]
            self._index += 1
            logger.info("microphone opened")
            logger.info("speech detected")
            if is_command:
                print("[Voice] Speech detected", flush=True)
            logger.info("audio received")
            logger.info("STT started")
            if is_command:
                print("[Voice] Recognition started", flush=True)
            logger.info(f"transcript produced: '{res}'")
            if is_command:
                print("[Voice] Recognition completed", flush=True)
                print(f"[Voice] Transcript: \"{res}\"", flush=True)
                print("[Voice] Listening elapsed: 0.15s", flush=True)
            return res

        logger.info("timeout")
        if is_command:
            print("[Voice] Timeout", flush=True)
            print(f"[Voice] Listening elapsed: {timeout:.2f}s", flush=True)
        return None

    async def listen_for_interrupt(
        self,
        stop_event: threading.Event,
        check_interrupt_fn: Callable[[str], bool],
    ) -> Optional[str]:
        while not stop_event.is_set():
            if self._index < len(self._responses):
                candidate = self._responses[self._index]
                if check_interrupt_fn(candidate):
                    self._index += 1
                    return candidate
            await asyncio.sleep(0.02)
        return None


def create_stt_engine(settings: Settings) -> BaseSTT:
    """Factory creating the appropriate STT engine based on settings."""
    if settings.stt_provider == "simulated":
        return SimulatedSTT()
    return LocalSpeechToText(settings)

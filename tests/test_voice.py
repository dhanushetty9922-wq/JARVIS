"""Tests for JARVIS Phase 3 Voice Interaction Subsystem."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from config import PermissionType, Settings
from core.assistant import JarvisAssistant
from core.command_router import CommandRouter
from voice.speech_to_text import BaseSTT, SimulatedSTT
from voice.text_to_speech import BaseTTS, SilentTTS
from voice.voice_manager import VoiceManager, VoiceState
from voice.wake_word import WakeWordDetector


@pytest.fixture
def voice_env():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        tmp_path = Path(tmp_dir).resolve()
        settings = Settings(
            data_dir=tmp_path / "data",
            db_path=tmp_path / "data" / "jarvis.db",
            log_dir=tmp_path / "data" / "logs",
            safe_mode=True,
            wake_phrase="Jzt Jarvis",
            tts_enabled=True,
            tts_provider="silent",
            stt_provider="simulated",
            command_timeout_seconds=0.1,
            wake_timeout_seconds=0.1,
            inactivity_timeout_seconds=0.5,
        )

        sim_stt = SimulatedSTT()
        sim_tts = SilentTTS()

        assistant = JarvisAssistant(custom_settings=settings)
        # Inject test engines
        assistant.voice.stt = sim_stt
        assistant.voice.tts = sim_tts

        router = CommandRouter(assistant)

        try:
            yield {
                "assistant": assistant,
                "router": router,
                "voice": assistant.voice,
                "stt": sim_stt,
                "tts": sim_tts,
                "settings": settings,
            }
        finally:
            try:
                assistant.shutdown()
            except Exception:
                pass
            try:
                from security.audit_logger import close_logging
                close_logging()
            except Exception:
                pass


def test_wake_phrase_detection_and_variants(voice_env):
    """Test wake phrase matching with case insensitivity and phonetic variants."""
    settings: Settings = voice_env["settings"]
    detector = WakeWordDetector(settings)

    # 1. Exact match
    ok, cmd = detector.match("Jzt Jarvis")
    assert ok is True
    assert cmd == ""

    # 2. Case-insensitive with command
    ok, cmd = detector.match("jzt jarvis open downloads")
    assert ok is True
    assert cmd.lower() == "open downloads"

    # 3. Phonetic variant "just jarvis"
    ok, cmd = detector.match("Just Jarvis, open Chrome")
    assert ok is True
    assert cmd.lower() == "open chrome"

    # 4. Phonetic variant "hey jarvis"
    ok, cmd = detector.match("Hey Jarvis, find python files")
    assert ok is True
    assert cmd.lower() == "find python files"

    # 5. Non-wake phrase
    ok, cmd = detector.match("Hello computer, what is the time?")
    assert ok is False
    assert cmd is None

    # 6. Dynamic update of wake phrase
    detector.set_wake_phrase("Computer")
    ok, cmd = detector.match("Computer, open notepad")
    assert ok is True
    assert cmd.lower() == "open notepad"


@pytest.mark.asyncio
async def test_mic_permission_denial(voice_env):
    """When microphone permission is blocked, voice actions must not execute."""
    v: VoiceManager = voice_env["voice"]
    assistant: JarvisAssistant = voice_env["assistant"]

    # Microphone is blocked by default
    assert not assistant.permissions.is_allowed(PermissionType.MICROPHONE)

    # Attempting to start listening must fail
    started = v.start_listening()
    assert started is False
    assert v.is_active is False
    assert v.state in (VoiceState.MIC_DISABLED, VoiceState.SLEEPING)

    # Attempting to process voice command must state permission is disabled
    res = await v.process_voice_input("Jzt Jarvis, open Downloads")
    assert "Microphone permission is disabled" in res
    assert v.state in (VoiceState.MIC_DISABLED, VoiceState.SLEEPING)


@pytest.mark.asyncio
async def test_voice_state_transitions(voice_env):
    """Test state transitions: SLEEPING -> LISTENING -> PROCESSING -> SPEAKING -> SLEEPING."""
    v: VoiceManager = voice_env["voice"]
    assistant: JarvisAssistant = voice_env["assistant"]
    assistant.permissions.allow(PermissionType.MICROPHONE)

    recorded_states: list[VoiceState] = []
    v.add_state_listener(lambda old_s, new_s: recorded_states.append(new_s))

    # Simulate wake phrase only -> enters LISTENING
    res = await v.process_voice_input("Jzt Jarvis")
    assert res == "Awaiting command."
    assert VoiceState.LISTENING in recorded_states
    assert v.state == VoiceState.LISTENING

    # Clear recorder for next command
    recorded_states.clear()

    # Simulate command processing
    res_cmd = await v._process_command("status")
    assert VoiceState.PROCESSING in recorded_states
    assert VoiceState.SPEAKING in recorded_states
    assert (VoiceState.SLEEPING in recorded_states) or (VoiceState.AWAKE in recorded_states)
    assert v.state in (VoiceState.SLEEPING, VoiceState.AWAKE)


@pytest.mark.asyncio
async def test_simulated_voice_executes_phase2_tools(voice_env):
    """Verify that voice commands execute Phase 2 tools while respecting permissions."""
    v: VoiceManager = voice_env["voice"]
    tts: SilentTTS = voice_env["tts"]
    assistant: JarvisAssistant = voice_env["assistant"]

    # Allow mic and pc_control
    assistant.permissions.allow(PermissionType.MICROPHONE)
    assistant.permissions.allow(PermissionType.PC_CONTROL)

    # Mock application launcher so we don't open real windows
    with patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.pid = 4321
        mock_popen.return_value = mock_proc

        spoken = await v.process_voice_input("Jzt Jarvis, open Notepad")
        assert "Opening Notepad." in spoken
        assert "Opening Notepad." in tts.last_spoken
        assert v.state in (VoiceState.SLEEPING, VoiceState.AWAKE)


@pytest.mark.asyncio
async def test_voice_unapproved_app_rejection(voice_env):
    """Voice request to open an unapproved application must be rejected."""
    v: VoiceManager = voice_env["voice"]
    assistant: JarvisAssistant = voice_env["assistant"]
    assistant.permissions.allow(PermissionType.MICROPHONE)
    assistant.permissions.allow(PermissionType.PC_CONTROL)

    spoken = await v.process_voice_input("Jzt Jarvis, open dangerous_app.exe")
    assert "not approved" in spoken
    assert v.state in (VoiceState.SLEEPING, VoiceState.AWAKE)


@pytest.mark.asyncio
async def test_voice_folder_launcher(voice_env):
    """Voice request to open Downloads must succeed when files permission is granted."""
    v: VoiceManager = voice_env["voice"]
    assistant: JarvisAssistant = voice_env["assistant"]
    assistant.permissions.allow(PermissionType.MICROPHONE)
    assistant.permissions.allow(PermissionType.FILES)

    with patch("os.startfile", create=True):
        spoken = await v.process_voice_input("Jzt Jarvis, open Downloads")
        assert "Opening Downloads." in spoken
        assert v.state in (VoiceState.SLEEPING, VoiceState.AWAKE)


@pytest.mark.asyncio
async def test_listening_timeout(voice_env):
    """When in listening loop and no speech is heard, returns to standby and SLEEPING."""
    v: VoiceManager = voice_env["voice"]
    stt: SimulatedSTT = voice_env["stt"]
    assistant: JarvisAssistant = voice_env["assistant"]
    assistant.permissions.allow(PermissionType.MICROPHONE)

    # Queue wake phrase with no subsequent command
    stt.enqueue_speech("Jzt Jarvis")

    # Run one turn of listen loop manually
    v.start_listening()
    await asyncio.sleep(0.3)
    v.stop_listening()

    assert v.state == VoiceState.SLEEPING


@pytest.mark.asyncio
async def test_tts_failure_resilience(voice_env):
    """If TTS engine raises an error, VoiceManager must not crash."""
    v: VoiceManager = voice_env["voice"]
    assistant: JarvisAssistant = voice_env["assistant"]
    assistant.permissions.allow(PermissionType.MICROPHONE)

    # Create a failing TTS engine
    failing_tts = MagicMock(spec=BaseTTS)
    failing_tts.speak = AsyncMock(side_effect=RuntimeError("Audio hardware error"))
    failing_tts.is_available.return_value = True
    v.tts = failing_tts

    # Execute a voice turn
    res = await v.process_voice_input("Jzt Jarvis, open Downloads")
    # Voice manager must recover cleanly to SLEEPING or AWAKE state
    assert v.state in (VoiceState.SLEEPING, VoiceState.AWAKE)


@pytest.mark.asyncio
async def test_cli_voice_commands(voice_env):
    """Test CLI commands: voice status, start listening, stop listening, voice simulate."""
    router: CommandRouter = voice_env["router"]
    assistant: JarvisAssistant = voice_env["assistant"]

    # 1. voice status
    status_out = await router.handle_command("voice status")
    assert "Voice State:" in status_out
    assert "Configured Wake Word:" in status_out

    # 2. start listening without mic permission -> error
    start_err = await router.handle_command("start listening")
    assert "Microphone permission is BLOCKED" in start_err

    # 3. Allow mic -> start listening succeeds
    await router.handle_command("allow microphone")
    start_ok = await router.handle_command("start listening")
    assert "Voice listener started" in start_ok

    # 4. stop listening
    stop_ok = await router.handle_command("stop listening")
    assert "Voice listener stopped" in stop_ok

    # 5. voice simulate
    sim_out = await router.handle_command("voice simulate Jzt Jarvis status")
    assert "Voice Simulation Result:" in sim_out
    assert ("Current Voice State: SLEEP" in sim_out) or ("Current Voice State: AWAKE" in sim_out)


def test_interrupt_phrase_matching():
    """Verify that all specified interrupt phrases are correctly identified."""
    required_phrases = [
        "Jzt Jarvis, stop.",
        "Jarvis, stop.",
        "Cancel.",
        "Stop.",
        "stop",
        "cancel",
        "just jarvis stop",
        "hey jarvis stop",
        "Stop speaking",
        "please stop",
    ]
    for phrase in required_phrases:
        assert VoiceManager.is_interrupt_phrase(phrase) is True, f"Failed for '{phrase}'"

    non_interrupt_phrases = [
        "Explain quantum theory",
        "What is artificial intelligence?",
        "Open Notepad",
        "Find my files",
        "Jzt Jarvis status",
    ]
    for phrase in non_interrupt_phrases:
        assert VoiceManager.is_interrupt_phrase(phrase) is False, f"Failed for '{phrase}'"


@pytest.mark.asyncio
async def test_interrupt_long_ai_response_while_speaking(voice_env):
    """Test that a long AI response can be immediately interrupted while speaking."""
    v: VoiceManager = voice_env["voice"]
    stt: SimulatedSTT = voice_env["stt"]
    tts: SilentTTS = voice_env["tts"]
    assistant: JarvisAssistant = voice_env["assistant"]

    assistant.permissions.allow(PermissionType.MICROPHONE)

    # Configure SilentTTS with a simulated speaking duration
    tts.simulate_duration = 2.0

    # Queue an interruption phrase in STT to be heard while speaking
    stt.enqueue_speech("Jzt Jarvis, stop.")

    long_ai_response = (
        "Quantum theory is the branch of physics that describes how nature behaves at the smallest scales. "
        "It describes the world of atoms, electrons, and photons in great detail. "
        "Energy is quantized into discrete packets called quanta."
    )

    # Mock command_handler to return the long AI response
    v.command_handler = AsyncMock(return_value=long_ai_response)

    res = await v._process_command("Can you explain quantum theory?")
    assert res == "Playback interrupted."
    assert tts.was_interrupted is True
    assert v.state == VoiceState.SLEEPING


@pytest.mark.asyncio
async def test_interrupt_with_stop_and_cancel_variations(voice_env):
    """Test interrupt variations: 'Cancel.', 'Stop.', 'Jarvis, stop.'."""
    v: VoiceManager = voice_env["voice"]
    stt: SimulatedSTT = voice_env["stt"]
    tts: SilentTTS = voice_env["tts"]
    assistant: JarvisAssistant = voice_env["assistant"]

    assistant.permissions.allow(PermissionType.MICROPHONE)

    for interrupt_word in ["Cancel.", "Stop.", "Jarvis, stop."]:
        tts.simulate_duration = 2.0
        tts.was_interrupted = False
        stt.enqueue_speech(interrupt_word)

        v.command_handler = AsyncMock(return_value="This is a long AI response that will be interrupted.")
        res = await v._process_command("Explain DBMS simply.")
        assert res == "Playback interrupted."
        assert tts.was_interrupted is True
        assert v.state == VoiceState.SLEEPING


@pytest.mark.asyncio
async def test_programmatic_interrupt(voice_env):
    """Test direct programmatic interrupt() method call while speaking."""
    v: VoiceManager = voice_env["voice"]
    tts: SilentTTS = voice_env["tts"]
    assistant: JarvisAssistant = voice_env["assistant"]

    assistant.permissions.allow(PermissionType.MICROPHONE)
    tts.simulate_duration = 2.0

    # Start speaking in the background
    speak_task = asyncio.create_task(v._safe_speak("A very long sentence being spoken right now."))
    await asyncio.sleep(0.05)

    # While speaking, call interrupt
    assert v._current_speak_task is not None
    interrupted = v.interrupt()
    assert interrupted is True
    assert tts.was_interrupted is True

    await speak_task
    assert v.state == VoiceState.SLEEPING


@pytest.mark.asyncio
async def test_router_interrupt_while_speaking(voice_env):
    """Router commands 'Jarvis, stop', 'stop', 'cancel' immediately interrupt active voice playback."""
    v: VoiceManager = voice_env["voice"]
    router: CommandRouter = voice_env["router"]
    tts: SilentTTS = voice_env["tts"]
    assistant: JarvisAssistant = voice_env["assistant"]

    assistant.permissions.allow(PermissionType.MICROPHONE)

    for phrase in ["Jarvis, stop", "Jzt Jarvis, stop", "stop", "cancel"]:
        tts.simulate_duration = 3.0
        tts.was_interrupted = False

        speak_task = asyncio.create_task(v._safe_speak("This is a long response that will be interrupted by the router."))
        await asyncio.sleep(0.05)

        # Call router while speaking
        res = await router.handle_command(phrase)
        assert res == "Playback interrupted."
        assert tts.was_interrupted is True

        await speak_task
        assert v.state == VoiceState.SLEEPING


@pytest.mark.asyncio
async def test_all_four_required_interrupt_phrases_via_process_voice_input(voice_env):
    """Verify that all four required interrupt phrases halt speech in process_voice_input."""
    v: VoiceManager = voice_env["voice"]
    tts: SilentTTS = voice_env["tts"]
    assistant: JarvisAssistant = voice_env["assistant"]

    assistant.permissions.allow(PermissionType.MICROPHONE)

    required_phrases = ["Jarvis, stop", "Jzt Jarvis, stop", "stop", "cancel"]
    for phrase in required_phrases:
        tts.simulate_duration = 3.0
        tts.was_interrupted = False

        speak_task = asyncio.create_task(v._safe_speak("Testing interruption with required phrase."))
        await asyncio.sleep(0.05)

        res = await v.process_voice_input(phrase)
        assert res == "Playback interrupted."
        assert tts.was_interrupted is True

        await speak_task
        assert v.state == VoiceState.SLEEPING


@pytest.mark.asyncio
async def test_local_tts_smooth_playback_and_instant_purge():
    """Verify LocalTTS smooth playback, instant interrupt without waiting for sentence completion, and recovery."""
    from voice.text_to_speech import LocalTTS
    settings = Settings(
        tts_enabled=True,
        tts_provider="local",
        tts_voice_rate=180,
        tts_voice_volume=1.0,
    )
    local_tts = LocalTTS(settings)
    if not local_tts.is_available():
        pytest.skip("Audio hardware or SAPI/pyttsx3 not available in this test environment.")

    # 1. Short AI answer speaks smoothly
    short_success = await local_tts.speak("Short test response.")
    assert short_success is True
    assert local_tts.is_speaking is False

    # 2. Long AI answer speaks smoothly from beginning to end
    long_text = "This is a smooth response that explains artificial intelligence without breaking into choppy chunks."
    long_success = await local_tts.speak(long_text)
    assert long_success is True
    assert local_tts.is_speaking is False

    # 3. Long answer interrupted halfway through
    speak_task = asyncio.create_task(local_tts.speak(
        "Quantum computing is an emerging field that uses the principles of quantum mechanics to process complex data."
    ))
    await asyncio.sleep(0.3)
    assert local_tts.is_speaking is True
    # Stop immediately mid-sentence
    local_tts.stop()
    interrupted_res = await speak_task
    assert interrupted_res is False
    assert local_tts.is_speaking is False

    # 4. Speak another command after interruption
    recover_success = await local_tts.speak("System recovered successfully.")
    assert recover_success is True
    assert local_tts.is_speaking is False

    # 5. Confirm no overlapping TTS playback
    assert local_tts.is_speaking is False


@pytest.mark.asyncio
async def test_wake_word_wakes_from_sleep_to_awake(voice_env):
    """Test wake word 'Jarvis' wakes assistant from SLEEP to AWAKE without clicking mic button."""
    v: VoiceManager = voice_env["voice"]
    assistant: JarvisAssistant = voice_env["assistant"]
    assistant.permissions.allow(PermissionType.MICROPHONE)

    # Put in sleep mode
    v.sleep()
    assert v.state == VoiceState.SLEEP

    # Spoken wake phrase "Jarvis" transitions SLEEP -> AWAKE
    res = await v.process_voice_input("Jarvis")
    assert res == "Jarvis is awake and listening."
    assert v.state == VoiceState.AWAKE


@pytest.mark.asyncio
async def test_automatic_inactivity_sleep_transition(voice_env):
    """Test that after inactivity timeout, assistant transitions from AWAKE to SLEEP."""
    v: VoiceManager = voice_env["voice"]
    assistant: JarvisAssistant = voice_env["assistant"]
    assistant.permissions.allow(PermissionType.MICROPHONE)

    # Use a short inactivity timeout for test (0.3s)
    v.inactivity_timeout_seconds = 0.3
    v.start_listening()
    v.wake_up()
    assert v.state == VoiceState.AWAKE

    # Wait past inactivity timeout
    await asyncio.sleep(0.5)

    # Monitor loop transitions to SLEEP
    assert v.state == VoiceState.SLEEP

    # Saying "Jarvis" wakes it again
    res = await v.process_voice_input("Jarvis")
    assert v.state == VoiceState.AWAKE

    v.stop_listening()


@pytest.mark.asyncio
async def test_manual_mic_mute_and_unmute(voice_env):
    """Test manual mic mute stops capture (MIC_DISABLED) and unmute returns to SLEEP."""
    v: VoiceManager = voice_env["voice"]
    assistant: JarvisAssistant = voice_env["assistant"]
    assistant.permissions.allow(PermissionType.MICROPHONE)

    # Start in SLEEP mode
    v.sleep()
    assert v.state == VoiceState.SLEEP

    # Manual mute puts state to MIC_DISABLED
    v.mute()
    assert v.is_muted is True
    assert v.state == VoiceState.MIC_DISABLED

    # When muted, voice input is rejected
    res = await v.process_voice_input("Jarvis")
    assert "muted" in res.lower()
    assert v.state == VoiceState.MIC_DISABLED

    # Unmute returns to SLEEP
    v.unmute()
    assert v.is_muted is False
    assert v.state == VoiceState.SLEEP

    # Wake phrase works again
    res = await v.process_voice_input("Jarvis")
    assert v.state == VoiceState.AWAKE


@pytest.mark.asyncio
async def test_commands_while_awake_without_repeating_wake_word(voice_env):
    """Test commands execute directly while in AWAKE mode without repeating 'Jarvis'."""
    v: VoiceManager = voice_env["voice"]
    assistant: JarvisAssistant = voice_env["assistant"]
    assistant.permissions.allow(PermissionType.MICROPHONE)
    assistant.permissions.allow(PermissionType.PC_CONTROL)

    # Wake up
    v.wake_up()
    assert v.state == VoiceState.AWAKE

    # Direct command without "Jarvis"
    with patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_popen.return_value = mock_proc

        spoken = await v.process_voice_input("open Notepad")
        assert "Opening Notepad." in spoken
        # Stays AWAKE and resets inactivity timer
        assert v.state == VoiceState.AWAKE


@pytest.mark.asyncio
async def test_all_nine_voice_states_exist():
    """Verify all 9 required voice states are present in VoiceState enum."""
    required_states = {
        "INITIALIZING",
        "AWAKE",
        "SLEEP",
        "LISTENING",
        "THINKING",
        "SPEAKING",
        "EXECUTING",
        "MIC_DISABLED",
        "ERROR",
    }
    actual_states = {s.value for s in VoiceState}
    assert required_states.issubset(actual_states)



"""JARVIS Voice Subsystem Package.

Unified single-capture voice interaction, wake-word detection,
speech-to-text, dedicated-worker text-to-speech, and barge-in interruption.
"""

from voice.speech_to_text import BaseSTT, LocalSpeechToText, SimulatedSTT, create_stt_engine
from voice.text_to_speech import BaseTTS, LocalTTS, SilentTTS, create_tts_engine
from voice.voice_manager import VoiceManager, VoiceState
from voice.wake_word import WakeWordDetector

__all__ = [
    "VoiceManager",
    "VoiceState",
    "WakeWordDetector",
    "BaseSTT",
    "LocalSpeechToText",
    "SimulatedSTT",
    "create_stt_engine",
    "BaseTTS",
    "LocalTTS",
    "SilentTTS",
    "create_tts_engine",
]

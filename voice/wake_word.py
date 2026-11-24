"""JARVIS Wake Word Detection Subsystem.

Deterministic, low-CPU local wake-word detection:
- Default phrase: 'Jzt Jarvis' (configurable via settings/env)
- Phonetic transcript variants: 'jzt jarvis', 'just jarvis', 'jz jarvis', 'hey jarvis', and standalone 'jarvis'
- Inline command extraction: 'Jarvis, open Notepad' -> (True, 'open Notepad')
- Standalone wake utterance: 'Jarvis' -> (True, '')
"""

from __future__ import annotations

import logging
import re
from typing import Optional, Tuple
from config import Settings

logger = logging.getLogger("jarvis.voice.wake_word")


class WakeWordDetector:
    """Configurable wake phrase detector and command extractor."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.configured_phrase = settings.wake_phrase.strip().lower()
        self._compile_patterns()

    def set_wake_phrase(self, phrase: str) -> None:
        """Update wake phrase dynamically and recompile regexes."""
        self.configured_phrase = phrase.strip().lower()
        self._compile_patterns()
        logger.info(f"Wake phrase updated to: '{self.configured_phrase}'")

    def _compile_patterns(self) -> None:
        """Compile regexes for configured wake phrase and common phonetic variants."""
        escaped = re.escape(self.configured_phrase)
        variants = {escaped}

        # If jarvis is in the phrase, support all standard addressing prefixes
        if "jarvis" in self.configured_phrase:
            variants.add(r"jarvis")
            for prefix in ("hey", "ok", "okay", "hi", "hello", "jzt", "just", "jz"):
                variants.add(rf"{prefix}\s+jarvis")

        if "jzt" in self.configured_phrase:
            variants.add(escaped.replace("jzt", "just"))
            variants.add(escaped.replace("jzt", "jz"))
            variants.add(escaped.replace("jzt", "hey"))

        # Sort variants by length descending so longer phrases match first
        sorted_variants = sorted(list(variants), key=len, reverse=True)
        pattern_str = r"^(?:" + "|".join(sorted_variants) + r")\b[\s,:]*(.*)$"
        self._prefix_regex = re.compile(pattern_str, re.IGNORECASE)

    @staticmethod
    def normalize_text(text: str) -> str:
        """Clean and normalize transcript text for matching."""
        if not text:
            return ""
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return " ".join(cleaned.split())

    def match(self, spoken_text: str) -> Tuple[bool, Optional[str]]:
        """Evaluate if spoken text contains the wake phrase.

        Returns:
            Tuple[bool, Optional[str]]:
                - bool: True if wake phrase was detected.
                - Optional[str]: Remaining command text if present (e.g. 'open Chrome'),
                                 or empty string if only the wake phrase was spoken.
        """
        if not spoken_text:
            return False, None

        trimmed = spoken_text.strip()
        m = self._prefix_regex.match(trimmed)
        if m:
            remaining_command = m.group(1).strip()
            return True, remaining_command

        # Fallback to normalized text without punctuation
        normalized = self.normalize_text(trimmed)
        m_norm = self._prefix_regex.match(normalized)
        if m_norm:
            return True, m_norm.group(1).strip()

        return False, None

    def is_wake_word(self, spoken_text: str) -> bool:
        """Simple check if spoken text begins with or is the wake phrase."""
        detected, _ = self.match(spoken_text)
        return detected

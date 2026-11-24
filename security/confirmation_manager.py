"""JARVIS Confirmation Manager.

Manages interactive confirmation and double-confirmation workflows for sensitive operations:
- LOW: No confirmation needed
- MEDIUM: Standard audit logging, optional confirmation
- HIGH: Single explicit confirmation required
- CRITICAL: Double confirmation required (two distinct positive affirmations)

Never allows automated bypass of safety confirmations.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Callable, Optional, Union
from config import RiskLevel

logger = logging.getLogger("jarvis.security.confirmation")


ConfirmationHandler = Callable[[str, int, int], Union[bool, asyncio.Future]]


class ConfirmationManager:
    """Handles confirmation requests across interactive interfaces (CLI, Voice, GUI)."""

    def __init__(self, interactive_handler: Optional[ConfirmationHandler] = None):
        """Initialize with an optional custom confirmation handler."""
        self._handler = interactive_handler

    def set_handler(self, handler: ConfirmationHandler) -> None:
        """Set or update the interaction callback for confirmation prompts."""
        self._handler = handler

    async def request_confirmation(
        self,
        action_name: str,
        risk_level: RiskLevel,
        details: str = "",
    ) -> bool:
        """Request required confirmation based on risk level.
        
        Returns:
            bool: True if all necessary confirmations were granted; False otherwise.
        """
        if risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM):
            return True

        if risk_level == RiskLevel.HIGH:
            # Single confirmation
            prompt_msg = f"[HIGH RISK] Action '{action_name}' requested. {details}\nDo you want to continue?"
            confirmed = await self._prompt_user(prompt_msg, step=1, total_steps=1)
            if not confirmed:
                logger.info(f"High-risk action '{action_name}' rejected by user.")
                return False
            logger.info(f"High-risk action '{action_name}' confirmed by user.")
            return True

        if risk_level == RiskLevel.CRITICAL:
            # Double confirmation
            prompt_1 = (
                f"[CRITICAL RISK] Action '{action_name}' requested. {details}\n"
                f"This is a critical operation. Do you want to continue?"
            )
            step1_ok = await self._prompt_user(prompt_1, step=1, total_steps=2)
            if not step1_ok:
                logger.info(f"Critical action '{action_name}' aborted at step 1.")
                return False

            prompt_2 = (
                f"[DOUBLE CONFIRMATION REQUIRED]\nPlease confirm again to execute '{action_name}'."
            )
            step2_ok = await self._prompt_user(prompt_2, step=2, total_steps=2)
            if not step2_ok:
                logger.info(f"Critical action '{action_name}' aborted at step 2.")
                return False

            logger.info(f"Critical action '{action_name}' double-confirmed by user.")
            return True

        return False

    async def _prompt_user(self, message: str, step: int, total_steps: int) -> bool:
        """Execute confirmation callback or fallback to safe CLI prompt."""
        if self._handler is not None:
            res = self._handler(message, step, total_steps)
            if inspect.isawaitable(res):
                return bool(await res)
            return bool(res)

        # Default fallback: interactive CLI input
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, self._cli_prompt_sync, message, step, total_steps)
        except Exception as e:
            logger.error(f"Error during confirmation prompt: {e}")
            return False

    @staticmethod
    def _cli_prompt_sync(message: str, step: int, total_steps: int) -> bool:
        """Synchronous CLI confirmation prompt."""
        try:
            print(f"\n{message} (yes/no): ", end="", flush=True)
            response = input().strip().lower()
            return response in ("y", "yes", "confirm", "proceed", "true")
        except (EOFError, KeyboardInterrupt):
            print("\nAction cancelled.")
            return False

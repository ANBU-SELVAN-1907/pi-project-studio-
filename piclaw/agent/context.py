"""
PiClaw Conversation Context Manager.
Maintains rolling window of messages, prevents token bloat,
and injects tool results cleanly.
"""

import logging
from typing import List, Optional

from piclaw.llm.base import LLMMessage
from piclaw.utils.config import get

log = logging.getLogger("piclaw.agent.context")


class ConversationContext:
    """
    Manages the chat message history sent to the LLM.
    - Keeps a system prompt pinned at position 0.
    - Trims old messages when window exceeds max_turns.
    - Provides a clean snapshot for each LLM call.
    """

    def __init__(self, system_prompt: str, max_turns: int = 20):
        self._system   = system_prompt
        self._max_turns = max_turns
        self._history: List[LLMMessage] = []   # user + assistant + tool msgs only

    def update_system_prompt(self, prompt: str) -> None:
        self._system = prompt

    def add_user(self, text: str) -> None:
        self._history.append(LLMMessage(role="user", content=text))
        self._trim()

    def add_assistant(self, text: str) -> None:
        self._history.append(LLMMessage(role="assistant", content=text))

    def add_tool_result(self, tool_name: str, result_text: str) -> None:
        """Inject tool result as a user-role message (compatible with all providers)."""
        self._history.append(LLMMessage(
            role="user",
            content=f"[Tool result — {tool_name}]: {result_text}",
            name=tool_name,
        ))

    def snapshot(self) -> List[LLMMessage]:
        """Return full message list: system + trimmed history."""
        return [LLMMessage(role="system", content=self._system)] + self._history

    def clear(self) -> None:
        self._history.clear()

    def last_user_message(self) -> Optional[str]:
        for msg in reversed(self._history):
            if msg.role == "user":
                return msg.content
        return None

    def _trim(self) -> None:
        """Keep only the most recent max_turns messages (paired user+assistant)."""
        if len(self._history) > self._max_turns * 2:
            # Drop oldest pairs but keep recent ones
            excess = len(self._history) - self._max_turns * 2
            self._history = self._history[excess:]
            log.debug(f"[Context] Trimmed {excess} old messages")

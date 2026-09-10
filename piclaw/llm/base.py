"""
PiClaw LLM Provider Abstract Base.
All concrete providers must implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LLMMessage:
    role: str       # "system" | "user" | "assistant" | "tool"
    content: str
    name: Optional[str] = None      # for tool result messages


@dataclass
class ToolCall:
    """Structured tool invocation parsed from LLM output."""
    tool: str
    args: Dict[str, Any] = field(default_factory=dict)
    raw: str = ""


@dataclass
class LLMResponse:
    content: str                            # human-readable text
    tool_call: Optional[ToolCall] = None    # set if LLM wants to invoke a tool
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    @abstractmethod
    def chat(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Send messages to LLM and return structured response."""
        ...

    @abstractmethod
    def test_connection(self) -> tuple[bool, str, float]:
        """Return (success, message, latency_ms)."""
        ...

    @abstractmethod
    def name(self) -> str:
        """Short provider name for logging."""
        ...

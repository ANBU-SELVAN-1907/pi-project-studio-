"""
PiClaw Core Agent — the ReAct (Reason + Act) loop.
Flow:
  user input
    → build context
    → LLM call
    → parse response
    → if tool call: execute → inject result → loop back
    → else: final answer
Max iterations per turn: configurable (default 5).
Never crashes on single tool failure.
"""

import logging
from typing import Any, Callable, Dict, Optional, Tuple

from piclaw.agent.context  import ConversationContext
from piclaw.agent.prompts  import build_system_prompt, build_tool_result_message
from piclaw.llm.base       import LLMProvider, LLMResponse
from piclaw.llm.openai_compat import OpenAICompatProvider
from piclaw.tools.registry import get_registry, Permission, ToolResult
from piclaw.utils.config   import (
    get, get_llm_api_key, get_llm_base_url, get_llm_model
)

log = logging.getLogger("piclaw.agent")


class PiClawAgent:
    """
    The core AI agent.
    Implements full ReAct loop:
      Observe → Reason → Act → Observe → … → Respond
    """

    def __init__(
        self,
        llm: Optional[LLMProvider] = None,
        confirm_callback: Optional[Callable[[str], bool]] = None,
    ):
        # LLM provider
        self._llm = llm or OpenAICompatProvider(
            base_url=get_llm_base_url(),
            api_key=get_llm_api_key(),
            model=get_llm_model(),
            timeout=get("llm", "timeout", 30),
            retries=get("llm", "retries", 2),
        )
        self._registry     = get_registry()
        self._max_iters    = get("agent", "max_iterations", 5)
        self._confirm_cb   = confirm_callback   # called for DANGEROUS tools
        self._confirm_mode = get("agent", "confirm_dangerous", True)

        # Conversation context
        self._context = ConversationContext(
            system_prompt=build_system_prompt(),
            max_turns=get("agent", "context_window", 20),
        )
        self._llm_available = True

        log.info(f"[Agent] PiClaw agent initialized — LLM: {self._llm.name()}")

    # ── Public API ───────────────────────────────────────────────────────────

    def chat(self, user_input: str) -> str:
        """
        Process a user message and return PiClaw's final response.
        This is the only method the CLI needs to call.
        """
        user_input = user_input.strip()
        if not user_input:
            return ""

        log.log(25, f"[AGENT] User: {user_input[:80]}")
        self._context.add_user(user_input)

        response = self._react_loop()

        self._context.add_assistant(response)
        log.log(25, f"[AGENT] Reply: {response[:80]}")
        return response

    def test_llm(self) -> Tuple[bool, str, float]:
        """Test LLM connectivity. Returns (ok, message, latency_ms)."""
        ok, msg, lat = self._llm.test_connection()
        self._llm_available = ok
        return ok, msg, lat

    def refresh_system_prompt(self) -> None:
        """Rebuild system prompt (e.g. after device registry changes)."""
        self._context.update_system_prompt(build_system_prompt())

    def clear_context(self) -> None:
        self._context.clear()

    # ── ReAct Loop ───────────────────────────────────────────────────────────

    def _react_loop(self) -> str:
        """
        Core reasoning loop.
        Iterates up to max_iterations times until the LLM produces a plain text
        response (no tool call) or we hit the limit.
        """
        tools_schema = self._registry.all_schemas()

        for iteration in range(self._max_iters):
            log.log(25, f"[AGENT] Iteration {iteration + 1}/{self._max_iters}")

            # --- LLM call ---
            if not self._llm_available:
                return self._offline_response()

            llm_resp = self._llm.chat(
                messages=self._context.snapshot(),
                tools=tools_schema if tools_schema else None,
                temperature=get("llm", "temperature", 0.2),
                max_tokens=get("llm", "max_tokens", 1024),
            )

            if not llm_resp.ok:
                self._llm_available = False
                log.warning(f"[Agent] LLM error: {llm_resp.error}")
                return (
                    f"⚠ LLM unavailable: {llm_resp.error}\n"
                    "Local tools and automation remain active. "
                    "Type /status to check system state."
                )

            # --- No tool call → final answer ---
            if llm_resp.tool_call is None:
                return llm_resp.content or "(no response)"

            # --- Tool call requested ---
            tc = llm_resp.tool_call
            log.log(25, f"[AGENT] Tool requested: {tc.tool} args={tc.args}")

            tool = self._registry.get(tc.tool)
            if tool is None:
                result = ToolResult(
                    success=False,
                    error=f"Unknown tool '{tc.tool}'. Please use only listed tools.",
                )
            elif (
                tool.permission == Permission.DANGEROUS
                and self._confirm_mode
                and self._confirm_cb is not None
            ):
                # Ask user confirmation for dangerous ops
                confirmed = self._confirm_cb(
                    f"⚠ DANGEROUS operation: {tc.tool}({tc.args}). Confirm? [y/N] "
                )
                if not confirmed:
                    result = ToolResult(
                        success=False,
                        error="User declined to execute dangerous operation.",
                    )
                else:
                    result = tool.run(tc.args)
            else:
                result = tool.run(tc.args)

            # Inject tool result back into context for next iteration
            result_text = result.message if result.success else f"ERROR: {result.error}"
            self._context.add_tool_result(tc.tool, result_text)

            # If LLM provided content along with the tool call, inject that too
            if llm_resp.content:
                self._context.add_assistant(llm_resp.content)

        # Hit max iterations — return last LLM content
        log.warning("[Agent] Max iterations reached")
        return "I reached my reasoning limit. Please try rephrasing your request."

    # ── Offline Mode ─────────────────────────────────────────────────────────

    def _offline_response(self) -> str:
        """
        When LLM is unavailable, attempt to handle simple commands locally
        using direct tool invocation based on keyword matching.
        """
        last = self._context.last_user_message() or ""
        q    = last.lower()

        # Simple offline keyword → tool dispatch
        if any(w in q for w in ["cpu", "processor"]):
            r = self._registry.execute("system.cpu", {})
            return r.message if r.success else "CPU info unavailable."

        if any(w in q for w in ["temperature", "temp"]):
            r = self._registry.execute("system.temperature", {})
            return r.message if r.success else "Temperature sensor unavailable."

        if any(w in q for w in ["memory", "ram"]):
            r = self._registry.execute("system.memory", {})
            return r.message if r.success else "Memory info unavailable."

        if any(w in q for w in ["disk", "storage", "space"]):
            r = self._registry.execute("system.disk", {})
            return r.message if r.success else "Disk info unavailable."

        if "status" in q:
            r = self._registry.execute("system.status", {})
            return r.message if r.success else "Status unavailable."

        if any(w in q for w in ["network", "ip", "wifi"]):
            r = self._registry.execute("network.status", {})
            return r.message if r.success else "Network info unavailable."

        return (
            "⚠ LLM is currently unavailable.\n"
            "Local tools still work. Try: /status  /tools  /rules  /tasks\n"
            "Or ask for: cpu, memory, disk, temperature, network status."
        )

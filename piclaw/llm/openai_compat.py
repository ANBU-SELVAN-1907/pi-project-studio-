"""
PiClaw OpenAI-Compatible LLM Provider.
Works with: OmniRoute (localhost:20128), OpenAI, any OpenAI-format endpoint.
Parses tool calls from model JSON responses.
"""

import json
import re
import time
import logging
from typing import Any, Dict, List, Optional

import requests

from piclaw.llm.base import LLMProvider, LLMMessage, LLMResponse, ToolCall

log = logging.getLogger("piclaw.llm")


class OpenAICompatProvider(LLMProvider):
    """
    Connects to any OpenAI-compatible /v1/chat/completions endpoint.
    Designed for minimal resource usage on Pi Zero W:
    - No streaming (simpler, lower overhead for short agent turns)
    - Structured JSON tool-call parsing with regex fallback
    - Automatic retry with exponential back-off
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str = "auto/best-chat",
        timeout: int = 30,
        retries: int = 2,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key  = api_key
        self._model    = model
        self._timeout  = timeout
        self._retries  = retries
        self._session  = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})
        if self._api_key:
            self._session.headers["Authorization"] = f"Bearer {self._api_key}"

    def name(self) -> str:
        return f"OpenAICompat({self._model})"

    # ── Public API ──────────────────────────────────────────────────────────

    def chat(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Send chat messages. Returns LLMResponse with optional ToolCall."""
        payload: Dict[str, Any] = {
            "model":       self._model,
            "messages":    [self._msg_to_dict(m) for m in messages],
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        last_error = ""
        for attempt in range(self._retries + 1):
            try:
                resp = self._session.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    timeout=self._timeout,
                )
                if resp.status_code == 200:
                    return self._parse_response(resp.json())
                else:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:120]}"
                    log.warning(f"[LLM] Attempt {attempt+1} failed: {last_error}")
            except requests.Timeout:
                last_error = f"Timeout after {self._timeout}s"
                log.warning(f"[LLM] Attempt {attempt+1} timeout")
            except Exception as e:
                last_error = str(e)[:80]
                log.warning(f"[LLM] Attempt {attempt+1} error: {e}")

            if attempt < self._retries:
                time.sleep(1.5 ** attempt)   # 0s, 1.5s back-off

        return LLMResponse(
            content="",
            error=f"LLM unavailable after {self._retries+1} attempts: {last_error}",
        )

    def test_connection(self) -> tuple[bool, str, float]:
        """Ping the /models endpoint, return (ok, message, latency_ms)."""
        t0 = time.time()
        try:
            r = self._session.get(
                f"{self._base_url}/models",
                timeout=5,
            )
            lat = (time.time() - t0) * 1000
            if r.status_code == 200:
                n = len(r.json().get("data", []))
                return True, f"Connected ({n} models, {int(lat)}ms)", lat
            elif r.status_code == 401:
                return False, "Unauthorized — check API key", lat
            else:
                return False, f"HTTP {r.status_code}", lat
        except Exception as e:
            lat = (time.time() - t0) * 1000
            return False, f"Connection failed: {str(e)[:50]}", lat

    # ── Internals ───────────────────────────────────────────────────────────

    @staticmethod
    def _msg_to_dict(m: LLMMessage) -> Dict[str, Any]:
        d: Dict[str, Any] = {"role": m.role, "content": m.content}
        if m.name:
            d["name"] = m.name
        return d

    def _parse_response(self, data: Dict[str, Any]) -> LLMResponse:
        """
        Parse OpenAI-format response.
        Tool calls are embedded in JSON inside the content string (for models
        that don't natively support function calling) OR via native tool_calls field.
        """
        usage = data.get("usage", {})
        model = data.get("model", self._model)
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content") or ""
        finish = choice.get("finish_reason", "")

        # 1. Native function/tool calling (OpenAI format)
        native_tools = message.get("tool_calls")
        if native_tools:
            tc = native_tools[0]
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except Exception:
                args = {}
            return LLMResponse(
                content=content,
                tool_call=ToolCall(tool=fn.get("name", ""), args=args, raw=str(fn)),
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                model=model,
            )

        # 2. JSON embedded in content (fallback for non-native models)
        tool_call = self._extract_json_tool_call(content)
        return LLMResponse(
            content=content,
            tool_call=tool_call,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            model=model,
        )

    @staticmethod
    def _extract_json_tool_call(text: str) -> Optional[ToolCall]:
        """
        Find JSON block {"tool": ..., "args": {...}} in model content.
        Handles:
          1. ```json ... ``` fenced code blocks
          2. Bare JSON objects anywhere in the text (brace-balanced scan)
        Returns ToolCall if found and valid, else None.
        """
        # 1. Fenced code block: ```json { ... } ```
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fence_match:
            try:
                obj = json.loads(fence_match.group(1))
                if "tool" in obj:
                    return ToolCall(
                        tool=str(obj["tool"]),
                        args=obj.get("args", obj.get("arguments", {})),
                        raw=fence_match.group(1),
                    )
            except (json.JSONDecodeError, KeyError):
                pass

        # 2. Bare JSON — brace-balanced scanner (handles nested objects in args)
        for start in range(len(text)):
            if text[start] != '{':
                continue
            depth = 0
            in_string = False
            escape_next = False
            end = start
            for i, ch in enumerate(text[start:], start):
                if escape_next:
                    escape_next = False
                    continue
                if ch == '\\' and in_string:
                    escape_next = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            if end > start:
                candidate = text[start:end + 1]
                try:
                    obj = json.loads(candidate)
                    if isinstance(obj, dict) and "tool" in obj:
                        return ToolCall(
                            tool=str(obj["tool"]),
                            args=obj.get("args", obj.get("arguments", {})),
                            raw=candidate,
                        )
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        return None

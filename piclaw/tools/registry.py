"""
PiClaw Tool Registry — Step 4.
Every tool: name, description, input schema, permission level, executor.
Safe / Controlled / Dangerous classification.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger("piclaw.tools")


class Permission(str, Enum):
    SAFE       = "safe"        # auto-execute, no confirmation needed
    CONTROLLED = "controlled"  # execute + log, notify user
    DANGEROUS  = "dangerous"   # require explicit user confirmation


@dataclass
class ToolParam:
    name:        str
    type:        str            # "string" | "integer" | "float" | "boolean" | "enum"
    description: str
    required:    bool = True
    default:     Any  = None
    choices:     Optional[List[str]] = None


@dataclass
class ToolResult:
    success:  bool
    data:     Dict[str, Any] = field(default_factory=dict)
    message:  str  = ""
    error:    str  = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data":    self.data,
            "message": self.message,
            "error":   self.error,
        }


@dataclass
class Tool:
    name:        str
    description: str
    permission:  Permission
    params:      List[ToolParam]
    executor:    Callable[..., ToolResult]
    examples:    List[str] = field(default_factory=list)

    def schema_dict(self) -> Dict[str, Any]:
        """OpenAI-compatible function schema for LLM tool listing."""
        properties: Dict[str, Any] = {}
        required: List[str] = []
        for p in self.params:
            prop: Dict[str, Any] = {
                "type":        p.type if p.type not in ("enum",) else "string",
                "description": p.description,
            }
            if p.choices:
                prop["enum"] = p.choices
            if p.default is not None:
                prop["default"] = p.default
            properties[p.name] = prop
            if p.required:
                required.append(p.name)

        return {
            "type": "function",
            "function": {
                "name":        self.name,
                "description": self.description,
                "parameters": {
                    "type":       "object",
                    "properties": properties,
                    "required":   required,
                },
            },
        }

    def validate_args(self, args: Dict[str, Any]) -> tuple[bool, str]:
        """Validate args against schema. Returns (ok, error_message)."""
        for p in self.params:
            if p.required and p.name not in args:
                if p.default is not None:
                    args[p.name] = p.default
                else:
                    return False, f"Missing required argument: '{p.name}'"
            val = args.get(p.name)
            if val is None:
                continue
            # type coercion
            try:
                if p.type == "integer":
                    args[p.name] = int(val)
                elif p.type == "float":
                    args[p.name] = float(val)
                elif p.type == "boolean":
                    if isinstance(val, str):
                        args[p.name] = val.lower() in ("true", "1", "yes", "on")
                elif p.choices and str(val) not in p.choices:
                    return False, f"'{p.name}' must be one of {p.choices}, got '{val}'"
            except (ValueError, TypeError) as e:
                return False, f"Argument '{p.name}' type error: {e}"
        return True, ""

    def run(self, args: Dict[str, Any]) -> ToolResult:
        """Validate then execute the tool."""
        ok, err = self.validate_args(args)
        if not ok:
            return ToolResult(success=False, error=err)
        try:
            log.log(24, f"[TOOL] Executing {self.name} args={args}")
            result = self.executor(**args)
            log.log(24, f"[TOOL] {self.name} -> success={result.success}")
            return result
        except Exception as e:
            log.error(f"[TOOL] {self.name} raised: {e}")
            return ToolResult(success=False, error=str(e))


class ToolRegistry:
    """Central registry for all PiClaw tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool
        log.debug(f"[Registry] Registered tool: {tool.name} ({tool.permission.value})")

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def all(self) -> List[Tool]:
        return list(self._tools.values())

    def all_schemas(self) -> List[Dict[str, Any]]:
        """Return OpenAI-format tool schemas for all registered tools."""
        return [t.schema_dict() for t in self._tools.values()]

    def names(self) -> List[str]:
        return list(self._tools.keys())

    def summary(self) -> str:
        """Human-readable table for /tools CLI command."""
        lines = [f"{'Tool':<30} {'Permission':<12} Description"]
        lines.append("-" * 80)
        for t in sorted(self._tools.values(), key=lambda x: x.name):
            lines.append(f"{t.name:<30} {t.permission.value:<12} {t.description[:40]}")
        return "\n".join(lines)

    def execute(self, name: str, args: Dict[str, Any]) -> ToolResult:
        """Look up and execute a tool by name."""
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Unknown tool: '{name}'. Available: {', '.join(self.names())}",
            )
        return tool.run(args)


# Global singleton
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry

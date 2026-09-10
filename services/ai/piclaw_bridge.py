"""
Pi Phone OS & Simulator Bridge to PiClaw Agent.
Connects the parent project's UI, Audio, and GPIO subsystems to the
native PiClaw agent package.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("core.piclaw_bridge")

_current_dir = Path(__file__).parent.parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))


class ParentPiClawBridge:
    """
    Bridge connecting the Pi Phone OS, GUI screens, and simulated hardware
    directly to the PiClaw autonomous agent.
    """

    def __init__(self):
        self._bridge = None
        self._init_connection()

    def _init_connection(self) -> None:
        try:
            from piclaw.bridge import get_bridge
            self._bridge = get_bridge(start_services=False)
            log.info("[PiClaw Bridge] Connected to native piclaw.bridge.")
        except Exception as e:
            try:
                from bridge import get_bridge
                self._bridge = get_bridge(start_services=False)
                log.info("[PiClaw Bridge] Connected to standalone bridge.")
            except Exception as ex:
                try:
                    # Fallback to direct agent instantiation
                    from piclaw.tools.registry import get_registry
                    from piclaw.agent.agent import PiClawAgent
                    self._agent = PiClawAgent()
                    self._reg = get_registry()
                    log.info("[PiClaw Bridge] Connected via direct piclaw package.")
                except Exception as ex2:
                    log.error(f"[PiClaw Bridge] Failed to connect to PiClaw: {ex2}")

    def is_connected(self) -> bool:
        return self._bridge is not None or hasattr(self, "_agent")

    def ask(self, query: str) -> str:
        """Send prompt to PiClaw agent."""
        if self._bridge:
            return self._bridge.ask(query)
        elif hasattr(self, "_agent"):
            return self._agent.run(query)
        return "PiClaw Agent is currently offline."

    def execute_tool(self, tool_name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a tool directly via PiClaw tool registry."""
        if self._bridge:
            return self._bridge.execute_tool(tool_name, args)
        elif hasattr(self, "_reg"):
            res = self._reg.execute(tool_name, args or {})
            return res.to_dict()
        return {"success": False, "error": "PiClaw registry not available."}

    def get_status(self) -> Dict[str, Any]:
        """Get agent and hardware status."""
        if self._bridge:
            return self._bridge.get_status()
        return {"status": "offline", "tools_registered": 0}

    def list_tools(self) -> List[str]:
        """List registered tool names."""
        if self._bridge:
            return self._bridge.list_tools()
        elif hasattr(self, "_reg"):
            return self._reg.names()
        return []


_parent_bridge: Optional[ParentPiClawBridge] = None

# Backward-compatible alias
PiClawBridge = ParentPiClawBridge


def get_piclaw_bridge() -> ParentPiClawBridge:
    global _parent_bridge
    if _parent_bridge is None:
        _parent_bridge = ParentPiClawBridge()
    return _parent_bridge

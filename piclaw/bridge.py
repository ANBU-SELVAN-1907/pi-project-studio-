"""
PiClaw Bridge — Programmatic API & Parent Project Interop.
Enables external applications (e.g. Pi Phone OS, GUI, REST API, Simulator)
to seamlessly query the agent, execute tools, and inspect subsystems.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from piclaw.utils import config as cfg
from piclaw.utils import logging as log_mod
from piclaw.tools.registry import get_registry, ToolResult
from piclaw.hardware.devices import get_device_registry
from piclaw.memory.store import get_memory_store
from piclaw.events.rules import get_rule_engine
from piclaw.scheduler.scheduler import get_scheduler

log = logging.getLogger("piclaw.bridge")


class PiClawBridge:
    """
    Unified programmatic interface to PiClaw.
    Can be used by parent projects or standalone scripts.
    """

    def __init__(self, init_background_services: bool = False):
        self._initialized = False
        self._agent = None
        self._init_subsystems(init_background_services)

    def _init_subsystems(self, start_services: bool) -> None:
        if self._initialized:
            return

        # Register tools
        from piclaw.tools import (
            system,
            gpio,
            network,
            memory_tool,
            tasks_tool,
            rules_tool,
            services,
            hardware_tools,
            cooperative_tools,
        )
        reg = get_registry()
        system.register_all(reg)
        gpio.register_all(reg)
        hardware_tools.register_all(reg)
        cooperative_tools.register_all(reg)
        network.register_all(reg)
        memory_tool.register_all(reg)
        tasks_tool.register_all(reg)
        rules_tool.register_all(reg)
        services.register_all(reg)

        if start_services:
            if cfg.get("rules", "enabled", True):
                get_rule_engine().start()
            if cfg.get("scheduler", "enabled", True):
                get_scheduler().start()

        from piclaw.agent.agent import PiClawAgent
        self._agent = PiClawAgent()
        self._initialized = True
        log.info(f"[Bridge] Initialized with {len(reg.names())} tools")

    def ask(self, user_query: str) -> str:
        """Send natural language request to PiClaw ReAct agent."""
        if not self._agent:
            return "PiClaw agent is not initialized."
        return self._agent.run(user_query)

    def execute_tool(self, tool_name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a specific tool directly by name."""
        reg = get_registry()
        res = reg.execute(tool_name, args or {})
        return res.to_dict()

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return get_registry().names()

    def get_devices(self) -> List[Dict[str, Any]]:
        """List registered hardware devices."""
        return get_device_registry().list_devices()

    def get_status(self) -> Dict[str, Any]:
        """Get summary snapshot of system health, memory, and automation."""
        reg = get_registry()
        cpu_res = reg.execute("system.cpu", {})
        mem_res = reg.execute("system.memory", {})
        devices = self.get_devices()
        rules = get_rule_engine().list_rules()
        tasks = get_scheduler().list_tasks()

        return {
            "status": "online",
            "tools_registered": len(reg.names()),
            "cpu": cpu_res.message,
            "memory": mem_res.message,
            "devices_count": len(devices),
            "rules_count": len(rules),
            "tasks_count": len(tasks),
        }


_bridge_instance: Optional[PiClawBridge] = None

def get_bridge(start_services: bool = False) -> PiClawBridge:
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = PiClawBridge(init_background_services=start_services)
    return _bridge_instance

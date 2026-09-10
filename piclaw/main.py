"""
PiClaw — Entry Point.
Initializes all subsystems and starts the CLI.

Usage:
    python -m piclaw
    python piclaw/main.py
"""

import sys
import logging
from pathlib import Path

# ── Bootstrap: add project root to path ──────────────────────────────────────
_root = Path(__file__).parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# ── Config + Logging (must be first) ─────────────────────────────────────────
from piclaw.utils import config as cfg
from piclaw.utils import logging as log_mod

log_mod.setup(
    level=cfg.get("logging", "level", "INFO"),
    log_file=cfg.get("logging", "file"),
)
log = logging.getLogger("piclaw.main")

log.info("=" * 50)
log.info(" PiClaw AI Agent — Starting")
log.info("=" * 50)


def _register_tools() -> None:
    """Register all tools into the global registry."""
    from piclaw.tools import system, gpio, network, memory_tool, tasks_tool, rules_tool, services, hardware_tools, cooperative_tools
    reg = None  # use global singleton
    system.register_all(reg)
    gpio.register_all(reg)
    hardware_tools.register_all(reg)
    cooperative_tools.register_all(reg)
    network.register_all(reg)
    memory_tool.register_all(reg)
    tasks_tool.register_all(reg)
    rules_tool.register_all(reg)
    services.register_all(reg)

    from piclaw.tools.registry import get_registry
    log.info(f"[Main] {len(get_registry().names())} tools registered")


def _start_background_services() -> None:
    """Start rule engine and scheduler as daemon threads."""
    if cfg.get("rules", "enabled", True):
        from piclaw.events.rules import get_rule_engine
        engine = get_rule_engine()
        engine.start()
        log.info("[Main] Rule engine started")

    if cfg.get("scheduler", "enabled", True):
        from piclaw.scheduler.scheduler import get_scheduler
        sched = get_scheduler()
        sched.start()
        log.info("[Main] Scheduler started")


def main() -> None:
    # 1. Register all tools
    _register_tools()

    # 2. Start background services (rule engine + scheduler)
    _start_background_services()

    # 3. Build agent
    from piclaw.agent.agent import PiClawAgent
    from piclaw.cli.interface import PiClawCLI

    agent = PiClawAgent()

    # 4. Build CLI with confirmation wired to agent
    cli = PiClawCLI(agent)
    agent._confirm_cb = cli.confirm   # wire dangerous-op confirmation

    # 5. Run
    log.info("[Main] Starting CLI")
    cli.run()

    # 6. Clean exit
    log.info("[Main] PiClaw exiting cleanly")
    sys.exit(0)


if __name__ == "__main__":
    main()

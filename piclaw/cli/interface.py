"""
PiClaw CLI — clean terminal interface.
Commands: /help /status /tools /memory /tasks /rules /clear /devices /exit
Natural language passes directly to the agent.
"""

import sys
import logging
from typing import Optional

from piclaw.agent.agent import PiClawAgent
from piclaw.utils import config as cfg

log = logging.getLogger("piclaw.cli")

VERSION = "1.0.0"

# ── ANSI colours (disabled on non-TTY) ───────────────────────────────────────
_TTY = sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    if not _TTY:
        return text
    return f"\033[{code}m{text}\033[0m"

def cyan(t):    return _c("96", t)
def green(t):   return _c("92", t)
def yellow(t):  return _c("93", t)
def red(t):     return _c("91", t)
def bold(t):    return _c("1",  t)
def dim(t):     return _c("2",  t)
def magenta(t): return _c("95", t)


BANNER = f"""
{cyan('╔══════════════════════════════════════╗')}
{cyan('║')}  {bold('PiClaw')} v{VERSION}  —  AI Edge Agent       {cyan('║')}
{cyan('║')}  Raspberry Pi Zero W  |  CLI Ready    {cyan('║')}
{cyan('╚══════════════════════════════════════╝')}
"""

HELP_TEXT = f"""
{bold('Built-in commands:')}
  {yellow('/help')}     — Show this help
  {yellow('/status')}   — System health (CPU, RAM, disk, temp)
  {yellow('/tools')}    — List all available tools
  {yellow('/memory')}   — Show all remembered information
  {yellow('/tasks')}    — Show scheduled tasks
  {yellow('/rules')}    — Show automation rules
  {yellow('/devices')}  — Show registered hardware devices
  {yellow('/clear')}    — Clear conversation context
  {yellow('/exit')}     — Quit PiClaw

{bold('Example natural-language requests:')}
  {dim('what is my CPU temperature?')}
  {dim('turn GPIO 17 on')}
  {dim('remember that GPIO 17 is my bedroom fan')}
  {dim('what GPIO is my fan connected to?')}
  {dim('create a rule: if temperature exceeds 30, turn fan on')}
  {dim('turn the fan off after 10 minutes')}
  {dim('what tasks are scheduled?')}
  {dim('check my disk space')}
  {dim('ping google.com')}
"""


class PiClawCLI:
    def __init__(self, agent: PiClawAgent):
        self._agent = agent
        self._running = True

    def run(self) -> None:
        print(BANNER)
        self._check_llm()
        print(dim("Type /help for commands or ask anything naturally.\n"))

        while self._running:
            try:
                user_input = input(f"{bold(green('You'))} > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                self._cmd_exit()
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                self._handle_command(user_input)
            else:
                self._handle_query(user_input)

    # ── Command dispatcher ────────────────────────────────────────────────────

    def _handle_command(self, cmd: str) -> None:
        cmd = cmd.strip().lower()
        if cmd in ("/help", "/h", "/?"):
            print(HELP_TEXT)
        elif cmd == "/status":
            self._cmd_status()
        elif cmd == "/tools":
            self._cmd_tools()
        elif cmd == "/memory":
            self._cmd_memory()
        elif cmd == "/tasks":
            self._cmd_tasks()
        elif cmd == "/rules":
            self._cmd_rules()
        elif cmd == "/devices":
            self._cmd_devices()
        elif cmd == "/clear":
            self._cmd_clear()
        elif cmd in ("/exit", "/quit", "/q"):
            self._cmd_exit()
        else:
            print(yellow(f"Unknown command: {cmd}. Type /help for options."))

    # ── Query handler (passes to agent) ──────────────────────────────────────

    def _handle_query(self, text: str) -> None:
        print(dim("  thinking…"), end="\r", flush=True)
        try:
            reply = self._agent.chat(text)
            print(" " * 20, end="\r")  # clear "thinking…"
            print(f"{bold(cyan('PiClaw'))} > {reply}\n")
        except Exception as e:
            print(" " * 20, end="\r")
            print(red(f"  ✗ Agent error: {e}\n"))

    # ── Slash command implementations ─────────────────────────────────────────

    def _check_llm(self) -> None:
        print(dim("  Connecting to LLM…"), end="\r", flush=True)
        ok, msg, lat = self._agent.test_llm()
        print(" " * 30, end="\r")
        if ok:
            print(f"  {green('●')} LLM: {msg}")
        else:
            print(f"  {yellow('●')} LLM: {msg} {dim('(offline mode active)')}")
        print()

    def _cmd_status(self) -> None:
        from piclaw.tools.registry import get_registry
        r = get_registry().execute("system.status", {})
        self._print_result("System Status", r.message, r.success)

    def _cmd_tools(self) -> None:
        from piclaw.tools.registry import get_registry
        print(f"\n{bold('Available Tools:')}\n")
        print(get_registry().summary())
        print()

    def _cmd_memory(self) -> None:
        from piclaw.memory.store import get_memory_store
        entries = get_memory_store().list_all(limit=30)
        total   = get_memory_store().count()
        if not entries:
            print(dim("  Memory is empty.\n"))
            return
        print(f"\n{bold(f'Memory ({total} entries):')}")
        for e in entries:
            print(f"  {yellow(e['key'])}: {e['value']}")
        print()

    def _cmd_tasks(self) -> None:
        from piclaw.tools.registry import get_registry
        r = get_registry().execute("task.list", {})
        self._print_result("Scheduled Tasks", r.message, r.success)

    def _cmd_rules(self) -> None:
        from piclaw.tools.registry import get_registry
        r = get_registry().execute("rule.list", {})
        self._print_result("Automation Rules", r.message, r.success)

    def _cmd_devices(self) -> None:
        from piclaw.hardware.devices import get_device_registry
        summary = get_device_registry().summary()
        print(f"\n{bold('Hardware Devices:')}\n{summary}\n")

    def _cmd_clear(self) -> None:
        self._agent.clear_context()
        self._agent.refresh_system_prompt()
        print(green("  ✓ Conversation context cleared.\n"))

    def _cmd_exit(self) -> None:
        print(f"\n{cyan('PiClaw')} > Goodbye.\n")
        self._running = False

    @staticmethod
    def _print_result(title: str, message: str, success: bool) -> None:
        icon = green("✓") if success else red("✗")
        print(f"\n{icon} {bold(title)}:\n{message}\n")

    # ── Confirmation callback (for DANGEROUS tools) ───────────────────────────

    def confirm(self, prompt: str) -> bool:
        """Called by agent before executing DANGEROUS tools."""
        try:
            ans = input(f"{red('  ⚠')} {prompt}").strip().lower()
            return ans in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False

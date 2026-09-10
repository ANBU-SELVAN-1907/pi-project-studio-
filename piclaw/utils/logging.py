"""
PiClaw structured logger.
Supports custom log levels: AGENT, TOOL, EVENT.
Outputs clean timestamped lines; does not expose secrets.
"""

import logging
import sys
from typing import Optional

# ── Custom numeric levels ─────────────────────────────────────────────────────
AGENT_LEVEL = 25   # Between INFO(20) and WARNING(30)
TOOL_LEVEL  = 24
EVENT_LEVEL = 23

logging.addLevelName(AGENT_LEVEL, "AGENT")
logging.addLevelName(TOOL_LEVEL,  "TOOL")
logging.addLevelName(EVENT_LEVEL, "EVENT")


class PiClawLogger(logging.Logger):
    def agent(self, msg: str, *args, **kwargs):
        if self.isEnabledFor(AGENT_LEVEL):
            self._log(AGENT_LEVEL, msg, args, **kwargs)

    def tool(self, msg: str, *args, **kwargs):
        if self.isEnabledFor(TOOL_LEVEL):
            self._log(TOOL_LEVEL, msg, args, **kwargs)

    def event(self, msg: str, *args, **kwargs):
        if self.isEnabledFor(EVENT_LEVEL):
            self._log(EVENT_LEVEL, msg, args, **kwargs)


logging.setLoggerClass(PiClawLogger)


class _SecretFilter(logging.Filter):
    """Strips common secret patterns from log output."""
    _PATTERNS = ["sk-", "AQ.", "AIza", "Bearer ", "api_key"]

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for pat in self._PATTERNS:
            if pat in msg:
                record.msg = "[REDACTED — contains sensitive data]"
                record.args = ()
                break
        return True


_formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)-5s] %(message)s",
    datefmt="%H:%M:%S"
)

_initialized = False


def setup(level: str = "INFO", log_file: Optional[str] = None) -> None:
    global _initialized
    if _initialized:
        return
    _initialized = True

    root = logging.getLogger()
    numeric = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(min(numeric, EVENT_LEVEL))   # always capture our custom levels

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(_formatter)
    ch.addFilter(_SecretFilter())
    root.addHandler(ch)

    # Optional file handler
    if log_file:
        fh = logging.FileHandler(log_file)
        fh.setFormatter(_formatter)
        fh.addFilter(_SecretFilter())
        root.addHandler(fh)


def get(name: str = "piclaw") -> PiClawLogger:
    """Return a named PiClawLogger instance."""
    return logging.getLogger(name)  # type: ignore[return-value]

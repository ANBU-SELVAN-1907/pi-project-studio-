"""
PiClaw Configuration System.
Loads from .env (secrets) and piclaw.json (non-secret settings).
Never exposes keys in source code.
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

# Project root is two levels up from piclaw/utils/
PROJECT_ROOT = Path(__file__).parent.parent.parent
PICLAW_ROOT  = Path(__file__).parent.parent   # piclaw/ dir


def _find_config() -> Path:
    for candidate in [PICLAW_ROOT / "piclaw.json", PICLAW_ROOT / "config.json", PROJECT_ROOT / "piclaw.json"]:
        if candidate.exists():
            return candidate
    return PICLAW_ROOT / "piclaw.json"


def _find_env() -> Path:
    for candidate in [PICLAW_ROOT / ".env", PROJECT_ROOT / ".env"]:
        if candidate.exists():
            return candidate
    return PROJECT_ROOT / ".env"


CONFIG_FILE = _find_config()
ENV_FILE    = _find_env()
DATA_DIR    = PICLAW_ROOT / "data" if (PICLAW_ROOT / "data").exists() else (PROJECT_ROOT / "data")

# ── Ensure data dirs exist ────────────────────────────────────────────────────
for _d in ["memory", "tasks", "rules", "devices"]:
    (DATA_DIR / _d).mkdir(parents=True, exist_ok=True)

# ── Load .env manually (no extra deps) ───────────────────────────────────────
def _load_env(path: Path) -> None:
    """Parse .env file and inject into os.environ (skip if file missing)."""
    if not path.exists():
        return
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:   # env vars take priority
                os.environ[key] = val

_load_env(ENV_FILE)

# ── Load piclaw.json ──────────────────────────────────────────────────────────
_DEFAULTS: Dict[str, Any] = {
    "llm": {
        "base_url":   "http://localhost:20128/v1",
        "model":      "auto/best-chat",
        "temperature": 0.2,
        "max_tokens": 1024,
        "timeout":    30,
        "retries":    2,
    },
    "agent": {
        "max_iterations": 5,
        "confirm_dangerous": True,
        "context_window": 20,
    },
    "hardware": {
        "simulation_mode": True,
        "ble_enabled":     False,
    },
    "scheduler": {
        "enabled":         True,
        "tick_interval_s": 10,
    },
    "rules": {
        "enabled":         True,
        "poll_interval_s": 15,
    },
    "logging": {
        "level":  "INFO",
        "file":   None,
    },
}

def _deep_merge(base: Dict, override: Dict) -> Dict:
    result = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result

def _load_json_config() -> Dict[str, Any]:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                user_cfg = json.load(f)
            return _deep_merge(_DEFAULTS, user_cfg)
        except Exception as e:
            logging.warning(f"[Config] piclaw.json parse error: {e} — using defaults")
    return dict(_DEFAULTS)

_cfg: Dict[str, Any] = _load_json_config()


def get(section: str, key: str, fallback: Any = None) -> Any:
    """Get a config value from section.key."""
    return _cfg.get(section, {}).get(key, fallback)


def get_section(section: str) -> Dict[str, Any]:
    """Return entire config section as dict."""
    return dict(_cfg.get(section, {}))


def get_llm_api_key() -> str:
    """
    Retrieve LLM API key — env var PICLAW_API_KEY takes priority,
    then OMNIROUTE_API_KEY (legacy), then openai_api_key from piclaw.json.
    Never hardcoded.
    """
    return (
        os.environ.get("PICLAW_API_KEY")
        or os.environ.get("OMNIROUTE_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or _cfg.get("llm", {}).get("api_key", "")
    )


def get_llm_base_url() -> str:
    return (
        os.environ.get("PICLAW_BASE_URL")
        or _cfg.get("llm", {}).get("base_url", "http://localhost:20128/v1")
    )


def get_llm_model() -> str:
    return (
        os.environ.get("PICLAW_MODEL")
        or _cfg.get("llm", {}).get("model", "auto/best-chat")
    )


def get_all() -> Dict[str, Any]:
    """Return full config dict (safe to print — no secret values)."""
    safe = _deep_merge({}, _cfg)
    if "llm" in safe and "api_key" in safe["llm"]:
        safe["llm"]["api_key"] = "***"
    return safe


def reload() -> None:
    """Hot-reload config from disk (useful for tests)."""
    global _cfg
    _load_env(ENV_FILE)
    _cfg = _load_json_config()


# Convenience constants used throughout piclaw
PROJECT_ROOT = PROJECT_ROOT
DATA_DIR     = DATA_DIR
MEMORY_DB    = DATA_DIR / "memory" / "memory.db"
DEVICES_FILE = DATA_DIR / "devices" / "devices.json"
RULES_FILE   = DATA_DIR / "rules" / "rules.json"
TASKS_FILE   = DATA_DIR / "tasks" / "tasks.json"

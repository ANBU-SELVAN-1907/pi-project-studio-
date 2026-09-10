"""
PiClaw Rule Engine — evaluates IF-THEN rules locally without the LLM.
Condition DSL: "system.temperature > 30", "system.memory.percent > 85"
Runs in a background thread; safe for Pi Zero W.
"""

import json
import logging
import operator
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from piclaw.utils.config import RULES_FILE, get

log = logging.getLogger("piclaw.events.rules")

_OPS: Dict[str, Callable] = {
    ">":  operator.gt,
    ">=": operator.ge,
    "<":  operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}


def _resolve_metric(metric: str) -> Optional[float]:
    """
    Resolve a dotted metric name to a numeric value.
    Examples: "system.temperature", "system.memory.percent", "system.cpu.usage_percent"
    """
    try:
        parts = metric.strip().split(".")
        domain = parts[0]

        if domain == "system":
            import psutil
            sub = parts[1] if len(parts) > 1 else ""
            field = parts[2] if len(parts) > 2 else None

            if sub == "temperature":
                for zone in ["/sys/class/thermal/thermal_zone0/temp"]:
                    try:
                        return int(open(zone).read().strip()) / 1000.0
                    except Exception:
                        pass
                temps = psutil.sensors_temperatures() or {}
                for key in ("cpu_thermal", "coretemp", "acpitz"):
                    if key in temps:
                        return temps[key][0].current
                return None

            elif sub == "cpu":
                val = psutil.cpu_percent(interval=0.3)
                return val

            elif sub == "memory":
                vm = psutil.virtual_memory()
                if field == "percent":
                    return vm.percent
                if field == "available_mb":
                    return vm.available / 1e6
                return vm.percent

            elif sub == "disk":
                du = psutil.disk_usage("/")
                if field == "percent":
                    return du.percent
                if field == "free_gb":
                    return du.free / 1e9
                return du.percent

    except Exception as e:
        log.debug(f"[Rules] metric resolve error for '{metric}': {e}")
    return None


def _evaluate_condition(condition: str) -> bool:
    """
    Parse and evaluate simple condition: '<metric> <op> <value>'
    e.g. "system.temperature > 30"
    """
    for op_str, op_fn in sorted(_OPS.items(), key=lambda x: -len(x[0])):
        if op_str in condition:
            parts = condition.split(op_str, 1)
            metric = parts[0].strip()
            try:
                threshold = float(parts[1].strip())
            except ValueError:
                return False
            current = _resolve_metric(metric)
            if current is None:
                return False
            result = op_fn(current, threshold)
            log.debug(f"[Rules] {metric}={current} {op_str} {threshold} → {result}")
            return result
    return False


class RuleEngine:
    def __init__(self):
        self._rules: List[Dict[str, Any]] = []
        self._lock    = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self.load_rules()

    def load_rules(self) -> None:
        try:
            if RULES_FILE.exists():
                data = json.loads(RULES_FILE.read_text())
                with self._lock:
                    self._rules = [r for r in data.get("rules", [])
                                   if r.get("enabled", True)]
                log.info(f"[Rules] Loaded {len(self._rules)} active rule(s)")
        except Exception as e:
            log.warning(f"[Rules] Could not load rules: {e}")

    def list_rules(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._rules)

    def start(self) -> None:
        if self._running:
            return
        poll_s = get("rules", "poll_interval_s", 15)
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, args=(poll_s,), daemon=True, name="piclaw-rules"
        )
        self._thread.start()
        log.info(f"[Rules] Engine started (poll every {poll_s}s)")

    def stop(self) -> None:
        self._running = False

    def _loop(self, interval: float) -> None:
        while self._running:
            try:
                self._evaluate_all()
            except Exception as e:
                log.error(f"[Rules] Loop error: {e}")
            time.sleep(interval)

    def _evaluate_all(self) -> None:
        with self._lock:
            rules = list(self._rules)

        for rule in rules:
            try:
                cond = rule.get("condition", "")
                if _evaluate_condition(cond):
                    self._fire(rule)
            except Exception as e:
                log.error(f"[Rules] Error evaluating rule {rule.get('id')}: {e}")

    def _fire(self, rule: Dict[str, Any]) -> None:
        # Cooldown: don't fire same rule within 60s
        last = rule.get("last_triggered") or 0
        if time.time() - last < 60:
            return

        action      = rule.get("action", "")
        action_args_str = rule.get("action_args", "{}")
        try:
            args = json.loads(action_args_str) if action_args_str else {}
        except Exception:
            args = {}

        log.log(23, f"[EVENT] Rule '{rule['id']}' fired: {action}({args})")

        from piclaw.tools.registry import get_registry
        result = get_registry().execute(action, args)
        rule["last_triggered"] = time.time()
        rule["trigger_count"]  = rule.get("trigger_count", 0) + 1

        log.log(23, f"[EVENT] Rule action result: {result.message}")

        # Persist updated trigger metadata
        try:
            data = json.loads(RULES_FILE.read_text())
            for r in data.get("rules", []):
                if r["id"] == rule["id"]:
                    r["last_triggered"] = rule["last_triggered"]
                    r["trigger_count"]  = rule["trigger_count"]
            RULES_FILE.write_text(json.dumps(data, indent=2))
        except Exception:
            pass


_engine: Optional[RuleEngine] = None


def get_rule_engine() -> RuleEngine:
    global _engine
    if _engine is None:
        _engine = RuleEngine()
    return _engine

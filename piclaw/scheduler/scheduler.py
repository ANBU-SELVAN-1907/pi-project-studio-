"""
PiClaw Task Scheduler — pure-Python, no APScheduler dependency.
Parses natural-language schedules ('in 10 minutes', 'every 5 minutes', 'at 08:00').
Runs in a daemon thread. Tasks persist in data/tasks/tasks.json.
"""

import json
import logging
import re
import threading
import time
from typing import Any, Dict, List, Optional

from piclaw.utils.config import TASKS_FILE, get

log = logging.getLogger("piclaw.scheduler")


# ── Schedule parsing ──────────────────────────────────────────────────────────

def _parse_schedule(schedule: str, created_at: float) -> Dict[str, Any]:
    """
    Returns {"type": "once"|"recurring", "next_run": timestamp, "interval_s": float|None}
    """
    s = schedule.strip().lower()
    now = time.time()

    # "in X minutes/hours/seconds"
    m = re.match(r"in\s+(\d+)\s*(second|minute|hour)s?", s)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        mult = {"second": 1, "minute": 60, "hour": 3600}[unit]
        return {"type": "once", "next_run": now + n * mult, "interval_s": None}

    # "every X minutes/hours/seconds"
    m = re.match(r"every\s+(\d+)\s*(second|minute|hour)s?", s)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        mult = {"second": 1, "minute": 60, "hour": 3600}[unit]
        interval = n * mult
        return {"type": "recurring", "next_run": now + interval, "interval_s": interval}

    # "at HH:MM"
    m = re.match(r"at\s+(\d{1,2}):(\d{2})", s)
    if m:
        import datetime
        h, mn = int(m.group(1)), int(m.group(2))
        t = datetime.datetime.now().replace(hour=h, minute=mn, second=0, microsecond=0)
        if t.timestamp() <= now:
            t = t + datetime.timedelta(days=1)
        return {"type": "once", "next_run": t.timestamp(), "interval_s": None}

    # "every day at HH:MM"
    m = re.match(r"every\s+day\s+at\s+(\d{1,2}):(\d{2})", s)
    if m:
        import datetime
        h, mn = int(m.group(1)), int(m.group(2))
        t = datetime.datetime.now().replace(hour=h, minute=mn, second=0, microsecond=0)
        if t.timestamp() <= now:
            t = t + datetime.timedelta(days=1)
        return {"type": "recurring", "next_run": t.timestamp(), "interval_s": 86400}

    # Default: run in 60s (unknown schedule)
    log.warning(f"[Scheduler] Could not parse schedule '{schedule}', defaulting to 60s")
    return {"type": "once", "next_run": now + 60, "interval_s": None}


# ── Scheduler ─────────────────────────────────────────────────────────────────

class Scheduler:
    def __init__(self):
        self._tasks: List[Dict[str, Any]] = []
        self._lock    = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self.load_tasks()

    def load_tasks(self) -> None:
        try:
            if TASKS_FILE.exists():
                data = json.loads(TASKS_FILE.read_text())
                raw  = [t for t in data.get("tasks", [])
                        if t.get("status") not in ("cancelled", "done")]
                tasks = []
                for t in raw:
                    if "next_run" not in t or t["next_run"] is None:
                        parsed = _parse_schedule(t.get("schedule", ""), t.get("created_at", time.time()))
                        t.update(parsed)
                    tasks.append(t)
                with self._lock:
                    self._tasks = tasks
                log.info(f"[Scheduler] Loaded {len(tasks)} pending task(s)")
        except Exception as e:
            log.warning(f"[Scheduler] Could not load tasks: {e}")

    def cancel_task(self, task_id: str) -> None:
        with self._lock:
            self._tasks = [t for t in self._tasks if t.get("id") != task_id]

    def list_tasks(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._tasks)

    def start(self) -> None:
        if self._running:
            return
        tick = get("scheduler", "tick_interval_s", 10)
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, args=(tick,), daemon=True, name="piclaw-scheduler"
        )
        self._thread.start()
        log.info(f"[Scheduler] Started (tick every {tick}s)")

    def stop(self) -> None:
        self._running = False

    def _loop(self, tick: float) -> None:
        while self._running:
            try:
                self._tick()
            except Exception as e:
                log.error(f"[Scheduler] Tick error: {e}")
            time.sleep(tick)

    def _tick(self) -> None:
        now = time.time()
        with self._lock:
            due = [t for t in self._tasks if (t.get("next_run") or 0) <= now]

        for task in due:
            self._run_task(task)

    def _run_task(self, task: Dict[str, Any]) -> None:
        action = task.get("action", "")
        args_str = task.get("action_args", "{}")
        try:
            args = json.loads(args_str) if args_str else {}
        except Exception:
            args = {}

        log.log(23, f"[EVENT] Scheduler firing task '{task['id']}': {action}({args})")

        from piclaw.tools.registry import get_registry
        result = get_registry().execute(action, args)
        log.log(23, f"[EVENT] Task result: {result.message}")

        task["last_run"]   = time.time()
        task["run_count"]  = task.get("run_count", 0) + 1

        # Reschedule recurring or mark done
        if task.get("type") == "recurring" and task.get("interval_s"):
            task["next_run"] = time.time() + task["interval_s"]
        else:
            task["status"]   = "done"
            task["next_run"] = None
            with self._lock:
                self._tasks = [t for t in self._tasks if t["id"] != task["id"]]

        self._persist_task(task)

    def _persist_task(self, updated: Dict[str, Any]) -> None:
        try:
            data = json.loads(TASKS_FILE.read_text()) if TASKS_FILE.exists() else {"tasks": []}
            for t in data.get("tasks", []):
                if t["id"] == updated["id"]:
                    t.update(updated)
            TASKS_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            log.warning(f"[Scheduler] Persist error: {e}")


_scheduler: Optional[Scheduler] = None


def get_scheduler() -> Scheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler

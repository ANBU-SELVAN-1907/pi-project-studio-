"""
PiClaw Tasks Tool — task.create, task.list, task.cancel.
Schedules one-shot or recurring actions persisted in data/tasks/tasks.json.
"""

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from piclaw.tools.registry import Tool, ToolParam, ToolResult, Permission, get_registry
from piclaw.utils.config import TASKS_FILE

log = logging.getLogger("piclaw.tools.tasks")


# ── Persistence helpers ───────────────────────────────────────────────────────

def _load() -> dict:
    try:
        if TASKS_FILE.exists():
            return json.loads(TASKS_FILE.read_text())
    except Exception:
        pass
    return {"tasks": []}


def _save(data: dict) -> None:
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TASKS_FILE.write_text(json.dumps(data, indent=2))


# ── Executors ─────────────────────────────────────────────────────────────────

def _task_create(description: str, action: str, schedule: str,
                 action_args: str = "", **_: Any) -> ToolResult:
    """
    Create a scheduled task.
    schedule: 'in 10 minutes' | 'every 5 minutes' | 'at 08:00' | cron expression
    """
    data   = _load()
    task_id = str(uuid.uuid4())[:8]
    now     = time.time()

    task = {
        "id":          task_id,
        "description": description,
        "action":      action,
        "action_args": action_args,
        "schedule":    schedule,
        "status":      "pending",
        "created_at":  now,
        "next_run":    None,
        "last_run":    None,
        "run_count":   0,
    }
    data["tasks"].append(task)
    _save(data)

    # Notify scheduler (if running)
    try:
        from piclaw.scheduler.scheduler import get_scheduler
        get_scheduler().load_tasks()
    except Exception:
        pass

    return ToolResult(
        success=True,
        data={"task_id": task_id},
        message=f"Task created (ID: {task_id}): {description} — {schedule}",
    )


def _task_list(**_: Any) -> ToolResult:
    data = _load()
    tasks = data.get("tasks", [])
    if not tasks:
        return ToolResult(success=True, data={"tasks": []},
                          message="No tasks scheduled.")
    lines = []
    for t in tasks:
        status = t.get("status", "?")
        lines.append(
            f"[{t['id']}] {t['description'][:45]} | {t['schedule']} | {status}"
        )
    return ToolResult(
        success=True,
        data={"tasks": tasks},
        message=f"{len(tasks)} task(s):\n" + "\n".join(lines),
    )


def _task_cancel(task_id: str, **_: Any) -> ToolResult:
    data  = _load()
    tasks = data.get("tasks", [])
    found = [t for t in tasks if t["id"] == task_id]
    if not found:
        return ToolResult(success=False, error=f"Task '{task_id}' not found.")
    found[0]["status"] = "cancelled"
    _save(data)
    try:
        from piclaw.scheduler.scheduler import get_scheduler
        get_scheduler().cancel_task(task_id)
    except Exception:
        pass
    return ToolResult(success=True, message=f"Task {task_id} cancelled.")


# ── Registration ──────────────────────────────────────────────────────────────

def register_all(registry=None) -> None:
    reg = registry or get_registry()

    reg.register(Tool(
        name="task.create",
        description="Schedule a one-shot or recurring task (e.g. 'in 10 minutes', 'every 5 minutes', 'at 08:00').",
        permission=Permission.CONTROLLED,
        params=[
            ToolParam("description", "string", "Human description of what this task does"),
            ToolParam("action",      "string", "Tool name to execute (e.g. gpio.write)"),
            ToolParam("schedule",    "string", "When to run: 'in 10 minutes', 'every 5 minutes', 'at 08:00'"),
            ToolParam("action_args", "string", "JSON string of args for the action tool",
                      required=False, default="{}"),
        ],
        executor=_task_create,
        examples=["turn the fan off after 10 minutes",
                  "check temperature every 5 minutes",
                  "run system health check every hour"],
    ))

    reg.register(Tool(
        name="task.list",
        description="List all scheduled tasks.",
        permission=Permission.SAFE,
        params=[],
        executor=_task_list,
        examples=["what tasks are scheduled?", "show my tasks"],
    ))

    reg.register(Tool(
        name="task.cancel",
        description="Cancel a scheduled task by its ID.",
        permission=Permission.CONTROLLED,
        params=[
            ToolParam("task_id", "string", "Task ID to cancel"),
        ],
        executor=_task_cancel,
        examples=["cancel task abc12345"],
    ))

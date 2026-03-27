from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def empty_snapshot() -> dict[str, Any]:
    return {
        "snapshot_time": utc_now_iso(),
        "collection_status": "stale",
        "summary": {
            "total_nodes": 0,
            "nodes_by_state": {
                "idle": 0,
                "allocated": 0,
                "mixed": 0,
                "down": 0,
                "drained": 0,
                "other": 0,
            },
            "total_gpus": 0,
            "active_gpus": 0,
            "running_jobs": 0,
            "pending_jobs": 0,
        },
        "nodes": [],
        "gpus": [],
        "jobs": [],
        "errors": [],
    }


def clone_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(snapshot)

from __future__ import annotations

from collections import defaultdict
from typing import Any


def parse_nvidia_gpu_query(stdout: str, node_name: str) -> list[dict[str, Any]]:
    gpus: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 7:
            continue
        gpus.append(
            {
                "node_name": node_name,
                "gpu_index": _safe_int(parts[0]),
                "gpu_name": parts[1],
                "gpu_uuid": parts[2],
                "memory_total_mb": _safe_int(parts[3]),
                "memory_used_mb": _safe_int(parts[4]),
                "memory_free_mb": _safe_int(parts[5]),
                "utilization_gpu_percent": _safe_int(parts[6]),
                "process_count": 0,
                "processes": [],
                "telemetry_status": "ok",
            }
        )
    return gpus


def attach_gpu_processes(gpus: list[dict[str, Any]], stdout: str) -> list[dict[str, Any]]:
    by_uuid = {gpu["gpu_uuid"]: gpu for gpu in gpus}
    per_gpu_processes: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for line in stdout.splitlines():
        if not line.strip():
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 4:
            continue
        process = {
            "gpu_uuid": parts[0],
            "pid": parts[1],
            "process_name": parts[2],
            "used_gpu_memory_mb": _safe_int(parts[3]),
        }
        per_gpu_processes[parts[0]].append(process)

    for gpu_uuid, processes in per_gpu_processes.items():
        gpu = by_uuid.get(gpu_uuid)
        if gpu is None:
            continue
        gpu["process_count"] = len(processes)
        gpu["processes"] = processes
    return gpus


def _safe_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0

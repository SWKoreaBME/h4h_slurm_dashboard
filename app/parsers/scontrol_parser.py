from __future__ import annotations

from typing import Any


def _parse_key_value_tokens(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for token in text.replace("\n", " ").split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        parsed[key] = value
    return parsed


def _canonical_state(raw_state: str) -> str:
    state = raw_state.split("+", 1)[0].lower()
    if state.startswith("idle"):
        return "idle"
    if state.startswith("alloc"):
        return "allocated"
    if state.startswith("mix"):
        return "mixed"
    if state.startswith("down"):
        return "down"
    if state.startswith("drain"):
        return "drained"
    return state or "unknown"


def _extract_gpu_count(gres: str) -> int:
    if not gres:
        return 0
    total = 0
    for part in gres.split(","):
        segments = part.split(":")
        if len(segments) < 2 or segments[0] != "gpu":
            continue
        count_token = segments[-1]
        try:
            total += int(count_token)
        except ValueError:
            continue
    return total


def _extract_gpu_type(gres: str) -> str:
    if not gres:
        return ""
    gpu_types: list[str] = []
    for part in gres.split(","):
        segments = part.split(":")
        if len(segments) < 2 or segments[0] != "gpu":
            continue
        if len(segments) >= 3:
            candidate = segments[1].strip()
            if candidate and candidate not in gpu_types:
                gpu_types.append(candidate)
    return ",".join(gpu_types)


def _extract_gpu_used_count(gres_used: str, alloc_tres: str) -> int:
    if gres_used:
        total = 0
        for part in gres_used.split(","):
            segments = part.split(":")
            if len(segments) < 2 or segments[0] != "gpu":
                continue
            count_token = segments[-1]
            try:
                total += int(count_token)
            except ValueError:
                continue
        if total > 0:
            return total

    for part in alloc_tres.split(","):
        if not part.startswith("gres/gpu="):
            continue
        _, value = part.split("=", 1)
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def parse_scontrol_nodes(stdout: str) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    blocks = [block.strip() for block in stdout.split("\n\n") if block.strip()]

    for block in blocks:
        data = _parse_key_value_tokens(block)
        node_name = data.get("NodeName")
        if not node_name:
            continue
        nodes.append(
            {
                "node_name": node_name,
                "partition": data.get("Partitions", ""),
                "state": _canonical_state(data.get("State", "unknown")),
                "reason": data.get("Reason", ""),
                "cpu_total": _safe_int(data.get("CPUTot")),
                "cpu_allocated": _safe_int(data.get("CPUAlloc")),
                "memory_total_mb": _safe_int(data.get("RealMemory")),
                "memory_allocated_mb": _safe_int(data.get("AllocMem")),
                "free_memory_mb": _safe_int(data.get("FreeMem")),
                "gpu_count": _extract_gpu_count(data.get("Gres", "")),
                "gpu_type": _extract_gpu_type(data.get("Gres", "")),
                "gpu_used_count": _extract_gpu_used_count(data.get("GresUsed", ""), data.get("AllocTRES", "")),
                "gres": data.get("Gres", ""),
                "gres_used": data.get("GresUsed", ""),
                "cfg_tres": data.get("CfgTRES", ""),
                "alloc_tres": data.get("AllocTRES", ""),
                "users_on_node": [],
                "jobs_on_node": [],
                "last_gpu_probe_status": "unknown",
            }
        )
    return nodes


def _safe_int(value: str | None) -> int:
    if not value:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0

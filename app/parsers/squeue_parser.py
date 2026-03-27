from __future__ import annotations

from typing import Any


def parse_squeue(stdout: str) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 11:
            continue
        jobs.append(
            {
                "job_id": parts[0],
                "user": parts[1],
                "partition": parts[2],
                "state": parts[3],
                "runtime": parts[4],
                "num_nodes": parts[5],
                "cpus": parts[6],
                "requested_memory": parts[7],
                "requested_gres": parts[8],
                "nodelist": parts[9],
                "job_name": parts[10],
            }
        )
    return jobs

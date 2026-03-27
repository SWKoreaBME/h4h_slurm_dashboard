from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path
from typing import Any

from app.commands.nvidia import query_nvidia_local, query_nvidia_over_ssh
from app.commands.runner import CommandRunner
from app.commands.slurm import query_scontrol_nodes, query_squeue_jobs
from app.config import Settings
from app.models import clone_snapshot, empty_snapshot, utc_now_iso
from app.parsers.nvidia_smi_parser import attach_gpu_processes, parse_nvidia_gpu_query
from app.parsers.scontrol_parser import parse_scontrol_nodes
from app.parsers.squeue_parser import parse_squeue


class SnapshotCollector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.runner = CommandRunner(timeout_seconds=settings.command_timeout_seconds)
        self._lock = threading.Lock()
        self._snapshot = empty_snapshot()

    def get_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return clone_snapshot(self._snapshot)

    def collect_once(self) -> dict[str, Any]:
        if self.settings.data_source == "mock":
            snapshot = self._load_mock_snapshot(self.settings.mock_snapshot_path)
        else:
            snapshot = self._collect_live_snapshot()
        with self._lock:
            self._snapshot = snapshot
        return clone_snapshot(snapshot)

    def start_background_polling(self) -> None:
        thread = threading.Thread(target=self._poll_forever, daemon=True, name="snapshot-poller")
        thread.start()

    def _poll_forever(self) -> None:
        while True:
            try:
                self.collect_once()
            except Exception as exc:  # pragma: no cover
                with self._lock:
                    self._snapshot = self._degraded_snapshot(f"collector error: {exc}")
            time.sleep(self.settings.poll_interval_seconds)

    def _load_mock_snapshot(self, path: Path) -> dict[str, Any]:
        data = json.loads(path.read_text())
        data.setdefault("errors", [])
        data["snapshot_time"] = utc_now_iso()
        return data

    def _collect_live_snapshot(self) -> dict[str, Any]:
        snapshot = empty_snapshot()
        snapshot["snapshot_time"] = utc_now_iso()

        nodes_result = query_scontrol_nodes(self.runner)
        jobs_result = query_squeue_jobs(self.runner)

        nodes = parse_scontrol_nodes(nodes_result.stdout) if nodes_result.ok else []
        jobs = parse_squeue(jobs_result.stdout) if jobs_result.ok else []

        errors: list[str] = []
        if not nodes_result.ok:
            errors.append(f"scontrol failed: {nodes_result.stderr.strip() or nodes_result.returncode}")
        if not jobs_result.ok:
            errors.append(f"squeue failed: {jobs_result.stderr.strip() or jobs_result.returncode}")

        node_map = {node["node_name"]: node for node in nodes}
        for job in jobs:
            raw_nodelist = job.get("nodelist", "")
            for node_name in [part.strip() for part in raw_nodelist.split(",") if part.strip()]:
                node = node_map.get(node_name)
                if node is None:
                    continue
                node["jobs_on_node"].append(job["job_id"])
                if job["user"] not in node["users_on_node"]:
                    node["users_on_node"].append(job["user"])

        gpus = self._collect_gpu_data(nodes, errors)

        snapshot["nodes"] = sorted(nodes, key=self._node_sort_key)
        snapshot["jobs"] = jobs
        snapshot["gpus"] = gpus
        snapshot["errors"] = errors
        snapshot["summary"] = self._build_summary(nodes, jobs, gpus)
        snapshot["collection_status"] = "healthy" if not errors else "partial"
        self._apply_gpu_rollup(snapshot)
        return snapshot

    def _collect_gpu_data(self, nodes: list[dict[str, Any]], errors: list[str]) -> list[dict[str, Any]]:
        if not self.settings.enable_gpu_telemetry:
            return []

        if self.settings.gpu_query_mode == "local":
            gpu_result, proc_result = query_nvidia_local(self.runner)
            if not gpu_result.ok:
                errors.append(f"nvidia-smi failed: {gpu_result.stderr.strip() or gpu_result.returncode}")
                return []
            local_node_name = socket.gethostname().split(".", 1)[0]
            local_gpus = parse_nvidia_gpu_query(gpu_result.stdout, node_name=local_node_name)
            return attach_gpu_processes(local_gpus, proc_result.stdout if proc_result.ok else "")

        if self.settings.gpu_query_mode == "ssh":
            all_gpus: list[dict[str, Any]] = []
            probe_nodes = self._select_gpu_probe_nodes(nodes)
            for node in probe_nodes:
                if node.get("gpu_count", 0) <= 0:
                    continue
                gpu_result, proc_result = query_nvidia_over_ssh(
                    self.runner,
                    ssh_bin=self.settings.gpu_node_ssh_bin,
                    node_name=node["node_name"],
                    ssh_user=self.settings.gpu_node_ssh_user,
                )
                if not gpu_result.ok:
                    errors.append(
                        f"{node['node_name']} GPU query failed: {gpu_result.stderr.strip() or gpu_result.returncode}"
                    )
                    continue
                node_gpus = parse_nvidia_gpu_query(gpu_result.stdout, node_name=node["node_name"])
                all_gpus.extend(attach_gpu_processes(node_gpus, proc_result.stdout if proc_result.ok else ""))
            skipped = sum(1 for node in nodes if node.get("gpu_count", 0) > 0) - len(probe_nodes)
            if skipped > 0:
                errors.append(f"skipped GPU probes on {skipped} nodes due to probe scope/limit")
            return all_gpus

        errors.append(f"unsupported GPU query mode: {self.settings.gpu_query_mode}")
        return []

    def _build_summary(
        self,
        nodes: list[dict[str, Any]],
        jobs: list[dict[str, Any]],
        gpus: list[dict[str, Any]],
    ) -> dict[str, Any]:
        nodes_by_state = {
            "idle": 0,
            "allocated": 0,
            "mixed": 0,
            "down": 0,
            "drained": 0,
            "other": 0,
        }
        for node in nodes:
            state = node.get("state", "other")
            if state not in nodes_by_state:
                nodes_by_state["other"] += 1
            else:
                nodes_by_state[state] += 1

        running_jobs = sum(1 for job in jobs if job.get("state") == "R")
        pending_jobs = sum(1 for job in jobs if job.get("state") == "PD")

        total_gpus = sum(node.get("gpu_count", 0) for node in nodes)
        active_gpus = sum(1 for gpu in gpus if gpu.get("memory_used_mb", 0) > 0 or gpu.get("process_count", 0) > 0)
        if active_gpus == 0:
            active_gpus = sum(node.get("gpu_used_count", 0) for node in nodes)

        return {
            "total_nodes": len(nodes),
            "nodes_by_state": nodes_by_state,
            "total_gpus": total_gpus,
            "active_gpus": active_gpus,
            "running_jobs": running_jobs,
            "pending_jobs": pending_jobs,
        }

    def _apply_gpu_rollup(self, snapshot: dict[str, Any]) -> None:
        if not snapshot["gpus"]:
            for node in snapshot["nodes"]:
                if node.get("gpu_count", 0) > 0:
                    node["last_gpu_probe_status"] = "slurm-only"
                else:
                    node["last_gpu_probe_status"] = "unavailable"
            return

        gpu_counts: dict[str, int] = {}
        for gpu in snapshot["gpus"]:
            node_name = gpu["node_name"]
            gpu_counts[node_name] = gpu_counts.get(node_name, 0) + (1 if gpu.get("process_count", 0) > 0 or gpu.get("memory_used_mb", 0) > 0 else 0)

        for node in snapshot["nodes"]:
            if node["node_name"] in gpu_counts:
                node["gpu_used_count"] = gpu_counts.get(node["node_name"], 0)
                node["last_gpu_probe_status"] = "ok"
            elif node.get("gpu_count", 0) > 0:
                node["last_gpu_probe_status"] = "slurm-only"
            else:
                node["last_gpu_probe_status"] = "unavailable"

    def _node_sort_key(self, item: dict[str, Any]) -> tuple[int, str]:
        state_order = {
            "down": 0,
            "drained": 1,
            "mixed": 2,
            "allocated": 3,
            "idle": 4,
        }
        return (state_order.get(item.get("state", "unknown"), 5), item["node_name"])

    def _select_gpu_probe_nodes(self, nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        gpu_nodes = [node for node in nodes if node.get("gpu_count", 0) > 0]
        scope = self.settings.gpu_probe_scope

        if scope == "all":
            selected = gpu_nodes
        elif scope == "gpu":
            selected = [node for node in gpu_nodes if node.get("state") in {"allocated", "mixed"}]
        else:
            selected = [node for node in gpu_nodes if node.get("jobs_on_node") or node.get("state") in {"allocated", "mixed"}]

        limit = max(self.settings.gpu_probe_limit, 0)
        if limit == 0:
            return []
        return selected[:limit]

    def _degraded_snapshot(self, error: str) -> dict[str, Any]:
        snapshot = empty_snapshot()
        snapshot["collection_status"] = "stale"
        snapshot["errors"] = [error]
        snapshot["snapshot_time"] = utc_now_iso()
        return snapshot

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    data_source: str
    mock_snapshot_path: Path
    bind_host: str
    port: int
    refresh_seconds: int
    poll_interval_seconds: int
    command_timeout_seconds: int
    enable_gpu_telemetry: bool
    gpu_query_mode: str
    gpu_node_ssh_user: str
    gpu_node_ssh_bin: str
    gpu_probe_scope: str
    gpu_probe_limit: int


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
      return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    base_dir = Path(__file__).resolve().parent.parent
    data_source = os.getenv("DASHBOARD_DATA_SOURCE", "mock").strip().lower()
    mock_path = os.getenv("DASHBOARD_MOCK_SNAPSHOT_PATH", "mock/snapshot_healthy.json")

    return Settings(
        base_dir=base_dir,
        data_source=data_source,
        mock_snapshot_path=(base_dir / mock_path).resolve(),
        bind_host=os.getenv("DASHBOARD_BIND_HOST", "127.0.0.1"),
        port=int(os.getenv("DASHBOARD_PORT", "8000")),
        refresh_seconds=int(os.getenv("DASHBOARD_REFRESH_SECONDS", "15")),
        poll_interval_seconds=int(os.getenv("DASHBOARD_POLL_INTERVAL_SECONDS", "15")),
        command_timeout_seconds=int(os.getenv("DASHBOARD_COMMAND_TIMEOUT_SECONDS", "8")),
        enable_gpu_telemetry=_bool_env("DASHBOARD_ENABLE_GPU_TELEMETRY", True),
        gpu_query_mode=os.getenv("DASHBOARD_GPU_QUERY_MODE", "local").strip().lower(),
        gpu_node_ssh_user=os.getenv("DASHBOARD_GPU_NODE_SSH_USER", "").strip(),
        gpu_node_ssh_bin=os.getenv("DASHBOARD_GPU_NODE_SSH_BIN", "ssh").strip() or "ssh",
        gpu_probe_scope=os.getenv("DASHBOARD_GPU_PROBE_SCOPE", "active").strip().lower(),
        gpu_probe_limit=int(os.getenv("DASHBOARD_GPU_PROBE_LIMIT", "8")),
    )

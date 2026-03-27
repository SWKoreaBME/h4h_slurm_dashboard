from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass
class SnapshotCache:
    _snapshot: dict[str, Any] | None = None
    _lock: Lock = field(default_factory=Lock)

    def set_snapshot(self, snapshot: dict[str, Any]) -> None:
        with self._lock:
            self._snapshot = snapshot

    def get_snapshot(self) -> dict[str, Any] | None:
        with self._lock:
            if self._snapshot is None:
                return None
            return dict(self._snapshot)

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Sequence


@dataclass
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class CommandRunner:
    def __init__(self, timeout_seconds: int) -> None:
        self.timeout_seconds = timeout_seconds

    def run(self, args: Sequence[str]) -> CommandResult:
        try:
            completed = subprocess.run(
                list(args),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            return CommandResult(
                args=list(args),
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        except subprocess.TimeoutExpired as exc:
            return CommandResult(
                args=list(args),
                returncode=124,
                stdout=exc.stdout or "",
                stderr=f"timeout after {self.timeout_seconds}s",
            )
        except FileNotFoundError:
            return CommandResult(
                args=list(args),
                returncode=127,
                stdout="",
                stderr=f"command not found: {args[0]}",
            )

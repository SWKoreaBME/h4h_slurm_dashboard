from __future__ import annotations

from app.commands.runner import CommandResult, CommandRunner


def query_scontrol_nodes(runner: CommandRunner) -> CommandResult:
    return runner.run(["scontrol", "show", "nodes"])


def query_squeue_jobs(runner: CommandRunner) -> CommandResult:
    fmt = "%.18i|%.8u|%.9P|%.2t|%.10M|%.6D|%.8C|%.10m|%.20b|%N|%.40j"
    return runner.run(["squeue", "-h", "-o", fmt])

from __future__ import annotations

from app.commands.runner import CommandResult, CommandRunner


def query_nvidia_local(runner: CommandRunner) -> tuple[CommandResult, CommandResult]:
    gpu_result = runner.run(
        [
            "nvidia-smi",
            "--query-gpu=index,name,uuid,memory.total,memory.used,memory.free,utilization.gpu",
            "--format=csv,noheader,nounits",
        ]
    )
    proc_result = runner.run(
        [
            "nvidia-smi",
            "--query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory",
            "--format=csv,noheader,nounits",
        ]
    )
    return gpu_result, proc_result


def query_nvidia_over_ssh(
    runner: CommandRunner,
    ssh_bin: str,
    node_name: str,
    ssh_user: str = "",
) -> tuple[CommandResult, CommandResult]:
    target = f"{ssh_user}@{node_name}" if ssh_user else node_name
    base_args = [ssh_bin, "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", target]

    gpu_result = runner.run(
        base_args
        + [
            "nvidia-smi",
            "--query-gpu=index,name,uuid,memory.total,memory.used,memory.free,utilization.gpu",
            "--format=csv,noheader,nounits",
        ]
    )
    proc_result = runner.run(
        base_args
        + [
            "nvidia-smi",
            "--query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory",
            "--format=csv,noheader,nounits",
        ]
    )
    return gpu_result, proc_result

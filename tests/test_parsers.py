from app.parsers.nvidia_smi_parser import attach_gpu_processes, parse_nvidia_gpu_query
from app.parsers.scontrol_parser import parse_scontrol_nodes
from app.parsers.squeue_parser import parse_squeue


def test_parse_squeue() -> None:
    stdout = "123|alice|gpu|R|10:00|1|8|64G|gpu:1|gpu-01|train\n"
    jobs = parse_squeue(stdout)
    assert len(jobs) == 1
    assert jobs[0]["job_id"] == "123"
    assert jobs[0]["user"] == "alice"
    assert jobs[0]["nodelist"] == "gpu-01"


def test_parse_scontrol_nodes() -> None:
    stdout = (
        "NodeName=gpu-01 CPUTot=64 CPUAlloc=32 RealMemory=515000 AllocMem=300000 "
        "FreeMem=120000 Gres=gpu:a100:4 State=MIXED Partitions=gpu\n\n"
    )
    nodes = parse_scontrol_nodes(stdout)
    assert len(nodes) == 1
    assert nodes[0]["node_name"] == "gpu-01"
    assert nodes[0]["state"] == "mixed"
    assert nodes[0]["gpu_count"] == 4
    assert nodes[0]["gpu_type"] == "a100"


def test_parse_nvidia_and_processes() -> None:
    gpu_stdout = "0, NVIDIA A100, GPU-1, 81920, 40960, 40960, 87\n"
    proc_stdout = "GPU-1, 9999, python, 40960\n"
    gpus = parse_nvidia_gpu_query(gpu_stdout, node_name="gpu-01")
    gpus = attach_gpu_processes(gpus, proc_stdout)
    assert len(gpus) == 1
    assert gpus[0]["process_count"] == 1

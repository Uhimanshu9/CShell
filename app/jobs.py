from __future__ import annotations

import os
from dataclasses import dataclass
from subprocess import Popen


@dataclass
class Job:
    job_id: int
    pid: int
    command: str
    process: Popen | None


_jobs: list[Job] = []
_next_job_id: int = 1


def _is_pid_running(pid: int) -> bool:
    try:
        waited_pid, _status = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        # Either already reaped, or not our child.
        return False
    return waited_pid == 0


def _job_status(job: Job) -> str:
    if job.process is not None:
        return "Running" if job.process.poll() is None else "Done"
    return "Running" if _is_pid_running(job.pid) else "Done"


def register_job(*, pid: int, command: str, process: Popen | None = None) -> Job:
    global _next_job_id

    job = Job(job_id=_next_job_id, pid=pid, command=command, process=process)
    _next_job_id += 1
    _jobs.append(job)
    return job


def handle_jobs(_args: list[str]) -> None:
    # Output format (example):
    # [1] +  Running                 sleep 10 &
    # - job number in brackets
    # - '+' for most recent job, '-' for previous, ' ' otherwise
    # - two spaces
    # - status padded to 24 chars
    # - command string

    global _jobs

    if not _jobs:
        return

    jobs_with_status: list[tuple[Job, str]] = [(job, _job_status(job)) for job in _jobs]

    most_recent = _jobs[-1].job_id
    previous = _jobs[-2].job_id if len(_jobs) >= 2 else None

    for job, status in jobs_with_status:
        marker = " "
        if job.job_id == most_recent:
            marker = "+"
        elif previous is not None and job.job_id == previous:
            marker = "-"
        print(f"[{job.job_id}] {marker}  {status:<24}{job.command}")

    # Remove completed jobs so they don't appear in subsequent `jobs` calls.
    _jobs = [job for job, status in jobs_with_status if status == "Running"]
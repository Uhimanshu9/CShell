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
    done: bool = False
    notified: bool = False


_jobs: list[Job] = []
_next_job_id: int = 1


def _is_pid_running(pid: int) -> bool:
    try:
        waited_pid, _status = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        # Either already reaped, or not our child.
        return False
    return waited_pid == 0


def _refresh_job_state(job: Job) -> None:
    if job.done:
        return

    if job.process is not None:
        if job.process.poll() is not None:
            job.done = True
        return

    # For forked builtins we don't have a Popen; use waitpid(WNOHANG).
    try:
        waited_pid, _status = os.waitpid(job.pid, os.WNOHANG)
    except ChildProcessError:
        # Already reaped.
        waited_pid = job.pid

    if waited_pid != 0:
        job.done = True


def _job_status(job: Job) -> str:
    _refresh_job_state(job)
    return "Done" if job.done else "Running"


def _job_marker(job_ids: list[int], job_id: int) -> str:
    if not job_ids:
        return " "
    most_recent = job_ids[-1]
    previous = job_ids[-2] if len(job_ids) >= 2 else None
    if job_id == most_recent:
        return "+"
    if previous is not None and job_id == previous:
        return "-"
    return " "


def _format_job_line(*, job: Job, status: str, marker: str) -> str:
    # Codecrafters expects a fixed amount of spacing after the status word.
    # - Running + 17 spaces
    # - Done + 17 spaces
    command_str = f"{job.command} &" if status == "Running" else job.command
    return f"[{job.job_id}]{marker}  {status}{' ' * 17}{command_str}"


def register_job(*, pid: int, command: str, process: Popen | None = None) -> Job:
    global _next_job_id

    job = Job(job_id=_next_job_id, pid=pid, command=command, process=process)
    _next_job_id += 1
    _jobs.append(job)
    return job


def notify_done_jobs() -> None:
    """Print one-time 'Done' recap lines for jobs that finished since last prompt."""
    job_ids = [job.job_id for job in _jobs]
    for job in _jobs:
        status = _job_status(job)
        if status == "Done" and not job.notified:
            marker = _job_marker(job_ids, job.job_id)
            print(_format_job_line(job=job, status=status, marker=marker))
            job.notified = True


def handle_jobs(_args: list[str]) -> None:
    # Output format (example):
    # [1] +  Running                 sleep 10 &
    # - job number in brackets
    # - '+' for most recent job, '-' for previous, ' ' otherwise
    # - two spaces
    # - status padded to a fixed width (Codecrafters expects exact spacing)
    # - command string

    global _jobs

    if not _jobs:
        return

    jobs_with_status: list[tuple[Job, str]] = [(job, _job_status(job)) for job in _jobs]

    # If a job was already announced as Done via the automatic recap, do not
    # print it again in `jobs` output. Still reap/remove it below.
    jobs_to_show: list[tuple[Job, str]] = [
        (job, status)
        for job, status in jobs_with_status
        if not (status == "Done" and job.notified)
    ]

    visible_job_ids = [job.job_id for job, _status in jobs_to_show]
    for job, status in jobs_to_show:
        marker = _job_marker(visible_job_ids, job.job_id)
        print(_format_job_line(job=job, status=status, marker=marker))

    # Remove completed jobs so they don't appear in subsequent `jobs` calls.
    _jobs = [job for job, status in jobs_with_status if status == "Running"]
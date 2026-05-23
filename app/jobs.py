background_jobs: list[int] = []


def register_job(pid: int) -> int:
    background_jobs.append(pid)
    return len(background_jobs)


def handle_jobs(_args: list[str]) -> None:
    # Minimal implementation: just list known background PIDs.
    for job_id, pid in enumerate(background_jobs, start=1):
        print(f"[{job_id}] {pid}")
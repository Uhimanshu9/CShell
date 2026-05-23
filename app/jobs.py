import subprocess



background_jobs = []


def handle_jobs(args):
    if len(args) > 1:
        if args[-1] == "&":
            process = subprocess.Popen(args[:-1])
            background_jobs.append(process)

            print(f"[{len(background_jobs)}] {process.pid}")
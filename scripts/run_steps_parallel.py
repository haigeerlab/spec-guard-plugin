#!/usr/bin/env python3
"""Run validate's regression steps side by side and print them in the original order.

    run_steps_parallel.py [--section <header>] <command> [<command> ...] [--section <header> <command> ...]

Each command runs under /bin/bash with stdin closed; its stdout and stderr go to one temporary file.  At most
SG_VALIDATE_JOBS commands run at once (default: CPU count; 1 runs them one after another).  A step is printed, in full,
as soon as it and every step before it have finished, under its section header.  The run fails when any step exits
non-zero or is killed, and the failing commands are listed at the end.  An empty command is a usage error rather than a
skipped step.  Standard library only; works on the macOS system Python 3.9.
"""
from __future__ import print_function

import concurrent.futures
import os
import subprocess
import sys
import tempfile
import time

USAGE = "用法: run_steps_parallel.py [--section <标题>] <命令> ...（SG_VALIDATE_JOBS 为正整数）"


def parse(args):
    """[(section header or None, command)]; None on a usage error."""
    steps, section = [], None
    index = 0
    while index < len(args):
        if args[index] == "--section":
            if index + 1 >= len(args):
                return None
            section = args[index + 1]
            index += 2
            continue
        if not args[index].strip():
            return None
        steps.append((section, args[index]))
        index += 1
    return steps or None


def jobs_from_env():
    raw = os.environ.get("SG_VALIDATE_JOBS", "")
    if raw == "":
        return os.cpu_count() or 1
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value >= 1 else None


def run_step(command, log):
    began = time.time()
    try:
        code = subprocess.call(["/bin/bash", "-c", command], stdin=subprocess.DEVNULL, stdout=log,
                               stderr=subprocess.STDOUT)
    except OSError as error:
        log.write(("无法启动：%s\n" % error).encode("utf-8"))
        code = 127
    return code, time.time() - began


def main(argv):
    steps = parse(argv[1:])
    jobs = jobs_from_env()
    if steps is None or jobs is None:
        print(USAGE, file=sys.stderr)
        return 2
    out = sys.stdout.buffer
    began = time.time()
    failed = []
    current = None
    with tempfile.TemporaryDirectory(prefix="sg-validate-steps-") as tmp:
        logs = [open(os.path.join(tmp, "%03d.log" % number), "w+b") for number in range(len(steps))]
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
                futures = [pool.submit(run_step, command, log) for (_, command), log in zip(steps, logs)]
                for (section, command), log, future in zip(steps, logs, futures):
                    code, seconds = future.result()
                    if section != current:
                        if current is not None:
                            out.write(b"\n")
                        out.write((section + "\n").encode("utf-8"))
                        current = section
                    log.seek(0)
                    out.write(log.read())
                    if code != 0:
                        failed.append(command)
                        out.write(("  ❌ 这一步失败（退出码 %d，%.1fs）：%s\n" % (code, seconds, command)).encode("utf-8"))
                    out.flush()
        finally:
            for log in logs:
                log.close()
    print("")
    print("── 共 %d 步，%d 个并行，用时 %.1fs ──" % (len(steps), jobs, time.time() - began))
    if failed:
        print("  ❌ 失败的步骤：")
        for command in failed:
            print("     %s" % command)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

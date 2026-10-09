#!/usr/bin/env python3
"""Run one unittest file with its TestCase classes split across processes.

    run_tests_parallel.py <test file> [--jobs N]

Each worker imports the file (its directory goes first on sys.path, as when the file is run directly), runs only its
share of the classes (a class bigger than a fair share is cut into method chunks), and reports how many tests ran.  The run fails when any worker fails, when no test was discovered,
or when the workers together ran fewer tests than discovery found -- a lost test is never a pass.  Standard library
only; works on the macOS system Python 3.9.
"""
from __future__ import print_function

import importlib.util
import io
import json
import os
import subprocess
import sys
import time
import unittest

WORKER_FLAG = "--worker"


def load_module(path):
    path = os.path.abspath(path)
    sys.path.insert(0, os.path.dirname(path))
    name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def discover(module):
    """[(class name, [test method names])] for every TestCase class defined in the module, in definition order."""
    loader = unittest.defaultTestLoader
    found = []
    for name, value in vars(module).items():
        if (isinstance(value, type) and issubclass(value, unittest.TestCase)
                and value.__module__ == module.__name__):
            methods = list(loader.getTestCaseNames(value))
            if methods:
                found.append((name, methods))
    return found


def units(classes, jobs):
    """Work units: whole classes, except that a class bigger than a fair share is cut into method chunks.

    A cut class runs its setUpClass once per chunk, which is correct but repeats that setup."""
    total = sum(len(methods) for _, methods in classes)
    share = max(1, -(-total // jobs))
    result = []
    for name, methods in classes:
        if len(methods) <= share:
            result.append((name, None, len(methods)))
            continue
        for start in range(0, len(methods), share):
            chunk = methods[start:start + share]
            result.append((name, chunk, len(chunk)))
    return result


def split(work, jobs):
    """Greedy balance by test count: largest unit first into the lightest bucket."""
    buckets = [[] for _ in range(jobs)]
    weights = [0] * jobs
    for name, methods, count in sorted(work, key=lambda item: -item[2]):
        index = weights.index(min(weights))
        buckets[index].append(name if methods is None else "%s=%s" % (name, ",".join(methods)))
        weights[index] += count
    return [bucket for bucket in buckets if bucket]


def worker(path, names):
    os.environ["SG_PARALLEL_WORKER"] = "1"
    module = load_module(path)
    suite = unittest.TestSuite()
    for spec in names:
        name, _, methods = spec.partition("=")
        cls = getattr(module, name, None)
        if cls is None:
            continue
        if methods:
            suite.addTests(cls(method) for method in methods.split(","))
        else:
            suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    stream = io.StringIO()
    began = time.time()
    result = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
    failed = sorted({type(test).__name__ for test, _ in result.failures + result.errors
                     if isinstance(test, unittest.TestCase)} |
                    {str(test) for test, _ in result.failures + result.errors
                     if not isinstance(test, unittest.TestCase)})
    print(json.dumps({"ran": result.testsRun, "ok": result.wasSuccessful(), "failed": failed,
                      "seconds": round(time.time() - began, 1), "output": stream.getvalue()}))
    return 0


def main(argv):
    if len(argv) >= 3 and argv[1] == WORKER_FLAG:
        return worker(argv[2], argv[3:])
    args = argv[1:]
    jobs = None
    if "--jobs" in args:
        index = args.index("--jobs")
        try:
            jobs = int(args[index + 1])
        except (IndexError, ValueError):
            print("用法: run_tests_parallel.py <test file> [--jobs N]", file=sys.stderr)
            return 2
        del args[index:index + 2]
    if len(args) != 1 or (jobs is not None and jobs < 1):
        print("用法: run_tests_parallel.py <test file> [--jobs N]", file=sys.stderr)
        return 2
    path = args[0]
    classes = discover(load_module(path))
    total = sum(len(methods) for _, methods in classes)
    if not total:
        print("  ❌ %s 里没有发现任何用例 —— 这是没找到，不是通过" % path)
        return 1
    jobs = jobs or os.cpu_count() or 1
    work = units(classes, jobs)
    jobs = min(jobs, len(work))
    began = time.time()
    procs = [subprocess.Popen([sys.executable, "-B", os.path.abspath(__file__), WORKER_FLAG, path] + bucket,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
             for bucket in split(work, jobs)]
    ran, failed, ok = 0, [], True
    print("── %s：%d 个用例，%d 个类，%d 个进程 ──" % (os.path.basename(path), total, len(classes), len(procs)))
    for number, proc in enumerate(procs, 1):
        out, err = proc.communicate()
        try:
            report = json.loads(out.strip().splitlines()[-1])
        except (IndexError, ValueError):
            report = {"ran": 0, "ok": False, "failed": ["进程 %d 没有返回结果" % number], "seconds": 0, "output": err}
        ran += report["ran"]
        if proc.returncode != 0 or not report["ok"]:
            ok = False
            failed.extend(report["failed"])
            print(report["output"][-4000:])
            if err.strip():
                print(err[-2000:])
        print("  进程 %d：%d 个用例，%.1fs" % (number, report["ran"], report["seconds"]))
    if ran != total:
        ok = False
        print("  ❌ 用例数对不上：发现 %d 个，实际只跑了 %d 个" % (total, ran))
    if failed:
        print("  ❌ 失败的类：%s" % "、".join(sorted(set(failed))))
    print("%s 共 %d 个用例，用时 %.1fs" % ("✅" if ok else "❌", ran, time.time() - began))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

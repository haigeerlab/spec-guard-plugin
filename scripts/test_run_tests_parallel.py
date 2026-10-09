"""run_tests_parallel.py splits one unittest file by TestCase class across processes and fails on any lost test."""
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

RUNNER = Path(__file__).resolve().with_name('run_tests_parallel.py')

TEMPLATE = '''
import os, unittest
import helper_mod  # imported from the test file's own directory, like the hooks tests do

class AlphaTests(unittest.TestCase):
    def test_one(self):
        self.assertEqual(helper_mod.VALUE, 1)
    def test_two(self):
        self.assertTrue(True)

class BetaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ready = True
    def test_three(self):
        self.assertTrue(self.ready)
    def test_four(self):
        {beta_four}

class GammaTests(unittest.TestCase):
    def test_five(self):
        self.assertTrue(True)
{extra}
'''


class RunTestsParallelTests(unittest.TestCase):
    def write(self, beta_four='self.assertTrue(True)', extra=''):
        self.tmp = tempfile.TemporaryDirectory(prefix='sg-parallel-')
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        (root / 'helper_mod.py').write_text('VALUE = 1\n')
        path = root / 'test_sample.py'
        path.write_text(textwrap.dedent(TEMPLATE.format(beta_four=beta_four, extra=extra)))
        return path

    def run_runner(self, path, *args):
        return subprocess.run([sys.executable, '-B', str(RUNNER), str(path), *args],
                              capture_output=True, text=True)

    def test_all_pass_exits_zero_and_counts_every_test(self):
        p = self.run_runner(self.write())
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn('5 个用例', p.stdout)

    def test_a_failing_class_fails_the_run_and_is_named(self):
        p = self.run_runner(self.write(beta_four='self.assertTrue(False)'))
        self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn('BetaTests', p.stdout + p.stderr)

    def test_an_erroring_class_fails_the_run(self):
        p = self.run_runner(self.write(beta_four='raise RuntimeError("boom")'))
        self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_a_lost_test_fails_the_run(self):
        # A class whose module-level skip removes it from the worker but not from discovery would lose
        # tests silently; simulate a worker that runs fewer tests than were discovered.
        extra = textwrap.dedent('''
        if os.environ.get("SG_PARALLEL_WORKER"):
            del GammaTests
        ''')
        p = self.run_runner(self.write(extra=extra))
        self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn('用例数对不上', p.stdout + p.stderr)

    def test_jobs_sets_the_number_of_processes(self):
        p = self.run_runner(self.write(), '--jobs', '1')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn('1 个进程', p.stdout)
        p = self.run_runner(self.write(), '--jobs', '3')
        self.assertIn('3 个进程', p.stdout)

    def test_a_big_single_class_is_split_by_method(self):
        # One class with many tests (like test_local_ticket_portability) still spreads across processes.
        path = self.write()
        body = 'import unittest\n\nclass OnlyTests(unittest.TestCase):\n' + ''.join(
            '    def test_%d(self):\n        self.assertTrue(True)\n' % i for i in range(9))
        path.write_text(body)
        p = self.run_runner(path, '--jobs', '3')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn('3 个进程', p.stdout)
        self.assertIn('9 个用例', p.stdout)
        path.write_text(body.replace('range(9)', 'range(9)').replace('self.assertTrue(True)\n', 'self.assertTrue(True)\n', 1)
                        + '    def test_bad(self):\n        self.fail("x")\n')
        p = self.run_runner(path, '--jobs', '3')
        self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_zero_discovered_tests_is_not_a_pass(self):
        path = self.write()
        path.write_text('import unittest\n')
        p = self.run_runner(path)
        self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == '__main__':
    unittest.main()

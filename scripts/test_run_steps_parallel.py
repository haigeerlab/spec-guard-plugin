"""run_steps_parallel.py runs validate's regression steps side by side, prints each step in the original order, and
fails when any step fails."""
from pathlib import Path
import os
import subprocess
import sys
import unittest

RUNNER = Path(__file__).resolve().with_name('run_steps_parallel.py')


def run(*args, jobs=None):
    env = dict(os.environ)
    env.pop('SG_VALIDATE_JOBS', None)
    if jobs is not None:
        env['SG_VALIDATE_JOBS'] = jobs
    return subprocess.run([sys.executable, '-B', str(RUNNER), *args], capture_output=True, text=True, env=env)


class RunStepsParallelTests(unittest.TestCase):
    def test_all_pass_exits_zero_and_counts_every_step(self):
        p = run('echo one', 'echo two', 'echo three')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn('3 步', p.stdout)
        for word in ('one', 'two', 'three'):
            self.assertIn(word, p.stdout)

    def test_a_failing_step_fails_the_run_and_is_named(self):
        p = run('echo fine', 'echo broken; exit 3', 'echo also-fine')
        self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        summary = p.stdout[p.stdout.rindex('失败的步骤'):]
        self.assertIn('echo broken; exit 3', summary)
        self.assertNotIn('echo fine', summary)
        self.assertIn('also-fine', p.stdout)  # later steps still run and print

    def test_a_killed_step_fails_the_run(self):
        p = run('echo fine', 'kill -9 $$')
        self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn('kill -9 $$', p.stdout)

    def test_output_keeps_the_original_order(self):
        # The first step finishes last; its output must still come first, stderr included.
        p = run('sleep 1; echo first-out; echo first-err >&2', 'echo second', jobs='2')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertLess(p.stdout.index('first-out'), p.stdout.index('second'))
        self.assertLess(p.stdout.index('first-err'), p.stdout.index('second'))

    def test_section_headers_come_before_their_steps(self):
        p = run('--section', '═══ A ═══', 'echo a1', 'echo a2', '--section', '═══ B ═══', 'echo b1')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        out = p.stdout
        self.assertLess(out.index('═══ A ═══'), out.index('a1'))
        self.assertLess(out.index('a2'), out.index('═══ B ═══'))
        self.assertLess(out.index('═══ B ═══'), out.index('b1'))
        self.assertIn('3 步', out)

    def test_jobs_one_runs_steps_one_after_another(self):
        # With one slot the second step only starts after the first ends, so it sees the first step's file.
        marker = Path(self.tmpdir()) / 'done'
        p = run('sleep 1; touch %s' % marker, 'test -f %s' % marker, jobs='1')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn('1 个并行', p.stdout)

    def test_jobs_runs_steps_side_by_side(self):
        # Handshake instead of timing: the first step only succeeds if the second one runs while it is still waiting.
        marker = Path(self.tmpdir()) / 'second-started'
        wait = 'for i in $(seq 300); do [ -f %s ] && exit 0; sleep 0.1; done; exit 1' % marker
        p = run(wait, 'touch %s' % marker, jobs='2')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_bad_jobs_is_a_usage_error(self):
        for value in ('0', '-1', 'x'):
            p = run('echo one', jobs=value)
            self.assertEqual(p.returncode, 2, value + p.stdout + p.stderr)
            self.assertIn('用法', p.stderr)

    def test_an_empty_step_is_a_usage_error_not_a_skip(self):
        # An unset variable in validate.sh would arrive as an empty step; it must not silently disappear.
        p = run('echo one', '')
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn('用法', p.stderr)

    def test_no_steps_is_a_usage_error(self):
        for args in ((), ('--section', '═══ A ═══')):
            p = run(*args)
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertIn('用法', p.stderr)

    def tmpdir(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory(prefix='sg-steps-')
        self.addCleanup(tmp.cleanup)
        return tmp.name


if __name__ == '__main__':
    unittest.main()

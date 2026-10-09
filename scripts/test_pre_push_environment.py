"""Exercise generated pre-push through real, local-only Git pushes."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

INSTALLER = Path(__file__).resolve().with_name('install-git-hooks.sh')


class PrePushEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='sg-pre-push-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        self.env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
        self.run_git('init', '-q', '-b', 'main', str(self.repo))
        self.run_git('-C', str(self.repo), 'config', 'user.name', 'Fixture Owner')
        self.run_git('-C', str(self.repo), 'config', 'user.email', 'owner@example.invalid')
        self.run_git('-C', str(self.repo), 'commit', '-q', '--allow-empty', '-m', 'fixture')
        self.remote = self.root / 'remote.git'
        self.run_git('init', '-q', '--bare', str(self.remote))
        self.run_git('-C', str(self.repo), 'remote', 'add', 'origin', str(self.remote))

    def run_git(self, *args):
        return subprocess.run(['git', *args], env=self.env, text=True,
                              capture_output=True, check=True).stdout.strip()

    def prepare(self, linked=False):
        work = self.repo
        if linked:
            work = self.root / 'linked'
            self.run_git('-C', str(self.repo), 'worktree', 'add', '-q', '-b', 'linked', str(work))
        (work / 'scripts').mkdir()
        shutil.copy2(INSTALLER, work / 'scripts/install-git-hooks.sh')
        shutil.copy2(INSTALLER.with_name('verified_trees.py'), work / 'scripts/verified_trees.py')
        probe = '''#!/bin/bash
set -eu
printf '%s\\n' "$0" >> "$SG_PROBE_LOG"
git init -q --bare "$SG_SCRATCH/bare"
git init -q "$SG_SCRATCH/normal"
git -C "$SG_SCRATCH/normal" config user.name "Probe Identity"
git -C "$SG_SCRATCH/normal" config remote.origin.url "fixture-only"
[ "${SG_FAIL:-}" != "$(basename "$0")" ]
'''
        for path in ['scripts/validate.sh', 'plugins/spec-guard/hooks/test-phase-guard.sh',
                     'plugins/spec-guard/hooks/test-verify-artifacts.sh']:
            p = work / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(probe)
        subprocess.run(['/bin/bash', str(work / 'scripts/install-git-hooks.sh')],
                       env=self.env, check=True, capture_output=True)
        return work

    def push(self, linked=False, failure=''):
        work = self.prepare(linked)
        config = self.repo / '.git/config'
        before = config.read_bytes()
        log = self.root / 'calls'
        scratch = self.root / 'scratch'
        scratch.mkdir()
        env = dict(self.env, SG_PROBE_LOG=str(log), SG_SCRATCH=str(scratch), SG_FAIL=failure)
        p = subprocess.run(['git', '-C', str(work), 'push', 'origin', 'HEAD:refs/heads/probe'],
                           env=env, text=True, capture_output=True)
        self.assertEqual(config.read_bytes(), before, p.stdout + p.stderr)
        self.assertEqual(len(log.read_text().splitlines()), 3)
        refs = self.run_git('--git-dir', str(self.remote), 'for-each-ref', '--format=%(refname)')
        if failure:
            self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertNotIn('refs/heads/probe', refs)
        else:
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertIn('refs/heads/probe', refs)

    def push_refs(self, work, *refspecs):
        """Push refspecs once; return the process and how many checks the hook ran."""
        log = self.root / 'calls'
        if log.exists():
            log.unlink()
        scratch = Path(tempfile.mkdtemp(dir=self.root))
        env = dict(self.env, SG_PROBE_LOG=str(log), SG_SCRATCH=str(scratch), SG_FAIL='')
        p = subprocess.run(['git', '-C', str(work), 'push', 'origin', *refspecs],
                           env=env, text=True, capture_output=True)
        calls = len(log.read_text().splitlines()) if log.exists() else 0
        return p, calls

    def remote_refs(self):
        return self.run_git('--git-dir', str(self.remote), 'for-each-ref', '--format=%(refname)')

    # pre-push-ref-only-skip: deletions and tag pushes verify nothing new, so they skip the checks.
    def test_branch_deletion_skips_checks(self):
        work = self.prepare()
        p, calls = self.push_refs(work, 'HEAD:refs/heads/done')
        self.assertEqual((p.returncode, calls), (0, 3), p.stdout + p.stderr)
        p, calls = self.push_refs(work, '--delete', 'done')
        self.assertEqual((p.returncode, calls), (0, 0), p.stdout + p.stderr)
        self.assertNotIn('refs/heads/done', self.remote_refs())
        self.assertIn('跳过', p.stderr + p.stdout)

    def test_tag_only_push_skips_checks(self):
        work = self.prepare()
        self.run_git('-C', str(work), 'tag', '-a', 'v9.9.9', '-m', 'fixture tag')
        p, calls = self.push_refs(work, 'refs/tags/v9.9.9')
        self.assertEqual((p.returncode, calls), (0, 0), p.stdout + p.stderr)
        self.assertIn('refs/tags/v9.9.9', self.remote_refs())
        self.assertIn('跳过', p.stderr + p.stdout)

    def test_branch_with_tag_runs_checks(self):
        work = self.prepare()
        self.run_git('-C', str(work), 'tag', 'v9.9.8')
        p, calls = self.push_refs(work, 'HEAD:refs/heads/mixed', 'refs/tags/v9.9.8')
        self.assertEqual((p.returncode, calls), (0, 3), p.stdout + p.stderr)
        self.assertIn('refs/heads/mixed', self.remote_refs())

    def test_empty_ref_list_runs_checks(self):
        # git does not call the hook with nothing to push, so run the installed hook directly.
        work = self.prepare()
        hook = self.run_git('-C', str(work), 'rev-parse', '--git-path', 'hooks/pre-push')
        log = self.root / 'calls'
        scratch = Path(tempfile.mkdtemp(dir=self.root))
        env = dict(self.env, SG_PROBE_LOG=str(log), SG_SCRATCH=str(scratch), SG_FAIL='')
        p = subprocess.run(['/bin/bash', str(work / hook), 'origin', str(self.remote)], cwd=work, env=env,
                           stdin=subprocess.DEVNULL, text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(len(log.read_text().splitlines()), 3)

    # local-check-dedup: commits whose trees verify-and-commit already checked skip the checks.
    def commit(self, work, rel, text, message):
        path = work / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        self.run_git('-C', str(work), 'add', rel)
        self.run_git('-C', str(work), 'commit', '-q', '-m', message)
        return self.run_git('-C', str(work), 'rev-parse', 'HEAD')

    def record(self, commit, tier):
        tree = self.run_git('-C', str(self.repo), 'rev-parse', commit + '^{tree}')
        path = self.repo / '.git/spec-guard/verified-trees'
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a') as handle:
            handle.write('%s %s\n' % (tree, tier))

    def assert_skipped(self, p, calls):
        self.assertEqual((p.returncode, calls), (0, 0), p.stdout + p.stderr)
        self.assertIn('跳过', p.stdout + p.stderr)

    def assert_full(self, p, calls):
        self.assertEqual((p.returncode, calls), (0, 3), p.stdout + p.stderr)

    def test_fully_recorded_commit_skips(self):
        work = self.prepare()
        self.record('HEAD', 'full')  # the never-pushed fixture commit is part of the push too
        c = self.commit(work, 'scripts/tool.sh', 'echo 1\n', 'tool')
        self.record(c, 'full')
        p, calls = self.push_refs(work, 'HEAD:refs/heads/rec')
        self.assert_skipped(p, calls)
        self.assertIn('refs/heads/rec', self.remote_refs())

    def test_quick_commit_on_a_recorded_parent_skips(self):
        work = self.prepare()
        self.record('HEAD', 'full')
        a = self.commit(work, 'scripts/tool.sh', 'echo 1\n', 'tool')
        self.record(a, 'full')
        b = self.commit(work, 'docs/guide.md', 'guide\n', 'docs')
        self.record(b, 'quick')
        p, calls = self.push_refs(work, 'HEAD:refs/heads/rec')
        self.assert_skipped(p, calls)

    def test_quick_commit_on_a_pushed_parent_skips(self):
        work = self.prepare()
        p, calls = self.push_refs(work, 'HEAD:refs/heads/rec')
        self.assert_full(p, calls)
        b = self.commit(work, 'docs/guide.md', 'guide\n', 'docs')
        self.record(b, 'quick')
        p, calls = self.push_refs(work, 'HEAD:refs/heads/rec')
        self.assert_skipped(p, calls)

    def test_unmatched_records_run_the_checks(self):
        cases = ['no-file', 'unrecorded', 'quick-outside-docs', 'quick-parent-unrecorded', 'dirty', 'quick-merge']
        for case in cases:
            with self.subTest(case=case):
                t = PrePushEnvironmentTests()
                t.setUp()
                try:
                    work = t.prepare()
                    if case != 'no-file':
                        # Record the never-pushed fixture commit, so only this case's condition can force the run.
                        t.record('HEAD', 'full')
                    if case == 'no-file':
                        t.commit(work, 'docs/a.md', 'a\n', 'a')
                    elif case == 'unrecorded':
                        t.record(t.commit(work, 'docs/a.md', 'a\n', 'a'), 'full')
                        t.commit(work, 'docs/b.md', 'b\n', 'b')
                    elif case == 'quick-outside-docs':
                        t.record(t.commit(work, 'docs/a.md', 'a\n', 'a'), 'full')
                        t.record(t.commit(work, 'scripts/x.sh', 'x\n', 'x'), 'quick')
                    elif case == 'quick-parent-unrecorded':
                        t.commit(work, 'scripts/x.sh', 'x\n', 'x')
                        t.record(t.commit(work, 'docs/a.md', 'a\n', 'a'), 'quick')
                    elif case == 'dirty':
                        c = t.commit(work, 'docs/a.md', 'a\n', 'a')
                        t.record(c, 'full')
                        (work / 'docs/a.md').write_text('changed\n')
                    elif case == 'quick-merge':
                        base = t.run_git('-C', str(work), 'rev-parse', 'HEAD')
                        t.record(t.commit(work, 'docs/a.md', 'a\n', 'a'), 'full')
                        t.run_git('-C', str(work), 'checkout', '-q', '-b', 'side', base)
                        t.record(t.commit(work, 'docs/b.md', 'b\n', 'b'), 'full')
                        t.run_git('-C', str(work), 'checkout', '-q', 'main')
                        t.run_git('-C', str(work), 'merge', '-q', '--no-edit', 'side')
                        t.record(t.run_git('-C', str(work), 'rev-parse', 'HEAD'), 'quick')
                    p, calls = t.push_refs(work, 'HEAD:refs/heads/rec')
                    t.assert_full(p, calls)
                finally:
                    t.doCleanups()

    def test_unrecorded_failure_still_blocks(self):
        work = self.prepare()
        self.commit(work, 'docs/a.md', 'a\n', 'a')
        log = self.root / 'calls'
        scratch = Path(tempfile.mkdtemp(dir=self.root))
        env = dict(self.env, SG_PROBE_LOG=str(log), SG_SCRATCH=str(scratch), SG_FAIL='validate.sh')
        p = subprocess.run(['git', '-C', str(work), 'push', 'origin', 'HEAD:refs/heads/rec'],
                           env=env, text=True, capture_output=True)
        self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertNotIn('refs/heads/rec', self.remote_refs())

    def test_regular_checkout_preserves_config(self):
        self.push()

    def test_linked_worktree_preserves_common_config(self):
        self.push(linked=True)

    def test_each_failed_check_blocks_push(self):
        # Each subtest owns its repositories, including failed-push state.
        for failure in ['validate.sh', 'test-phase-guard.sh', 'test-verify-artifacts.sh']:
            with self.subTest(failure=failure):
                case = PrePushEnvironmentTests()
                case.setUp()
                try:
                    case.push(linked=True, failure=failure)
                finally:
                    case.doCleanups()


if __name__ == '__main__':
    unittest.main()

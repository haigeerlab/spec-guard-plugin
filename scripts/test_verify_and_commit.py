"""verify-and-commit.sh commits only after every selected suite passes (stub suites, temp repos)."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().with_name('verify-and-commit.sh')
SUITES = {
    'validate': 'scripts/validate.sh',
    'phase-guard': 'plugins/spec-guard/hooks/test-phase-guard.sh',
    'verify-artifacts': 'plugins/spec-guard/hooks/test-verify-artifacts.sh',
    'setup-teardown': 'plugins/spec-guard/hooks/test-setup-teardown.sh',
    'pre-push': 'scripts/test_pre_push_environment.py',
}
# Every stub prints a success-looking last line even when it fails: a check that
# reads the output instead of the exit code would be fooled.
STUB = '''#!/bin/bash
printf '%s\\n' "{name}" >> "$SG_CALLS"
for i in 1 2 3; do echo "noise $i"; done
case ",$SG_FAIL," in *,{name},*) echo "  ❌ {name} broke"; echo "校验通过 ✅"; exit 1 ;; esac
echo "{name} passed"
'''
PY_STUB = '''import os, sys
open(os.environ["SG_CALLS"], "a").write("{name}\\n")
print("noise")
if "{name}" in os.environ.get("SG_FAIL", "").split(","):
    print("  ❌ {name} broke"); print("OK"); sys.exit(1)
print("{name} passed")
'''
NPX_STUB = '''#!/bin/bash
printf 'shellcheck\\n' >> "$SG_CALLS"
[ -n "${SG_NO_NPX:-}" ] && { echo "npx: command not found" >&2; exit 127; }
case ",$SG_FAIL," in *,shellcheck,*) echo "SC2034 warning"; exit 1 ;; esac
exit 0
'''


class VerifyAndCommitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='sg-verify-commit-')
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.repo = root / 'repo'
        self.calls = root / 'calls'
        bin_dir = root / 'bin'
        bin_dir.mkdir()
        (bin_dir / 'npx').write_text(NPX_STUB)
        (bin_dir / 'npx').chmod(0o755)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        self.env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, SG_CALLS=str(self.calls),
                        SG_FAIL='', PATH=str(bin_dir) + os.pathsep + os.environ['PATH'])
        self.git('init', '-q', '-b', 'main', str(self.repo))
        self.git('config', 'user.name', 'Fixture Owner')
        self.git('config', 'user.email', 'owner@example.invalid')
        (self.repo / 'scripts').mkdir()
        shutil.copy2(SCRIPT, self.repo / 'scripts/verify-and-commit.sh')
        for name, rel in SUITES.items():
            p = self.repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text((PY_STUB if rel.endswith('.py') else STUB).replace('{name}', name))
        for rel in ['plugins/spec-guard/hooks/managed-block.py', 'scripts/install-git-hooks.sh', 'notes.txt']:
            (self.repo / rel).write_text('v1\n')
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'fixture')

    def git(self, *args):
        cwd = None if args[0] == 'init' else self.repo
        return subprocess.run(['git', *args], cwd=cwd, env=self.env, text=True,
                              capture_output=True, check=True).stdout.strip()

    def commits(self):
        return int(self.git('rev-list', '--count', 'HEAD'))

    def stage(self, rel, text='v2\n'):
        (self.repo / rel).write_text(text)
        self.git('add', rel)

    def run_script(self, *args, **env):
        if self.calls.exists():
            self.calls.unlink()
        p = subprocess.run(['/bin/bash', 'scripts/verify-and-commit.sh', *args], cwd=self.repo,
                           env=dict(self.env, **env), text=True, capture_output=True)
        called = self.calls.read_text().split() if self.calls.exists() else []
        return p, called

    def test_all_pass_commits_the_staged_content(self):
        self.stage('notes.txt')
        before = self.commits()
        p, called = self.run_script('--', '-q', '-m', 'change notes')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(called, ['validate', 'phase-guard', 'verify-artifacts'])
        self.assertEqual(self.commits(), before + 1)
        self.assertEqual(self.git('log', '-1', '--format=%s'), 'change notes')
        self.assertEqual(self.git('show', '--name-only', '--format=', 'HEAD'), 'notes.txt')

    def test_any_failed_suite_blocks_the_commit(self):
        for failing in ['validate', 'phase-guard', 'verify-artifacts']:
            with self.subTest(failing=failing):
                self.stage('notes.txt', 'v-%s\n' % failing)
                before = self.commits()
                p, called = self.run_script('--', '-q', '-m', 'should not land', SG_FAIL=failing)
                self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
                self.assertEqual(self.commits(), before)
                self.assertIn(failing, p.stdout + p.stderr)
                self.assertIn('.log', p.stdout + p.stderr)
                self.assertIn('notes.txt', self.git('diff', '--cached', '--name-only'))

    def test_success_looking_output_does_not_hide_a_failure(self):
        # The failing stub's last line is "校验通过 ✅"; only its exit code may decide.
        self.stage('notes.txt')
        before = self.commits()
        p, _ = self.run_script('--', '-q', '-m', 'should not land', SG_FAIL='validate')
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(self.commits(), before)

    def test_refuses_unstaged_tracked_changes(self):
        self.stage('notes.txt')
        (self.repo / 'scripts/install-git-hooks.sh').write_text('unstaged\n')
        before = self.commits()
        p, called = self.run_script('--', '-q', '-m', 'x')
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertEqual((self.commits(), called), (before, []))

    def test_refuses_when_nothing_is_staged(self):
        p, called = self.run_script('--', '-q', '-m', 'x')
        self.assertEqual((p.returncode, called), (1, []), p.stdout + p.stderr)

    def test_usage_errors_exit_2(self):
        self.stage('notes.txt')
        for args in [('-q', '-m', 'no separator'), ('--suite', 'nope', '--', '-q', '-m', 'x')]:
            with self.subTest(args=args):
                before = self.commits()
                p, called = self.run_script(*args)
                self.assertEqual((p.returncode, called, self.commits()), (2, [], before), p.stdout + p.stderr)

    def test_staged_paths_select_extra_suites(self):
        self.stage('plugins/spec-guard/hooks/managed-block.py')
        p, called = self.run_script('--', '-q', '-m', 'block')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(called, ['validate', 'phase-guard', 'verify-artifacts', 'setup-teardown'])
        self.stage('scripts/install-git-hooks.sh')
        p, called = self.run_script('--', '-q', '-m', 'hook')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(called, ['validate', 'phase-guard', 'verify-artifacts', 'pre-push', 'shellcheck'])
        self.assertIn('✅ shellcheck —— 无告警', p.stdout)

    def test_manual_suite_runs_and_can_block(self):
        self.stage('notes.txt')
        before = self.commits()
        p, called = self.run_script('--suite', 'setup-teardown', '--', '-q', '-m', 'x', SG_FAIL='setup-teardown')
        self.assertIn('setup-teardown', called)
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(self.commits(), before)

    def test_unavailable_shellcheck_is_a_failure(self):
        self.stage('scripts/install-git-hooks.sh')
        before = self.commits()
        p, called = self.run_script('--', '-q', '-m', 'x', SG_NO_NPX='1')
        self.assertIn('shellcheck', called)
        self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(self.commits(), before)


if __name__ == '__main__':
    unittest.main()

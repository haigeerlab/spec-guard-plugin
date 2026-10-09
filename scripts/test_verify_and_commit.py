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
    'repo-artifacts': 'plugins/spec-guard/hooks/verify-artifacts.sh',
}
FULL = {'validate', 'phase-guard', 'verify-artifacts', 'repo-artifacts'}
QUICK = {'validate-quick', 'verify-artifacts', 'repo-artifacts'}
# Every stub prints a success-looking last line even when it fails: a check that
# reads the output instead of the exit code would be fooled.
STUB = '''#!/bin/bash
n="{name}"; [ "${1:-}" = --quick ] && n="$n-quick"
printf '%s\\n' "$n" >> "$SG_CALLS"
for i in 1 2 3; do echo "noise $i"; done
case ",$SG_FAIL," in *,"$n",*) echo "  ❌ $n broke"; echo "校验通过 ✅"; exit 1 ;; esac
echo "$n passed"
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
        shutil.copy2(SCRIPT.with_name('verified_trees.py'), self.repo / 'scripts/verified_trees.py')
        (self.repo / '.gitignore').write_text('.agent/state.json\n')
        for rel in ['docs/guide.md', 'spec/a.md', 'README.md', 'plugins/spec-guard/commands/x.md']:
            (self.repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / rel).write_text('v1\n')
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
        called = set(self.calls.read_text().split()) if self.calls.exists() else set()
        return p, called

    def records(self):
        path = self.repo / '.git/spec-guard/verified-trees'
        return path.read_text().split('\n') if path.exists() else []

    def head_tree(self):
        return self.git('rev-parse', 'HEAD^{tree}')

    def test_all_pass_commits_the_staged_content(self):
        self.stage('notes.txt')
        before = self.commits()
        p, called = self.run_script('--', '-q', '-m', 'change notes')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(called, FULL)
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
        self.assertEqual((self.commits(), called), (before, set()))

    def test_refuses_when_nothing_is_staged(self):
        p, called = self.run_script('--', '-q', '-m', 'x')
        self.assertEqual((p.returncode, called), (1, set()), p.stdout + p.stderr)

    def test_usage_errors_exit_2(self):
        self.stage('notes.txt')
        for args in [('-q', '-m', 'no separator'), ('--suite', 'nope', '--', '-q', '-m', 'x')]:
            with self.subTest(args=args):
                before = self.commits()
                p, called = self.run_script(*args)
                self.assertEqual((p.returncode, called, self.commits()), (2, set(), before), p.stdout + p.stderr)

    def test_staged_paths_no_longer_add_suites_validate_already_runs(self):
        # validate.sh already runs the setup/teardown and pre-push regressions.
        self.stage('plugins/spec-guard/hooks/managed-block.py')
        p, called = self.run_script('--', '-q', '-m', 'block')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(called, FULL)
        self.stage('scripts/install-git-hooks.sh')
        p, called = self.run_script('--', '-q', '-m', 'hook')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(called, FULL | {'shellcheck'})
        self.assertRegex(p.stdout, r'✅ shellcheck（\d+s）—— 无告警')

    def test_docs_only_commit_runs_the_quick_tier(self):
        for rel in ['docs/guide.md', 'spec/a.md', 'README.md']:
            with self.subTest(rel=rel):
                self.stage(rel, 'v-%s\n' % rel)
                p, called = self.run_script('--', '-q', '-m', 'docs')
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                self.assertEqual(called, QUICK)
                self.assertIn('快档', p.stdout)
                self.assertIn(self.head_tree() + ' quick', self.records())

    def test_paths_outside_the_quick_set_run_everything(self):
        for rel in ['plugins/spec-guard/commands/x.md', 'notes.txt']:
            with self.subTest(rel=rel):
                self.stage(rel, 'v-%s\n' % rel)
                self.stage('docs/guide.md', 'v-mixed-%s\n' % rel)
                p, called = self.run_script('--', '-q', '-m', 'mixed')
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                self.assertEqual(called, FULL)
                self.assertIn(self.head_tree() + ' full', self.records())

    def test_tier_classifier(self):
        quick = ['spec/x.md', 'tasks/m/plan.md', 'docs/releases/v1-source.json', 'README.md', 'CHANGELOG.md']
        # evals/ markdown is eval input, not documentation
        full = ['plugins/spec-guard/commands/x.md', '.github/ISSUE_TEMPLATE/bug.md', 'evals/dispatch-cost/task.md',
                'scripts/a.sh',
                'scripts/readme.txt', '.gitignore', 'spec', 'docsx/a.md.txt']
        tool = SCRIPT.with_name('verified_trees.py')
        def tier(paths):
            return subprocess.run(['python3', str(tool), 'tier'], input='\n'.join(paths), text=True,
                                  capture_output=True, check=True).stdout.strip()
        for path in quick:
            self.assertEqual(tier([path]), 'quick', path)
        for path in full:
            self.assertEqual(tier([path]), 'full', path)
        self.assertEqual(tier(quick + full[:1]), 'full')
        self.assertEqual(tier([]), 'full')

    def test_partial_commit_writes_no_record(self):
        # `-- -m x <path>` commits only part of what was checked: HEAD's tree is not the verified tree.
        self.stage('notes.txt')
        self.stage('docs/guide.md', 'v-partial\n')
        p, _ = self.run_script('--', '-q', '-m', 'partial', 'notes.txt')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(self.git('show', '--name-only', '--format=', 'HEAD'), 'notes.txt')
        self.assertEqual([r for r in self.records() if r], [])
        self.assertIn('未写入检查记录', p.stdout)

    def test_failed_run_writes_no_record(self):
        self.stage('notes.txt')
        self.run_script('--', '-q', '-m', 'x', SG_FAIL='phase-guard')
        self.assertEqual([r for r in self.records() if r], [])

    def test_untracked_files_skip_the_record_but_not_the_commit(self):
        self.stage('notes.txt')
        (self.repo / 'forgotten.py').write_text('print(1)\n')
        before = self.commits()
        p, _ = self.run_script('--', '-q', '-m', 'x')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(self.commits(), before + 1)
        self.assertEqual([r for r in self.records() if r], [])
        self.assertIn('未写入检查记录：工作区有未跟踪文件（见上方警告）', p.stdout)
        # listed once, in the warning before the checks; the post-commit note points back to it
        self.assertEqual(p.stdout.count('forgotten.py'), 1, p.stdout)

    def test_ignored_state_file_does_not_block_the_record(self):
        (self.repo / '.agent').mkdir()
        (self.repo / '.agent/state.json').write_text('{"activeModule":"m"}\n')
        self.stage('notes.txt')
        p, _ = self.run_script('--', '-q', '-m', 'x')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn(self.head_tree() + ' full', self.records())

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

    def test_untracked_files_are_warned_about_before_the_checks(self):
        self.stage('notes.txt')
        (self.repo / 'forgotten.py').write_text('print(1)\n')
        before = self.commits()
        p, _ = self.run_script('--', '-q', '-m', 'x')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(self.commits(), before + 1)
        header = p.stdout.index('── verify-and-commit:')
        warning = p.stdout.find('⚠️  工作区有 1 个未跟踪文件')
        self.assertTrue(0 <= warning < header, p.stdout)
        self.assertTrue(0 <= p.stdout.find('forgotten.py') < header, p.stdout)
        self.assertIn('git add', p.stdout[warning:header])

    def test_no_warning_without_untracked_or_with_only_ignored_files(self):
        (self.repo / '.agent').mkdir()
        (self.repo / '.agent/state.json').write_text('{"activeModule":"m"}\n')
        self.stage('notes.txt')
        p, _ = self.run_script('--', '-q', '-m', 'x')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertNotIn('未跟踪文件', p.stdout + p.stderr)

    def test_warning_still_shows_when_a_check_fails(self):
        self.stage('notes.txt')
        (self.repo / 'forgotten.py').write_text('print(1)\n')
        before = self.commits()
        p, _ = self.run_script('--', '-q', '-m', 'x', SG_FAIL='validate')
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertEqual(self.commits(), before)
        self.assertIn('⚠️  工作区有 1 个未跟踪文件', p.stdout)

    def test_long_untracked_list_is_truncated(self):
        self.stage('notes.txt')
        names = ['new-%02d.txt' % i for i in range(12)]
        for name in names:
            (self.repo / name).write_text('x\n')
        p, _ = self.run_script('--', '-q', '-m', 'x')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn('⚠️  工作区有 12 个未跟踪文件', p.stdout)
        listed = [n for n in names if n in p.stdout]
        self.assertEqual(listed, names[:10], p.stdout)
        self.assertIn('… 另有 2 个', p.stdout)


if __name__ == '__main__':
    unittest.main()

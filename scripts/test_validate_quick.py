"""validate.sh --quick runs only the structural checks, still blocks a structural error, and leaves the full run alone."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
QUICK_SECTIONS = ['结构', 'JSON 语法', 'marketplace ↔ Claude / Codex plugin 一致性', '公开安装元数据', 'Shell 语法',
                  '可执行位', 'bash 3.2 兼容', 'gh --json 字段', '管道 + grep -q', '用户可见输出里的命令名',
                  '指纹算法自检', '本机状态路径', '发布证据记录回归', 'README 内嵌声明块', '命令 frontmatter']
FULL_ONLY_SECTIONS = ['校验器自身的回归', 'Proposal 与本地结构回归', 'Capability history', 'Python 3.9 兼容',
                      'Hook 入口命令回归', 'Setup/teardown regression', 'History verification',
                      'History migration', 'Codex 真实宿主 smoke 判决器自检']


def headers(output):
    return [line.strip('═ ').strip() for line in output.splitlines() if line.startswith('═══')]


def has(found, name):
    return any(h.startswith(name) for h in found)


class ValidateQuickTests(unittest.TestCase):
    def run_validate(self, root, *args):
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        return subprocess.run(['/bin/bash', str(root / 'scripts/validate.sh'), *args], cwd=root, env=env,
                              text=True, capture_output=True)

    def test_quick_runs_only_structural_sections(self):
        p = self.run_validate(ROOT, '--quick')
        self.assertEqual(p.returncode, 0, p.stdout[-2000:] + p.stderr)
        found = headers(p.stdout)
        for name in QUICK_SECTIONS:
            self.assertTrue(has(found, name), name)
        for name in FULL_ONLY_SECTIONS:
            self.assertFalse(has(found, name), name)
        self.assertIn('校验通过', p.stdout)

    def test_quick_still_blocks_a_structural_error(self):
        with tempfile.TemporaryDirectory(prefix='sg-validate-quick-') as tmp:
            copy = Path(tmp) / 'repo'
            archive = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '-z'], capture_output=True, check=True)
            copy.mkdir()
            subprocess.run(['tar', '-C', str(ROOT), '--null', '-T', '-', '-cf', str(Path(tmp) / 'a.tar')],
                           input=archive.stdout, check=True, capture_output=True)
            subprocess.run(['tar', '-C', str(copy), '-xf', str(Path(tmp) / 'a.tar')], check=True)
            env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
            for cmd in (['init', '-q'], ['add', '-A']):
                subprocess.run(['git', '-C', str(copy), *cmd], env=env, check=True, capture_output=True)
            (copy / '.claude-plugin/marketplace.json').write_text('{ not json\n')
            p = self.run_validate(copy, '--quick')
            self.assertNotEqual(p.returncode, 0, p.stdout[-2000:])
            self.assertIn('校验失败', p.stdout)

    def test_unknown_argument_is_a_usage_error(self):
        p = self.run_validate(ROOT, '--nope')
        self.assertEqual(p.returncode, 2, p.stdout[-500:] + p.stderr)

    def test_full_run_keeps_every_section(self):
        # Read the script instead of running the slow full validate: every full-only section stays reachable.
        text = (ROOT / 'scripts/validate.sh').read_text()
        for name in FULL_ONLY_SECTIONS + QUICK_SECTIONS:
            self.assertIn('═══ ' + name, text, name)


if __name__ == '__main__':
    unittest.main()

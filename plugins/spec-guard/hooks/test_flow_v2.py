"""flow-doc-skeletons: the flow v2 marker, its tier, and the stages of a v2 module.  No network."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import module_stage  # noqa: E402
from module_stage import DOC_SECTIONS, effective_tier, flow_marker, module_state  # noqa: E402

SKELETONS = HERE.parent / "references" / "doc-skeletons.md"


def marker(tier):
    return "<!-- spec-guard: flow v2 tier=%s -->" % tier


def requirement(tier="normal", boundary="`src/a/`", shared=None, extra=""):
    text = "# a\n\n<!-- spec-guard: review approved -->\n%s\n\n" % marker(tier)
    text += "".join("## %s\n\n不涉及\n\n" % name for name in DOC_SECTIONS["requirement"]["zh"])
    text += extra
    if boundary:
        text += "## 并行边界\n\n- 独占：%s\n%s" % (boundary, "- 公共：%s\n" % shared if shared else "")
    return text


class Project:
    def __init__(self, ids=("a",)):
        self.ids = ids

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "spec").mkdir()
        rows = "".join("| %s | x | — |\n" % module for module in self.ids)
        (self.root / "spec" / "CAPABILITY-MAP.md").write_text(
            "# Capability Map: t\n\n| Module id | Responsibility | Depends on |\n|---|---|---|\n%s\nBuild order: %s\n"
            % (rows, " → ".join(self.ids)), encoding="utf-8")
        return self

    def __exit__(self, *exc):
        self.tmp.cleanup()

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class SkeletonTest(unittest.TestCase):
    def test_every_section_is_in_the_reference_in_both_languages(self):
        text = SKELETONS.read_text(encoding="utf-8")
        for doc, names in DOC_SECTIONS.items():
            self.assertEqual(len(names["zh"]), len(names["en"]), doc)
            for zh, en in zip(names["zh"], names["en"]):
                with self.subTest(doc=doc, section=zh):
                    self.assertIn("| %s | %s |" % (zh, en), text)


class MarkerTest(unittest.TestCase):
    def marker(self, spec):
        with Project() as project:
            if spec is not None:
                project.write("spec/a.md", spec)
            return flow_marker(project.root, "a")

    def test_no_marker_or_no_file_is_the_old_flow(self):
        self.assertEqual(self.marker("# a\n\nbody\n"), {"v2": False, "tier": None, "problems": []})
        self.assertEqual(self.marker(None), {"v2": False, "tier": None, "problems": []})

    def test_four_tiers(self):
        for tier in ("bug", "small", "normal", "important"):
            with self.subTest(tier=tier):
                self.assertEqual(self.marker("# a\n\n%s\n" % marker(tier)), {"v2": True, "tier": tier, "problems": []})

    def test_invalid_tier_reads_as_normal(self):
        self.assertEqual(self.marker("# a\n\n%s\n" % marker("huge")),
                         {"v2": True, "tier": "normal", "problems": ["tier-invalid"]})

    def test_fenced_marker_does_not_count(self):
        self.assertEqual(self.marker("# a\n\n```\n%s\n```\n" % marker("bug"))["v2"], False)


class EffectiveTierTest(unittest.TestCase):
    def test_rule_lifts_a_lower_tier_to_important(self):
        with Project() as project:
            project.write("spec/a.md", requirement("small", shared="全局配置"))
            self.assertEqual(effective_tier(project.root, "a"),
                             {"v2": True, "tier": "important", "problems": ["tier-below-rule"]})

    def test_ordinary_module_keeps_its_tier(self):
        with Project() as project:
            project.write("spec/a.md", requirement("small"))
            self.assertEqual(effective_tier(project.root, "a"), {"v2": True, "tier": "small", "problems": []})

    def test_old_module_has_no_tier(self):
        with Project() as project:
            project.write("spec/a.md", "# a\n")
            self.assertEqual(effective_tier(project.root, "a"), {"v2": False, "tier": None, "problems": []})


if __name__ == "__main__":
    unittest.main()

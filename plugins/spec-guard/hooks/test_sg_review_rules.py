"""sg-review-rules (autopilot module 5): one review round before the requirement is confirmed, designs reviewed only
on three high-risk reasons, the design approver from the takeover alone, and flow v2 important requirements decided
by risk paths only.  No network; every project is a temporary git repository."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from module_stage import important  # noqa: E402
import test_important_requirement as tir  # noqa: E402

_spec = tir._spec

V2 = "<!-- spec-guard: flow v2 tier=normal -->\n"


class ImportantV2(unittest.TestCase):
    """R11: a flow v2 module is important only on a risk path; an old module keeps all five rules."""
    git, config, risk, insert = tir.Important.git, tir.Important.config, tir.Important.risk, tir.Important.insert

    def setUp(self):
        tir.Important.setUp(self)
        self.config({})

    def test_v2_ignores_multi_and_cross_module(self):
        self.insert("alpha", "beta", specs={"alpha": V2 + _spec(shared="锁文件"), "beta": V2 + _spec()})
        self.assertEqual(important(self.root, "alpha"), [])
        self.insert("gamma", specs={"gamma": V2 + _spec("`src/a/x.py`")})
        self.assertEqual(important(self.root, "gamma"), [])

    def test_v2_risk_path_still_counts(self):
        self.insert("alpha", "beta", specs={"alpha": V2 + _spec("`.github/workflows/`"), "beta": V2 + _spec()})
        self.assertEqual(important(self.root, "alpha"), ["risk-path"])

    def test_old_flow_unchanged(self):
        self.insert("alpha", "beta", specs={"alpha": _spec(shared="锁文件"), "beta": _spec("`.github/x`")})
        self.assertEqual(important(self.root, "alpha"), ["multi-module", "cross-module"])
        self.assertEqual(important(self.root, "beta"), ["multi-module", "risk-path"])


if __name__ == "__main__":
    unittest.main()

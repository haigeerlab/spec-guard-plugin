"""Read-only transport selection must not split one session across mailboxes."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from collaboration_backend import selected_backend
from native_collaboration_runtime import BRIDGE_COMMIT


class CollaborationBackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sg-backend-")
        self.addCleanup(self.tmp.cleanup)
        self.marker = Path(self.tmp.name) / "transport.json"
        self.root = Path(self.tmp.name) / "native"

    def test_missing_marker_keeps_current_xats_without_writing(self):
        self.assertEqual(selected_backend(self.marker, self.root), {"backend": "xats"})
        self.assertFalse(self.marker.exists())

    def test_native_marker_selects_only_ready_native_runtime(self):
        self.marker.write_text(json.dumps({"backend": "native", "commit": BRIDGE_COMMIT}))
        self.marker.chmod(0o600)
        with patch("collaboration_backend.native_status", return_value={"state": "ready"}):
            self.assertEqual(selected_backend(self.marker, self.root), {"backend": "native"})
        with patch("collaboration_backend.native_status", return_value={"state": "absent"}):
            self.assertEqual(selected_backend(self.marker, self.root)["backend"], "unavailable")

    def test_invalid_or_symlinked_marker_never_falls_back_to_xats(self):
        self.marker.write_text("not JSON")
        self.marker.chmod(0o600)
        self.assertEqual(selected_backend(self.marker, self.root)["backend"], "invalid")
        self.marker.unlink()
        self.marker.symlink_to(Path(self.tmp.name) / "other")
        self.assertEqual(selected_backend(self.marker, self.root)["backend"], "invalid")


if __name__ == "__main__":
    unittest.main()

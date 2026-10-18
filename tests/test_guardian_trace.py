"""Isolated hash-chain journal tests. No secrets, network or Codex usage."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.guardian_trace import TraceError, append, init, verify


class TraceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "journal.jsonl"

    def test_init_append_verify(self):
        self.assertEqual(init(self.path)["events"], 1)
        result = append(self.path, "verification", {"tests": 4, "status": "reported"})
        self.assertEqual(result["events"], 2)
        self.assertFalse(result["authenticated"])

    def test_no_overwrite(self):
        init(self.path)
        with self.assertRaises(TraceError):
            init(self.path)

    def test_tamper_detected(self):
        init(self.path)
        append(self.path, "finish", {"outcome": "planned"})
        content = self.path.read_text(encoding="utf-8").replace("planned", "faked")
        self.path.write_text(content, encoding="utf-8")
        with self.assertRaises(TraceError):
            verify(self.path)

    def test_secret_keys_and_values_rejected(self):
        init(self.path)
        for data in ({"api_key": "123"}, {"comment": "Bearer aaa.bbb.ccc"}, {"nested": {"password": "foo"}}):
            with self.assertRaises(TraceError):
                append(self.path, "verification", data)
        self.assertEqual(verify(self.path)["events"], 1)

    def test_unknown_event_rejected(self):
        init(self.path)
        with self.assertRaises(TraceError):
            append(self.path, "deploy", {"status": "done"})

    def test_partial_event_rejected(self):
        init(self.path)
        with self.path.open("a", encoding="utf-8") as file:
            file.write('{"sequence": 1}')
        with self.assertRaises(TraceError):
            verify(self.path)


if __name__ == "__main__":
    unittest.main()

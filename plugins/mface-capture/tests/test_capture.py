import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CAPTURE_MODULE = PROJECT_ROOT / "capture.py"


def load_capture_module():
    spec = importlib.util.spec_from_file_location("mface_capture", CAPTURE_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MFaceCaptureTest(unittest.TestCase):
    def test_extracts_mface_and_image_without_text_or_sender_fields(self):
        capture = load_capture_module()
        raw_message = {
            "user_id": 123456,
            "group_id": 888888,
            "message": [
                {"type": "text", "data": {"text": "private text"}},
                {
                    "type": "mface",
                    "data": {
                        "emoji_id": "1001",
                        "emoji_package_id": "pkg",
                        "key": "abc",
                        "summary": "[happy]",
                        "url": "https://example.test/a.png?token=secret",
                    },
                },
                {
                    "type": "image",
                    "data": {
                        "file": "abc.gif",
                        "url": "https://gchat.qpic.cn/path/file.gif?auth=secret",
                        "summary": "[animated]",
                    },
                },
            ],
        }

        records = capture.collect_records(raw_message, message_type="group")

        self.assertEqual([r["segment_type"] for r in records], ["mface", "image"])
        encoded = json.dumps(records, ensure_ascii=False)
        self.assertNotIn("private text", encoded)
        self.assertNotIn("123456", encoded)
        self.assertNotIn("888888", encoded)
        self.assertNotIn("token=secret", encoded)
        self.assertNotIn("auth=secret", encoded)
        self.assertIn("url_host", records[0]["data"])
        self.assertIn("url_path_tail", records[1]["data"])

    def test_collect_records_can_attach_label(self):
        capture = load_capture_module()
        raw_message = {
            "message": [
                {
                    "type": "image",
                    "data": {"file": "angry.gif", "summary": "[angry]"},
                }
            ]
        }

        records = capture.collect_records(raw_message, message_type="friend", label="生气")

        self.assertEqual(records[0]["label"], "生气")

    def test_build_download_jobs_uses_label_and_safe_filename(self):
        capture = load_capture_module()
        raw_message = {
            "message": [
                {
                    "type": "image",
                    "data": {
                        "file": "bad/name.gif",
                        "url": "https://gchat.qpic.cn/path/file.gif?auth=secret",
                    },
                }
            ]
        }
        records = capture.collect_records(raw_message, message_type="friend", label="疑惑")

        jobs = capture.build_download_jobs(raw_message, records, label="疑惑")

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["url"], "https://gchat.qpic.cn/path/file.gif?auth=secret")
        self.assertTrue(jobs[0]["relative_path"].startswith("images/疑惑/"))
        self.assertTrue(jobs[0]["relative_path"].endswith(".gif"))
        self.assertNotIn("auth=secret", jobs[0]["relative_path"])

    def test_append_jsonl_creates_local_file(self):
        capture = load_capture_module()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "captures.jsonl"
            records = [
                {
                    "segment_type": "mface",
                    "message_type": "friend",
                    "data": {"emoji_id": "1001"},
                }
            ]

            written = capture.append_jsonl(target, records)

            self.assertEqual(written, 1)
            lines = target.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["segment_type"], "mface")

    def test_capture_state_auto_expires(self):
        capture = load_capture_module()
        state = capture.CaptureState(enabled=False, auto_stop_seconds=120, now=1000.0)

        state.activate(now=1000.0, label="害羞")

        self.assertTrue(state.is_active(now=1001.0))
        self.assertEqual(state.label, "害羞")
        self.assertEqual(state.remaining_seconds(now=1060.2), 60)
        self.assertFalse(state.is_active(now=1120.0))
        self.assertFalse(state.enabled)
        self.assertEqual(state.label, "")

    def test_capture_state_is_bound_to_source_origin(self):
        capture = load_capture_module()
        state = capture.CaptureState(enabled=False, auto_stop_seconds=120, now=1000.0)

        state.activate(
            now=1000.0,
            label="开心",
            source_origin="aiocqhttp:FriendMessage:target-session",
        )

        self.assertTrue(
            state.is_active_for(
                now=1001.0,
                source_origin="aiocqhttp:FriendMessage:target-session",
            )
        )
        self.assertFalse(
            state.is_active_for(
                now=1001.0,
                source_origin="aiocqhttp:FriendMessage:other-session",
            )
        )

    def test_capture_state_can_be_manually_deactivated(self):
        capture = load_capture_module()
        state = capture.CaptureState(enabled=True, auto_stop_seconds=120, now=1000.0)

        state.deactivate()

        self.assertFalse(state.is_active(now=1001.0))
        self.assertEqual(state.remaining_seconds(now=1001.0), 0)

    def test_parse_capture_label_command(self):
        capture = load_capture_module()

        self.assertEqual(capture.parse_capture_label_command("/表情采集 生气"), "生气")
        self.assertEqual(capture.parse_capture_label_command(" /表情采集   shy "), "shy")
        self.assertIsNone(capture.parse_capture_label_command("/表情采集 开启"))
        self.assertIsNone(capture.parse_capture_label_command("/表情采集 状态"))
        self.assertIsNone(capture.parse_capture_label_command("普通聊天"))


if __name__ == "__main__":
    unittest.main()

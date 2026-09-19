from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from Environment.chatroom import cli as chatroom_cli
from Environment.chatroom import config
from Environment.chatroom.json_io import load_json, write_json_atomic
from Environment.chatroom.paths import ChatroomPaths
from Environment.chatroom.service import ChatroomService


def load_claude_connector_module():
    path = Path(__file__).resolve().parents[1] / "Models" / "Claude" / "scripts" / "claude_chatroom_v2.py"
    if not path.exists():
        raise unittest.SkipTest("Private host connector is intentionally excluded from this public snapshot.")
    spec = importlib.util.spec_from_file_location("claude_chatroom_connector", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load Claude connector: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ChatroomBackendTests(unittest.TestCase):
    def test_path_derivation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = ChatroomPaths(tmp)
            visible = paths.active_dir / "Parking_Lot" / "Test_Chat.json"
            self.assertEqual(paths.companion_dir(visible).name, "_Test_Chat")
            self.assertEqual(paths.messages_dir(visible).name, "messages")
            self.assertEqual(paths.state_path(visible).name, "state.json")
            self.assertEqual(paths.visible_from_state_path(paths.state_path(visible)), visible)

    def test_json_io_handles_bom_and_malformed_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            path.write_text("\ufeff{\"ok\": true}", encoding="utf-8")
            self.assertEqual(load_json(path), {"ok": True})

            write_json_atomic(path, {"value": 7})
            self.assertEqual(load_json(path), {"value": 7})

            bad = Path(tmp) / "bad.json"
            bad.write_text("{bad", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                load_json(bad)

    def test_create_post_and_compile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            created = service.create_chat("Test Chat", folder="Parking_Lot")
            state = created["state"]
            self.assertEqual(state["schema_version"], config.STATE_SCHEMA_VERSION)
            self.assertEqual(state["participants"], [])

            first = service.post_message(state["chat_id"], "Avery", "Hello")
            second = service.post_message(state["chat_id"], "Codex", "Reviewing", kind="review")

            messages = second["messages"]
            self.assertEqual([m["message_id"] for m in messages], [1, 2])
            self.assertEqual(messages[1]["kind"], "review")
            self.assertEqual(second["state"]["participants"], [])
            self.assertEqual(messages[0]["char_count"], len("Hello"))
            self.assertEqual(set(messages[0]["versions"].keys()), {str(index) for index in range(10)})
            self.assertFalse(messages[0]["version_prep"]["semantic_prepared"])

            compiled = load_json(second["visible_path"])
            self.assertEqual(compiled["schema_version"], config.COMPILED_SCHEMA_VERSION)
            self.assertEqual(compiled["last_message_id"], 2)
            self.assertIsInstance(compiled["compiled_chars"], int)

    def test_compile_policy_excludes_individual_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            chat = service.create_chat("Policy Chat")
            chat_id = chat["state"]["chat_id"]
            for index in range(1, 5):
                chat = service.post_message(chat_id, "Avery", f"Message {index}")

            service.exclude_messages(chat_id, [2, 4])
            loaded = service.load_chat(chat_id)
            raw_messages = loaded["messages"]
            compiled = load_json(loaded["visible_path"])

            self.assertEqual([m["message_id"] for m in raw_messages], [1, 2, 3, 4])
            self.assertEqual([m["message_id"] for m in compiled["messages"]], [1, 3])
            self.assertEqual(compiled["last_message_id"], 4)
            self.assertEqual(compiled["compile_policy"]["excluded_message_ids"], [2, 4])

    def test_compile_policy_standin_replaces_messages_in_compiled_view(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            chat = service.create_chat("Standin Chat")
            chat_id = chat["state"]["chat_id"]
            for index in range(1, 5):
                chat = service.post_message(chat_id, "Avery", f"Message {index}")

            service.add_standin(
                chat_id,
                [2, 3],
                "Messages 2 and 3 resolved the logging decision.",
                insert_after_message_id=3,
                standin_id="standin_logging",
            )
            loaded = service.load_chat(chat_id)
            raw_messages = loaded["messages"]
            compiled = load_json(loaded["visible_path"])
            compiled_messages = compiled["messages"]

            self.assertEqual([m["message_id"] for m in raw_messages], [1, 2, 3, 4])
            self.assertEqual(compiled_messages[0]["message_id"], 1)
            self.assertEqual(compiled_messages[1]["schema_version"], config.STANDIN_SCHEMA_VERSION)
            self.assertEqual(compiled_messages[1]["message_id"], "standin:standin_logging")
            self.assertEqual(compiled_messages[1]["replaces_message_ids"], [2, 3])
            self.assertEqual(compiled_messages[2]["message_id"], 4)
            self.assertEqual(compiled["last_message_id"], 4)

    def test_scan_and_mark_seen_only_mutates_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            chat = service.create_chat("Scan Chat", participants=["Codex"])
            chat = service.post_message(chat["state"]["chat_id"], "Avery", "Ping")
            state_before = load_json(chat["state_path"])

            cursor_path = Path(tmp) / "codex_cursor.json"
            unread = service.scan_unread("Codex", cursor_path)
            self.assertEqual(len(unread), 1)
            self.assertEqual(unread[0].unread_count, 1)

            service.mark_seen("Codex", cursor_path, chat["state"]["chat_id"])
            unread_after = service.scan_unread("Codex", cursor_path)
            state_after = load_json(chat["state_path"])

            self.assertEqual(unread_after, [])
            self.assertEqual(state_before, state_after)
            cursor = load_json(cursor_path)
            self.assertEqual(cursor["positions"][chat["state"]["chat_id"]]["last_seen_message_id"], 1)

    def test_canonical_scan_uses_messages_when_state_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            chat = service.create_chat("Canonical Scan", participants=["Claude"])
            chat = service.post_message(chat["state"]["chat_id"], "Avery", "One")
            chat = service.post_message(chat["state"]["chat_id"], "Avery", "Two")
            chat_id = chat["state"]["chat_id"]

            cursor_path = Path(tmp) / "claude_cursor.json"
            service.mark_seen("Claude", cursor_path, chat_id, message_id=1)

            state = load_json(chat["state_path"])
            state["last_message_id"] = 1
            write_json_atomic(chat["state_path"], state)

            state_scan = service.scan_unread("Claude", cursor_path, source="state")
            canonical_scan = service.scan_unread("Claude", cursor_path, source="canonical")

            self.assertEqual(state_scan, [])
            self.assertEqual(len(canonical_scan), 1)
            self.assertEqual(canonical_scan[0].last_message_id, 2)
            self.assertEqual(canonical_scan[0].unread_count, 1)
            self.assertIn("state/cache looked stale", canonical_scan[0].warnings[0])

    def test_participant_gated_scan_ignores_non_participant_rooms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            chat = service.create_chat("Gated Scan", participants=["Avery"])
            chat = service.post_message(chat["state"]["chat_id"], "Avery", "Private")
            cursor_path = Path(tmp) / "cursor.json"

            self.assertEqual(service.scan_unread("Codex", cursor_path), [])
            audit_scan = service.scan_unread("Codex", cursor_path, participant_gated=False)
            self.assertEqual(len(audit_scan), 1)
            self.assertEqual(audit_scan[0].chat_id, chat["state"]["chat_id"])

    def test_participant_operations_are_explicit_and_create_consumer_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            chat = service.create_chat("Participant Ops", participants=["Avery"])
            chat_id = chat["state"]["chat_id"]

            dry_run = service.add_participant_operation(chat_id, "Codex", threshold_chars=1200)
            self.assertTrue(dry_run["dry_run"])
            self.assertEqual(service.load_chat(chat_id)["state"]["participants"], ["Avery"])

            applied = service.add_participant_operation(chat_id, "Codex", threshold_chars=1200, apply=True)
            self.assertTrue(applied["applied"])
            self.assertEqual(service.load_chat(chat_id)["state"]["participants"], ["Avery", "Codex"])
            consumer_state = service.load_consumer_state(chat_id, "Codex")
            self.assertEqual(consumer_state["threshold_chars"], 1200)

            removed = service.remove_participant_operation(chat_id, "Codex", reason="test removal", apply=True)
            self.assertTrue(removed["applied"])
            self.assertEqual(service.load_chat(chat_id)["state"]["participants"], ["Avery"])
            consumer_state = service.load_consumer_state(chat_id, "Codex")
            self.assertEqual(consumer_state["status"], "removed_from_room")
            self.assertEqual(consumer_state["removal"]["reason"], "test removal")

    def test_mark_seen_canonical_uses_hidden_message_highest_when_state_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            chat = service.create_chat("Canonical Seen")
            chat = service.post_message(chat["state"]["chat_id"], "Avery", "One")
            chat = service.post_message(chat["state"]["chat_id"], "Avery", "Two")
            chat_id = chat["state"]["chat_id"]

            state = load_json(chat["state_path"])
            state["last_message_id"] = 1
            write_json_atomic(chat["state_path"], state)

            cursor_path = Path(tmp) / "claude_cursor.json"
            cursor = service.mark_seen("Claude", cursor_path, chat_id, source="canonical")
            self.assertEqual(cursor["positions"][chat_id]["last_seen_message_id"], 2)

    def test_message_version_audit_and_update_track_semantic_preparation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            chat = service.create_chat("Versions")
            chat = service.post_message(chat["state"]["chat_id"], "Avery", "Long canonical message")
            chat_id = chat["state"]["chat_id"]

            structural = service.audit_message_versions(chat_id)
            self.assertEqual(structural["needs_work_count"], 0)
            semantic = service.audit_message_versions(chat_id, semantic=True)
            self.assertEqual(semantic["needs_work_count"], 1)

            versions = {
                str(index): {"message": "Long canonical message" if index == 0 else f"Summary {index}"}
                for index in range(10)
            }
            service.update_message_versions(chat_id, 1, versions, prepared_by="Codex")
            semantic_after = service.audit_message_versions(chat_id, semantic=True)
            self.assertEqual(semantic_after["needs_work_count"], 0)
            loaded = service.load_chat(chat_id)["messages"][0]
            self.assertTrue(loaded["version_prep"]["semantic_prepared"])
            self.assertEqual(loaded["versions"]["9"]["char_count"], len("Summary 9"))

    def test_mark_version_prepped_requires_verified_message_and_writes_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            chat = service.create_chat("Version Cursor")
            chat = service.post_message(chat["state"]["chat_id"], "Avery", "Cursor canonical message")
            chat_id = chat["state"]["chat_id"]
            cursor_path = Path(tmp) / "codex_version_cursor.json"

            with self.assertRaises(ValueError):
                service.mark_version_prepped("Codex", cursor_path, chat_id, 1)

            versions = {
                str(index): {"message": "Cursor canonical message" if index == 0 else f"Cursor summary {index}"}
                for index in range(10)
            }
            service.update_message_versions(chat_id, 1, versions, prepared_by="Codex")
            state_before = load_json(chat["state_path"])

            cursor = service.mark_version_prepped("Codex", cursor_path, chat_id, 1)
            state_after = load_json(chat["state_path"])
            loaded = service.load_chat(chat_id)["messages"][0]
            prep = loaded["version_prep"]
            key = f"{chat_id}:1:semantic"

            self.assertEqual(state_before, state_after)
            self.assertEqual(cursor["schema_version"], config.VERSION_PREP_CURSOR_SCHEMA_VERSION)
            self.assertEqual(cursor["completed"][key]["source_hash"], prep["source_hash"])
            self.assertEqual(cursor["completed"][key]["bundle_hash"], prep["bundle_hash"])
            self.assertEqual(cursor["completed"][key]["prepared_at"], prep["prepared_at"])

            cli_cursor_path = Path(tmp) / "codex_version_cursor_cli.json"
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                self.assertEqual(
                    chatroom_cli.main(
                        [
                            "--root",
                            tmp,
                            "mark-version-prepped",
                            "--agent",
                            "Codex",
                            "--cursor",
                            str(cli_cursor_path),
                            "--chat",
                            chat_id,
                            "--message-id",
                            "1",
                        ]
                    ),
                    0,
                )
            cli_cursor = json.loads(buffer.getvalue())
            self.assertEqual(cli_cursor["completed"][key]["bundle_hash"], prep["bundle_hash"])

    def test_consumer_lens_steps_versions_and_removes_on_exhaustion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            chat = service.create_chat("Consumer Lens", participants=["Tiny"])
            chat = service.post_message(chat["state"]["chat_id"], "Avery", "A" * 40)
            chat_id = chat["state"]["chat_id"]
            versions = {"0": {"message": "A" * 40}}
            for index in range(1, 10):
                versions[str(index)] = {"message": "B" * 30}
            service.update_message_versions(chat_id, 1, versions)

            lens = service.render_consumer_lens(chat_id, "Tiny", threshold_chars=1)
            self.assertEqual(lens["consumer_compile"]["status"], "exhausted")
            self.assertNotIn("Tiny", service.load_chat(chat_id)["state"]["participants"])
            consumer_state = service.load_consumer_state(chat_id, "Tiny")
            self.assertEqual(consumer_state["status"], "removed_from_room")

    def test_render_chat_lens_uses_canonical_messages_when_compiled_cache_is_bad(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            chat = service.create_chat("Lens Chat")
            chat_id = chat["state"]["chat_id"]
            for index in range(1, 4):
                chat = service.post_message(chat_id, "Avery", f"Message {index}")
            service.add_standin(
                chat_id,
                [2],
                "Message 2 was resolved.",
                insert_after_message_id=2,
                standin_id="standin_message_2",
            )
            loaded = service.load_chat(chat_id)
            visible_path = Path(loaded["visible_path"])
            state_path = Path(loaded["state_path"])
            state_before = state_path.read_text(encoding="utf-8")
            message_before = {
                path.name: path.read_text(encoding="utf-8")
                for path in sorted((visible_path.parent / f"_{visible_path.stem}" / "messages").iterdir())
            }
            visible_path.write_text("{broken", encoding="utf-8")

            lens = service.render_chat_lens(chat_id, source="canonical")

            self.assertEqual([m["message_id"] for m in lens["messages"]], [1, "standin:standin_message_2", 3])
            self.assertEqual(lens["last_message_id"], 3)
            self.assertEqual(visible_path.read_text(encoding="utf-8"), "{broken")
            self.assertEqual(state_path.read_text(encoding="utf-8"), state_before)
            message_after = {
                path.name: path.read_text(encoding="utf-8")
                for path in sorted((visible_path.parent / f"_{visible_path.stem}" / "messages").iterdir())
            }
            self.assertEqual(message_after, message_before)

    def test_state_parse_failure_falls_back_to_messages_for_scan_and_verify(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            chat = service.create_chat("Broken State")
            chat = service.post_message(chat["state"]["chat_id"], "Avery", "Still visible")
            state_path = Path(chat["state_path"])
            state_path.write_text("{broken", encoding="utf-8")

            cursor_path = Path(tmp) / "cursor.json"
            unread = service.scan_unread("Codex", cursor_path)
            self.assertEqual(len(unread), 1)
            self.assertEqual(unread[0].last_message_id, 1)

            verify = service.verify()
            self.assertFalse(verify["ok"])
            self.assertIn("state_parse_failed", {issue["code"] for issue in verify["issues"]})

    def test_archive_restore_moves_visible_and_hidden_pair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            chat = service.create_chat("Move Chat")
            chat = service.post_message(chat["state"]["chat_id"], "Avery", "Move me")
            chat_id = chat["state"]["chat_id"]
            active_visible = Path(chat["visible_path"])
            active_hidden = active_visible.parent / f"_{active_visible.stem}"

            archived = service.archive_chat(chat_id)
            archived_visible = Path(archived["visible_path"])
            archived_hidden = archived_visible.parent / f"_{archived_visible.stem}"

            self.assertFalse(active_visible.exists())
            self.assertFalse(active_hidden.exists())
            self.assertTrue(archived_visible.exists())
            self.assertTrue(archived_hidden.exists())
            self.assertEqual(archived["state"]["status"], "archived")

            restored = service.restore_chat(chat_id)
            restored_visible = Path(restored["visible_path"])
            restored_hidden = restored_visible.parent / f"_{restored_visible.stem}"
            self.assertTrue(restored_visible.exists())
            self.assertTrue(restored_hidden.exists())
            self.assertEqual(restored["state"]["status"], "active")

    def test_create_room_operation_dry_run_apply_and_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            dry_run = service.create_room_operation(
                "Operations Room",
                folder="Projects/Chatroom",
                participants=["Avery", "Codex"],
                requested_by="Avery",
            )
            self.assertTrue(dry_run["dry_run"])
            self.assertFalse(dry_run["applied"])
            self.assertFalse(Path(dry_run["target"]["visible_path"]).exists())

            applied = service.create_room_operation(
                "Operations Room",
                folder="Projects/Chatroom",
                participants=["Avery", "Codex"],
                requested_by="Avery",
                apply=True,
            )
            self.assertFalse(applied["dry_run"])
            self.assertTrue(applied["applied"])
            self.assertTrue(Path(applied["target"]["visible_path"]).exists())
            self.assertEqual(applied["target"]["participants"], ["Avery", "Codex"])
            self.assertTrue(applied["verification"]["ok"])

            operations = service.read_operation_log()
            self.assertEqual(len(operations), 1)
            self.assertEqual(operations[0]["operation_type"], "create-room")
            self.assertEqual(operations[0]["target_chat_id"], applied["target"]["chat_id"])

    def test_archive_restore_operations_report_and_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            chat = service.create_chat("Operation Move", folder="Projects/Chatroom")
            chat_id = chat["state"]["chat_id"]

            dry_run = service.archive_room_operation(chat_id, requested_by="Codex")
            self.assertTrue(dry_run["dry_run"])
            self.assertEqual(dry_run["actions"][0]["status"], "would_move")
            self.assertEqual(dry_run["target"]["status"], "archived")

            archived = service.archive_room_operation(chat_id, requested_by="Codex", apply=True)
            self.assertTrue(archived["applied"])
            self.assertEqual(service.load_chat(chat_id)["state"]["status"], "archived")

            restored = service.restore_room_operation(chat_id, requested_by="Codex", apply=True)
            self.assertTrue(restored["applied"])
            self.assertEqual(service.load_chat(chat_id)["state"]["status"], "active")

            operations = service.read_operation_log()
            self.assertEqual([entry["operation_type"] for entry in operations], ["archive-room", "restore-room"])

    def test_place_message_preserves_kind_and_placement_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            source = service.create_chat("Source Chat")
            target = service.create_chat("Target Chat")
            source = service.post_message(source["state"]["chat_id"], "Codex", "Structural review", kind="review")
            source_id = source["state"]["chat_id"]
            target_id = target["state"]["chat_id"]

            dry_run = service.place_message_operation(
                source_id,
                1,
                target_id,
                placement_reason="Collect backend design review",
                requested_by="Codex",
            )
            self.assertTrue(dry_run["dry_run"])
            self.assertEqual(dry_run["actions"][0]["status"], "would_place")
            self.assertEqual(dry_run["actions"][0]["kind"], "review")

            applied = service.place_message_operation(
                source_id,
                1,
                target_id,
                placement_reason="Collect backend design review",
                requested_by="Codex",
                apply=True,
            )
            self.assertTrue(applied["applied"])
            target_loaded = service.load_chat(target_id)
            placed = target_loaded["messages"][-1]
            self.assertEqual(placed["speaker"], "Codex")
            self.assertEqual(placed["kind"], "review")
            self.assertEqual(placed["message"], "Structural review")
            self.assertEqual(placed["placement_metadata"]["source_chat_id"], source_id)
            self.assertEqual(placed["placement_metadata"]["source_message_id"], 1)
            self.assertEqual(placed["placement_metadata"]["target_message_id"], 1)

            compiled = load_json(target_loaded["visible_path"])
            self.assertEqual(compiled["messages"][-1]["placement_metadata"]["source_message_id"], 1)
            lens = service.render_chat_lens(target_id)
            self.assertEqual(lens["messages"][-1]["placement_metadata"]["source_message_id"], 1)

            duplicate_dry_run = service.place_message_operation(
                source_id,
                1,
                target_id,
                placement_reason="Collect backend design review",
                requested_by="Codex",
            )
            self.assertEqual(duplicate_dry_run["actions"][0]["status"], "skipped_duplicate")
            self.assertIn("already appears", duplicate_dry_run["warnings"][0])

            duplicate = service.duplicate_message_operation(
                source_id,
                1,
                target_id,
                placement_reason="Collect backend design review",
                requested_by="Codex",
                apply=True,
            )
            self.assertTrue(duplicate["applied"])
            self.assertEqual(duplicate["target"]["target_message_ids"], [2])

    def test_place_range_wraps_single_message_placement_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            source = service.create_chat("Range Source")
            target = service.create_chat("Range Target")
            source_id = source["state"]["chat_id"]
            target_id = target["state"]["chat_id"]
            for index in range(1, 4):
                service.post_message(source_id, "Avery", f"Message {index}")

            applied = service.place_range_operation(
                source_id,
                1,
                2,
                target_id,
                placement_reason="Copy ordered setup context",
                requested_by="Codex",
                apply=True,
            )
            self.assertTrue(applied["applied"])
            self.assertEqual(applied["target"]["target_message_ids"], [1, 2])
            target_messages = service.load_chat(target_id)["messages"]
            self.assertEqual([message["message"] for message in target_messages], ["Message 1", "Message 2"])
            self.assertEqual([message["placement_metadata"]["source_message_id"] for message in target_messages], [1, 2])

    def test_compile_policy_operation_no_standin_preserves_canonical_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            chat = service.create_chat("No Standin Policy")
            chat_id = chat["state"]["chat_id"]
            for index in range(1, 4):
                service.post_message(chat_id, "Avery", f"Message {index}")

            applied = service.apply_compile_policy_operation(
                chat_id,
                [2],
                mode="no-standin",
                requested_by="Codex",
                apply=True,
            )
            self.assertTrue(applied["applied"])
            loaded = service.load_chat(chat_id)
            compiled = load_json(loaded["visible_path"])
            self.assertEqual([message["message_id"] for message in loaded["messages"]], [1, 2, 3])
            self.assertEqual([message["message_id"] for message in compiled["messages"]], [1, 3])
            self.assertEqual(compiled["compile_policy"]["standins"], [])

            operations = service.read_operation_log()
            self.assertEqual(operations[0]["operation_type"], "compile-policy")
            self.assertEqual(operations[0]["compile_policy_changes"]["mode"], "no-standin")

    def test_cli_create_room_defaults_to_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                self.assertEqual(
                    chatroom_cli.main(["--root", tmp, "create-room", "--title", "CLI Dry Run"]),
                    0,
                )
            report = json.loads(buffer.getvalue())
            self.assertTrue(report["dry_run"])
            self.assertFalse(Path(report["target"]["visible_path"]).exists())

    def test_lock_prevents_duplicate_message_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            chat = service.create_chat("Locked Chat")
            visible = Path(chat["visible_path"])
            lock_path = visible.parent / f"_{visible.stem}" / config.LOCK_FILE_NAME
            lock_path.write_text("locked", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                service.post_message(chat["state"]["chat_id"], "Avery", "Blocked")

    def test_lock_release_renames_when_delete_is_denied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ChatroomService(tmp)
            chat = service.create_chat("Delete Denied Lock")
            visible = Path(chat["visible_path"])
            companion = visible.parent / f"_{visible.stem}"
            lock_path = companion / config.LOCK_FILE_NAME
            original_unlink = Path.unlink

            def deny_lock_unlink(path: Path, *args, **kwargs):
                if path.name == config.LOCK_FILE_NAME:
                    raise PermissionError("simulated delete denial")
                return original_unlink(path, *args, **kwargs)

            with patch.object(Path, "unlink", deny_lock_unlink):
                posted = service.post_message(chat["state"]["chat_id"], "Claude", "Posted through a delete-hostile mount")

            self.assertEqual(posted["state"]["last_message_id"], 1)
            self.assertFalse(lock_path.exists())
            released_locks = sorted(companion.glob(f"{config.LOCK_FILE_NAME}.released.*"))
            self.assertEqual(len(released_locks), 1)

            posted_again = service.post_message(chat["state"]["chat_id"], "Codex", "Next writer is not blocked")
            self.assertEqual(posted_again["state"]["last_message_id"], 2)

    def test_claude_connector_check_read_seen_and_post(self) -> None:
        connector = load_claude_connector_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = ChatroomService(root)
            chat = service.create_chat("Claude Door", folder="Projects/Chatroom", participants=["Claude"])
            chat = service.post_message(chat["state"]["chat_id"], "Avery", "Review this")
            chat_id = chat["state"]["chat_id"]
            model_root = root / "Models" / "Claude"
            outbox = model_root / "outbox"
            cursor_path = model_root / "state" / "claude_chatroom_cursor.json"
            outbox.mkdir(parents=True)
            ctx = connector.RuntimeContext(
                project_root=root,
                chat_root=root,
                model_root=model_root,
                cursor_path=cursor_path,
                outbox_dir=outbox,
                service=service,
            )

            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                self.assertEqual(connector.command_check(SimpleNamespace(status="active"), ctx), 0)
            self.assertIn(chat_id, buffer.getvalue())
            self.assertIn("project=true", buffer.getvalue())
            self.assertFalse(cursor_path.exists())

            Path(chat["visible_path"]).write_text("{broken", encoding="utf-8")
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                self.assertEqual(connector.command_read(SimpleNamespace(chat=chat_id, debug=False), ctx), 0)
            self.assertIn("SOURCE: canonical hidden messages", buffer.getvalue())
            self.assertIn("Review this", buffer.getvalue())
            self.assertFalse(cursor_path.exists())

            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                self.assertEqual(connector.command_seen(SimpleNamespace(chat=chat_id), ctx), 0)
            self.assertTrue(cursor_path.exists())
            self.assertEqual(load_json(cursor_path)["positions"][chat_id]["last_seen_message_id"], 1)

            message_path = outbox / "reply.md"
            message_path.write_text("Claude connector reply", encoding="utf-8")
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                self.assertEqual(
                    connector.command_post(
                        SimpleNamespace(chat=chat_id, message_file=str(message_path), kind="review", mentions=None),
                        ctx,
                    ),
                    0,
                )
            posted = service.load_chat(chat_id)["messages"][-1]
            self.assertEqual(posted["speaker"], "Claude")
            self.assertEqual(posted["kind"], "review")
            self.assertEqual(posted["message"], "Claude connector reply")

    def test_claude_connector_check_failure_is_graceful(self) -> None:
        connector = load_claude_connector_module()

        class StaleService:
            def scan_unread(self, *args, **kwargs):
                raise TypeError("ChatroomService.scan_unread() got an unexpected keyword argument 'source'")

        ctx = connector.RuntimeContext(
            project_root=Path("unused"),
            chat_root=Path("unused"),
            model_root=Path("unused"),
            cursor_path=Path("unused") / "cursor.json",
            outbox_dir=Path("unused") / "outbox",
            service=StaleService(),
        )

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.assertEqual(connector.command_check(SimpleNamespace(status="active"), ctx), 1)
        output = buffer.getvalue()
        self.assertIn("check failed:", output)
        self.assertIn("no write occurred", output)
        self.assertIn("backend item for Codex", output)

    def test_claude_connector_prefers_mounted_chat_root_over_empty_registry_root(self) -> None:
        connector = load_claude_connector_module()
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            registry_path = project_root / "Storage" / "Generated Artifacts" / "System" / "storage_registry.json"
            registry_path.parent.mkdir(parents=True)
            registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "key": "repo_root",
                                "label": "Repo Root",
                                "path": str(project_root / "elsewhere"),
                                "read_only": True,
                                "supports_migration": False,
                            },
                            {
                                "key": "chat_root",
                                "label": "Chats",
                                "path": "Storage\\Generated Artifacts\\Chats\\",
                                "uses_repo_root": True,
                                "read_only": False,
                                "supports_migration": True,
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            mounted_chat_root = project_root / "Storage" / "Generated Artifacts" / "Chats"
            mounted_active = mounted_chat_root / "Active" / "Projects"
            mounted_active.mkdir(parents=True)
            (mounted_active / "Real_Chat.json").write_text("{}", encoding="utf-8")

            self.assertEqual(connector.resolve_chat_root(project_root), mounted_chat_root.resolve())


if __name__ == "__main__":
    unittest.main()

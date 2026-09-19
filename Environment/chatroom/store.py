from __future__ import annotations

import errno
import hashlib
import json
import os
import shutil
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from . import config
from .consumer_compile import fit_selected_versions, render_selected_messages
from .json_io import append_jsonl, load_json, write_json_atomic
from .models import ChatSummary, VerificationIssue
from .paths import ChatroomPaths, normalize_status, sanitize_file_stem


def now_timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def clean_unique_strings(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    results: list[str] = []
    for value in values:
        clean = str(value or "").strip()
        if clean and clean not in results:
            results.append(clean)
    return results


def clean_kind(kind: str | None) -> str:
    clean = str(kind or "").strip().lower() or "message"
    if clean not in config.ALLOWED_MESSAGE_KINDS:
        raise ValueError(f"Unsupported chat message kind: {clean}")
    return clean


def clean_message_ids(values: object) -> list[int]:
    if isinstance(values, str):
        raw_values: object = [part.strip() for part in values.split(",")]
    else:
        raw_values = values
    if not isinstance(raw_values, list):
        raise ValueError("Message IDs must be a list or comma-separated string.")

    results: list[int] = []
    for value in raw_values:
        try:
            message_id = int(value)
        except Exception as exc:
            raise ValueError(f"Invalid message id: {value}") from exc
        if message_id <= 0:
            raise ValueError(f"Message id must be positive: {message_id}")
        if message_id not in results:
            results.append(message_id)
    return sorted(results)


def text_char_count(value: object) -> int:
    return len(str(value or ""))


def stable_json_char_count(value: object) -> int:
    return len(json.dumps(value, ensure_ascii=False, default=str))


def text_hash(value: object) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def identity_versions(message: str) -> dict[str, dict]:
    count = text_char_count(message)
    return {
        str(level): {"message": message, "char_count": count}
        for level in range(config.MESSAGE_VERSION_MIN_LEVEL, config.MESSAGE_VERSION_MAX_LEVEL + 1)
    }


def bundle_hash(versions: dict) -> str:
    return hashlib.sha256(json.dumps(versions, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def version_prep_record(
    message: str,
    versions: dict,
    *,
    prepared_by: str,
    semantic_prepared: bool,
    prepared_at: str | None = None,
) -> dict:
    return {
        "schema_version": config.VERSION_PREP_SCHEMA_VERSION,
        "structural_valid": True,
        "semantic_prepared": bool(semantic_prepared),
        "prepared_by": str(prepared_by or "").strip() or "Backend",
        "prepared_at": prepared_at or now_timestamp(),
        "source_hash": text_hash(message),
        "bundle_hash": bundle_hash(versions),
    }


PLACEMENT_METADATA_STRING_FIELDS = {
    "source_chat_id",
    "source_chat_title",
    "source_speaker",
    "source_timestamp",
    "target_chat_id",
    "target_chat_title",
    "placement_reason",
    "placed_by",
    "placed_at",
    "content_mode",
    "operation_id",
}


def clean_placement_metadata(values: object) -> dict | None:
    if not isinstance(values, dict):
        return None
    cleaned: dict[str, Any] = {"is_placement_copy": bool(values.get("is_placement_copy", True))}
    for field_name in PLACEMENT_METADATA_STRING_FIELDS:
        raw_value = values.get(field_name)
        if raw_value is None:
            continue
        cleaned[field_name] = str(raw_value or "").strip()
    for field_name in ("source_message_id", "target_message_id"):
        if field_name not in values:
            continue
        try:
            cleaned[field_name] = int(values.get(field_name, 0) or 0)
        except Exception:
            continue
    return cleaned


def clean_content_mode(content_mode: str | None) -> str:
    clean = str(content_mode or "full_copy").strip().lower() or "full_copy"
    if clean != "full_copy":
        raise ValueError(f"Unsupported placement content mode: {content_mode}")
    return clean


def new_operation_id(operation_type: str) -> str:
    clean_type = str(operation_type or "operation").strip().lower().replace("_", "-")
    return f"op_{clean_type}_{uuid.uuid4().hex}"


def normalize_compile_policy(raw_policy: object) -> dict:
    if not isinstance(raw_policy, dict):
        return {"excluded_message_ids": [], "standins": []}

    try:
        excluded_message_ids = clean_message_ids(raw_policy.get("excluded_message_ids", []))
    except ValueError:
        excluded_message_ids = []

    standins: list[dict] = []
    raw_standins = raw_policy.get("standins", [])
    if isinstance(raw_standins, list):
        for raw_standin in raw_standins:
            if not isinstance(raw_standin, dict):
                continue
            message = str(raw_standin.get("message", "") or "").strip()
            if not message:
                continue
            standin_id = str(raw_standin.get("standin_id", "") or "").strip()
            if not standin_id:
                standin_id = f"standin_{uuid.uuid4().hex}"
            try:
                replaces_message_ids = clean_message_ids(raw_standin.get("replaces_message_ids", []))
            except ValueError:
                replaces_message_ids = []
            try:
                insert_after_message_id = int(raw_standin.get("insert_after_message_id", 0) or 0)
            except Exception:
                insert_after_message_id = 0
            standins.append(
                {
                    "standin_id": standin_id,
                    "replaces_message_ids": replaces_message_ids,
                    "insert_after_message_id": max(0, insert_after_message_id),
                    "speaker": str(raw_standin.get("speaker", "") or "System").strip() or "System",
                    "timestamp": str(raw_standin.get("timestamp", "") or "").strip(),
                    "kind": clean_kind(str(raw_standin.get("kind", "") or "system")),
                    "mentions": clean_unique_strings(raw_standin.get("mentions", [])),
                    "message": message,
                }
            )

    return {
        "excluded_message_ids": excluded_message_ids,
        "standins": standins,
    }


class ChatroomStore:
    def __init__(self, root_dir: str | Path) -> None:
        self.paths = ChatroomPaths(root_dir)
        self.paths.ensure_roots()

    @property
    def root_dir(self) -> Path:
        return self.paths.root_dir

    def list_chats(self, status: str = "active") -> list[ChatSummary]:
        summaries: list[ChatSummary] = []
        for visible_path in self.paths.iter_visible_paths(status):
            try:
                state = self.load_state(visible_path)
            except Exception:
                continue
            compile_info = state.get("compile", {})
            if not isinstance(compile_info, dict):
                compile_info = {}
            summaries.append(
                ChatSummary(
                    chat_id=str(state.get("chat_id", "") or ""),
                    chat_title=str(state.get("chat_title", "") or visible_path.stem),
                    status=str(state.get("status", "") or self.paths.infer_status(visible_path)),
                    visible_path=visible_path,
                    state_path=self.paths.state_path(visible_path),
                    last_message_id=int(state.get("last_message_id", 0) or 0),
                    last_message_at=str(state.get("last_message_at", "") or ""),
                    compile_status=str(compile_info.get("status", "") or ""),
                    last_compiled_message_id=int(compile_info.get("last_compiled_message_id", 0) or 0),
                )
            )
        return sorted(summaries, key=lambda item: (str(item.visible_path.parent).lower(), item.chat_title.lower()))

    def create_chat(
        self,
        title: str,
        folder: str | None = None,
        participants: list[str] | None = None,
    ) -> dict:
        clean_title = str(title or "").strip()
        if not clean_title:
            raise ValueError("Chat title is required.")

        visible_path = self.paths.unique_visible_path(clean_title, folder)
        chat_paths = self.paths.chat_paths(visible_path)
        chat_paths.messages_dir.mkdir(parents=True, exist_ok=True)
        chat_paths.consumers_dir.mkdir(parents=True, exist_ok=True)

        timestamp = now_timestamp()
        chat_id = f"chat_{uuid.uuid4().hex}"
        clean_participants = clean_unique_strings(participants or [])
        state = {
            "schema_version": config.STATE_SCHEMA_VERSION,
            "chat_id": chat_id,
            "chat_file": visible_path.name,
            "chat_title": clean_title,
            "status": "active",
            "participants": clean_participants,
            "created_at": timestamp,
            "updated_at": timestamp,
            "last_message_id": 0,
            "last_message_at": "",
            "compile": {
                "status": "clean",
                "last_compiled_message_id": 0,
                "last_compiled_at": timestamp,
                "error": "",
            },
            "compile_policy": {
                "excluded_message_ids": [],
                "standins": [],
            },
        }
        compiled = self._build_compiled_payload(state, [], timestamp)
        state["compile"]["compiled_chars"] = int(compiled.get("compiled_chars", 0) or 0)
        state["last_full_compile"] = {
            "compiled_chars": int(compiled.get("compiled_chars", 0) or 0),
            "message_count": 0,
            "compiled_at": timestamp,
        }
        write_json_atomic(visible_path, compiled)
        write_json_atomic(chat_paths.state_path, state)
        for participant in clean_participants:
            self._save_consumer_state(
                visible_path,
                self._default_consumer_state(state, participant, timestamp=timestamp),
            )
        return self.load_chat(visible_path)

    def load_chat(self, chat_ref: str | Path) -> dict:
        visible_path = self.resolve_chat_ref(chat_ref)
        state = self.load_state(visible_path)
        messages = self.load_messages(visible_path)
        return {
            "state": state,
            "messages": messages,
            "visible_path": str(visible_path),
            "state_path": str(self.paths.state_path(visible_path)),
            "messages_dir": str(self.paths.messages_dir(visible_path)),
        }

    def load_state(self, chat_ref: str | Path) -> dict:
        visible_path = self._visible_from_path_ref(chat_ref)
        state_path = self.paths.state_path(visible_path)
        parsed = load_json(state_path)
        if not isinstance(parsed, dict):
            raise ValueError(f"Chatroom state must be a JSON object: {state_path}")
        if parsed.get("schema_version") != config.STATE_SCHEMA_VERSION:
            raise ValueError(f"Unsupported chatroom state schema at {state_path}: {parsed.get('schema_version')}")
        if not str(parsed.get("chat_id", "") or "").startswith("chat_"):
            raise ValueError(f"Chatroom state missing chat_id: {state_path}")
        return parsed

    def load_messages(self, chat_ref: str | Path) -> list[dict]:
        visible_path = self.resolve_chat_ref(chat_ref)
        messages: list[dict] = []
        for message_path in self.message_file_paths(visible_path):
            parsed = load_json(message_path)
            if not isinstance(parsed, dict):
                raise ValueError(f"Message file must be a JSON object: {message_path}")
            if parsed.get("schema_version") != config.MESSAGE_SCHEMA_VERSION:
                raise ValueError(f"Unsupported chatroom message schema at {message_path}: {parsed.get('schema_version')}")
            messages.append(self._normalize_message(parsed))
        return sorted(messages, key=lambda item: int(item.get("message_id", 0) or 0))

    def message_file_paths(self, chat_ref: str | Path) -> list[Path]:
        visible_path = self._visible_from_path_ref(chat_ref)
        messages_dir = self.paths.messages_dir(visible_path)
        if not messages_dir.exists():
            return []
        return sorted(
            [path for path in messages_dir.iterdir() if path.is_file() and path.suffix.lower() == ".json"],
            key=lambda path: self._message_sort_key(path),
        )

    def resolve_chat_ref(self, chat_ref: str | Path) -> Path:
        ref_text = str(chat_ref or "").strip()
        if not ref_text:
            raise ValueError("chat_ref is required.")
        if ref_text.startswith("chat_"):
            for visible_path in self.paths.iter_visible_paths(None):
                try:
                    state = self.load_state(visible_path)
                except Exception:
                    continue
                if str(state.get("chat_id", "") or "") == ref_text:
                    return visible_path
            raise FileNotFoundError(f"Chat id not found: {ref_text}")
        return self._visible_from_path_ref(ref_text)

    def post_message(
        self,
        chat_ref: str | Path,
        speaker: str,
        message: str,
        *,
        kind: str = "message",
        mentions: list[str] | None = None,
        placement_metadata: dict | None = None,
        compile_after: bool = True,
        require_participant: bool = False,
        force_stale_lock: bool = False,
    ) -> dict:
        visible_path = self.resolve_chat_ref(chat_ref)
        clean_speaker = str(speaker or "").strip()
        if not clean_speaker:
            raise ValueError("Speaker is required.")
        clean_message = str(message or "").strip()
        if not clean_message:
            raise ValueError("Message is required.")
        clean_mentions = clean_unique_strings(mentions or [])
        clean_message_kind = clean_kind(kind)

        with self.chat_lock(visible_path, force_stale=force_stale_lock):
            state = self.load_state(visible_path)
            participants = clean_unique_strings(state.get("participants", []))
            if require_participant and clean_speaker not in participants:
                raise PermissionError(f"Speaker is not a current participant in this room: {clean_speaker}")
            highest_message_id = self.highest_message_id(visible_path)
            next_id = max(int(state.get("last_message_id", 0) or 0), highest_message_id) + 1
            timestamp = now_timestamp()
            versions = identity_versions(clean_message)
            message_record = {
                "schema_version": config.MESSAGE_SCHEMA_VERSION,
                "chat_id": state["chat_id"],
                "message_id": next_id,
                "speaker": clean_speaker,
                "timestamp": timestamp,
                "kind": clean_message_kind,
                "mentions": clean_mentions,
                "message": clean_message,
                "char_count": text_char_count(clean_message),
                "versions": versions,
                "version_prep": version_prep_record(
                    clean_message,
                    versions,
                    prepared_by="Backend",
                    semantic_prepared=False,
                    prepared_at=timestamp,
                ),
            }
            clean_metadata = clean_placement_metadata(placement_metadata)
            if clean_metadata:
                clean_metadata["target_message_id"] = next_id
                message_record["placement_metadata"] = clean_metadata
            message_path = self.paths.messages_dir(visible_path) / f"{next_id:06d}.json"
            if message_path.exists():
                raise FileExistsError(f"Message file already exists: {message_path}")
            write_json_atomic(message_path, message_record)

            state["participants"] = participants
            state["updated_at"] = timestamp
            state["last_message_id"] = next_id
            state["last_message_at"] = timestamp
            state["chat_file"] = visible_path.name
            state["status"] = self.paths.infer_status(visible_path)

            if compile_after:
                return self._compile_visible(visible_path, state=state, timestamp=timestamp)

            state["compile"] = {
                "status": "dirty",
                "last_compiled_message_id": int(state.get("compile", {}).get("last_compiled_message_id", 0) or 0)
                if isinstance(state.get("compile"), dict)
                else 0,
                "last_compiled_at": str(state.get("compile", {}).get("last_compiled_at", "") or "")
                if isinstance(state.get("compile"), dict)
                else "",
                "error": "",
            }
            write_json_atomic(self.paths.state_path(visible_path), state)
            return self.load_chat(visible_path)

    def compile_chat(self, chat_ref: str | Path, *, force_stale_lock: bool = False) -> dict:
        visible_path = self.resolve_chat_ref(chat_ref)
        with self.chat_lock(visible_path, force_stale=force_stale_lock):
            state = self.load_state(visible_path)
            return self._compile_visible(visible_path, state=state)

    def get_compile_policy(self, chat_ref: str | Path) -> dict:
        visible_path = self.resolve_chat_ref(chat_ref)
        state = self.load_state(visible_path)
        return normalize_compile_policy(state.get("compile_policy", {}))

    def exclude_messages(
        self,
        chat_ref: str | Path,
        message_ids: list[int],
        *,
        compile_after: bool = True,
        force_stale_lock: bool = False,
    ) -> dict:
        clean_ids = clean_message_ids(message_ids)
        visible_path = self.resolve_chat_ref(chat_ref)
        with self.chat_lock(visible_path, force_stale=force_stale_lock):
            state = self.load_state(visible_path)
            self._assert_message_ids_exist(visible_path, clean_ids)
            policy = normalize_compile_policy(state.get("compile_policy", {}))
            existing_ids = set(policy["excluded_message_ids"])
            existing_ids.update(clean_ids)
            policy["excluded_message_ids"] = sorted(existing_ids)
            state["compile_policy"] = policy
            state["updated_at"] = now_timestamp()
            return self._write_state_after_policy_change(visible_path, state, compile_after=compile_after)

    def include_messages(
        self,
        chat_ref: str | Path,
        message_ids: list[int],
        *,
        compile_after: bool = True,
        force_stale_lock: bool = False,
    ) -> dict:
        clean_ids = set(clean_message_ids(message_ids))
        visible_path = self.resolve_chat_ref(chat_ref)
        with self.chat_lock(visible_path, force_stale=force_stale_lock):
            state = self.load_state(visible_path)
            policy = normalize_compile_policy(state.get("compile_policy", {}))
            policy["excluded_message_ids"] = [
                message_id for message_id in policy["excluded_message_ids"] if message_id not in clean_ids
            ]
            state["compile_policy"] = policy
            state["updated_at"] = now_timestamp()
            return self._write_state_after_policy_change(visible_path, state, compile_after=compile_after)

    def add_standin(
        self,
        chat_ref: str | Path,
        replaces_message_ids: list[int],
        message: str,
        *,
        insert_after_message_id: int | None = None,
        speaker: str = "System",
        kind: str = "system",
        mentions: list[str] | None = None,
        standin_id: str | None = None,
        compile_after: bool = True,
        force_stale_lock: bool = False,
    ) -> dict:
        clean_replaces = clean_message_ids(replaces_message_ids)
        clean_message = str(message or "").strip()
        if not clean_message:
            raise ValueError("Stand-in message is required.")
        clean_insert_after = int(insert_after_message_id if insert_after_message_id is not None else max(clean_replaces))
        if clean_insert_after < 0:
            raise ValueError("insert_after_message_id cannot be negative.")

        visible_path = self.resolve_chat_ref(chat_ref)
        with self.chat_lock(visible_path, force_stale=force_stale_lock):
            state = self.load_state(visible_path)
            self._assert_message_ids_exist(visible_path, clean_replaces)
            if clean_insert_after:
                self._assert_message_ids_exist(visible_path, [clean_insert_after])

            timestamp = now_timestamp()
            policy = normalize_compile_policy(state.get("compile_policy", {}))
            excluded_ids = set(policy["excluded_message_ids"])
            excluded_ids.update(clean_replaces)
            clean_standin_id = str(standin_id or "").strip() or f"standin_{uuid.uuid4().hex}"
            policy["excluded_message_ids"] = sorted(excluded_ids)
            policy["standins"].append(
                {
                    "standin_id": clean_standin_id,
                    "replaces_message_ids": clean_replaces,
                    "insert_after_message_id": clean_insert_after,
                    "speaker": str(speaker or "System").strip() or "System",
                    "timestamp": timestamp,
                    "kind": clean_kind(kind),
                    "mentions": clean_unique_strings(mentions or []),
                    "message": clean_message,
                }
            )
            state["compile_policy"] = policy
            state["updated_at"] = timestamp
            return self._write_state_after_policy_change(visible_path, state, compile_after=compile_after)

    def clear_compile_policy(
        self,
        chat_ref: str | Path,
        *,
        compile_after: bool = True,
        force_stale_lock: bool = False,
    ) -> dict:
        visible_path = self.resolve_chat_ref(chat_ref)
        with self.chat_lock(visible_path, force_stale=force_stale_lock):
            state = self.load_state(visible_path)
            state["compile_policy"] = {
                "excluded_message_ids": [],
                "standins": [],
            }
            state["updated_at"] = now_timestamp()
            return self._write_state_after_policy_change(visible_path, state, compile_after=compile_after)

    def participant_coverage(self, participant: str, *, status: str = "active") -> dict:
        clean_participant = str(participant or "").strip()
        if not clean_participant:
            raise ValueError("Participant is required.")
        rooms: list[dict] = []
        for visible_path in self.paths.iter_visible_paths(status):
            try:
                state = self.load_state(visible_path)
            except Exception as exc:
                rooms.append(
                    {
                        "visible_path": str(visible_path),
                        "state_path": str(self.paths.state_path(visible_path)),
                        "participants_known": False,
                        "included": False,
                        "error": str(exc),
                    }
                )
                continue
            participants = clean_unique_strings(state.get("participants", []))
            included = clean_participant in participants
            rooms.append(
                {
                    "chat_id": state["chat_id"],
                    "chat_title": state.get("chat_title", visible_path.stem),
                    "status": state.get("status", self.paths.infer_status(visible_path)),
                    "visible_path": str(visible_path),
                    "state_path": str(self.paths.state_path(visible_path)),
                    "participants": participants,
                    "participants_known": True,
                    "included": included,
                }
            )
        return {
            "participant": clean_participant,
            "status": normalize_status(status),
            "room_count": len(rooms),
            "included_count": sum(1 for room in rooms if room.get("included")),
            "rooms": rooms,
        }

    def add_participant_operation(
        self,
        chat_ref: str | Path,
        participant: str,
        *,
        threshold_chars: int | None = None,
        requested_by: str = "Codex",
        apply: bool = False,
        force_stale_lock: bool = False,
    ) -> dict:
        visible_path = self.resolve_chat_ref(chat_ref)
        state = self.load_state(visible_path)
        clean_participant = str(participant or "").strip()
        if not clean_participant:
            raise ValueError("Participant is required.")
        current = clean_unique_strings(state.get("participants", []))
        target_participants = current[:] if clean_participant in current else [*current, clean_participant]
        report = self._operation_report(
            operation_id=new_operation_id("participant-add"),
            operation_type="participant-add",
            requested_by=requested_by,
            apply=apply,
            source={
                "chat_id": state["chat_id"],
                "chat_title": state.get("chat_title", ""),
                "visible_path": str(visible_path),
                "participants": current,
            },
            target={
                "chat_id": state["chat_id"],
                "chat_title": state.get("chat_title", ""),
                "visible_path": str(visible_path),
                "participants": target_participants,
                "participant": clean_participant,
                "threshold_chars": int(threshold_chars or config.DEFAULT_CONSUMER_THRESHOLD_CHARS),
            },
            actions=[
                {
                    "type": "participant-add",
                    "status": "noop" if clean_participant in current else ("would_add" if not apply else "pending"),
                    "participant": clean_participant,
                    "creates_or_updates_consumer_state": True,
                }
            ],
        )
        if not apply or clean_participant in current:
            return report

        with self.chat_lock(visible_path, force_stale=force_stale_lock):
            locked_state = self.load_state(visible_path)
            locked_participants = clean_unique_strings(locked_state.get("participants", []))
            if clean_participant not in locked_participants:
                locked_participants.append(clean_participant)
            timestamp = now_timestamp()
            locked_state["participants"] = locked_participants
            locked_state["updated_at"] = timestamp
            consumer_state = self._default_consumer_state(
                locked_state,
                clean_participant,
                threshold_chars=int(threshold_chars or config.DEFAULT_CONSUMER_THRESHOLD_CHARS),
                timestamp=timestamp,
            )
            existing = self._load_consumer_state_if_exists(visible_path, clean_participant)
            if existing:
                consumer_state.update(existing)
                consumer_state["status"] = "active"
                consumer_state["threshold_chars"] = int(threshold_chars or existing.get("threshold_chars", config.DEFAULT_CONSUMER_THRESHOLD_CHARS) or config.DEFAULT_CONSUMER_THRESHOLD_CHARS)
                consumer_state["updated_at"] = timestamp
            self._save_consumer_state(visible_path, consumer_state)
            result = self._compile_visible(visible_path, state=locked_state, timestamp=timestamp)
        report["actions"][0]["status"] = "added"
        report["target"]["participants"] = result["state"].get("participants", [])
        report["applied"] = True
        report["verification"] = self._verification_summary()
        self._append_operation_report(report)
        return report

    def remove_participant_operation(
        self,
        chat_ref: str | Path,
        participant: str,
        *,
        reason: str = "",
        requested_by: str = "Codex",
        apply: bool = False,
        force_stale_lock: bool = False,
    ) -> dict:
        visible_path = self.resolve_chat_ref(chat_ref)
        state = self.load_state(visible_path)
        clean_participant = str(participant or "").strip()
        if not clean_participant:
            raise ValueError("Participant is required.")
        current = clean_unique_strings(state.get("participants", []))
        target_participants = [item for item in current if item != clean_participant]
        report = self._operation_report(
            operation_id=new_operation_id("participant-remove"),
            operation_type="participant-remove",
            requested_by=requested_by,
            apply=apply,
            source={
                "chat_id": state["chat_id"],
                "chat_title": state.get("chat_title", ""),
                "visible_path": str(visible_path),
                "participants": current,
            },
            target={
                "chat_id": state["chat_id"],
                "chat_title": state.get("chat_title", ""),
                "visible_path": str(visible_path),
                "participants": target_participants,
                "participant": clean_participant,
            },
            actions=[
                {
                    "type": "participant-remove",
                    "status": "noop" if clean_participant not in current else ("would_remove" if not apply else "pending"),
                    "participant": clean_participant,
                    "historical_messages_preserved": True,
                    "reason": str(reason or "").strip(),
                }
            ],
        )
        if not apply or clean_participant not in current:
            return report

        with self.chat_lock(visible_path, force_stale=force_stale_lock):
            locked_state = self.load_state(visible_path)
            timestamp = now_timestamp()
            locked_state["participants"] = [
                item for item in clean_unique_strings(locked_state.get("participants", [])) if item != clean_participant
            ]
            locked_state["updated_at"] = timestamp
            consumer_state = self._load_consumer_state_if_exists(visible_path, clean_participant)
            if consumer_state:
                consumer_state["status"] = "removed_from_room"
                consumer_state["updated_at"] = timestamp
                consumer_state["removal"] = {
                    "reason": str(reason or "participant_removed_explicitly").strip(),
                    "removed_at": timestamp,
                    "last_compiled_chars": int(
                        consumer_state.get("last_compile", {}).get("compiled_chars", 0) or 0
                    )
                    if isinstance(consumer_state.get("last_compile"), dict)
                    else 0,
                }
                self._save_consumer_state(visible_path, consumer_state)
            result = self._compile_visible(visible_path, state=locked_state, timestamp=timestamp)
        report["actions"][0]["status"] = "removed"
        report["target"]["participants"] = result["state"].get("participants", [])
        report["applied"] = True
        report["verification"] = self._verification_summary()
        self._append_operation_report(report)
        return report

    def audit_message_versions(
        self,
        chat_ref: str | Path | None = None,
        *,
        status: str = "active",
        semantic: bool = False,
    ) -> dict:
        visible_paths = [self.resolve_chat_ref(chat_ref)] if chat_ref else self.paths.iter_visible_paths(status)
        rooms: list[dict] = []
        for visible_path in visible_paths:
            try:
                state = self.load_state(visible_path)
            except Exception as exc:
                rooms.append(
                    {
                        "visible_path": str(visible_path),
                        "state_path": str(self.paths.state_path(visible_path)),
                        "error": str(exc),
                        "messages": [],
                    }
                )
                continue
            message_reports: list[dict] = []
            for message_path in self.message_file_paths(visible_path):
                try:
                    parsed = load_json(message_path)
                except Exception as exc:
                    message_reports.append(
                        {
                            "message_path": str(message_path),
                            "structural_ready": False,
                            "semantic_prepared": False,
                            "needs_work": True,
                            "issues": [f"parse failed: {exc}"],
                        }
                    )
                    continue
                report = self._message_version_report(parsed, message_path)
                report["needs_work"] = not report["structural_ready"] or (semantic and not report["semantic_prepared"])
                message_reports.append(report)
            rooms.append(
                {
                    "chat_id": state["chat_id"],
                    "chat_title": state.get("chat_title", visible_path.stem),
                    "visible_path": str(visible_path),
                    "state_path": str(self.paths.state_path(visible_path)),
                    "message_count": len(message_reports),
                    "needs_work_count": sum(1 for item in message_reports if item.get("needs_work")),
                    "messages": message_reports,
                }
            )
        return {
            "schema_version": "chatroom.version_audit.v1",
            "semantic": bool(semantic),
            "room_count": len(rooms),
            "needs_work_count": sum(int(room.get("needs_work_count", 0) or 0) for room in rooms),
            "rooms": rooms,
        }

    def update_message_versions(
        self,
        chat_ref: str | Path,
        message_id: int,
        versions: dict,
        *,
        prepared_by: str = "Codex",
        semantic_prepared: bool = True,
        compile_after: bool = True,
        force_stale_lock: bool = False,
    ) -> dict:
        visible_path = self.resolve_chat_ref(chat_ref)
        clean_message_id = int(message_id)
        if clean_message_id <= 0:
            raise ValueError("message_id must be positive.")
        clean_versions = self._normalize_version_update(versions)
        with self.chat_lock(visible_path, force_stale=force_stale_lock):
            state = self.load_state(visible_path)
            message_path = self.paths.messages_dir(visible_path) / f"{clean_message_id:06d}.json"
            parsed = load_json(message_path)
            if not isinstance(parsed, dict):
                raise ValueError(f"Message file must be a JSON object: {message_path}")
            if parsed.get("chat_id") != state.get("chat_id"):
                raise ValueError("Message chat_id does not match state chat_id.")
            message_text = str(parsed.get("message", "") or "")
            parsed["char_count"] = text_char_count(message_text)
            parsed["versions"] = clean_versions
            parsed["version_prep"] = version_prep_record(
                message_text,
                clean_versions,
                prepared_by=prepared_by,
                semantic_prepared=semantic_prepared,
            )
            report = self._message_version_report(parsed, message_path)
            if not report["structural_ready"]:
                raise ValueError(f"Invalid message version bundle: {report['issues']}")
            write_json_atomic(message_path, parsed)
            if compile_after:
                return self._compile_visible(visible_path, state=state)
            return self.load_chat(visible_path)

    def load_consumer_state(self, chat_ref: str | Path, consumer_id: str) -> dict:
        visible_path = self.resolve_chat_ref(chat_ref)
        state = self.load_state(visible_path)
        return self._load_consumer_state_if_exists(visible_path, consumer_id) or self._default_consumer_state(
            state,
            consumer_id,
        )

    def render_consumer_lens(
        self,
        chat_ref: str | Path,
        consumer_id: str,
        *,
        threshold_chars: int | None = None,
        force_stale_lock: bool = False,
    ) -> dict:
        visible_path = self.resolve_chat_ref(chat_ref)
        clean_consumer = str(consumer_id or "").strip()
        if not clean_consumer:
            raise ValueError("consumer_id is required.")
        with self.chat_lock(visible_path, force_stale=force_stale_lock):
            state = self.load_state(visible_path)
            timestamp = now_timestamp()
            messages = self._apply_compile_policy(state, self.load_messages(visible_path))
            consumer_state = self._load_consumer_state_if_exists(visible_path, clean_consumer) or self._default_consumer_state(
                state,
                clean_consumer,
                threshold_chars=threshold_chars,
                timestamp=timestamp,
            )
            threshold = int(threshold_chars or consumer_state.get("threshold_chars", config.DEFAULT_CONSUMER_THRESHOLD_CHARS) or config.DEFAULT_CONSUMER_THRESHOLD_CHARS)

            def rendered_count(selected: dict[str, int]) -> int:
                selected_messages = render_selected_messages(messages, selected)
                payload = self._build_compiled_payload(
                    state,
                    selected_messages,
                    timestamp,
                    canonical_last_message_id=int(state.get("last_message_id", 0) or 0),
                )
                payload["consumer_id"] = clean_consumer
                return stable_json_char_count(payload)

            fit = fit_selected_versions(
                messages,
                consumer_state.get("selected_versions", {}),
                threshold,
                rendered_count,
            )
            selected_messages = render_selected_messages(messages, fit["selected_versions"])
            payload = self._build_compiled_payload(
                state,
                selected_messages,
                timestamp,
                canonical_last_message_id=int(state.get("last_message_id", 0) or 0),
            )
            payload["consumer_id"] = clean_consumer
            payload["consumer_compile"] = {
                "status": "exhausted" if fit["exhausted"] else "valid",
                "threshold_chars": fit["threshold_chars"],
                "compiled_chars": stable_json_char_count(payload),
                "remaining_margin_chars": fit["remaining_margin_chars"],
                "highest_version_used": fit["highest_version_used"],
            }
            consumer_state["status"] = "removed_from_room" if fit["exhausted"] else "active"
            consumer_state["threshold_chars"] = fit["threshold_chars"]
            consumer_state["selected_versions"] = fit["selected_versions"]
            consumer_state["last_compile"] = dict(payload["consumer_compile"])
            consumer_state["last_compile"]["compiled_at"] = timestamp
            consumer_state["updated_at"] = timestamp
            if fit["exhausted"]:
                consumer_state["removal"] = {
                    "reason": "compiled_output_exceeded_threshold_after_all_versions_reached_L9",
                    "removed_at": timestamp,
                    "last_compiled_chars": int(payload["consumer_compile"]["compiled_chars"]),
                }
                state["participants"] = [
                    item for item in clean_unique_strings(state.get("participants", [])) if item != clean_consumer
                ]
                state["updated_at"] = timestamp
            self._save_consumer_state(visible_path, consumer_state)
            if fit["exhausted"]:
                write_json_atomic(self.paths.state_path(visible_path), state)
            return payload

    def archive_chat(self, chat_ref: str | Path, *, force_stale_lock: bool = False) -> dict:
        return self._move_chat(chat_ref, target_status="archived", force_stale_lock=force_stale_lock)

    def restore_chat(self, chat_ref: str | Path, *, force_stale_lock: bool = False) -> dict:
        return self._move_chat(chat_ref, target_status="active", force_stale_lock=force_stale_lock)

    def create_room_operation(
        self,
        title: str,
        *,
        folder: str | None = None,
        participants: list[str] | None = None,
        requested_by: str = "Codex",
        apply: bool = False,
    ) -> dict:
        clean_title = str(title or "").strip()
        if not clean_title:
            raise ValueError("Chat title is required.")
        clean_participants = clean_unique_strings(participants or [])
        visible_path = self.paths.unique_visible_path(clean_title, folder, create_parent=False)
        chat_paths = self.paths.chat_paths(visible_path)
        operation_id = new_operation_id("create-room")
        report = self._operation_report(
            operation_id=operation_id,
            operation_type="create-room",
            requested_by=requested_by,
            apply=apply,
            source={},
            target={
                "chat_title": clean_title,
                "status": "active",
                "visible_path": str(visible_path),
                "state_path": str(chat_paths.state_path),
                "messages_dir": str(chat_paths.messages_dir),
                "participants": clean_participants,
            },
            actions=[
                {
                    "type": "create-room",
                    "status": "would_create" if not apply else "pending",
                    "visible_path": str(visible_path),
                    "companion_dir": str(chat_paths.companion_dir),
                }
            ],
        )
        if not apply:
            return report

        created = self.create_chat(clean_title, folder=folder, participants=clean_participants)
        state = created["state"]
        report["target"].update(
            {
                "chat_id": state["chat_id"],
                "visible_path": created["visible_path"],
                "state_path": created["state_path"],
                "messages_dir": created["messages_dir"],
            }
        )
        report["actions"][0]["status"] = "created"
        report["actions"][0]["chat_id"] = state["chat_id"]
        report["applied"] = True
        report["verification"] = self._verification_summary()
        self._append_operation_report(report)
        return report

    def archive_room_operation(
        self,
        chat_ref: str | Path,
        *,
        requested_by: str = "Codex",
        apply: bool = False,
        force_stale_lock: bool = False,
    ) -> dict:
        return self._move_room_operation(
            chat_ref,
            target_status="archived",
            operation_type="archive-room",
            requested_by=requested_by,
            apply=apply,
            force_stale_lock=force_stale_lock,
        )

    def restore_room_operation(
        self,
        chat_ref: str | Path,
        *,
        requested_by: str = "Codex",
        apply: bool = False,
        force_stale_lock: bool = False,
    ) -> dict:
        return self._move_room_operation(
            chat_ref,
            target_status="active",
            operation_type="restore-room",
            requested_by=requested_by,
            apply=apply,
            force_stale_lock=force_stale_lock,
        )

    def place_message_operation(
        self,
        source_chat_ref: str | Path,
        source_message_id: int,
        target_chat_ref: str | Path,
        *,
        placement_reason: str,
        content_mode: str = "full_copy",
        requested_by: str = "Codex",
        apply: bool = False,
        force_stale_lock: bool = False,
    ) -> dict:
        return self._placement_operation(
            "place-message",
            source_chat_ref,
            [source_message_id],
            target_chat_ref,
            placement_reason=placement_reason,
            content_mode=content_mode,
            requested_by=requested_by,
            apply=apply,
            allow_duplicate=False,
            force_stale_lock=force_stale_lock,
        )

    def duplicate_message_operation(
        self,
        source_chat_ref: str | Path,
        source_message_id: int,
        target_chat_ref: str | Path,
        *,
        placement_reason: str,
        content_mode: str = "full_copy",
        requested_by: str = "Codex",
        apply: bool = False,
        force_stale_lock: bool = False,
    ) -> dict:
        return self._placement_operation(
            "duplicate-message",
            source_chat_ref,
            [source_message_id],
            target_chat_ref,
            placement_reason=placement_reason,
            content_mode=content_mode,
            requested_by=requested_by,
            apply=apply,
            allow_duplicate=True,
            force_stale_lock=force_stale_lock,
        )

    def place_range_operation(
        self,
        source_chat_ref: str | Path,
        start_message_id: int,
        end_message_id: int,
        target_chat_ref: str | Path,
        *,
        placement_reason: str,
        content_mode: str = "full_copy",
        requested_by: str = "Codex",
        apply: bool = False,
        force_stale_lock: bool = False,
    ) -> dict:
        start_id = int(start_message_id)
        end_id = int(end_message_id)
        if start_id <= 0 or end_id <= 0 or end_id < start_id:
            raise ValueError("Range must use positive start/end ids with end >= start.")
        return self._placement_operation(
            "place-range",
            source_chat_ref,
            list(range(start_id, end_id + 1)),
            target_chat_ref,
            placement_reason=placement_reason,
            content_mode=content_mode,
            requested_by=requested_by,
            apply=apply,
            allow_duplicate=False,
            force_stale_lock=force_stale_lock,
        )

    def duplicate_range_operation(
        self,
        source_chat_ref: str | Path,
        start_message_id: int,
        end_message_id: int,
        target_chat_ref: str | Path,
        *,
        placement_reason: str,
        content_mode: str = "full_copy",
        requested_by: str = "Codex",
        apply: bool = False,
        force_stale_lock: bool = False,
    ) -> dict:
        start_id = int(start_message_id)
        end_id = int(end_message_id)
        if start_id <= 0 or end_id <= 0 or end_id < start_id:
            raise ValueError("Range must use positive start/end ids with end >= start.")
        return self._placement_operation(
            "duplicate-range",
            source_chat_ref,
            list(range(start_id, end_id + 1)),
            target_chat_ref,
            placement_reason=placement_reason,
            content_mode=content_mode,
            requested_by=requested_by,
            apply=apply,
            allow_duplicate=True,
            force_stale_lock=force_stale_lock,
        )

    def apply_compile_policy_operation(
        self,
        chat_ref: str | Path,
        message_ids: list[int],
        *,
        mode: str,
        standin_message: str | None = None,
        requested_by: str = "Codex",
        apply: bool = False,
        force_stale_lock: bool = False,
    ) -> dict:
        clean_ids = clean_message_ids(message_ids)
        clean_mode = str(mode or "").strip().lower()
        if clean_mode not in {"detailed-standin", "short-standin", "no-standin"}:
            raise ValueError(f"Unsupported compile-policy operation mode: {mode}")
        clean_standin_message = str(standin_message or "").strip()
        if clean_mode in {"detailed-standin", "short-standin"} and not clean_standin_message:
            raise ValueError("A stand-in message is required for stand-in compile-policy modes.")

        visible_path = self.resolve_chat_ref(chat_ref)
        state = self.load_state(visible_path)
        self._assert_message_ids_exist(visible_path, clean_ids)
        operation_id = new_operation_id("compile-policy")
        action_type = "exclude-no-standin" if clean_mode == "no-standin" else f"exclude-{clean_mode}"
        report = self._operation_report(
            operation_id=operation_id,
            operation_type="compile-policy",
            requested_by=requested_by,
            apply=apply,
            source={
                "chat_id": state["chat_id"],
                "chat_title": state.get("chat_title", ""),
                "visible_path": str(visible_path),
                "message_ids": clean_ids,
            },
            target={
                "chat_id": state["chat_id"],
                "chat_title": state.get("chat_title", ""),
                "visible_path": str(visible_path),
            },
            actions=[
                {
                    "type": action_type,
                    "status": "would_apply" if not apply else "pending",
                    "message_ids": clean_ids,
                    "canonical_messages_preserved": True,
                }
            ],
            compile_policy={
                "mode": clean_mode,
                "message_ids": clean_ids,
                "standin_message": clean_standin_message if clean_mode != "no-standin" else "",
            },
        )
        if not apply:
            return report

        if clean_mode == "no-standin":
            result = self.exclude_messages(
                visible_path,
                clean_ids,
                compile_after=True,
                force_stale_lock=force_stale_lock,
            )
        else:
            result = self.add_standin(
                visible_path,
                clean_ids,
                clean_standin_message,
                insert_after_message_id=max(clean_ids),
                standin_id=f"standin_{operation_id}",
                compile_after=True,
                force_stale_lock=force_stale_lock,
            )
        report["actions"][0]["status"] = "applied"
        report["applied"] = True
        report["compile_policy"]["result"] = result["state"].get("compile_policy", {})
        report["verification"] = self._verification_summary()
        self._append_operation_report(report)
        return report

    def read_operation_log(self, *, limit: int | None = None) -> list[dict]:
        log_path = self.paths.operation_log_path
        if not log_path.exists():
            return []
        entries: list[dict] = []
        for line in log_path.read_text(encoding="utf-8").splitlines():
            clean = line.strip()
            if not clean:
                continue
            parsed = json.loads(clean)
            if isinstance(parsed, dict):
                entries.append(parsed)
        if limit is not None and limit >= 0:
            return entries[-limit:]
        return entries

    def latest_records(self, status: str = "active", *, source: str = "state") -> list[dict]:
        clean_source = str(source or "state").strip().lower()
        if clean_source == "messages":
            clean_source = "canonical"
        if clean_source not in {"state", "canonical"}:
            raise ValueError(f"Unsupported latest record source: {source}")

        records: list[dict] = []
        for visible_path in self.paths.iter_visible_paths(status):
            state_path = self.paths.state_path(visible_path)
            if clean_source == "canonical":
                fallback = self.latest_from_messages(visible_path)
                state = None
                state_last = None
                warnings: list[str] = []
                try:
                    state = self.load_state(visible_path)
                    state_last = int(state.get("last_message_id", 0) or 0)
                except Exception:
                    state = None
                chat_id = str(fallback.get("chat_id", "") or (state or {}).get("chat_id", "") or "")
                if not chat_id:
                    continue
                participants = clean_unique_strings((state or {}).get("participants", [])) if state else []
                last_message_id = int(fallback.get("last_message_id", 0) or 0)
                if state_last is not None and state_last != last_message_id:
                    warnings.append("state/cache looked stale; unread count used canonical messages; no action needed")
                records.append(
                    {
                        "chat_id": chat_id,
                        "chat_title": str((state or {}).get("chat_title", "") or visible_path.stem),
                        "status": str((state or {}).get("status", "") or self.paths.infer_status(visible_path)),
                        "visible_path": visible_path,
                        "state_path": state_path,
                        "last_message_id": last_message_id,
                        "last_message_at": str(fallback.get("last_message_at", "") or (state or {}).get("last_message_at", "") or ""),
                        "participants": participants,
                        "participants_known": state is not None,
                        "warnings": warnings,
                    }
                )
                continue

            try:
                state = self.load_state(visible_path)
                records.append(
                    {
                        "chat_id": state["chat_id"],
                        "chat_title": state.get("chat_title", visible_path.stem),
                        "status": state.get("status", self.paths.infer_status(visible_path)),
                        "visible_path": visible_path,
                        "state_path": state_path,
                        "last_message_id": int(state.get("last_message_id", 0) or 0),
                        "last_message_at": str(state.get("last_message_at", "") or ""),
                        "participants": clean_unique_strings(state.get("participants", [])),
                        "participants_known": True,
                        "warnings": [],
                    }
                )
                continue
            except Exception:
                pass
            fallback = self.latest_from_messages(visible_path)
            if fallback["chat_id"]:
                records.append(
                    {
                        "chat_id": fallback["chat_id"],
                        "chat_title": visible_path.stem,
                        "status": self.paths.infer_status(visible_path),
                        "visible_path": visible_path,
                        "state_path": state_path,
                        "last_message_id": fallback["last_message_id"],
                        "last_message_at": fallback.get("last_message_at", ""),
                        "participants": [],
                        "participants_known": False,
                        "warnings": ["state unreadable; unread count used canonical messages; no action needed"],
                    }
                )
        return records

    def latest_from_messages(self, chat_ref: str | Path) -> dict:
        visible_path = self._visible_from_path_ref(chat_ref)
        chat_id = ""
        highest = 0
        latest_timestamp = ""
        for path in self.message_file_paths(visible_path):
            try:
                parsed = load_json(path)
            except Exception:
                continue
            if isinstance(parsed, dict):
                chat_id = str(parsed.get("chat_id", "") or chat_id)
                try:
                    highest = max(highest, int(parsed.get("message_id", 0) or 0))
                except Exception:
                    pass
                latest_timestamp = str(parsed.get("timestamp", "") or latest_timestamp)
        return {"chat_id": chat_id, "last_message_id": highest, "last_message_at": latest_timestamp}

    def highest_message_id(self, chat_ref: str | Path) -> int:
        return int(self.latest_from_messages(chat_ref).get("last_message_id", 0) or 0)

    def render_chat_lens(self, chat_ref: str | Path, *, source: str = "canonical") -> dict:
        clean_source = str(source or "canonical").strip().lower()
        if clean_source == "messages":
            clean_source = "canonical"
        if clean_source != "canonical":
            raise ValueError(f"Unsupported chat lens source: {source}")

        visible_path = self.resolve_chat_ref(chat_ref)
        state = self.load_state(visible_path)
        messages = self.load_messages(visible_path)
        highest = max([int(message.get("message_id", 0) or 0) for message in messages], default=0)
        warnings: list[str] = []
        try:
            state_last = int(state.get("last_message_id", 0) or 0)
        except Exception:
            state_last = 0
        if state_last != highest:
            warnings.append("state/cache looked stale; rendered from canonical messages; nothing to fix")

        state_for_lens = dict(state)
        state_for_lens["chat_file"] = visible_path.name
        state_for_lens["status"] = self.paths.infer_status(visible_path)
        state_for_lens["compile_policy"] = normalize_compile_policy(state_for_lens.get("compile_policy", {}))
        shaped_messages = self._apply_compile_policy(state_for_lens, messages)
        return {
            "schema_version": "chatroom.lens.v1",
            "chat_id": state_for_lens["chat_id"],
            "chat_title": state_for_lens.get("chat_title", ""),
            "status": state_for_lens.get("status", "active"),
            "lens_source": "canonical",
            "visible_cache_path": str(visible_path),
            "state_path": str(self.paths.state_path(visible_path)),
            "messages_dir": str(self.paths.messages_dir(visible_path)),
            "last_message_id": highest,
            "message_count": len(shaped_messages),
            "raw_message_count": len(messages),
            "compile_policy": state_for_lens["compile_policy"],
            "messages": shaped_messages,
            "warnings": warnings,
        }

    def verify(self, root: str | Path | None = None) -> dict:
        target_paths = ChatroomPaths(root) if root is not None else self.paths
        issues: list[VerificationIssue] = []
        chats: list[dict] = []

        for visible_path in target_paths.iter_visible_paths(None):
            chat_paths = target_paths.chat_paths(visible_path)
            if not chat_paths.companion_dir.exists():
                issues.append(VerificationIssue("error", "missing_companion", "Missing hidden companion folder.", chat_paths.companion_dir))
                continue
            if not chat_paths.state_path.exists():
                issues.append(VerificationIssue("error", "missing_state", "Missing state.json.", chat_paths.state_path))
                continue

            state = None
            try:
                state = load_json(chat_paths.state_path)
                if not isinstance(state, dict):
                    raise ValueError("State root is not an object.")
                if state.get("schema_version") != config.STATE_SCHEMA_VERSION:
                    raise ValueError(f"Unsupported state schema: {state.get('schema_version')}")
                chat_id = str(state.get("chat_id", "") or "")
                if not chat_id.startswith("chat_"):
                    raise ValueError("State missing chat_id.")
            except Exception as exc:
                issues.append(VerificationIssue("error", "state_parse_failed", str(exc), chat_paths.state_path))
                fallback = self.latest_from_messages(visible_path)
                chats.append(
                    {
                        "visible_path": str(visible_path),
                        "state_path": str(chat_paths.state_path),
                        "chat_id": fallback.get("chat_id", ""),
                        "state_last_message_id": None,
                        "highest_message_id": fallback.get("last_message_id", 0),
                        "compiled_last_message_id": None,
                    }
                )
                continue

            messages = []
            message_chat_ids: set[str] = set()
            highest = 0
            for message_path in self.message_file_paths(visible_path):
                try:
                    parsed = load_json(message_path)
                    if not isinstance(parsed, dict):
                        raise ValueError("Message root is not an object.")
                    if parsed.get("schema_version") != config.MESSAGE_SCHEMA_VERSION:
                        raise ValueError(f"Unsupported message schema: {parsed.get('schema_version')}")
                    if parsed.get("chat_id") != state.get("chat_id"):
                        raise ValueError("Message chat_id does not match state chat_id.")
                    message_id = int(parsed.get("message_id", 0) or 0)
                    highest = max(highest, message_id)
                    message_chat_ids.add(str(parsed.get("chat_id", "") or ""))
                    version_report = self._message_version_report(parsed, message_path)
                    if version_report["has_version_metadata"] and not version_report["structural_ready"]:
                        issues.append(
                            VerificationIssue(
                                "error",
                                "message_version_invalid",
                                "; ".join(version_report["issues"]),
                                message_path,
                            )
                        )
                    messages.append(parsed)
                except Exception as exc:
                    issues.append(VerificationIssue("error", "message_parse_failed", str(exc), message_path))

            state_last = int(state.get("last_message_id", 0) or 0)
            if highest != state_last:
                issues.append(
                    VerificationIssue(
                        "error",
                        "state_message_mismatch",
                        f"state last_message_id {state_last} does not match highest message id {highest}.",
                        chat_paths.state_path,
                    )
                )

            compiled_last = None
            try:
                compiled = load_json(visible_path)
                if not isinstance(compiled, dict):
                    raise ValueError("Compiled chat root is not an object.")
                if compiled.get("schema_version") != config.COMPILED_SCHEMA_VERSION:
                    raise ValueError(f"Unsupported compiled schema: {compiled.get('schema_version')}")
                compiled_last = int(compiled.get("last_message_id", 0) or 0)
                if compiled.get("chat_id") != state.get("chat_id"):
                    raise ValueError("Compiled chat_id does not match state chat_id.")
                if compiled_last != highest:
                    issues.append(
                        VerificationIssue(
                            "warning",
                            "compiled_stale",
                            f"compiled last_message_id {compiled_last} does not match highest message id {highest}.",
                            visible_path,
                        )
                    )
            except Exception as exc:
                issues.append(VerificationIssue("error", "compiled_parse_failed", str(exc), visible_path))

            consumer_count = 0
            if chat_paths.consumers_dir.exists():
                for consumer_path in sorted(chat_paths.consumers_dir.glob("*.json")):
                    try:
                        consumer_state = load_json(consumer_path)
                        if not isinstance(consumer_state, dict):
                            raise ValueError("Consumer state root is not an object.")
                        if consumer_state.get("schema_version") != config.CONSUMER_STATE_SCHEMA_VERSION:
                            raise ValueError(f"Unsupported consumer state schema: {consumer_state.get('schema_version')}")
                        if consumer_state.get("chat_id") != state.get("chat_id"):
                            raise ValueError("Consumer state chat_id does not match state chat_id.")
                        threshold_chars = consumer_state.get("threshold_chars")
                        if not isinstance(threshold_chars, int) or threshold_chars <= 0:
                            raise ValueError("Consumer threshold_chars must be a positive integer.")
                        selected_versions = consumer_state.get("selected_versions", {})
                        if not isinstance(selected_versions, dict):
                            raise ValueError("Consumer selected_versions must be an object.")
                        consumer_count += 1
                    except Exception as exc:
                        issues.append(VerificationIssue("error", "consumer_state_invalid", str(exc), consumer_path))

            chats.append(
                {
                    "chat_id": state.get("chat_id", ""),
                    "chat_title": state.get("chat_title", visible_path.stem),
                    "status": state.get("status", target_paths.infer_status(visible_path)),
                    "visible_path": str(visible_path),
                    "state_path": str(chat_paths.state_path),
                    "state_last_message_id": state_last,
                    "highest_message_id": highest,
                    "compiled_last_message_id": compiled_last,
                    "message_count": len(messages),
                    "message_chat_ids": sorted(message_chat_ids),
                    "consumer_count": consumer_count,
                }
            )

        issue_dicts = [
            {
                "severity": issue.severity,
                "code": issue.code,
                "message": issue.message,
                "path": str(issue.path) if issue.path else "",
            }
            for issue in issues
        ]
        error_count = sum(1 for issue in issues if issue.severity == "error")
        return {"ok": error_count == 0, "error_count": error_count, "issues": issue_dicts, "chats": chats}

    @contextmanager
    def chat_lock(
        self,
        chat_ref: str | Path,
        *,
        timeout_seconds: int = config.DEFAULT_LOCK_TIMEOUT_SECONDS,
        force_stale: bool = False,
    ) -> Iterator[None]:
        visible_path = self._visible_from_path_ref(chat_ref)
        lock_path = self.paths.companion_dir(visible_path) / config.LOCK_FILE_NAME
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "pid": os.getpid(),
            "created_at": now_timestamp(),
            "visible_path": str(visible_path),
        }
        acquired = False
        try:
            while True:
                try:
                    fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    with os.fdopen(fd, "w", encoding="utf-8") as handle:
                        handle.write(str(payload))
                    acquired = True
                    break
                except FileExistsError:
                    age = time.time() - lock_path.stat().st_mtime
                    if force_stale and age > timeout_seconds:
                        self._release_lock(lock_path)
                        continue
                    raise RuntimeError(f"Chat write lock exists: {lock_path}")
            yield
        finally:
            if acquired:
                self._release_lock(lock_path)

    def _release_lock(self, lock_path: Path) -> None:
        try:
            lock_path.unlink(missing_ok=True)
            return
        except FileNotFoundError:
            return
        except PermissionError as exc:
            delete_error = exc
        except OSError as exc:
            if exc.errno not in {errno.EACCES, errno.EPERM}:
                raise
            delete_error = exc

        released_path = self._next_released_lock_path(lock_path)
        try:
            lock_path.rename(released_path)
        except FileNotFoundError:
            return
        except OSError as rename_error:
            raise RuntimeError(
                f"Could not release chat write lock: {lock_path}. "
                f"Delete failed with {delete_error!r}; rename failed with {rename_error!r}."
            ) from rename_error

    def _next_released_lock_path(self, lock_path: Path) -> Path:
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        base_name = f"{lock_path.name}.released.{timestamp}.{os.getpid()}"
        for index in range(100):
            suffix = "" if index == 0 else f".{index}"
            candidate = lock_path.with_name(f"{base_name}{suffix}")
            if not candidate.exists():
                return candidate
        return lock_path.with_name(f"{base_name}.{uuid.uuid4().hex}")

    def _assert_message_ids_exist(self, visible_path: Path, message_ids: list[int]) -> None:
        existing_ids = {int(message.get("message_id", 0) or 0) for message in self.load_messages(visible_path)}
        missing_ids = [message_id for message_id in message_ids if message_id not in existing_ids]
        if missing_ids:
            raise ValueError(f"Message id(s) do not exist in chat: {missing_ids}")

    def _consumer_state_path(self, visible_path: Path, consumer_id: str) -> Path:
        clean_stem = sanitize_file_stem(consumer_id) or "consumer"
        return self.paths.consumers_dir(visible_path) / f"{clean_stem}.json"

    def _default_consumer_state(
        self,
        state: dict,
        consumer_id: str,
        *,
        threshold_chars: int | None = None,
        timestamp: str | None = None,
    ) -> dict:
        created_at = timestamp or now_timestamp()
        return {
            "schema_version": config.CONSUMER_STATE_SCHEMA_VERSION,
            "chat_id": state["chat_id"],
            "consumer_id": str(consumer_id or "").strip(),
            "status": "active",
            "threshold_chars": int(threshold_chars or config.DEFAULT_CONSUMER_THRESHOLD_CHARS),
            "selected_versions": {},
            "last_compile": {},
            "removal": {},
            "created_at": created_at,
            "updated_at": created_at,
        }

    def _load_consumer_state_if_exists(self, visible_path: Path, consumer_id: str) -> dict | None:
        path = self._consumer_state_path(visible_path, consumer_id)
        if not path.exists():
            return None
        parsed = load_json(path)
        if not isinstance(parsed, dict):
            raise ValueError(f"Consumer state must be a JSON object: {path}")
        if parsed.get("schema_version") != config.CONSUMER_STATE_SCHEMA_VERSION:
            raise ValueError(f"Unsupported consumer state schema at {path}: {parsed.get('schema_version')}")
        return parsed

    def _save_consumer_state(self, visible_path: Path, consumer_state: dict) -> None:
        consumer_id = str(consumer_state.get("consumer_id", "") or "").strip()
        if not consumer_id:
            raise ValueError("consumer_state missing consumer_id.")
        path = self._consumer_state_path(visible_path, consumer_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(path, consumer_state)

    def _normalize_version_update(self, versions: dict) -> dict[str, dict]:
        if not isinstance(versions, dict):
            raise ValueError("versions must be a JSON object keyed by level 0-9.")
        clean_versions: dict[str, dict] = {}
        for level in range(config.MESSAGE_VERSION_MIN_LEVEL, config.MESSAGE_VERSION_MAX_LEVEL + 1):
            key = str(level)
            raw_record = versions.get(key)
            if not isinstance(raw_record, dict):
                raise ValueError(f"versions missing level {key}.")
            text = str(raw_record.get("message", "") or "")
            clean_versions[key] = {
                "message": text,
                "char_count": int(raw_record.get("char_count", text_char_count(text)) or 0),
            }
        return clean_versions

    def _message_version_report(self, parsed: dict, message_path: Path) -> dict:
        issues: list[str] = []
        message_id = int(parsed.get("message_id", 0) or 0)
        message = str(parsed.get("message", "") or "")
        has_version_metadata = any(key in parsed for key in ("char_count", "versions", "version_prep"))

        char_count = parsed.get("char_count")
        if not isinstance(char_count, int):
            issues.append("top-level char_count missing or not an integer")
        elif char_count != text_char_count(message):
            issues.append("top-level char_count does not match message text")

        versions = parsed.get("versions")
        if not isinstance(versions, dict):
            issues.append("versions missing or not an object")
            versions = {}

        for level in range(config.MESSAGE_VERSION_MIN_LEVEL, config.MESSAGE_VERSION_MAX_LEVEL + 1):
            key = str(level)
            version = versions.get(key) if isinstance(versions, dict) else None
            if not isinstance(version, dict):
                issues.append(f"version {key} missing or not an object")
                continue
            version_text = str(version.get("message", "") or "")
            version_count = version.get("char_count")
            if not isinstance(version_count, int):
                issues.append(f"version {key} char_count missing or not an integer")
            elif version_count != text_char_count(version_text):
                issues.append(f"version {key} char_count does not match message text")

        version_zero = versions.get("0") if isinstance(versions, dict) else None
        if isinstance(version_zero, dict) and str(version_zero.get("message", "") or "") != message:
            issues.append("version 0 message does not match canonical message")

        prep = parsed.get("version_prep")
        semantic_prepared = False
        if isinstance(prep, dict):
            semantic_prepared = bool(prep.get("semantic_prepared"))
            if prep.get("source_hash") != text_hash(message):
                issues.append("version_prep source_hash does not match canonical message")
            if isinstance(versions, dict) and prep.get("bundle_hash") != bundle_hash(versions):
                issues.append("version_prep bundle_hash does not match versions")
        elif has_version_metadata:
            issues.append("version_prep missing or not an object")

        structural_ready = not issues and has_version_metadata
        return {
            "message_id": message_id,
            "message_path": str(message_path),
            "has_version_metadata": has_version_metadata,
            "structural_ready": structural_ready,
            "semantic_prepared": semantic_prepared if structural_ready else False,
            "prepared_by": str(prep.get("prepared_by", "") or "") if isinstance(prep, dict) else "",
            "prepared_at": str(prep.get("prepared_at", "") or "") if isinstance(prep, dict) else "",
            "issues": issues,
        }

    def _write_state_after_policy_change(self, visible_path: Path, state: dict, *, compile_after: bool) -> dict:
        if compile_after:
            return self._compile_visible(visible_path, state=state)
        compile_info = state.get("compile", {})
        if not isinstance(compile_info, dict):
            compile_info = {}
        state["compile"] = {
            "status": "dirty",
            "last_compiled_message_id": int(compile_info.get("last_compiled_message_id", 0) or 0),
            "last_compiled_at": str(compile_info.get("last_compiled_at", "") or ""),
            "error": "",
        }
        write_json_atomic(self.paths.state_path(visible_path), state)
        return self.load_chat(visible_path)

    def _compile_visible(self, visible_path: Path, *, state: dict | None = None, timestamp: str | None = None) -> dict:
        if state is None:
            state = self.load_state(visible_path)
        compile_timestamp = timestamp or now_timestamp()
        messages = self.load_messages(visible_path)
        highest = max([int(message.get("message_id", 0) or 0) for message in messages], default=0)
        if highest:
            state["last_message_id"] = highest
            state["last_message_at"] = str(messages[-1].get("timestamp", "") or state.get("last_message_at", ""))
        state["chat_file"] = visible_path.name
        state["status"] = self.paths.infer_status(visible_path)
        state["compile_policy"] = normalize_compile_policy(state.get("compile_policy", {}))
        state["compile"] = {
            "status": "clean",
            "last_compiled_message_id": highest,
            "last_compiled_at": compile_timestamp,
            "error": "",
        }
        compiled_messages = self._apply_compile_policy(state, messages)
        compiled = self._build_compiled_payload(
            state,
            compiled_messages,
            compile_timestamp,
            canonical_last_message_id=highest,
        )
        state["compile"]["compiled_chars"] = int(compiled.get("compiled_chars", 0) or 0)
        state["last_full_compile"] = {
            "compiled_chars": int(compiled.get("compiled_chars", 0) or 0),
            "message_count": len(compiled_messages),
            "compiled_at": compile_timestamp,
        }
        write_json_atomic(visible_path, compiled)
        write_json_atomic(self.paths.state_path(visible_path), state)
        return {"state": state, "messages": messages, "visible_path": str(visible_path), "state_path": str(self.paths.state_path(visible_path))}

    def _apply_compile_policy(self, state: dict, messages: list[dict]) -> list[dict]:
        policy = normalize_compile_policy(state.get("compile_policy", {}))
        excluded_ids = set(policy["excluded_message_ids"])
        standins_by_insert_after: dict[int, list[dict]] = {}
        for standin in policy["standins"]:
            insert_after = int(standin.get("insert_after_message_id", 0) or 0)
            standins_by_insert_after.setdefault(insert_after, []).append(standin)

        compiled_messages: list[dict] = []
        for standin in standins_by_insert_after.get(0, []):
            compiled_messages.append(self._compiled_standin_message(state, standin))

        for message in messages:
            message_id = int(message.get("message_id", 0) or 0)
            if message_id not in excluded_ids:
                compiled_messages.append(message)
            for standin in standins_by_insert_after.get(message_id, []):
                compiled_messages.append(self._compiled_standin_message(state, standin))
        return compiled_messages

    def _compiled_standin_message(self, state: dict, standin: dict) -> dict:
        standin_id = str(standin.get("standin_id", "") or f"standin_{uuid.uuid4().hex}")
        return {
            "schema_version": config.STANDIN_SCHEMA_VERSION,
            "chat_id": state["chat_id"],
            "message_id": f"standin:{standin_id}",
            "speaker": str(standin.get("speaker", "") or "System").strip() or "System",
            "timestamp": str(standin.get("timestamp", "") or "").strip(),
            "kind": clean_kind(str(standin.get("kind", "") or "system")),
            "mentions": clean_unique_strings(standin.get("mentions", [])),
            "message": str(standin.get("message", "") or ""),
            "char_count": text_char_count(standin.get("message", "")),
            "synthetic": True,
            "standin_id": standin_id,
            "replaces_message_ids": clean_message_ids(standin.get("replaces_message_ids", [])),
            "insert_after_message_id": int(standin.get("insert_after_message_id", 0) or 0),
        }

    def _build_compiled_payload(
        self,
        state: dict,
        messages: list[dict],
        timestamp: str,
        *,
        canonical_last_message_id: int | None = None,
    ) -> dict:
        last_message_id = (
            int(canonical_last_message_id)
            if canonical_last_message_id is not None
            else max([int(message.get("message_id", 0) or 0) for message in messages if isinstance(message.get("message_id", 0), int)], default=0)
        )
        payload = {
            "schema_version": config.COMPILED_SCHEMA_VERSION,
            "chat_id": state["chat_id"],
            "chat_title": state.get("chat_title", ""),
            "status": state.get("status", "active"),
            "compiled_at": timestamp,
            "last_message_id": last_message_id,
            "compile_policy": normalize_compile_policy(state.get("compile_policy", {})),
            "messages": messages,
        }
        payload["compiled_chars"] = 0
        for _ in range(4):
            next_count = stable_json_char_count(payload)
            if payload["compiled_chars"] == next_count:
                break
            payload["compiled_chars"] = next_count
        return payload

    def _operation_report(
        self,
        *,
        operation_id: str,
        operation_type: str,
        requested_by: str,
        apply: bool,
        source: dict,
        target: dict,
        actions: list[dict],
        provenance: dict | None = None,
        compile_policy: dict | None = None,
        warnings: list[str] | None = None,
    ) -> dict:
        return {
            "schema_version": config.OPERATION_REPORT_SCHEMA_VERSION,
            "operation_id": operation_id,
            "operation_type": operation_type,
            "dry_run": not apply,
            "apply": bool(apply),
            "applied": False,
            "requested_by": str(requested_by or "").strip() or "Codex",
            "created_at": now_timestamp(),
            "source": source,
            "target": target,
            "actions": actions,
            "provenance": provenance or {},
            "compile_policy": compile_policy or {},
            "warnings": warnings or [],
            "verification": {},
        }

    def _verification_summary(self) -> dict:
        result = self.verify()
        return {
            "ok": bool(result.get("ok")),
            "error_count": int(result.get("error_count", 0) or 0),
            "issue_count": len(result.get("issues", [])) if isinstance(result.get("issues"), list) else 0,
        }

    def _append_operation_report(self, report: dict) -> None:
        if not report.get("applied"):
            return
        source = report.get("source", {}) if isinstance(report.get("source"), dict) else {}
        target = report.get("target", {}) if isinstance(report.get("target"), dict) else {}
        entry = {
            "schema_version": config.OPERATION_LOG_SCHEMA_VERSION,
            "operation_id": report.get("operation_id", ""),
            "operation_type": report.get("operation_type", ""),
            "timestamp": now_timestamp(),
            "applied_by": report.get("requested_by", ""),
            "requested_by": report.get("requested_by", ""),
            "source_chat_id": source.get("chat_id", ""),
            "source_message_ids": source.get("message_ids", []),
            "target_chat_id": target.get("chat_id", ""),
            "target_message_ids": target.get("target_message_ids", []),
            "compile_policy_changes": report.get("compile_policy", {}),
            "placement_metadata": report.get("provenance", {}).get("placement_metadata", []),
            "verification_summary": report.get("verification", {}),
            "warnings": report.get("warnings", []),
            "report": report,
        }
        append_jsonl(self.paths.operation_log_path, entry)

    def _move_room_operation(
        self,
        chat_ref: str | Path,
        *,
        target_status: str,
        operation_type: str,
        requested_by: str,
        apply: bool,
        force_stale_lock: bool,
    ) -> dict:
        visible_path = self.resolve_chat_ref(chat_ref)
        state = self.load_state(visible_path)
        source_status = self.paths.infer_status(visible_path)
        clean_target_status = normalize_status(target_status)
        source_root = self.paths.status_dir(source_status)
        target_root = self.paths.status_dir(clean_target_status)
        relative_path = visible_path.resolve().relative_to(source_root.resolve())
        target_visible = target_root / relative_path
        source_companion = self.paths.companion_dir(visible_path)
        target_companion = self.paths.companion_dir(target_visible)
        warnings: list[str] = []
        action_status = "would_move" if not apply else "pending"
        if source_status == clean_target_status:
            warnings.append(f"Chat is already {clean_target_status}; no move needed.")
            action_status = "noop"
        report = self._operation_report(
            operation_id=new_operation_id(operation_type),
            operation_type=operation_type,
            requested_by=requested_by,
            apply=apply,
            source={
                "chat_id": state["chat_id"],
                "chat_title": state.get("chat_title", ""),
                "status": source_status,
                "visible_path": str(visible_path),
                "companion_dir": str(source_companion),
            },
            target={
                "chat_id": state["chat_id"],
                "chat_title": state.get("chat_title", ""),
                "status": clean_target_status,
                "visible_path": str(target_visible),
                "companion_dir": str(target_companion),
            },
            actions=[
                {
                    "type": operation_type,
                    "status": action_status,
                    "visible_pair_preserved": True,
                }
            ],
            warnings=warnings,
        )
        if not apply or source_status == clean_target_status:
            return report

        moved = self._move_chat(visible_path, target_status=clean_target_status, force_stale_lock=force_stale_lock)
        report["target"].update(
            {
                "visible_path": moved["visible_path"],
                "state_path": moved["state_path"],
                "messages_dir": moved["messages_dir"],
            }
        )
        report["actions"][0]["status"] = "moved"
        report["applied"] = True
        report["verification"] = self._verification_summary()
        self._append_operation_report(report)
        return report

    def _placement_operation(
        self,
        operation_type: str,
        source_chat_ref: str | Path,
        source_message_ids: list[int],
        target_chat_ref: str | Path,
        *,
        placement_reason: str,
        content_mode: str,
        requested_by: str,
        apply: bool,
        allow_duplicate: bool,
        force_stale_lock: bool,
    ) -> dict:
        clean_message_ids_to_place = clean_message_ids(source_message_ids)
        clean_reason = str(placement_reason or "").strip()
        if not clean_reason:
            raise ValueError("Placement reason is required.")
        clean_mode = clean_content_mode(content_mode)

        source_visible = self.resolve_chat_ref(source_chat_ref)
        target_visible = self.resolve_chat_ref(target_chat_ref)
        source_state = self.load_state(source_visible)
        target_state = self.load_state(target_visible)
        source_messages = self.load_messages(source_visible)
        target_messages = self.load_messages(target_visible)
        source_by_id = {int(message.get("message_id", 0) or 0): message for message in source_messages}
        missing_ids = [message_id for message_id in clean_message_ids_to_place if message_id not in source_by_id]
        if missing_ids:
            raise ValueError(f"Source message id(s) do not exist in chat: {missing_ids}")

        operation_id = new_operation_id(operation_type)
        placed_at = now_timestamp()
        projected_next_id = max([int(message.get("message_id", 0) or 0) for message in target_messages], default=0) + 1
        warnings: list[str] = []
        actions: list[dict] = []
        placements: list[dict] = []
        provenance_entries: list[dict] = []

        for source_message_id in clean_message_ids_to_place:
            source_message = source_by_id[source_message_id]
            duplicate_ids = self._placement_duplicate_ids(
                target_messages,
                source_chat_id=source_state["chat_id"],
                source_message_id=source_message_id,
                placement_reason=clean_reason,
                content_mode=clean_mode,
            )
            metadata = clean_placement_metadata(
                {
                    "is_placement_copy": True,
                    "source_chat_id": source_state["chat_id"],
                    "source_chat_title": source_state.get("chat_title", ""),
                    "source_message_id": source_message_id,
                    "source_speaker": source_message.get("speaker", ""),
                    "source_timestamp": source_message.get("timestamp", ""),
                    "target_chat_id": target_state["chat_id"],
                    "target_chat_title": target_state.get("chat_title", ""),
                    "placement_reason": clean_reason,
                    "placed_by": requested_by,
                    "placed_at": placed_at,
                    "content_mode": clean_mode,
                    "operation_id": operation_id,
                }
            )
            if metadata is None:
                raise ValueError("Could not build placement metadata.")
            action = {
                "type": "place-message",
                "status": "would_place" if not apply else "pending",
                "source_message_id": source_message_id,
                "target_projected_message_id": projected_next_id,
                "speaker": source_message.get("speaker", ""),
                "kind": source_message.get("kind", "message"),
                "content_mode": clean_mode,
            }
            if duplicate_ids and not allow_duplicate:
                action["status"] = "skipped_duplicate"
                action["existing_target_message_ids"] = duplicate_ids
                warnings.append(
                    f"Source message {source_message_id} already appears in target as placement copy {duplicate_ids}."
                )
            else:
                placements.append({"source_message": source_message, "metadata": metadata, "action": action})
                provenance_entries.append(metadata)
                projected_next_id += 1
            actions.append(action)

        report = self._operation_report(
            operation_id=operation_id,
            operation_type=operation_type,
            requested_by=requested_by,
            apply=apply,
            source={
                "chat_id": source_state["chat_id"],
                "chat_title": source_state.get("chat_title", ""),
                "visible_path": str(source_visible),
                "message_ids": clean_message_ids_to_place,
            },
            target={
                "chat_id": target_state["chat_id"],
                "chat_title": target_state.get("chat_title", ""),
                "visible_path": str(target_visible),
                "target_message_ids": [],
            },
            actions=actions,
            provenance={"placement_metadata": provenance_entries},
            warnings=warnings,
        )
        if not apply:
            return report

        target_message_ids: list[int] = []
        for placement in placements:
            source_message = placement["source_message"]
            metadata = placement["metadata"]
            posted = self.post_message(
                target_visible,
                str(source_message.get("speaker", "") or "Unknown"),
                str(source_message.get("message", "") or ""),
                kind=str(source_message.get("kind", "") or "message"),
                mentions=clean_unique_strings(source_message.get("mentions", [])),
                placement_metadata=metadata,
                compile_after=True,
                force_stale_lock=force_stale_lock,
            )
            target_message_id = int(posted["state"].get("last_message_id", 0) or 0)
            target_message_ids.append(target_message_id)
            placement["action"]["status"] = "placed"
            placement["action"]["target_message_id"] = target_message_id
            metadata["target_message_id"] = target_message_id

        if target_message_ids:
            report["applied"] = True
            report["target"]["target_message_ids"] = target_message_ids
            report["provenance"]["placement_metadata"] = [placement["metadata"] for placement in placements]
            report["verification"] = self._verification_summary()
            self._append_operation_report(report)
        return report

    def _placement_duplicate_ids(
        self,
        target_messages: list[dict],
        *,
        source_chat_id: str,
        source_message_id: int,
        placement_reason: str,
        content_mode: str,
    ) -> list[int]:
        duplicate_ids: list[int] = []
        for message in target_messages:
            metadata = clean_placement_metadata(message.get("placement_metadata"))
            if not metadata:
                continue
            if metadata.get("source_chat_id") != source_chat_id:
                continue
            if int(metadata.get("source_message_id", 0) or 0) != int(source_message_id):
                continue
            if metadata.get("placement_reason") != placement_reason:
                continue
            if metadata.get("content_mode") != content_mode:
                continue
            duplicate_ids.append(int(message.get("message_id", 0) or 0))
        return duplicate_ids

    def _move_chat(self, chat_ref: str | Path, *, target_status: str, force_stale_lock: bool = False) -> dict:
        visible_path = self.resolve_chat_ref(chat_ref)
        source_status = self.paths.infer_status(visible_path)
        clean_target_status = normalize_status(target_status)
        if source_status == clean_target_status:
            return self.load_chat(visible_path)

        source_root = self.paths.status_dir(source_status)
        target_root = self.paths.status_dir(clean_target_status)
        relative_path = visible_path.resolve().relative_to(source_root.resolve())
        target_visible = target_root / relative_path
        source_companion = self.paths.companion_dir(visible_path)
        target_companion = self.paths.companion_dir(target_visible)

        if target_visible.exists():
            raise FileExistsError(f"Destination chat already exists: {target_visible}")
        if target_companion.exists():
            raise FileExistsError(f"Destination companion already exists: {target_companion}")

        with self.chat_lock(visible_path, force_stale=force_stale_lock):
            target_visible.parent.mkdir(parents=True, exist_ok=True)
            target_companion.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_companion), str(target_companion))
            shutil.move(str(visible_path), str(target_visible))
        self._release_lock(target_companion / config.LOCK_FILE_NAME)

        state = self.load_state(target_visible)
        state["status"] = clean_target_status
        state["chat_file"] = target_visible.name
        state["updated_at"] = now_timestamp()
        write_json_atomic(self.paths.state_path(target_visible), state)
        self._compile_visible(target_visible, state=state)
        self._remove_empty_parent_dirs(visible_path.parent, source_root)
        return self.load_chat(target_visible)

    def _remove_empty_parent_dirs(self, start_dir: Path, stop_dir: Path) -> None:
        current = start_dir.resolve()
        stop = stop_dir.resolve()
        while current != stop and stop in current.parents:
            try:
                if any(current.iterdir()):
                    return
                current.rmdir()
            except Exception:
                return
            current = current.parent

    def _visible_from_path_ref(self, chat_ref: str | Path) -> Path:
        ref = Path(str(chat_ref)).expanduser()
        if ref.exists():
            resolved = ref.resolve()
            if resolved.is_dir():
                return self.paths.visible_from_hidden_dir(resolved).resolve()
            if resolved.name == config.STATE_FILE_NAME:
                return self.paths.visible_from_state_path(resolved).resolve()
            return resolved

        for root in (self.paths.active_dir, self.paths.archived_dir):
            candidate = (root / ref).resolve()
            if candidate.exists():
                if candidate.is_dir():
                    return self.paths.visible_from_hidden_dir(candidate).resolve()
                if candidate.name == config.STATE_FILE_NAME:
                    return self.paths.visible_from_state_path(candidate).resolve()
                return candidate
        raise FileNotFoundError(f"Chat reference not found: {chat_ref}")

    def _normalize_message(self, parsed: dict) -> dict:
        message = {
            "schema_version": config.MESSAGE_SCHEMA_VERSION,
            "chat_id": str(parsed.get("chat_id", "") or ""),
            "message_id": int(parsed.get("message_id", 0) or 0),
            "speaker": str(parsed.get("speaker", "") or "").strip() or "Unknown",
            "timestamp": str(parsed.get("timestamp", "") or "").strip(),
            "kind": clean_kind(str(parsed.get("kind", "") or "message")),
            "mentions": clean_unique_strings(parsed.get("mentions", [])),
            "message": str(parsed.get("message", "") or ""),
        }
        message["char_count"] = (
            int(parsed.get("char_count"))
            if isinstance(parsed.get("char_count"), int)
            else text_char_count(message["message"])
        )
        if isinstance(parsed.get("versions"), dict):
            versions: dict[str, dict] = {}
            for level in range(config.MESSAGE_VERSION_MIN_LEVEL, config.MESSAGE_VERSION_MAX_LEVEL + 1):
                key = str(level)
                version = parsed["versions"].get(key)
                if not isinstance(version, dict):
                    continue
                version_message = str(version.get("message", "") or "")
                versions[key] = {
                    "message": version_message,
                    "char_count": int(version.get("char_count"))
                    if isinstance(version.get("char_count"), int)
                    else text_char_count(version_message),
                }
            if versions:
                message["versions"] = versions
        if isinstance(parsed.get("version_prep"), dict):
            message["version_prep"] = dict(parsed["version_prep"])
        placement_metadata = clean_placement_metadata(parsed.get("placement_metadata"))
        if placement_metadata:
            message["placement_metadata"] = placement_metadata
        return message

    def _message_sort_key(self, path: Path) -> tuple[int, str]:
        try:
            return (int(path.stem), path.stem)
        except Exception:
            return (10**12, path.stem)

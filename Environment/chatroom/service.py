from __future__ import annotations

from pathlib import Path

from . import cursors
from .json_io import load_json
from .models import ChatSummary, ScanItem
from .scanner import scan_unread as scan_unread_for_agent
from .store import ChatroomStore


class ChatroomService:
    def __init__(self, root_dir: str | Path) -> None:
        self.store = ChatroomStore(root_dir)

    @property
    def root_dir(self) -> Path:
        return self.store.root_dir

    def list_chats(self, status: str = "active") -> list[ChatSummary]:
        return self.store.list_chats(status)

    def create_chat(
        self,
        title: str,
        folder: str = "Parking_Lot",
        participants: list[str] | None = None,
    ) -> dict:
        return self.store.create_chat(title, folder, participants)

    def load_chat(self, chat_ref: str | Path) -> dict:
        return self.store.load_chat(chat_ref)

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
        return self.store.post_message(
            chat_ref,
            speaker,
            message,
            kind=kind,
            mentions=mentions,
            placement_metadata=placement_metadata,
            compile_after=compile_after,
            require_participant=require_participant,
            force_stale_lock=force_stale_lock,
        )

    def compile_chat(self, chat_ref: str | Path, *, force_stale_lock: bool = False) -> dict:
        return self.store.compile_chat(chat_ref, force_stale_lock=force_stale_lock)

    def get_compile_policy(self, chat_ref: str | Path) -> dict:
        return self.store.get_compile_policy(chat_ref)

    def exclude_messages(
        self,
        chat_ref: str | Path,
        message_ids: list[int],
        *,
        compile_after: bool = True,
        force_stale_lock: bool = False,
    ) -> dict:
        return self.store.exclude_messages(
            chat_ref,
            message_ids,
            compile_after=compile_after,
            force_stale_lock=force_stale_lock,
        )

    def include_messages(
        self,
        chat_ref: str | Path,
        message_ids: list[int],
        *,
        compile_after: bool = True,
        force_stale_lock: bool = False,
    ) -> dict:
        return self.store.include_messages(
            chat_ref,
            message_ids,
            compile_after=compile_after,
            force_stale_lock=force_stale_lock,
        )

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
        return self.store.add_standin(
            chat_ref,
            replaces_message_ids,
            message,
            insert_after_message_id=insert_after_message_id,
            speaker=speaker,
            kind=kind,
            mentions=mentions,
            standin_id=standin_id,
            compile_after=compile_after,
            force_stale_lock=force_stale_lock,
        )

    def clear_compile_policy(
        self,
        chat_ref: str | Path,
        *,
        compile_after: bool = True,
        force_stale_lock: bool = False,
    ) -> dict:
        return self.store.clear_compile_policy(
            chat_ref,
            compile_after=compile_after,
            force_stale_lock=force_stale_lock,
        )

    def scan_unread(
        self,
        agent_name: str,
        cursor_path: str | Path,
        *,
        status: str = "active",
        source: str = "state",
        participant_gated: bool = True,
    ) -> list[ScanItem]:
        return scan_unread_for_agent(
            self.root_dir,
            agent_name=agent_name,
            cursor_path=cursor_path,
            status=status,
            source=source,
            participant_gated=participant_gated,
        )

    def render_chat_lens(self, chat_ref: str | Path, *, source: str = "canonical") -> dict:
        return self.store.render_chat_lens(chat_ref, source=source)

    def mark_seen(
        self,
        agent_name: str,
        cursor_path: str | Path,
        chat_ref: str | Path,
        message_id: int | None = None,
        source: str = "state",
    ) -> dict:
        loaded = self.store.load_chat(chat_ref)
        state = loaded["state"]
        if message_id is not None:
            seen_id = int(message_id)
        elif str(source or "state").strip().lower() in {"canonical", "messages"}:
            visible_path = self.store.resolve_chat_ref(chat_ref)
            seen_id = int(self.store.latest_from_messages(visible_path).get("last_message_id", 0) or 0)
        else:
            seen_id = int(state.get("last_message_id", 0) or 0)
        return cursors.mark_seen(
            cursor_path,
            agent_name,
            chat_id=state["chat_id"],
            chat_title=state.get("chat_title", ""),
            state_path=loaded["state_path"],
            last_seen_message_id=seen_id,
        )

    def archive_chat(self, chat_ref: str | Path, *, force_stale_lock: bool = False) -> dict:
        return self.store.archive_chat(chat_ref, force_stale_lock=force_stale_lock)

    def restore_chat(self, chat_ref: str | Path, *, force_stale_lock: bool = False) -> dict:
        return self.store.restore_chat(chat_ref, force_stale_lock=force_stale_lock)

    def participant_coverage(self, participant: str, *, status: str = "active") -> dict:
        return self.store.participant_coverage(participant, status=status)

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
        return self.store.add_participant_operation(
            chat_ref,
            participant,
            threshold_chars=threshold_chars,
            requested_by=requested_by,
            apply=apply,
            force_stale_lock=force_stale_lock,
        )

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
        return self.store.remove_participant_operation(
            chat_ref,
            participant,
            reason=reason,
            requested_by=requested_by,
            apply=apply,
            force_stale_lock=force_stale_lock,
        )

    def audit_message_versions(
        self,
        chat_ref: str | Path | None = None,
        *,
        status: str = "active",
        semantic: bool = False,
    ) -> dict:
        return self.store.audit_message_versions(chat_ref, status=status, semantic=semantic)

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
        return self.store.update_message_versions(
            chat_ref,
            message_id,
            versions,
            prepared_by=prepared_by,
            semantic_prepared=semantic_prepared,
            compile_after=compile_after,
            force_stale_lock=force_stale_lock,
        )

    def mark_version_prepped(
        self,
        agent_name: str,
        cursor_path: str | Path,
        chat_ref: str | Path,
        message_id: int,
        *,
        mode: str = "semantic",
    ) -> dict:
        clean_mode = str(mode or "semantic").strip().lower()
        if clean_mode not in {"semantic", "structural"}:
            raise ValueError("mode must be 'semantic' or 'structural'.")
        visible_path = self.store.resolve_chat_ref(chat_ref)
        state = self.store.load_state(visible_path)
        clean_message_id = int(message_id)
        if clean_message_id <= 0:
            raise ValueError("message_id must be positive.")

        audit = self.store.audit_message_versions(visible_path, semantic=(clean_mode == "semantic"))
        room = audit.get("rooms", [{}])[0]
        target_report = None
        for report in room.get("messages", []):
            if int(report.get("message_id", 0) or 0) == clean_message_id:
                target_report = report
                break
        if target_report is None:
            raise ValueError(f"Message {clean_message_id} not found in {state.get('chat_title', visible_path)}.")
        if target_report.get("needs_work"):
            raise ValueError(f"Message {clean_message_id} still needs version-prep work: {target_report.get('issues', [])}")
        if not target_report.get("structural_ready"):
            raise ValueError(f"Message {clean_message_id} is not structurally ready.")
        if clean_mode == "semantic" and not target_report.get("semantic_prepared"):
            raise ValueError(f"Message {clean_message_id} is not semantically prepared.")

        message_path = self.store.paths.messages_dir(visible_path) / f"{clean_message_id:06d}.json"
        parsed = load_json(message_path)
        if not isinstance(parsed, dict):
            raise ValueError(f"Message file must be a JSON object: {message_path}")
        prep = parsed.get("version_prep")
        if not isinstance(prep, dict):
            raise ValueError(f"Message {clean_message_id} is missing version_prep metadata.")

        return cursors.mark_version_prepped(
            cursor_path,
            agent_name,
            chat_id=state["chat_id"],
            chat_title=state.get("chat_title", ""),
            message_id=clean_message_id,
            mode=clean_mode,
            source_hash=str(prep.get("source_hash", "") or ""),
            bundle_hash=str(prep.get("bundle_hash", "") or ""),
            prepared_at=str(prep.get("prepared_at", "") or ""),
        )

    def load_consumer_state(self, chat_ref: str | Path, consumer_id: str) -> dict:
        return self.store.load_consumer_state(chat_ref, consumer_id)

    def render_consumer_lens(
        self,
        chat_ref: str | Path,
        consumer_id: str,
        *,
        threshold_chars: int | None = None,
        force_stale_lock: bool = False,
    ) -> dict:
        return self.store.render_consumer_lens(
            chat_ref,
            consumer_id,
            threshold_chars=threshold_chars,
            force_stale_lock=force_stale_lock,
        )

    def create_room_operation(
        self,
        title: str,
        *,
        folder: str | None = None,
        participants: list[str] | None = None,
        requested_by: str = "Codex",
        apply: bool = False,
    ) -> dict:
        return self.store.create_room_operation(
            title,
            folder=folder,
            participants=participants,
            requested_by=requested_by,
            apply=apply,
        )

    def archive_room_operation(
        self,
        chat_ref: str | Path,
        *,
        requested_by: str = "Codex",
        apply: bool = False,
        force_stale_lock: bool = False,
    ) -> dict:
        return self.store.archive_room_operation(
            chat_ref,
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
        return self.store.restore_room_operation(
            chat_ref,
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
        return self.store.place_message_operation(
            source_chat_ref,
            source_message_id,
            target_chat_ref,
            placement_reason=placement_reason,
            content_mode=content_mode,
            requested_by=requested_by,
            apply=apply,
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
        return self.store.duplicate_message_operation(
            source_chat_ref,
            source_message_id,
            target_chat_ref,
            placement_reason=placement_reason,
            content_mode=content_mode,
            requested_by=requested_by,
            apply=apply,
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
        return self.store.place_range_operation(
            source_chat_ref,
            start_message_id,
            end_message_id,
            target_chat_ref,
            placement_reason=placement_reason,
            content_mode=content_mode,
            requested_by=requested_by,
            apply=apply,
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
        return self.store.duplicate_range_operation(
            source_chat_ref,
            start_message_id,
            end_message_id,
            target_chat_ref,
            placement_reason=placement_reason,
            content_mode=content_mode,
            requested_by=requested_by,
            apply=apply,
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
        return self.store.apply_compile_policy_operation(
            chat_ref,
            message_ids,
            mode=mode,
            standin_message=standin_message,
            requested_by=requested_by,
            apply=apply,
            force_stale_lock=force_stale_lock,
        )

    def read_operation_log(self, *, limit: int | None = None) -> list[dict]:
        return self.store.read_operation_log(limit=limit)

    def verify(self, root: str | Path | None = None) -> dict:
        return self.store.verify(root)

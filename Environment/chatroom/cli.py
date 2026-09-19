from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .service import ChatroomService


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _default_chat_root() -> Path:
    project_root = Path(__file__).resolve().parents[2]
    fallback_root = (project_root / "Storage" / "Generated Artifacts" / "Chats").resolve()

    def has_visible_chats(chat_root: Path) -> bool:
        active_dir = chat_root / "Active"
        if not active_dir.exists():
            return False
        for path in active_dir.rglob("*.json"):
            if any(part.startswith("_") for part in path.parts):
                continue
            return True
        return False

    try:
        sys.path.insert(0, str(project_root))
        from collection_handoff import CollectionHandoff

        registry_root = Path(
            CollectionHandoff(base_dir=str(project_root)).get_storage_entry_directory("chat_root")
        ).resolve()
        if has_visible_chats(registry_root):
            return registry_root
        if registry_root != fallback_root and has_visible_chats(fallback_root):
            return fallback_root
        return registry_root
    except Exception:
        return fallback_root


def _service(args: argparse.Namespace) -> ChatroomService:
    root = Path(args.root).resolve() if getattr(args, "root", None) else _default_chat_root()
    return ChatroomService(root)


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def _parse_mentions(raw_mentions: str | None) -> list[str]:
    if not raw_mentions:
        return []
    return [part.strip() for part in raw_mentions.split(",") if part.strip()]


def _parse_message_ids(raw_message_ids: str) -> list[int]:
    results: list[int] = []
    for part in str(raw_message_ids or "").split(","):
        clean = part.strip()
        if not clean:
            continue
        value = int(clean)
        if value <= 0:
            raise ValueError(f"Message id must be positive: {value}")
        if value not in results:
            results.append(value)
    if not results:
        raise ValueError("At least one message id is required.")
    return results


def command_scan(args: argparse.Namespace) -> int:
    service = _service(args)
    items = service.scan_unread(
        args.agent,
        args.cursor,
        status=args.status,
        source=args.source,
        participant_gated=not args.all_active,
    )
    _print_json(
        {
            "unread": [
                {
                    "chat_id": item.chat_id,
                    "chat_title": item.chat_title,
                    "status": item.status,
                    "visible_path": str(item.visible_path),
                    "state_path": str(item.state_path),
                    "last_message_id": item.last_message_id,
                    "last_seen_message_id": item.last_seen_message_id,
                    "unread_count": item.unread_count,
                    "warnings": item.warnings,
                }
                for item in items
            ]
        }
    )
    return 0


def command_post(args: argparse.Namespace) -> int:
    service = _service(args)
    if args.message_file:
        message = Path(args.message_file).read_text(encoding="utf-8")
    else:
        message = str(args.message or "")
    result = service.post_message(
        args.chat,
        args.speaker,
        message,
        kind=args.kind,
        mentions=_parse_mentions(args.mentions),
        compile_after=not args.no_compile,
        require_participant=args.require_participant,
        force_stale_lock=args.force_stale_lock,
    )
    _print_json({"posted": result["state"]})
    return 0


def command_mark_seen(args: argparse.Namespace) -> int:
    service = _service(args)
    cursor = service.mark_seen(args.agent, args.cursor, args.chat, message_id=args.message_id, source=args.source)
    _print_json(cursor)
    return 0


def command_render_lens(args: argparse.Namespace) -> int:
    service = _service(args)
    lens = service.render_chat_lens(args.chat, source=args.source)
    _print_json(lens)
    return 0


def command_compile(args: argparse.Namespace) -> int:
    service = _service(args)
    result = service.compile_chat(args.chat, force_stale_lock=args.force_stale_lock)
    _print_json({"compiled": result["state"]})
    return 0


def command_compile_policy(args: argparse.Namespace) -> int:
    service = _service(args)
    _print_json({"compile_policy": service.get_compile_policy(args.chat)})
    return 0


def command_exclude_messages(args: argparse.Namespace) -> int:
    service = _service(args)
    result = service.exclude_messages(
        args.chat,
        _parse_message_ids(args.message_ids),
        compile_after=not args.no_compile,
        force_stale_lock=args.force_stale_lock,
    )
    _print_json({"state": result["state"]})
    return 0


def command_include_messages(args: argparse.Namespace) -> int:
    service = _service(args)
    result = service.include_messages(
        args.chat,
        _parse_message_ids(args.message_ids),
        compile_after=not args.no_compile,
        force_stale_lock=args.force_stale_lock,
    )
    _print_json({"state": result["state"]})
    return 0


def command_add_standin(args: argparse.Namespace) -> int:
    service = _service(args)
    if args.message_file:
        message = Path(args.message_file).read_text(encoding="utf-8")
    else:
        message = str(args.message or "")
    result = service.add_standin(
        args.chat,
        _parse_message_ids(args.replaces),
        message,
        insert_after_message_id=args.insert_after,
        speaker=args.speaker,
        kind=args.kind,
        mentions=_parse_mentions(args.mentions),
        standin_id=args.standin_id,
        compile_after=not args.no_compile,
        force_stale_lock=args.force_stale_lock,
    )
    _print_json({"state": result["state"]})
    return 0


def command_clear_compile_policy(args: argparse.Namespace) -> int:
    service = _service(args)
    result = service.clear_compile_policy(
        args.chat,
        compile_after=not args.no_compile,
        force_stale_lock=args.force_stale_lock,
    )
    _print_json({"state": result["state"]})
    return 0


def command_participant_coverage(args: argparse.Namespace) -> int:
    service = _service(args)
    _print_json(service.participant_coverage(args.participant, status=args.status))
    return 0


def command_add_participant(args: argparse.Namespace) -> int:
    service = _service(args)
    result = service.add_participant_operation(
        args.chat,
        args.participant,
        threshold_chars=args.threshold_chars,
        requested_by=args.requested_by,
        apply=args.apply,
        force_stale_lock=args.force_stale_lock,
    )
    _print_json(result)
    return 0


def command_remove_participant(args: argparse.Namespace) -> int:
    service = _service(args)
    result = service.remove_participant_operation(
        args.chat,
        args.participant,
        reason=args.reason,
        requested_by=args.requested_by,
        apply=args.apply,
        force_stale_lock=args.force_stale_lock,
    )
    _print_json(result)
    return 0


def command_version_audit(args: argparse.Namespace) -> int:
    service = _service(args)
    _print_json(service.audit_message_versions(args.chat, status=args.status, semantic=args.semantic))
    return 0


def command_update_message_versions(args: argparse.Namespace) -> int:
    service = _service(args)
    versions = json.loads(Path(args.versions_file).read_text(encoding="utf-8"))
    result = service.update_message_versions(
        args.chat,
        args.message_id,
        versions,
        prepared_by=args.prepared_by,
        semantic_prepared=not args.structural_only,
        compile_after=not args.no_compile,
        force_stale_lock=args.force_stale_lock,
    )
    _print_json({"updated": result["state"]})
    return 0


def command_mark_version_prepped(args: argparse.Namespace) -> int:
    service = _service(args)
    cursor = service.mark_version_prepped(
        args.agent,
        args.cursor,
        args.chat,
        args.message_id,
        mode=args.mode,
    )
    _print_json(cursor)
    return 0


def command_consumer_state(args: argparse.Namespace) -> int:
    service = _service(args)
    _print_json(service.load_consumer_state(args.chat, args.consumer))
    return 0


def command_render_consumer_lens(args: argparse.Namespace) -> int:
    service = _service(args)
    _print_json(
        service.render_consumer_lens(
            args.chat,
            args.consumer,
            threshold_chars=args.threshold_chars,
            force_stale_lock=args.force_stale_lock,
        )
    )
    return 0


def command_create_room(args: argparse.Namespace) -> int:
    service = _service(args)
    result = service.create_room_operation(
        args.title,
        folder=args.folder,
        participants=_parse_mentions(args.participants),
        requested_by=args.requested_by,
        apply=args.apply,
    )
    _print_json(result)
    return 0


def command_archive_room(args: argparse.Namespace) -> int:
    service = _service(args)
    result = service.archive_room_operation(
        args.chat,
        requested_by=args.requested_by,
        apply=args.apply,
        force_stale_lock=args.force_stale_lock,
    )
    _print_json(result)
    return 0


def command_restore_room(args: argparse.Namespace) -> int:
    service = _service(args)
    result = service.restore_room_operation(
        args.chat,
        requested_by=args.requested_by,
        apply=args.apply,
        force_stale_lock=args.force_stale_lock,
    )
    _print_json(result)
    return 0


def command_place_message(args: argparse.Namespace) -> int:
    service = _service(args)
    command = service.duplicate_message_operation if args.command == "duplicate-message" else service.place_message_operation
    result = command(
        args.source_chat,
        args.source_message_id,
        args.target_chat,
        placement_reason=args.placement_reason,
        content_mode=args.content_mode,
        requested_by=args.requested_by,
        apply=args.apply,
        force_stale_lock=args.force_stale_lock,
    )
    _print_json(result)
    return 0


def command_place_range(args: argparse.Namespace) -> int:
    service = _service(args)
    command = service.duplicate_range_operation if args.command == "duplicate-range" else service.place_range_operation
    result = command(
        args.source_chat,
        args.start_message_id,
        args.end_message_id,
        args.target_chat,
        placement_reason=args.placement_reason,
        content_mode=args.content_mode,
        requested_by=args.requested_by,
        apply=args.apply,
        force_stale_lock=args.force_stale_lock,
    )
    _print_json(result)
    return 0


def command_apply_compile_policy(args: argparse.Namespace) -> int:
    service = _service(args)
    if args.standin_file:
        standin_message = Path(args.standin_file).read_text(encoding="utf-8")
    else:
        standin_message = args.standin_message
    result = service.apply_compile_policy_operation(
        args.chat,
        _parse_message_ids(args.message_ids),
        mode=args.mode,
        standin_message=standin_message,
        requested_by=args.requested_by,
        apply=args.apply,
        force_stale_lock=args.force_stale_lock,
    )
    _print_json(result)
    return 0


def command_operation_log(args: argparse.Namespace) -> int:
    service = _service(args)
    _print_json({"operations": service.read_operation_log(limit=args.limit)})
    return 0


def command_verify(args: argparse.Namespace) -> int:
    service = _service(args)
    result = service.verify()
    _print_json(result)
    return 0 if result.get("ok") else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Chatroom v2 command line interface.")
    parser.add_argument("--root", help="Chat root directory. Defaults to collection_handoff chat_root.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan")
    scan.add_argument("--agent", required=True)
    scan.add_argument("--cursor", required=True)
    scan.add_argument("--status", default="active", choices=["active", "archived"])
    scan.add_argument("--source", default="state", choices=["state", "canonical", "messages"])
    scan.add_argument("--all-active", action="store_true", help="Audit every room instead of participant-gated rooms.")
    scan.set_defaults(func=command_scan)

    post = subparsers.add_parser("post")
    post.add_argument("--chat", required=True)
    post.add_argument("--speaker", required=True)
    message_group = post.add_mutually_exclusive_group(required=True)
    message_group.add_argument("--message")
    message_group.add_argument("--message-file")
    post.add_argument("--kind", default="message")
    post.add_argument("--mentions")
    post.add_argument("--no-compile", action="store_true")
    post.add_argument("--require-participant", action="store_true")
    post.add_argument("--force-stale-lock", action="store_true")
    post.set_defaults(func=command_post)

    mark_seen = subparsers.add_parser("mark-seen")
    mark_seen.add_argument("--agent", required=True)
    mark_seen.add_argument("--cursor", required=True)
    mark_seen.add_argument("--chat", required=True)
    mark_seen.add_argument("--message-id", type=int)
    mark_seen.add_argument("--source", default="state", choices=["state", "canonical", "messages"])
    mark_seen.set_defaults(func=command_mark_seen)

    render_lens = subparsers.add_parser("render-lens")
    render_lens.add_argument("--chat", required=True)
    render_lens.add_argument("--source", default="canonical", choices=["canonical", "messages"])
    render_lens.set_defaults(func=command_render_lens)

    compile_cmd = subparsers.add_parser("compile")
    compile_cmd.add_argument("--chat", required=True)
    compile_cmd.add_argument("--force-stale-lock", action="store_true")
    compile_cmd.set_defaults(func=command_compile)

    compile_policy = subparsers.add_parser("compile-policy")
    compile_policy.add_argument("--chat", required=True)
    compile_policy.set_defaults(func=command_compile_policy)

    exclude_messages = subparsers.add_parser("exclude-messages")
    exclude_messages.add_argument("--chat", required=True)
    exclude_messages.add_argument("--message-ids", required=True, help="Comma-separated message ids to exclude from compiled output.")
    exclude_messages.add_argument("--no-compile", action="store_true")
    exclude_messages.add_argument("--force-stale-lock", action="store_true")
    exclude_messages.set_defaults(func=command_exclude_messages)

    include_messages = subparsers.add_parser("include-messages")
    include_messages.add_argument("--chat", required=True)
    include_messages.add_argument("--message-ids", required=True, help="Comma-separated message ids to restore to compiled output.")
    include_messages.add_argument("--no-compile", action="store_true")
    include_messages.add_argument("--force-stale-lock", action="store_true")
    include_messages.set_defaults(func=command_include_messages)

    add_standin = subparsers.add_parser("add-standin")
    add_standin.add_argument("--chat", required=True)
    add_standin.add_argument("--replaces", required=True, help="Comma-separated message ids represented by this stand-in.")
    add_standin.add_argument("--insert-after", type=int, help="Message id after which the stand-in should appear. Defaults to the highest replaced id.")
    add_standin.add_argument("--speaker", default="System")
    message_group = add_standin.add_mutually_exclusive_group(required=True)
    message_group.add_argument("--message")
    message_group.add_argument("--message-file")
    add_standin.add_argument("--kind", default="system")
    add_standin.add_argument("--mentions")
    add_standin.add_argument("--standin-id")
    add_standin.add_argument("--no-compile", action="store_true")
    add_standin.add_argument("--force-stale-lock", action="store_true")
    add_standin.set_defaults(func=command_add_standin)

    clear_compile_policy = subparsers.add_parser("clear-compile-policy")
    clear_compile_policy.add_argument("--chat", required=True)
    clear_compile_policy.add_argument("--no-compile", action="store_true")
    clear_compile_policy.add_argument("--force-stale-lock", action="store_true")
    clear_compile_policy.set_defaults(func=command_clear_compile_policy)

    participant_coverage = subparsers.add_parser("participant-coverage")
    participant_coverage.add_argument("--participant", required=True)
    participant_coverage.add_argument("--status", default="active", choices=["active", "archived"])
    participant_coverage.set_defaults(func=command_participant_coverage)

    add_participant = subparsers.add_parser("add-participant")
    add_participant.add_argument("--chat", required=True)
    add_participant.add_argument("--participant", required=True)
    add_participant.add_argument("--threshold-chars", type=int)
    add_participant.add_argument("--requested-by", default="Codex")
    add_participant.add_argument("--apply", action="store_true")
    add_participant.add_argument("--force-stale-lock", action="store_true")
    add_participant.set_defaults(func=command_add_participant)

    remove_participant = subparsers.add_parser("remove-participant")
    remove_participant.add_argument("--chat", required=True)
    remove_participant.add_argument("--participant", required=True)
    remove_participant.add_argument("--reason", default="")
    remove_participant.add_argument("--requested-by", default="Codex")
    remove_participant.add_argument("--apply", action="store_true")
    remove_participant.add_argument("--force-stale-lock", action="store_true")
    remove_participant.set_defaults(func=command_remove_participant)

    version_audit = subparsers.add_parser("version-audit")
    version_audit.add_argument("--chat")
    version_audit.add_argument("--status", default="active", choices=["active", "archived"])
    version_audit.add_argument("--semantic", action="store_true")
    version_audit.set_defaults(func=command_version_audit)

    update_versions = subparsers.add_parser("update-message-versions")
    update_versions.add_argument("--chat", required=True)
    update_versions.add_argument("--message-id", required=True, type=int)
    update_versions.add_argument("--versions-file", required=True)
    update_versions.add_argument("--prepared-by", default="Codex")
    update_versions.add_argument("--structural-only", action="store_true")
    update_versions.add_argument("--no-compile", action="store_true")
    update_versions.add_argument("--force-stale-lock", action="store_true")
    update_versions.set_defaults(func=command_update_message_versions)

    mark_version_prepped = subparsers.add_parser("mark-version-prepped")
    mark_version_prepped.add_argument("--agent", required=True)
    mark_version_prepped.add_argument("--cursor", required=True)
    mark_version_prepped.add_argument("--chat", required=True)
    mark_version_prepped.add_argument("--message-id", required=True, type=int)
    mark_version_prepped.add_argument("--mode", default="semantic", choices=["semantic", "structural"])
    mark_version_prepped.set_defaults(func=command_mark_version_prepped)

    consumer_state = subparsers.add_parser("consumer-state")
    consumer_state.add_argument("--chat", required=True)
    consumer_state.add_argument("--consumer", required=True)
    consumer_state.set_defaults(func=command_consumer_state)

    render_consumer_lens = subparsers.add_parser("render-consumer-lens")
    render_consumer_lens.add_argument("--chat", required=True)
    render_consumer_lens.add_argument("--consumer", required=True)
    render_consumer_lens.add_argument("--threshold-chars", type=int)
    render_consumer_lens.add_argument("--force-stale-lock", action="store_true")
    render_consumer_lens.set_defaults(func=command_render_consumer_lens)

    create_room = subparsers.add_parser("create-room")
    create_room.add_argument("--title", required=True)
    create_room.add_argument("--folder", default="Parking_Lot")
    create_room.add_argument("--participants")
    create_room.add_argument("--requested-by", default="Codex")
    create_room.add_argument("--apply", action="store_true")
    create_room.set_defaults(func=command_create_room)

    archive_room = subparsers.add_parser("archive-room")
    archive_room.add_argument("--chat", required=True)
    archive_room.add_argument("--requested-by", default="Codex")
    archive_room.add_argument("--apply", action="store_true")
    archive_room.add_argument("--force-stale-lock", action="store_true")
    archive_room.set_defaults(func=command_archive_room)

    restore_room = subparsers.add_parser("restore-room")
    restore_room.add_argument("--chat", required=True)
    restore_room.add_argument("--requested-by", default="Codex")
    restore_room.add_argument("--apply", action="store_true")
    restore_room.add_argument("--force-stale-lock", action="store_true")
    restore_room.set_defaults(func=command_restore_room)

    for command_name in ("place-message", "duplicate-message"):
        place_message = subparsers.add_parser(command_name)
        place_message.add_argument("--source-chat", required=True)
        place_message.add_argument("--source-message-id", required=True, type=int)
        place_message.add_argument("--target-chat", required=True)
        place_message.add_argument("--placement-reason", required=True)
        place_message.add_argument("--content-mode", default="full_copy")
        place_message.add_argument("--requested-by", default="Codex")
        place_message.add_argument("--apply", action="store_true")
        place_message.add_argument("--force-stale-lock", action="store_true")
        place_message.set_defaults(func=command_place_message)

    for command_name in ("place-range", "duplicate-range"):
        place_range = subparsers.add_parser(command_name)
        place_range.add_argument("--source-chat", required=True)
        place_range.add_argument("--start-message-id", required=True, type=int)
        place_range.add_argument("--end-message-id", required=True, type=int)
        place_range.add_argument("--target-chat", required=True)
        place_range.add_argument("--placement-reason", required=True)
        place_range.add_argument("--content-mode", default="full_copy")
        place_range.add_argument("--requested-by", default="Codex")
        place_range.add_argument("--apply", action="store_true")
        place_range.add_argument("--force-stale-lock", action="store_true")
        place_range.set_defaults(func=command_place_range)

    apply_compile_policy = subparsers.add_parser("apply-compile-policy")
    apply_compile_policy.add_argument("--chat", required=True)
    apply_compile_policy.add_argument("--message-ids", required=True, help="Comma-separated message ids.")
    apply_compile_policy.add_argument(
        "--mode",
        required=True,
        choices=["detailed-standin", "short-standin", "no-standin"],
    )
    standin_group = apply_compile_policy.add_mutually_exclusive_group()
    standin_group.add_argument("--standin-message")
    standin_group.add_argument("--standin-file")
    apply_compile_policy.add_argument("--requested-by", default="Codex")
    apply_compile_policy.add_argument("--apply", action="store_true")
    apply_compile_policy.add_argument("--force-stale-lock", action="store_true")
    apply_compile_policy.set_defaults(func=command_apply_compile_policy)

    operation_log = subparsers.add_parser("operation-log")
    operation_log.add_argument("--limit", type=int)
    operation_log.set_defaults(func=command_operation_log)

    verify = subparsers.add_parser("verify")
    verify.set_defaults(func=command_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

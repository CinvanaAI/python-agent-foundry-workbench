from __future__ import annotations

from pathlib import Path

from .cursors import load_cursor
from .models import ScanItem
from .store import ChatroomStore


def scan_unread(
    root_dir: str | Path,
    *,
    agent_name: str,
    cursor_path: str | Path,
    status: str = "active",
    source: str = "state",
    participant_gated: bool = True,
) -> list[ScanItem]:
    store = ChatroomStore(root_dir)
    cursor = load_cursor(cursor_path, agent_name)
    positions = cursor.get("positions", {})
    if not isinstance(positions, dict):
        positions = {}

    results: list[ScanItem] = []
    for latest in store.latest_records(status, source=source):
        chat_id = latest["chat_id"]
        if participant_gated and latest.get("participants_known", True):
            participants = latest.get("participants", [])
            if agent_name not in participants:
                continue
        cursor_entry = positions.get(chat_id, {})
        if not isinstance(cursor_entry, dict):
            cursor_entry = {}
        try:
            seen = int(cursor_entry.get("last_seen_message_id", 0) or 0)
        except Exception:
            seen = 0
        last_message_id = int(latest.get("last_message_id", 0) or 0)
        unread = max(0, last_message_id - seen)
        if unread <= 0:
            continue
        results.append(
            ScanItem(
                chat_id=chat_id,
                chat_title=str(latest.get("chat_title", "") or ""),
                status=str(latest.get("status", "") or "active"),
                visible_path=latest["visible_path"],
                state_path=latest["state_path"],
                last_message_id=last_message_id,
                last_seen_message_id=seen,
                unread_count=unread,
                warnings=list(latest.get("warnings", [])),
            )
        )
    return results

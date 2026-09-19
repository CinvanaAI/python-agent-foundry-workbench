from __future__ import annotations

from pathlib import Path

from . import config
from .json_io import load_json, write_json_atomic
from .store import now_timestamp


def load_cursor(cursor_path: str | Path, agent_name: str) -> dict:
    path = Path(cursor_path)
    clean_agent = str(agent_name or "").strip()
    if not clean_agent:
        raise ValueError("agent_name is required.")
    if not path.exists():
        return {
            "schema_version": config.CURSOR_SCHEMA_VERSION,
            "agent_name": clean_agent,
            "updated_at": "",
            "positions": {},
        }
    parsed = load_json(path)
    if not isinstance(parsed, dict):
        raise ValueError(f"Cursor file must be a JSON object: {path}")
    if parsed.get("schema_version") != config.CURSOR_SCHEMA_VERSION:
        raise ValueError(f"Unsupported cursor schema at {path}: {parsed.get('schema_version')}")
    file_agent = str(parsed.get("agent_name", "") or "").strip()
    if file_agent and file_agent != clean_agent:
        raise ValueError(f"Cursor file belongs to {file_agent}, not {clean_agent}: {path}")
    parsed["agent_name"] = clean_agent
    if not isinstance(parsed.get("positions"), dict):
        parsed["positions"] = {}
    return parsed


def save_cursor(cursor_path: str | Path, cursor: dict) -> None:
    write_json_atomic(cursor_path, cursor)


def mark_seen(
    cursor_path: str | Path,
    agent_name: str,
    *,
    chat_id: str,
    chat_title: str,
    state_path: str,
    last_seen_message_id: int,
) -> dict:
    cursor = load_cursor(cursor_path, agent_name)
    timestamp = now_timestamp()
    cursor["updated_at"] = timestamp
    cursor.setdefault("positions", {})[chat_id] = {
        "last_seen_message_id": int(last_seen_message_id),
        "last_seen_at": timestamp,
        "chat_title": str(chat_title or ""),
        "state_path": str(state_path or ""),
    }
    save_cursor(cursor_path, cursor)
    return cursor


def load_version_prep_cursor(cursor_path: str | Path, agent_name: str) -> dict:
    path = Path(cursor_path)
    clean_agent = str(agent_name or "").strip()
    if not clean_agent:
        raise ValueError("agent_name is required.")
    if not path.exists():
        return {
            "schema_version": config.VERSION_PREP_CURSOR_SCHEMA_VERSION,
            "agent_name": clean_agent,
            "updated_at": "",
            "completed": {},
        }
    parsed = load_json(path)
    if not isinstance(parsed, dict):
        raise ValueError(f"Version prep cursor file must be a JSON object: {path}")
    if parsed.get("schema_version") != config.VERSION_PREP_CURSOR_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported version prep cursor schema at {path}: {parsed.get('schema_version')}"
        )
    file_agent = str(parsed.get("agent_name", "") or "").strip()
    if file_agent and file_agent != clean_agent:
        raise ValueError(f"Version prep cursor file belongs to {file_agent}, not {clean_agent}: {path}")
    parsed["agent_name"] = clean_agent
    if not isinstance(parsed.get("completed"), dict):
        parsed["completed"] = {}
    return parsed


def mark_version_prepped(
    cursor_path: str | Path,
    agent_name: str,
    *,
    chat_id: str,
    chat_title: str,
    message_id: int,
    mode: str,
    source_hash: str,
    bundle_hash: str,
    prepared_at: str,
) -> dict:
    cursor = load_version_prep_cursor(cursor_path, agent_name)
    timestamp = now_timestamp()
    clean_mode = str(mode or "").strip().lower() or "semantic"
    clean_message_id = int(message_id)
    key = f"{chat_id}:{clean_message_id}:{clean_mode}"
    cursor["updated_at"] = timestamp
    cursor.setdefault("completed", {})[key] = {
        "chat_id": str(chat_id or ""),
        "chat_title": str(chat_title or ""),
        "message_id": clean_message_id,
        "mode": clean_mode,
        "source_hash": str(source_hash or ""),
        "bundle_hash": str(bundle_hash or ""),
        "prepared_at": str(prepared_at or ""),
        "verified_at": timestamp,
    }
    save_cursor(cursor_path, cursor)
    return cursor

from __future__ import annotations

from pathlib import Path

from .store import ChatroomStore


def compile_chat(root_dir: str | Path, chat_ref: str | Path, *, force_stale_lock: bool = False) -> dict:
    return ChatroomStore(root_dir).compile_chat(chat_ref, force_stale_lock=force_stale_lock)

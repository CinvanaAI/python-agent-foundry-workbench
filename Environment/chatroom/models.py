from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ChatPaths:
    visible_path: Path
    companion_dir: Path
    state_path: Path
    messages_dir: Path
    consumers_dir: Path


@dataclass(frozen=True)
class ChatSummary:
    chat_id: str
    chat_title: str
    status: str
    visible_path: Path
    state_path: Path
    last_message_id: int
    last_message_at: str
    compile_status: str
    last_compiled_message_id: int


@dataclass(frozen=True)
class ScanItem:
    chat_id: str
    chat_title: str
    status: str
    visible_path: Path
    state_path: Path
    last_message_id: int
    last_seen_message_id: int
    unread_count: int
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VerificationIssue:
    severity: str
    code: str
    message: str
    path: Path | None = None

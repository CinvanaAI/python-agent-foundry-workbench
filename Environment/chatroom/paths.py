from __future__ import annotations

import re
from pathlib import Path

from . import config
from .models import ChatPaths


class ChatroomPaths:
    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = Path(root_dir).expanduser().resolve()
        self.active_dir = self.root_dir / config.ACTIVE_FOLDER
        self.archived_dir = self.root_dir / config.ARCHIVED_FOLDER
        self.meta_dir = self.root_dir / "_meta"
        self.operation_log_path = self.meta_dir / "operations.jsonl"

    def ensure_roots(self) -> None:
        self.active_dir.mkdir(parents=True, exist_ok=True)
        self.archived_dir.mkdir(parents=True, exist_ok=True)

    def status_dir(self, status: str) -> Path:
        clean_status = normalize_status(status)
        if clean_status == "archived":
            return self.archived_dir
        return self.active_dir

    def infer_status(self, path: str | Path) -> str:
        resolved = Path(path).expanduser().resolve()
        try:
            if self.archived_dir.resolve() in resolved.parents:
                return "archived"
        except Exception:
            pass
        return "active"

    def companion_dir(self, visible_path: str | Path) -> Path:
        path = Path(visible_path)
        return path.parent / f"{config.HIDDEN_FOLDER_PREFIX}{path.stem}"

    def messages_dir(self, visible_path: str | Path) -> Path:
        return self.companion_dir(visible_path) / config.MESSAGES_FOLDER_NAME

    def state_path(self, visible_path: str | Path) -> Path:
        return self.companion_dir(visible_path) / config.STATE_FILE_NAME

    def consumers_dir(self, visible_path: str | Path) -> Path:
        return self.companion_dir(visible_path) / config.CONSUMERS_FOLDER_NAME

    def chat_paths(self, visible_path: str | Path) -> ChatPaths:
        visible = Path(visible_path).expanduser().resolve()
        companion = self.companion_dir(visible)
        return ChatPaths(
            visible_path=visible,
            companion_dir=companion,
            state_path=companion / config.STATE_FILE_NAME,
            messages_dir=companion / config.MESSAGES_FOLDER_NAME,
            consumers_dir=companion / config.CONSUMERS_FOLDER_NAME,
        )

    def visible_from_state_path(self, state_path: str | Path) -> Path:
        state = Path(state_path).expanduser().resolve()
        hidden_dir = state.parent
        if not hidden_dir.name.startswith(config.HIDDEN_FOLDER_PREFIX):
            raise ValueError(f"State path is not inside a hidden chat folder: {state}")
        visible_stem = hidden_dir.name[len(config.HIDDEN_FOLDER_PREFIX):]
        return hidden_dir.parent / f"{visible_stem}.json"

    def visible_from_hidden_dir(self, hidden_dir: str | Path) -> Path:
        hidden = Path(hidden_dir).expanduser().resolve()
        if not hidden.name.startswith(config.HIDDEN_FOLDER_PREFIX):
            raise ValueError(f"Not a hidden chat folder: {hidden}")
        visible_stem = hidden.name[len(config.HIDDEN_FOLDER_PREFIX):]
        return hidden.parent / f"{visible_stem}.json"

    def iter_visible_paths(self, status: str | None = None) -> list[Path]:
        roots = [self.status_dir(status)] if status else [self.active_dir, self.archived_dir]
        visible_paths: list[Path] = []
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*.json"):
                if any(part.startswith(config.HIDDEN_FOLDER_PREFIX) for part in path.parts):
                    continue
                if path.is_file():
                    visible_paths.append(path.resolve())
        return sorted(visible_paths, key=lambda item: str(item).lower())

    def unique_visible_path(self, title: str, folder: str | None = None, *, create_parent: bool = True) -> Path:
        clean_stem = sanitize_file_stem(title) or "chat"
        relative_folder = normalize_relative_folder(folder or config.DEFAULT_NEW_CHAT_FOLDER)
        folder_dir = self.active_dir / Path(relative_folder) if relative_folder else self.active_dir
        if create_parent:
            folder_dir.mkdir(parents=True, exist_ok=True)

        candidate = folder_dir / f"{clean_stem}.json"
        if not candidate.exists():
            return candidate.resolve()

        index = 2
        while True:
            candidate = folder_dir / f"{clean_stem}_{index}.json"
            if not candidate.exists():
                return candidate.resolve()
            index += 1


def normalize_status(status: str | None) -> str:
    clean_status = str(status or "").strip().lower()
    if clean_status == "archived":
        return "archived"
    return "active"


def sanitize_file_stem(raw_value: object) -> str:
    text = str(raw_value or "").strip()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^A-Za-z0-9_]", "", text)
    return text


def normalize_relative_folder(raw_value: object) -> str:
    text = str(raw_value or "").strip()
    if not text:
        return ""
    text = text.replace("\\", "/")
    raw_parts = [part for part in text.split("/") if part.strip()]
    clean_parts: list[str] = []
    for raw_part in raw_parts:
        clean_part = sanitize_file_stem(raw_part)
        if not clean_part:
            continue
        if clean_part.startswith(config.HIDDEN_FOLDER_PREFIX):
            raise ValueError("Folder names beginning with '_' are reserved for hidden chat storage.")
        clean_parts.append(clean_part)
    return "/".join(clean_parts)

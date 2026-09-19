from __future__ import annotations

import copy
from typing import Any, Callable

from . import config


def version_level(value: object) -> int:
    try:
        level = int(value)
    except Exception:
        level = config.MESSAGE_VERSION_MIN_LEVEL
    return max(config.MESSAGE_VERSION_MIN_LEVEL, min(config.MESSAGE_VERSION_MAX_LEVEL, level))


def selected_versions_for(messages: list[dict], selected_versions: dict | None = None) -> dict[str, int]:
    raw_selected = selected_versions if isinstance(selected_versions, dict) else {}
    results: dict[str, int] = {}
    for message in messages:
        message_id = message.get("message_id")
        if not isinstance(message_id, int):
            continue
        results[str(message_id)] = version_level(raw_selected.get(str(message_id), 0))
    return results


def render_selected_messages(messages: list[dict], selected_versions: dict[str, int]) -> list[dict]:
    rendered: list[dict] = []
    for message in messages:
        selected = copy.deepcopy(message)
        message_id = selected.get("message_id")
        if isinstance(message_id, int):
            level = version_level(selected_versions.get(str(message_id), 0))
            versions = selected.get("versions")
            version_record: Any = versions.get(str(level)) if isinstance(versions, dict) else None
            if isinstance(version_record, dict) and "message" in version_record:
                selected["message"] = str(version_record.get("message", "") or "")
                selected["char_count"] = int(version_record.get("char_count", len(selected["message"])) or 0)
            selected["selected_version"] = level
        selected.pop("versions", None)
        rendered.append(selected)
    return rendered


def fit_selected_versions(
    messages: list[dict],
    selected_versions: dict | None,
    threshold_chars: int,
    render_char_count: Callable[[dict[str, int]], int],
) -> dict:
    threshold = max(1, int(threshold_chars or config.DEFAULT_CONSUMER_THRESHOLD_CHARS))
    selected = selected_versions_for(messages, selected_versions)
    candidate_chars = render_char_count(selected)
    changed = False

    while candidate_chars > threshold:
        stepped = False
        for key in sorted(selected, key=lambda item: int(item)):
            if selected[key] >= config.MESSAGE_VERSION_MAX_LEVEL:
                continue
            selected[key] += 1
            stepped = True
            changed = True
            break
        if not stepped:
            return {
                "selected_versions": selected,
                "compiled_chars": candidate_chars,
                "threshold_chars": threshold,
                "remaining_margin_chars": threshold - candidate_chars,
                "highest_version_used": max(selected.values(), default=0),
                "changed": changed,
                "exhausted": True,
            }
        candidate_chars = render_char_count(selected)

    return {
        "selected_versions": selected,
        "compiled_chars": candidate_chars,
        "threshold_chars": threshold,
        "remaining_margin_chars": threshold - candidate_chars,
        "highest_version_used": max(selected.values(), default=0),
        "changed": changed,
        "exhausted": False,
    }

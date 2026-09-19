from __future__ import annotations

import re
from pathlib import Path
from typing import Any


OUTCASTS_GROUP_NAME = "Outcasts"
VALID_TASK_STATUSES = {"System", "On Demand"}

CANONICAL_AGENT_KEYS = {
    "name",
    "default_returns",
    "groups",
}

CANONICAL_GROUP_KEYS = {
    "name",
    "group_file",
    "default_returns",
    "tasks",
}

CANONICAL_TASK_KEYS = {
    "name",
    "task_file",
    "task_status",
    "workflow",
    "Triggers",
    "default_returns",
    "packages",
    "prompts",
    "memory",
}

CANONICAL_PACKAGE_KEYS = {
    "position",
    "name",
    "package_status",
    "required_replacements",
    "optional_replacements",
    "arguments",
    "returns",
    "recognitions",
    "logic",
}

CANONICAL_ARGUMENT_KEYS = {
    "argument_question",
    "argument_value_name",
    "argument_fallback",
    "argument_hidden",
    "task_argument_mapping",
}

CANONICAL_RETURN_KEYS = {
    "return_value_name",
    "return_description",
    "visible",
    "friendship",
}

CANONICAL_DEFAULT_RETURN_KEYS = {
    "return_value_name",
    "return_description",
    "return_value",
}

CANONICAL_PROMPT_KEYS = {
    "name",
    "prompt_source",
}

CANONICAL_MEMORY_KEYS = {
    "name",
    "has_file",
    "file_path",
    "content",
}


def clean_text(value: object) -> str:
    return str(value or "").strip()


def sanitize_filename_stem(raw_name: object) -> str:
    text = clean_text(raw_name)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^A-Za-z0-9_]", "", text)
    return text


def build_agent_filename(agent_name: object) -> str:
    clean_name = sanitize_filename_stem(agent_name)
    if not clean_name:
        raise ValueError("Agent name is required.")
    return f"{clean_name}.json"


def build_group_filename(group_name: object) -> str:
    clean_name = sanitize_filename_stem(group_name)
    if not clean_name:
        raise ValueError("Group name is required.")
    return f"{clean_name}.group.json"


def build_task_filename(task_name: object) -> str:
    clean_name = sanitize_filename_stem(task_name)
    if not clean_name:
        raise ValueError("Task name is required.")
    return f"{clean_name}.task.json"


def build_memory_filename(task_name: object, memory_name: object) -> str:
    clean_task_name = sanitize_filename_stem(task_name)
    clean_memory_name = sanitize_filename_stem(memory_name)

    if not clean_task_name:
        raise ValueError("Task name is required.")
    if not clean_memory_name:
        raise ValueError("Memory name is required.")

    return f"{clean_memory_name}__{clean_task_name}.memory.json"


def ensure_json_object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return value


def ensure_json_list(value: object, label: str) -> list[Any]:
    if value in (None, ""):
        return []

    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list.")

    return value


def require_known_keys(
    source: dict[str, Any],
    allowed_keys: set[str],
    label: str,
) -> None:
    unknown_keys = sorted(
        str(key)
        for key in source.keys()
        if str(key) not in allowed_keys
    )

    if unknown_keys:
        raise ValueError(
            f"{label} contains unknown field(s): {', '.join(unknown_keys)}"
        )


def strip_known_json_suffix(path_or_name: object) -> str:
    text = clean_text(path_or_name)
    if not text:
        return ""

    name = Path(text).name

    for suffix in (
        ".group.json",
        ".task.json",
        ".json",
    ):
        if name.endswith(suffix):
            return name[: -len(suffix)]

    return Path(name).stem
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any


AGENT_INDEX_FILE_NAME = "agent_index.json"
PACKAGE_INDEX_FILE_NAME = "package_index.json"
TASK_INDEX_FILE_NAME = "task_index.json"
GROUP_INDEX_FILE_NAME = "group_index.json"

BLUEPRINT_FILE_SUFFIX = ".blueprint.txt"
METADATA_FILE_SUFFIX = ".agent_foundry.json"
LEFTOVERS_FILE_SUFFIX = ".leftovers.agent_foundry.txt"

REQUIRED_OUTCASTS_GROUP_NAME = "Outcasts"

ROOT_AGENT_NAME = "Agent"


def _path(value: object) -> Path:
    return Path(value).expanduser().resolve()


def _get_agent_foundry_layout_from_handoff(handoff) -> dict[str, Path]:
    foundry_root = _path(handoff.get_agent_foundry_root_directory())
    agents_dir = _path(handoff.get_agent_foundry_agents_directory())
    packages_dir = _path(handoff.get_agent_foundry_packages_directory())
    tasks_dir = _path(handoff.get_agent_foundry_tasks_directory())
    groups_dir = _path(handoff.get_agent_foundry_groups_directory())
    indexes_dir = _path(handoff.get_agent_foundry_indexes_directory())

    agent_index_file = _path(handoff.get_agent_foundry_agent_index_file())
    package_index_file = _path(handoff.get_agent_foundry_package_index_file())
    task_index_file = _path(handoff.get_agent_foundry_task_index_file())
    group_index_file = _path(handoff.get_agent_foundry_group_index_file())

    return {
        "foundry_root": foundry_root,
        "agents_dir": agents_dir,
        "packages_dir": packages_dir,
        "tasks_dir": tasks_dir,
        "groups_dir": groups_dir,
        "indexes_dir": indexes_dir,
        "agent_index_file": agent_index_file,
        "package_index_file": package_index_file,
        "task_index_file": task_index_file,
        "group_index_file": group_index_file,
    }


def _ensure_agent_foundry_layout_from_handoff(handoff) -> dict[str, Path]:
    layout = _get_agent_foundry_layout_from_handoff(handoff)

    layout["foundry_root"].mkdir(parents=True, exist_ok=True)
    layout["agents_dir"].mkdir(parents=True, exist_ok=True)
    layout["packages_dir"].mkdir(parents=True, exist_ok=True)
    layout["tasks_dir"].mkdir(parents=True, exist_ok=True)
    layout["groups_dir"].mkdir(parents=True, exist_ok=True)
    layout["indexes_dir"].mkdir(parents=True, exist_ok=True)

    return layout


def _agent_dir_for_foundry_name(
    *,
    handoff,
    layout: dict[str, Path],
    foundry_name: str,
) -> Path:
    clean_name = handoff.sanitize_name("agent_foundry_workspace", foundry_name)
    if not clean_name:
        raise ValueError(f"Invalid Agent Foundry workspace name: {foundry_name!r}")

    return (layout["agents_dir"] / clean_name).expanduser().resolve()


def _agent_schema_file_for_agent_dir(agent_dir: Path) -> Path:
    return (agent_dir / f"{agent_dir.name}.json").expanduser().resolve()


def _blueprint_file_for_agent_dir(agent_dir: Path) -> Path:
    return (agent_dir / f"{agent_dir.name}{BLUEPRINT_FILE_SUFFIX}").expanduser().resolve()


def _metadata_file_for_agent_dir(agent_dir: Path) -> Path:
    return (agent_dir / f"{agent_dir.name}{METADATA_FILE_SUFFIX}").expanduser().resolve()


def _leftovers_file_for_agent_dir(agent_dir: Path) -> Path:
    return (agent_dir / f"{agent_dir.name}{LEFTOVERS_FILE_SUFFIX}").expanduser().resolve()


class AgentFoundryWorkspaceIndexMixin:
    def _update_agent_foundry_all_indexes_after_save(
        self,
        *,
        foundry_name: str,
        record: dict[str, Any],
        blueprint_path: Path,
        frontend_object: dict[str, Any],
        import_payload: dict[str, Any] | None = None,
    ) -> None:
        self._update_agent_foundry_agent_index_after_save(
            foundry_name=foundry_name,
            record=record,
            blueprint_path=blueprint_path,
            frontend_object=frontend_object,
            import_payload=import_payload,
        )

        handoff = self._get_agent_foundry_collection_handoff()
        layout = _ensure_agent_foundry_layout_from_handoff(handoff)
        ensure_empty_package_index(layout["package_index_file"])

    def _update_agent_foundry_metadata_after_save(
        self,
        *,
        foundry_name: str,
        record: dict[str, Any],
        blueprint_path: Path,
        leftovers_path: Path | None,
        frontend_object: dict[str, Any],
        import_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        clean_foundry_name = str(foundry_name or "").strip()
        if not clean_foundry_name:
            return dict(record or {})

        handoff = self._get_agent_foundry_collection_handoff()
        layout = _ensure_agent_foundry_layout_from_handoff(handoff)

        updated_record = dict(record or {})
        now_text = self._now_agent_foundry_text()

        blueprint_path = Path(blueprint_path).expanduser().resolve()
        agent_dir = blueprint_path.parent.expanduser().resolve()

        if agent_dir.name != clean_foundry_name:
            record_workspace_dir = self._coerce_optional_path(
                updated_record.get("workspace_dir")
            )
            if record_workspace_dir is not None:
                agent_dir = record_workspace_dir.expanduser().resolve()
            else:
                agent_dir = _agent_dir_for_foundry_name(
                    handoff=handoff,
                    layout=layout,
                    foundry_name=clean_foundry_name,
                )

        metadata_file = _metadata_file_for_agent_dir(agent_dir)

        if leftovers_path is None:
            leftovers_path = _leftovers_file_for_agent_dir(agent_dir)
        else:
            leftovers_path = Path(leftovers_path).expanduser().resolve()

        agent_name = self._resolve_agent_foundry_agent_name_for_save(
            foundry_name=clean_foundry_name,
            record=updated_record,
            frontend_object=frontend_object,
        )

        updated_record["updated_at"] = now_text
        updated_record["last_updated_in_foundry"] = now_text
        updated_record["agent_name"] = agent_name
        updated_record["name"] = clean_foundry_name
        updated_record["foundry_name"] = clean_foundry_name
        updated_record["storage_root"] = str(layout["foundry_root"].resolve())
        updated_record["agent_dir"] = str(agent_dir.resolve())
        updated_record["workspace_dir"] = str(agent_dir.resolve())
        updated_record["blueprint_file"] = str(blueprint_path.resolve())
        updated_record["metadata_file"] = str(metadata_file.resolve())
        updated_record["leftovers_file"] = str(leftovers_path.resolve())
        updated_record["agent_index_file"] = str(layout["agent_index_file"].resolve())
        updated_record["package_index_file"] = str(layout["package_index_file"].resolve())
        updated_record["task_index_file"] = str(layout["task_index_file"].resolve())
        updated_record["group_index_file"] = str(layout["group_index_file"].resolve())
        updated_record["agent_foundry_packages_dir"] = str(layout["packages_dir"].resolve())
        updated_record["agent_foundry_tasks_dir"] = str(layout["tasks_dir"].resolve())
        updated_record["agent_foundry_groups_dir"] = str(layout["groups_dir"].resolve())
        updated_record["source_verification_status"] = "passed"

        updated_record.pop("packages_dir", None)

        import_patch = self._get_agent_foundry_import_index_patch(import_payload)
        if import_patch:
            for key, value in import_patch.items():
                if key in {"agent_name", "name"}:
                    continue
                updated_record[key] = value

        record_map = getattr(self, "agent_foundry_record_map", None)
        if isinstance(record_map, dict):
            record_map[clean_foundry_name] = updated_record

        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        metadata_file.write_text(
            json.dumps(
                {
                    "record": updated_record,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        try:
            saved_record = handoff.save_agent_foundry_metadata(
                foundry_name=clean_foundry_name,
                record=updated_record,
            )

            saved_metadata_path = self._coerce_optional_path(
                saved_record.get("record_path") if isinstance(saved_record, dict) else ""
            )
            if saved_metadata_path is not None:
                updated_record["metadata_file"] = str(saved_metadata_path.resolve())

            if isinstance(record_map, dict):
                record_map[clean_foundry_name] = updated_record

        except Exception:
            pass

        return updated_record

    def _update_agent_foundry_agent_index_after_save(
        self,
        *,
        foundry_name: str,
        record: dict[str, Any],
        blueprint_path: Path,
        frontend_object: dict[str, Any],
        import_payload: dict[str, Any] | None = None,
    ) -> None:
        clean_foundry_name = str(foundry_name or "").strip()
        if not clean_foundry_name:
            return

        handoff = self._get_agent_foundry_collection_handoff()
        layout = _ensure_agent_foundry_layout_from_handoff(handoff)

        blueprint_path = Path(blueprint_path).expanduser().resolve()
        agent_dir = blueprint_path.parent.expanduser().resolve()

        if agent_dir.name != clean_foundry_name:
            record_workspace_dir = self._coerce_optional_path(record.get("workspace_dir"))
            if record_workspace_dir is not None:
                agent_dir = record_workspace_dir.expanduser().resolve()
            else:
                agent_dir = _agent_dir_for_foundry_name(
                    handoff=handoff,
                    layout=layout,
                    foundry_name=clean_foundry_name,
                )

        metadata_file = _metadata_file_for_agent_dir(agent_dir)
        agent_index_file = layout["agent_index_file"]

        agent_id = self._get_agent_foundry_agent_id_for_save(
            foundry_name=clean_foundry_name,
            record=record,
            workspace_dir=agent_dir,
        )
        if agent_id <= 0:
            return

        agent_name = self._resolve_agent_foundry_agent_name_for_save(
            foundry_name=clean_foundry_name,
            record=record,
            frontend_object=frontend_object,
        )

        agent_index = load_or_create_agent_index(agent_index_file)
        validate_agent_index(agent_index, agent_index_file)

        now_text = self._now_agent_foundry_text()
        import_patch = self._get_agent_foundry_import_index_patch(import_payload)
        matched = False

        for entry in agent_index["agents"]:
            if not isinstance(entry, dict):
                continue

            try:
                entry_agent_id = int(entry.get("agent_id"))
            except Exception:
                continue

            if entry_agent_id != agent_id:
                continue

            if not str(entry.get("created_at", "") or "").strip():
                entry["created_at"] = now_text

            entry["foundry_name"] = clean_foundry_name
            entry["agent_dir"] = str(agent_dir.resolve())
            entry["workspace_dir"] = str(agent_dir.resolve())
            entry["metadata_file"] = str(metadata_file.resolve())
            entry["blueprint_file"] = str(blueprint_path.resolve())
            entry["agent_name"] = agent_name
            entry["updated_at"] = now_text
            entry["last_updated_in_foundry"] = now_text
            entry.pop("packages_dir", None)

            for key, value in import_patch.items():
                if key in {"agent_name", "name"}:
                    continue
                entry[key] = value

            matched = True
            break

        if not matched:
            new_entry = {
                "agent_id": agent_id,
                "agent_key": str(record.get("agent_key", "") or ""),
                "agent_index_key": str(
                    record.get("agent_index_key", record.get("agent_key", "")) or ""
                ),
                "foundry_name": clean_foundry_name,
                "agent_dir": str(agent_dir.resolve()),
                "workspace_dir": str(agent_dir.resolve()),
                "metadata_file": str(metadata_file.resolve()),
                "blueprint_file": str(blueprint_path.resolve()),
                "agent_name": agent_name,
                "created_at": now_text,
                "updated_at": now_text,
                "last_updated_in_foundry": now_text,
            }

            for key, value in import_patch.items():
                if key in {"agent_name", "name"}:
                    continue
                new_entry[key] = value

            agent_index.setdefault("agents", []).append(new_entry)

        agent_index["last_agent_id"] = max(
            int(agent_index.get("last_agent_id", 0) or 0),
            agent_id,
        )

        save_agent_index(agent_index_file, agent_index)


def create_foundry_draft(
    *,
    handoff,
    agent_name: str = "",
    blueprint_text: str = "",
    leftovers_text: str = "",
    import_index_patch: dict[str, Any] | None = None,
    imported_agent_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    layout = _ensure_agent_foundry_layout_from_handoff(handoff)

    requested_agent_name = str(agent_name or "").strip()
    if not requested_agent_name:
        raise ValueError("Agent name is required.")

    clean_agent_name = handoff.sanitize_name(
        "agent_foundry_workspace",
        requested_agent_name,
    )
    if not clean_agent_name:
        raise ValueError(f"Agent name sanitized blank: {requested_agent_name!r}")

    agent_index_path = layout["agent_index_file"]
    package_index_path = layout["package_index_file"]
    task_index_path = layout["task_index_file"]
    group_index_path = layout["group_index_file"]

    agent_index = load_or_create_agent_index(agent_index_path)

    agent_id = reserve_next_agent_id(agent_index)
    agent_key = f"agent_{agent_id:06d}"
    clean_agent_key = handoff.sanitize_name("agent_foundry_workspace", agent_key)

    if clean_agent_key != agent_key:
        raise ValueError(
            "Agent index key did not sanitize cleanly. This should never happen.\n\n"
            f"Raw key: {agent_key}\n"
            f"Sanitized key: {clean_agent_key}"
        )

    assert_agent_id_is_not_registered(
        agent_index=agent_index,
        agent_id=agent_id,
    )

    agent_dir = _agent_dir_for_foundry_name(
        handoff=handoff,
        layout=layout,
        foundry_name=clean_agent_name,
    )

    if agent_dir.exists():
        raise FileExistsError(f"Agent Foundry agent folder already exists: {agent_dir}")

    agent_schema_file = _agent_schema_file_for_agent_dir(agent_dir)
    blueprint_file = _blueprint_file_for_agent_dir(agent_dir)
    metadata_file = _metadata_file_for_agent_dir(agent_dir)
    leftovers_file = _leftovers_file_for_agent_dir(agent_dir)

    agent_dir.mkdir(parents=True, exist_ok=False)

    for expected_file in (
        agent_schema_file,
        blueprint_file,
        metadata_file,
        leftovers_file,
    ):
        if expected_file.exists():
            raise FileExistsError(f"Agent Foundry file already exists: {expected_file}")

    now_text = datetime.now().isoformat(timespec="seconds")

    if str(blueprint_text or "").strip():
        blueprint_seed_text = ensure_agent_index_id_block_in_blueprint(
            blueprint_text=str(blueprint_text or ""),
            agent_index_key=clean_agent_key,
        )
    else:
        blueprint_seed_text = build_created_agent_blueprint_seed(
            agent_name=clean_agent_name,
            agent_index_key=clean_agent_key,
        )

    blueprint_file.write_text(
        normalize_text_file_content(blueprint_seed_text),
        encoding="utf-8",
    )

    leftovers_file.write_text(
        normalize_text_file_content(leftovers_text),
        encoding="utf-8",
    )

    if isinstance(imported_agent_schema, dict):
        write_agent_schema_file(
            output_file=agent_schema_file,
            agent_schema=normalize_imported_agent_schema(
                agent_schema=imported_agent_schema,
                agent_id=agent_id,
                agent_name=clean_agent_name,
                agent_key=clean_agent_key,
            ),
        )
    else:
        write_empty_agent_schema(
            output_file=agent_schema_file,
            agent_id=agent_id,
            agent_name=clean_agent_name,
            agent_key=clean_agent_key,
        )

    agent_schema_file = agent_schema_file.expanduser().resolve()
    blueprint_file = blueprint_file.expanduser().resolve()
    leftovers_file = leftovers_file.expanduser().resolve()
    metadata_file = metadata_file.expanduser().resolve()

    import_patch = (
        dict(import_index_patch or {})
        if isinstance(import_index_patch, dict)
        else {}
    )

    metadata_record = {
        "agent_id": agent_id,
        "id": agent_id,
        "draft_id": agent_id,
        "agent_key": clean_agent_key,
        "agent_index_key": clean_agent_key,
        "draft_key": clean_agent_name,
        "foundry_name": clean_agent_name,
        "name": clean_agent_name,
        "agent_name": clean_agent_name,
        "requested_agent_name": requested_agent_name,
        "status": "Draft",
        "created_at": now_text,
        "updated_at": now_text,
        "last_updated_in_foundry": now_text,
        "storage_root": str(layout["foundry_root"].resolve()),
        "agent_dir": str(agent_dir.resolve()),
        "workspace_dir": str(agent_dir.resolve()),
        "blueprint_file": str(blueprint_file.resolve()),
        "leftovers_file": str(leftovers_file.resolve()),
        "metadata_file": str(metadata_file.resolve()),
        "draft_agent_schema_file": str(agent_schema_file.resolve()),
        "agent_index_file": str(agent_index_path.resolve()),
        "package_index_file": str(package_index_path.resolve()),
        "task_index_file": str(task_index_path.resolve()),
        "group_index_file": str(group_index_path.resolve()),
        "agent_foundry_packages_dir": str(layout["packages_dir"].resolve()),
        "agent_foundry_tasks_dir": str(layout["tasks_dir"].resolve()),
        "agent_foundry_groups_dir": str(layout["groups_dir"].resolve()),
        "package_drafts_created": False,
        "agent_schema_applied": False,
        "apply_stage": "draft_created",
    }

    for key, value in import_patch.items():
        if key in {"agent_name", "name"}:
            continue
        metadata_record[key] = value

    metadata_file.write_text(
        json.dumps(
            {
                "record": metadata_record,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        saved_record = handoff.save_agent_foundry_metadata(
            foundry_name=clean_agent_name,
            record=metadata_record,
        )
        saved_metadata_path = Path(saved_record["record_path"]).expanduser().resolve()
        metadata_record["metadata_file"] = str(saved_metadata_path)
        metadata_file = saved_metadata_path

        handoff.save_agent_foundry_metadata(
            foundry_name=clean_agent_name,
            record=metadata_record,
        )
    except Exception:
        metadata_file.write_text(
            json.dumps(
                {
                    "record": metadata_record,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    register_agent_id(
        agent_index=agent_index,
        agent_id=agent_id,
        foundry_name=clean_agent_name,
        agent_dir=agent_dir,
        metadata_file=metadata_file,
        blueprint_file=blueprint_file,
        agent_name=clean_agent_name,
        agent_key=clean_agent_key,
        created_at=now_text,
        extra_index_fields=import_patch,
    )
    save_agent_index(agent_index_path, agent_index)

    ensure_empty_package_index(package_index_path)

    return {
        "foundry_name": clean_agent_name,
        "agent_id": agent_id,
        "agent_key": clean_agent_key,
        "agent_index_key": clean_agent_key,
        "agent_name": clean_agent_name,
        "requested_agent_name": requested_agent_name,
        "storage_root": str(layout["foundry_root"].resolve()),
        "agent_dir": str(agent_dir.resolve()),
        "workspace_dir": str(agent_dir.resolve()),
        "blueprint_file": str(blueprint_file.resolve()),
        "leftovers_file": str(leftovers_file.resolve()),
        "agent_file": str(agent_schema_file.resolve()),
        "metadata_file": str(metadata_file.resolve()),
        "agent_index_file": str(agent_index_path.resolve()),
        "package_index_file": str(package_index_path.resolve()),
        "task_index_file": str(task_index_path.resolve()),
        "group_index_file": str(group_index_path.resolve()),
        "agent_foundry_packages_dir": str(layout["packages_dir"].resolve()),
        "agent_foundry_tasks_dir": str(layout["tasks_dir"].resolve()),
        "agent_foundry_groups_dir": str(layout["groups_dir"].resolve()),
        "metadata_record": metadata_record,
    }


def normalize_text_file_content(value: object) -> str:
    text = str(value or "").rstrip()
    if text:
        return text + "\n"
    return ""


def ensure_agent_index_id_block_in_blueprint(
    *,
    blueprint_text: str,
    agent_index_key: str,
) -> str:
    source_text = str(blueprint_text or "").rstrip()
    clean_agent_index_key = str(agent_index_key or "").strip()
    if not clean_agent_index_key:
        return normalize_text_file_content(source_text)

    block_text = (
        "Agent Index ID:\n"
        f"- {clean_agent_index_key}\n"
        "End Agent Index ID"
    )

    start_pattern = re.compile(r"(?im)^\s*Agent\s+Index\s+ID\s*:\s*$")
    start_match = start_pattern.search(source_text)
    if start_match is None:
        if source_text:
            return normalize_text_file_content(source_text + "\n\n" + block_text)
        return normalize_text_file_content(block_text)

    end_pattern = re.compile(r"(?im)^\s*End\s+Agent\s+Index\s+ID\s*$")
    end_match = end_pattern.search(source_text, start_match.end())
    if end_match is None:
        if source_text:
            return normalize_text_file_content(source_text + "\n\n" + block_text)
        return normalize_text_file_content(block_text)

    updated_text = (
        source_text[:start_match.start()].rstrip()
        + ("\n\n" if source_text[:start_match.start()].strip() else "")
        + block_text
        + ("\n\n" if source_text[end_match.end():].strip() else "")
        + source_text[end_match.end():].lstrip()
    )
    return normalize_text_file_content(updated_text)


def normalize_imported_agent_schema(
    *,
    agent_schema: dict[str, Any],
    agent_id: int,
    agent_name: str,
    agent_key: str,
) -> dict[str, Any]:
    normalized = dict(agent_schema or {})
    normalized["agent_id"] = agent_id
    normalized["agent_key"] = str(agent_key or "")
    normalized["name"] = str(agent_name or "")
    normalized.setdefault("default_returns", [])
    normalized.setdefault("groups", [])
    return normalized


def build_created_agent_blueprint_seed(
    agent_name: str,
    agent_index_key: str = "",
) -> str:
    clean_agent_name = str(agent_name or "").strip()
    if not clean_agent_name:
        clean_agent_name = "UnnamedAgent"

    clean_agent_index_key = str(agent_index_key or "").strip()
    if not clean_agent_index_key:
        clean_agent_index_key = "agent_000000"

    parts = [
        (
            "Agent ID:\n"
            f"- {clean_agent_name}\n"
            "End Agent ID"
        ),
        (
            "Agent Index ID:\n"
            f"- {clean_agent_index_key}\n"
            "End Agent Index ID"
        ),
        (
            f"{clean_agent_name} Seeded Groups:\n"
            f"- {REQUIRED_OUTCASTS_GROUP_NAME}\n"
            f"End {clean_agent_name} Seeded Groups"
        ),
    ]

    return "\n\n".join(
        part.strip()
        for part in parts
        if str(part or "").strip()
    ).rstrip() + "\n"


def write_empty_agent_schema(
    output_file: Path,
    agent_id: int | str | None = "",
    agent_name: str = "",
    agent_key: str = "",
) -> Path:
    return write_agent_schema_file(
        output_file=output_file,
        agent_schema=create_baseline_agent_schema(
            agent_id=agent_id,
            agent_name=agent_name,
            agent_key=agent_key,
        ),
    )


def write_agent_schema_file(
    *,
    output_file: str | Path,
    agent_schema: dict[str, Any],
) -> Path:
    output_path = _path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(agent_schema, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def create_baseline_agent_schema(
    agent_id: int | str | None = "",
    agent_name: str = "",
    agent_key: str = "",
) -> dict[str, Any]:
    return {
        "agent_id": agent_id if agent_id is not None else "",
        "agent_key": str(agent_key or ""),
        "name": str(agent_name or ""),
        "default_returns": [],
        "groups": [],
    }


def load_or_create_agent_index(index_path: str | Path) -> dict[str, Any]:
    resolved_path = _path(index_path)

    if not resolved_path.exists():
        return {
            "version": 1,
            "last_agent_id": 0,
            "agents": [],
        }

    raw_text = resolved_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        return {
            "version": 1,
            "last_agent_id": 0,
            "agents": [],
        }

    data = json.loads(raw_text)
    validate_agent_index(data, resolved_path)
    return data


def validate_agent_index(agent_index: dict[str, Any], index_path: Path | None = None) -> None:
    if not isinstance(agent_index, dict):
        raise ValueError(f"Agent index must be a dictionary: {index_path}")

    if "version" not in agent_index:
        agent_index["version"] = 1

    if "last_agent_id" not in agent_index:
        agent_index["last_agent_id"] = 0

    try:
        agent_index["last_agent_id"] = int(agent_index["last_agent_id"])
    except Exception as exc:
        raise ValueError(f"Agent index last_agent_id is invalid: {index_path}") from exc

    agents = agent_index.get("agents", [])
    if not isinstance(agents, list):
        raise ValueError(f"Agent index agents must be a list: {index_path}")

    agent_index["agents"] = agents


def save_agent_index(index_path: str | Path, agent_index: dict[str, Any]) -> Path:
    resolved_path = _path(index_path)
    validate_agent_index(agent_index, resolved_path)

    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(
        json.dumps(agent_index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return resolved_path


def reserve_next_agent_id(agent_index: dict[str, Any]) -> int:
    validate_agent_index(agent_index)
    current_id = int(agent_index.get("last_agent_id", 0) or 0)
    next_id = current_id + 1
    agent_index["last_agent_id"] = next_id
    return next_id


def assert_agent_id_is_not_registered(
    *,
    agent_index: dict[str, Any],
    agent_id: int,
) -> None:
    validate_agent_index(agent_index)

    for entry in agent_index["agents"]:
        if not isinstance(entry, dict):
            continue

        if int(entry.get("agent_id", -1)) == int(agent_id):
            raise ValueError(f"Agent id is already registered: {agent_id}")


def register_agent_id(
    *,
    agent_index: dict[str, Any],
    agent_id: int,
    foundry_name: str,
    agent_dir: Path,
    metadata_file: Path,
    blueprint_file: Path,
    agent_name: str,
    agent_key: str,
    created_at: str,
    extra_index_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_agent_index(agent_index)
    assert_agent_id_is_not_registered(
        agent_index=agent_index,
        agent_id=agent_id,
    )

    entry = {
        "agent_id": int(agent_id),
        "agent_key": str(agent_key or ""),
        "agent_index_key": str(agent_key or ""),
        "foundry_name": str(foundry_name or ""),
        "agent_dir": str(Path(agent_dir).expanduser().resolve()),
        "workspace_dir": str(Path(agent_dir).expanduser().resolve()),
        "metadata_file": str(Path(metadata_file).expanduser().resolve()),
        "blueprint_file": str(Path(blueprint_file).expanduser().resolve()),
        "agent_name": str(agent_name or foundry_name or ""),
        "created_at": str(created_at or ""),
        "updated_at": str(created_at or ""),
        "last_updated_in_foundry": str(created_at or ""),
    }

    if isinstance(extra_index_fields, dict):
        for key, value in extra_index_fields.items():
            if key in {"agent_name", "name"}:
                continue
            entry[key] = value

    entry.pop("packages_dir", None)

    agent_index["agents"].append(entry)
    agent_index["last_agent_id"] = max(
        int(agent_index.get("last_agent_id", 0) or 0),
        int(agent_id),
    )
    return entry


def load_or_create_package_index(index_path: str | Path) -> dict[str, Any]:
    resolved_path = _path(index_path)

    if not resolved_path.exists():
        return {
            "version": 1,
            "last_package_number": 0,
            "packages": [],
        }

    raw_text = resolved_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        return {
            "version": 1,
            "last_package_number": 0,
            "packages": [],
        }

    data = json.loads(raw_text)
    validate_package_index(data, resolved_path)
    return data


def validate_package_index(package_index: dict[str, Any], index_path: Path | None = None) -> None:
    if not isinstance(package_index, dict):
        raise ValueError(f"Package index must be a dictionary: {index_path}")

    if "version" not in package_index:
        package_index["version"] = 1

    if "last_package_number" not in package_index:
        package_index["last_package_number"] = 0

    try:
        package_index["last_package_number"] = int(package_index["last_package_number"])
    except Exception as exc:
        raise ValueError(f"Package index last_package_number is invalid: {index_path}") from exc

    packages = package_index.get("packages", [])
    if not isinstance(packages, list):
        raise ValueError(f"Package index packages must be a list: {index_path}")

    package_index["packages"] = packages


def save_package_index(index_path: str | Path, package_index: dict[str, Any]) -> Path:
    resolved_path = _path(index_path)
    validate_package_index(package_index, resolved_path)

    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(
        json.dumps(package_index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return resolved_path


def ensure_empty_package_index(index_path: str | Path) -> Path:
    package_index = load_or_create_package_index(index_path)
    return save_package_index(index_path, package_index)
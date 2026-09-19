from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
from typing import Any

from Environment.agent_foundry.foundry_workspace_index import create_foundry_draft


AGENT_INDEX_FILE_NAME = "agent_index.json"
LEFTOVERS_FILE_SUFFIX = ".leftovers.agent_foundry.txt"
BLUEPRINT_FILE_SUFFIX = ".blueprint.txt"
METADATA_FILE_SUFFIX = ".agent_foundry.json"

ROOT_AGENT_ID = "agent"
ROOT_LEFTOVERS_ID = "leftovers"
ROOT_VIEWER_ID = "viewer"

ROOT_AGENT_NAME = "Agent"
GRAMMAR_SUFFIX_ID = "ID"


def _path(value: object) -> Path:
    return Path(value).expanduser().resolve()


class AgentFoundryWorkspaceVerificationMixin:
    LEFTOVERS_FILE_SUFFIX = LEFTOVERS_FILE_SUFFIX

    def _save_agent_foundry_current_frontend_object_to_files(
        self,
        *,
        import_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        foundry_name = str(getattr(self, "agent_foundry_loaded_name", "") or "").strip()
        if not foundry_name:
            return {}

        record_map = getattr(self, "agent_foundry_record_map", {})
        record = record_map.get(foundry_name) if isinstance(record_map, dict) else {}
        if not isinstance(record, dict):
            record = {}

        frontend_object = self._get_current_foundry_frontend_object()
        if not isinstance(frontend_object, dict):
            raise ValueError("No live Agent Foundry frontend object is available to save.")

        blueprint_path = self._resolve_current_agent_foundry_blueprint_path(
            foundry_name=foundry_name,
            record=record,
        )

        leftovers_path = self._get_leftovers_path_for_foundry(
            foundry_name=foundry_name,
            record=record,
        )

        (
            blueprint_text,
            leftovers_text,
            _agent_json_text,
            runtime_file,
        ) = self._compose_agent_foundry_save_texts_from_frontend_object(
            frontend_object=frontend_object,
        )

        return self._save_agent_foundry_texts_to_files(
            foundry_name=foundry_name,
            record=record,
            blueprint_path=blueprint_path,
            leftovers_path=leftovers_path,
            blueprint_text=blueprint_text,
            leftovers_text=leftovers_text,
            runtime_file=runtime_file,
            frontend_object=frontend_object,
            import_payload=import_payload,
        )

    def _save_agent_foundry_import_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("Import payload must be a dictionary.")

        agent_name = str(payload.get("agent_name", "") or "").strip()
        if not agent_name:
            raise ValueError("Import payload is missing agent_name.")

        blueprint_text = str(payload.get("blueprint_text", "") or "")
        leftovers_text = str(payload.get("leftovers_text", "") or "")

        if not blueprint_text.strip():
            raise ValueError(f"Import payload for {agent_name!r} has no blueprint_text.")

        self._refresh_agent_foundry_workspaces()

        foundry_name, record = self._find_agent_foundry_record_for_import(payload)

        if not foundry_name:
            return self._create_agent_foundry_workspace_from_import(payload)

        return self._update_agent_foundry_workspace_from_import(
            foundry_name=foundry_name,
            record=record,
            payload=payload,
            blueprint_text=blueprint_text,
            leftovers_text=leftovers_text,
        )

    def _create_agent_foundry_workspace_from_import(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        agent_name = str(payload.get("agent_name", "") or "").strip()
        if not agent_name:
            raise ValueError("Import payload is missing agent_name.")

        result = create_foundry_draft(
            handoff=self._get_agent_foundry_collection_handoff(),
            agent_name=agent_name,
            blueprint_text=str(payload.get("blueprint_text", "") or ""),
            leftovers_text=str(payload.get("leftovers_text", "") or ""),
            import_index_patch=self._get_agent_foundry_import_index_patch(payload),
            imported_agent_schema=None,
        )

        self._refresh_agent_foundry_workspaces()

        foundry_name = str(result.get("foundry_name", "") or "").strip()
        record = dict(result.get("metadata_record", {}) or {})
        if foundry_name and record:
            record_map = getattr(self, "agent_foundry_record_map", None)
            if isinstance(record_map, dict):
                record_map[foundry_name] = record

        return {
            "status": "created",
            "foundry_name": foundry_name,
            "agent_id": result.get("agent_id", ""),
            "agent_index_id": result.get("agent_key", result.get("agent_index_key", "")),
            "agent_key": result.get("agent_key", ""),
            "agent_name": result.get("agent_name", agent_name),
            "foundry_blueprint_path": result.get("blueprint_file", ""),
            "leftovers_file": result.get("leftovers_file", ""),
            "metadata_file": result.get("metadata_file", ""),
            "workspace_dir": result.get("workspace_dir", ""),
        }

    def _update_agent_foundry_workspace_from_import(
        self,
        *,
        foundry_name: str,
        record: dict[str, Any],
        payload: dict[str, Any],
        blueprint_text: str,
        leftovers_text: str,
    ) -> dict[str, Any]:
        clean_foundry_name = str(foundry_name or "").strip()
        if not clean_foundry_name:
            raise ValueError("Cannot update Foundry import without foundry_name.")

        record = dict(record or {})

        blueprint_path = self._get_blueprint_path_for_foundry(
            foundry_name=clean_foundry_name,
            record=record,
        )
        leftovers_path = self._get_leftovers_path_for_foundry(
            foundry_name=clean_foundry_name,
            record=record,
        )

        frontend_object = self._build_minimal_frontend_object_for_direct_save(
            blueprint_text=blueprint_text,
            leftovers_text=leftovers_text,
            viewer_text="",
        )

        save_result = self._save_agent_foundry_texts_to_files(
            foundry_name=clean_foundry_name,
            record=record,
            blueprint_path=blueprint_path,
            leftovers_path=leftovers_path,
            blueprint_text=blueprint_text,
            leftovers_text=leftovers_text,
            runtime_file=None,
            frontend_object=frontend_object,
            import_payload=payload,
        )

        save_result["status"] = "updated"
        return save_result

    def _save_agent_foundry_texts_to_files(
        self,
        *,
        foundry_name: str,
        record: dict[str, Any],
        blueprint_path: Path,
        leftovers_path: Path | None,
        blueprint_text: str,
        leftovers_text: str,
        runtime_file: dict[str, Any] | None = None,
        frontend_object: dict[str, Any],
        import_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        clean_foundry_name = str(foundry_name or "").strip()
        if not clean_foundry_name:
            return {}

        blueprint_path = Path(blueprint_path).expanduser().resolve()
        workspace_dir = blueprint_path.parent.expanduser().resolve()

        if leftovers_path is None:
            leftovers_path = self._leftovers_path_from_workspace_dir(
                workspace_dir=workspace_dir,
            )
        else:
            leftovers_path = Path(leftovers_path).expanduser().resolve()

        blueprint_text = self._normalize_agent_foundry_text_for_file(blueprint_text)
        leftovers_text = self._normalize_agent_foundry_text_for_file(leftovers_text)

        workspace_dir.mkdir(parents=True, exist_ok=True)

        blueprint_path.write_text(blueprint_text, encoding="utf-8")
        leftovers_path.write_text(leftovers_text, encoding="utf-8")

        runtime_file_path = self._write_agent_foundry_runtime_file(
            blueprint_path=blueprint_path,
            runtime_file=runtime_file,
        )

        runtime_viewer_text = self._read_agent_foundry_runtime_viewer_text(
            runtime_file_path=runtime_file_path,
            runtime_file=runtime_file,
        )

        combined_text = self._combine_blueprint_and_leftovers_for_load(
            blueprint_text=blueprint_text,
            leftovers_text=leftovers_text,
        )

        self.agent_foundry_blueprint_path = blueprint_path
        self.agent_foundry_loaded_blueprint_only_text = blueprint_text
        self.agent_foundry_loaded_blueprint_text = combined_text
        self.agent_foundry_last_saved_blueprint_text = blueprint_text
        self.agent_foundry_loaded_leftovers_text = leftovers_text
        self.agent_foundry_last_saved_leftovers_text = leftovers_text
        self.agent_foundry_loaded_viewer_text = runtime_viewer_text
        self.agent_foundry_last_saved_viewer_text = runtime_viewer_text
        self.agent_foundry_dirty = False

        edited_scopes = getattr(self, "agent_foundry_edited_scopes", None)
        if isinstance(edited_scopes, set):
            edited_scopes.clear()

        updated_record = self._update_agent_foundry_metadata_after_save(
            foundry_name=clean_foundry_name,
            record=record,
            blueprint_path=blueprint_path,
            leftovers_path=leftovers_path,
            frontend_object=frontend_object,
            import_payload=import_payload,
        )

        if runtime_file_path is not None:
            updated_record["runtime_file"] = str(runtime_file_path.expanduser().resolve())

        updated_record.pop("draft_agent_schema_file", None)
        updated_record.pop("agent_schema_file", None)
        updated_record.pop("agent_file", None)

        record_map = getattr(self, "agent_foundry_record_map", None)
        if isinstance(record_map, dict):
            record_map[clean_foundry_name] = updated_record

        metadata_file = self._metadata_path_from_workspace_dir(workspace_dir=workspace_dir)
        updated_record["metadata_file"] = str(metadata_file.resolve())

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

        self._update_agent_foundry_all_indexes_after_save(
            foundry_name=clean_foundry_name,
            record=updated_record,
            blueprint_path=blueprint_path,
            frontend_object=frontend_object,
            import_payload=import_payload,
        )

        return {
            "status": "saved",
            "foundry_name": clean_foundry_name,
            "agent_id": updated_record.get("agent_id", updated_record.get("id", "")),
            "agent_index_id": updated_record.get(
                "agent_key",
                updated_record.get("agent_index_key", ""),
            ),
            "agent_key": updated_record.get("agent_key", ""),
            "agent_name": updated_record.get("agent_name", clean_foundry_name),
            "foundry_blueprint_path": str(blueprint_path.expanduser().resolve()),
            "leftovers_file": str(leftovers_path.expanduser().resolve()),
            "runtime_file": str(runtime_file_path.expanduser().resolve()) if runtime_file_path is not None else "",
            "metadata_file": str(updated_record.get("metadata_file", "") or ""),
            "workspace_dir": str(updated_record.get("workspace_dir", "") or str(workspace_dir)),
        }

    def _write_agent_foundry_runtime_file(
        self,
        *,
        blueprint_path: Path,
        runtime_file: dict[str, Any] | None,
    ) -> Path | None:
        if not isinstance(runtime_file, dict):
            return None

        runtime_file_name = str(runtime_file.get("file_name", "") or "").strip()
        runtime_file_content = str(runtime_file.get("content", "") or "").rstrip()

        if not runtime_file_name:
            return None

        if not runtime_file_content:
            runtime_data = runtime_file.get("data", {})
            if isinstance(runtime_data, dict):
                runtime_file_content = json.dumps(
                    runtime_data,
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=False,
                ).rstrip()

        if not runtime_file_content:
            return None

        runtime_file_path = blueprint_path.parent / runtime_file_name
        runtime_file_path.parent.mkdir(parents=True, exist_ok=True)
        runtime_file_path.write_text(
            self._normalize_agent_foundry_text_for_file(runtime_file_content),
            encoding="utf-8",
        )

        return runtime_file_path

    def _read_agent_foundry_runtime_viewer_text(
        self,
        *,
        runtime_file_path: Path | None,
        runtime_file: dict[str, Any] | None,
    ) -> str:
        if runtime_file_path is not None and runtime_file_path.exists():
            try:
                raw_text = runtime_file_path.read_text(encoding="utf-8")
                clean_text = raw_text.strip()
                if clean_text:
                    try:
                        parsed_json = json.loads(clean_text)
                    except json.JSONDecodeError:
                        return clean_text.rstrip() + "\n"

                    return json.dumps(parsed_json, indent=2, ensure_ascii=False).rstrip() + "\n"
            except Exception:
                pass

        if isinstance(runtime_file, dict):
            content = str(runtime_file.get("content", "") or "").strip()
            if content:
                return content.rstrip() + "\n"

            data = runtime_file.get("data", {})
            if isinstance(data, dict):
                return json.dumps(data, indent=2, ensure_ascii=False).rstrip() + "\n"

        return "No runtime.json file is currently available.\n"

    def _normalize_agent_foundry_text_for_file(self, value: object) -> str:
        text = str(value or "").rstrip()
        if text:
            return text + "\n"
        return ""

    def _build_minimal_frontend_object_for_direct_save(
        self,
        *,
        blueprint_text: str,
        leftovers_text: str,
        viewer_text: str = "",
    ) -> dict[str, Any]:
        return {
            "object_type": "agent_foundry_direct_save_source",
            "schema_version": "direct_text.v1",
            "root_node_ids": [],
            "nodes": {
                ROOT_AGENT_ID: {
                    "id": ROOT_AGENT_ID,
                    "name": ROOT_AGENT_NAME,
                    "kind": "agent",
                    "area": "content",
                    "content": str(blueprint_text or ""),
                    "children": [],
                },
                ROOT_LEFTOVERS_ID: {
                    "id": ROOT_LEFTOVERS_ID,
                    "name": "Leftovers",
                    "kind": "leftovers",
                    "area": "content",
                    "content": str(leftovers_text or ""),
                    "children": [],
                },
                ROOT_VIEWER_ID: {
                    "id": ROOT_VIEWER_ID,
                    "name": "Viewer",
                    "kind": "static",
                    "area": "content",
                    "content": str(viewer_text or ""),
                    "children": [],
                    "data": {
                        "source": "runtime_file",
                        "parser_search_exclude": True,
                        "save_exclude": True,
                    },
                },
            },
        }

    def _find_agent_foundry_record_for_import(
        self,
        payload: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        agent_name = str(payload.get("agent_name", "") or "").strip()
        agent_index_id = str(payload.get("agent_index_id", "") or "").strip()
        assembly_path = str(payload.get("assembly_agent_json_path", "") or "").strip()

        record_map = getattr(self, "agent_foundry_record_map", None)
        if not isinstance(record_map, dict):
            record_map = {}

        if assembly_path:
            assembly_key = str(Path(assembly_path).expanduser().resolve()).lower()
            for foundry_name, record in record_map.items():
                if not isinstance(record, dict):
                    continue

                record_assembly_path = str(record.get("assembly_agent_json_path", "") or "").strip()
                if not record_assembly_path:
                    continue

                try:
                    record_key = str(Path(record_assembly_path).expanduser().resolve()).lower()
                except Exception:
                    record_key = record_assembly_path.lower()

                if record_key == assembly_key:
                    return str(foundry_name or "").strip(), dict(record)

        if agent_index_id:
            for foundry_name, record in record_map.items():
                if not isinstance(record, dict):
                    continue

                if agent_index_id in {
                    str(record.get("agent_key", "") or "").strip(),
                    str(record.get("agent_index_key", "") or "").strip(),
                    str(record.get("agent_index_id", "") or "").strip(),
                }:
                    return str(foundry_name or "").strip(), dict(record)

        if agent_name:
            for foundry_name, record in record_map.items():
                if not isinstance(record, dict):
                    continue

                names = {
                    str(foundry_name or "").strip().lower(),
                    str(record.get("agent_name", "") or "").strip().lower(),
                    str(record.get("name", "") or "").strip().lower(),
                    str(record.get("requested_agent_name", "") or "").strip().lower(),
                }
                if agent_name.lower() in names:
                    return str(foundry_name or "").strip(), dict(record)

        return "", {}

    def _get_agent_foundry_import_index_patch(
        self,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}

        patch = payload.get("index_patch", {})
        if not isinstance(patch, dict):
            patch = {}

        allowed_direct_fields = {
            "assembly_agent_json_path",
            "assembly_file_mtime",
            "last_imported_from_assembly",
            "last_updated_in_assembly",
            "last_updated_in_foundry",
        }

        result = dict(patch)
        for field_name in allowed_direct_fields:
            value = str(payload.get(field_name, "") or "").strip()
            if value:
                result[field_name] = value

        if bool(payload.get("update_import_timestamp", False)):
            import_timestamp = str(payload.get("import_timestamp", "") or "").strip()
            if import_timestamp:
                result["last_imported_from_assembly"] = import_timestamp

        return result

    def _resolve_current_agent_foundry_blueprint_path(
        self,
        *,
        foundry_name: str,
        record: dict[str, Any],
    ) -> Path:
        current_path = self._coerce_optional_path(
            getattr(self, "agent_foundry_blueprint_path", None)
        )
        if current_path is not None:
            return current_path

        return self._get_blueprint_path_for_foundry(
            foundry_name=foundry_name,
            record=record,
        )

    def _coerce_optional_path(self, value: object) -> Path | None:
        clean_value = str(value or "").strip()
        if not clean_value:
            return None

        return Path(clean_value).expanduser().resolve()

    def _resolve_workspace_dir_from_record(self, record: dict[str, Any]) -> Path | None:
        if not isinstance(record, dict):
            return None

        workspace_dir = self._coerce_optional_path(record.get("workspace_dir"))
        if workspace_dir is not None and workspace_dir.exists() and workspace_dir.is_dir():
            return workspace_dir

        blueprint_path = self._coerce_optional_path(record.get("blueprint_file"))
        if blueprint_path is not None:
            candidate = blueprint_path.parent
            if candidate.exists() and candidate.is_dir():
                return candidate

        metadata_file = self._coerce_optional_path(record.get("metadata_file"))
        if metadata_file is not None:
            candidate = metadata_file.parent
            if candidate.exists() and candidate.is_dir():
                return candidate

        return None

    def _get_blueprint_path_for_foundry(
        self,
        *,
        foundry_name: str,
        record: dict[str, Any],
    ) -> Path:
        workspace_dir = self._get_agent_foundry_workspace_dir_for_save(
            foundry_name=foundry_name,
            record=record,
        )

        if workspace_dir is None:
            raise FileNotFoundError(f"Agent Foundry workspace not found: {foundry_name}")

        blueprint_path = self._blueprint_path_from_workspace_dir(
            workspace_dir=workspace_dir,
        )

        if blueprint_path.exists() and blueprint_path.is_file():
            return blueprint_path

        raise FileNotFoundError(f"Agent Foundry blueprint not found: {blueprint_path}")

    def _get_leftovers_path_for_foundry(
        self,
        *,
        foundry_name: str,
        record: dict[str, Any],
    ) -> Path | None:
        workspace_dir = self._get_agent_foundry_workspace_dir_for_save(
            foundry_name=foundry_name,
            record=record,
        )
        if workspace_dir is None:
            return None

        return self._leftovers_path_from_workspace_dir(workspace_dir=workspace_dir)

    def _load_leftovers_text_for_foundry_record(
        self,
        *,
        foundry_name: str,
        record: dict[str, Any],
    ) -> str:
        leftovers_path = self._get_leftovers_path_for_foundry(
            foundry_name=foundry_name,
            record=record,
        )
        if leftovers_path is None:
            return ""

        if not leftovers_path.exists():
            return ""

        if not leftovers_path.is_file():
            return ""

        try:
            return leftovers_path.read_text(encoding="utf-8")
        except Exception:
            return ""

    def _load_agent_schema_viewer_text_for_foundry(
        self,
        *,
        foundry_name: str,
        record: dict[str, Any],
    ) -> str:
        runtime_path = self._get_runtime_path_for_foundry(
            foundry_name=foundry_name,
            record=record,
        )
        if runtime_path is None:
            return "No runtime.json file is currently selected."

        if not runtime_path.exists():
            return f"runtime.json file does not exist:\n{runtime_path}"

        if not runtime_path.is_file():
            return f"runtime.json path is not a file:\n{runtime_path}"

        raw_text = runtime_path.read_text(encoding="utf-8")
        clean_text = raw_text.strip()

        if not clean_text:
            return f"runtime.json file is empty:\n{runtime_path}"

        try:
            parsed_json = json.loads(clean_text)
        except json.JSONDecodeError:
            return clean_text.rstrip() + "\n"

        return json.dumps(parsed_json, indent=2, ensure_ascii=False).rstrip() + "\n"

    def _get_runtime_path_for_foundry(
        self,
        *,
        foundry_name: str,
        record: dict[str, Any],
    ) -> Path | None:
        if isinstance(record, dict):
            raw_runtime_file = str(record.get("runtime_file", "") or "").strip()
            if raw_runtime_file:
                return Path(raw_runtime_file).expanduser().resolve()

        workspace_dir = self._get_agent_foundry_workspace_dir_for_save(
            foundry_name=foundry_name,
            record=record,
        )
        if workspace_dir is not None:
            return (workspace_dir / "runtime.json").expanduser().resolve()

        return None

    def _strip_agent_foundry_metadata_suffix(self, filename: str) -> str:
        clean_filename = str(filename or "").strip()
        if not clean_filename:
            return ""

        metadata_suffix = METADATA_FILE_SUFFIX
        if clean_filename.endswith(metadata_suffix):
            return clean_filename[: -len(metadata_suffix)].strip()

        path_stem = Path(clean_filename).stem
        if path_stem.endswith(".agent_foundry"):
            return path_stem[: -len(".agent_foundry")].strip()

        return path_stem.strip()

    def _get_agent_foundry_workspace_dir_for_save(
        self,
        *,
        foundry_name: str,
        record: dict[str, Any],
    ) -> Path | None:
        workspace_dir = self._resolve_workspace_dir_from_record(record)
        if workspace_dir is not None:
            return workspace_dir

        workspace_map = getattr(self, "agent_foundry_workspace_map", None)
        if isinstance(workspace_map, dict):
            mapped_dir = workspace_map.get(foundry_name)
            if mapped_dir:
                workspace_dir = _path(mapped_dir)
                if workspace_dir.exists() and workspace_dir.is_dir():
                    return workspace_dir

        try:
            handoff = self._get_agent_foundry_collection_handoff()
            workspaces_dir = _path(handoff.get_agent_foundry_workspaces_directory())

            clean_name = handoff.sanitize_name("agent_foundry_workspace", foundry_name)
            if clean_name:
                workspace_dir = workspaces_dir / clean_name
                if workspace_dir.exists() and workspace_dir.is_dir():
                    return workspace_dir
        except Exception:
            return None

        return None

    def _get_agent_foundry_metadata_file_for_save(
        self,
        *,
        foundry_name: str,
        record: dict[str, Any],
    ) -> Path | None:
        workspace_dir = self._get_agent_foundry_workspace_dir_for_save(
            foundry_name=foundry_name,
            record=record,
        )
        if workspace_dir is None:
            return None

        return self._metadata_path_from_workspace_dir(workspace_dir=workspace_dir)

    def _get_agent_foundry_packages_dir_for_save(
        self,
        *,
        workspace_dir: Path | None,
        record: dict[str, Any],
    ) -> Path | None:
        try:
            handoff = self._get_agent_foundry_collection_handoff()
            return _path(handoff.get_agent_foundry_packages_directory())
        except Exception:
            return None

    def _get_agent_foundry_agent_index_file_for_save(
        self,
        *,
        record: dict[str, Any],
    ) -> Path | None:
        agent_index_file = self._coerce_optional_path(record.get("agent_index_file"))
        if agent_index_file is not None:
            return agent_index_file

        try:
            handoff = self._get_agent_foundry_collection_handoff()
            agent_index_dir = _path(handoff.get_agent_foundry_agent_index_directory())
            return agent_index_dir / AGENT_INDEX_FILE_NAME
        except Exception:
            return None

    def _get_agent_foundry_agent_id_for_save(
        self,
        *,
        foundry_name: str,
        record: dict[str, Any],
        workspace_dir: Path | None,
    ) -> int:
        raw_agent_id = record.get("agent_id", "")

        try:
            return max(0, int(raw_agent_id))
        except (TypeError, ValueError):
            pass

        raw_agent_key = str(record.get("agent_key", "") or "").strip()
        if raw_agent_key:
            match = re.search(r"agent_(\d+)", raw_agent_key)
            if match:
                return max(0, int(match.group(1)))

        for value in (
            foundry_name,
            workspace_dir.name if workspace_dir is not None else "",
        ):
            match = re.search(r"agent_(\d+)", str(value or ""))
            if match:
                return max(0, int(match.group(1)))

        return 0

    def _blueprint_path_from_workspace_dir(
        self,
        *,
        workspace_dir: Path,
    ) -> Path:
        workspace_dir = Path(workspace_dir).expanduser().resolve()
        return workspace_dir / f"{workspace_dir.name}{BLUEPRINT_FILE_SUFFIX}"

    def _leftovers_path_from_workspace_dir(
        self,
        *,
        workspace_dir: Path,
    ) -> Path:
        workspace_dir = Path(workspace_dir).expanduser().resolve()
        return workspace_dir / f"{workspace_dir.name}{LEFTOVERS_FILE_SUFFIX}"

    def _metadata_path_from_workspace_dir(
        self,
        *,
        workspace_dir: Path,
    ) -> Path:
        workspace_dir = Path(workspace_dir).expanduser().resolve()
        return workspace_dir / f"{workspace_dir.name}{METADATA_FILE_SUFFIX}"

    def _combine_blueprint_and_leftovers_for_load(
        self,
        *,
        blueprint_text: str,
        leftovers_text: str,
    ) -> str:
        clean_blueprint_text = str(blueprint_text or "").rstrip()
        clean_leftovers_text = str(leftovers_text or "").strip()

        if not clean_blueprint_text:
            return clean_leftovers_text + ("\n" if clean_leftovers_text else "")

        if not clean_leftovers_text:
            return clean_blueprint_text + "\n"

        return clean_blueprint_text + "\n\n" + clean_leftovers_text + "\n"

    def _get_agent_foundry_agent_name_from_frontend_object(
        self,
        *,
        frontend_object: dict[str, Any],
    ) -> str:
        if not isinstance(frontend_object, dict):
            return ""

        agent_names = self._extract_agent_names_from_frontend_object(frontend_object)
        if agent_names:
            return agent_names[0]

        return ""

    def _extract_agent_names_from_frontend_object(
        self,
        frontend_object: dict[str, Any],
    ) -> list[str]:
        if not isinstance(frontend_object, dict):
            return []

        names = self._extract_agent_names_from_agent_id_list(frontend_object)
        if names:
            return self._unique_text_values(names)

        names = self._extract_agent_names_from_agent_nodes(frontend_object)
        return self._unique_text_values(names)

    def _extract_agent_names_from_agent_id_list(
        self,
        frontend_object: dict[str, Any],
    ) -> list[str]:
        list_heading = f"{ROOT_AGENT_NAME} {GRAMMAR_SUFFIX_ID}"

        for node in self._iter_frontend_text_nodes_for_name_extraction(frontend_object):
            source_text = str(node.get("content", "") or "")
            names = self._extract_fenced_list_items_from_text(
                source_text=source_text,
                list_heading=list_heading,
            )
            if names:
                return names

        return []

    def _extract_agent_names_from_agent_nodes(
        self,
        frontend_object: dict[str, Any],
    ) -> list[str]:
        nodes = frontend_object.get("nodes", {})
        if not isinstance(nodes, dict):
            return []

        names: list[str] = []

        for node in nodes.values():
            if not isinstance(node, dict):
                continue

            if str(node.get("kind", "") or "").strip() != "agent":
                continue

            name = str(node.get("name", "") or "").strip()
            if name:
                names.append(name)

        return names

    def _iter_frontend_text_nodes_for_name_extraction(
        self,
        frontend_object: dict[str, Any],
    ) -> list[dict[str, Any]]:
        nodes = frontend_object.get("nodes", {})
        if not isinstance(nodes, dict):
            return []

        results: list[dict[str, Any]] = []

        for node in nodes.values():
            if not isinstance(node, dict):
                continue

            area = str(node.get("area", "") or "").strip().lower()
            if area not in {"content", "fused"}:
                continue

            if "content" not in node:
                continue

            data = node.get("data", {})
            if isinstance(data, dict) and bool(data.get("parser_search_exclude", False)):
                continue

            results.append(node)

        return results

    def _extract_fenced_list_items_from_text(
        self,
        *,
        source_text: str,
        list_heading: str,
    ) -> list[str]:
        source = str(source_text or "")
        clean_heading = str(list_heading or "").strip()
        if not source.strip() or not clean_heading:
            return []

        start_pattern = rf"(?im)^\s*{re.escape(clean_heading)}\s*:\s*$"
        start_match = re.search(start_pattern, source)
        if start_match is None:
            return []

        end_heading = f"End {clean_heading}"
        end_pattern = rf"(?im)^\s*{re.escape(end_heading)}\s*$"
        end_match = re.search(end_pattern, source[start_match.end():])
        if end_match is None:
            return []

        inner_text = source[start_match.end(): start_match.end() + end_match.start()]
        results: list[str] = []

        for raw_line in inner_text.splitlines():
            line = str(raw_line or "").strip()
            if not line:
                continue

            bullet_match = re.match(r"^[-*]\s+(?P<value>.*)$", line)
            if bullet_match is None:
                continue

            value = str(bullet_match.group("value") or "").strip()
            if value:
                results.append(value)

        return results

    def _unique_text_values(self, values: list[str] | tuple[str, ...] | set[str]) -> list[str]:
        results: list[str] = []
        seen: set[str] = set()

        for value in list(values or []):
            clean_value = str(value or "").strip()
            if not clean_value:
                continue

            key = clean_value.lower()
            if key in seen:
                continue

            seen.add(key)
            results.append(clean_value)

        return results

    def _verify_agent_foundry_parser_source_conservation_or_fail_load(
        self,
        *,
        foundry_name: str,
        record: dict[str, Any],
        original_blueprint_text: str,
        original_leftovers_text: str,
        parser_blueprint_text: str,
        parser_leftovers_text: str,
    ) -> None:
        original_combined = self._normalize_agent_foundry_verification_text(
            self._combine_blueprint_and_leftovers_for_load(
                blueprint_text=original_blueprint_text,
                leftovers_text=original_leftovers_text,
            )
        )

        parser_combined = self._normalize_agent_foundry_verification_text(
            self._combine_blueprint_and_leftovers_for_load(
                blueprint_text=parser_blueprint_text,
                leftovers_text=parser_leftovers_text,
            )
        )

        original_units = self._extract_agent_foundry_source_units_for_verification(
            original_combined
        )
        parser_units = self._extract_agent_foundry_source_units_for_verification(
            parser_combined
        )

        original_counter = Counter(original_units)
        parser_counter = Counter(parser_units)

        passed = original_counter == parser_counter
        self.agent_foundry_source_verification_passed = passed

        if passed:
            self.agent_foundry_source_verification_report = {}
            return

        report = self._build_agent_foundry_source_verification_report(
            foundry_name=foundry_name,
            record=record,
            original_blueprint_text=original_blueprint_text,
            original_leftovers_text=original_leftovers_text,
            parser_blueprint_text=parser_blueprint_text,
            parser_leftovers_text=parser_leftovers_text,
            original_combined_text=original_combined,
            parser_combined_text=parser_combined,
            original_units=original_units,
            parser_units=parser_units,
            original_counter=original_counter,
            parser_counter=parser_counter,
        )

        self.agent_foundry_source_verification_report = report
        self._write_agent_foundry_source_verification_report_to_metadata(
            foundry_name=foundry_name,
            record=record,
            report=report,
        )

        self._safe_show_agent_foundry_entry_screen()

        raise RuntimeError(
            "Agent Foundry source verification failed. "
            "Load was cancelled and no save was performed. "
            "A failure report was written into the draft metadata record."
        )

    def _normalize_agent_foundry_verification_text(self, value: str) -> str:
        return str(value or "").replace("\r\n", "\n").replace("\r", "\n").rstrip()

    def _extract_agent_foundry_source_units_for_verification(
        self,
        source_text: str,
    ) -> list[str]:
        normalized_source = self._normalize_agent_foundry_verification_text(source_text)
        if not normalized_source.strip():
            return []

        lines = normalized_source.split("\n")
        units: list[str] = []
        pending_free_lines: list[str] = []
        index = 0

        while index < len(lines):
            line = str(lines[index] or "")
            clean_line = line.strip()

            if not clean_line:
                self._flush_agent_foundry_verification_free_lines(
                    pending_free_lines=pending_free_lines,
                    units=units,
                )
                index += 1
                continue

            start_heading = self._extract_agent_foundry_verification_fence_start_heading(
                clean_line
            )
            if start_heading:
                end_index = self._find_agent_foundry_verification_fence_end_index(
                    lines=lines,
                    start_index=index + 1,
                    end_heading=f"End {start_heading}",
                )

                if end_index is not None:
                    self._flush_agent_foundry_verification_free_lines(
                        pending_free_lines=pending_free_lines,
                        units=units,
                    )
                    block_text = "\n".join(lines[index:end_index + 1]).strip()
                    if block_text:
                        units.append(block_text)
                    index = end_index + 1
                    continue

            pending_free_lines.append(line.rstrip())
            index += 1

        self._flush_agent_foundry_verification_free_lines(
            pending_free_lines=pending_free_lines,
            units=units,
        )

        return units

    def _extract_agent_foundry_verification_fence_start_heading(
        self,
        line: str,
    ) -> str:
        clean_line = str(line or "").strip()
        if not clean_line:
            return ""

        if not clean_line.endswith(":"):
            return ""

        if re.match(r"(?i)^End\s+", clean_line):
            return ""

        return clean_line[:-1].strip()

    def _find_agent_foundry_verification_fence_end_index(
        self,
        *,
        lines: list[str],
        start_index: int,
        end_heading: str,
    ) -> int | None:
        clean_end_heading = str(end_heading or "").strip()
        if not clean_end_heading:
            return None

        end_pattern = re.compile(
            rf"^\s*{re.escape(clean_end_heading)}\s*$",
            re.IGNORECASE,
        )

        for index in range(max(0, int(start_index)), len(lines)):
            if end_pattern.match(str(lines[index] or "")):
                return index

        return None

    def _flush_agent_foundry_verification_free_lines(
        self,
        *,
        pending_free_lines: list[str],
        units: list[str],
    ) -> None:
        if not pending_free_lines:
            return

        text = "\n".join(
            str(line or "").rstrip()
            for line in pending_free_lines
            if str(line or "").strip()
        ).strip()

        pending_free_lines.clear()

        if text:
            units.append(text)

    def _build_agent_foundry_source_verification_report(
        self,
        *,
        foundry_name: str,
        record: dict[str, Any],
        original_blueprint_text: str,
        original_leftovers_text: str,
        parser_blueprint_text: str,
        parser_leftovers_text: str,
        original_combined_text: str,
        parser_combined_text: str,
        original_units: list[str],
        parser_units: list[str],
        original_counter: Counter[str],
        parser_counter: Counter[str],
    ) -> dict[str, Any]:
        original_blueprint = str(original_blueprint_text or "").rstrip()
        original_leftovers = str(original_leftovers_text or "").rstrip()
        parser_blueprint = str(parser_blueprint_text or "").rstrip()
        parser_leftovers = str(parser_leftovers_text or "").rstrip()
        original_combined = str(original_combined_text or "").rstrip()
        parser_combined = str(parser_combined_text or "").rstrip()

        missing_units = list((original_counter - parser_counter).elements())
        added_units = list((parser_counter - original_counter).elements())

        return {
            "status": "failed",
            "failed_at": self._now_agent_foundry_text(),
            "foundry_name": str(foundry_name or "").strip(),
            "agent_id": record.get("agent_id", record.get("id", ""))
            if isinstance(record, dict)
            else "",
            "message": (
                "The original source-unit inventory and Parser-composed source-unit inventory "
                "did not match. Verification compares Blueprint + Leftovers as one conserved "
                "source stream and ignores parser reordering, but it still fails if any fenced "
                "or unfenced source unit is missing, duplicated, or newly invented."
            ),
            "original_combined_length": len(original_combined),
            "parser_combined_length": len(parser_combined),
            "original_blueprint_length": len(original_blueprint),
            "original_leftovers_length": len(original_leftovers),
            "parser_blueprint_length": len(parser_blueprint),
            "parser_leftovers_length": len(parser_leftovers),
            "original_unit_count": len(original_units),
            "parser_unit_count": len(parser_units),
            "missing_unit_count": len(missing_units),
            "added_unit_count": len(added_units),
            "missing_units": missing_units,
            "added_units": added_units,
            "original_blueprint_text": original_blueprint,
            "original_leftovers_text": original_leftovers,
            "parser_blueprint_text": parser_blueprint,
            "parser_leftovers_text": parser_leftovers,
            "original_combined_text": original_combined,
            "parser_combined_text": parser_combined,
            "original_units": original_units,
            "parser_units": parser_units,
        }

    def _write_agent_foundry_source_verification_report_to_metadata(
        self,
        *,
        foundry_name: str,
        record: dict[str, Any],
        report: dict[str, Any],
    ) -> None:
        clean_foundry_name = str(foundry_name or "").strip()
        if not clean_foundry_name:
            return

        updated_record = dict(record or {})
        updated_record["source_verification"] = dict(report or {})
        updated_record["source_verification_status"] = "failed"
        updated_record["source_verification_failed_at"] = str(
            dict(report or {}).get("failed_at", "") or self._now_agent_foundry_text()
        )

        workspace_dir = self._get_agent_foundry_workspace_dir_for_save(
            foundry_name=clean_foundry_name,
            record=updated_record,
        )
        if workspace_dir is None:
            return

        metadata_file = self._metadata_path_from_workspace_dir(workspace_dir=workspace_dir)

        updated_record["foundry_name"] = clean_foundry_name
        updated_record["name"] = clean_foundry_name
        updated_record["workspace_dir"] = str(workspace_dir.resolve())
        updated_record["agent_dir"] = str(workspace_dir.resolve())
        updated_record["metadata_file"] = str(metadata_file.resolve())

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
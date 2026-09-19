import fnmatch
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from Storage.file_collection_manager import FileCollectionManager


class CollectionHandoff:
    def __init__(self, base_dir: Optional[str] = None) -> None:
        if base_dir is None:
            base_dir = str(Path(__file__).resolve().parent)

        self.base_dir = str(Path(base_dir).resolve())
        self._collection_config: Dict[str, Dict[str, object]] = {
            "package_record": {
                "registry_key": "package_root",
                "folder_name": "packages",
                "file_extension": ".package.json",
                "use_item_subfolder": False,
            },
            "assembly": {
                "registry_key": "assembly_root",
                "folder_name": "assemblies",
                "file_extension": ".json",
                "use_item_subfolder": True,
            },
            "agent_foundry_workspace": {
                "registry_key": "agent_foundry_agents_root",
                "folder_name": "Agents",
                "file_extension": ".json",
                "use_item_subfolder": True,
            },
            "agent_foundry_blueprint": {
                "registry_key": "agent_foundry_agents_root",
                "folder_name": "Agents",
                "file_extension": ".blueprint.txt",
                "use_item_subfolder": True,
            },
            "agent_foundry_metadata": {
                "registry_key": "agent_foundry_agents_root",
                "folder_name": "Agents",
                "file_extension": ".agent_foundry.json",
                "use_item_subfolder": True,
            },
            "agent_foundry_agent_index": {
                "registry_key": "agent_foundry_indexes_root",
                "folder_name": "AgentFoundry",
                "file_extension": ".json",
                "use_item_subfolder": False,
            },
        }
        self._managers: Dict[str, FileCollectionManager] = {}

        self._system_dir = (
            Path(self.base_dir)
            / "Storage"
            / "Generated Artifacts"
            / "System"
        )
        self._system_dir.mkdir(parents=True, exist_ok=True)
        self._storage_registry_path = self._system_dir / "storage_registry.json"

        # The optional follow-up agent is not bundled. Enable it explicitly only
        # after configuring a local review workflow.
        self.package_post_save_review_enabled = False
        self.package_post_save_review_agent_name = "Blacksmith"
        self.package_post_save_review_task_name = "Package Update and Verification Preparation"

    def sanitize_name(self, item_type: str, raw_name: str) -> str:
        manager = self._get_manager(item_type)
        return manager.sanitize_name(raw_name)

    def save_item(self, item_type: str, item_name: str, content: str) -> str:
        manager = self._get_manager(item_type)
        return manager.save_item(item_name, content)

    def load_item(self, item_type: str, item_name: str) -> str:
        manager = self._get_manager(item_type)
        return manager.load_item(item_name)

    def list_items(self, item_type: str) -> list[str]:
        manager = self._get_manager(item_type)
        return manager.list_items()

    def item_exists(self, item_type: str, item_name: str) -> bool:
        manager = self._get_manager(item_type)
        return manager.item_exists(item_name)

    def delete_item(self, item_type: str, item_name: str) -> str:
        manager = self._get_manager(item_type)
        return manager.delete_item(item_name)

    def get_storage_dir(self, item_type: str) -> str:
        manager = self._get_manager(item_type)
        return str(manager.storage_dir)

    def get_base_dir(self) -> str:
        return self.base_dir

    def get_storage_root(self) -> str:
        manager = self._get_manager("assembly")
        return str(manager.storage_root)

    def get_storage_registry_path(self) -> str:
        return str(self._storage_registry_path)

    def initialize_storage_registry(self) -> dict[str, Any]:
        """Create local defaults for a fresh workspace without replacing a registry."""
        if not self._storage_registry_path.exists():
            entries = [{
                "key": "repo_root", "label": "Workspace", "path": self.base_dir,
                "uses_repo_root": False, "supports_migration": False, "read_only": True,
            }]
            for key, label, folder in [
                ("package_root", "Packages", "Packages"),
                ("assembly_root", "Agents", "Assemblies"),
                ("user_approval_root", "User Control", "UserControl"),
            ]:
                entries.append({
                    "key": key, "label": label,
                    "path": f"Storage/Generated Artifacts/{folder}",
                    "uses_repo_root": True, "supports_migration": True,
                    "read_only": False, "migration_mode": "children",
                    "migration_patterns": ["*"],
                })
            try:
                with self._storage_registry_path.open("x", encoding="utf-8") as stream:
                    json.dump({"entries": entries}, stream, indent=2)
                    stream.write("\n")
            except FileExistsError:
                pass
        return self.get_storage_registry()

    def get_storage_registry(self) -> dict[str, Any]:
        if not self._storage_registry_path.exists():
            raise FileNotFoundError(
                f"Storage registry not found: {self._storage_registry_path}"
            )

        try:
            raw_text = self._storage_registry_path.read_text(encoding="utf-8")
            parsed = json.loads(raw_text)
        except Exception as exc:
            raise ValueError(
                f"Could not read storage registry: {self._storage_registry_path}\n{exc}"
            ) from exc

        if not isinstance(parsed, dict):
            raise ValueError("Storage registry root must be a JSON object.")

        entries = parsed.get("entries")
        if not isinstance(entries, list):
            raise ValueError("Storage registry must contain an 'entries' list.")

        parsed = self._ensure_agent_foundry_registry_entries(parsed)

        return parsed

    def save_storage_registry(self, registry_data: dict[str, Any]) -> str:
        if not isinstance(registry_data, dict):
            raise ValueError("Storage registry must be a dict.")

        entries = registry_data.get("entries")
        if not isinstance(entries, list):
            raise ValueError("Storage registry must contain an 'entries' list.")

        self._storage_registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._storage_registry_path.write_text(
            json.dumps(registry_data, indent=2) + "\n",
            encoding="utf-8",
        )
        return str(self._storage_registry_path)

    def get_storage_registry_entry(self, key: str) -> dict[str, Any]:
        clean_key = str(key).strip()
        if not clean_key:
            raise ValueError("Registry entry key cannot be blank.")

        registry_data = self.get_storage_registry()
        for entry in registry_data["entries"]:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("key", "")).strip() == clean_key:
                return dict(entry)

        raise KeyError(f"Storage registry entry not found: {clean_key}")

    def list_storage_registry_entries(self) -> list[dict[str, Any]]:
        registry_data = self.get_storage_registry()
        results: list[dict[str, Any]] = []

        for raw_entry in registry_data["entries"]:
            if not isinstance(raw_entry, dict):
                continue

            entry = dict(raw_entry)
            key = str(entry.get("key", "")).strip()
            if not key:
                continue

            resolved_path = self._resolve_registry_entry_path(entry)
            linked_item_type = self._get_item_type_for_registry_key(key)

            entry["resolved_path"] = str(resolved_path)
            entry["linked_item_type"] = linked_item_type
            entry["can_migrate"] = bool(entry.get("supports_migration", False)) and not bool(
                entry.get("read_only", False)
            )
            entry["migration_mode"] = self._get_registry_migration_mode(entry)
            entry["migration_patterns"] = self._get_registry_migration_patterns(entry)

            results.append(entry)

        return results

    def update_storage_registry_entry(self, key: str, new_entry: dict[str, Any]) -> str:
        clean_key = str(key).strip()
        if not clean_key:
            raise ValueError("Registry entry key cannot be blank.")
        if not isinstance(new_entry, dict):
            raise ValueError("Replacement registry entry must be a dict.")

        registry_data = self.get_storage_registry()
        updated = False

        for index, entry in enumerate(registry_data["entries"]):
            if not isinstance(entry, dict):
                continue
            if str(entry.get("key", "")).strip() == clean_key:
                registry_data["entries"][index] = dict(new_entry)
                updated = True
                break

        if not updated:
            raise KeyError(f"Storage registry entry not found: {clean_key}")

        return self.save_storage_registry(registry_data)

    def _ensure_agent_foundry_registry_entries(
        self,
        registry_data: dict[str, Any],
    ) -> dict[str, Any]:
        entries = registry_data.get("entries")
        if not isinstance(entries, list):
            raise ValueError("Storage registry must contain an 'entries' list.")

        existing_keys = {
            str(entry.get("key", "")).strip()
            for entry in entries
            if isinstance(entry, dict)
        }

        default_entries = [
            {
                "key": "agent_foundry_root",
                "label": "Agent Foundry Root",
                "description": "Unified root folder for Agent Foundry indexes and indexed object folders.",
                "path": r"Storage\Generated Artifacts\AgentFoundry",
                "uses_repo_root": True,
                "supports_migration": False,
                "read_only": False,
                "migration_mode": "children",
                "migration_patterns": ["*"],
            },
            {
                "key": "agent_foundry_agents_root",
                "label": "Agent Foundry Agents",
                "description": "Agent Foundry agent folders. Each agent folder stores its agent schema, blueprint, metadata, and leftovers files.",
                "path": r"Storage\Generated Artifacts\AgentFoundry\Agents",
                "uses_repo_root": True,
                "supports_migration": True,
                "read_only": False,
                "migration_mode": "children",
                "migration_patterns": ["*"],
            },
            {
                "key": "agent_foundry_packages_root",
                "label": "Agent Foundry Packages",
                "description": "Agent Foundry indexed package item files.",
                "path": r"Storage\Generated Artifacts\AgentFoundry\Packages",
                "uses_repo_root": True,
                "supports_migration": True,
                "read_only": False,
                "migration_mode": "children",
                "migration_patterns": ["*"],
            },
            {
                "key": "agent_foundry_tasks_root",
                "label": "Agent Foundry Tasks",
                "description": "Agent Foundry indexed task item files.",
                "path": r"Storage\Generated Artifacts\AgentFoundry\Tasks",
                "uses_repo_root": True,
                "supports_migration": True,
                "read_only": False,
                "migration_mode": "children",
                "migration_patterns": ["*"],
            },
            {
                "key": "agent_foundry_groups_root",
                "label": "Agent Foundry Groups",
                "description": "Agent Foundry indexed group item files.",
                "path": r"Storage\Generated Artifacts\AgentFoundry\Groups",
                "uses_repo_root": True,
                "supports_migration": True,
                "read_only": False,
                "migration_mode": "children",
                "migration_patterns": ["*"],
            },
            {
                "key": "agent_foundry_indexes_root",
                "label": "Agent Foundry Indexes",
                "description": "Canonical Agent Foundry index files.",
                "path": r"Storage\Generated Artifacts\AgentFoundry",
                "uses_repo_root": True,
                "supports_migration": True,
                "read_only": False,
                "migration_mode": "files",
                "migration_patterns": [
                    "agent_index.json",
                    "package_index.json",
                    "task_index.json",
                    "group_index.json",
                ],
            },
            {
                "key": "chat_root",
                "label": "Chats",
                "description": "Chatroom JSON storage root. Stores Active and Archived chat conversation files.",
                "path": r"Storage\Generated Artifacts\Chats",
                "uses_repo_root": True,
                "supports_migration": True,
                "read_only": False,
                "migration_mode": "children",
                "migration_patterns": ["*"],
            },
        ]

        changed = False

        for default_entry in default_entries:
            key = str(default_entry["key"]).strip()
            if key in existing_keys:
                continue

            entries.append(default_entry)
            existing_keys.add(key)
            changed = True

        if changed:
            self._storage_registry_path.parent.mkdir(parents=True, exist_ok=True)
            self._storage_registry_path.write_text(
                json.dumps(registry_data, indent=2) + "\n",
                encoding="utf-8",
            )

        return registry_data

    def _resolve_registry_entry_path(self, entry: dict[str, Any]) -> Path:
        if not isinstance(entry, dict):
            raise ValueError("Registry entry must be a dict.")

        raw_path = str(entry.get("path", "")).strip()
        if not raw_path:
            raise ValueError(
                f"Registry entry '{entry.get('key', '<unknown>')}' has a blank path."
            )

        uses_repo_root = bool(entry.get("uses_repo_root", False))

        if uses_repo_root:
            repo_root_entry = self.get_storage_registry_entry("repo_root")
            repo_root_raw = str(repo_root_entry.get("path", "")).strip()
            if not repo_root_raw:
                raise ValueError("Registry entry 'repo_root' has a blank path.")
            repo_root_path = Path(repo_root_raw).expanduser().resolve()
            return (repo_root_path / Path(raw_path.replace("\\", "/"))).resolve()

        return Path(raw_path).expanduser().resolve()

    def _convert_path_for_registry_storage(self, absolute_path: Path) -> tuple[str, bool]:
        resolved_directory = Path(absolute_path).expanduser().resolve()

        repo_root_entry = self.get_storage_registry_entry("repo_root")
        repo_root_path = self._resolve_registry_entry_path(repo_root_entry)

        try:
            relative_path = resolved_directory.relative_to(repo_root_path)
            return str(relative_path).replace("/", "\\"), True
        except ValueError:
            return str(resolved_directory), False

    def get_repo_root(self) -> str:
        repo_root_entry = self.get_storage_registry_entry("repo_root")
        return str(self._resolve_registry_entry_path(repo_root_entry))

    def get_storage_entry_directory(self, key: str) -> str:
        entry = self.get_storage_registry_entry(key)
        return str(self._resolve_registry_entry_path(entry))

    def get_agent_foundry_root_directory(self) -> str:
        return self.get_storage_entry_directory("agent_foundry_root")

    def get_agent_foundry_agents_directory(self) -> str:
        return self.get_storage_entry_directory("agent_foundry_agents_root")

    def get_agent_foundry_packages_directory(self) -> str:
        return self.get_storage_entry_directory("agent_foundry_packages_root")

    def get_agent_foundry_tasks_directory(self) -> str:
        return self.get_storage_entry_directory("agent_foundry_tasks_root")

    def get_agent_foundry_groups_directory(self) -> str:
        return self.get_storage_entry_directory("agent_foundry_groups_root")

    def get_agent_foundry_indexes_directory(self) -> str:
        return self.get_storage_entry_directory("agent_foundry_indexes_root")

    def get_agent_foundry_agent_index_file(self) -> str:
        return str(Path(self.get_agent_foundry_indexes_directory()) / "agent_index.json")

    def get_agent_foundry_package_index_file(self) -> str:
        return str(Path(self.get_agent_foundry_indexes_directory()) / "package_index.json")

    def get_agent_foundry_task_index_file(self) -> str:
        return str(Path(self.get_agent_foundry_indexes_directory()) / "task_index.json")

    def get_agent_foundry_group_index_file(self) -> str:
        return str(Path(self.get_agent_foundry_indexes_directory()) / "group_index.json")

    def get_agent_foundry_workspaces_directory(self) -> str:
        return self.get_agent_foundry_agents_directory()

    def get_agent_foundry_blueprints_directory(self) -> str:
        return self.get_agent_foundry_agents_directory()

    def get_agent_foundry_metadata_directory(self) -> str:
        return self.get_agent_foundry_agents_directory()

    def get_agent_foundry_agent_index_directory(self) -> str:
        return self.get_agent_foundry_indexes_directory()

    def get_agent_foundry_agent_directory(self, foundry_name: str) -> str:
        clean_name = self.sanitize_name("agent_foundry_workspace", foundry_name)
        if not clean_name:
            raise ValueError("Invalid Agent Foundry agent name.")

        return str(Path(self.get_agent_foundry_agents_directory()) / clean_name)

    def get_agent_foundry_agent_schema_file(self, foundry_name: str) -> str:
        clean_name = self.sanitize_name("agent_foundry_workspace", foundry_name)
        if not clean_name:
            raise ValueError("Invalid Agent Foundry agent name.")

        return str(Path(self.get_agent_foundry_agent_directory(clean_name)) / f"{clean_name}.json")

    def get_agent_foundry_blueprint_file(self, foundry_name: str) -> str:
        clean_name = self.sanitize_name("agent_foundry_blueprint", foundry_name)
        if not clean_name:
            raise ValueError("Invalid Agent Foundry blueprint name.")

        return str(Path(self.get_agent_foundry_agent_directory(clean_name)) / f"{clean_name}.blueprint.txt")

    def get_agent_foundry_metadata_file(self, foundry_name: str) -> str:
        clean_name = self.sanitize_name("agent_foundry_metadata", foundry_name)
        if not clean_name:
            raise ValueError("Invalid Agent Foundry metadata name.")

        return str(Path(self.get_agent_foundry_agent_directory(clean_name)) / f"{clean_name}.agent_foundry.json")

    def get_agent_foundry_leftovers_file(self, foundry_name: str) -> str:
        clean_name = self.sanitize_name("agent_foundry_metadata", foundry_name)
        if not clean_name:
            raise ValueError("Invalid Agent Foundry metadata name.")

        return str(Path(self.get_agent_foundry_agent_directory(clean_name)) / f"{clean_name}.leftovers.agent_foundry.txt")

    def set_storage_entry_directory(self, key: str, directory: str | Path) -> str:
        clean_key = str(key).strip()
        if not clean_key:
            raise ValueError("Registry entry key cannot be blank.")

        resolved_directory = Path(directory).expanduser().resolve()
        resolved_directory.mkdir(parents=True, exist_ok=True)

        entry = self.get_storage_registry_entry(clean_key)

        if bool(entry.get("read_only", False)):
            raise ValueError(f"Registry entry '{clean_key}' is read-only and cannot be updated.")

        updated_entry = dict(entry)
        stored_path, uses_repo_root = self._convert_path_for_registry_storage(resolved_directory)
        updated_entry["path"] = stored_path
        updated_entry["uses_repo_root"] = uses_repo_root

        self.update_storage_registry_entry(clean_key, updated_entry)
        self._invalidate_manager_for_registry_key(clean_key)

        return str(resolved_directory)

    def migrate_storage_entry(self, key: str, directory: str | Path) -> dict[str, Any]:
        clean_key = str(key).strip()
        if not clean_key:
            raise ValueError("Registry entry key cannot be blank.")

        entry = self.get_storage_registry_entry(clean_key)

        if bool(entry.get("read_only", False)):
            raise ValueError(f"Registry entry '{clean_key}' is read-only and cannot be migrated.")

        if not bool(entry.get("supports_migration", False)):
            raise ValueError(f"Registry entry '{clean_key}' does not support migration.")

        target_directory = Path(directory).expanduser().resolve()
        target_directory.mkdir(parents=True, exist_ok=True)

        source_directory = Path(self.get_storage_entry_directory(clean_key)).resolve()

        if target_directory == source_directory:
            raise ValueError(
                f"Target directory matches the current directory for registry entry '{clean_key}'."
            )

        migration_mode = self._get_registry_migration_mode(entry)
        migration_patterns = self._get_registry_migration_patterns(entry)

        moved_count = self._migrate_registry_entry_directory(
            source_directory=source_directory,
            target_directory=target_directory,
            migration_mode=migration_mode,
            migration_patterns=migration_patterns,
        )

        self.set_storage_entry_directory(clean_key, target_directory)

        item_type = self._get_item_type_for_registry_key(clean_key)

        return {
            "registry_entry_key": clean_key,
            "item_type": item_type or "",
            "migration_kind": "registry_patterns",
            "migration_mode": migration_mode,
            "migration_patterns": migration_patterns,
            "source_directory": str(source_directory),
            "target_directory": str(target_directory),
            "moved_count": moved_count,
        }

    def _get_registry_migration_mode(self, entry: dict[str, Any]) -> str:
        raw_mode = str(entry.get("migration_mode", "") or "").strip().lower()
        if not raw_mode:
            return "all"

        if raw_mode not in {"files", "children", "all"}:
            raise ValueError(
                "Invalid registry migration_mode.\n\n"
                f"Entry: {entry.get('key', '<unknown>')}\n"
                f"migration_mode: {raw_mode}\n\n"
                "Allowed values: files, children, all"
            )

        return raw_mode

    def _get_registry_migration_patterns(self, entry: dict[str, Any]) -> list[str]:
        raw_patterns = entry.get("migration_patterns", None)

        if raw_patterns in (None, ""):
            return ["*"]

        if not isinstance(raw_patterns, list):
            raise ValueError(
                "Registry migration_patterns must be a list.\n\n"
                f"Entry: {entry.get('key', '<unknown>')}"
            )

        patterns: list[str] = []
        for raw_pattern in raw_patterns:
            clean_pattern = str(raw_pattern or "").strip()
            if clean_pattern:
                patterns.append(clean_pattern)

        if not patterns:
            return ["*"]

        return patterns

    def _migrate_registry_entry_directory(
        self,
        *,
        source_directory: Path,
        target_directory: Path,
        migration_mode: str,
        migration_patterns: list[str],
    ) -> int:
        source_directory = Path(source_directory).expanduser().resolve()
        target_directory = Path(target_directory).expanduser().resolve()
        target_directory.mkdir(parents=True, exist_ok=True)

        if not source_directory.exists():
            return 0

        if not source_directory.is_dir():
            raise ValueError(f"Source path is not a directory: {source_directory}")

        moved_count = 0

        for child in source_directory.iterdir():
            if not self._registry_migration_child_matches(
                child=child,
                migration_mode=migration_mode,
                migration_patterns=migration_patterns,
            ):
                continue

            destination = target_directory / child.name
            if destination.exists():
                raise FileExistsError(
                    f"Migration aborted because target path already exists: {destination}"
                )

            shutil.move(str(child), str(destination))
            moved_count += 1

        return moved_count

    def _registry_migration_child_matches(
        self,
        *,
        child: Path,
        migration_mode: str,
        migration_patterns: list[str],
    ) -> bool:
        if migration_mode == "files" and not child.is_file():
            return False

        if migration_mode == "children" and not (child.is_file() or child.is_dir()):
            return False

        if migration_mode == "all" and not (child.is_file() or child.is_dir()):
            return False

        child_name = child.name
        return any(fnmatch.fnmatchcase(child_name, pattern) for pattern in migration_patterns)

    def _migrate_general_directory(
        self,
        source_directory: Path,
        target_directory: Path,
    ) -> int:
        source_directory = Path(source_directory).expanduser().resolve()
        target_directory = Path(target_directory).expanduser().resolve()
        target_directory.mkdir(parents=True, exist_ok=True)

        if not source_directory.exists():
            return 0

        if not source_directory.is_dir():
            raise ValueError(f"Source path is not a directory: {source_directory}")

        moved_count = 0

        for child in source_directory.iterdir():
            destination = target_directory / child.name
            if destination.exists():
                raise FileExistsError(
                    f"Migration aborted because target path already exists: {destination}"
                )

            shutil.move(str(child), str(destination))
            moved_count += 1

        return moved_count

    def _migrate_collection_directory(
        self,
        item_type: str,
        source_directory: Path,
        target_directory: Path,
    ) -> int:
        normalized_type = str(item_type).strip().lower()
        if normalized_type not in self._collection_config:
            raise ValueError(f"Unknown collection type: {item_type}")

        source_directory = Path(source_directory).expanduser().resolve()
        target_directory = Path(target_directory).expanduser().resolve()
        target_directory.mkdir(parents=True, exist_ok=True)

        config = self._collection_config[normalized_type]
        file_extension = str(config["file_extension"])
        use_item_subfolder = bool(config.get("use_item_subfolder", False))

        if not source_directory.exists():
            return 0

        moved_count = 0

        if use_item_subfolder:
            for child in source_directory.iterdir():
                if not child.is_dir():
                    continue

                expected_file = child / f"{child.name}{file_extension}"
                if not expected_file.exists():
                    continue

                destination = target_directory / child.name
                if destination.exists():
                    raise FileExistsError(
                        f"Migration aborted because target directory already exists: {destination}"
                    )

                shutil.move(str(child), str(destination))
                moved_count += 1

            return moved_count

        for child in source_directory.iterdir():
            if not child.is_file():
                continue
            if not child.name.endswith(file_extension):
                continue

            destination = target_directory / child.name
            if destination.exists():
                raise FileExistsError(
                    f"Migration aborted because target file already exists: {destination}"
                )

            shutil.move(str(child), str(destination))
            moved_count += 1

        return moved_count

    def _get_item_type_for_registry_key(self, registry_key: str) -> Optional[str]:
        clean_key = str(registry_key).strip()
        if not clean_key:
            return None

        for item_type, config in self._collection_config.items():
            if str(config.get("registry_key", "")).strip() == clean_key:
                return item_type

        return None

    def _invalidate_manager_for_registry_key(self, registry_key: str) -> None:
        item_type = self._get_item_type_for_registry_key(registry_key)
        if item_type:
            self._managers.pop(item_type, None)

    def save_package_bundle(self, package_name: str, logic: str, record: dict) -> dict[str, Any]:
        clean_name = self.sanitize_name("package_record", package_name)
        if not clean_name:
            raise ValueError("Invalid package name.")

        normalized_record = dict(record or {})
        normalized_logic = str(logic or "").rstrip()
        if not normalized_logic:
            raise ValueError("Package logic is required.")

        normalized_record["name"] = clean_name
        normalized_record["logic"] = normalized_logic + "\n"

        record_path = self.save_item(
            "package_record",
            clean_name,
            json.dumps(normalized_record, indent=2),
        )

        review_result: dict[str, Any] = {
            "trigger_enabled": self.package_post_save_review_enabled,
            "trigger_attempted": False,
            "trigger_succeeded": False,
            "error": "",
            "task_result": None,
        }

        if self.package_post_save_review_enabled:
            review_result = self._trigger_package_post_save_review(record_path)

        return {
            "record_path": record_path,
            "review_trigger_enabled": review_result["trigger_enabled"],
            "review_trigger_attempted": review_result["trigger_attempted"],
            "review_trigger_succeeded": review_result["trigger_succeeded"],
            "review_trigger_error": review_result["error"],
            "review_task_result": review_result["task_result"],
        }

    def load_package_bundle(self, package_name: str) -> dict:
        clean_name = self.sanitize_name("package_record", package_name)
        if not clean_name:
            raise ValueError("Invalid package name.")

        if not self.item_exists("package_record", clean_name):
            raise FileNotFoundError(f"Package not found: {clean_name}")

        raw_record = self.load_item("package_record", clean_name)
        try:
            parsed = json.loads(raw_record)
        except Exception as exc:
            raise ValueError(f"Could not read package record for {clean_name}: {exc}") from exc

        if not isinstance(parsed, dict):
            raise ValueError(f"Package record must be a JSON object: {clean_name}")

        logic = str(parsed.get("logic", "") or "")
        if logic:
            logic = logic.rstrip() + "\n"

        return {
            "name": clean_name,
            "logic": logic,
            "record": parsed,
        }

    def delete_package_bundle(self, package_name: str) -> dict[str, str]:
        clean_name = self.sanitize_name("package_record", package_name)
        if not clean_name:
            raise ValueError("Invalid package name.")

        if not self.item_exists("package_record", clean_name):
            raise FileNotFoundError(f"Package not found: {clean_name}")

        record_deleted = self.delete_item("package_record", clean_name)

        return {
            "record_path": record_deleted,
        }

    def package_bundle_exists(self, package_name: str) -> bool:
        clean_name = self.sanitize_name("package_record", package_name)
        if not clean_name:
            return False

        return self.item_exists("package_record", clean_name)

    def list_package_bundles(self) -> list[str]:
        return sorted(self.list_items("package_record"), key=str.lower)

    def save_agent_foundry_blueprint(
        self,
        foundry_name: str,
        blueprint_text: str,
    ) -> dict[str, Any]:
        clean_name = self.sanitize_name("agent_foundry_blueprint", foundry_name)
        if not clean_name:
            raise ValueError("Invalid Agent Foundry blueprint name.")

        blueprint_path = Path(self.get_agent_foundry_blueprint_file(clean_name))
        blueprint_path.parent.mkdir(parents=True, exist_ok=True)
        blueprint_path.write_text(str(blueprint_text or ""), encoding="utf-8")

        return {
            "blueprint_path": str(blueprint_path.resolve()),
        }

    def load_agent_foundry_blueprint(self, foundry_name: str) -> str:
        clean_name = self.sanitize_name("agent_foundry_blueprint", foundry_name)
        if not clean_name:
            raise ValueError("Invalid Agent Foundry blueprint name.")

        blueprint_path = Path(self.get_agent_foundry_blueprint_file(clean_name))
        if not blueprint_path.exists():
            raise FileNotFoundError(f"Agent Foundry blueprint not found: {clean_name}")

        return blueprint_path.read_text(encoding="utf-8")

    def delete_agent_foundry_blueprint(self, foundry_name: str) -> dict[str, str]:
        clean_name = self.sanitize_name("agent_foundry_blueprint", foundry_name)
        if not clean_name:
            raise ValueError("Invalid Agent Foundry blueprint name.")

        blueprint_path = Path(self.get_agent_foundry_blueprint_file(clean_name))
        if not blueprint_path.exists():
            raise FileNotFoundError(f"Agent Foundry blueprint not found: {clean_name}")

        blueprint_path.unlink()

        return {
            "blueprint_path": str(blueprint_path.resolve()),
        }

    def agent_foundry_blueprint_exists(self, foundry_name: str) -> bool:
        clean_name = self.sanitize_name("agent_foundry_blueprint", foundry_name)
        if not clean_name:
            return False

        return Path(self.get_agent_foundry_blueprint_file(clean_name)).exists()

    def list_agent_foundry_blueprints(self) -> list[str]:
        agents_dir = Path(self.get_agent_foundry_agents_directory())
        if not agents_dir.exists():
            return []

        results: list[str] = []
        for child in agents_dir.iterdir():
            if not child.is_dir():
                continue
            blueprint_path = child / f"{child.name}.blueprint.txt"
            if blueprint_path.exists():
                results.append(child.name)

        return sorted(results, key=str.lower)

    def save_agent_foundry_metadata(self, foundry_name: str, record: dict) -> dict[str, Any]:
        clean_name = self.sanitize_name("agent_foundry_metadata", foundry_name)
        if not clean_name:
            raise ValueError("Invalid Agent Foundry metadata name.")

        normalized_record = dict(record or {})
        normalized_record["name"] = clean_name

        record_path = Path(self.get_agent_foundry_metadata_file(clean_name))
        record_path.parent.mkdir(parents=True, exist_ok=True)
        record_path.write_text(
            json.dumps(normalized_record, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        return {
            "record_path": str(record_path.resolve()),
        }

    def load_agent_foundry_metadata(self, foundry_name: str) -> dict:
        clean_name = self.sanitize_name("agent_foundry_metadata", foundry_name)
        if not clean_name:
            raise ValueError("Invalid Agent Foundry metadata name.")

        record_path = Path(self.get_agent_foundry_metadata_file(clean_name))
        if not record_path.exists():
            raise FileNotFoundError(f"Agent Foundry metadata not found: {clean_name}")

        raw_record = record_path.read_text(encoding="utf-8")
        try:
            parsed = json.loads(raw_record)
        except Exception as exc:
            raise ValueError(f"Could not read Agent Foundry metadata for {clean_name}: {exc}") from exc

        if not isinstance(parsed, dict):
            raise ValueError(f"Agent Foundry metadata must be a JSON object: {clean_name}")

        return {
            "name": clean_name,
            "record": parsed,
        }

    def delete_agent_foundry_metadata(self, foundry_name: str) -> dict[str, str]:
        clean_name = self.sanitize_name("agent_foundry_metadata", foundry_name)
        if not clean_name:
            raise ValueError("Invalid Agent Foundry metadata name.")

        record_path = Path(self.get_agent_foundry_metadata_file(clean_name))
        if not record_path.exists():
            raise FileNotFoundError(f"Agent Foundry metadata not found: {clean_name}")

        record_path.unlink()

        return {
            "record_path": str(record_path.resolve()),
        }

    def agent_foundry_metadata_exists(self, foundry_name: str) -> bool:
        clean_name = self.sanitize_name("agent_foundry_metadata", foundry_name)
        if not clean_name:
            return False

        return Path(self.get_agent_foundry_metadata_file(clean_name)).exists()

    def list_agent_foundry_metadata(self) -> list[str]:
        agents_dir = Path(self.get_agent_foundry_agents_directory())
        if not agents_dir.exists():
            return []

        results: list[str] = []
        for child in agents_dir.iterdir():
            if not child.is_dir():
                continue
            metadata_path = child / f"{child.name}.agent_foundry.json"
            if metadata_path.exists():
                results.append(child.name)

        return sorted(results, key=str.lower)

    def _trigger_package_post_save_review(self, record_path: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "trigger_enabled": True,
            "trigger_attempted": False,
            "trigger_succeeded": False,
            "error": "",
            "task_result": None,
        }

        try:
            attached_file_path = str(Path(record_path).resolve())

            if not attached_file_path.strip():
                raise ValueError("Saved package path was blank.")

            if not Path(attached_file_path).exists():
                raise FileNotFoundError(f"Saved package file not found: {attached_file_path}")

            from Operations.task_runner import run_task

            result["trigger_attempted"] = True
            task_result = run_task(
                base_dir=self.base_dir,
                agent_name=self.package_post_save_review_agent_name,
                task_name=self.package_post_save_review_task_name,
                runtime_payload={
                    "attached_file_path": attached_file_path,
                    "source_agent_name": self.package_post_save_review_agent_name,
                    "source_task_name": self.package_post_save_review_task_name,
                },
            )

            result["task_result"] = task_result
            result["trigger_succeeded"] = True
            return result

        except Exception as exc:
            result["error"] = str(exc)
            return result

    def _get_manager(self, item_type: str) -> FileCollectionManager:
        normalized_type = item_type.strip().lower()

        if normalized_type not in self._collection_config:
            raise ValueError(f"Unknown collection type: {item_type}")

        if normalized_type not in self._managers:
            config = self._collection_config[normalized_type]
            registry_key = str(config.get("registry_key", "")).strip()

            explicit_storage_dir: Optional[str] = None
            if registry_key:
                try:
                    explicit_storage_dir = self.get_storage_entry_directory(registry_key)
                except KeyError:
                    explicit_storage_dir = None

            if explicit_storage_dir:
                self._managers[normalized_type] = FileCollectionManager(
                    base_dir=self.base_dir,
                    folder_name=str(config["folder_name"]),
                    file_extension=str(config["file_extension"]),
                    use_item_subfolder=bool(config.get("use_item_subfolder", False)),
                    explicit_storage_dir=explicit_storage_dir,
                )
            else:
                self._managers[normalized_type] = FileCollectionManager(
                    base_dir=self.base_dir,
                    folder_name=str(config["folder_name"]),
                    file_extension=str(config["file_extension"]),
                    use_item_subfolder=bool(config.get("use_item_subfolder", False)),
                )

        return self._managers[normalized_type]

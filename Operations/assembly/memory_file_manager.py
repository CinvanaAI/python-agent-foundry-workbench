from __future__ import annotations

from pathlib import Path
from typing import Any

from Operations.assembly.agent_paths import AgentPaths
from Operations.assembly.agent_schema import clean_text


class MemoryFileManager:
    def __init__(self, paths: AgentPaths) -> None:
        self.paths = paths

    def ensure_memory_files_for_agent(self, agent_data: dict[str, Any]) -> None:
        agent_name = clean_text(agent_data.get("name", ""))
        if not agent_name:
            raise ValueError("Agent name is required before ensuring memory files.")

        for group in agent_data.get("groups", []):
            if not isinstance(group, dict):
                continue

            for task in group.get("tasks", []):
                if not isinstance(task, dict):
                    continue

                self.ensure_memory_files_for_task(
                    agent_name=agent_name,
                    task_data=task,
                )

    def ensure_memory_files_for_task(self, agent_name: str, task_data: dict[str, Any]) -> None:
        task_name = clean_text(task_data.get("name", ""))
        if not task_name:
            raise ValueError("Task name is required before ensuring memory files.")

        memory_entries = task_data.get("memory", [])
        if memory_entries in (None, ""):
            memory_entries = []
            task_data["memory"] = memory_entries

        if not isinstance(memory_entries, list):
            raise ValueError(f"Task '{task_name}' memory must be a list.")

        for index, memory_entry in enumerate(memory_entries, start=1):
            if not isinstance(memory_entry, dict):
                raise ValueError(f"Task '{task_name}' memory entry {index} must be a JSON object.")

            memory_name = clean_text(memory_entry.get("name", "")) or f"Memory {index}"
            has_file = bool(memory_entry.get("has_file", False))

            memory_entry["name"] = memory_name
            memory_entry["has_file"] = has_file

            if "content" not in memory_entry or memory_entry.get("content") is None:
                memory_entry["content"] = ""
            else:
                memory_entry["content"] = str(memory_entry.get("content", ""))

            if not has_file:
                memory_entry["file_path"] = ""
                continue

            desired_path = self.paths.get_memory_file_path(
                agent_name=agent_name,
                task_name=task_name,
                memory_name=memory_name,
            ).resolve()

            existing_file_path = clean_text(memory_entry.get("file_path", ""))
            existing_path = Path(existing_file_path).expanduser().resolve() if existing_file_path else None

            if existing_path is not None and existing_path != desired_path:
                if existing_path.exists() and existing_path.is_file():
                    if desired_path.exists():
                        raise FileExistsError(
                            "Cannot move memory file because the desired memory file already exists.\n"
                            f"Existing memory file: {existing_path}\n"
                            f"Desired memory file: {desired_path}"
                        )

                    desired_path.parent.mkdir(parents=True, exist_ok=True)
                    existing_path.rename(desired_path)

            desired_path.parent.mkdir(parents=True, exist_ok=True)

            if not desired_path.exists():
                desired_path.write_text("{}\n", encoding="utf-8")
            elif not desired_path.is_file():
                raise ValueError(f"Memory path exists but is not a file: {desired_path}")

            memory_entry["file_path"] = str(desired_path)

    def delete_memory_files(self, file_paths: object) -> list[str]:
        if file_paths in (None, ""):
            return []

        if not isinstance(file_paths, list):
            raise ValueError("file_paths must be a list.")

        deleted_paths: list[str] = []
        seen_paths: set[str] = set()

        for index, raw_path in enumerate(file_paths, start=1):
            path_text = clean_text(raw_path)
            if not path_text:
                continue

            path = Path(path_text).expanduser().resolve()
            path_key = str(path)

            if path_key in seen_paths:
                continue

            seen_paths.add(path_key)

            if not path.exists():
                continue

            if not path.is_file():
                raise ValueError(
                    f"Memory file deletion target exists but is not a file at index {index}: {path}"
                )

            path.unlink()
            deleted_paths.append(path_key)

        return deleted_paths
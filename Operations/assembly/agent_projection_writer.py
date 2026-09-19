from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from Operations.assembly.agent_paths import AgentPaths
from Operations.assembly.agent_schema import clean_text


class AgentProjectionWriter:
    """
    Writes generated group/task projection files from a canonical agent object.

    Rule:
        - Agent JSON remains the source of truth.
        - Each group file is a projection of one group.
        - Each task belongs to exactly one group.
        - Each task file is a projection written by agent-wide unique task name.
    """

    def __init__(self, paths: AgentPaths) -> None:
        self.paths = paths

    def write_projection_files(self, agent_data: dict[str, Any]) -> dict[str, list[str]]:
        agent_name = clean_text(agent_data.get("name", ""))
        if not agent_name:
            raise ValueError("Agent name is required before writing projections.")

        agent_folder = self.paths.get_agent_folder(agent_name)
        agent_folder.mkdir(parents=True, exist_ok=True)

        expected_group_filenames: set[str] = set()
        expected_task_filenames: set[str] = set()

        written_group_files: list[str] = []
        written_task_files: list[str] = []

        task_projection_map: dict[str, dict[str, Any]] = {}

        for group in agent_data.get("groups", []):
            if not isinstance(group, dict):
                continue

            group_name = clean_text(group.get("name", ""))
            if not group_name:
                raise ValueError("Cannot write group projection for unnamed group.")

            group_path = self.paths.get_group_file_path(
                agent_name=agent_name,
                group_name=group_name,
            )

            expected_group_filenames.add(group_path.name)
            self._write_json_file(group_path, copy.deepcopy(group))
            written_group_files.append(str(group_path))

            for task in group.get("tasks", []):
                if not isinstance(task, dict):
                    continue

                task_name = clean_text(task.get("name", ""))
                if not task_name:
                    raise ValueError(f"Group '{group_name}' contains unnamed task.")

                task_path = self.paths.get_task_file_path(
                    agent_name=agent_name,
                    task_name=task_name,
                )

                expected_task_filenames.add(task_path.name)

                if task_path.name not in task_projection_map:
                    task_projection_map[task_path.name] = copy.deepcopy(task)
                    continue

                existing_task = task_projection_map[task_path.name]
                existing_task_name = clean_text(existing_task.get("name", ""))

                if existing_task_name != task_name:
                    raise ValueError(
                        f"Task projection filename collision: {task_path.name} is shared by "
                        f"'{existing_task_name}' and '{task_name}'."
                    )

        for task_file_name, task_payload in task_projection_map.items():
            task_name = clean_text(task_payload.get("name", ""))
            if not task_name:
                raise ValueError(f"Cannot write unnamed task projection: {task_file_name}")

            task_path = self.paths.get_task_file_path(
                agent_name=agent_name,
                task_name=task_name,
            )

            if task_path.name != task_file_name:
                raise ValueError(
                    f"Task projection filename mismatch: {task_path.name} != {task_file_name}"
                )

            self._write_json_file(task_path, task_payload)
            written_task_files.append(str(task_path))

        self._delete_stale_projection_files(
            agent_folder=agent_folder,
            expected_group_filenames=expected_group_filenames,
            expected_task_filenames=expected_task_filenames,
        )

        return {
            "group_files": written_group_files,
            "task_files": written_task_files,
        }

    def _write_json_file(self, file_path: Path, payload: dict[str, Any]) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False).rstrip() + "\n",
            encoding="utf-8",
        )

    def _delete_stale_projection_files(
        self,
        agent_folder: Path,
        expected_group_filenames: set[str],
        expected_task_filenames: set[str],
    ) -> None:
        if not agent_folder.exists():
            return

        if not agent_folder.is_dir():
            raise ValueError(f"Agent folder path exists but is not a directory: {agent_folder}")

        for file_path in agent_folder.glob("*.group.json"):
            if file_path.name not in expected_group_filenames:
                file_path.unlink()

        for file_path in agent_folder.glob("*.task.json"):
            if file_path.name not in expected_task_filenames:
                file_path.unlink()
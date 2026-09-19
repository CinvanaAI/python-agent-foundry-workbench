from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from typing import Any, Optional

from collection_handoff import CollectionHandoff

from Operations.assembly.agent_normalizer import AgentNormalizer
from Operations.assembly.agent_paths import AgentPaths
from Operations.assembly.agent_projection_writer import AgentProjectionWriter
from Operations.assembly.agent_schema import OUTCASTS_GROUP_NAME, clean_text
from Operations.assembly.agent_validator import AgentValidator
from Operations.assembly.memory_file_manager import MemoryFileManager


class AssemblyManager:
    """
    Clean canonical agent manager.

    Rule:
        - Agent JSON is the source of truth.
        - Group files are generated projections.
        - Task files are generated projections.
        - Memory files are managed from task memory entries.
        - A task belongs to exactly one group: the group whose tasks[] list contains it.
        - No compatibility payload aliases.
    """

    def __init__(self, handoff: Optional[CollectionHandoff] = None) -> None:
        self.handoff = handoff or CollectionHandoff()
        self.paths = AgentPaths(handoff=self.handoff)
        self.normalizer = AgentNormalizer()
        self.validator = AgentValidator()
        self.memory_file_manager = MemoryFileManager(paths=self.paths)
        self.projection_writer = AgentProjectionWriter(paths=self.paths)

    def sanitize_name(self, raw_name: object) -> str:
        return self.paths.sanitize_name(raw_name)

    def sanitize_agent_name(self, raw_name: object) -> str:
        return self.paths.sanitize_agent_name(raw_name)

    def sanitize_group_name(self, raw_name: object) -> str:
        return self.paths.sanitize_group_name(raw_name)

    def sanitize_task_name(self, raw_name: object) -> str:
        return self.paths.sanitize_task_name(raw_name)

    def sanitize_memory_name(self, raw_name: object) -> str:
        return self.paths.sanitize_memory_name(raw_name)

    def get_outcasts_group_name(self) -> str:
        return OUTCASTS_GROUP_NAME

    def get_agents_dir(self) -> str:
        return str(self.paths.get_assemblies_dir())

    def get_agent_folder(self, agent_name: object) -> str:
        return str(self.paths.get_agent_folder(agent_name))

    def get_agent_file_path(self, agent_name: object) -> Path:
        return self.paths.get_agent_file_path(agent_name)

    def get_group_file_path(self, agent_name: object, group_name: object) -> Path:
        return self.paths.get_group_file_path(agent_name, group_name)

    def get_task_file_path(self, agent_name: object, task_name: object) -> Path:
        return self.paths.get_task_file_path(agent_name, task_name)

    def get_memory_file_path(
        self,
        agent_name: object,
        task_name: object,
        memory_name: object,
    ) -> Path:
        return self.paths.get_memory_file_path(
            agent_name=agent_name,
            task_name=task_name,
            memory_name=memory_name,
        )

    def save_agent(self, agent_name: str, agent_payload: object) -> str:
        """
        Save a full canonical agent payload.

        agent_payload must be:

        {
          "name": "...",
          "default_returns": [],
          "groups": []
        }
        """
        clean_agent_name = self.sanitize_agent_name(agent_name)
        if not clean_agent_name:
            raise ValueError("Agent name is required.")

        if not isinstance(agent_payload, dict):
            raise ValueError("save_agent requires a canonical agent dict.")

        if "groups" not in agent_payload:
            raise ValueError("Canonical agent payload must contain 'groups'.")

        raw_agent = copy.deepcopy(agent_payload)
        raw_agent["name"] = clean_text(raw_agent.get("name", "")) or clean_agent_name

        if self.sanitize_agent_name(raw_agent["name"]) != clean_agent_name:
            raise ValueError(
                f"Agent payload name '{raw_agent['name']}' does not match "
                f"target agent '{clean_agent_name}'."
            )

        normalized_agent = self.normalizer.normalize_agent(
            raw_agent=raw_agent,
            fallback_name=clean_agent_name,
        )

        self.memory_file_manager.ensure_memory_files_for_agent(normalized_agent)
        self.validator.validate_agent(normalized_agent)

        agent_folder = self.paths.get_agent_folder(clean_agent_name)
        agent_folder.mkdir(parents=True, exist_ok=True)

        agent_file_path = self.paths.get_agent_file_path(clean_agent_name)
        self._write_json_file(agent_file_path, normalized_agent)

        self.projection_writer.write_projection_files(normalized_agent)

        return str(agent_file_path)

    def load_agent_source(self, agent_name: str) -> str:
        file_path = self.get_agent_file_path(agent_name)
        if not file_path.exists():
            raise FileNotFoundError(f"Agent file not found: {file_path}")

        return file_path.read_text(encoding="utf-8")

    def load_agent_data(self, agent_name: str) -> dict[str, Any]:
        clean_agent_name = self.sanitize_agent_name(agent_name)
        if not clean_agent_name:
            raise ValueError("Agent name is required.")

        file_path = self.paths.get_agent_file_path(clean_agent_name)
        if not file_path.exists():
            raise FileNotFoundError(f"Agent file not found: {file_path}")

        raw_agent = self._load_json_file(file_path, "Agent file")

        normalized_agent = self.normalizer.normalize_agent(
            raw_agent=raw_agent,
            fallback_name=clean_agent_name,
        )

        self.validator.validate_agent(normalized_agent)

        return normalized_agent

    def list_agents(self) -> list[str]:
        agents_dir = self.paths.get_assemblies_dir()
        agents_dir.mkdir(parents=True, exist_ok=True)

        result: list[str] = []

        for agent_folder in agents_dir.iterdir():
            if not agent_folder.is_dir():
                continue

            agent_name = agent_folder.name.strip()
            if not agent_name:
                continue

            agent_file_path = self.paths.get_agent_file_path(agent_name)
            if agent_file_path.exists() and agent_file_path.is_file():
                result.append(agent_name)

        result.sort(key=str.lower)
        return result

    def delete_agent(self, agent_name: str) -> str:
        clean_agent_name = self.sanitize_agent_name(agent_name)
        if not clean_agent_name:
            raise ValueError("Agent name is required.")

        agent_file_path = self.paths.get_agent_file_path(clean_agent_name)
        agent_folder = self.paths.get_agent_folder(clean_agent_name)

        if not agent_folder.exists():
            raise FileNotFoundError(f"Agent not found: {clean_agent_name}")

        if not agent_folder.is_dir():
            raise ValueError(f"Agent path exists but is not a directory: {agent_folder}")

        shutil.rmtree(agent_folder)
        return str(agent_file_path)

    def agent_exists(self, agent_name: str) -> bool:
        try:
            return self.paths.get_agent_file_path(agent_name).exists()
        except ValueError:
            return False

    def get_task_names(self, agent_name: str) -> list[str]:
        agent_data = self.load_agent_data(agent_name)

        task_names: list[str] = []
        for group in agent_data.get("groups", []):
            if not isinstance(group, dict):
                continue

            for task in group.get("tasks", []):
                if not isinstance(task, dict):
                    continue

                task_name = clean_text(task.get("name", ""))
                if task_name and task_name not in task_names:
                    task_names.append(task_name)

        return task_names

    def load_task_data(self, agent_name: str, task_name: str) -> dict[str, Any]:
        clean_task_name = self.sanitize_task_name(task_name)
        if not clean_task_name:
            raise ValueError("Task name is required.")

        agent_data = self.load_agent_data(agent_name)

        for group in agent_data.get("groups", []):
            if not isinstance(group, dict):
                continue

            for task in group.get("tasks", []):
                if not isinstance(task, dict):
                    continue

                current_task_name = clean_text(task.get("name", ""))
                if self.sanitize_task_name(current_task_name) == clean_task_name:
                    return copy.deepcopy(task)

        raise FileNotFoundError(
            f"Task '{task_name}' was not found in agent '{agent_name}'."
        )

    def load_group_data(self, agent_name: str, group_name: str) -> dict[str, Any]:
        clean_group_name = clean_text(group_name)
        if not clean_group_name:
            raise ValueError("Group name is required.")

        agent_data = self.load_agent_data(agent_name)

        for group in agent_data.get("groups", []):
            if not isinstance(group, dict):
                continue

            if clean_text(group.get("name", "")) == clean_group_name:
                return copy.deepcopy(group)

        raise FileNotFoundError(
            f"Group '{group_name}' was not found in agent '{agent_name}'."
        )

    def get_task_data(self, agent_name: str, task_name: str) -> dict[str, Any]:
        return self.load_task_data(agent_name, task_name)

    def load_task(self, agent_name: str, task_name: str) -> dict[str, Any]:
        return self.load_task_data(agent_name, task_name)

    def read_task(self, agent_name: str, task_name: str) -> dict[str, Any]:
        return self.load_task_data(agent_name, task_name)

    def get_group_data(self, agent_name: str, group_name: str) -> dict[str, Any]:
        return self.load_group_data(agent_name, group_name)

    def load_group(self, agent_name: str, group_name: str) -> dict[str, Any]:
        return self.load_group_data(agent_name, group_name)

    def read_group(self, agent_name: str, group_name: str) -> dict[str, Any]:
        return self.load_group_data(agent_name, group_name)

    def get_agent_data(self, agent_name: str) -> dict[str, Any]:
        return self.load_agent_data(agent_name)

    def load_agent(self, agent_name: str) -> dict[str, Any]:
        return self.load_agent_data(agent_name)

    def read_agent(self, agent_name: str) -> dict[str, Any]:
        return self.load_agent_data(agent_name)

    def _write_json_file(self, file_path: Path, payload: dict[str, Any]) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False).rstrip() + "\n",
            encoding="utf-8",
        )

    def _load_json_file(self, file_path: Path, label: str) -> dict[str, Any]:
        try:
            parsed = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{label} is not valid JSON: {file_path}: {exc}") from exc

        if not isinstance(parsed, dict):
            raise ValueError(f"{label} must contain a JSON object: {file_path}")

        return parsed
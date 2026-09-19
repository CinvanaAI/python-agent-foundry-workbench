from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from collection_handoff import CollectionHandoff

from Operations.assembly.agent_paths import AgentPaths
from Operations.assembly.assembly_manager import AssemblyManager


class AssemblyReader:
    """
    Read-only facade for canonical agent storage.

    Rule:
        - Agent JSON is the source of truth.
        - Group/task files are projections.
        - Public reads go through AssemblyManager so normalization and validation
          stay centralized.
    """

    def __init__(self, handoff: Optional[CollectionHandoff] = None) -> None:
        self.handoff = handoff or CollectionHandoff()
        self.paths = AgentPaths(handoff=self.handoff)
        self.manager = AssemblyManager(handoff=self.handoff)

    def sanitize_name(self, raw_name: object) -> str:
        return self.paths.sanitize_name(raw_name)

    def sanitize_agent_name(self, raw_name: object) -> str:
        return self.paths.sanitize_agent_name(raw_name)

    def sanitize_group_name(self, raw_name: object) -> str:
        return self.paths.sanitize_group_name(raw_name)

    def sanitize_task_name(self, raw_name: object) -> str:
        return self.paths.sanitize_task_name(raw_name)

    def get_agents_dir(self) -> Path:
        return self.paths.get_assemblies_dir()

    def get_agent_folder(self, agent_name: object) -> Path:
        return self.paths.get_agent_folder(agent_name)

    def get_agent_file_path(self, agent_name: object) -> Path:
        return self.paths.get_agent_file_path(agent_name)

    def get_group_file_path(self, agent_name: object, group_name: object) -> Path:
        return self.paths.get_group_file_path(agent_name, group_name)

    def get_task_file_path(self, agent_name: object, task_name: object) -> Path:
        return self.paths.get_task_file_path(agent_name, task_name)

    def load_agent_source(self, agent_name: object) -> str:
        return self.manager.load_agent_source(str(agent_name or ""))

    def load_agent_data(self, agent_name: object) -> dict[str, Any]:
        return self.manager.load_agent_data(str(agent_name or ""))

    def get_agent_data(self, agent_name: object) -> dict[str, Any]:
        return self.load_agent_data(agent_name)

    def load_agent(self, agent_name: object) -> dict[str, Any]:
        return self.load_agent_data(agent_name)

    def read_agent(self, agent_name: object) -> dict[str, Any]:
        return self.load_agent_data(agent_name)

    def load_task_data(
        self,
        agent_name: object,
        task_name: object,
    ) -> dict[str, Any]:
        return self.manager.load_task_data(
            agent_name=str(agent_name or ""),
            task_name=str(task_name or ""),
        )

    def get_task_data(
        self,
        agent_name: object,
        task_name: object,
    ) -> dict[str, Any]:
        return self.load_task_data(
            agent_name=agent_name,
            task_name=task_name,
        )

    def load_task(
        self,
        agent_name: object,
        task_name: object,
    ) -> dict[str, Any]:
        return self.load_task_data(
            agent_name=agent_name,
            task_name=task_name,
        )

    def read_task(
        self,
        agent_name: object,
        task_name: object,
    ) -> dict[str, Any]:
        return self.load_task_data(
            agent_name=agent_name,
            task_name=task_name,
        )

    def load_group_data(
        self,
        agent_name: object,
        group_name: object,
    ) -> dict[str, Any]:
        return self.manager.load_group_data(
            agent_name=str(agent_name or ""),
            group_name=str(group_name or ""),
        )

    def get_group_data(
        self,
        agent_name: object,
        group_name: object,
    ) -> dict[str, Any]:
        return self.load_group_data(
            agent_name=agent_name,
            group_name=group_name,
        )

    def load_group(
        self,
        agent_name: object,
        group_name: object,
    ) -> dict[str, Any]:
        return self.load_group_data(
            agent_name=agent_name,
            group_name=group_name,
        )

    def read_group(
        self,
        agent_name: object,
        group_name: object,
    ) -> dict[str, Any]:
        return self.load_group_data(
            agent_name=agent_name,
            group_name=group_name,
        )

    def get_task_names(self, agent_name: object) -> list[str]:
        return self.manager.get_task_names(str(agent_name or ""))

    def list_agents(self) -> list[str]:
        return self.manager.list_agents()

    def agent_exists(self, agent_name: object) -> bool:
        return self.manager.agent_exists(str(agent_name or ""))
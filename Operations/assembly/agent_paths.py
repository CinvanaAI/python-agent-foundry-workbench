from __future__ import annotations

from pathlib import Path
from typing import Optional

from collection_handoff import CollectionHandoff

from Operations.assembly.agent_schema import (
    build_agent_filename,
    build_group_filename,
    build_memory_filename,
    build_task_filename,
)


class AgentPaths:
    def __init__(self, handoff: Optional[CollectionHandoff] = None) -> None:
        self.handoff = handoff or CollectionHandoff()

    def sanitize_name(self, raw_name: object) -> str:
        return self.handoff.sanitize_name("assembly", str(raw_name or ""))

    def sanitize_agent_name(self, raw_name: object) -> str:
        return self.sanitize_name(raw_name)

    def sanitize_group_name(self, raw_name: object) -> str:
        return self.sanitize_name(raw_name)

    def sanitize_task_name(self, raw_name: object) -> str:
        return self.sanitize_name(raw_name)

    def sanitize_memory_name(self, raw_name: object) -> str:
        return self.sanitize_name(raw_name)

    def get_assemblies_dir(self) -> Path:
        return Path(self.handoff.get_storage_dir("assembly"))

    def get_agent_folder(self, agent_name: object) -> Path:
        clean_agent_name = self.sanitize_agent_name(agent_name)
        if not clean_agent_name:
            raise ValueError("Agent name is required.")

        return self.get_assemblies_dir() / clean_agent_name

    def get_agent_file_path(self, agent_name: object) -> Path:
        clean_agent_name = self.sanitize_agent_name(agent_name)
        if not clean_agent_name:
            raise ValueError("Agent name is required.")

        return self.get_agent_folder(clean_agent_name) / build_agent_filename(clean_agent_name)

    def get_group_file_path(self, agent_name: object, group_name: object) -> Path:
        clean_agent_name = self.sanitize_agent_name(agent_name)
        clean_group_name = self.sanitize_group_name(group_name)

        if not clean_agent_name:
            raise ValueError("Agent name is required.")
        if not clean_group_name:
            raise ValueError("Group name is required.")

        return self.get_agent_folder(clean_agent_name) / build_group_filename(clean_group_name)

    def get_task_file_path(self, agent_name: object, task_name: object) -> Path:
        clean_agent_name = self.sanitize_agent_name(agent_name)
        clean_task_name = self.sanitize_task_name(task_name)

        if not clean_agent_name:
            raise ValueError("Agent name is required.")
        if not clean_task_name:
            raise ValueError("Task name is required.")

        return self.get_agent_folder(clean_agent_name) / build_task_filename(clean_task_name)

    def get_memory_file_path(
        self,
        agent_name: object,
        task_name: object,
        memory_name: object,
    ) -> Path:
        clean_agent_name = self.sanitize_agent_name(agent_name)
        clean_task_name = self.sanitize_task_name(task_name)
        clean_memory_name = self.sanitize_memory_name(memory_name)

        if not clean_agent_name:
            raise ValueError("Agent name is required.")
        if not clean_task_name:
            raise ValueError("Task name is required.")
        if not clean_memory_name:
            raise ValueError("Memory name is required.")

        return self.get_agent_folder(clean_agent_name) / build_memory_filename(
            task_name=clean_task_name,
            memory_name=clean_memory_name,
        )
from __future__ import annotations

import copy


class AgentTaskLookupControllerMixin:
    """
    Generic Assembly lookup helpers for UI selectors.

    Owns:
        - listing saved agents for dropdowns/pickers
        - listing groups for a selected agent
        - listing tasks for a selected agent/group
        - loading selected task data through the existing Assembly backend

    Does not own:
        - rendering widgets
        - package-specific behavior
        - Friendship behavior
        - User Approval behavior
        - saving/mutating agent files

    Source of truth:
        self.assembly_manager
    """

    def _clean_lookup_text(self, value: object) -> str:
        return str(value or "").strip()

    def _get_agent_lookup_options(self) -> list[str]:
        if not hasattr(self, "assembly_manager"):
            raise RuntimeError("Assembly manager is not configured.")

        raw_agents = self.assembly_manager.list_agents()

        if raw_agents in (None, ""):
            return []

        if not isinstance(raw_agents, list):
            raise ValueError("assembly_manager.list_agents() must return a list.")

        agents: list[str] = []

        for item in raw_agents:
            agent_name = self._clean_lookup_text(item)
            if agent_name and agent_name not in agents:
                agents.append(agent_name)

        agents.sort(key=str.lower)
        return agents

    def _load_agent_data_for_lookup(self, agent_name: object) -> dict:
        clean_agent_name = self._clean_lookup_text(agent_name)
        if not clean_agent_name:
            raise ValueError("Agent name is required.")

        if not hasattr(self, "assembly_manager"):
            raise RuntimeError("Assembly manager is not configured.")

        agent_data = self.assembly_manager.load_agent_data(clean_agent_name)

        if not isinstance(agent_data, dict):
            raise ValueError(
                f"Agent '{clean_agent_name}' did not load as a JSON object."
            )

        return agent_data

    def _get_group_lookup_options(self, agent_name: object) -> list[str]:
        agent_data = self._load_agent_data_for_lookup(agent_name)

        raw_groups = agent_data.get("groups", [])
        if raw_groups in (None, ""):
            return []

        if not isinstance(raw_groups, list):
            raise ValueError(f"Agent '{agent_name}' groups must be a list.")

        groups: list[str] = []

        for group in raw_groups:
            if not isinstance(group, dict):
                continue

            group_name = self._clean_lookup_text(group.get("name", ""))
            if group_name and group_name not in groups:
                groups.append(group_name)

        return groups

    def _get_task_lookup_options(
        self,
        agent_name: object,
        group_name: object = "",
    ) -> list[str]:
        agent_data = self._load_agent_data_for_lookup(agent_name)
        clean_group_name = self._clean_lookup_text(group_name)

        raw_groups = agent_data.get("groups", [])
        if raw_groups in (None, ""):
            return []

        if not isinstance(raw_groups, list):
            raise ValueError(f"Agent '{agent_name}' groups must be a list.")

        tasks: list[str] = []

        for group in raw_groups:
            if not isinstance(group, dict):
                continue

            current_group_name = self._clean_lookup_text(group.get("name", ""))

            if clean_group_name and current_group_name != clean_group_name:
                continue

            raw_tasks = group.get("tasks", [])
            if raw_tasks in (None, ""):
                continue

            if not isinstance(raw_tasks, list):
                raise ValueError(
                    f"Agent '{agent_name}' group '{current_group_name}' tasks must be a list."
                )

            for task in raw_tasks:
                if not isinstance(task, dict):
                    continue

                task_name = self._clean_lookup_text(task.get("name", ""))
                if task_name and task_name not in tasks:
                    tasks.append(task_name)

        return tasks

    def _get_task_data_for_lookup(
        self,
        agent_name: object,
        task_name: object,
    ) -> dict:
        clean_agent_name = self._clean_lookup_text(agent_name)
        clean_task_name = self._clean_lookup_text(task_name)

        if not clean_agent_name:
            raise ValueError("Agent name is required.")

        if not clean_task_name:
            raise ValueError("Task name is required.")

        if not hasattr(self, "assembly_manager"):
            raise RuntimeError("Assembly manager is not configured.")

        if hasattr(self.assembly_manager, "load_task_data"):
            task_data = self.assembly_manager.load_task_data(
                agent_name=clean_agent_name,
                task_name=clean_task_name,
            )
        else:
            task_data = self._find_task_data_for_lookup(
                agent_name=clean_agent_name,
                task_name=clean_task_name,
            )

        if not isinstance(task_data, dict):
            raise ValueError(
                f"Task '{clean_task_name}' from agent '{clean_agent_name}' "
                "did not load as a JSON object."
            )

        return copy.deepcopy(task_data)

    def _find_task_data_for_lookup(
        self,
        agent_name: object,
        task_name: object,
    ) -> dict:
        clean_task_name = self._clean_lookup_text(task_name)
        agent_data = self._load_agent_data_for_lookup(agent_name)

        raw_groups = agent_data.get("groups", [])
        if not isinstance(raw_groups, list):
            raise ValueError(f"Agent '{agent_name}' groups must be a list.")

        for group in raw_groups:
            if not isinstance(group, dict):
                continue

            raw_tasks = group.get("tasks", [])
            if not isinstance(raw_tasks, list):
                continue

            for task in raw_tasks:
                if not isinstance(task, dict):
                    continue

                if self._clean_lookup_text(task.get("name", "")) == clean_task_name:
                    return copy.deepcopy(task)

        raise ValueError(
            f"Task '{clean_task_name}' was not found in agent '{agent_name}'."
        )
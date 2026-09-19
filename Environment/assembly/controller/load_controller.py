from __future__ import annotations

import copy

from Operations.assembly.agent_schema import build_group_filename


class LoadControllerMixin:
    """
    Loads canonical agent/group/task payloads into the Assembly UI.

    Owns load-side UI population only.
    Backend canonical loading remains in Operations/assembly.
    """

    def _load_tasks_into_tabs(self, tasks: object) -> None:
        if not isinstance(tasks, list):
            raise ValueError("tasks must be a list.")

        outcasts_name = self._get_outcasts_task_group_name()

        groups = [
            {
                "name": outcasts_name,
                "group_file": build_group_filename(outcasts_name),
                "default_returns": [],
                "tasks": copy.deepcopy(tasks),
            }
        ]

        self._load_task_groups_into_tabs(groups)

    def _load_task_groups_into_tabs(self, groups: object) -> None:
        self._clear_all_task_tabs()

        if not isinstance(groups, list):
            raise ValueError("groups must be a list.")

        if not groups:
            raise ValueError("Agent must contain at least one group.")

        first_group_info = None

        for group in groups:
            if not isinstance(group, dict):
                raise ValueError("Each group must be a dict.")

            group_name = str(group.get("name", "")).strip()
            if not group_name:
                raise ValueError("Each group must have a name.")

            group_info = self._create_task_group_tab(group_name, select=False)
            self._load_group_defaults_into_tab(group_info, group.get("default_returns", []))

            if first_group_info is None:
                first_group_info = group_info

            raw_tasks = group.get("tasks", [])
            if not isinstance(raw_tasks, list):
                raise ValueError(f"Group '{group_name}' tasks must be a list.")

            for task in raw_tasks:
                if not isinstance(task, dict):
                    raise ValueError(f"Group '{group_name}' contains a non-dict task.")

                self._create_new_task_tab(
                    name=str(task.get("name", "")).strip(),
                    task_status=self._normalize_task_status(task.get("task_status", "On Demand")),
                    workflow=task.get("workflow"),
                    packages=task.get("packages", []),
                    prompts=task.get("prompts", []),
                    triggers=task.get("Triggers", ""),
                    memory=task.get("memory", []),
                    default_returns=task.get("default_returns", []),
                    group_info=group_info,
                    select=False,
                )

        if first_group_info is None:
            raise ValueError("Could not create first group tab.")

        self.task_group_notebook.select(first_group_info["frame"])
        self._last_selected_group_frame = first_group_info["frame"]

        for group_info in self.task_group_tabs:
            if group_info.get("task_tabs"):
                group_info["task_notebook"].select(group_info["task_tabs"][0]["frame"])
                self._last_selected_task_frame_by_group[id(group_info)] = group_info["task_tabs"][0]["frame"]

    def _collect_child_assemblies(self) -> dict:
        return self._collect_tasks()

    def _load_child_assemblies_into_tasks(self, child_assemblies: object) -> None:
        if not isinstance(child_assemblies, dict):
            raise ValueError("child_assemblies must be canonical agent payload dict.")

        self._load_agent_defaults_into_tab(child_assemblies.get("default_returns", []))
        self._load_task_groups_into_tabs(child_assemblies.get("groups", []))
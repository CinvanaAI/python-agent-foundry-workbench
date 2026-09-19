from __future__ import annotations

import copy

from Operations.assembly.agent_schema import build_group_filename, build_task_filename


class SaveControllerMixin:
    """
    Collects live Assembly UI state into the canonical agent payload.

    Owns save-side UI collection only.
    Backend canonical normalization/validation still belongs to Operations/assembly.
    """

    def _sync_task_value_controls(self, tab_info: dict) -> None:
        if hasattr(self, "_refresh_returns_panel"):
            self._refresh_returns_panel(tab_info)

        if hasattr(self, "_refresh_defaults_panel"):
            self._refresh_defaults_panel(tab_info)

    def _collect_package_payloads_from_tab(self, tab_info: dict) -> list[dict]:
        packages: list[dict] = []

        for package_entry in tab_info.get("packages", []):
            if not isinstance(package_entry, dict):
                continue

            packages.append(copy.deepcopy(package_entry))

        return packages

    def _collect_pending_memory_file_deletions(self) -> list[str]:
        pending_paths: list[str] = []
        seen_paths: set[str] = set()

        for tab_info in getattr(self, "assembly_tabs", []):
            if not isinstance(tab_info, dict):
                continue

            raw_pending = tab_info.get("pending_memory_file_deletions", [])
            if not isinstance(raw_pending, list):
                continue

            for raw_path in raw_pending:
                path_text = str(raw_path or "").strip()
                if not path_text or path_text in seen_paths:
                    continue

                seen_paths.add(path_text)
                pending_paths.append(path_text)

        return pending_paths

    def _clear_pending_memory_file_deletions(self) -> None:
        for tab_info in getattr(self, "assembly_tabs", []):
            if isinstance(tab_info, dict):
                tab_info["pending_memory_file_deletions"] = []

    def _sync_special_packages_before_collect(self, tab_info: dict) -> None:
        if not isinstance(tab_info, dict):
            return

        packages = tab_info.get("packages", [])
        if not isinstance(packages, list):
            return

        if not hasattr(self, "_sync_special_package_generated_fields"):
            return

        for package_index, package_entry in enumerate(packages):
            if not isinstance(package_entry, dict):
                continue

            self._sync_special_package_generated_fields(
                tab_info=tab_info,
                package_entry=package_entry,
                package_index=package_index,
                mark_dirty_on_change=False,
            )

    def _collect_single_task_from_tab_no_hydrate(self, tab_info: dict) -> dict:
        self._sync_special_packages_before_collect(tab_info)

        task_name = tab_info["task_name_entry"].get().strip()
        task_status = self._normalize_task_status(tab_info["task_status_var"].get())
        workflow_source = self._collect_workflow_from_tab(tab_info)
        triggers_source = self._collect_triggers_from_tab(tab_info)
        prompts = self._collect_prompts_from_tab(tab_info)
        memory = self._normalize_memory_block(self._collect_memory_from_tab(tab_info))
        default_returns = self._collect_default_returns_from_tab(tab_info)
        current_packages = self._collect_package_payloads_from_tab(tab_info)

        return {
            "name": task_name,
            "task_file": build_task_filename(task_name),
            "task_status": task_status,
            "workflow": {
                "workflow_source": workflow_source,
            },
            "Triggers": triggers_source,
            "default_returns": copy.deepcopy(default_returns),
            "packages": current_packages,
            "prompts": prompts,
            "memory": copy.deepcopy(memory),
        }

    def _collect_single_task_from_tab(self, tab_info: dict) -> dict:
        self._sync_special_packages_before_collect(tab_info)

        task_name = tab_info["task_name_entry"].get().strip()
        task_status = self._normalize_task_status(tab_info["task_status_var"].get())
        workflow_source = self._collect_workflow_from_tab(tab_info)
        triggers_source = self._collect_triggers_from_tab(tab_info)
        prompts = self._collect_prompts_from_tab(tab_info)
        memory = self._normalize_memory_block(self._collect_memory_from_tab(tab_info))
        default_returns = self._collect_default_returns_from_tab(tab_info)

        current_packages = self._collect_package_payloads_from_tab(tab_info)
        refreshed_packages = self._rehydrate_packages_from_disk_for_save(current_packages)

        (
            hydrated_packages,
            merged_triggers,
            previous_auto_sources,
            current_auto_sources,
        ) = self._hydrate_special_packages_for_task(
            task_name=task_name,
            packages=refreshed_packages,
            friendship_state={},
            existing_triggers_text=triggers_source,
        )

        current_agent_name = self._get_parent_name()

        self._update_reverse_friendship_stamps(
            borrower_agent_name=current_agent_name,
            borrower_task_name=task_name,
            old_sources=previous_auto_sources,
            new_sources=current_auto_sources,
        )

        tab_info["packages"] = copy.deepcopy(hydrated_packages)
        tab_info["triggers"] = merged_triggers
        tab_info["memory"] = copy.deepcopy(memory)
        tab_info["default_return_rows"] = copy.deepcopy(default_returns)

        self._load_triggers_into_tab(tab_info, merged_triggers)
        self._refresh_package_editor(tab_info)
        self._sync_task_value_controls(tab_info)

        collected = {
            "name": task_name,
            "task_file": build_task_filename(task_name),
            "task_status": task_status,
            "workflow": {
                "workflow_source": workflow_source,
            },
            "Triggers": merged_triggers,
            "default_returns": copy.deepcopy(default_returns),
            "packages": copy.deepcopy(tab_info["packages"]),
            "prompts": prompts,
            "memory": copy.deepcopy(memory),
        }

        tab_info["loaded_snapshot"] = copy.deepcopy(collected)
        tab_info["dirty"] = False

        return collected

    def _collect_tasks(self) -> dict:
        seen_task_names: set[str] = set()
        groups_payload: list[dict] = []

        for group_info in self.task_group_tabs:
            group_name = str(group_info.get("name", "")).strip()
            if not group_name:
                continue

            group_tasks: list[dict] = []

            for tab_info in group_info.get("task_tabs", []):
                task_name = self._get_task_name_from_tab(tab_info)
                if not task_name:
                    continue

                if task_name in seen_task_names:
                    raise ValueError(
                        f"Duplicate task name across agent: {task_name}. "
                        "Task names must remain unique across the agent for now."
                    )

                task_data = self._collect_single_task_from_tab(tab_info)
                clean_task_name = str(task_data.get("name", "")).strip()

                if not clean_task_name:
                    continue

                if clean_task_name in seen_task_names:
                    raise ValueError(
                        f"Duplicate task name across agent: {clean_task_name}. "
                        "Task names must remain unique across the agent for now."
                    )

                seen_task_names.add(clean_task_name)
                group_tasks.append(task_data)

            groups_payload.append(
                {
                    "name": group_name,
                    "group_file": build_group_filename(group_name),
                    "default_returns": self._collect_group_default_returns(group_info),
                    "tasks": group_tasks,
                }
            )

        return {
            "name": self._get_parent_name(),
            "default_returns": self._collect_agent_default_returns(),
            "groups": groups_payload,
        }
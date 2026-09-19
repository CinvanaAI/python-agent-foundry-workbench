from __future__ import annotations

import copy
from typing import Any

from Operations.assembly.agent_schema import VALID_TASK_STATUSES


class AssemblyTasksNormalizationMixin:
    """
    UI-side adapter helpers for the Assembly task editor.

    This file does not own backend canonical schema normalization.
    Canonical agent/task/group/package normalization belongs to:

        Operations.assembly.agent_normalizer.AgentNormalizer

    This mixin only keeps frontend-owned responsibilities:
        - Outcasts display/name helper used by task/group tabs
        - lightweight normalization for live widget/tab state
        - package snapshot loading through the UI package controller
        - package snapshot list guarding before collection/hydration

    This file intentionally does not support old parent-shell payloads,
    old Defaults blocks, provisions, package-name string refs, task-level
    friendship/package_sources side channels, or legacy parent/group/task
    payload conversion.
    """

    OUTCASTS_GROUP_NAME = "Outcasts"

    def _get_outcasts_task_group_name(self) -> str:
        return self.OUTCASTS_GROUP_NAME

    def _normalize_task_status(self, raw_task_status: object) -> str:
        task_status = str(raw_task_status or "").strip()

        if not task_status:
            return "On Demand"

        if task_status not in VALID_TASK_STATUSES:
            raise ValueError(
                f"Task status must be one of {sorted(VALID_TASK_STATUSES)}, "
                f"got '{task_status}'."
            )

        return task_status

    def _normalize_workflow_block(self, workflow: object = None) -> dict[str, str]:
        if workflow in (None, ""):
            return {
                "workflow_source": "",
            }

        if not isinstance(workflow, dict):
            raise ValueError("workflow must be a dict.")

        if "workflow_source" not in workflow:
            raise ValueError("workflow is missing workflow_source.")

        workflow_source_value = workflow.get("workflow_source", "")
        if not isinstance(workflow_source_value, str):
            raise ValueError("workflow.workflow_source must be a string.")

        return {
            "workflow_source": workflow_source_value,
        }

    def _normalize_triggers_block(self, triggers: object) -> str:
        if triggers is None:
            return ""

        if not isinstance(triggers, str):
            raise ValueError("Triggers must be a string.")

        return triggers

    def _normalize_memory_block(self, memory: object) -> list[dict[str, Any]]:
        if memory in (None, ""):
            return []

        if not isinstance(memory, list):
            raise ValueError("memory must be a list.")

        normalized_memory: list[dict[str, Any]] = []
        seen_names: set[str] = set()

        for index, item in enumerate(memory, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"memory entry {index} must be a dict.")

            memory_name = str(item.get("name", "")).strip()
            if not memory_name:
                raise ValueError(f"memory entry {index} is missing name.")

            if memory_name in seen_names:
                raise ValueError(f"memory contains duplicate name: {memory_name}")

            seen_names.add(memory_name)

            for required_field in ("has_file", "file_path", "content"):
                if required_field not in item:
                    raise ValueError(f"memory entry '{memory_name}' is missing {required_field}.")

            has_file = bool(item.get("has_file", False))

            file_path = item.get("file_path", "")
            if file_path is None:
                file_path = ""

            content = item.get("content", "")
            if content is None:
                content = ""

            normalized_memory.append(
                {
                    "name": memory_name,
                    "has_file": has_file,
                    "file_path": str(file_path or "").strip() if has_file else "",
                    "content": str(content),
                }
            )

        return normalized_memory

    def _load_full_package_snapshot(self, package_name: str) -> dict[str, Any]:
        clean_name = str(package_name or "").strip()
        if not clean_name:
            raise ValueError("Package name cannot be empty.")

        self._sync_package_directory_state()
        package_data = self.package_controller.load_into_fields(clean_name)

        if not isinstance(package_data, dict):
            raise ValueError(f"Package '{clean_name}' did not load as a dict.")

        package_copy = copy.deepcopy(package_data)

        if not str(package_copy.get("name", "")).strip():
            package_copy["name"] = clean_name

        return package_copy

    def _normalize_loaded_packages(self, packages: object) -> list[dict[str, Any]]:
        """
        Guard package snapshots already loaded into the UI.

        This does not normalize backend package schema. It only ensures the UI is
        carrying package dicts with names before task collection hands the payload
        to hydration/backend normalization/backend validation.
        """
        if packages in (None, ""):
            return []

        if not isinstance(packages, list):
            raise ValueError("packages must be a list.")

        normalized_packages: list[dict[str, Any]] = []

        for index, package_entry in enumerate(packages, start=1):
            if not isinstance(package_entry, dict):
                raise ValueError(f"Package entry {index} must be a dict.")

            package_name = str(package_entry.get("name", "")).strip()
            if not package_name:
                raise ValueError(f"Package entry {index} is missing name.")

            normalized_packages.append(copy.deepcopy(package_entry))

        return normalized_packages
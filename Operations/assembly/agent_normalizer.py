from __future__ import annotations

import copy
from typing import Any

from Operations.assembly.agent_schema import (
    VALID_TASK_STATUSES,
    build_group_filename,
    build_task_filename,
    clean_text,
    ensure_json_list,
)


class AgentNormalizer:
    """
    Strict canonical agent normalizer.

    This does not convert broad legacy schemas.
    This does not invent missing task/group names.
    This does not silently repair invalid statuses.
    This only normalizes the clean canonical shape.

    Boundary rule:
        Package files may provide package logic as a plain string.
        Agent task package instances are normalized to:
            {"logic": {"logic_source": "..."}}

    Rule:
        A task belongs to exactly one group: the group whose tasks[] list
        contains it. Task payloads do not carry task_groups.

    Memory rule:
        has_file is canonical and required for every memory entry.
    """

    def normalize_agent(self, raw_agent: object, fallback_name: str = "") -> dict[str, Any]:
        if not isinstance(raw_agent, dict):
            raise ValueError("Agent data must be a JSON object.")

        agent_name = clean_text(raw_agent.get("name", "")) or clean_text(fallback_name)
        if not agent_name:
            raise ValueError("Agent name is required.")

        raw_groups = ensure_json_list(raw_agent.get("groups", []), "agent.groups")
        if not raw_groups:
            raise ValueError("Agent must contain at least one group.")

        groups = [
            self.normalize_group(group_entry, group_index=index)
            for index, group_entry in enumerate(raw_groups, start=1)
        ]

        return {
            "name": agent_name,
            "default_returns": self.normalize_default_returns(
                raw_agent.get("default_returns", []),
                label="agent.default_returns",
            ),
            "groups": groups,
        }

    def normalize_group(self, raw_group: object, group_index: int) -> dict[str, Any]:
        if not isinstance(raw_group, dict):
            raise ValueError(f"Group entry {group_index} must be a JSON object.")

        group_name = clean_text(raw_group.get("name", ""))
        if not group_name:
            raise ValueError(f"Group entry {group_index} is missing name.")

        group_file = clean_text(raw_group.get("group_file", ""))
        if not group_file:
            group_file = build_group_filename(group_name)

        raw_tasks = ensure_json_list(raw_group.get("tasks", []), f"group '{group_name}'.tasks")

        return {
            "name": group_name,
            "group_file": group_file,
            "default_returns": self.normalize_default_returns(
                raw_group.get("default_returns", []),
                label=f"group '{group_name}'.default_returns",
            ),
            "tasks": [
                self.normalize_task(
                    raw_task=task_entry,
                    group_name=group_name,
                    task_index=index,
                )
                for index, task_entry in enumerate(raw_tasks, start=1)
            ],
        }

    def normalize_task(
        self,
        raw_task: object,
        group_name: str,
        task_index: int,
    ) -> dict[str, Any]:
        if not isinstance(raw_task, dict):
            raise ValueError(
                f"Task entry {task_index} in group '{group_name}' must be a JSON object."
            )

        task_name = clean_text(raw_task.get("name", ""))
        if not task_name:
            raise ValueError(f"Task entry {task_index} in group '{group_name}' is missing name.")

        task_file = clean_text(raw_task.get("task_file", ""))
        if not task_file:
            task_file = build_task_filename(task_name)

        task_status = clean_text(raw_task.get("task_status", ""))
        if task_status not in VALID_TASK_STATUSES:
            raise ValueError(
                f"Task '{task_name}' task_status must be one of {sorted(VALID_TASK_STATUSES)}, got '{task_status}'."
            )

        workflow = self.normalize_workflow(
            raw_task.get("workflow", {}),
            task_name=task_name,
        )

        return {
            "name": task_name,
            "task_file": task_file,
            "task_status": task_status,
            "workflow": workflow,
            "Triggers": self.normalize_triggers(raw_task.get("Triggers", ""), task_name=task_name),
            "default_returns": self.normalize_default_returns(
                raw_task.get("default_returns", []),
                label=f"task '{task_name}'.default_returns",
            ),
            "packages": self.normalize_packages(
                raw_task.get("packages", []),
                task_name=task_name,
            ),
            "prompts": self.normalize_prompts(
                raw_task.get("prompts", []),
                task_name=task_name,
            ),
            "memory": self.normalize_memory(
                raw_task.get("memory", []),
                task_name=task_name,
            ),
        }

    def normalize_workflow(self, raw_workflow: object, task_name: str) -> dict[str, str]:
        if not isinstance(raw_workflow, dict):
            raise ValueError(f"Task '{task_name}' workflow must be a JSON object.")

        if "workflow_source" not in raw_workflow:
            raise ValueError(f"Task '{task_name}' workflow is missing workflow_source.")

        workflow_source = raw_workflow.get("workflow_source", "")
        if not isinstance(workflow_source, str):
            raise ValueError(f"Task '{task_name}' workflow.workflow_source must be a string.")

        return {
            "workflow_source": workflow_source,
        }

    def normalize_triggers(self, raw_triggers: object, task_name: str) -> str:
        if raw_triggers is None:
            return ""

        if not isinstance(raw_triggers, str):
            raise ValueError(f"Task '{task_name}' Triggers must be a string.")

        return raw_triggers

    def normalize_default_returns(self, raw_default_returns: object, label: str) -> list[dict[str, Any]]:
        raw_items = ensure_json_list(raw_default_returns, label)

        normalized: list[dict[str, Any]] = []
        seen_names: set[str] = set()

        for index, item in enumerate(raw_items, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"{label} entry {index} must be a JSON object.")

            return_value_name = clean_text(item.get("return_value_name", ""))
            if not return_value_name:
                raise ValueError(f"{label} entry {index} is missing return_value_name.")

            if return_value_name in seen_names:
                raise ValueError(f"{label} contains duplicate return_value_name: {return_value_name}")

            seen_names.add(return_value_name)

            if "return_description" not in item:
                raise ValueError(f"{label} entry '{return_value_name}' is missing return_description.")

            if "return_value" not in item:
                raise ValueError(f"{label} entry '{return_value_name}' is missing return_value.")

            return_description = item.get("return_description", "")
            if return_description is None:
                return_description = ""

            return_value = item.get("return_value", "")
            if return_value is None:
                return_value = ""

            normalized.append(
                {
                    "return_value_name": return_value_name,
                    "return_description": str(return_description),
                    "return_value": str(return_value),
                }
            )

        return normalized

    def normalize_package_logic(
        self,
        raw_logic: object,
        task_name: str,
        package_name: str,
    ) -> dict[str, str]:
        if isinstance(raw_logic, str):
            logic_source = raw_logic
            return {
                "logic_source": logic_source,
            }

        if not isinstance(raw_logic, dict):
            raise ValueError(
                f"Task '{task_name}' package '{package_name}' logic must be a string "
                "or a JSON object."
            )

        if "logic_source" not in raw_logic:
            raise ValueError(
                f"Task '{task_name}' package '{package_name}' logic is missing logic_source."
            )

        logic_source = raw_logic.get("logic_source", "")
        if not isinstance(logic_source, str):
            raise ValueError(
                f"Task '{task_name}' package '{package_name}' logic.logic_source must be a string."
            )

        return {
            "logic_source": logic_source,
        }

    def normalize_packages(self, raw_packages: object, task_name: str) -> list[dict[str, Any]]:
        raw_items = ensure_json_list(raw_packages, f"task '{task_name}'.packages")

        normalized: list[dict[str, Any]] = []

        for expected_position, item in enumerate(raw_items, start=1):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Task '{task_name}' package entry {expected_position} must be a JSON object."
                )

            package_name = clean_text(item.get("name", ""))
            if not package_name:
                raise ValueError(f"Task '{task_name}' package entry {expected_position} is missing name.")

            raw_position = item.get("position", expected_position)
            if raw_position is not None and not isinstance(raw_position, int):
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' position must be an integer when provided."
                )

            package_status = clean_text(item.get("package_status", ""))
            if not package_status:
                raise ValueError(f"Task '{task_name}' package '{package_name}' is missing package_status.")

            logic = self.normalize_package_logic(
                raw_logic=item.get("logic", {}),
                task_name=task_name,
                package_name=package_name,
            )

            normalized.append(
                {
                    "position": expected_position,
                    "name": package_name,
                    "package_status": package_status,
                    "required_replacements": self.normalize_replacements(
                        item.get("required_replacements", []),
                        label=f"Task '{task_name}' package '{package_name}'.required_replacements",
                    ),
                    "optional_replacements": self.normalize_replacements(
                        item.get("optional_replacements", []),
                        label=f"Task '{task_name}' package '{package_name}'.optional_replacements",
                    ),
                    "arguments": self.normalize_arguments(
                        item.get("arguments", []),
                        task_name=task_name,
                        package_name=package_name,
                    ),
                    "returns": self.normalize_returns(
                        item.get("returns", []),
                        task_name=task_name,
                        package_name=package_name,
                    ),
                    "recognitions": self.normalize_recognitions(
                        item.get("recognitions", []),
                        task_name=task_name,
                        package_name=package_name,
                    ),
                    "logic": logic,
                }
            )

        return normalized

    def normalize_replacements(self, raw_replacements: object, label: str) -> list[dict[str, str]]:
        raw_items = ensure_json_list(raw_replacements, label)

        normalized: list[dict[str, str]] = []
        seen_labels: set[str] = set()

        for index, item in enumerate(raw_items, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"{label} entry {index} must be a JSON object.")

            to_be_replaced = clean_text(item.get("to_be_replaced", ""))
            if not to_be_replaced:
                raise ValueError(f"{label} entry {index} is missing to_be_replaced.")

            if to_be_replaced in seen_labels:
                raise ValueError(f"{label} contains duplicate to_be_replaced: {to_be_replaced}")

            seen_labels.add(to_be_replaced)

            value = item.get("value", "")
            if value is None:
                value = ""

            normalized.append(
                {
                    "to_be_replaced": to_be_replaced,
                    "value": str(value),
                }
            )

        return normalized

    def normalize_arguments(
        self,
        raw_arguments: object,
        task_name: str,
        package_name: str,
    ) -> list[dict[str, Any]]:
        raw_items = ensure_json_list(
            raw_arguments,
            f"Task '{task_name}' package '{package_name}'.arguments",
        )

        normalized: list[dict[str, Any]] = []
        seen_names: set[str] = set()

        for index, item in enumerate(raw_items, start=1):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' argument {index} must be a JSON object."
                )

            argument_question = clean_text(item.get("argument_question", ""))
            argument_value_name = clean_text(item.get("argument_value_name", ""))

            if not argument_question:
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' argument {index} is missing argument_question."
                )

            if not argument_value_name:
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' argument {index} is missing argument_value_name."
                )

            if argument_value_name in seen_names:
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' contains duplicate argument_value_name: {argument_value_name}"
                )

            seen_names.add(argument_value_name)

            for required_field in (
                "argument_fallback",
                "argument_hidden",
                "task_argument_mapping",
            ):
                if required_field not in item:
                    raise ValueError(
                        f"Task '{task_name}' package '{package_name}' argument '{argument_value_name}' is missing {required_field}."
                    )

            mapping = item.get("task_argument_mapping")
            if not isinstance(mapping, dict):
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' argument '{argument_value_name}' task_argument_mapping must be a JSON object."
                )

            argument_fallback = item.get("argument_fallback", "")
            if argument_fallback is None:
                argument_fallback = ""

            normalized.append(
                {
                    "argument_question": argument_question,
                    "argument_value_name": argument_value_name,
                    "argument_fallback": str(argument_fallback),
                    "argument_hidden": bool(item.get("argument_hidden", False)),
                    "task_argument_mapping": copy.deepcopy(mapping),
                }
            )

        return normalized

    def normalize_returns(
        self,
        raw_returns: object,
        task_name: str,
        package_name: str,
    ) -> list[dict[str, Any]]:
        raw_items = ensure_json_list(
            raw_returns,
            f"Task '{task_name}' package '{package_name}'.returns",
        )

        normalized: list[dict[str, Any]] = []
        seen_names: set[str] = set()

        for index, item in enumerate(raw_items, start=1):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' return {index} must be a JSON object."
                )

            return_value_name = clean_text(item.get("return_value_name", ""))
            if not return_value_name:
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' return {index} is missing return_value_name."
                )

            if return_value_name in seen_names:
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' contains duplicate return_value_name: {return_value_name}"
                )

            seen_names.add(return_value_name)

            for required_field in (
                "return_description",
                "visible",
                "friendship",
            ):
                if required_field not in item:
                    raise ValueError(
                        f"Task '{task_name}' package '{package_name}' return '{return_value_name}' is missing {required_field}."
                    )

            return_description = item.get("return_description", "")
            if return_description is None:
                return_description = ""

            normalized.append(
                {
                    "return_value_name": return_value_name,
                    "return_description": str(return_description),
                    "visible": bool(item.get("visible", True)),
                    "friendship": bool(item.get("friendship", False)),
                }
            )

        return normalized

    def normalize_recognitions(
        self,
        raw_recognitions: object,
        task_name: str,
        package_name: str,
    ) -> list[Any]:
        return copy.deepcopy(
            ensure_json_list(
                raw_recognitions,
                f"Task '{task_name}' package '{package_name}'.recognitions",
            )
        )

    def normalize_prompts(self, raw_prompts: object, task_name: str) -> list[dict[str, str]]:
        raw_items = ensure_json_list(raw_prompts, f"Task '{task_name}'.prompts")

        normalized: list[dict[str, str]] = []
        seen_names: set[str] = set()

        for index, item in enumerate(raw_items, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"Task '{task_name}' prompt entry {index} must be a JSON object.")

            prompt_name = clean_text(item.get("name", ""))
            if not prompt_name:
                raise ValueError(f"Task '{task_name}' prompt entry {index} is missing name.")

            if prompt_name in seen_names:
                raise ValueError(f"Task '{task_name}' contains duplicate prompt name: {prompt_name}")

            seen_names.add(prompt_name)

            if "prompt_source" not in item:
                raise ValueError(f"Task '{task_name}' prompt '{prompt_name}' is missing prompt_source.")

            prompt_source = item.get("prompt_source", "")
            if prompt_source is None:
                prompt_source = ""

            if not isinstance(prompt_source, str):
                raise ValueError(f"Task '{task_name}' prompt '{prompt_name}' prompt_source must be a string.")

            normalized.append(
                {
                    "name": prompt_name,
                    "prompt_source": prompt_source,
                }
            )

        return normalized

    def normalize_memory(self, raw_memory: object, task_name: str) -> list[dict[str, Any]]:
        raw_items = ensure_json_list(raw_memory, f"Task '{task_name}'.memory")

        normalized: list[dict[str, Any]] = []
        seen_names: set[str] = set()

        for index, item in enumerate(raw_items, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"Task '{task_name}' memory entry {index} must be a JSON object.")

            memory_name = clean_text(item.get("name", ""))
            if not memory_name:
                raise ValueError(f"Task '{task_name}' memory entry {index} is missing name.")

            if memory_name in seen_names:
                raise ValueError(f"Task '{task_name}' contains duplicate memory name: {memory_name}")

            seen_names.add(memory_name)

            for required_field in ("has_file", "file_path", "content"):
                if required_field not in item:
                    raise ValueError(
                        f"Task '{task_name}' memory '{memory_name}' is missing {required_field}."
                    )

            has_file = bool(item.get("has_file", False))

            file_path = item.get("file_path", "")
            if file_path is None:
                file_path = ""

            content = item.get("content", "")
            if content is None:
                content = ""

            normalized.append(
                {
                    "name": memory_name,
                    "has_file": has_file,
                    "file_path": clean_text(file_path) if has_file else "",
                    "content": str(content),
                }
            )

        return normalized
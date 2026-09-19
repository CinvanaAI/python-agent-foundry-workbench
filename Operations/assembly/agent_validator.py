from __future__ import annotations

from typing import Any

from Operations.assembly.agent_schema import (
    CANONICAL_AGENT_KEYS,
    CANONICAL_ARGUMENT_KEYS,
    CANONICAL_DEFAULT_RETURN_KEYS,
    CANONICAL_GROUP_KEYS,
    CANONICAL_MEMORY_KEYS,
    CANONICAL_PACKAGE_KEYS,
    CANONICAL_PROMPT_KEYS,
    CANONICAL_RETURN_KEYS,
    CANONICAL_TASK_KEYS,
    OUTCASTS_GROUP_NAME,
    VALID_TASK_STATUSES,
    build_group_filename,
    build_task_filename,
    clean_text,
    require_known_keys,
)


CANONICAL_WORKFLOW_KEYS = {
    "workflow_source",
}

CANONICAL_LOGIC_KEYS = {
    "logic_source",
}


class AgentValidator:
    def validate_agent(self, agent_data: object) -> dict[str, Any]:
        if not isinstance(agent_data, dict):
            raise ValueError("Agent data must be a JSON object.")

        require_known_keys(
            source=agent_data,
            allowed_keys=CANONICAL_AGENT_KEYS,
            label="agent",
        )

        agent_name = clean_text(agent_data.get("name", ""))
        if not agent_name:
            raise ValueError("Agent name is required.")

        self._validate_default_returns(
            agent_data.get("default_returns", []),
            "agent.default_returns",
        )

        groups = agent_data.get("groups", [])
        if not isinstance(groups, list):
            raise ValueError("agent.groups must be a list.")
        if not groups:
            raise ValueError("Agent must contain at least one group.")

        seen_group_names: set[str] = set()
        group_names: set[str] = set()

        for index, group in enumerate(groups, start=1):
            if not isinstance(group, dict):
                raise ValueError(f"Group entry {index} must be a JSON object.")

            require_known_keys(
                source=group,
                allowed_keys=CANONICAL_GROUP_KEYS,
                label=f"group entry {index}",
            )

            group_name = clean_text(group.get("name", ""))
            if not group_name:
                raise ValueError(f"Group entry {index} is missing name.")

            if group_name in seen_group_names:
                raise ValueError(f"Duplicate group name: {group_name}")

            seen_group_names.add(group_name)
            group_names.add(group_name)

        if OUTCASTS_GROUP_NAME not in group_names:
            raise ValueError(f"Required group '{OUTCASTS_GROUP_NAME}' is missing.")

        first_group_name = clean_text(groups[0].get("name", ""))
        if first_group_name != OUTCASTS_GROUP_NAME:
            raise ValueError(f"Required group '{OUTCASTS_GROUP_NAME}' must be first.")

        seen_task_files: dict[str, str] = {}
        seen_task_names: set[str] = set()

        for group_index, group in enumerate(groups, start=1):
            self._validate_group(
                group=group,
                group_index=group_index,
                seen_task_files=seen_task_files,
                seen_task_names=seen_task_names,
            )

        return agent_data

    def _validate_group(
        self,
        group: dict[str, Any],
        group_index: int,
        seen_task_files: dict[str, str],
        seen_task_names: set[str],
    ) -> None:
        require_known_keys(
            source=group,
            allowed_keys=CANONICAL_GROUP_KEYS,
            label=f"group entry {group_index}",
        )

        group_name = clean_text(group.get("name", ""))
        expected_group_file = build_group_filename(group_name)
        actual_group_file = clean_text(group.get("group_file", ""))

        if not actual_group_file:
            raise ValueError(f"Group '{group_name}' is missing group_file.")

        if actual_group_file != expected_group_file:
            raise ValueError(
                f"Group '{group_name}' group_file must be '{expected_group_file}', "
                f"got '{actual_group_file}'."
            )

        self._validate_default_returns(
            group.get("default_returns", []),
            f"group '{group_name}'.default_returns",
        )

        tasks = group.get("tasks", [])
        if not isinstance(tasks, list):
            raise ValueError(f"Group '{group_name}' tasks must be a list.")

        seen_task_names_in_group: set[str] = set()

        for task_index, task in enumerate(tasks, start=1):
            if not isinstance(task, dict):
                raise ValueError(
                    f"Group '{group_name}' task entry {task_index} must be a JSON object."
                )

            require_known_keys(
                source=task,
                allowed_keys=CANONICAL_TASK_KEYS,
                label=f"group '{group_name}' task entry {task_index}",
            )

            task_name = clean_text(task.get("name", ""))
            if not task_name:
                raise ValueError(
                    f"Group '{group_name}' task entry {task_index} is missing name."
                )

            if task_name in seen_task_names_in_group:
                raise ValueError(
                    f"Duplicate task name '{task_name}' inside group '{group_name}'."
                )

            if task_name in seen_task_names:
                raise ValueError(
                    f"Duplicate task name '{task_name}' across agent. "
                    "Task names must remain unique across the agent for now."
                )

            seen_task_names_in_group.add(task_name)
            seen_task_names.add(task_name)

            task_file = self._validate_task(
                task=task,
                group_name=group_name,
            )

            existing_owner = seen_task_files.get(task_file)
            if existing_owner is not None:
                raise ValueError(
                    f"Task file '{task_file}' is used by both "
                    f"'{existing_owner}' and '{task_name}'."
                )

            seen_task_files[task_file] = task_name

    def _validate_task(
        self,
        task: dict[str, Any],
        group_name: str,
    ) -> str:
        require_known_keys(
            source=task,
            allowed_keys=CANONICAL_TASK_KEYS,
            label=f"task in group '{group_name}'",
        )

        task_name = clean_text(task.get("name", ""))
        if not task_name:
            raise ValueError(f"Task in group '{group_name}' is missing name.")

        expected_task_file = build_task_filename(task_name)
        actual_task_file = clean_text(task.get("task_file", ""))

        if not actual_task_file:
            raise ValueError(f"Task '{task_name}' is missing task_file.")

        if actual_task_file != expected_task_file:
            raise ValueError(
                f"Task '{task_name}' task_file must be '{expected_task_file}', "
                f"got '{actual_task_file}'."
            )

        task_status = clean_text(task.get("task_status", ""))
        if task_status not in VALID_TASK_STATUSES:
            raise ValueError(
                f"Task '{task_name}' task_status must be one of "
                f"{sorted(VALID_TASK_STATUSES)}, got '{task_status}'."
            )

        self._validate_workflow(task.get("workflow", {}), task_name=task_name)

        triggers = task.get("Triggers", "")
        if not isinstance(triggers, str):
            raise ValueError(f"Task '{task_name}' Triggers must be a string.")

        self._validate_default_returns(
            task.get("default_returns", []),
            f"task '{task_name}'.default_returns",
        )
        self._validate_packages(task.get("packages", []), task_name=task_name)
        self._validate_prompts(task.get("prompts", []), task_name=task_name)
        self._validate_memory(task.get("memory", []), task_name=task_name)

        return actual_task_file

    def _validate_workflow(self, workflow: object, task_name: str) -> None:
        if not isinstance(workflow, dict):
            raise ValueError(f"Task '{task_name}' workflow must be a JSON object.")

        require_known_keys(
            source=workflow,
            allowed_keys=CANONICAL_WORKFLOW_KEYS,
            label=f"task '{task_name}'.workflow",
        )

        if "workflow_source" not in workflow:
            raise ValueError(f"Task '{task_name}' workflow is missing workflow_source.")

        if not isinstance(workflow.get("workflow_source", ""), str):
            raise ValueError(
                f"Task '{task_name}' workflow.workflow_source must be a string."
            )

    def _validate_default_returns(self, default_returns: object, label: str) -> None:
        if not isinstance(default_returns, list):
            raise ValueError(f"{label} must be a list.")

        seen_names: set[str] = set()

        for index, item in enumerate(default_returns, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"{label} entry {index} must be a JSON object.")

            require_known_keys(
                source=item,
                allowed_keys=CANONICAL_DEFAULT_RETURN_KEYS,
                label=f"{label} entry {index}",
            )

            return_value_name = clean_text(item.get("return_value_name", ""))
            if not return_value_name:
                raise ValueError(f"{label} entry {index} is missing return_value_name.")

            if return_value_name in seen_names:
                raise ValueError(
                    f"{label} contains duplicate return_value_name: {return_value_name}"
                )

            seen_names.add(return_value_name)

            for required_field in ("return_description", "return_value"):
                if required_field not in item:
                    raise ValueError(
                        f"{label} entry '{return_value_name}' is missing {required_field}."
                    )

    def _validate_packages(self, packages: object, task_name: str) -> None:
        if not isinstance(packages, list):
            raise ValueError(f"Task '{task_name}' packages must be a list.")

        expected_position = 1
        seen_package_names_at_position: set[tuple[int, str]] = set()

        for index, package in enumerate(packages, start=1):
            if not isinstance(package, dict):
                raise ValueError(
                    f"Task '{task_name}' package entry {index} must be a JSON object."
                )

            require_known_keys(
                source=package,
                allowed_keys=CANONICAL_PACKAGE_KEYS,
                label=f"task '{task_name}' package entry {index}",
            )

            package_name = clean_text(package.get("name", ""))
            if not package_name:
                raise ValueError(
                    f"Task '{task_name}' package entry {index} is missing name."
                )

            position = package.get("position")
            if not isinstance(position, int):
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' position must be an integer."
                )

            if position != expected_position:
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' position must be "
                    f"{expected_position}, got {position}."
                )

            expected_position += 1

            pair = (position, package_name)
            if pair in seen_package_names_at_position:
                raise ValueError(
                    f"Task '{task_name}' has duplicate package '{package_name}' "
                    f"at position {position}."
                )

            seen_package_names_at_position.add(pair)

            self._validate_package(package, task_name=task_name)

    def _validate_package(self, package: dict[str, Any], task_name: str) -> None:
        require_known_keys(
            source=package,
            allowed_keys=CANONICAL_PACKAGE_KEYS,
            label=f"task '{task_name}' package",
        )

        package_name = clean_text(package.get("name", ""))

        for field_name in (
            "package_status",
            "required_replacements",
            "optional_replacements",
            "arguments",
            "returns",
            "recognitions",
            "logic",
        ):
            if field_name not in package:
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' is missing {field_name}."
                )

        if not clean_text(package.get("package_status", "")):
            raise ValueError(
                f"Task '{task_name}' package '{package_name}' package_status is required."
            )

        if not isinstance(package.get("required_replacements"), list):
            raise ValueError(
                f"Task '{task_name}' package '{package_name}' "
                f"required_replacements must be a list."
            )

        if not isinstance(package.get("optional_replacements"), list):
            raise ValueError(
                f"Task '{task_name}' package '{package_name}' "
                f"optional_replacements must be a list."
            )

        if not isinstance(package.get("recognitions"), list):
            raise ValueError(
                f"Task '{task_name}' package '{package_name}' recognitions must be a list."
            )

        self._validate_arguments(
            package.get("arguments"),
            task_name=task_name,
            package_name=package_name,
        )

        self._validate_returns(
            package.get("returns"),
            task_name=task_name,
            package_name=package_name,
        )

        self._validate_logic(
            package.get("logic"),
            task_name=task_name,
            package_name=package_name,
        )

    def _validate_arguments(
        self,
        arguments: object,
        task_name: str,
        package_name: str,
    ) -> None:
        if not isinstance(arguments, list):
            raise ValueError(
                f"Task '{task_name}' package '{package_name}' arguments must be a list."
            )

        seen_argument_names: set[str] = set()

        for argument_index, argument in enumerate(arguments, start=1):
            if not isinstance(argument, dict):
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' argument "
                    f"{argument_index} must be a JSON object."
                )

            require_known_keys(
                source=argument,
                allowed_keys=CANONICAL_ARGUMENT_KEYS,
                label=(
                    f"task '{task_name}' package '{package_name}' "
                    f"argument {argument_index}"
                ),
            )

            argument_value_name = clean_text(argument.get("argument_value_name", ""))
            if not argument_value_name:
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' argument "
                    f"{argument_index} is missing argument_value_name."
                )

            if argument_value_name in seen_argument_names:
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' has duplicate "
                    f"argument_value_name: {argument_value_name}"
                )

            seen_argument_names.add(argument_value_name)

            for required_field in (
                "argument_question",
                "argument_fallback",
                "argument_hidden",
                "task_argument_mapping",
            ):
                if required_field not in argument:
                    raise ValueError(
                        f"Task '{task_name}' package '{package_name}' argument "
                        f"'{argument_value_name}' is missing {required_field}."
                    )

            if not isinstance(argument.get("argument_question", ""), str):
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' argument "
                    f"'{argument_value_name}' argument_question must be a string."
                )

            if not isinstance(argument.get("argument_fallback", ""), str):
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' argument "
                    f"'{argument_value_name}' argument_fallback must be a string."
                )

            if not isinstance(argument.get("argument_hidden"), bool):
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' argument "
                    f"'{argument_value_name}' argument_hidden must be a boolean."
                )

            mapping = argument.get("task_argument_mapping")
            if not isinstance(mapping, dict):
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' argument "
                    f"'{argument_value_name}' task_argument_mapping must be a JSON object."
                )

            source_type = clean_text(mapping.get("source_type", ""))
            if not source_type:
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' argument "
                    f"'{argument_value_name}' task_argument_mapping is missing source_type."
                )

    def _validate_returns(
        self,
        returns: object,
        task_name: str,
        package_name: str,
    ) -> None:
        if not isinstance(returns, list):
            raise ValueError(
                f"Task '{task_name}' package '{package_name}' returns must be a list."
            )

        seen_return_names: set[str] = set()

        for return_index, return_entry in enumerate(returns, start=1):
            if not isinstance(return_entry, dict):
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' return "
                    f"{return_index} must be a JSON object."
                )

            require_known_keys(
                source=return_entry,
                allowed_keys=CANONICAL_RETURN_KEYS,
                label=(
                    f"task '{task_name}' package '{package_name}' "
                    f"return {return_index}"
                ),
            )

            return_value_name = clean_text(return_entry.get("return_value_name", ""))
            if not return_value_name:
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' return "
                    f"{return_index} is missing return_value_name."
                )

            if return_value_name in seen_return_names:
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' has duplicate "
                    f"return_value_name: {return_value_name}"
                )

            seen_return_names.add(return_value_name)

            for required_field in (
                "return_description",
                "visible",
                "friendship",
            ):
                if required_field not in return_entry:
                    raise ValueError(
                        f"Task '{task_name}' package '{package_name}' return "
                        f"'{return_value_name}' is missing {required_field}."
                    )

            if not isinstance(return_entry.get("return_description", ""), str):
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' return "
                    f"'{return_value_name}' return_description must be a string."
                )

            if not isinstance(return_entry.get("visible"), bool):
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' return "
                    f"'{return_value_name}' visible must be a boolean."
                )

            if not isinstance(return_entry.get("friendship"), bool):
                raise ValueError(
                    f"Task '{task_name}' package '{package_name}' return "
                    f"'{return_value_name}' friendship must be a boolean."
                )

    def _validate_logic(
        self,
        logic: object,
        task_name: str,
        package_name: str,
    ) -> None:
        if not isinstance(logic, dict):
            raise ValueError(
                f"Task '{task_name}' package '{package_name}' logic must be a JSON object."
            )

        require_known_keys(
            source=logic,
            allowed_keys=CANONICAL_LOGIC_KEYS,
            label=f"task '{task_name}' package '{package_name}'.logic",
        )

        if "logic_source" not in logic:
            raise ValueError(
                f"Task '{task_name}' package '{package_name}' logic is missing logic_source."
            )

        if not isinstance(logic.get("logic_source", ""), str):
            raise ValueError(
                f"Task '{task_name}' package '{package_name}' logic.logic_source must be a string."
            )

    def _validate_prompts(self, prompts: object, task_name: str) -> None:
        if not isinstance(prompts, list):
            raise ValueError(f"Task '{task_name}' prompts must be a list.")

        seen_names: set[str] = set()

        for prompt_index, prompt in enumerate(prompts, start=1):
            if not isinstance(prompt, dict):
                raise ValueError(
                    f"Task '{task_name}' prompt entry {prompt_index} must be a JSON object."
                )

            require_known_keys(
                source=prompt,
                allowed_keys=CANONICAL_PROMPT_KEYS,
                label=f"task '{task_name}' prompt entry {prompt_index}",
            )

            prompt_name = clean_text(prompt.get("name", ""))
            if not prompt_name:
                raise ValueError(
                    f"Task '{task_name}' prompt entry {prompt_index} is missing name."
                )

            if prompt_name in seen_names:
                raise ValueError(f"Task '{task_name}' contains duplicate prompt name: {prompt_name}")

            seen_names.add(prompt_name)

            if "prompt_source" not in prompt:
                raise ValueError(f"Task '{task_name}' prompt '{prompt_name}' is missing prompt_source.")

            if not isinstance(prompt.get("prompt_source", ""), str):
                raise ValueError(f"Task '{task_name}' prompt '{prompt_name}' prompt_source must be a string.")

    def _validate_memory(self, memory: object, task_name: str) -> None:
        if not isinstance(memory, list):
            raise ValueError(f"Task '{task_name}' memory must be a list.")

        seen_names: set[str] = set()

        for memory_index, memory_entry in enumerate(memory, start=1):
            if not isinstance(memory_entry, dict):
                raise ValueError(
                    f"Task '{task_name}' memory entry {memory_index} must be a JSON object."
                )

            require_known_keys(
                source=memory_entry,
                allowed_keys=CANONICAL_MEMORY_KEYS,
                label=f"task '{task_name}' memory entry {memory_index}",
            )

            memory_name = clean_text(memory_entry.get("name", ""))
            if not memory_name:
                raise ValueError(
                    f"Task '{task_name}' memory entry {memory_index} is missing name."
                )

            if memory_name in seen_names:
                raise ValueError(f"Task '{task_name}' contains duplicate memory name: {memory_name}")

            seen_names.add(memory_name)

            for required_field in ("has_file", "file_path", "content"):
                if required_field not in memory_entry:
                    raise ValueError(
                        f"Task '{task_name}' memory '{memory_name}' is missing {required_field}."
                    )

            has_file = memory_entry.get("has_file")
            if not isinstance(has_file, bool):
                raise ValueError(f"Task '{task_name}' memory '{memory_name}' has_file must be a boolean.")

            file_path = memory_entry.get("file_path", "")
            if not isinstance(file_path, str):
                raise ValueError(f"Task '{task_name}' memory '{memory_name}' file_path must be a string.")

            content = memory_entry.get("content", "")
            if not isinstance(content, str):
                raise ValueError(f"Task '{task_name}' memory '{memory_name}' content must be a string.")

            if not has_file and file_path:
                raise ValueError(
                    f"Task '{task_name}' memory '{memory_name}' file_path must be blank when has_file is false."
                )
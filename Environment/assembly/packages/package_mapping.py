from __future__ import annotations

import copy


class PackageMappingInspectionMixin:
    """
    Package declaration inspection helpers.

    Owns:
        - inspecting saved package definitions through the UI package controller
        - extracting declared replacement labels
        - extracting declared package argument entries for UI binding/comparison

    Does not own:
        - canonical backend validation
        - task_argument_mapping state
        - rendering mapping rows
        - package hydration from disk
    """

    def _extract_replacement_labels(
        self,
        raw_replacements: object,
        field_name: str,
    ) -> list[str]:
        if raw_replacements in (None, ""):
            return []

        if not isinstance(raw_replacements, list):
            raise ValueError(f"{field_name} must be a list of replacement objects.")

        labels: list[str] = []
        seen_labels: set[str] = set()

        for index, item in enumerate(raw_replacements, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"{field_name} entry {index} must be a dict.")

            to_be_replaced = str(item.get("to_be_replaced", "")).strip()
            if not to_be_replaced:
                raise ValueError(
                    f"{field_name} entry {index} is missing to_be_replaced."
                )

            if to_be_replaced in seen_labels:
                raise ValueError(
                    f"{field_name} contains duplicate to_be_replaced: {to_be_replaced}"
                )

            seen_labels.add(to_be_replaced)
            labels.append(to_be_replaced)

        return labels

    def _extract_declared_argument_entries(
        self,
        raw_arguments: object,
        field_name: str,
    ) -> list[dict[str, object]]:
        if raw_arguments in (None, ""):
            return []

        if not isinstance(raw_arguments, list):
            raise ValueError(f"{field_name} must be a list of argument objects.")

        entries: list[dict[str, object]] = []
        seen_names: set[str] = set()

        for index, item in enumerate(raw_arguments, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"{field_name} entry {index} must be a dict.")

            argument_question = str(item.get("argument_question", "")).strip()
            argument_value_name = str(item.get("argument_value_name", "")).strip()

            if not argument_question:
                raise ValueError(
                    f"{field_name} entry {index} is missing argument_question."
                )

            if not argument_value_name:
                raise ValueError(
                    f"{field_name} entry {index} is missing argument_value_name."
                )

            if argument_value_name in seen_names:
                raise ValueError(
                    f"{field_name} contains duplicate argument_value_name: "
                    f"{argument_value_name}"
                )

            seen_names.add(argument_value_name)

            if "argument_fallback" not in item:
                raise ValueError(
                    f"{field_name} entry '{argument_value_name}' is missing "
                    "argument_fallback."
                )

            if "argument_hidden" not in item:
                raise ValueError(
                    f"{field_name} entry '{argument_value_name}' is missing "
                    "argument_hidden."
                )

            if "task_argument_mapping" not in item:
                raise ValueError(
                    f"{field_name} entry '{argument_value_name}' is missing "
                    "task_argument_mapping."
                )

            mapping = item.get("task_argument_mapping")
            if not isinstance(mapping, dict):
                raise ValueError(
                    f"{field_name} entry '{argument_value_name}' "
                    "task_argument_mapping must be a dict."
                )

            entries.append(
                {
                    "argument_question": argument_question,
                    "argument_value_name": argument_value_name,
                    "argument_fallback": (
                        ""
                        if item.get("argument_fallback", "") is None
                        else str(item.get("argument_fallback", ""))
                    ),
                    "argument_hidden": bool(item.get("argument_hidden", False)),
                    "task_argument_mapping": copy.deepcopy(mapping),
                }
            )

        return entries

    def _get_declared_inputs_for_package(self, package_name: str) -> dict[str, object]:
        clean_package_name = str(package_name or "").strip()
        if not clean_package_name:
            raise ValueError("Package name is required.")

        self._sync_package_directory_state()
        package_data = self.package_controller.load_into_fields(clean_package_name)

        if not isinstance(package_data, dict):
            raise ValueError(f"Package '{clean_package_name}' did not load as a dict.")

        required_replacements = self._extract_replacement_labels(
            package_data.get("required_replacements", []),
            "required_replacements",
        )

        optional_replacements = self._extract_replacement_labels(
            package_data.get("optional_replacements", []),
            "optional_replacements",
        )

        arguments = self._extract_declared_argument_entries(
            package_data.get("arguments", []),
            "arguments",
        )

        return {
            "required_replacements": required_replacements,
            "optional_replacements": optional_replacements,
            "arguments": arguments,
        }
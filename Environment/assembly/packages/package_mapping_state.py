from __future__ import annotations

import copy


class PackageMappingStateMixin:
    """
    Package argument mapping state helpers.

    task_argument_mapping is the machine-readable source of truth.
    argument_fallback is only a plain fallback/manual value.

    Supported mapping source types:
        - manual
        - external
        - previous_return
        - list
        - payload

    Payload is used for Friendship runtime_payload. It contains a nested list of
    normal argument rows under task_argument_mapping["arguments"].
    """

    def _normalize_list_item_mapping(self, item: object) -> dict:
        if not isinstance(item, dict):
            return {
                "package_name": "",
                "return_value_name": "",
            }

        return {
            "package_name": str(item.get("package_name", "")).strip(),
            "return_value_name": str(item.get("return_value_name", "")).strip(),
        }

    def _normalize_payload_argument_state(self, item: object) -> dict | None:
        if not isinstance(item, dict):
            return None

        argument_question = str(item.get("argument_question", "")).strip()
        argument_value_name = str(item.get("argument_value_name", "")).strip()
        argument_fallback = item.get("argument_fallback", "")
        argument_hidden = bool(item.get("argument_hidden", False))

        if not argument_value_name:
            argument_value_name = argument_question

        if not argument_question:
            argument_question = argument_value_name

        if not argument_value_name:
            return None

        if argument_fallback is None:
            argument_fallback = ""

        mapping = self._normalize_mapping_state(
            item.get("task_argument_mapping", {}),
            fallback_argument_name=argument_value_name,
            fallback_manual_value=argument_fallback,
        )

        return {
            "argument_question": argument_question,
            "argument_value_name": argument_value_name,
            "argument_fallback": "" if argument_fallback is None else str(argument_fallback),
            "argument_hidden": argument_hidden,
            "task_argument_mapping": mapping,
        }

    def _normalize_payload_arguments_list(self, raw_arguments: object) -> list[dict]:
        if raw_arguments in (None, ""):
            return []

        if not isinstance(raw_arguments, list):
            return []

        cleaned_arguments: list[dict] = []
        seen_names: set[str] = set()

        for item in raw_arguments:
            normalized_item = self._normalize_payload_argument_state(item)
            if normalized_item is None:
                continue

            argument_value_name = normalized_item["argument_value_name"]
            if argument_value_name in seen_names:
                continue

            seen_names.add(argument_value_name)
            cleaned_arguments.append(normalized_item)

        return cleaned_arguments

    def _normalize_mapping_state(
        self,
        mapping: object,
        fallback_argument_name: str = "",
        fallback_manual_value: object = "",
    ) -> dict:
        argument_name = str(fallback_argument_name or "").strip()

        if not isinstance(mapping, dict):
            return {
                "source_type": "manual",
                "manual_value": copy.deepcopy(fallback_manual_value),
            }

        source_type = str(mapping.get("source_type", "")).strip() or "manual"

        if source_type == "previous_return":
            return {
                "source_type": "previous_return",
                "package_name": str(mapping.get("package_name", "")).strip(),
                "return_value_name": str(mapping.get("return_value_name", "")).strip(),
            }

        if source_type == "list":
            raw_items = mapping.get("items", [])
            if not isinstance(raw_items, list):
                raw_items = []

            cleaned_items: list[dict] = []

            for item in raw_items:
                normalized_item = self._normalize_list_item_mapping(item)
                if normalized_item["package_name"] and normalized_item["return_value_name"]:
                    cleaned_items.append(normalized_item)

            return {
                "source_type": "list",
                "items": cleaned_items,
            }

        if source_type == "external":
            external_value_name = str(mapping.get("external_value_name", "")).strip()

            return {
                "source_type": "external",
                "external_value_name": external_value_name or argument_name,
            }

        if source_type == "payload":
            return {
                "source_type": "payload",
                "arguments": self._normalize_payload_arguments_list(
                    mapping.get("arguments", [])
                ),
            }

        return {
            "source_type": "manual",
            "manual_value": copy.deepcopy(mapping.get("manual_value", fallback_manual_value)),
        }

    def _normalize_payload_field_state(self, item: object) -> dict:
        normalized_item = self._normalize_payload_argument_state(item)

        if normalized_item is None:
            return {
                "argument_question": "",
                "argument_value_name": "",
                "argument_fallback": "",
                "argument_hidden": False,
                "task_argument_mapping": {
                    "source_type": "external",
                    "external_value_name": "",
                },
            }

        return normalized_item

    def _get_argument_mapping(self, argument_entry: dict) -> dict:
        if not isinstance(argument_entry, dict):
            return {
                "source_type": "manual",
                "manual_value": "",
            }

        argument_value_name = str(argument_entry.get("argument_value_name", "")).strip()

        return self._normalize_mapping_state(
            argument_entry.get("task_argument_mapping", {}),
            fallback_argument_name=argument_value_name,
            fallback_manual_value=argument_entry.get("argument_fallback", ""),
        )

    def _set_argument_mapping(self, argument_entry: dict, mapping: dict) -> None:
        if not isinstance(argument_entry, dict):
            raise ValueError("argument_entry must be a dict.")

        argument_value_name = str(argument_entry.get("argument_value_name", "")).strip()

        cleaned_mapping = self._normalize_mapping_state(
            mapping,
            fallback_argument_name=argument_value_name,
            fallback_manual_value=argument_entry.get("argument_fallback", ""),
        )

        argument_entry["task_argument_mapping"] = cleaned_mapping

        source_type = str(cleaned_mapping.get("source_type", "")).strip()

        if source_type == "manual":
            manual_value = cleaned_mapping.get("manual_value", "")
            argument_entry["argument_fallback"] = manual_value if isinstance(manual_value, str) else ""
            return

        argument_entry["argument_fallback"] = ""

    def _parse_previous_return_option(self, option_text: str) -> tuple[str, str]:
        text = str(option_text or "").strip()

        if not text.endswith(")") or " (" not in text:
            return "", ""

        left, right = text.rsplit(" (", 1)
        return_value_name = left.strip()
        package_name = right[:-1].strip()

        if not return_value_name or not package_name:
            return "", ""

        return return_value_name, package_name

    def _get_global_source_type_options(self) -> list[str]:
        return ["manual", "external", "list"]
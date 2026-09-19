from typing import Any, List, Optional

from collection_handoff import CollectionHandoff


class PackageEditorController:
    def __init__(self, handoff: Optional[CollectionHandoff] = None) -> None:
        self.handoff = handoff or CollectionHandoff()
        self.current_package_name: Optional[str] = None

    def create_new_package_data(self) -> dict:
        self.current_package_name = None
        return {
            "name": "",
            "package_status": "",
            "required_replacements": [],
            "optional_replacements": [],
            "arguments": [],
            "returns": [],
            "recognitions": [],
            "logic": "",
            "status": "New package form ready.",
        }

    def _normalize_replacement_items(self, raw_items: Any, field_name: str) -> list[dict[str, str]]:
        if raw_items in (None, ""):
            return []

        if not isinstance(raw_items, list):
            raise ValueError(f"{field_name} must be a list.")

        normalized_items: list[dict[str, str]] = []

        for index, item in enumerate(raw_items, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"{field_name} entry {index} must be a dict.")

            anchor = str(item.get("anchor", "")).strip()
            to_be_replaced = str(item.get("to_be_replaced", "")).strip()

            if not anchor:
                raise ValueError(f"{field_name} entry {index} is missing 'anchor'.")
            if not to_be_replaced:
                raise ValueError(f"{field_name} entry {index} is missing 'to_be_replaced'.")

            normalized_items.append(
                {
                    "anchor": anchor,
                    "to_be_replaced": to_be_replaced,
                }
            )

        return normalized_items

    def _normalize_argument_items(self, raw_items: Any, field_name: str) -> list[dict[str, object]]:
        if raw_items in (None, ""):
            return []

        if not isinstance(raw_items, list):
            raise ValueError(f"{field_name} must be a list.")

        normalized_items: list[dict[str, object]] = []

        for index, item in enumerate(raw_items, start=1):
            if isinstance(item, str):
                raw_value = item.strip()
                if not raw_value:
                    raise ValueError(f"{field_name} entry {index} is blank.")

                normalized_items.append(
                    {
                        "argument_question": raw_value,
                        "argument_value_name": raw_value,
                        "argument_fallback": "",
                        "argument_hidden": False,
                    }
                )
                continue

            if not isinstance(item, dict):
                raise ValueError(f"{field_name} entry {index} must be a dict.")

            argument_question = str(item.get("argument_question", "")).strip()
            argument_value_name = str(item.get("argument_value_name", "")).strip()

            if not argument_question and not argument_value_name:
                raise ValueError(
                    f"{field_name} entry {index} is missing both 'argument_question' and 'argument_value_name'."
                )

            if not argument_question:
                argument_question = argument_value_name
            if not argument_value_name:
                argument_value_name = argument_question

            argument_fallback = item.get("argument_fallback", "")
            argument_hidden = bool(item.get("argument_hidden", False))

            normalized_items.append(
                {
                    "argument_question": argument_question,
                    "argument_value_name": argument_value_name,
                    "argument_fallback": "" if argument_fallback is None else str(argument_fallback),
                    "argument_hidden": argument_hidden,
                }
            )

        return normalized_items

    def _normalize_return_items(self, raw_items: Any, field_name: str) -> list[dict[str, str]]:
        if raw_items in (None, ""):
            return []

        if not isinstance(raw_items, list):
            raise ValueError(f"{field_name} must be a list.")

        normalized_items: list[dict[str, str]] = []

        for index, item in enumerate(raw_items, start=1):
            if isinstance(item, str):
                return_value_name = item.strip()
                if not return_value_name:
                    raise ValueError(f"{field_name} entry {index} is missing 'return_value_name'.")

                normalized_items.append(
                    {
                        "return_value_name": return_value_name,
                        "return_description": "",
                    }
                )
                continue

            if not isinstance(item, dict):
                raise ValueError(f"{field_name} entry {index} must be a dict.")

            return_value_name = str(item.get("return_value_name", "")).strip()
            return_description = str(item.get("return_description", "")).strip()

            if not return_value_name:
                raise ValueError(f"{field_name} entry {index} is missing 'return_value_name'.")

            normalized_items.append(
                {
                    "return_value_name": return_value_name,
                    "return_description": return_description,
                }
            )

        return normalized_items

    def _normalize_recognition_items(self, raw_items: Any, field_name: str) -> list[dict[str, object]]:
        if raw_items in (None, ""):
            return []

        if not isinstance(raw_items, list):
            raise ValueError(f"{field_name} must be a list.")

        normalized_items: list[dict[str, object]] = []

        for index, item in enumerate(raw_items, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"{field_name} entry {index} must be a dict.")

            recognition_name = str(item.get("recognition_name", "")).strip()
            recognition_text = str(item.get("recognition_text", "")).strip()
            recognition_url = str(item.get("recognition_url", "")).strip()
            recognition_kind = str(item.get("recognition_kind", "")).strip()
            propagate_to_outputs = bool(item.get("propagate_to_outputs", False))

            if not recognition_name and not recognition_text and not recognition_url:
                raise ValueError(
                    f"{field_name} entry {index} is missing recognition content."
                )

            normalized_items.append(
                {
                    "recognition_name": recognition_name,
                    "recognition_text": recognition_text,
                    "recognition_url": recognition_url,
                    "recognition_kind": recognition_kind,
                    "propagate_to_outputs": propagate_to_outputs,
                }
            )

        return normalized_items

    def save_from_fields(
        self,
        package_name: str,
        package_status: str,
        required_replacements: list[dict[str, str]],
        optional_replacements: list[dict[str, str]],
        arguments: list[dict[str, object]],
        returns: list[dict[str, str]],
        recognitions: list[dict[str, object]],
        logic: str,
    ) -> dict:
        clean_name = self.handoff.sanitize_name("package_record", package_name)
        if not clean_name:
            raise ValueError("Package name is required.")

        normalized_package_status = str(package_status).strip()
        normalized_logic = logic.rstrip() + "\n" if str(logic).strip() else ""
        if not normalized_logic:
            raise ValueError("Logic is required.")

        normalized_required_replacements = self._normalize_replacement_items(
            required_replacements,
            "required_replacements",
        )
        normalized_optional_replacements = self._normalize_replacement_items(
            optional_replacements,
            "optional_replacements",
        )
        normalized_arguments = self._normalize_argument_items(
            arguments,
            "arguments",
        )
        normalized_returns = self._normalize_return_items(
            returns,
            "returns",
        )
        normalized_recognitions = self._normalize_recognition_items(
            recognitions,
            "recognitions",
        )

        record = {
            "name": clean_name,
            "package_status": normalized_package_status,
            "required_replacements": normalized_required_replacements,
            "optional_replacements": normalized_optional_replacements,
            "arguments": normalized_arguments,
            "returns": normalized_returns,
            "recognitions": normalized_recognitions,
            "logic": normalized_logic,
        }

        save_result = self.handoff.save_package_bundle(
            package_name=clean_name,
            logic=normalized_logic,
            record=record,
        )

        record_path = str(save_result.get("record_path", "")).strip()
        if not record_path:
            raise ValueError("Package save did not return a record_path.")

        self.current_package_name = clean_name

        review_trigger_enabled = bool(save_result.get("review_trigger_enabled", False))
        review_trigger_attempted = bool(save_result.get("review_trigger_attempted", False))
        review_trigger_succeeded = bool(save_result.get("review_trigger_succeeded", False))
        review_trigger_error = str(save_result.get("review_trigger_error", "") or "").strip()
        review_task_result = save_result.get("review_task_result")

        status_parts: list[str] = [f"Saved: {record_path}"]

        if review_trigger_enabled:
            if review_trigger_attempted and review_trigger_succeeded:
                status_parts.append("post-save review completed")
            elif review_trigger_attempted and not review_trigger_succeeded:
                status_parts.append("post-save review failed")
            else:
                status_parts.append("post-save review not attempted")

        return {
            "name": clean_name,
            "package_status": normalized_package_status,
            "required_replacements": normalized_required_replacements,
            "optional_replacements": normalized_optional_replacements,
            "arguments": normalized_arguments,
            "returns": normalized_returns,
            "recognitions": normalized_recognitions,
            "logic": normalized_logic,
            "status": " | ".join(status_parts),
            "saved_path": record_path,
            "record_path": record_path,
            "review_trigger_enabled": review_trigger_enabled,
            "review_trigger_attempted": review_trigger_attempted,
            "review_trigger_succeeded": review_trigger_succeeded,
            "review_trigger_error": review_trigger_error,
            "review_task_result": review_task_result,
        }

    def get_package_list(self) -> List[str]:
        return sorted(self.handoff.list_items("package_record"), key=str.lower)

    def load_into_fields(self, package_name: str) -> dict:
        clean_name = self.handoff.sanitize_name("package_record", package_name)
        if not clean_name:
            raise ValueError("Invalid package name.")

        bundle = self.handoff.load_package_bundle(clean_name)
        record = bundle.get("record")

        if not isinstance(record, dict):
            raise ValueError(f"Package record must be a JSON object: {clean_name}")

        logic = str(record.get("logic", "")).strip()
        if logic:
            logic = logic.rstrip() + "\n"

        package_status = str(record.get("package_status", "")).strip()

        required_replacements = self._normalize_replacement_items(
            record.get("required_replacements", []),
            "required_replacements",
        )
        optional_replacements = self._normalize_replacement_items(
            record.get("optional_replacements", []),
            "optional_replacements",
        )

        arguments = self._normalize_argument_items(
            record.get("arguments", []),
            "arguments",
        )

        returns = self._normalize_return_items(
            record.get("returns", []),
            "returns",
        )

        recognitions = self._normalize_recognition_items(
            record.get("recognitions", []),
            "recognitions",
        )

        self.current_package_name = clean_name

        return {
            "name": clean_name,
            "package_status": package_status,
            "required_replacements": required_replacements,
            "optional_replacements": optional_replacements,
            "arguments": arguments,
            "returns": returns,
            "recognitions": recognitions,
            "logic": logic,
            "status": f"Loaded package: {clean_name}",
        }

    def delete_from_name(self, package_name: str) -> dict:
        if not package_name or not package_name.strip():
            raise ValueError("Enter or load a package name first.")

        clean_name = self.handoff.sanitize_name("package_record", package_name)
        if not clean_name:
            raise ValueError("Invalid package name.")

        deleted_result = self.handoff.delete_package_bundle(clean_name)
        deleted_path = str(deleted_result.get("record_path", "")).strip()
        self.current_package_name = None

        return {
            "name": "",
            "package_status": "",
            "required_replacements": [],
            "optional_replacements": [],
            "arguments": [],
            "returns": [],
            "recognitions": [],
            "logic": "",
            "status": f"Deleted: {deleted_path}",
            "deleted_path": deleted_path,
        }

    def get_package_storage_directory(self) -> str:
        return self.handoff.get_storage_entry_directory("package_root")

    def set_package_storage_directory(self, directory: str) -> str:
        return self.handoff.set_storage_entry_directory("package_root", directory)

    def package_bundle_exists(self, package_name: str) -> bool:
        clean_name = self.handoff.sanitize_name("package_record", package_name)
        if not clean_name:
            return False
        return self.handoff.package_bundle_exists(clean_name)

    def get_base_dir(self) -> str:
        return self.handoff.get_base_dir()
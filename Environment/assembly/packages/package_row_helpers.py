import tkinter as tk


class PackageRowHelpersMixin:
    def _normalize_declared_argument_entry(self, argument_entry: object) -> dict:
        if not isinstance(argument_entry, dict):
            raw_value = str(argument_entry or "").strip()
            return {
                "argument_question": raw_value,
                "argument_value_name": raw_value,
                "argument_fallback": "",
                "argument_hidden": False,
                "task_argument_mapping": {
                    "source_type": "manual",
                    "manual_value": "",
                },
            }

        argument_question = str(argument_entry.get("argument_question", "")).strip()
        argument_value_name = str(argument_entry.get("argument_value_name", "")).strip()
        argument_fallback = argument_entry.get("argument_fallback", "")
        argument_hidden = bool(argument_entry.get("argument_hidden", False))

        if not argument_value_name:
            argument_value_name = argument_question

        if not argument_question:
            argument_question = argument_value_name

        if argument_fallback is None:
            argument_fallback = ""

        mapping = argument_entry.get("task_argument_mapping", {})
        if not isinstance(mapping, dict):
            mapping = {
                "source_type": "manual",
                "manual_value": argument_fallback,
            }

        return {
            "argument_question": argument_question,
            "argument_value_name": argument_value_name,
            "argument_fallback": argument_fallback,
            "argument_hidden": argument_hidden,
            "task_argument_mapping": self._normalize_mapping_state(
                mapping,
                fallback_argument_name=argument_value_name,
                fallback_manual_value=argument_fallback,
            ),
        }

    def _get_package_arguments_list(self, package_entry: dict) -> list[dict]:
        if not isinstance(package_entry, dict):
            raise ValueError("package_entry must be a dict.")

        raw_arguments = package_entry.get("arguments", [])

        if isinstance(raw_arguments, list):
            return raw_arguments

        package_entry["arguments"] = []
        return package_entry["arguments"]

    def _get_package_returns_list(self, package_entry: dict) -> list[dict]:
        if not isinstance(package_entry, dict):
            raise ValueError("package_entry must be a dict.")

        raw_returns = package_entry.get("returns", [])

        if isinstance(raw_returns, list):
            return raw_returns

        package_entry["returns"] = []
        return package_entry["returns"]

    def _build_replacement_value_row(
        self,
        tab_info: dict,
        package_entry: dict,
        section_name: str,
        replacement_label: str,
        row: int,
        indent: int = 40,
    ) -> int:
        if section_name not in {"required_replacements", "optional_replacements"}:
            raise ValueError(f"Unknown replacement section: {section_name}")

        raw_section = package_entry.get(section_name, [])
        if not isinstance(raw_section, list):
            raw_section = []
            package_entry[section_name] = raw_section

        matched_entry = None

        for entry in raw_section:
            if not isinstance(entry, dict):
                continue

            if str(entry.get("to_be_replaced", "")).strip() == replacement_label:
                matched_entry = entry
                break

        if matched_entry is None:
            matched_entry = {
                "to_be_replaced": replacement_label,
                "value": "",
            }
            raw_section.append(matched_entry)

        input_row = tk.Frame(tab_info["package_inner"])
        input_row.grid(row=row, column=0, sticky="ew", padx=(indent, 6), pady=2)
        input_row.grid_columnconfigure(0, weight=1)

        declared_label = tk.Label(
            input_row,
            text=replacement_label,
            anchor="w",
            justify="left",
        )
        declared_label.grid(row=0, column=0, sticky="ew", pady=(0, 2))

        value_entry = tk.Entry(
            input_row,
            font=("Consolas", 10),
        )
        value_entry.grid(row=1, column=0, sticky="ew")
        value_entry.insert(0, str(matched_entry.get("value", "")))

        def _capture_value(event=None, entry=value_entry, target_entry=matched_entry) -> None:
            target_entry["value"] = entry.get().strip()
            self._mark_tab_dirty(tab_info)

        value_entry.bind("<KeyRelease>", _capture_value)
        value_entry.bind("<FocusOut>", _capture_value)

        tab_info["package_row_widgets"].append(input_row)
        return row + 1

    def _add_declared_argument_row(
        self,
        tab_info: dict,
        package_entry: dict,
        declared_argument_entry: dict,
        row: int,
        package_index: int,
        available_previous_return_options: list[str],
        indent: int = 40,
    ) -> int:
        normalized_argument = self._normalize_declared_argument_entry(declared_argument_entry)

        argument_question = str(normalized_argument.get("argument_question", "")).strip()
        argument_value_name = str(normalized_argument.get("argument_value_name", "")).strip()
        argument_fallback = normalized_argument.get("argument_fallback", "")
        argument_hidden = bool(normalized_argument.get("argument_hidden", False))

        if not argument_value_name:
            argument_value_name = argument_question

        if not argument_question:
            argument_question = argument_value_name

        package_arguments = self._get_package_arguments_list(package_entry)

        target_argument_entry = None

        for argument_entry in package_arguments:
            if not isinstance(argument_entry, dict):
                continue

            current_value_name = str(argument_entry.get("argument_value_name", "")).strip()
            if not current_value_name:
                current_value_name = str(argument_entry.get("argument_question", "")).strip()

            if current_value_name == argument_value_name:
                target_argument_entry = argument_entry
                break

        if target_argument_entry is None:
            target_argument_entry = {
                "argument_question": argument_question,
                "argument_value_name": argument_value_name,
                "argument_fallback": argument_fallback,
                "argument_hidden": argument_hidden,
                "task_argument_mapping": self._normalize_mapping_state(
                    normalized_argument.get("task_argument_mapping", {}),
                    fallback_argument_name=argument_value_name,
                    fallback_manual_value=argument_fallback,
                ),
            }
            package_arguments.append(target_argument_entry)

        if not str(target_argument_entry.get("argument_question", "")).strip():
            target_argument_entry["argument_question"] = argument_question

        if not str(target_argument_entry.get("argument_value_name", "")).strip():
            target_argument_entry["argument_value_name"] = argument_value_name

        if "argument_hidden" not in target_argument_entry:
            target_argument_entry["argument_hidden"] = argument_hidden

        if "argument_fallback" not in target_argument_entry:
            target_argument_entry["argument_fallback"] = argument_fallback

        if not isinstance(target_argument_entry.get("task_argument_mapping"), dict):
            target_argument_entry["task_argument_mapping"] = self._normalize_mapping_state(
                {},
                fallback_argument_name=argument_value_name,
                fallback_manual_value=target_argument_entry.get("argument_fallback", ""),
            )

        package_name = str(package_entry.get("name", "")).strip()

        container = self._build_mapping_editor_row(
            parent=tab_info["package_inner"],
            target_entry=target_argument_entry,
            argument_question=argument_question,
            argument_value_name=argument_value_name,
            package_index=package_index,
            available_previous_return_options=available_previous_return_options,
            show_metadata=True,
            metadata_suffix="Package Hidden" if argument_hidden else "",
            tab_info=tab_info,
            package_name=package_name,
        )
        container.grid(row=row, column=0, sticky="ew", padx=(indent, 6), pady=4)

        tab_info["package_row_widgets"].append(container)
        return row + 1

    def _should_skip_declared_argument_row(
        self,
        package_name: str,
        declared_argument_entry: dict,
    ) -> bool:
        clean_package_name = str(package_name or "").strip().lower()
        argument_value_name = str(declared_argument_entry.get("argument_value_name", "")).strip()

        # Friendship and Append now render their source/payload/list arguments
        # through the normal mapping row system.
        if clean_package_name in {"friendship", "append_entry_to_user_approval_report"}:
            return False

        config = self._get_special_package_source_config(package_name)
        if config is None:
            return False

        agent_argument_name = str(config.get("agent_argument_name", "")).strip()
        task_argument_name = str(config.get("task_argument_name", "")).strip()

        if argument_value_name in {agent_argument_name, task_argument_name}:
            return False

        target_list_argument_name = str(config.get("target_list_argument_name", "")).strip()
        if target_list_argument_name and argument_value_name == target_list_argument_name:
            return True

        payload_argument_name = str(config.get("payload_argument_name", "")).strip()
        supports_payload_import = bool(config.get("supports_payload_import", False))

        if payload_argument_name and argument_value_name == payload_argument_name and supports_payload_import:
            return True

        return False

    def _sort_declared_arguments_for_display(
        self,
        package_name: str,
        normalized_declared_arguments: list[dict],
    ) -> list[dict]:
        config = self._get_special_package_source_config(package_name)
        if not config:
            return normalized_declared_arguments

        target_list_argument_name = str(config.get("target_list_argument_name", "")).strip()
        payload_argument_name = str(config.get("payload_argument_name", "")).strip()

        target_list_entries = []
        payload_entries = []
        other_entries = []

        for entry in normalized_declared_arguments:
            argument_value_name = str(entry.get("argument_value_name", "")).strip()

            if target_list_argument_name and argument_value_name == target_list_argument_name:
                target_list_entries.append(entry)
            elif payload_argument_name and argument_value_name == payload_argument_name:
                payload_entries.append(entry)
            else:
                other_entries.append(entry)

        return other_entries + target_list_entries + payload_entries
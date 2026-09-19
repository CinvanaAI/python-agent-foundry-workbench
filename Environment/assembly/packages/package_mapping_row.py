import tkinter as tk
from tkinter import ttk


class PackageMappingRowMixin:
    """
    Package argument mapping row UI.

    Owns:
        - rendering one argument mapping editor row
        - wiring row widgets to task_argument_mapping updates
        - rendering special agent/task dropdowns for selected package arguments
        - rendering Append target-list dropdown
        - rendering generated runtime_payload as nested argument mapping rows

    Does not own:
        - mapping state normalization
        - package declaration inspection
        - package tab layout
        - backend persistence
        - Friendship return borrowing
        - approval action save-time behavior
    """

    SPECIAL_AGENT_TASK_ARGUMENTS = {
        "friendship": {
            "agent": "friendship_agent_name",
            "task": "friendship_task_name",
        },
        "append_entry_to_user_approval_report": {
            "agent": "approval_agent_name",
            "task": "approval_task_name",
        },
    }

    GENERATED_PAYLOAD_PACKAGES = {
        "friendship",
        "append_entry_to_user_approval_report",
    }

    APPEND_PACKAGE_NAME = "append_entry_to_user_approval_report"
    APPEND_TARGET_LIST_ARGUMENT_NAME = "target_list_name"
    RUNTIME_PAYLOAD_ARGUMENT_NAME = "runtime_payload"

    def _request_package_editor_refresh(self, tab_info: dict | None) -> None:
        if not isinstance(tab_info, dict):
            return

        if hasattr(self, "_schedule_package_editor_refresh"):
            self._schedule_package_editor_refresh(tab_info)
            return

        self._refresh_package_editor(tab_info)

    def _get_special_argument_role(
        self,
        package_name: object,
        argument_value_name: object,
    ) -> str:
        clean_package_name = str(package_name or "").strip().lower()
        clean_argument_value_name = str(argument_value_name or "").strip()

        if not clean_package_name or not clean_argument_value_name:
            return ""

        config = self.SPECIAL_AGENT_TASK_ARGUMENTS.get(clean_package_name)
        if not config:
            return ""

        if clean_argument_value_name == config.get("agent"):
            return "agent"

        if clean_argument_value_name == config.get("task"):
            return "task"

        return ""

    def _is_generated_payload_argument(
        self,
        package_name: object,
        argument_value_name: object,
    ) -> bool:
        return (
            str(package_name or "").strip().lower() in self.GENERATED_PAYLOAD_PACKAGES
            and str(argument_value_name or "").strip() == self.RUNTIME_PAYLOAD_ARGUMENT_NAME
        )

    def _is_append_target_list_argument(
        self,
        package_name: object,
        argument_value_name: object,
    ) -> bool:
        return (
            str(package_name or "").strip().lower() == self.APPEND_PACKAGE_NAME
            and str(argument_value_name or "").strip() == self.APPEND_TARGET_LIST_ARGUMENT_NAME
        )

    def _get_manual_mapping_value(self, argument_entry: object) -> str:
        if not isinstance(argument_entry, dict):
            return ""

        mapping = self._get_argument_mapping(argument_entry)
        if not isinstance(mapping, dict):
            return ""

        if str(mapping.get("source_type", "")).strip() != "manual":
            return ""

        return str(mapping.get("manual_value", "")).strip()

    def _get_package_argument_manual_value(
        self,
        tab_info: dict | None,
        package_index: int,
        argument_value_name: str,
    ) -> str:
        if not isinstance(tab_info, dict):
            return ""

        packages = tab_info.get("packages", [])
        if not isinstance(packages, list):
            return ""

        if package_index < 0 or package_index >= len(packages):
            return ""

        package_entry = packages[package_index]
        if not isinstance(package_entry, dict):
            return ""

        arguments = package_entry.get("arguments", [])
        if not isinstance(arguments, list):
            return ""

        for argument_entry in arguments:
            if not isinstance(argument_entry, dict):
                continue

            current_value_name = str(argument_entry.get("argument_value_name", "")).strip()
            if current_value_name == argument_value_name:
                return self._get_manual_mapping_value(argument_entry)

        return ""

    def _get_agent_argument_name_for_package(self, package_name: object) -> str:
        clean_package_name = str(package_name or "").strip().lower()
        config = self.SPECIAL_AGENT_TASK_ARGUMENTS.get(clean_package_name, {})
        return str(config.get("agent", "")).strip()

    def _get_special_lookup_options(
        self,
        package_name: object,
        argument_value_name: object,
        tab_info: dict | None,
        package_index: int,
    ) -> list[str]:
        role = self._get_special_argument_role(package_name, argument_value_name)

        if role == "agent":
            options = self._get_agent_lookup_options()
            return [str(option).strip() for option in options if str(option).strip()]

        if role == "task":
            agent_argument_name = self._get_agent_argument_name_for_package(package_name)
            selected_agent = self._get_package_argument_manual_value(
                tab_info=tab_info,
                package_index=package_index,
                argument_value_name=agent_argument_name,
            )

            if not selected_agent:
                return []

            options = self._get_task_lookup_options(selected_agent)
            return [str(option).strip() for option in options if str(option).strip()]

        return []

    def _build_special_lookup_mapping_row(
        self,
        parent: tk.Widget,
        target_entry: dict,
        argument_question: str,
        argument_value_name: str,
        package_index: int,
        package_name: str,
        show_metadata: bool = True,
        metadata_suffix: str = "",
        tab_info: dict | None = None,
    ) -> tk.Widget:
        role = self._get_special_argument_role(package_name, argument_value_name)

        container = tk.Frame(parent, bd=1, relief="flat")
        container.grid_columnconfigure(0, weight=1)

        question_label = tk.Label(
            container,
            text=argument_question,
            anchor="w",
            justify="left",
            wraplength=760,
        )
        question_label.grid(row=0, column=0, sticky="ew")

        if show_metadata:
            metadata_text = f"Value Name: {argument_value_name} | Package Position: {package_index + 1}"
            if metadata_suffix:
                metadata_text = f"{metadata_text} | {metadata_suffix}"

            metadata_label = tk.Label(
                container,
                text=metadata_text,
                anchor="w",
                justify="left",
                fg="gray40",
            )
            metadata_label.grid(row=1, column=0, sticky="ew", pady=(2, 0))
            selector_row_index = 2
        else:
            selector_row_index = 1

        label_text = "Agent" if role == "agent" else "Task"

        selector_label = tk.Label(
            container,
            text=label_text,
            anchor="w",
        )
        selector_label.grid(row=selector_row_index, column=0, sticky="w", pady=(6, 2))

        option_values = self._get_special_lookup_options(
            package_name=package_name,
            argument_value_name=argument_value_name,
            tab_info=tab_info,
            package_index=package_index,
        )

        current_value = self._get_manual_mapping_value(target_entry)
        if current_value and current_value not in option_values:
            option_values = [current_value, *option_values]

        selected_value_var = tk.StringVar(value=current_value)

        selector_combo = ttk.Combobox(
            container,
            state="readonly",
            values=option_values,
            textvariable=selected_value_var,
            font=("Consolas", 10),
        )
        selector_combo.grid(row=selector_row_index + 1, column=0, sticky="ew")

        fallback_text = target_entry.get("argument_fallback", "")
        if not isinstance(fallback_text, str):
            fallback_text = ""
        fallback_text = fallback_text if fallback_text else "(blank)"

        fallback_label = tk.Label(
            container,
            text=f"Package Fallback: {fallback_text}",
            anchor="w",
            justify="left",
            fg="gray40",
        )
        fallback_label.grid(row=selector_row_index + 2, column=0, sticky="ew", pady=(2, 0))

        def _mark_mapping_dirty() -> None:
            if tab_info is not None:
                self._mark_tab_dirty(tab_info)

        def _save_special_lookup_mapping(mark_dirty: bool = True) -> None:
            selected_value = selected_value_var.get().strip()

            self._set_argument_mapping(
                target_entry,
                {
                    "source_type": "manual",
                    "manual_value": selected_value,
                },
            )

            if mark_dirty:
                _mark_mapping_dirty()

            if tab_info is not None:
                if (
                    str(package_name or "").strip().lower() in self.GENERATED_PAYLOAD_PACKAGES
                    and hasattr(self, "_sync_special_package_generated_fields")
                ):
                    packages = tab_info.get("packages", [])
                    if isinstance(packages, list) and 0 <= package_index < len(packages):
                        package_entry = packages[package_index]
                        if isinstance(package_entry, dict):
                            self._sync_special_package_generated_fields(
                                tab_info=tab_info,
                                package_entry=package_entry,
                                package_index=package_index,
                                mark_dirty_on_change=mark_dirty,
                            )

                if mark_dirty:
                    if role == "agent":
                        self._request_package_editor_refresh(tab_info)

                    elif role == "task" and str(package_name or "").strip().lower() in self.GENERATED_PAYLOAD_PACKAGES:
                        self._request_package_editor_refresh(tab_info)

        selector_combo.bind(
            "<<ComboboxSelected>>",
            lambda event=None: _save_special_lookup_mapping(mark_dirty=True),
        )

        _save_special_lookup_mapping(mark_dirty=False)

        return container

    def _build_append_target_list_mapping_row(
        self,
        parent: tk.Widget,
        target_entry: dict,
        argument_question: str,
        argument_value_name: str,
        package_index: int,
        package_name: str,
        show_metadata: bool = True,
        metadata_suffix: str = "",
        tab_info: dict | None = None,
    ) -> tk.Widget:
        container = tk.Frame(parent, bd=1, relief="flat")
        container.grid_columnconfigure(0, weight=1)

        question_label = tk.Label(
            container,
            text=argument_question,
            anchor="w",
            justify="left",
            wraplength=760,
        )
        question_label.grid(row=0, column=0, sticky="ew")

        if show_metadata:
            metadata_text = f"Value Name: {argument_value_name} | Package Position: {package_index + 1}"
            if metadata_suffix:
                metadata_text = f"{metadata_text} | {metadata_suffix}"

            metadata_label = tk.Label(
                container,
                text=metadata_text,
                anchor="w",
                justify="left",
                fg="gray40",
            )
            metadata_label.grid(row=1, column=0, sticky="ew", pady=(2, 0))
            selector_row_index = 2
        else:
            selector_row_index = 1

        selector_label = tk.Label(
            container,
            text="Target List",
            anchor="w",
        )
        selector_label.grid(row=selector_row_index, column=0, sticky="w", pady=(6, 2))

        option_values: list[str] = []
        if hasattr(self, "_get_user_approval_target_list_options"):
            try:
                option_values = self._get_user_approval_target_list_options()
            except Exception:
                option_values = []

        option_values = [str(option).strip() for option in option_values if str(option).strip()]

        current_value = self._get_manual_mapping_value(target_entry)
        if current_value and current_value not in option_values:
            option_values = [current_value, *option_values]

        selected_value_var = tk.StringVar(value=current_value)

        selector_combo = ttk.Combobox(
            container,
            state="readonly",
            values=option_values,
            textvariable=selected_value_var,
            font=("Consolas", 10),
        )
        selector_combo.grid(row=selector_row_index + 1, column=0, sticky="ew")

        fallback_text = target_entry.get("argument_fallback", "")
        if not isinstance(fallback_text, str):
            fallback_text = ""
        fallback_text = fallback_text if fallback_text else "(blank)"

        fallback_label = tk.Label(
            container,
            text=f"Package Fallback: {fallback_text}",
            anchor="w",
            justify="left",
            fg="gray40",
        )
        fallback_label.grid(row=selector_row_index + 2, column=0, sticky="ew", pady=(2, 0))

        def _save_target_list_mapping(mark_dirty: bool = True) -> None:
            selected_value = selected_value_var.get().strip()

            self._set_argument_mapping(
                target_entry,
                {
                    "source_type": "manual",
                    "manual_value": selected_value,
                },
            )

            if mark_dirty and tab_info is not None:
                self._mark_tab_dirty(tab_info)

        selector_combo.bind(
            "<<ComboboxSelected>>",
            lambda event=None: _save_target_list_mapping(mark_dirty=True),
        )

        _save_target_list_mapping(mark_dirty=False)

        return container

    def _get_payload_nested_arguments(self, target_entry: dict) -> list[dict]:
        if not isinstance(target_entry, dict):
            return []

        mapping = target_entry.get("task_argument_mapping", {})
        if not isinstance(mapping, dict):
            return []

        if str(mapping.get("source_type", "")).strip() != "payload":
            return []

        raw_arguments = mapping.get("arguments", [])
        if not isinstance(raw_arguments, list):
            return []

        return raw_arguments

    def _build_payload_mapping_editor_row(
        self,
        parent: tk.Widget,
        target_entry: dict,
        argument_question: str,
        argument_value_name: str,
        package_index: int,
        package_name: str,
        available_previous_return_options: list[str],
        show_metadata: bool = True,
        metadata_suffix: str = "",
        tab_info: dict | None = None,
    ) -> tk.Widget:
        container = tk.Frame(parent, bd=1, relief="flat")
        container.grid_columnconfigure(0, weight=1)

        question_label = tk.Label(
            container,
            text=argument_question,
            anchor="w",
            justify="left",
            wraplength=760,
        )
        question_label.grid(row=0, column=0, sticky="ew")

        if show_metadata:
            metadata_text = f"Value Name: {argument_value_name} | Package Position: {package_index + 1}"
            if metadata_suffix:
                metadata_text = f"{metadata_text} | {metadata_suffix}"

            metadata_label = tk.Label(
                container,
                text=metadata_text,
                anchor="w",
                justify="left",
                fg="gray40",
            )
            metadata_label.grid(row=1, column=0, sticky="ew", pady=(2, 0))
            title_row = 2
        else:
            title_row = 1

        payload_title = tk.Label(
            container,
            text="Payload Arguments",
            anchor="w",
            font=("Segoe UI", 9, "bold"),
            fg="gray25",
        )
        payload_title.grid(row=title_row, column=0, sticky="ew", pady=(6, 2))

        payload_helper = tk.Label(
            container,
            text=(
                "These nested payload fields are generated from external arguments "
                "on the selected target task. Each one uses the normal argument "
                "mapping controls."
            ),
            anchor="w",
            justify="left",
            wraplength=760,
            fg="gray40",
        )
        payload_helper.grid(row=title_row + 1, column=0, sticky="ew", pady=(0, 4))

        nested_arguments = self._get_payload_nested_arguments(target_entry)

        if not nested_arguments:
            empty_label = tk.Label(
                container,
                text="No external payload fields found for the selected target task.",
                anchor="w",
                fg="gray35",
            )
            empty_label.grid(row=title_row + 2, column=0, sticky="ew", pady=(2, 0))
            return container

        row = title_row + 2

        for nested_argument in nested_arguments:
            if not isinstance(nested_argument, dict):
                continue

            nested_question = str(nested_argument.get("argument_question", "")).strip()
            nested_value_name = str(nested_argument.get("argument_value_name", "")).strip()

            if not nested_value_name:
                nested_value_name = nested_question

            if not nested_question:
                nested_question = nested_value_name

            if not nested_value_name:
                continue

            nested_container = self._build_mapping_editor_row(
                parent=container,
                target_entry=nested_argument,
                argument_question=nested_question,
                argument_value_name=nested_value_name,
                package_index=package_index,
                available_previous_return_options=available_previous_return_options,
                show_metadata=True,
                metadata_suffix="Payload Field",
                tab_info=tab_info,
                package_name="",
            )
            nested_container.grid(row=row, column=0, sticky="ew", padx=(24, 0), pady=4)
            row += 1

        return container

    def _build_mapping_editor_row(
        self,
        parent: tk.Widget,
        target_entry: dict,
        argument_question: str,
        argument_value_name: str,
        package_index: int,
        available_previous_return_options: list[str],
        show_metadata: bool = True,
        metadata_suffix: str = "",
        tab_info: dict | None = None,
        package_name: str = "",
    ) -> tk.Widget:
        special_role = self._get_special_argument_role(package_name, argument_value_name)
        if special_role in {"agent", "task"}:
            return self._build_special_lookup_mapping_row(
                parent=parent,
                target_entry=target_entry,
                argument_question=argument_question,
                argument_value_name=argument_value_name,
                package_index=package_index,
                package_name=package_name,
                show_metadata=show_metadata,
                metadata_suffix=metadata_suffix,
                tab_info=tab_info,
            )

        if self._is_append_target_list_argument(package_name, argument_value_name):
            return self._build_append_target_list_mapping_row(
                parent=parent,
                target_entry=target_entry,
                argument_question=argument_question,
                argument_value_name=argument_value_name,
                package_index=package_index,
                package_name=package_name,
                show_metadata=show_metadata,
                metadata_suffix=metadata_suffix,
                tab_info=tab_info,
            )

        if self._is_generated_payload_argument(package_name, argument_value_name):
            return self._build_payload_mapping_editor_row(
                parent=parent,
                target_entry=target_entry,
                argument_question=argument_question,
                argument_value_name=argument_value_name,
                package_index=package_index,
                package_name=package_name,
                available_previous_return_options=available_previous_return_options,
                show_metadata=show_metadata,
                metadata_suffix=metadata_suffix,
                tab_info=tab_info,
            )

        mapping = self._get_argument_mapping(target_entry)

        container = tk.Frame(parent, bd=1, relief="flat")
        container.grid_columnconfigure(0, weight=1)

        question_label = tk.Label(
            container,
            text=argument_question,
            anchor="w",
            justify="left",
            wraplength=760,
        )
        question_label.grid(row=0, column=0, sticky="ew")

        if show_metadata:
            metadata_text = f"Value Name: {argument_value_name} | Package Position: {package_index + 1}"
            if metadata_suffix:
                metadata_text = f"{metadata_text} | {metadata_suffix}"

            metadata_label = tk.Label(
                container,
                text=metadata_text,
                anchor="w",
                justify="left",
                fg="gray40",
            )
            metadata_label.grid(row=1, column=0, sticky="ew", pady=(2, 0))
            source_row_index = 2
        else:
            source_row_index = 1

        source_label = tk.Label(
            container,
            text="Task Value Source",
            anchor="w",
        )
        source_label.grid(row=source_row_index, column=0, sticky="w", pady=(6, 2))

        option_values = [
            *self._get_global_source_type_options(),
            *available_previous_return_options,
        ]
        list_option_values = list(available_previous_return_options)

        initial_selector_value = "manual"
        initial_manual_text = ""
        initial_external_name = argument_value_name

        if mapping.get("source_type") == "previous_return":
            previous_return_label = self._format_previous_return_option(
                str(mapping.get("return_value_name", "")).strip(),
                str(mapping.get("package_name", "")).strip(),
            )

            if previous_return_label in available_previous_return_options:
                initial_selector_value = previous_return_label

        elif mapping.get("source_type") == "list":
            initial_selector_value = "list"

        elif mapping.get("source_type") == "external":
            initial_selector_value = "external"
            initial_external_name = (
                str(mapping.get("external_value_name", "")).strip()
                or argument_value_name
            )

        else:
            initial_selector_value = "manual"
            initial_manual_text = mapping.get("manual_value", "")
            if not isinstance(initial_manual_text, str):
                initial_manual_text = str(initial_manual_text)

        selected_source_var = tk.StringVar(value=initial_selector_value)
        manual_text_var = tk.StringVar(value=initial_manual_text)
        external_name_var = tk.StringVar(value=initial_external_name)

        source_combo = ttk.Combobox(
            container,
            state="readonly",
            values=option_values,
            textvariable=selected_source_var,
            font=("Consolas", 10),
        )
        source_combo.grid(row=source_row_index + 1, column=0, sticky="ew")

        manual_value_label = tk.Label(
            container,
            text="Manual Value",
            anchor="w",
        )
        manual_entry = tk.Entry(
            container,
            font=("Consolas", 10),
            textvariable=manual_text_var,
        )

        external_value_label = tk.Label(
            container,
            text="External Value Name",
            anchor="w",
        )
        external_entry = tk.Entry(
            container,
            font=("Consolas", 10),
            textvariable=external_name_var,
        )

        list_container = tk.Frame(container)
        list_container.grid_columnconfigure(0, weight=1)

        fallback_text = target_entry.get("argument_fallback", "")
        if not isinstance(fallback_text, str):
            fallback_text = ""
        fallback_text = fallback_text if fallback_text else "(blank)"

        fallback_label = tk.Label(
            container,
            text=f"Package Fallback: {fallback_text}",
            anchor="w",
            justify="left",
            fg="gray40",
        )

        def _mark_mapping_dirty() -> None:
            if tab_info is not None:
                self._mark_tab_dirty(tab_info)

        def _extract_list_items_from_ui() -> list[dict]:
            collected_items: list[dict] = []

            for item_var in getattr(list_container, "_item_vars", []):
                selected_option = item_var.get().strip()
                return_value_name, parsed_package_name = self._parse_previous_return_option(
                    selected_option
                )

                if parsed_package_name and return_value_name:
                    collected_items.append(
                        {
                            "package_name": parsed_package_name,
                            "return_value_name": return_value_name,
                        }
                    )

            return collected_items

        def _save_argument_mapping(mark_dirty: bool = True) -> None:
            selected_source = selected_source_var.get().strip()

            if selected_source == "manual":
                self._set_argument_mapping(
                    target_entry,
                    {
                        "source_type": "manual",
                        "manual_value": manual_text_var.get(),
                    },
                )
                if mark_dirty:
                    _mark_mapping_dirty()
                return

            if selected_source == "external":
                self._set_argument_mapping(
                    target_entry,
                    {
                        "source_type": "external",
                        "external_value_name": external_name_var.get().strip(),
                    },
                )
                if mark_dirty:
                    _mark_mapping_dirty()
                return

            if selected_source == "list":
                self._set_argument_mapping(
                    target_entry,
                    {
                        "source_type": "list",
                        "items": _extract_list_items_from_ui(),
                    },
                )
                if mark_dirty:
                    _mark_mapping_dirty()
                return

            return_value_name, parsed_package_name = self._parse_previous_return_option(selected_source)
            self._set_argument_mapping(
                target_entry,
                {
                    "source_type": "previous_return",
                    "package_name": parsed_package_name,
                    "return_value_name": return_value_name,
                },
            )
            if mark_dirty:
                _mark_mapping_dirty()

        def _build_list_item_row(item_mapping: dict | None = None) -> None:
            normalized_item = self._normalize_list_item_mapping(item_mapping or {})
            selected_label = ""

            if normalized_item["package_name"] and normalized_item["return_value_name"]:
                candidate_label = self._format_previous_return_option(
                    normalized_item["return_value_name"],
                    normalized_item["package_name"],
                )

                if candidate_label in list_option_values:
                    selected_label = candidate_label

            row_frame = tk.Frame(list_container)
            row_frame.pack(fill="x", pady=2)
            row_frame.grid_columnconfigure(0, weight=1)

            item_var = tk.StringVar(value=selected_label)
            combo = ttk.Combobox(
                row_frame,
                state="readonly",
                values=list_option_values,
                textvariable=item_var,
                font=("Consolas", 10),
            )
            combo.grid(row=0, column=0, sticky="ew")

            def _remove_item() -> None:
                item_vars = getattr(list_container, "_item_vars", [])
                if item_var in item_vars:
                    item_vars.remove(item_var)

                try:
                    row_frame.destroy()
                except tk.TclError:
                    pass

                _save_argument_mapping(mark_dirty=True)

            remove_button = tk.Button(
                row_frame,
                text="Remove",
                width=8,
                command=_remove_item,
            )
            remove_button.grid(row=0, column=1, padx=(8, 0))

            combo.bind(
                "<<ComboboxSelected>>",
                lambda event=None: _save_argument_mapping(mark_dirty=True),
            )

            item_vars = getattr(list_container, "_item_vars", None)
            if item_vars is None:
                item_vars = []
                list_container._item_vars = item_vars

            item_vars.append(item_var)

        def _render_list_rows() -> None:
            for child in list_container.winfo_children():
                try:
                    child.destroy()
                except tk.TclError:
                    pass

            list_container._item_vars = []

            list_intro = tk.Label(
                list_container,
                text="List Items",
                anchor="w",
            )
            list_intro.pack(anchor="w", pady=(0, 2))

            existing_items = []
            if mapping.get("source_type") == "list":
                raw_items = mapping.get("items", [])
                if isinstance(raw_items, list):
                    existing_items = [
                        self._normalize_list_item_mapping(item)
                        for item in raw_items
                    ]

            if not existing_items:
                existing_items = [{"package_name": "", "return_value_name": ""}]

            for existing_item in existing_items:
                _build_list_item_row(existing_item)

            add_button = tk.Button(
                list_container,
                text="Add List Item",
                width=14,
                command=lambda: (
                    _build_list_item_row({}),
                    _save_argument_mapping(mark_dirty=True),
                ),
            )
            add_button.pack(anchor="w", pady=(6, 0))

        def _render_visibility() -> None:
            selected_source = selected_source_var.get().strip()
            manual_row = source_row_index + 2
            external_row = source_row_index + 2
            list_row = source_row_index + 2

            manual_value_label.grid_remove()
            manual_entry.grid_remove()
            external_value_label.grid_remove()
            external_entry.grid_remove()
            list_container.grid_remove()
            fallback_label.grid_remove()

            if selected_source == "manual":
                manual_value_label.grid(row=manual_row, column=0, sticky="w", pady=(6, 2))
                manual_entry.grid(row=manual_row + 1, column=0, sticky="ew")
                fallback_label.grid(row=manual_row + 2, column=0, sticky="ew", pady=(2, 0))
                return

            if selected_source == "external":
                external_value_label.grid(row=external_row, column=0, sticky="w", pady=(6, 2))
                external_entry.grid(row=external_row + 1, column=0, sticky="ew")
                fallback_label.grid(row=external_row + 2, column=0, sticky="ew", pady=(2, 0))
                return

            if selected_source == "list":
                list_container.grid(row=list_row, column=0, sticky="ew", pady=(6, 0))
                fallback_label.grid(row=list_row + 1, column=0, sticky="ew", pady=(2, 0))
                return

            fallback_label.grid(row=source_row_index + 2, column=0, sticky="ew", pady=(6, 0))

        def _on_source_change(event=None) -> None:
            _render_visibility()
            _save_argument_mapping(mark_dirty=True)

        def _on_text_change(event=None) -> None:
            selected_source = selected_source_var.get().strip()
            if selected_source in {"manual", "external"}:
                _save_argument_mapping(mark_dirty=True)

        source_combo.bind("<<ComboboxSelected>>", _on_source_change)
        manual_entry.bind("<KeyRelease>", _on_text_change)
        manual_entry.bind("<FocusOut>", _on_text_change)
        external_entry.bind("<KeyRelease>", _on_text_change)
        external_entry.bind("<FocusOut>", _on_text_change)

        _render_list_rows()
        _render_visibility()
        _save_argument_mapping(mark_dirty=False)

        return container
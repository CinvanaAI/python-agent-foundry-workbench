import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


class PackageTabMixin:
    def _build_package_tab(self) -> None:
        parent_controls_frame = tk.Frame(self.package_tab)
        parent_controls_frame.pack(fill="x", pady=(0, 12))

        top_row = tk.Frame(parent_controls_frame)
        top_row.pack(fill="x")

        choose_frame = tk.Frame(top_row)
        choose_frame.pack(side="left", fill="y", padx=(0, 12))

        choose_label = tk.Label(choose_frame, text="Choose Package")
        choose_label.pack(anchor="w")

        tk.Button(
            choose_frame,
            text="Choose Package",
            width=16,
            command=self._handle_edit_package,
        ).pack(anchor="w", pady=(4, 0))

        name_frame = tk.Frame(top_row)
        name_frame.pack(side="left", fill="x", expand=True)

        name_label = tk.Label(name_frame, text="Name")
        name_label.pack(anchor="w")

        self.package_name_entry = tk.Entry(name_frame, font=("Segoe UI", 11))
        self.package_name_entry.pack(fill="x", pady=(4, 0), padx=(0, 12))

        status_frame = tk.Frame(top_row, width=220)
        status_frame.pack(side="left", fill="y")
        status_frame.pack_propagate(False)

        status_label = tk.Label(status_frame, text="Status")
        status_label.pack(anchor="w")

        self.package_status_var = tk.StringVar(value="Active")
        self.package_status_dropdown = ttk.Combobox(
            status_frame,
            textvariable=self.package_status_var,
            values=["Favorite", "Active", "Archived"],
            state="readonly",
            font=("Segoe UI", 10),
        )
        self.package_status_dropdown.pack(fill="x", pady=(4, 0))

        package_inner_notebook = ttk.Notebook(self.package_tab)
        package_inner_notebook.pack(fill="both", expand=True)

        package_main_tab = tk.Frame(package_inner_notebook, padx=10, pady=10)
        package_replacements_tab = tk.Frame(package_inner_notebook, padx=10, pady=10)
        package_recognitions_tab = tk.Frame(package_inner_notebook, padx=10, pady=10)

        package_inner_notebook.add(package_main_tab, text="Main")
        package_inner_notebook.add(package_replacements_tab, text="Additional")
        package_inner_notebook.add(package_recognitions_tab, text="Recognitions")

        logic_label = tk.Label(package_main_tab, text="Logic")
        logic_label.pack(anchor="w")

        text_frame = tk.Frame(package_main_tab)
        text_frame.pack(fill="both", expand=True, pady=(4, 12))

        self.package_logic_text = tk.Text(
            text_frame,
            wrap="none",
            undo=True,
            font=("Consolas", 11),
        )
        self.package_logic_text.pack(side="left", fill="both", expand=True)

        y_scroll = tk.Scrollbar(text_frame, orient="vertical", command=self.package_logic_text.yview)
        y_scroll.pack(side="right", fill="y")
        self.package_logic_text.configure(yscrollcommand=y_scroll.set)

        x_scroll_frame = tk.Frame(package_main_tab)
        x_scroll_frame.pack(fill="x", pady=(0, 12))

        x_scroll = tk.Scrollbar(x_scroll_frame, orient="horizontal", command=self.package_logic_text.xview)
        x_scroll.pack(fill="x")
        self.package_logic_text.configure(xscrollcommand=x_scroll.set)
        self.package_logic_text.bind(
            "<KeyRelease>",
            lambda event=None: self._refresh_all_anchor_validation_styles(),
        )
        self.package_logic_text.bind(
            "<FocusOut>",
            lambda event=None: self._refresh_all_anchor_validation_styles(),
        )

        replacements_controls_row = tk.Frame(package_replacements_tab)
        replacements_controls_row.pack(fill="x", pady=(0, 10))

        tk.Button(
            replacements_controls_row,
            text="Add Argument",
            width=18,
            command=self._handle_add_argument,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            replacements_controls_row,
            text="Add Required Replacement",
            width=22,
            command=self._handle_add_required_replacement,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            replacements_controls_row,
            text="Add Optional Replacement",
            width=22,
            command=self._handle_add_optional_replacement,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            replacements_controls_row,
            text="Add Return",
            width=18,
            command=self._handle_add_return,
        ).pack(side="left")

        replacements_canvas_frame = tk.Frame(package_replacements_tab)
        replacements_canvas_frame.pack(fill="both", expand=True)

        self.package_replacements_canvas = tk.Canvas(replacements_canvas_frame, highlightthickness=0)
        self.package_replacements_canvas.pack(side="left", fill="both", expand=True)

        replacements_scroll = tk.Scrollbar(
            replacements_canvas_frame,
            orient="vertical",
            command=self.package_replacements_canvas.yview,
        )
        replacements_scroll.pack(side="right", fill="y")
        self.package_replacements_canvas.configure(yscrollcommand=replacements_scroll.set)

        self.package_replacements_inner = tk.Frame(self.package_replacements_canvas)
        package_replacements_window = self.package_replacements_canvas.create_window(
            (0, 0),
            window=self.package_replacements_inner,
            anchor="nw",
        )

        def _sync_package_replacements_scrollregion(event=None) -> None:
            self.package_replacements_canvas.configure(scrollregion=self.package_replacements_canvas.bbox("all"))

        def _sync_package_replacements_inner_width(event) -> None:
            self.package_replacements_canvas.itemconfigure(package_replacements_window, width=event.width)

        self.package_replacements_inner.bind("<Configure>", _sync_package_replacements_scrollregion)
        self.package_replacements_canvas.bind("<Configure>", _sync_package_replacements_inner_width)

        recognitions_controls_row = tk.Frame(package_recognitions_tab)
        recognitions_controls_row.pack(fill="x", pady=(0, 10))

        tk.Button(
            recognitions_controls_row,
            text="Add Recognition",
            width=18,
            command=self._handle_add_recognition,
        ).pack(side="left")

        recognitions_canvas_frame = tk.Frame(package_recognitions_tab)
        recognitions_canvas_frame.pack(fill="both", expand=True)

        self.package_recognitions_canvas = tk.Canvas(recognitions_canvas_frame, highlightthickness=0)
        self.package_recognitions_canvas.pack(side="left", fill="both", expand=True)

        recognitions_scroll = tk.Scrollbar(
            recognitions_canvas_frame,
            orient="vertical",
            command=self.package_recognitions_canvas.yview,
        )
        recognitions_scroll.pack(side="right", fill="y")
        self.package_recognitions_canvas.configure(yscrollcommand=recognitions_scroll.set)

        self.package_recognitions_inner = tk.Frame(self.package_recognitions_canvas)
        package_recognitions_window = self.package_recognitions_canvas.create_window(
            (0, 0),
            window=self.package_recognitions_inner,
            anchor="nw",
        )

        def _sync_package_recognitions_scrollregion(event=None) -> None:
            self.package_recognitions_canvas.configure(scrollregion=self.package_recognitions_canvas.bbox("all"))

        def _sync_package_recognitions_inner_width(event) -> None:
            self.package_recognitions_canvas.itemconfigure(package_recognitions_window, width=event.width)

        self.package_recognitions_inner.bind("<Configure>", _sync_package_recognitions_scrollregion)
        self.package_recognitions_canvas.bind("<Configure>", _sync_package_recognitions_inner_width)

        button_frame = tk.Frame(self.package_tab)
        button_frame.pack(fill="x", pady=(12, 0))

        tk.Button(
            button_frame,
            text="Create New Package",
            width=18,
            command=self._handle_create_new_package,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            button_frame,
            text="Save Package",
            width=14,
            command=self._handle_save_package,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            button_frame,
            text="Delete Package",
            width=14,
            command=self._handle_delete_package,
        ).pack(side="left", padx=(0, 8))

        self.package_status_label = tk.Label(self.package_tab, text="", anchor="w", fg="gray25")
        self.package_status_label.pack(fill="x", pady=(12, 0))

        self._refresh_package_replacement_editor()
        self._refresh_package_recognition_editor()

    def _count_anchor_occurrences_in_package_logic(self, anchor: str) -> int:
        anchor_text = str(anchor).strip()
        if not anchor_text:
            return 0

        logic = self.package_logic_text.get("1.0", tk.END)
        return logic.count(anchor_text)

    def _apply_anchor_validation_style(self, anchor_widget: tk.Text) -> None:
        anchor_value = anchor_widget.get("1.0", tk.END).strip()
        occurrence_count = self._count_anchor_occurrences_in_package_logic(anchor_value)

        default_bg = anchor_widget.cget("bg")
        for item in self.package_required_replacement_rows + self.package_optional_replacement_rows:
            if item.get("_anchor_widget") is anchor_widget:
                default_bg = item.get("_anchor_default_bg", default_bg)
                break

        if occurrence_count > 1:
            anchor_widget.configure(bg="#ffcccc")
        else:
            anchor_widget.configure(bg=default_bg)

    def _refresh_all_anchor_validation_styles(self) -> None:
        for item in self.package_required_replacement_rows + self.package_optional_replacement_rows:
            anchor_widget = item.get("_anchor_widget")
            if anchor_widget is not None and anchor_widget.winfo_exists():
                self._apply_anchor_validation_style(anchor_widget)

    def _refresh_package_replacement_editor(self) -> None:
        for widget in self.package_replacements_inner.winfo_children():
            widget.destroy()

        row = 0

        if getattr(self, "package_argument_rows", []):
            arguments_label = tk.Label(
                self.package_replacements_inner,
                text="Arguments",
                anchor="w",
                font=("Segoe UI", 10, "bold"),
            )
            arguments_label.grid(row=row, column=0, sticky="ew", padx=4, pady=(4, 6))
            row += 1

            for index, item in enumerate(self.package_argument_rows):
                row = self._build_package_argument_item_row(
                    row=row,
                    item=item,
                    index=index,
                )

        if getattr(self, "package_return_rows", []):
            returns_label = tk.Label(
                self.package_replacements_inner,
                text="Returns",
                anchor="w",
                font=("Segoe UI", 10, "bold"),
            )
            returns_label.grid(row=row, column=0, sticky="ew", padx=4, pady=(10, 6))
            row += 1

            for index, item in enumerate(self.package_return_rows):
                row = self._build_package_return_item_row(
                    row=row,
                    item=item,
                    index=index,
                )

        if self.package_required_replacement_rows:
            required_label = tk.Label(
                self.package_replacements_inner,
                text="Required Replacements",
                anchor="w",
                font=("Segoe UI", 10, "bold"),
            )
            required_label.grid(row=row, column=0, sticky="ew", padx=4, pady=(10, 6))
            row += 1

            for index, item in enumerate(self.package_required_replacement_rows):
                row = self._build_package_replacement_item_row(
                    row=row,
                    item=item,
                    replacement_kind="required",
                    index=index,
                )

        if self.package_optional_replacement_rows:
            optional_label = tk.Label(
                self.package_replacements_inner,
                text="Optional Replacements",
                anchor="w",
                font=("Segoe UI", 10, "bold"),
            )
            optional_label.grid(row=row, column=0, sticky="ew", padx=4, pady=(10, 6))
            row += 1

            for index, item in enumerate(self.package_optional_replacement_rows):
                row = self._build_package_replacement_item_row(
                    row=row,
                    item=item,
                    replacement_kind="optional",
                    index=index,
                )

        if (
            not getattr(self, "package_argument_rows", [])
            and not getattr(self, "package_return_rows", [])
            and not self.package_required_replacement_rows
            and not self.package_optional_replacement_rows
        ):
            empty_label = tk.Label(
                self.package_replacements_inner,
                text="No additional items added.",
                anchor="w",
                fg="gray35",
            )
            empty_label.grid(row=0, column=0, sticky="w", padx=6, pady=6)

        self.package_replacements_inner.grid_columnconfigure(0, weight=1)
        self._refresh_all_anchor_validation_styles()

    def _refresh_package_recognition_editor(self) -> None:
        for widget in self.package_recognitions_inner.winfo_children():
            widget.destroy()

        row = 0

        if getattr(self, "package_recognition_rows", []):
            for index, item in enumerate(self.package_recognition_rows):
                row = self._build_package_recognition_item_row(
                    row=row,
                    item=item,
                    index=index,
                )
        else:
            empty_label = tk.Label(
                self.package_recognitions_inner,
                text="No recognitions added.",
                anchor="w",
                fg="gray35",
            )
            empty_label.grid(row=0, column=0, sticky="w", padx=6, pady=6)

        self.package_recognitions_inner.grid_columnconfigure(0, weight=1)

    def _build_package_argument_item_row(self, row: int, item: dict, index: int) -> int:
        container = tk.LabelFrame(self.package_replacements_inner, text=f"Argument {index + 1}", padx=10, pady=10)
        container.grid(row=row, column=0, sticky="ew", padx=4, pady=4)
        container.grid_columnconfigure(0, weight=1)

        hidden_var = tk.BooleanVar(value=bool(item.get("argument_hidden", False)))

        def _capture_hidden_state(*_, target=item, var=hidden_var) -> None:
            target["argument_hidden"] = bool(var.get())

        tk.Checkbutton(
            container,
            text="Hidden",
            variable=hidden_var,
            command=_capture_hidden_state,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        tk.Label(container, text="Question / Label:").grid(row=1, column=0, sticky="w", pady=(0, 4))
        question_entry = tk.Entry(container, font=("Consolas", 10))
        question_entry.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        question_entry.insert(0, item.get("argument_question", ""))

        tk.Label(container, text="Actual Value Name:").grid(row=3, column=0, sticky="w", pady=(0, 4))
        actual_value_name_entry = tk.Entry(container, font=("Consolas", 10))
        actual_value_name_entry.grid(row=4, column=0, sticky="ew", pady=(0, 6))
        actual_value_name_entry.insert(0, item.get("argument_value_name", ""))

        tk.Label(container, text="Fallback Value:").grid(row=5, column=0, sticky="w", pady=(0, 4))
        fallback_entry = tk.Entry(container, font=("Consolas", 10))
        fallback_entry.grid(row=6, column=0, sticky="ew")
        fallback_entry.insert(0, item.get("argument_fallback", ""))

        def _capture_argument_fields(event=None, target=item) -> None:
            target["argument_question"] = question_entry.get().strip()
            target["argument_value_name"] = actual_value_name_entry.get().strip()
            target["argument_fallback"] = fallback_entry.get()
            target["argument_hidden"] = bool(hidden_var.get())

        question_entry.bind("<KeyRelease>", _capture_argument_fields)
        question_entry.bind("<FocusOut>", _capture_argument_fields)

        actual_value_name_entry.bind("<KeyRelease>", _capture_argument_fields)
        actual_value_name_entry.bind("<FocusOut>", _capture_argument_fields)

        fallback_entry.bind("<KeyRelease>", _capture_argument_fields)
        fallback_entry.bind("<FocusOut>", _capture_argument_fields)

        button_row = tk.Frame(container)
        button_row.grid(row=7, column=0, sticky="e", pady=(8, 0))

        tk.Button(
            button_row,
            text="Remove",
            width=10,
            command=lambda item_index=index: self._remove_package_argument_item(item_index),
        ).pack(side="right")

        return row + 1

    def _build_package_return_item_row(self, row: int, item: dict, index: int) -> int:
        container = tk.LabelFrame(self.package_replacements_inner, text=f"Return {index + 1}", padx=10, pady=10)
        container.grid(row=row, column=0, sticky="ew", padx=4, pady=4)
        container.grid_columnconfigure(0, weight=1)

        tk.Label(container, text="Return Value Name:").grid(row=0, column=0, sticky="w", pady=(0, 4))
        name_entry = tk.Entry(container, font=("Consolas", 10))
        name_entry.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        name_entry.insert(0, item.get("return_value_name", ""))

        tk.Label(container, text="Description:").grid(row=2, column=0, sticky="w", pady=(0, 4))
        description_entry = tk.Entry(container, font=("Consolas", 10))
        description_entry.grid(row=3, column=0, sticky="ew")
        description_entry.insert(0, item.get("return_description", ""))

        def _capture_return_fields(event=None, target=item) -> None:
            target["return_value_name"] = name_entry.get().strip()
            target["return_description"] = description_entry.get().strip()

        name_entry.bind("<KeyRelease>", _capture_return_fields)
        name_entry.bind("<FocusOut>", _capture_return_fields)

        description_entry.bind("<KeyRelease>", _capture_return_fields)
        description_entry.bind("<FocusOut>", _capture_return_fields)

        button_row = tk.Frame(container)
        button_row.grid(row=4, column=0, sticky="e", pady=(8, 0))

        tk.Button(
            button_row,
            text="Remove",
            width=10,
            command=lambda item_index=index: self._remove_package_return_item(item_index),
        ).pack(side="right")

        return row + 1

    def _build_package_recognition_item_row(self, row: int, item: dict, index: int) -> int:
        container = tk.LabelFrame(self.package_recognitions_inner, text=f"Recognition {index + 1}", padx=10, pady=10)
        container.grid(row=row, column=0, sticky="ew", padx=4, pady=4)
        container.grid_columnconfigure(0, weight=1)

        propagate_var = tk.BooleanVar(value=bool(item.get("propagate_to_outputs", False)))

        def _capture_propagate_state(*_, target=item, var=propagate_var) -> None:
            target["propagate_to_outputs"] = bool(var.get())

        tk.Checkbutton(
            container,
            text="Propagate To Outputs",
            variable=propagate_var,
            command=_capture_propagate_state,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        tk.Label(container, text="Recognition Name:").grid(row=1, column=0, sticky="w", pady=(0, 4))
        name_entry = tk.Entry(container, font=("Consolas", 10))
        name_entry.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        name_entry.insert(0, item.get("recognition_name", ""))

        tk.Label(container, text="Recognition Kind:").grid(row=3, column=0, sticky="w", pady=(0, 4))
        kind_var = tk.StringVar(value=item.get("recognition_kind", ""))
        kind_dropdown = ttk.Combobox(
            container,
            textvariable=kind_var,
            values=["Creator", "Internal", "External", "License", "Contributor", "Other"],
            state="readonly",
            font=("Segoe UI", 10),
        )
        kind_dropdown.grid(row=4, column=0, sticky="ew", pady=(0, 6))

        tk.Label(container, text="Recognition Text:").grid(row=5, column=0, sticky="w", pady=(0, 4))
        text_entry = tk.Entry(container, font=("Consolas", 10))
        text_entry.grid(row=6, column=0, sticky="ew", pady=(0, 6))
        text_entry.insert(0, item.get("recognition_text", ""))

        tk.Label(container, text="Recognition URL:").grid(row=7, column=0, sticky="w", pady=(0, 4))
        url_entry = tk.Entry(container, font=("Consolas", 10))
        url_entry.grid(row=8, column=0, sticky="ew")
        url_entry.insert(0, item.get("recognition_url", ""))

        def _capture_recognition_fields(event=None, target=item) -> None:
            target["recognition_name"] = name_entry.get().strip()
            target["recognition_kind"] = kind_var.get().strip()
            target["recognition_text"] = text_entry.get().strip()
            target["recognition_url"] = url_entry.get().strip()
            target["propagate_to_outputs"] = bool(propagate_var.get())

        name_entry.bind("<KeyRelease>", _capture_recognition_fields)
        name_entry.bind("<FocusOut>", _capture_recognition_fields)

        kind_dropdown.bind("<<ComboboxSelected>>", _capture_recognition_fields)

        text_entry.bind("<KeyRelease>", _capture_recognition_fields)
        text_entry.bind("<FocusOut>", _capture_recognition_fields)

        url_entry.bind("<KeyRelease>", _capture_recognition_fields)
        url_entry.bind("<FocusOut>", _capture_recognition_fields)

        button_row = tk.Frame(container)
        button_row.grid(row=9, column=0, sticky="e", pady=(8, 0))

        tk.Button(
            button_row,
            text="Remove",
            width=10,
            command=lambda item_index=index: self._remove_package_recognition_item(item_index),
        ).pack(side="right")

        return row + 1

    def _build_package_replacement_item_row(self, row: int, item: dict, replacement_kind: str, index: int) -> int:
        container = tk.LabelFrame(self.package_replacements_inner, text=f"Replacement {index + 1}", padx=10, pady=10)
        container.grid(row=row, column=0, sticky="ew", padx=4, pady=4)
        container.grid_columnconfigure(1, weight=1)

        tk.Label(container, text="To Be Replaced:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 6))
        replace_entry = tk.Entry(container, font=("Consolas", 10))
        replace_entry.grid(row=0, column=1, sticky="ew", pady=(0, 6))
        replace_entry.insert(0, item.get("to_be_replaced", ""))

        def _capture_to_be_replaced(event=None, entry=replace_entry, target=item) -> None:
            target["to_be_replaced"] = entry.get().strip()

        replace_entry.bind("<KeyRelease>", _capture_to_be_replaced)
        replace_entry.bind("<FocusOut>", _capture_to_be_replaced)

        tk.Label(container, text="Anchor:").grid(row=1, column=0, sticky="nw", padx=(0, 8))
        anchor_text = tk.Text(container, height=3, wrap="word", font=("Consolas", 10))
        anchor_text.grid(row=1, column=1, sticky="ew")
        anchor_text.insert("1.0", item.get("anchor", "").strip())
        item["_anchor_widget"] = anchor_text
        item["_anchor_default_bg"] = anchor_text.cget("bg")

        def _capture_anchor(event=None, text_widget=anchor_text, target=item) -> None:
            target["anchor"] = text_widget.get("1.0", tk.END).strip()
            self._apply_anchor_validation_style(text_widget)

        anchor_text.bind("<KeyRelease>", _capture_anchor)
        anchor_text.bind("<FocusOut>", _capture_anchor)

        button_row = tk.Frame(container)
        button_row.grid(row=2, column=0, columnspan=2, sticky="e", pady=(8, 0))

        tk.Button(
            button_row,
            text="Remove",
            width=10,
            command=lambda kind=replacement_kind, item_index=index: self._remove_package_replacement_item(kind, item_index),
        ).pack(side="right")

        return row + 1

    def _remove_package_argument_item(self, index: int) -> None:
        if 0 <= index < len(self.package_argument_rows):
            self.package_argument_rows.pop(index)
            self._refresh_package_replacement_editor()

    def _remove_package_return_item(self, index: int) -> None:
        if 0 <= index < len(self.package_return_rows):
            self.package_return_rows.pop(index)
            self._refresh_package_replacement_editor()

    def _remove_package_recognition_item(self, index: int) -> None:
        if 0 <= index < len(self.package_recognition_rows):
            self.package_recognition_rows.pop(index)
            self._refresh_package_recognition_editor()

    def _remove_package_replacement_item(self, replacement_kind: str, index: int) -> None:
        if replacement_kind == "required":
            if 0 <= index < len(self.package_required_replacement_rows):
                self.package_required_replacement_rows.pop(index)
        elif replacement_kind == "optional":
            if 0 <= index < len(self.package_optional_replacement_rows):
                self.package_optional_replacement_rows.pop(index)

        self._refresh_package_replacement_editor()

    def _handle_add_argument(self) -> None:
        self.package_argument_rows.append(
            {
                "argument_question": "",
                "argument_value_name": "",
                "argument_fallback": "",
                "argument_hidden": False,
            }
        )
        self._refresh_package_replacement_editor()

    def _handle_add_return(self) -> None:
        self.package_return_rows.append(
            {
                "return_value_name": "",
                "return_description": "",
            }
        )
        self._refresh_package_replacement_editor()

    def _handle_add_recognition(self) -> None:
        self.package_recognition_rows.append(
            {
                "recognition_name": "",
                "recognition_text": "",
                "recognition_url": "",
                "recognition_kind": "Creator",
                "propagate_to_outputs": True,
            }
        )
        self._refresh_package_recognition_editor()

    def _handle_add_required_replacement(self) -> None:
        self.package_required_replacement_rows.append({"to_be_replaced": "", "anchor": ""})
        self._refresh_package_replacement_editor()

    def _handle_add_optional_replacement(self) -> None:
        self.package_optional_replacement_rows.append({"to_be_replaced": "", "anchor": ""})
        self._refresh_package_replacement_editor()

    def _set_package_status(self, message: str) -> None:
        self.package_status_label.configure(text=message)

    def _build_save_success_message(self, package_name: str, package_path: Path, package_data: dict) -> str:
        lines = [
            f"Saved package: {package_name}",
            f"Path: {package_path}",
        ]

        review_attempted = bool(package_data.get("review_trigger_attempted", False))
        review_succeeded = bool(package_data.get("review_trigger_succeeded", False))
        review_error = str(package_data.get("review_trigger_error", "") or "").strip()

        if review_attempted and review_succeeded:
            lines.append("Post-save argument review: completed")
        elif review_attempted and not review_succeeded:
            lines.append("Post-save argument review: attempted but failed")
            if review_error:
                lines.append(f"Review error: {review_error}")
        elif package_data.get("review_trigger_enabled", False):
            lines.append("Post-save argument review: enabled but not attempted")

        status_text = str(package_data.get("status", "") or "").strip()
        if status_text:
            lines.append(f"Status: {status_text}")

        return "\n".join(lines)

    def _collect_package_argument_rows(self) -> list[dict[str, object]]:
        collected: list[dict[str, object]] = []
        for item in self.package_argument_rows:
            argument_question = str(item.get("argument_question", "")).strip()
            argument_value_name = str(item.get("argument_value_name", "")).strip()
            argument_fallback = item.get("argument_fallback", "")
            argument_hidden = bool(item.get("argument_hidden", False))

            if argument_question or argument_value_name:
                collected.append(
                    {
                        "argument_question": argument_question,
                        "argument_value_name": argument_value_name,
                        "argument_fallback": "" if argument_fallback is None else str(argument_fallback),
                        "argument_hidden": argument_hidden,
                    }
                )
        return collected

    def _collect_package_return_rows(self) -> list[dict[str, str]]:
        collected: list[dict[str, str]] = []
        for item in self.package_return_rows:
            return_value_name = str(item.get("return_value_name", "")).strip()
            return_description = str(item.get("return_description", "")).strip()

            if return_value_name or return_description:
                collected.append(
                    {
                        "return_value_name": return_value_name,
                        "return_description": return_description,
                    }
                )
        return collected

    def _collect_package_recognition_rows(self) -> list[dict[str, object]]:
        collected: list[dict[str, object]] = []
        for item in self.package_recognition_rows:
            recognition_name = str(item.get("recognition_name", "")).strip()
            recognition_text = str(item.get("recognition_text", "")).strip()
            recognition_url = str(item.get("recognition_url", "")).strip()
            recognition_kind = str(item.get("recognition_kind", "")).strip()
            propagate_to_outputs = bool(item.get("propagate_to_outputs", False))

            if recognition_name or recognition_text or recognition_url:
                collected.append(
                    {
                        "recognition_name": recognition_name,
                        "recognition_text": recognition_text,
                        "recognition_url": recognition_url,
                        "recognition_kind": recognition_kind,
                        "propagate_to_outputs": propagate_to_outputs,
                    }
                )
        return collected

    def _collect_package_replacement_rows(self, rows: list[dict]) -> list[dict[str, str]]:
        collected: list[dict[str, str]] = []
        for item in rows:
            anchor = str(item.get("anchor", "")).strip()
            to_be_replaced = str(item.get("to_be_replaced", "")).strip()
            if anchor or to_be_replaced:
                collected.append(
                    {
                        "anchor": anchor,
                        "to_be_replaced": to_be_replaced,
                    }
                )
        return collected

    def _load_package_data_into_fields(self, package_data: dict) -> None:
        self.package_name_entry.delete(0, tk.END)
        self.package_name_entry.insert(0, package_data.get("name", ""))

        package_status = package_data.get("package_status", "") or "Active"
        self.package_status_var.set(package_status)

        self.package_logic_text.delete("1.0", tk.END)
        self.package_logic_text.insert("1.0", package_data.get("logic", ""))

        self.package_required_replacement_rows = [
            {
                "anchor": item.get("anchor", ""),
                "to_be_replaced": item.get("to_be_replaced", ""),
            }
            for item in package_data.get("required_replacements", [])
        ]

        self.package_optional_replacement_rows = [
            {
                "anchor": item.get("anchor", ""),
                "to_be_replaced": item.get("to_be_replaced", ""),
            }
            for item in package_data.get("optional_replacements", [])
        ]

        self.package_argument_rows = []
        for item in package_data.get("arguments", []):
            if isinstance(item, dict):
                self.package_argument_rows.append(
                    {
                        "argument_question": item.get("argument_question", ""),
                        "argument_value_name": item.get("argument_value_name", ""),
                        "argument_fallback": item.get("argument_fallback", ""),
                        "argument_hidden": bool(item.get("argument_hidden", False)),
                    }
                )
            else:
                raw_value = str(item).strip()
                self.package_argument_rows.append(
                    {
                        "argument_question": raw_value,
                        "argument_value_name": raw_value,
                        "argument_fallback": "",
                        "argument_hidden": False,
                    }
                )

        self.package_return_rows = []
        for item in package_data.get("returns", []):
            if isinstance(item, dict):
                self.package_return_rows.append(
                    {
                        "return_value_name": item.get("return_value_name", ""),
                        "return_description": item.get("return_description", ""),
                    }
                )
            else:
                self.package_return_rows.append(
                    {
                        "return_value_name": str(item).strip(),
                        "return_description": "",
                    }
                )

        self.package_recognition_rows = []
        for item in package_data.get("recognitions", []):
            if isinstance(item, dict):
                self.package_recognition_rows.append(
                    {
                        "recognition_name": item.get("recognition_name", ""),
                        "recognition_text": item.get("recognition_text", ""),
                        "recognition_url": item.get("recognition_url", ""),
                        "recognition_kind": item.get("recognition_kind", ""),
                        "propagate_to_outputs": bool(item.get("propagate_to_outputs", False)),
                    }
                )

        self._refresh_package_directory_path()
        self._refresh_package_replacement_editor()
        self._refresh_package_recognition_editor()

    def _handle_create_new_package(self) -> None:
        try:
            self._sync_package_directory_state()
            package_data = self.package_controller.create_new_package_data()
            self._load_package_data_into_fields(package_data)
            self._set_package_status(package_data.get("status", "New package form ready."))
        except Exception as e:
            messagebox.showerror("New Package Failed", str(e))

    def _handle_save_package(self) -> None:
        try:
            live_directory = self._get_live_package_directory()

            package_name = str(self.package_name_entry.get()).strip()
            if not package_name:
                raise ValueError("Package name is required.")

            expected_path = self._get_package_file_path(package_name, live_directory)

            package_data = self.package_controller.save_from_fields(
                package_name=package_name,
                package_status=self.package_status_var.get(),
                required_replacements=self._collect_package_replacement_rows(self.package_required_replacement_rows),
                optional_replacements=self._collect_package_replacement_rows(self.package_optional_replacement_rows),
                arguments=self._collect_package_argument_rows(),
                returns=self._collect_package_return_rows(),
                recognitions=self._collect_package_recognition_rows(),
                logic=self.package_logic_text.get("1.0", tk.END),
            )

            self._refresh_package_directory_path()

            if not expected_path.exists():
                raise FileNotFoundError(
                    f"Save completed but the package file was not found on disk:\n{expected_path}"
                )

            success_message = self._build_save_success_message(
                package_name=package_name,
                package_path=expected_path,
                package_data=package_data if isinstance(package_data, dict) else {},
            )

            self._set_package_status(success_message.replace("\n", " | "))
            messagebox.showinfo("Package Saved", success_message)
        except Exception as e:
            messagebox.showerror("Save Package Failed", str(e))

    def _handle_edit_package(self) -> None:
        try:
            package_names = self.package_controller.get_package_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        if not package_names:
            messagebox.showinfo("No Packages", "There are no saved packages yet.")
            return

        self._open_item_picker(
            title_text="Package",
            item_names=package_names,
            on_select=self._load_selected_package,
        )

    def _load_selected_package(self, package_name: str) -> None:
        try:
            package_data = self.package_controller.load_into_fields(package_name)
            self._load_package_data_into_fields(package_data)
            self._set_package_status(package_data.get("status", f"Loaded: {package_name}"))
        except Exception as e:
            messagebox.showerror("Load Package Failed", str(e))

    def _handle_delete_package(self) -> None:
        package_name = self.package_name_entry.get().strip()
        if not package_name:
            messagebox.showerror("Delete Package Failed", "Enter or load a package name first.")
            return

        confirmed = messagebox.askyesno(
            "Delete Package",
            f"Are you sure you want to delete '{package_name}'?",
        )
        if not confirmed:
            return

        try:
            result = self.package_controller.delete_from_name(package_name)
            self._handle_create_new_package()
            self._set_package_status(result.get("status", f"Deleted: {package_name}"))
        except Exception as e:
            messagebox.showerror("Delete Package Failed", str(e))
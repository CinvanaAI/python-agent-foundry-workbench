import tkinter as tk


class PackagesTabMixin:
    """
    Packages tab UI.

    Owns:
        - building the visible Packages tab surface
        - rendering the package editor/list
        - applying package selection styling
        - clearing package editor widgets
        - asking special packages to sync generated payload/returns before render
        - safely scheduling package editor refreshes after mapping dropdown changes

    Does not own:
        - package add/remove/move policy
        - package hydration before save
        - package mapping state
        - special package extraction internals
        - return list ownership
        - return exposure state
        - backend persistence
    """

    def _build_packages_tab(self, packages_tab: tk.Widget, tab_info: dict) -> None:
        packages_section = tk.LabelFrame(
            packages_tab,
            text="Packages",
            padx=10,
            pady=10,
        )
        packages_section.pack(fill="both", expand=True)

        package_editor_container = tk.Frame(packages_section)
        package_editor_container.pack(fill="both", expand=True)

        controls_row = tk.Frame(package_editor_container)
        controls_row.pack(fill="x", pady=(0, 10))

        tk.Button(
            controls_row,
            text="Add Package",
            width=14,
            command=lambda: self._handle_add_package(tab_info),
        ).pack(side="left")

        tk.Button(
            controls_row,
            text="Remove Package",
            width=14,
            command=lambda: self._handle_remove_package(tab_info),
        ).pack(side="left", padx=(8, 0))

        tk.Button(
            controls_row,
            text="Move Up",
            width=12,
            command=lambda: self._move_package_up(tab_info),
        ).pack(side="left", padx=(8, 0))

        tk.Button(
            controls_row,
            text="Move Down",
            width=12,
            command=lambda: self._move_package_down(tab_info),
        ).pack(side="left", padx=(8, 0))

        tk.Button(
            controls_row,
            text="Draft Package List",
            width=16,
            command=lambda: self._handle_draft_package_list(tab_info),
        ).pack(side="left", padx=(8, 0))

        package_list_frame = tk.Frame(package_editor_container)
        package_list_frame.pack(fill="both", expand=True)

        package_canvas = tk.Canvas(package_list_frame, highlightthickness=0)
        package_canvas.pack(side="left", fill="both", expand=True)

        package_scroll = tk.Scrollbar(
            package_list_frame,
            orient="vertical",
            command=package_canvas.yview,
        )
        package_scroll.pack(side="right", fill="y")
        package_canvas.configure(yscrollcommand=package_scroll.set)

        package_inner = tk.Frame(package_canvas)
        package_window = package_canvas.create_window(
            (0, 0),
            window=package_inner,
            anchor="nw",
        )

        def _sync_package_scrollregion(event=None) -> None:
            try:
                package_canvas.configure(scrollregion=package_canvas.bbox("all"))
            except tk.TclError:
                return

        def _sync_package_inner_width(event=None) -> None:
            try:
                if event is not None:
                    package_canvas.itemconfigure(package_window, width=event.width)
            except tk.TclError:
                return

        package_inner.bind("<Configure>", _sync_package_scrollregion)
        package_canvas.bind("<Configure>", _sync_package_inner_width)

        tab_info["package_canvas"] = package_canvas
        tab_info["package_inner"] = package_inner
        tab_info["package_refresh_after_id"] = None
        tab_info["package_refresh_in_progress"] = False
        tab_info["package_refresh_requested"] = False

    def _schedule_package_editor_refresh(self, tab_info: dict, delay_ms: int = 35) -> None:
        """
        Debounce package editor refreshes from real mapping-row user changes.

        Render-time setup must not call this. Mapping rows now only request a
        refresh when mark_dirty=True, so this helper should not be part of normal
        open/render loops.
        """
        if not isinstance(tab_info, dict):
            return

        root = getattr(self, "root", None)
        if root is None:
            self._refresh_package_editor(tab_info)
            return

        if tab_info.get("package_refresh_in_progress"):
            tab_info["package_refresh_requested"] = True
            return

        existing_after_id = tab_info.get("package_refresh_after_id")
        if existing_after_id:
            try:
                root.after_cancel(existing_after_id)
            except Exception:
                pass

            tab_info["package_refresh_after_id"] = None

        def _run_scheduled_refresh() -> None:
            tab_info["package_refresh_after_id"] = None

            try:
                self._refresh_package_editor(tab_info)
            except tk.TclError:
                return

        try:
            tab_info["package_refresh_after_id"] = root.after(delay_ms, _run_scheduled_refresh)
        except tk.TclError:
            return

    def _refresh_package_editor(self, tab_info: dict) -> None:
        if not isinstance(tab_info, dict):
            return

        if tab_info.get("package_refresh_in_progress"):
            tab_info["package_refresh_requested"] = True
            return

        tab_info["package_refresh_in_progress"] = True

        try:
            self._clear_package_editor(tab_info)

            packages = tab_info.get("packages", [])
            if not isinstance(packages, list):
                packages = []
                tab_info["packages"] = packages

            selected_index = tab_info.get("selected_package_index")
            if selected_index is not None and selected_index >= len(packages):
                selected_index = len(packages) - 1 if packages else None
                tab_info["selected_package_index"] = selected_index

            row = 0

            if not packages:
                empty_label = tk.Label(
                    tab_info["package_inner"],
                    text="No packages added.",
                    anchor="w",
                    fg="gray35",
                )
                empty_label.grid(row=0, column=0, sticky="w", padx=6, pady=6)
                tab_info["package_row_widgets"].append(empty_label)

                if hasattr(self, "_refresh_returns_panel"):
                    self._refresh_returns_panel(tab_info)

                return

            for package_index, package_entry in enumerate(packages):
                if not isinstance(package_entry, dict):
                    continue

                if hasattr(self, "_sync_special_package_generated_fields"):
                    self._sync_special_package_generated_fields(
                        tab_info=tab_info,
                        package_entry=package_entry,
                        package_index=package_index,
                        mark_dirty_on_change=False,
                    )

                package_name = (
                    str(package_entry.get("name", "")).strip()
                    or f"Package {package_index + 1}"
                )

                available_previous_return_options = self._get_available_previous_return_options(
                    packages,
                    package_index,
                    tab_info=tab_info,
                )

                package_label = tk.Label(
                    tab_info["package_inner"],
                    text=package_name,
                    anchor="w",
                    justify="left",
                    font=("Segoe UI", 10, "bold"),
                    padx=6,
                    pady=4,
                    relief="groove",
                    bd=1,
                    cursor="hand2",
                )
                package_label.grid(row=row, column=0, sticky="ew", padx=4, pady=(4, 2))
                package_label.bind(
                    "<Button-1>",
                    lambda event=None, info=tab_info, index=package_index: self._set_selected_package_index(
                        info,
                        index,
                    ),
                )

                tab_info["package_row_widgets"].append(package_label)
                tab_info["package_name_labels"].append(package_label)
                row += 1

                required_replacements = package_entry.get("required_replacements", [])
                optional_replacements = package_entry.get("optional_replacements", [])
                declared_argument_entries = package_entry.get("arguments", [])

                normalized_declared_arguments = [
                    self._normalize_declared_argument_entry(entry)
                    for entry in declared_argument_entries
                ]
                normalized_declared_arguments = self._sort_declared_arguments_for_display(
                    package_name,
                    normalized_declared_arguments,
                )
                normalized_declared_arguments = [
                    entry
                    for entry in normalized_declared_arguments
                    if not self._should_skip_declared_argument_row(package_name, entry)
                ]

                if (
                    not required_replacements
                    and not optional_replacements
                    and not normalized_declared_arguments
                ):
                    none_label = tk.Label(
                        tab_info["package_inner"],
                        text="(No declared inputs)",
                        anchor="w",
                        fg="gray35",
                    )
                    none_label.grid(row=row, column=0, sticky="ew", padx=(24, 6), pady=(0, 6))
                    tab_info["package_row_widgets"].append(none_label)
                    row += 1
                    continue

                if normalized_declared_arguments:
                    arguments_label = tk.Label(
                        tab_info["package_inner"],
                        text="Arguments",
                        anchor="w",
                        font=("Segoe UI", 9, "bold"),
                        fg="gray25",
                    )
                    arguments_label.grid(row=row, column=0, sticky="ew", padx=(24, 6), pady=(2, 2))
                    tab_info["package_row_widgets"].append(arguments_label)
                    row += 1

                    visible_entries = [
                        entry
                        for entry in normalized_declared_arguments
                        if not bool(entry.get("argument_hidden", False))
                    ]
                    hidden_entries = [
                        entry
                        for entry in normalized_declared_arguments
                        if bool(entry.get("argument_hidden", False))
                    ]

                    show_hidden = self._get_show_hidden_package_arguments(
                        tab_info,
                        package_index,
                    )

                    entries_to_render = list(visible_entries)
                    if show_hidden:
                        entries_to_render.extend(hidden_entries)

                    for declared_argument_entry in entries_to_render:
                        row = self._add_declared_argument_row(
                            tab_info=tab_info,
                            package_entry=package_entry,
                            declared_argument_entry=declared_argument_entry,
                            row=row,
                            package_index=package_index,
                            available_previous_return_options=available_previous_return_options,
                            indent=40,
                        )

                    if hidden_entries:
                        hidden_footer = tk.Frame(tab_info["package_inner"])
                        hidden_footer.grid(row=row, column=0, sticky="ew", padx=(40, 6), pady=(2, 6))

                        hidden_count = len(hidden_entries)
                        hidden_text = (
                            f"{hidden_count} package-hidden value"
                            if hidden_count == 1
                            else f"{hidden_count} package-hidden values"
                        )

                        hidden_label = tk.Label(
                            hidden_footer,
                            text=hidden_text,
                            anchor="w",
                            fg="gray45",
                        )
                        hidden_label.pack(side="left")

                        toggle_text = "Hide Hidden" if show_hidden else "View Hidden"
                        toggle_button = tk.Button(
                            hidden_footer,
                            text=toggle_text,
                            width=12,
                            command=lambda info=tab_info, index=package_index: self._toggle_show_hidden_package_arguments(
                                info,
                                index,
                            ),
                        )
                        toggle_button.pack(side="left", padx=(8, 0))

                        tab_info["package_row_widgets"].append(hidden_footer)
                        row += 1

                if required_replacements:
                    required_label = tk.Label(
                        tab_info["package_inner"],
                        text="Required",
                        anchor="w",
                        font=("Segoe UI", 9, "bold"),
                        fg="gray25",
                    )
                    required_label.grid(row=row, column=0, sticky="ew", padx=(24, 6), pady=(6, 2))
                    tab_info["package_row_widgets"].append(required_label)
                    row += 1

                    for replacement_entry in required_replacements:
                        if not isinstance(replacement_entry, dict):
                            continue

                        replacement_label = str(
                            replacement_entry.get("to_be_replaced", "")
                        ).strip()

                        if not replacement_label:
                            continue

                        row = self._build_replacement_value_row(
                            tab_info=tab_info,
                            package_entry=package_entry,
                            section_name="required_replacements",
                            replacement_label=replacement_label,
                            row=row,
                            indent=40,
                        )

                if optional_replacements:
                    optional_label = tk.Label(
                        tab_info["package_inner"],
                        text="Optional",
                        anchor="w",
                        font=("Segoe UI", 9, "bold"),
                        fg="gray25",
                    )
                    optional_label.grid(row=row, column=0, sticky="ew", padx=(24, 6), pady=(6, 2))
                    tab_info["package_row_widgets"].append(optional_label)
                    row += 1

                    for replacement_entry in optional_replacements:
                        if not isinstance(replacement_entry, dict):
                            continue

                        replacement_label = str(
                            replacement_entry.get("to_be_replaced", "")
                        ).strip()

                        if not replacement_label:
                            continue

                        row = self._build_replacement_value_row(
                            tab_info=tab_info,
                            package_entry=package_entry,
                            section_name="optional_replacements",
                            replacement_label=replacement_label,
                            row=row,
                            indent=40,
                        )

            self._apply_package_selection_styles(tab_info)

            if hasattr(self, "_refresh_returns_panel"):
                self._refresh_returns_panel(tab_info)

        finally:
            tab_info["package_refresh_in_progress"] = False

            if tab_info.get("package_refresh_requested"):
                tab_info["package_refresh_requested"] = False
                self._schedule_package_editor_refresh(tab_info)

    def _safe_destroy_widget(self, widget: tk.Widget) -> None:
        try:
            if widget.winfo_exists():
                widget.destroy()
        except tk.TclError:
            return
        except AttributeError:
            return

    def _clear_package_editor(self, tab_info: dict) -> None:
        inner = tab_info.get("package_inner")
        if inner is None:
            return

        try:
            children = list(inner.winfo_children())
        except tk.TclError:
            return

        for widget in children:
            self._safe_destroy_widget(widget)

        tab_info["package_row_widgets"] = []
        tab_info["package_name_labels"] = []

    def _apply_package_selection_styles(self, tab_info: dict) -> None:
        selected_index = tab_info.get("selected_package_index")
        labels = tab_info.get("package_name_labels", [])

        for index, label in enumerate(labels):
            try:
                if index == selected_index:
                    label.configure(bg="#d9edf7")
                else:
                    label.configure(bg=label.master.cget("bg"))
            except Exception:
                pass
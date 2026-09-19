import tkinter as tk
from tkinter import ttk


class ReturnsTabMixin:
    """
    Returns tab UI.

    Owns:
        - building the visible Returns tab surface
        - displaying task defaults from the live task UI state
        - displaying package returns from the live task UI state
        - editing package return visible/friendship flags directly on package return entries
        - providing the live task return universe helper for package/dropdown consumers

    Source of truth:
        Defaults:
            tab_info["default_return_rows"]

        Package returns:
            tab_info["packages"][package_index]["returns"][return_index]

    Does not own:
        - backend persistence
        - package hydration
        - package row rendering
        - mapping row rendering
    """

    DEFAULTS_SOURCE_NAME = "Defaults"

    def _build_returns_tab(
        self,
        inner_notebook: ttk.Notebook,
        tab_info: dict,
    ) -> None:
        returns_tab = tk.Frame(inner_notebook, padx=8, pady=8)
        inner_notebook.add(returns_tab, text="Returns")

        returns_header_label = tk.Label(
            returns_tab,
            text="Task Returns",
            anchor="w",
            justify="left",
            font=("Segoe UI", 10, "bold"),
        )
        returns_header_label.pack(fill="x", pady=(0, 2))

        returns_helper_label = tk.Label(
            returns_tab,
            text=(
                "Returns are read from this task's defaults and package return list. "
                "Package returns can be marked visible and/or friendship-enabled here."
            ),
            anchor="w",
            justify="left",
            wraplength=900,
            fg="gray40",
        )
        returns_helper_label.pack(fill="x", pady=(0, 8))

        returns_outer = tk.Frame(
            returns_tab,
            bd=1,
            relief="groove",
            padx=4,
            pady=4,
        )
        returns_outer.pack(fill="both", expand=True)

        returns_canvas = tk.Canvas(returns_outer, highlightthickness=0)
        returns_canvas.pack(side="left", fill="both", expand=True)

        returns_scroll = tk.Scrollbar(
            returns_outer,
            orient="vertical",
            command=returns_canvas.yview,
        )
        returns_scroll.pack(side="right", fill="y")
        returns_canvas.configure(yscrollcommand=returns_scroll.set)

        returns_inner = tk.Frame(returns_canvas)
        returns_window = returns_canvas.create_window(
            (0, 0),
            window=returns_inner,
            anchor="nw",
        )

        def _sync_returns_scrollregion(event=None) -> None:
            returns_canvas.configure(scrollregion=returns_canvas.bbox("all"))

        def _sync_returns_inner_width(event) -> None:
            returns_canvas.itemconfigure(returns_window, width=event.width)

        returns_inner.bind("<Configure>", _sync_returns_scrollregion)
        returns_canvas.bind("<Configure>", _sync_returns_inner_width)

        tab_info["returns_tab"] = returns_tab
        tab_info["returns_canvas"] = returns_canvas
        tab_info["returns_inner"] = returns_inner

        self._refresh_returns_panel(tab_info)

    def _get_live_packages_for_returns(self, tab_info: dict | None) -> list:
        if not isinstance(tab_info, dict):
            return []

        packages = tab_info.get("packages", [])

        if packages in (None, ""):
            packages = []
            tab_info["packages"] = packages

        if not isinstance(packages, list):
            return []

        return packages

    def _iter_live_default_return_entries(self, tab_info: dict | None) -> list[dict]:
        if not isinstance(tab_info, dict):
            return []

        defaults = tab_info.get("default_return_rows", [])

        if defaults in (None, ""):
            defaults = []
            tab_info["default_return_rows"] = defaults

        if not isinstance(defaults, list):
            return []

        default_entries: list[dict] = []

        for default_entry in defaults:
            if not isinstance(default_entry, dict):
                continue

            return_value_name = str(default_entry.get("return_value_name", "")).strip()
            if not return_value_name:
                continue

            default_entries.append(default_entry)

        return default_entries

    def _get_task_return_universe(
        self,
        tab_info: dict | None,
        include_defaults: bool = True,
        include_package_returns: bool = True,
        only_visible_package_returns: bool = False,
        only_friendship_returns: bool = False,
        before_package_index: int | None = None,
    ) -> list[dict]:
        """
        Return the live task return universe from the current UI task state.

        This reads dirty/in-memory UI state, not the saved agent file.

        Defaults are always:
            visible=True
            friendship=True

        Package returns use their current in-memory flags:
            visible=return_entry["visible"] defaulting to True
            friendship=return_entry["friendship"] defaulting to False
        """
        if not isinstance(tab_info, dict):
            return []

        return_items: list[dict] = []
        seen_keys: set[tuple[str, str, str, int | None]] = set()

        if include_defaults:
            for default_entry in self._iter_live_default_return_entries(tab_info):
                return_value_name = str(default_entry.get("return_value_name", "")).strip()
                if not return_value_name:
                    continue

                item = {
                    "source_type": "default_return",
                    "source_name": self.DEFAULTS_SOURCE_NAME,
                    "package_index": None,
                    "package_name": self.DEFAULTS_SOURCE_NAME,
                    "return_value_name": return_value_name,
                    "visible": True,
                    "friendship": True,
                }

                if only_friendship_returns and not item["friendship"]:
                    continue

                key = (
                    item["source_type"],
                    item["package_name"],
                    item["return_value_name"],
                    item["package_index"],
                )
                if key in seen_keys:
                    continue

                seen_keys.add(key)
                return_items.append(item)

        if include_package_returns:
            packages = self._get_live_packages_for_returns(tab_info)

            for package_index, package_entry in enumerate(packages):
                if before_package_index is not None and package_index >= before_package_index:
                    continue

                if not isinstance(package_entry, dict):
                    continue

                package_name = (
                    str(package_entry.get("name", "")).strip()
                    or f"Package {package_index + 1}"
                )

                returns = package_entry.get("returns", [])
                if returns in (None, ""):
                    returns = []
                    package_entry["returns"] = returns

                if not isinstance(returns, list):
                    continue

                for return_entry in returns:
                    if not isinstance(return_entry, dict):
                        continue

                    return_value_name = str(return_entry.get("return_value_name", "")).strip()
                    if not return_value_name:
                        continue

                    visible = bool(return_entry.get("visible", True))
                    friendship = bool(return_entry.get("friendship", False))

                    if only_visible_package_returns and not visible:
                        continue

                    if only_friendship_returns and not friendship:
                        continue

                    item = {
                        "source_type": "package_return",
                        "source_name": package_name,
                        "package_index": package_index,
                        "package_name": package_name,
                        "return_value_name": return_value_name,
                        "visible": visible,
                        "friendship": friendship,
                    }

                    key = (
                        item["source_type"],
                        item["package_name"],
                        item["return_value_name"],
                        item["package_index"],
                    )
                    if key in seen_keys:
                        continue

                    seen_keys.add(key)
                    return_items.append(item)

        return return_items

    def _format_return_universe_option(self, return_item: dict) -> str:
        return_value_name = str(return_item.get("return_value_name", "")).strip()
        package_name = str(return_item.get("package_name", "")).strip()

        return self._format_previous_return_option(
            return_value_name=return_value_name,
            package_name=package_name,
        )

    def _format_previous_return_option(
        self,
        return_value_name: str,
        package_name: str,
    ) -> str:
        clean_return_value_name = str(return_value_name or "").strip()
        clean_package_name = str(package_name or "").strip()

        if not clean_return_value_name:
            return ""

        if not clean_package_name:
            return clean_return_value_name

        return f"{clean_return_value_name} ({clean_package_name})"

    def _get_return_universe_options(
        self,
        tab_info: dict | None,
        include_defaults: bool = True,
        include_package_returns: bool = True,
        only_visible_package_returns: bool = False,
        only_friendship_returns: bool = False,
        before_package_index: int | None = None,
    ) -> list[str]:
        options: list[str] = []

        for return_item in self._get_task_return_universe(
            tab_info=tab_info,
            include_defaults=include_defaults,
            include_package_returns=include_package_returns,
            only_visible_package_returns=only_visible_package_returns,
            only_friendship_returns=only_friendship_returns,
            before_package_index=before_package_index,
        ):
            option = self._format_return_universe_option(return_item)
            if option and option not in options:
                options.append(option)

        return options

    def _get_available_previous_return_options(
        self,
        packages: list[dict],
        current_package_index: int,
        tab_info: dict | None = None,
    ) -> list[str]:
        if tab_info is None:
            tab_info = {
                "default_return_rows": [],
                "packages": packages if isinstance(packages, list) else [],
            }

        return self._get_return_universe_options(
            tab_info=tab_info,
            include_defaults=True,
            include_package_returns=True,
            only_visible_package_returns=True,
            only_friendship_returns=False,
            before_package_index=current_package_index,
        )

    def _refresh_returns_panel(self, tab_info: dict) -> None:
        returns_inner = tab_info.get("returns_inner")

        if returns_inner is None:
            return

        for child in returns_inner.winfo_children():
            child.destroy()

        rendered_defaults = self._render_defaults_section(
            parent=returns_inner,
            tab_info=tab_info,
        )

        rendered_package_returns = self._render_all_package_returns(
            parent=returns_inner,
            tab_info=tab_info,
        )

        if rendered_defaults == 0 and rendered_package_returns == 0:
            self._render_empty_message(
                parent=returns_inner,
                message="No defaults or package returns are currently available for this task.",
            )

    def _render_empty_message(self, parent: tk.Widget, message: str) -> None:
        empty_frame = tk.Frame(parent, padx=12, pady=12)
        empty_frame.pack(fill="x", anchor="n")

        tk.Label(
            empty_frame,
            text=message,
            anchor="w",
            justify="left",
            fg="gray40",
            font=("Segoe UI", 10),
        ).pack(fill="x")

    def _render_section_header(self, parent: tk.Widget, text: str) -> tk.LabelFrame:
        section = tk.LabelFrame(
            parent,
            text=text,
            padx=8,
            pady=8,
        )
        section.pack(fill="x", expand=True, padx=4, pady=(0, 8), anchor="n")
        return section

    def _render_defaults_section(self, parent: tk.Widget, tab_info: dict) -> int:
        default_items = self._get_task_return_universe(
            tab_info=tab_info,
            include_defaults=True,
            include_package_returns=False,
        )

        if not default_items:
            return 0

        section = self._render_section_header(parent, "Defaults")

        for default_item in default_items:
            return_name = str(default_item.get("return_value_name", "")).strip()

            row = tk.Frame(section)
            row.pack(fill="x", pady=2)

            tk.Label(
                row,
                text=return_name,
                anchor="w",
                justify="left",
                font=("Consolas", 10),
            ).pack(side="left", fill="x", expand=True)

        return len(default_items)

    def _render_all_package_returns(self, parent: tk.Widget, tab_info: dict) -> int:
        packages = self._get_live_packages_for_returns(tab_info)

        if not packages:
            return 0

        rendered_count = 0

        for package_index, package_entry in enumerate(packages, start=1):
            if not isinstance(package_entry, dict):
                continue

            package_name = str(package_entry.get("name", "")).strip() or f"Package {package_index}"
            returns = package_entry.get("returns", [])

            if returns in (None, ""):
                returns = []
                package_entry["returns"] = returns

            if not isinstance(returns, list):
                continue

            valid_returns = [
                return_entry
                for return_entry in returns
                if isinstance(return_entry, dict)
                and str(return_entry.get("return_value_name", "")).strip()
            ]

            if not valid_returns:
                continue

            self._render_package_returns_section(
                parent=parent,
                tab_info=tab_info,
                package_name=package_name,
                returns=valid_returns,
            )

            rendered_count += len(valid_returns)

        return rendered_count

    def _render_package_returns_section(
        self,
        parent: tk.Widget,
        tab_info: dict,
        package_name: str,
        returns: list[dict],
    ) -> None:
        section = self._render_section_header(parent, package_name)

        header = tk.Frame(section)
        header.pack(fill="x", pady=(0, 4))

        tk.Label(
            header,
            text="Return",
            width=38,
            anchor="w",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(0, 8))

        tk.Label(
            header,
            text="Visible",
            width=10,
            anchor="w",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(0, 8))

        tk.Label(
            header,
            text="Friendship",
            width=12,
            anchor="w",
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")

        for return_entry in returns:
            self._ensure_package_return_flags(return_entry)

            return_name = str(return_entry.get("return_value_name", "")).strip()

            row = tk.Frame(section)
            row.pack(fill="x", pady=2)

            tk.Label(
                row,
                text=return_name,
                width=38,
                anchor="w",
                justify="left",
                font=("Consolas", 10),
            ).pack(side="left", padx=(0, 8))

            visible_var = tk.BooleanVar(value=bool(return_entry.get("visible", True)))
            friendship_var = tk.BooleanVar(value=bool(return_entry.get("friendship", False)))

            tk.Checkbutton(
                row,
                variable=visible_var,
                command=lambda entry=return_entry, var=visible_var, info=tab_info: self._handle_package_return_visible_changed(
                    tab_info=info,
                    return_entry=entry,
                    visible_value=bool(var.get()),
                ),
            ).pack(side="left", padx=(0, 8))

            tk.Checkbutton(
                row,
                variable=friendship_var,
                command=lambda entry=return_entry, var=friendship_var, info=tab_info: self._handle_package_return_friendship_changed(
                    tab_info=info,
                    return_entry=entry,
                    friendship_value=bool(var.get()),
                ),
            ).pack(side="left")

    def _ensure_package_return_flags(self, return_entry: dict) -> None:
        if "visible" not in return_entry:
            return_entry["visible"] = True

        if "friendship" not in return_entry:
            return_entry["friendship"] = False

        return_entry["visible"] = bool(return_entry.get("visible", True))
        return_entry["friendship"] = bool(return_entry.get("friendship", False))

    def _handle_package_return_visible_changed(
        self,
        tab_info: dict,
        return_entry: dict,
        visible_value: bool,
    ) -> None:
        return_entry["visible"] = bool(visible_value)
        self._mark_tab_dirty(tab_info)
        self._refresh_returns_panel(tab_info)

    def _handle_package_return_friendship_changed(
        self,
        tab_info: dict,
        return_entry: dict,
        friendship_value: bool,
    ) -> None:
        return_entry["friendship"] = bool(friendship_value)
        self._mark_tab_dirty(tab_info)
        self._refresh_returns_panel(tab_info)
from __future__ import annotations

import copy
import tkinter as tk
from tkinter import messagebox, ttk


class DefaultsTabMixin:
    """
    Defaults tab UI and default-return collection.

    Owns:
        - building the Defaults tab
        - editing default return rows
        - inheriting defaults from agent/group scopes
        - loading/collecting default returns for agent/group/task payloads

    Does not own:
        - backend canonical validation
        - package return exposure state
        - package hydration
    """

    def _normalize_default_return_row(self, item: object) -> dict[str, str]:
        if not isinstance(item, dict):
            return {
                "return_value_name": "",
                "return_description": "",
                "return_value": "",
            }

        return_value_name = str(item.get("return_value_name", "")).strip()
        return_description = str(item.get("return_description", "")).strip()
        return_value = item.get("return_value", "")

        return {
            "return_value_name": return_value_name,
            "return_description": return_description,
            "return_value": "" if return_value is None else str(return_value),
        }

    def _normalize_default_rows_for_copy(self, raw_rows: object) -> list[dict]:
        if raw_rows in (None, ""):
            return []

        if not isinstance(raw_rows, list):
            return []

        normalized_rows: list[dict] = []

        for row in raw_rows:
            normalized_row = self._normalize_default_return_row(row)
            return_value_name = str(normalized_row.get("return_value_name", "")).strip()

            if not return_value_name:
                continue

            normalized_rows.append(
                {
                    "return_value_name": return_value_name,
                    "return_description": str(normalized_row.get("return_description", "")).strip(),
                    "return_value": "" if normalized_row.get("return_value", "") is None else str(normalized_row.get("return_value", "")),
                }
            )

        return normalized_rows

    def _get_default_return_rows(self, tab_info: dict) -> list[dict]:
        raw_rows = tab_info.setdefault("default_return_rows", [])

        if not isinstance(raw_rows, list):
            raw_rows = []
            tab_info["default_return_rows"] = raw_rows

        normalized_rows: list[dict] = []
        changed = False

        for item in raw_rows:
            normalized_item = self._normalize_default_return_row(item)
            normalized_rows.append(normalized_item)

            if normalized_item != item:
                changed = True

        if changed:
            tab_info["default_return_rows"] = normalized_rows
            raw_rows = normalized_rows

        return raw_rows

    def _refresh_task_value_surfaces_after_defaults_change(self, tab_info: dict) -> None:
        if tab_info.get("scope") != "task":
            return

        if hasattr(self, "_refresh_package_editor"):
            self._refresh_package_editor(tab_info)

        if hasattr(self, "_refresh_returns_panel"):
            self._refresh_returns_panel(tab_info)

    def _handle_add_default_return(self, tab_info: dict) -> None:
        rows = self._get_default_return_rows(tab_info)
        rows.append(
            {
                "return_value_name": "",
                "return_description": "",
                "return_value": "",
            }
        )

        self._mark_tab_dirty(tab_info)
        self._refresh_defaults_panel(tab_info)
        self._refresh_task_value_surfaces_after_defaults_change(tab_info)

    def _remove_default_return_item(self, tab_info: dict, index: int) -> None:
        rows = self._get_default_return_rows(tab_info)

        if 0 <= index < len(rows):
            rows.pop(index)
            self._mark_tab_dirty(tab_info)

        self._refresh_defaults_panel(tab_info)
        self._refresh_task_value_surfaces_after_defaults_change(tab_info)

    def _build_default_return_item_row(
        self,
        tab_info: dict,
        row: int,
        item: dict,
        index: int,
    ) -> int:
        inner = tab_info.get("defaults_inner")
        if inner is None:
            return row

        normalized_item = self._normalize_default_return_row(item)
        item.clear()
        item.update(normalized_item)

        container = tk.LabelFrame(
            inner,
            text=f"Default Return {index + 1}",
            padx=10,
            pady=10,
        )
        container.grid(row=row, column=0, sticky="ew", padx=4, pady=4)
        container.grid_columnconfigure(0, weight=1)

        tk.Label(container, text="Return Value Name:").grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 4),
        )
        return_value_name_entry = tk.Entry(container, font=("Consolas", 10))
        return_value_name_entry.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        return_value_name_entry.insert(0, item.get("return_value_name", ""))

        tk.Label(container, text="Return Description:").grid(
            row=2,
            column=0,
            sticky="w",
            pady=(0, 4),
        )
        return_description_entry = tk.Entry(container, font=("Consolas", 10))
        return_description_entry.grid(row=3, column=0, sticky="ew", pady=(0, 6))
        return_description_entry.insert(0, item.get("return_description", ""))

        tk.Label(container, text="Return Value:").grid(
            row=4,
            column=0,
            sticky="w",
            pady=(0, 4),
        )

        return_value_frame = tk.Frame(container)
        return_value_frame.grid(row=5, column=0, sticky="nsew")
        return_value_frame.grid_columnconfigure(0, weight=1)
        return_value_frame.grid_rowconfigure(0, weight=1)

        return_value_text = tk.Text(
            return_value_frame,
            wrap="none",
            undo=True,
            font=("Consolas", 10),
            height=4,
        )
        return_value_text.grid(row=0, column=0, sticky="nsew")
        return_value_text.insert("1.0", item.get("return_value", ""))

        return_value_y_scroll = tk.Scrollbar(
            return_value_frame,
            orient="vertical",
            command=return_value_text.yview,
        )
        return_value_y_scroll.grid(row=0, column=1, sticky="ns")
        return_value_text.configure(yscrollcommand=return_value_y_scroll.set)

        def _capture_return_fields(event=None, target=item) -> None:
            target["return_value_name"] = return_value_name_entry.get().strip()
            target["return_description"] = return_description_entry.get().strip()
            target["return_value"] = return_value_text.get("1.0", "end-1c")
            self._mark_tab_dirty(tab_info)

        def _capture_return_fields_and_refresh_options(event=None, target=item) -> None:
            _capture_return_fields(event=event, target=target)
            self._refresh_task_value_surfaces_after_defaults_change(tab_info)

        return_value_name_entry.bind("<KeyRelease>", _capture_return_fields)
        return_value_name_entry.bind("<FocusOut>", _capture_return_fields_and_refresh_options)

        return_description_entry.bind("<KeyRelease>", _capture_return_fields)
        return_description_entry.bind("<FocusOut>", _capture_return_fields)

        return_value_text.bind("<KeyRelease>", _capture_return_fields)
        return_value_text.bind("<FocusOut>", _capture_return_fields)

        button_row = tk.Frame(container)
        button_row.grid(row=6, column=0, sticky="e", pady=(8, 0))

        tk.Button(
            button_row,
            text="Remove",
            width=10,
            command=lambda item_index=index: self._remove_default_return_item(
                tab_info,
                item_index,
            ),
        ).pack(side="right")

        return row + 1

    def _refresh_defaults_panel(self, tab_info: dict) -> None:
        inner = tab_info.get("defaults_inner")
        if inner is None:
            return

        for widget in inner.winfo_children():
            widget.destroy()

        rows = self._get_default_return_rows(tab_info)

        if not rows:
            empty_label = tk.Label(
                inner,
                text="No default returns added.",
                anchor="w",
                fg="gray35",
            )
            empty_label.grid(row=0, column=0, sticky="w", padx=6, pady=6)
            inner.grid_columnconfigure(0, weight=1)
            return

        row = 0

        for index, item in enumerate(rows):
            if not isinstance(item, dict):
                item = {
                    "return_value_name": "",
                    "return_description": "",
                    "return_value": "",
                }
                rows[index] = item

            row = self._build_default_return_item_row(
                tab_info=tab_info,
                row=row,
                item=item,
                index=index,
            )

        inner.grid_columnconfigure(0, weight=1)

    def _collect_default_return_rows(self, tab_info: dict) -> list[dict[str, str]]:
        collected: list[dict[str, str]] = []

        for item in self._get_default_return_rows(tab_info):
            normalized_item = self._normalize_default_return_row(item)

            return_value_name = str(normalized_item.get("return_value_name", "")).strip()
            return_description = str(normalized_item.get("return_description", "")).strip()
            return_value = normalized_item.get("return_value", "")

            if return_value_name:
                collected.append(
                    {
                        "return_value_name": return_value_name,
                        "return_description": return_description,
                        "return_value": "" if return_value is None else str(return_value),
                    }
                )

        return collected

    def _get_defaults_helper_text(self, scope: str) -> str:
        if scope == "agent":
            return (
                "Add agent-level default returns. Groups can copy selected values from this list "
                "using Inherit Agent Defaults."
            )

        if scope == "group":
            return (
                "Add group-level default returns. These are saved directly to this group. "
                "Tasks can copy selected values from this list using Inherit Group Defaults."
            )

        return (
            "Add task-level return values that already exist before the first package runs. "
            "These values appear in package argument dropdowns as Defaults returns."
        )

    def _build_defaults_tab(
        self,
        inner_notebook: ttk.Notebook,
        tab_info: dict,
    ) -> None:
        defaults_tab = tk.Frame(inner_notebook, padx=8, pady=8)
        inner_notebook.add(defaults_tab, text="Defaults")

        scope = str(tab_info.get("scope", "task")).strip().lower()

        defaults_header_label = tk.Label(
            defaults_tab,
            text="Default Returns",
            anchor="w",
            justify="left",
            font=("Segoe UI", 10, "bold"),
        )
        defaults_header_label.pack(fill="x", pady=(0, 2))

        defaults_helper_label = tk.Label(
            defaults_tab,
            text=self._get_defaults_helper_text(scope),
            anchor="w",
            justify="left",
            wraplength=900,
            fg="gray40",
        )
        defaults_helper_label.pack(fill="x", pady=(0, 8))

        defaults_controls_row = tk.Frame(defaults_tab)
        defaults_controls_row.pack(fill="x", pady=(0, 8))

        tk.Button(
            defaults_controls_row,
            text="Add Default Return",
            width=18,
            command=lambda info=tab_info: self._handle_add_default_return(info),
        ).pack(side="left")

        if scope == "group":
            tk.Button(
                defaults_controls_row,
                text="Inherit Agent Defaults",
                width=22,
                command=lambda info=tab_info: self._handle_inherit_agent_defaults_for_group(info),
            ).pack(side="left", padx=(8, 0))

        if scope == "task":
            tk.Button(
                defaults_controls_row,
                text="Inherit Group Defaults",
                width=22,
                command=lambda info=tab_info: self._handle_inherit_group_defaults_for_task(info),
            ).pack(side="left", padx=(8, 0))

        defaults_canvas_frame = tk.Frame(defaults_tab)
        defaults_canvas_frame.pack(fill="both", expand=True)

        defaults_canvas = tk.Canvas(defaults_canvas_frame, highlightthickness=0)
        defaults_canvas.pack(side="left", fill="both", expand=True)

        defaults_scroll = tk.Scrollbar(
            defaults_canvas_frame,
            orient="vertical",
            command=defaults_canvas.yview,
        )
        defaults_scroll.pack(side="right", fill="y")
        defaults_canvas.configure(yscrollcommand=defaults_scroll.set)

        defaults_inner = tk.Frame(defaults_canvas)
        defaults_window = defaults_canvas.create_window(
            (0, 0),
            window=defaults_inner,
            anchor="nw",
        )

        def _sync_defaults_scrollregion(event=None) -> None:
            defaults_canvas.configure(scrollregion=defaults_canvas.bbox("all"))

        def _sync_defaults_inner_width(event) -> None:
            defaults_canvas.itemconfigure(defaults_window, width=event.width)

        defaults_inner.bind("<Configure>", _sync_defaults_scrollregion)
        defaults_canvas.bind("<Configure>", _sync_defaults_inner_width)

        tab_info["defaults_tab"] = defaults_tab
        tab_info["defaults_canvas"] = defaults_canvas
        tab_info["defaults_inner"] = defaults_inner

        self._refresh_defaults_panel(tab_info)

    def _copy_default_rows_into_tab(self, tab_info: dict, selected_rows: list[dict]) -> None:
        if not isinstance(tab_info, dict):
            return

        current_rows = self._normalize_default_rows_for_copy(
            tab_info.get("default_return_rows", [])
        )
        current_names = {
            str(row.get("return_value_name", "")).strip()
            for row in current_rows
            if str(row.get("return_value_name", "")).strip()
        }

        rows_to_add: list[dict] = []

        for selected_row in self._normalize_default_rows_for_copy(selected_rows):
            return_value_name = str(selected_row.get("return_value_name", "")).strip()
            if not return_value_name or return_value_name in current_names:
                continue

            rows_to_add.append(copy.deepcopy(selected_row))
            current_names.add(return_value_name)

        if not rows_to_add:
            messagebox.showinfo("Inherit Defaults", "No new defaults were added.")
            return

        current_rows.extend(rows_to_add)
        tab_info["default_return_rows"] = current_rows

        self._mark_tab_dirty(tab_info)
        self._refresh_defaults_panel(tab_info)
        self._refresh_task_value_surfaces_after_defaults_change(tab_info)

        added_count = len(rows_to_add)
        label = "default" if added_count == 1 else "defaults"
        messagebox.showinfo("Inherit Defaults", f"Added {added_count} {label}.")

    def _open_default_row_multi_picker(
        self,
        title: str,
        source_rows: list[dict],
        on_confirm,
    ) -> None:
        rows = self._normalize_default_rows_for_copy(source_rows)

        if not rows:
            messagebox.showinfo(title, "No defaults are available to inherit.")
            return

        popup = tk.Toplevel(self.root)
        popup.title(title)
        popup.geometry("560x420")
        popup.minsize(420, 300)
        popup.transient(self.root)
        popup.grab_set()

        outer = tk.Frame(popup, padx=12, pady=12)
        outer.pack(fill="both", expand=True)

        tk.Label(
            outer,
            text="Choose defaults to copy into this list.",
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(0, 8))

        list_frame = tk.Frame(outer)
        list_frame.pack(fill="both", expand=True)

        listbox = tk.Listbox(
            list_frame,
            selectmode="extended",
            font=("Consolas", 10),
        )
        listbox.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.configure(yscrollcommand=scrollbar.set)

        row_by_index: dict[int, dict] = {}

        for index, row in enumerate(rows):
            return_value_name = str(row.get("return_value_name", "")).strip()
            return_description = str(row.get("return_description", "")).strip()

            label = return_value_name
            if return_description:
                label = f"{return_value_name} — {return_description}"

            listbox.insert(tk.END, label)
            row_by_index[index] = row

        button_row = tk.Frame(outer)
        button_row.pack(fill="x", pady=(10, 0))

        def _confirm_selection() -> None:
            selected_indexes = listbox.curselection()

            if not selected_indexes:
                messagebox.showerror("No Selection", "Choose at least one default to inherit.")
                return

            selected_rows = [
                copy.deepcopy(row_by_index[index])
                for index in selected_indexes
                if index in row_by_index
            ]

            popup.destroy()
            on_confirm(selected_rows)

        tk.Button(
            button_row,
            text="Inherit Selected",
            width=16,
            command=_confirm_selection,
        ).pack(side="left")

        tk.Button(
            button_row,
            text="Cancel",
            width=12,
            command=popup.destroy,
        ).pack(side="right")

    def _handle_inherit_agent_defaults_for_group(self, group_info: dict) -> None:
        if not isinstance(group_info, dict):
            messagebox.showerror("Inherit Defaults Failed", "No group is selected.")
            return

        agent_defaults_info = getattr(self, "agent_defaults_tab_info", None)
        if not isinstance(agent_defaults_info, dict):
            messagebox.showerror("Inherit Defaults Failed", "Agent defaults are not available.")
            return

        source_rows = agent_defaults_info.get("default_return_rows", [])

        self._open_default_row_multi_picker(
            title="Inherit Agent Defaults",
            source_rows=source_rows,
            on_confirm=lambda selected_rows, target=group_info: self._copy_default_rows_into_tab(
                target,
                selected_rows,
            ),
        )

    def _handle_inherit_group_defaults_for_task(self, tab_info: dict) -> None:
        if not isinstance(tab_info, dict):
            messagebox.showerror("Inherit Defaults Failed", "No task is selected.")
            return

        group_info = tab_info.get("group_info")
        if not isinstance(group_info, dict):
            messagebox.showerror("Inherit Defaults Failed", "Could not find this task's group.")
            return

        source_rows = group_info.get("default_return_rows", [])

        self._open_default_row_multi_picker(
            title="Inherit Group Defaults",
            source_rows=source_rows,
            on_confirm=lambda selected_rows, target=tab_info: self._copy_default_rows_into_tab(
                target,
                selected_rows,
            ),
        )

    def _collect_default_returns_from_tab(self, tab_info: dict) -> list[dict]:
        if not isinstance(tab_info, dict):
            return []

        return self._collect_default_return_rows(tab_info)

    def _collect_agent_default_returns(self) -> list[dict]:
        tab_info = getattr(self, "agent_defaults_tab_info", None)
        if not isinstance(tab_info, dict):
            return []

        return self._collect_default_returns_from_tab(tab_info)

    def _collect_group_default_returns(self, group_info: dict) -> list[dict]:
        if not isinstance(group_info, dict):
            return []

        return self._collect_default_returns_from_tab(group_info)

    def _load_agent_defaults_into_tab(self, default_returns: object) -> None:
        tab_info = getattr(self, "agent_defaults_tab_info", None)
        if not isinstance(tab_info, dict):
            return

        tab_info["default_return_rows"] = self._normalize_default_rows_for_copy(default_returns)
        tab_info["dirty"] = False

        self._refresh_defaults_panel(tab_info)

    def _load_group_defaults_into_tab(self, group_info: dict, default_returns: object) -> None:
        if not isinstance(group_info, dict):
            return

        group_info["default_return_rows"] = self._normalize_default_rows_for_copy(default_returns)
        group_info["dirty"] = False

        self._refresh_defaults_panel(group_info)
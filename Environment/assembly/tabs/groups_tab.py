from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk


class GroupsTabMixin:
    """
    Group/outer task-area UI for the Assembly editor.

    Owns:
        - building the outer group notebook
        - agent defaults tab setup
        - group defaults tab setup
        - group tab creation/rename/delete
        - moving a task from one group to another

    Does not own:
        - canonical backend schema validation
        - package hydration
        - save/load persistence
        - generic notebook drag mechanics
        - canonical Outcasts naming
        - return visibility/friendship state
    """

    def _build_tasks_area(self, parent: tk.Widget) -> None:
        self.assembly_tabs = []
        self.task_group_tabs = []
        self.task_group_tab_by_name = {}
        self.agent_defaults_tab_info = None
        self._task_ui_switch_guard = False
        self._last_selected_group_frame = None
        self._last_selected_task_frame_by_group = {}

        tasks_outer = tk.Frame(parent)
        tasks_outer.pack(fill="both", expand=True)

        self.task_group_notebook = ttk.Notebook(tasks_outer)
        self.task_group_notebook.pack(fill="both", expand=True)

        self.task_group_notebook.bind(
            "<<NotebookTabChanged>>",
            self._handle_task_group_notebook_changed,
            add="+",
        )

        self._bind_reorderable_notebook_tabs(
            notebook=self.task_group_notebook,
            reorder_callback=self._sync_group_order_from_notebook,
            pinned_first=True,
        )

        self._create_agent_defaults_tab(select=False)
        self._create_task_group_tab(self._get_outcasts_task_group_name(), select=True)

    def _create_defaults_scope_tab_info(self, scope_name: str, frame: tk.Widget) -> dict:
        return {
            "scope": scope_name,
            "frame": frame,
            "packages": [],
            "package_canvas": None,
            "package_inner": tk.Frame(frame),
            "package_row_widgets": [],
            "package_name_labels": [],
            "selected_package_index": None,
            "show_hidden_package_arguments": {},
            "default_return_rows": [],
            "dirty": False,
            "loaded_snapshot": None,
        }

    def _create_agent_defaults_tab(self, select: bool = False) -> dict:
        defaults_frame = tk.Frame(self.task_group_notebook, padx=8, pady=8)
        tab_info = self._create_defaults_scope_tab_info("agent", defaults_frame)
        self.agent_defaults_tab_info = tab_info

        defaults_notebook = ttk.Notebook(defaults_frame)
        defaults_notebook.pack(fill="both", expand=True)

        self._build_defaults_tab(defaults_notebook, tab_info)

        self.task_group_notebook.add(defaults_frame, text="Defaults")

        if select:
            self.task_group_notebook.select(defaults_frame)

        if hasattr(self, "_refresh_defaults_panel"):
            self._refresh_defaults_panel(tab_info)

        return tab_info

    def _is_agent_defaults_frame(self, frame: tk.Widget | None) -> bool:
        tab_info = getattr(self, "agent_defaults_tab_info", None)
        return isinstance(tab_info, dict) and tab_info.get("frame") == frame

    def _create_task_group_defaults_tab(self, group_info: dict) -> None:
        task_notebook = group_info["task_notebook"]

        defaults_frame = tk.Frame(task_notebook, padx=8, pady=8)
        group_info["defaults_frame"] = defaults_frame

        defaults_notebook = ttk.Notebook(defaults_frame)
        defaults_notebook.pack(fill="both", expand=True)

        self._build_defaults_tab(defaults_notebook, group_info)
        task_notebook.add(defaults_frame, text="Defaults")

        if hasattr(self, "_refresh_defaults_panel"):
            self._refresh_defaults_panel(group_info)

    def _is_group_defaults_frame(self, group_info: dict, frame: tk.Widget | None) -> bool:
        return isinstance(group_info, dict) and group_info.get("defaults_frame") == frame

    def _create_task_group_tab(
        self,
        group_name: str | None = None,
        select: bool = True,
    ) -> dict:
        if group_name is None:
            group_name = self._generate_unique_task_group_name("New Group")

        group_name = str(group_name or "").strip() or self._generate_unique_task_group_name("New Group")

        if group_name in self.task_group_tab_by_name:
            group_name = self._generate_unique_task_group_name(group_name)

        group_frame = tk.Frame(self.task_group_notebook, padx=8, pady=8)

        top_row = tk.Frame(group_frame)
        top_row.pack(fill="x", pady=(0, 8))

        tk.Label(top_row, text="Group Name").pack(side="left")

        group_name_var = tk.StringVar(value=group_name)
        group_name_entry = tk.Entry(
            top_row,
            textvariable=group_name_var,
            font=("Segoe UI", 11),
        )
        group_name_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))

        if group_name == self._get_outcasts_task_group_name():
            group_name_entry.configure(state="readonly")

        tk.Button(
            top_row,
            text="Add Task",
            width=12,
            command=self._handle_add_task_tab,
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            top_row,
            text="Delete Task",
            width=12,
            command=self._handle_delete_task_tab,
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            top_row,
            text="Copy Task",
            width=12,
            command=self._handle_copy_task_tab,
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            top_row,
            text="Change Group",
            width=14,
            command=self._handle_change_current_task_group,
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            top_row,
            text="Remove from Group",
            width=18,
            command=self._handle_remove_current_task_from_group,
        ).pack(side="right")

        task_notebook = ttk.Notebook(group_frame)
        task_notebook.pack(fill="both", expand=True)

        group_info = {
            "scope": "group",
            "name": group_name,
            "frame": group_frame,
            "group_name_var": group_name_var,
            "group_name_entry": group_name_entry,
            "task_notebook": task_notebook,
            "task_tabs": [],
            "packages": [],
            "package_canvas": None,
            "package_inner": tk.Frame(group_frame),
            "package_row_widgets": [],
            "package_name_labels": [],
            "selected_package_index": None,
            "show_hidden_package_arguments": {},
            "default_return_rows": [],
            "dirty": False,
            "loaded_snapshot": None,
        }

        self._create_task_group_defaults_tab(group_info)

        task_notebook.bind(
            "<<NotebookTabChanged>>",
            lambda event, info=group_info: self._handle_group_task_notebook_changed(event, info),
            add="+",
        )

        self._bind_reorderable_notebook_tabs(
            notebook=task_notebook,
            reorder_callback=lambda info=group_info: self._sync_task_order_from_notebook(info),
            pinned_first=True,
        )

        group_name_var.trace_add(
            "write",
            lambda *_args, info=group_info: self._handle_task_group_name_changed(info),
        )

        self.task_group_notebook.add(group_frame, text=group_name)
        self.task_group_tabs.append(group_info)
        self.task_group_tab_by_name[group_name] = group_info

        if select:
            self.task_group_notebook.select(group_frame)
            self._last_selected_group_frame = group_frame

        return group_info

    def _generate_unique_task_group_name(self, base_name: str) -> str:
        clean_base = str(base_name or "").strip() or "New Group"

        existing = {
            str(group.get("name", "")).strip()
            for group in getattr(self, "task_group_tabs", [])
            if str(group.get("name", "")).strip()
        }

        if clean_base not in existing:
            return clean_base

        index = 2
        while True:
            candidate = f"{clean_base} {index}"
            if candidate not in existing:
                return candidate
            index += 1

    def _get_current_group_info(self) -> dict:
        current_tab_id = self.task_group_notebook.select()

        if not current_tab_id:
            raise ValueError("No group is selected.")

        current_frame = self.root.nametowidget(current_tab_id)

        if self._is_agent_defaults_frame(current_frame):
            raise ValueError("Agent Defaults is selected, not a group.")

        for group_info in self.task_group_tabs:
            if group_info["frame"] == current_frame:
                return group_info

        raise ValueError("Could not find selected group.")

    def _handle_task_group_name_changed(self, group_info: dict) -> None:
        old_name = str(group_info.get("name", "")).strip()
        requested_name = str(group_info["group_name_var"].get() or "").strip()

        outcasts_name = self._get_outcasts_task_group_name()

        if old_name == outcasts_name:
            if requested_name != outcasts_name:
                group_info["group_name_var"].set(outcasts_name)
            return

        if not requested_name:
            return

        if requested_name != old_name and requested_name in self.task_group_tab_by_name:
            return

        if requested_name == old_name:
            return

        self.task_group_tab_by_name.pop(old_name, None)
        group_info["name"] = requested_name
        self.task_group_tab_by_name[requested_name] = group_info
        self.task_group_notebook.tab(group_info["frame"], text=requested_name)
        self._mark_tab_dirty(group_info)

    def _handle_add_task_group(self) -> None:
        if not self._prompt_to_save_dirty_current_task_before_group_switch():
            return

        group_name = self._generate_unique_task_group_name("New Group")
        group_info = self._create_task_group_tab(group_name, select=True)
        self._mark_tab_dirty(group_info)

    def _handle_delete_task_group(self) -> None:
        try:
            group_info = self._get_current_group_info()
        except Exception as exc:
            messagebox.showerror("Delete Group Failed", str(exc))
            return

        group_name = str(group_info.get("name", "")).strip()
        outcasts_name = self._get_outcasts_task_group_name()

        if group_name == outcasts_name:
            messagebox.showerror("Delete Group Failed", "Outcasts cannot be deleted.")
            return

        confirmed = messagebox.askyesno(
            "Delete Group",
            f"Delete group '{group_name}'?\n\n"
            "Tasks in this group will be moved to Outcasts.",
        )

        if not confirmed:
            return

        if not self._prompt_to_save_dirty_current_task_before_group_switch():
            return

        outcasts_group = self._get_or_create_task_group(outcasts_name)

        move_snapshots: list[dict] = []

        for tab_info in list(group_info.get("task_tabs", [])):
            snapshot = self._collect_single_task_from_tab_no_hydrate(tab_info)
            if str(snapshot.get("name", "")).strip():
                move_snapshots.append(snapshot)

            self._remove_task_tab_from_group(tab_info, group_info, destroy_frame=True)

        for snapshot in move_snapshots:
            task_name = str(snapshot.get("name", "")).strip()
            if not task_name:
                continue

            self._create_task_tab_from_snapshot(
                snapshot=snapshot,
                group_info=outcasts_group,
                task_name=task_name,
                select=False,
                mark_dirty=True,
            )

        self.task_group_notebook.forget(group_info["frame"])
        self.task_group_tabs.remove(group_info)
        self.task_group_tab_by_name.pop(group_name, None)

        try:
            group_info["frame"].destroy()
        except Exception:
            pass

        self._mark_tab_dirty(outcasts_group)

        if self.task_group_tabs:
            self.task_group_notebook.select(self.task_group_tabs[0]["frame"])

    def _get_or_create_task_group(self, group_name: str) -> dict:
        clean_name = str(group_name or "").strip() or self._get_outcasts_task_group_name()

        existing = self.task_group_tab_by_name.get(clean_name)
        if existing is not None:
            return existing

        return self._create_task_group_tab(clean_name, select=False)

    def _handle_change_current_task_group(self) -> None:
        try:
            tab_info = self._get_current_task_tab_info()
        except Exception as exc:
            messagebox.showerror("Change Group Failed", str(exc))
            return

        source_group = tab_info.get("group_info")
        if source_group is None:
            messagebox.showerror("Change Group Failed", "Could not find the current task group.")
            return

        source_group_name = str(source_group.get("name", "")).strip()

        available_groups = [
            str(group.get("name", "")).strip()
            for group in self.task_group_tabs
            if str(group.get("name", "")).strip()
            and str(group.get("name", "")).strip() != source_group_name
        ]

        if not available_groups:
            messagebox.showinfo("Change Group", "There is no other group to move this task into.")
            return

        self._open_item_picker(
            title_text="Group",
            item_names=available_groups,
            on_select=lambda selected_group_name, info=tab_info: self._move_task_to_group(
                info,
                selected_group_name,
            ),
        )

    def _move_task_to_group(self, source_tab_info: dict, target_group_name: str) -> None:
        source_group = source_tab_info.get("group_info")
        target_group = self.task_group_tab_by_name.get(str(target_group_name).strip())

        if source_group is None:
            messagebox.showerror("Change Group Failed", "Could not find the source group.")
            return

        if target_group is None:
            messagebox.showerror("Change Group Failed", f"Group not found: {target_group_name}")
            return

        task_snapshot = self._collect_single_task_from_tab_no_hydrate(source_tab_info)
        task_name = str(task_snapshot.get("name", "")).strip()

        if not task_name:
            messagebox.showerror("Change Group Failed", "Current task must have a name before moving it.")
            return

        try:
            frame_index = source_group["task_tabs"].index(source_tab_info)
        except Exception:
            frame_index = None

        self._remove_task_tab_from_group(
            source_tab_info,
            source_group,
            destroy_frame=True,
        )

        moved_tab = self._create_task_tab_from_snapshot(
            snapshot=task_snapshot,
            group_info=target_group,
            task_name=task_name,
            select=True,
            mark_dirty=True,
        )

        self.task_group_notebook.select(target_group["frame"])
        target_group["task_notebook"].select(moved_tab["frame"])
        self._last_selected_task_frame_by_group[id(target_group)] = moved_tab["frame"]

        self._mark_tab_dirty(source_group)
        self._mark_tab_dirty(target_group)

        if frame_index is None:
            return

    def _handle_remove_current_task_from_group(self) -> None:
        messagebox.showinfo(
            "Not Implemented",
            "Remove from Group is currently disabled in the single-group task model.",
        )

    def _task_exists_in_group(self, task_name: str, group_name: str) -> bool:
        group_info = self.task_group_tab_by_name.get(str(group_name).strip())
        if group_info is None:
            return False

        clean_task_name = str(task_name or "").strip()
        if not clean_task_name:
            return False

        for tab_info in group_info.get("task_tabs", []):
            if self._get_task_name_from_tab(tab_info) == clean_task_name:
                return True

        return False

    def _remove_task_tab_from_group(
        self,
        tab_info: dict,
        group_info: dict,
        destroy_frame: bool = True,
    ) -> None:
        if tab_info in group_info.get("task_tabs", []):
            group_info["task_tabs"].remove(tab_info)

        if tab_info in self.assembly_tabs:
            self.assembly_tabs.remove(tab_info)

        try:
            group_info["task_notebook"].forget(tab_info["frame"])
        except Exception:
            pass

        if destroy_frame:
            try:
                tab_info["frame"].destroy()
            except Exception:
                pass

    def _handle_task_group_notebook_changed(self, _event=None) -> None:
        if self._task_ui_switch_guard:
            return

        if not self._prompt_to_save_dirty_current_task_before_group_switch():
            try:
                if self._last_selected_group_frame is not None:
                    self._task_ui_switch_guard = True
                    self.task_group_notebook.select(self._last_selected_group_frame)
                    self._task_ui_switch_guard = False
            except Exception:
                self._task_ui_switch_guard = False
            return

        try:
            current_group = self._get_current_group_info()
        except Exception:
            return

        self._last_selected_group_frame = current_group["frame"]

    def _handle_group_task_notebook_changed(self, _event, group_info: dict) -> None:
        if self._task_ui_switch_guard:
            return

        try:
            current_tab = self._get_current_task_tab_info_for_group(group_info)
        except Exception:
            return

        self._last_selected_task_frame_by_group[id(group_info)] = current_tab["frame"]

    def _sync_group_order_from_notebook(self) -> None:
        if not hasattr(self, "task_group_notebook"):
            return

        frame_to_group = {
            str(group_info["frame"]): group_info
            for group_info in self.task_group_tabs
        }

        ordered_groups: list[dict] = []

        for tab_id in self.task_group_notebook.tabs():
            try:
                frame = self.root.nametowidget(tab_id)
            except Exception:
                continue

            if self._is_agent_defaults_frame(frame):
                continue

            group_info = frame_to_group.get(str(frame))
            if group_info is not None:
                ordered_groups.append(group_info)

        if ordered_groups:
            self.task_group_tabs = ordered_groups

    def _sync_task_order_from_notebook(self, group_info: dict) -> None:
        task_notebook = group_info.get("task_notebook")
        if task_notebook is None:
            return

        frame_to_task = {
            str(tab_info["frame"]): tab_info
            for tab_info in group_info.get("task_tabs", [])
        }

        ordered_tasks: list[dict] = []

        for tab_id in task_notebook.tabs():
            try:
                frame = self.root.nametowidget(tab_id)
            except Exception:
                continue

            if self._is_group_defaults_frame(group_info, frame):
                continue

            tab_info = frame_to_task.get(str(frame))
            if tab_info is not None:
                ordered_tasks.append(tab_info)

        if ordered_tasks:
            group_info["task_tabs"] = ordered_tasks
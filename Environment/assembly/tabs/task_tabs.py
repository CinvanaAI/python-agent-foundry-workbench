from __future__ import annotations

import copy
import tkinter as tk
from tkinter import messagebox, ttk

try:
    from fake_call import fake_call
except ModuleNotFoundError as error:
    if error.name != "fake_call":
        raise
    # This optional historical demo connector is not part of the public workbench.
    fake_call = None


class TaskTabsMixin:
    def _generate_unique_task_name(self, base_name: str) -> str:
        clean_base = str(base_name or "").strip() or "Task"
        existing = {
            self._get_task_name_from_tab(tab_info)
            for tab_info in getattr(self, "assembly_tabs", [])
        }
        existing = {name for name in existing if name}

        if clean_base not in existing:
            return clean_base

        index = 2
        while True:
            candidate = f"{clean_base} {index}"
            if candidate not in existing:
                return candidate
            index += 1

    def _generate_copy_task_name(self, base_name: str) -> str:
        clean_base = str(base_name or "").strip() or "Task"
        return self._generate_unique_task_name(f"{clean_base} Copy")

    def _get_task_name_from_tab(self, tab_info: dict) -> str:
        try:
            return tab_info["task_name_entry"].get().strip()
        except Exception:
            return str(tab_info.get("name", "")).strip()

    def _get_current_task_tab_info(self) -> dict:
        group_info = self._get_current_group_info()
        return self._get_current_task_tab_info_for_group(group_info)

    def _get_current_task_tab_info_for_group(self, group_info: dict) -> dict:
        task_notebook = group_info["task_notebook"]
        current_tab_id = task_notebook.select()

        if not current_tab_id:
            raise ValueError("No task is selected.")

        current_frame = self.root.nametowidget(current_tab_id)

        if self._is_group_defaults_frame(group_info, current_frame):
            raise ValueError("Group Defaults is selected, not a task.")

        for tab_info in group_info.get("task_tabs", []):
            if tab_info["frame"] == current_frame:
                return tab_info

        raise ValueError("Could not find selected task.")

    def _get_unique_task_names(self) -> list[str]:
        names: list[str] = []

        for tab_info in self.assembly_tabs:
            name = self._get_task_name_from_tab(tab_info)
            if name and name not in names:
                names.append(name)

        return names

    def _create_task_tab_widgets(
        self,
        parent: tk.Widget,
        default_name: str,
        task_status: str = "On Demand",
    ) -> dict:
        top_row = tk.Frame(parent)
        top_row.pack(fill="x", pady=(0, 12))

        name_frame = tk.Frame(top_row)
        name_frame.pack(side="left", fill="x", expand=True, padx=(0, 12))

        tk.Label(name_frame, text="Task Name").pack(anchor="w")

        task_name_entry = tk.Entry(name_frame, font=("Segoe UI", 11))
        task_name_entry.pack(fill="x", pady=(4, 0))
        task_name_entry.insert(0, default_name)

        status_frame = tk.Frame(top_row, width=220)
        status_frame.pack(side="left", fill="y", padx=(0, 12))
        status_frame.pack_propagate(False)

        tk.Label(status_frame, text="Status").pack(anchor="w")

        task_status_var = tk.StringVar(value=self._normalize_task_status(task_status))
        task_status_dropdown = ttk.Combobox(
            status_frame,
            textvariable=task_status_var,
            values=["System", "On Demand"],
            state="readonly",
            font=("Segoe UI", 10),
        )
        task_status_dropdown.pack(fill="x", pady=(4, 0))

        fake_frame = tk.Frame(top_row, width=120)
        fake_frame.pack(side="left", fill="y")
        fake_frame.pack_propagate(False)

        tk.Label(fake_frame, text="").pack(anchor="w")
        tk.Button(
            fake_frame,
            text="Fake" if fake_call else "Demo unavailable",
            width=12,
            command=fake_call,
            state="normal" if fake_call else "disabled",
        ).pack(fill="x", pady=(4, 0))

        inner_notebook = ttk.Notebook(parent)
        inner_notebook.pack(fill="both", expand=True)

        tab_info = {
            "scope": "task",
            "task_name_entry": task_name_entry,
            "task_status_var": task_status_var,
            "task_status_dropdown": task_status_dropdown,
            "inner_notebook": inner_notebook,
            "package_canvas": None,
            "package_inner": None,
            "package_row_widgets": [],
            "package_name_labels": [],
            "selected_package_index": None,
            "packages": [],
            "prompt_tabs": [],
            "prompts_notebook": None,
            "prompts_tab": None,
            "workflow_tab": None,
            "workflow_text": None,
            "triggers_tab": None,
            "triggers_text": None,
            "memory_tab": None,
            "memory_notebook": None,
            "memory_tabs": [],
            "show_hidden_package_arguments": {},
            "default_return_rows": [],
            "triggers": "",
            "memory": [],
            "dirty": False,
            "loaded_snapshot": None,
        }

        self._build_defaults_tab(inner_notebook, tab_info)

        packages_tab = tk.Frame(inner_notebook, padx=8, pady=8)
        inner_notebook.add(packages_tab, text="Packages")
        self._build_packages_tab(packages_tab, tab_info)

        self._build_returns_tab(inner_notebook, tab_info)
        self._build_workflow_tab(inner_notebook, tab_info)
        self._build_triggers_tab(inner_notebook, tab_info)
        self._build_prompts_tab(inner_notebook, tab_info)
        self._build_memory_tab(inner_notebook, tab_info)

        return tab_info

    def _create_new_task_tab(
        self,
        name: str | None = None,
        task_status: str = "On Demand",
        workflow: dict | None = None,
        packages: list[dict] | None = None,
        prompts: list[dict] | None = None,
        triggers: object = None,
        memory: object = None,
        default_returns: object = None,
        group_info: dict | None = None,
        select: bool = True,
        insert_index: int | None = None,
        mark_dirty: bool = False,
    ) -> dict:
        if group_info is None:
            group_info = self._get_current_group_info()

        if name is None:
            name = self._generate_unique_task_name(f"Task {len(self.assembly_tabs) + 1}")
        else:
            name = str(name).strip() or self._generate_unique_task_name(
                f"Task {len(self.assembly_tabs) + 1}"
            )

        normalized_task_status = self._normalize_task_status(task_status)
        normalized_packages = self._normalize_loaded_packages(packages or [])
        normalized_workflow = self._normalize_workflow_block(workflow=workflow)
        normalized_triggers = self._normalize_triggers_block(triggers)
        normalized_memory = self._normalize_memory_block(memory)
        normalized_default_returns = self._normalize_default_rows_for_copy(default_returns)

        tab_frame = tk.Frame(group_info["task_notebook"], padx=12, pady=12)
        tab_info = self._create_task_tab_widgets(tab_frame, name, normalized_task_status)

        tab_info["frame"] = tab_frame
        tab_info["group_info"] = group_info
        tab_info["packages"] = copy.deepcopy(normalized_packages)
        tab_info["triggers"] = normalized_triggers
        tab_info["memory"] = copy.deepcopy(normalized_memory)
        tab_info["default_return_rows"] = copy.deepcopy(normalized_default_returns)

        group_info["task_notebook"].add(tab_frame, text=name)

        if insert_index is None or insert_index < 0 or insert_index > len(group_info["task_tabs"]):
            group_info["task_tabs"].append(tab_info)
        else:
            group_info["task_tabs"].insert(insert_index, tab_info)
            try:
                group_info["task_notebook"].insert(insert_index + 1, tab_frame)
            except Exception:
                pass

        self.assembly_tabs.append(tab_info)

        self._load_workflow_into_tab(tab_info, normalized_workflow.get("workflow_source", ""))
        self._load_triggers_into_tab(tab_info, normalized_triggers)
        self._load_prompts_into_tab(tab_info, prompts or [])
        self._load_memory_into_tab(tab_info, normalized_memory)
        self._refresh_package_editor(tab_info)

        if hasattr(self, "_refresh_defaults_panel"):
            self._refresh_defaults_panel(tab_info)

        if hasattr(self, "_refresh_returns_panel"):
            self._refresh_returns_panel(tab_info)

        tab_info["task_name_entry"].bind(
            "<KeyRelease>",
            lambda event, info=tab_info: self._handle_task_name_key_release(info),
            add="+",
        )

        self._bind_dirty_tracking_for_task_tab(tab_info)

        snapshot = self._collect_single_task_from_tab_no_hydrate(tab_info)
        tab_info["loaded_snapshot"] = copy.deepcopy(snapshot)
        tab_info["dirty"] = bool(mark_dirty)

        if select:
            group_info["task_notebook"].select(tab_frame)
            self._last_selected_task_frame_by_group[id(group_info)] = tab_frame

        return tab_info

    def _create_task_tab_from_snapshot(
        self,
        snapshot: dict,
        group_info: dict,
        task_name: str | None = None,
        select: bool = False,
        insert_index: int | None = None,
        mark_dirty: bool = False,
    ) -> dict:
        if not isinstance(snapshot, dict):
            raise ValueError("Task snapshot must be a dict.")

        clean_name = str(task_name or snapshot.get("name", "")).strip() or "Task"

        created = self._create_new_task_tab(
            name=clean_name,
            task_status=snapshot.get("task_status", "On Demand"),
            workflow=copy.deepcopy(snapshot.get("workflow", {})),
            packages=copy.deepcopy(snapshot.get("packages", [])),
            prompts=copy.deepcopy(snapshot.get("prompts", [])),
            triggers=snapshot.get("Triggers", ""),
            memory=copy.deepcopy(snapshot.get("memory", [])),
            default_returns=copy.deepcopy(snapshot.get("default_returns", [])),
            group_info=group_info,
            select=select,
            insert_index=insert_index,
            mark_dirty=mark_dirty,
        )

        created_snapshot = self._collect_single_task_from_tab_no_hydrate(created)
        created["loaded_snapshot"] = copy.deepcopy(created_snapshot)
        created["dirty"] = bool(mark_dirty)

        return created

    def _handle_task_name_key_release(self, tab_info: dict) -> None:
        self._mark_tab_dirty(tab_info)
        self._sync_task_tab_title(tab_info)

    def _sync_task_tab_title(self, tab_info: dict) -> None:
        title = tab_info["task_name_entry"].get().strip() or "Untitled"
        frame = tab_info["frame"]
        group_info = tab_info.get("group_info")
        if group_info is not None:
            group_info["task_notebook"].tab(frame, text=title)

    def _handle_add_task_tab(self) -> None:
        try:
            group_info = self._get_current_group_info()
        except Exception as exc:
            messagebox.showerror("Add Task Failed", str(exc))
            return

        task_name = self._generate_unique_task_name(
            f"Task {len(self._get_unique_task_names()) + 1}"
        )

        self._create_new_task_tab(
            name=task_name,
            packages=[],
            group_info=group_info,
            select=True,
            mark_dirty=True,
        )

    def _handle_delete_task_tab(self) -> None:
        try:
            tab_info = self._get_current_task_tab_info()
        except Exception as exc:
            messagebox.showerror("Delete Task Failed", str(exc))
            return

        task_name = self._get_task_name_from_tab(tab_info) or "Untitled"

        confirmed = messagebox.askyesno(
            "Delete Task",
            f"Delete task '{task_name}'?",
        )
        if not confirmed:
            return

        group_info = tab_info.get("group_info")
        if group_info is not None:
            self._remove_task_tab_from_group(
                tab_info,
                group_info,
                destroy_frame=True,
            )
            self._mark_tab_dirty(group_info)

        if not self._get_unique_task_names():
            outcasts_group = self._get_or_create_task_group(self._get_outcasts_task_group_name())
            self.task_group_notebook.select(outcasts_group["frame"])
            self._create_new_task_tab(group_info=outcasts_group, mark_dirty=True)

    def _handle_copy_task_tab(self) -> None:
        try:
            source_tab_info = self._get_current_task_tab_info()
            group_info = source_tab_info["group_info"]
        except Exception as exc:
            messagebox.showerror("Copy Task Failed", str(exc))
            return

        source_task = self._collect_single_task_from_tab_no_hydrate(source_tab_info)
        source_name = str(source_task.get("name", "")).strip() or "Task"
        copy_name = self._generate_copy_task_name(source_name)

        source_task["name"] = copy_name
        source_task["task_file"] = ""

        self._create_task_tab_from_snapshot(
            snapshot=source_task,
            group_info=group_info,
            task_name=copy_name,
            select=True,
            mark_dirty=True,
        )

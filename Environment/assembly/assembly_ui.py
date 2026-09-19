import copy
import tkinter as tk
from tkinter import messagebox

from Environment.assembly.controller.assembly_controller import AssemblyControllerMixin
from Operations.task_runner import materialize_system_task


class AssemblyTabMixin(AssemblyControllerMixin):
    """
    Top-level Assembly tab UI.

    This file stays as the public entry point for the Assembly tab.
    Deeper editor behavior lives under Environment/assembly/controller,
    Environment/assembly/tabs, Environment/assembly/packages,
    Environment/assembly/state, and Environment/assembly/widgets.
    """

    def _build_assembly_tab(self) -> None:
        top_row = tk.Frame(self.assembly_tab)
        top_row.pack(fill="x", pady=(0, 12))

        tk.Label(top_row, text="Agent Name").pack(side="left")

        self.assembly_name_entry = tk.Entry(top_row, font=("Segoe UI", 11))
        self.assembly_name_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))

        button_row = tk.Frame(self.assembly_tab)
        button_row.pack(fill="x", pady=(0, 12))

        tk.Button(
            button_row,
            text="Create New Agent",
            width=18,
            command=self._handle_create_new_assembly,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            button_row,
            text="Save Agent",
            width=14,
            command=self._handle_save_assembly,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            button_row,
            text="Open Agent",
            width=14,
            command=self._handle_edit_assembly,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            button_row,
            text="Delete Agent",
            width=14,
            command=self._handle_delete_assembly,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            button_row,
            text="Add Group",
            width=14,
            command=self._handle_add_task_group,
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            button_row,
            text="Delete Group",
            width=14,
            command=self._handle_delete_task_group,
        ).pack(side="right")

        self.tasks_tab = tk.Frame(self.assembly_tab, padx=8, pady=8)
        self.tasks_tab.pack(fill="both", expand=True, pady=(0, 8))

        self._build_tasks_area(self.tasks_tab)

        self.assembly_status_label = tk.Label(
            self.assembly_tab,
            text="",
            anchor="w",
            fg="gray25",
        )
        self.assembly_status_label.pack(fill="x", pady=(12, 0))

    def _set_assembly_status(self, text: str) -> None:
        self.assembly_status_label.config(text=text)

    def _get_parent_name(self) -> str:
        return self.assembly_name_entry.get().strip()

    def _has_dirty_editor_state(self) -> bool:
        agent_defaults = getattr(self, "agent_defaults_tab_info", None)
        if isinstance(agent_defaults, dict) and bool(agent_defaults.get("dirty", False)):
            return True

        for group_info in getattr(self, "task_group_tabs", []):
            if isinstance(group_info, dict) and bool(group_info.get("dirty", False)):
                return True

        for tab_info in getattr(self, "assembly_tabs", []):
            if isinstance(tab_info, dict) and bool(tab_info.get("dirty", False)):
                return True

        return False

    def _prompt_before_agent_context_change(self) -> bool:
        if not self._has_dirty_editor_state():
            return True

        result = messagebox.askyesnocancel(
            "Unsaved Edits",
            "This agent has unsaved edits. Save before switching agents?",
        )

        if result is None:
            return False

        if result is True:
            self._handle_save_assembly()
            return not self._has_dirty_editor_state()

        return True

    def _mark_all_editor_state_clean(self) -> None:
        agent_defaults = getattr(self, "agent_defaults_tab_info", None)
        if isinstance(agent_defaults, dict):
            agent_defaults["dirty"] = False

        for group_info in getattr(self, "task_group_tabs", []):
            if isinstance(group_info, dict):
                group_info["dirty"] = False

        for tab_info in getattr(self, "assembly_tabs", []):
            if isinstance(tab_info, dict):
                tab_info["dirty"] = False

    def _get_all_tasks_from_agent_payload(self, agent_payload: object) -> list[dict]:
        if not isinstance(agent_payload, dict):
            return []

        raw_groups = agent_payload.get("groups", [])
        if not isinstance(raw_groups, list):
            return []

        tasks: list[dict] = []
        seen_task_names: set[str] = set()

        for group in raw_groups:
            if not isinstance(group, dict):
                continue

            raw_tasks = group.get("tasks", [])
            if not isinstance(raw_tasks, list):
                continue

            for task in raw_tasks:
                if not isinstance(task, dict):
                    continue

                task_name = str(task.get("name", "")).strip()
                if not task_name:
                    continue

                if task_name in seen_task_names:
                    continue

                tasks.append(task)
                seen_task_names.add(task_name)

        return tasks

    def _handle_create_new_assembly(self) -> None:
        if not self._prompt_before_agent_context_change():
            return

        self.current_parent_name = None
        self.assembly_name_entry.delete(0, tk.END)
        self._reset_tasks_area()
        self._mark_all_editor_state_clean()
        self._set_assembly_status("New agent form ready.")

    def _handle_save_assembly(self) -> None:
        parent_name = self._get_parent_name()
        if not parent_name:
            messagebox.showerror("Save Failed", "Agent name is required.")
            return

        try:
            pending_memory_file_deletions = self._collect_pending_memory_file_deletions()
            agent_payload = self._collect_tasks()
        except Exception as e:
            messagebox.showerror("Save Failed", str(e))
            return

        if not isinstance(agent_payload, dict):
            messagebox.showerror(
                "Save Failed",
                "_collect_tasks() must return the canonical agent payload dict.",
            )
            return

        agent_payload = copy.deepcopy(agent_payload)
        agent_payload["name"] = str(agent_payload.get("name", "") or parent_name).strip()

        try:
            saved_path = self.assembly_manager.save_agent(
                agent_name=parent_name,
                agent_payload=agent_payload,
            )
        except Exception as e:
            messagebox.showerror("Save Failed", str(e))
            return

        deleted_memory_files: list[str] = []

        if pending_memory_file_deletions:
            try:
                deleted_memory_files = self.assembly_manager.memory_file_manager.delete_memory_files(
                    pending_memory_file_deletions
                )
                self._clear_pending_memory_file_deletions()
            except Exception as e:
                self._set_assembly_status(
                    f"Saved: {saved_path} | Memory file cleanup failed: {e}"
                )
                messagebox.showerror(
                    "Memory File Cleanup Failed",
                    (
                        "Agent was saved successfully, but one or more staged "
                        "memory files could not be deleted.\n\n"
                        f"{e}"
                    ),
                )
                return

        clean_name = self.assembly_manager.sanitize_name(parent_name)
        self.current_parent_name = clean_name
        self.assembly_name_entry.delete(0, tk.END)
        self.assembly_name_entry.insert(0, clean_name)

        self._mark_all_editor_state_clean()

        materialized_task_names: list[str] = []

        try:
            manager_handoff = self.assembly_manager.handoff

            for task_data in self._get_all_tasks_from_agent_payload(agent_payload):
                task_name = str(task_data.get("name", "")).strip()
                task_status = str(task_data.get("task_status", "On Demand")).strip() or "On Demand"

                if not task_name or task_status != "System":
                    continue

                materialize_system_task(
                    base_dir=manager_handoff.get_base_dir(),
                    agent_name=clean_name,
                    task_name=task_name,
                    handoff=manager_handoff,
                )
                materialized_task_names.append(task_name)

        except Exception as e:
            self._set_assembly_status(
                f"Saved: {saved_path} | System task materialization failed: {e}"
            )
            messagebox.showerror(
                "System Task Materialization Failed",
                f"Agent was saved successfully, but system task materialization failed.\n\n{e}",
            )
            return

        status_parts = [f"Saved: {saved_path}"]

        if deleted_memory_files:
            status_parts.append(f"Deleted memory files: {len(deleted_memory_files)}")

        if materialized_task_names:
            materialized_display = ", ".join(materialized_task_names)
            status_parts.append(f"Materialized system tasks: {materialized_display}")

            self._set_assembly_status(" | ".join(status_parts))
            messagebox.showinfo(
                "Saved",
                (
                    f"Agent saved successfully:\n\n{saved_path}\n\n"
                    f"Materialized system tasks:\n{materialized_display}"
                ),
            )
            return

        self._set_assembly_status(" | ".join(status_parts))

        if deleted_memory_files:
            messagebox.showinfo(
                "Saved",
                (
                    f"Agent saved successfully:\n\n{saved_path}\n\n"
                    f"Deleted staged memory files: {len(deleted_memory_files)}"
                ),
            )
            return

        messagebox.showinfo("Saved", f"Agent saved successfully:\n\n{saved_path}")

    def _handle_edit_assembly(self) -> None:
        try:
            agent_names = self._get_agent_lookup_options()
        except Exception as e:
            messagebox.showerror("Open Failed", str(e))
            return

        if not agent_names:
            messagebox.showinfo("No Agents", "There are no saved agents yet.")
            return

        self._open_item_picker(
            title_text="Agent",
            item_names=agent_names,
            on_select=self._load_selected_assembly,
        )

    def _load_selected_assembly(self, parent_name: str) -> None:
        if not self._prompt_before_agent_context_change():
            return

        try:
            agent_payload = self.assembly_manager.load_agent_data(parent_name)
        except Exception as e:
            messagebox.showerror("Load Failed", str(e))
            return

        clean_parent_name = self.assembly_manager.sanitize_name(parent_name)

        self.current_parent_name = clean_parent_name
        self.assembly_name_entry.delete(0, tk.END)
        self.assembly_name_entry.insert(0, agent_payload.get("name", clean_parent_name))

        groups = agent_payload.get("groups", [])
        if not isinstance(groups, list):
            messagebox.showerror("Load Failed", "Agent payload field 'groups' must be a list.")
            return

        self._load_task_groups_into_tabs(groups)
        self._load_agent_defaults_into_tab(agent_payload.get("default_returns", []))

        self._mark_all_editor_state_clean()
        self._set_assembly_status(f"Loaded agent: {clean_parent_name}")

    def _handle_delete_assembly(self) -> None:
        parent_name = self._get_parent_name()

        if not parent_name:
            messagebox.showerror("No Agent", "Enter or load an agent name first.")
            return

        confirmed = messagebox.askyesno(
            "Delete Agent",
            f"Are you sure you want to delete '{parent_name}'?",
        )
        if not confirmed:
            return

        try:
            deleted_path = self.assembly_manager.delete_agent(parent_name)
        except Exception as e:
            messagebox.showerror("Delete Failed", str(e))
            return

        self.current_parent_name = None
        self.assembly_name_entry.delete(0, tk.END)
        self._reset_tasks_area()
        self._mark_all_editor_state_clean()

        self._set_assembly_status(f"Deleted: {deleted_path}")
        messagebox.showinfo("Deleted", f"Deleted agent:\n\n{deleted_path}")
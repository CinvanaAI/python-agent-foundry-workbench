from __future__ import annotations

import copy
import tkinter as tk
from tkinter import messagebox, ttk


class DirtyControllerMixin:
    """
    Dirty-state and save-before-switch controller for the Assembly editor.

    Owns:
        - generic tab dirty marking
        - task dirty tracking bindings
        - save/discard prompt before switching context
        - clearing/resetting the task/group editor area
        - restoring dirty task tabs from loaded snapshots

    Does not own:
        - package-specific mutation logic
        - tab rendering
        - backend persistence
        - canonical schema validation
    """

    def _mark_tab_dirty(self, tab_info: dict | None) -> None:
        if not isinstance(tab_info, dict):
            return

        tab_info["dirty"] = True

    def _bind_dirty_tracking_for_widget(
        self,
        tab_info: dict,
        widget: tk.Widget | None,
    ) -> None:
        """
        Bind dirty tracking to a widget subtree.

        Important:
            Dynamic tabs can be created after the first full task-tab bind.
            Parent frames may already be marked as bound, so this method must
            still recurse into children even when the current widget was already
            processed earlier.
        """
        if not isinstance(tab_info, dict):
            return

        if widget is None:
            return

        def _mark_current_tab_dirty(_event=None, info=tab_info) -> None:
            self._mark_tab_dirty(info)

        def _bind_recursive(current_widget: tk.Widget) -> None:
            already_bound = bool(getattr(current_widget, "_assembly_dirty_bound", False))

            if not already_bound:
                if isinstance(current_widget, tk.Entry):
                    current_widget.bind("<KeyRelease>", _mark_current_tab_dirty, add="+")
                    current_widget.bind("<FocusOut>", _mark_current_tab_dirty, add="+")

                elif isinstance(current_widget, tk.Text):
                    current_widget.bind("<KeyRelease>", _mark_current_tab_dirty, add="+")
                    current_widget.bind("<FocusOut>", _mark_current_tab_dirty, add="+")

                elif isinstance(current_widget, ttk.Combobox):
                    current_widget.bind(
                        "<<ComboboxSelected>>",
                        _mark_current_tab_dirty,
                        add="+",
                    )

                elif isinstance(current_widget, tk.Checkbutton):
                    current_widget.bind(
                        "<ButtonRelease-1>",
                        lambda event, info=tab_info, bound_widget=current_widget: bound_widget.after_idle(
                            lambda: self._mark_tab_dirty(info)
                        ),
                        add="+",
                    )

                current_widget._assembly_dirty_bound = True

            for child in current_widget.winfo_children():
                _bind_recursive(child)

        _bind_recursive(widget)

    def _bind_dirty_tracking_for_task_tab(self, tab_info: dict) -> None:
        if not isinstance(tab_info, dict):
            return

        frame = tab_info.get("frame")
        if frame is None:
            return

        self._bind_dirty_tracking_for_widget(tab_info, frame)

    def _get_safely_current_task_or_none(self) -> dict | None:
        try:
            return self._get_current_task_tab_info()
        except Exception:
            return None

    def _clear_all_task_tabs(self) -> None:
        for group_info in list(getattr(self, "task_group_tabs", [])):
            for tab_info in list(group_info.get("task_tabs", [])):
                try:
                    group_info["task_notebook"].forget(tab_info["frame"])
                except Exception:
                    pass

                try:
                    tab_info["frame"].destroy()
                except Exception:
                    pass

        if hasattr(self, "task_group_notebook"):
            for group_info in list(getattr(self, "task_group_tabs", [])):
                try:
                    self.task_group_notebook.forget(group_info["frame"])
                except Exception:
                    pass

                try:
                    group_info["frame"].destroy()
                except Exception:
                    pass

        self.assembly_tabs = []
        self.task_group_tabs = []
        self.task_group_tab_by_name = {}
        self._last_selected_group_frame = None
        self._last_selected_task_frame_by_group = {}

    def _reset_tasks_area(self) -> None:
        self._clear_all_task_tabs()

        if isinstance(getattr(self, "agent_defaults_tab_info", None), dict):
            self.agent_defaults_tab_info["default_return_rows"] = []
            self.agent_defaults_tab_info["dirty"] = False

            if hasattr(self, "_refresh_defaults_panel"):
                self._refresh_defaults_panel(self.agent_defaults_tab_info)

        outcasts_group = self._create_task_group_tab(
            self._get_outcasts_task_group_name(),
            select=True,
        )

        self._create_new_task_tab(group_info=outcasts_group)

    def _prompt_to_save_dirty_current_task_before_group_switch(self) -> bool:
        current_tab_info = self._get_safely_current_task_or_none()

        if current_tab_info is None:
            return True

        if not bool(current_tab_info.get("dirty", False)):
            return True

        result = messagebox.askyesnocancel(
            "Unsaved Edits",
            "Unsaved edits in the current task. Save before switching groups?",
        )

        if result is None:
            return False

        if result is True:
            try:
                saved_task = self._collect_single_task_from_tab(current_tab_info)
                current_tab_info["loaded_snapshot"] = copy.deepcopy(saved_task)
                current_tab_info["dirty"] = False
                return True
            except Exception as exc:
                messagebox.showerror("Save Failed", str(exc))
                return False

        self._discard_task_tab_changes(current_tab_info)
        return True

    def _prompt_to_save_dirty_current_task_before_switch(self) -> bool:
        return self._prompt_to_save_dirty_current_task_before_group_switch()

    def _discard_task_tab_changes(self, tab_info: dict) -> None:
        snapshot = tab_info.get("loaded_snapshot")

        if not isinstance(snapshot, dict):
            tab_info["dirty"] = False
            return

        group_info = tab_info.get("group_info")

        if group_info is None:
            tab_info["dirty"] = False
            return

        group_was_dirty = bool(group_info.get("dirty", False))

        try:
            frame_index = group_info["task_tabs"].index(tab_info)
        except Exception:
            frame_index = None

        selected = False
        try:
            selected = group_info["task_notebook"].select() == str(tab_info["frame"])
        except Exception:
            selected = False

        self._remove_task_tab_from_group(
            tab_info,
            group_info,
            destroy_frame=True,
        )

        replacement = self._create_task_tab_from_snapshot(
            snapshot=snapshot,
            group_info=group_info,
            task_name=str(snapshot.get("name", "")).strip() or "Task",
            select=selected,
            insert_index=frame_index,
            mark_dirty=False,
        )

        replacement["dirty"] = False
        replacement["loaded_snapshot"] = copy.deepcopy(snapshot)
        group_info["dirty"] = group_was_dirty
from __future__ import annotations


class SelectionControllerMixin:
    """
    Assembly-specific notebook selection and order synchronization.

    This file owns behavior that depends on Assembly UI state:
        - save-before-switch guard
        - selected group/task frame tracking
        - group order synchronization
        - task order synchronization inside a group
        - keeping Outcasts pinned as the first real group
    """

    def _handle_task_group_notebook_changed(self, event=None) -> None:
        if self._task_ui_switch_guard:
            return

        current_tab_id = self.task_group_notebook.select()
        if not current_tab_id:
            return

        current_frame = self.root.nametowidget(current_tab_id)
        previous_frame = self._last_selected_group_frame

        if previous_frame is not None and previous_frame != current_frame:
            if not self._prompt_to_save_dirty_current_task_before_group_switch():
                self._task_ui_switch_guard = True
                try:
                    self.task_group_notebook.select(previous_frame)
                finally:
                    self._task_ui_switch_guard = False
                return

        self._last_selected_group_frame = current_frame

    def _handle_group_task_notebook_changed(self, event, group_info: dict) -> None:
        if self._task_ui_switch_guard:
            return

        task_notebook = group_info["task_notebook"]
        current_tab_id = task_notebook.select()

        if not current_tab_id:
            return

        current_frame = self.root.nametowidget(current_tab_id)
        self._last_selected_task_frame_by_group[id(group_info)] = current_frame

    def _sync_group_order_from_notebook(self) -> None:
        if not hasattr(self, "task_group_notebook"):
            return

        frame_order = [
            self.root.nametowidget(tab_id)
            for tab_id in self.task_group_notebook.tabs()
        ]

        rebuilt: list[dict] = []

        for frame in frame_order:
            if self._is_agent_defaults_frame(frame):
                continue

            for group_info in self.task_group_tabs:
                if group_info["frame"] == frame and group_info not in rebuilt:
                    rebuilt.append(group_info)
                    break

        self.task_group_tabs = rebuilt

        outcasts_name = self._get_outcasts_task_group_name()

        if self.task_group_tabs and self.task_group_tabs[0]["name"] != outcasts_name:
            outcasts_group = self.task_group_tab_by_name.get(outcasts_name)

            if outcasts_group is not None and outcasts_group in self.task_group_tabs:
                self.task_group_tabs.remove(outcasts_group)
                self.task_group_tabs.insert(0, outcasts_group)

                try:
                    # Index 0 is the Agent Defaults tab, so Outcasts should sit at 1.
                    self.task_group_notebook.insert(1, outcasts_group["frame"])
                except Exception:
                    pass

    def _sync_task_order_from_notebook(self, group_info: dict) -> None:
        task_notebook = group_info["task_notebook"]

        frame_order = [
            self.root.nametowidget(tab_id)
            for tab_id in task_notebook.tabs()
        ]

        rebuilt: list[dict] = []

        for frame in frame_order:
            if self._is_group_defaults_frame(group_info, frame):
                continue

            for tab_info in group_info.get("task_tabs", []):
                if tab_info["frame"] == frame and tab_info not in rebuilt:
                    rebuilt.append(tab_info)
                    break

        group_info["task_tabs"] = rebuilt
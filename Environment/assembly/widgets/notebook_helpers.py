from __future__ import annotations

from tkinter import ttk


class NotebookHelpersMixin:
    """
    Generic Tkinter notebook helpers.

    This file should stay reusable. It should not know about agents, groups,
    tasks, dirty state, Outcasts, package data, or the canonical agent schema.
    """

    def _bind_reorderable_notebook_tabs(
        self,
        notebook: ttk.Notebook,
        reorder_callback,
        pinned_first: bool = False,
    ) -> None:
        state = {
            "pressed_index": None,
        }

        def _on_press(event):
            try:
                index = notebook.index(f"@{event.x},{event.y}")
            except Exception:
                state["pressed_index"] = None
                return

            if pinned_first and index == 0:
                state["pressed_index"] = None
                return

            state["pressed_index"] = index

        def _on_release(event):
            start_index = state.get("pressed_index")
            state["pressed_index"] = None

            if start_index is None:
                return

            try:
                end_index = notebook.index(f"@{event.x},{event.y}")
            except Exception:
                return

            if pinned_first and end_index == 0:
                end_index = 1

            if start_index == end_index:
                return

            tabs = list(notebook.tabs())

            if start_index < 0 or start_index >= len(tabs):
                return

            if end_index < 0 or end_index >= len(tabs):
                return

            tab_id = tabs[start_index]
            notebook.insert(end_index, tab_id)
            reorder_callback()

        notebook.bind("<ButtonPress-1>", _on_press, add="+")
        notebook.bind("<ButtonRelease-1>", _on_release, add="+")
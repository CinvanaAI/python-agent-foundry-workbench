import tkinter as tk
from tkinter import ttk


class TriggersTabMixin:
    """
    Triggers tab UI.

    Owns:
        - building the Triggers tab
        - loading trigger text into the UI
        - collecting trigger text from the UI

    Does not own:
        - friendship trigger stamp generation
        - reverse friendship stamp updates
        - backend task persistence
    """

    def _build_triggers_tab(
        self,
        inner_notebook: ttk.Notebook,
        tab_info: dict,
    ) -> None:
        triggers_tab = tk.Frame(inner_notebook, padx=8, pady=8)
        inner_notebook.add(triggers_tab, text="Triggers")

        triggers_label = tk.Label(triggers_tab, text="Triggers")
        triggers_label.pack(anchor="w", padx=4, pady=(4, 0))

        triggers_frame = tk.Frame(triggers_tab, padx=4, pady=4)
        triggers_frame.pack(fill="both", expand=True)

        triggers_text = tk.Text(
            triggers_frame,
            wrap="none",
            undo=True,
            font=("Consolas", 11),
            height=12,
        )
        triggers_text.pack(side="left", fill="both", expand=True)

        triggers_y_scroll = tk.Scrollbar(
            triggers_frame,
            orient="vertical",
            command=triggers_text.yview,
        )
        triggers_y_scroll.pack(side="right", fill="y")
        triggers_text.configure(yscrollcommand=triggers_y_scroll.set)

        triggers_x_scroll_frame = tk.Frame(triggers_tab, padx=4)
        triggers_x_scroll_frame.pack(fill="x", pady=(0, 4))

        triggers_x_scroll = tk.Scrollbar(
            triggers_x_scroll_frame,
            orient="horizontal",
            command=triggers_text.xview,
        )
        triggers_x_scroll.pack(fill="x")
        triggers_text.configure(xscrollcommand=triggers_x_scroll.set)

        tab_info["triggers_tab"] = triggers_tab
        tab_info["triggers_text"] = triggers_text

    def _load_triggers_into_tab(
        self,
        tab_info: dict,
        triggers_source: str,
    ) -> None:
        triggers_text = tab_info["triggers_text"]
        triggers_text.delete("1.0", tk.END)
        triggers_text.insert("1.0", str(triggers_source or ""))

    def _collect_triggers_from_tab(self, tab_info: dict) -> str:
        return tab_info["triggers_text"].get("1.0", "end-1c").rstrip()
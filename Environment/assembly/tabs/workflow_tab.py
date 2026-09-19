import tkinter as tk
from tkinter import ttk


class WorkflowTabMixin:
    """
    Workflow tab UI.

    Owns:
        - building the Workflow tab
        - loading workflow_source into the workflow text box
        - collecting workflow_source from the workflow text box

    Does not own:
        - saving to disk
        - canonical task payload construction
        - backend workflow validation
    """

    def _build_workflow_tab(
        self,
        inner_notebook: ttk.Notebook,
        tab_info: dict,
    ) -> None:
        workflow_tab = tk.Frame(inner_notebook, padx=8, pady=8)
        inner_notebook.add(workflow_tab, text="Workflow")

        workflow_label = tk.Label(workflow_tab, text="Workflow")
        workflow_label.pack(anchor="w", padx=4, pady=(4, 0))

        workflow_frame = tk.Frame(workflow_tab, padx=4, pady=4)
        workflow_frame.pack(fill="both", expand=True)

        workflow_text = tk.Text(
            workflow_frame,
            wrap="none",
            undo=True,
            font=("Consolas", 11),
            height=12,
        )
        workflow_text.pack(side="left", fill="both", expand=True)

        workflow_y_scroll = tk.Scrollbar(
            workflow_frame,
            orient="vertical",
            command=workflow_text.yview,
        )
        workflow_y_scroll.pack(side="right", fill="y")
        workflow_text.configure(yscrollcommand=workflow_y_scroll.set)

        workflow_x_scroll_frame = tk.Frame(workflow_tab, padx=4)
        workflow_x_scroll_frame.pack(fill="x", pady=(0, 4))

        workflow_x_scroll = tk.Scrollbar(
            workflow_x_scroll_frame,
            orient="horizontal",
            command=workflow_text.xview,
        )
        workflow_x_scroll.pack(fill="x")
        workflow_text.configure(xscrollcommand=workflow_x_scroll.set)

        tab_info["workflow_tab"] = workflow_tab
        tab_info["workflow_text"] = workflow_text

    def _load_workflow_into_tab(
        self,
        tab_info: dict,
        workflow_source: str,
    ) -> None:
        workflow_text = tab_info["workflow_text"]
        workflow_text.delete("1.0", tk.END)
        workflow_text.insert("1.0", str(workflow_source or ""))

    def _collect_workflow_from_tab(self, tab_info: dict) -> str:
        return tab_info["workflow_text"].get("1.0", "end-1c")
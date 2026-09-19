import tkinter as tk
from tkinter import messagebox, ttk


class PromptsTabMixin:
    """
    Prompts tab UI.

    Owns:
        - building the Prompts tab
        - adding/removing prompt tabs
        - loading prompt entries into the UI
        - collecting prompt entries from the UI

    Does not own:
        - saving to disk
        - canonical task payload construction
        - backend prompt validation
    """

    def _build_prompts_tab(
        self,
        inner_notebook: ttk.Notebook,
        tab_info: dict,
    ) -> None:
        prompts_tab = tk.Frame(inner_notebook, padx=8, pady=8)
        inner_notebook.add(prompts_tab, text="Prompts")

        controls_row = tk.Frame(prompts_tab)
        controls_row.pack(fill="x", pady=(0, 8))

        tk.Button(
            controls_row,
            text="Add Prompt",
            width=12,
            command=lambda: self._handle_add_prompt_tab(tab_info),
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            controls_row,
            text="Delete Prompt",
            width=12,
            command=lambda: self._handle_delete_prompt_tab(tab_info),
        ).pack(side="right")

        prompts_body = tk.Frame(prompts_tab)
        prompts_body.pack(fill="both", expand=True)

        prompts_notebook = ttk.Notebook(prompts_body)
        prompts_notebook.pack(fill="both", expand=True)

        empty_frame = tk.Frame(prompts_body, padx=24, pady=24)

        empty_label = tk.Label(
            empty_frame,
            text="No prompts yet.",
            font=("Segoe UI", 12, "bold"),
            fg="gray30",
        )
        empty_label.pack(pady=(0, 12))

        tk.Button(
            empty_frame,
            text="Create First Prompt",
            width=22,
            command=lambda: self._handle_add_prompt_tab(tab_info),
        ).pack()

        tab_info["prompts_tab"] = prompts_tab
        tab_info["prompts_body"] = prompts_body
        tab_info["prompts_notebook"] = prompts_notebook
        tab_info["prompts_empty_frame"] = empty_frame
        tab_info["prompt_tabs"] = []

        self._refresh_prompts_empty_state(tab_info)

    def _refresh_prompts_empty_state(self, tab_info: dict) -> None:
        prompts_notebook = tab_info.get("prompts_notebook")
        empty_frame = tab_info.get("prompts_empty_frame")
        prompt_tabs = tab_info.get("prompt_tabs", [])

        if prompts_notebook is None or empty_frame is None:
            return

        if prompt_tabs:
            empty_frame.pack_forget()
            prompts_notebook.pack(fill="both", expand=True)
            return

        prompts_notebook.pack_forget()
        empty_frame.pack(fill="both", expand=True)

    def _create_prompt_tab_widgets(
        self,
        prompts_notebook: ttk.Notebook,
        default_name: str,
    ) -> dict:
        prompt_frame = tk.Frame(prompts_notebook, padx=10, pady=10)

        name_row = tk.Frame(prompt_frame)
        name_row.pack(fill="x", pady=(0, 10))

        tk.Label(name_row, text="Prompt Name").pack(side="left")

        prompt_name_entry = tk.Entry(name_row, font=("Segoe UI", 11))
        prompt_name_entry.pack(side="left", fill="x", expand=True, padx=(8, 0))
        prompt_name_entry.insert(0, default_name)

        prompt_label = tk.Label(prompt_frame, text="Prompt")
        prompt_label.pack(anchor="w", padx=4, pady=(4, 0))

        prompt_text_frame = tk.Frame(prompt_frame, padx=4, pady=4)
        prompt_text_frame.pack(fill="both", expand=True)

        prompt_text = tk.Text(
            prompt_text_frame,
            wrap="none",
            undo=True,
            font=("Consolas", 11),
            height=12,
        )
        prompt_text.pack(side="left", fill="both", expand=True)

        prompt_y_scroll = tk.Scrollbar(
            prompt_text_frame,
            orient="vertical",
            command=prompt_text.yview,
        )
        prompt_y_scroll.pack(side="right", fill="y")
        prompt_text.configure(yscrollcommand=prompt_y_scroll.set)

        prompt_x_scroll_frame = tk.Frame(prompt_frame, padx=4)
        prompt_x_scroll_frame.pack(fill="x", pady=(0, 4))

        prompt_x_scroll = tk.Scrollbar(
            prompt_x_scroll_frame,
            orient="horizontal",
            command=prompt_text.xview,
        )
        prompt_x_scroll.pack(fill="x")
        prompt_text.configure(xscrollcommand=prompt_x_scroll.set)

        return {
            "frame": prompt_frame,
            "prompt_name_entry": prompt_name_entry,
            "prompt_text": prompt_text,
        }

    def _create_new_prompt_tab(
        self,
        tab_info: dict,
        name: str | None = None,
        prompt_source: str = "",
        bind_dirty: bool = True,
        select: bool = True,
    ) -> dict:
        prompts_notebook = tab_info["prompts_notebook"]
        prompt_tabs = tab_info["prompt_tabs"]

        if name is None:
            name = f"Prompt {len(prompt_tabs) + 1}"

        prompt_info = self._create_prompt_tab_widgets(prompts_notebook, name)

        prompts_notebook.add(prompt_info["frame"], text=name)
        prompt_tabs.append(prompt_info)

        prompt_info["prompt_text"].delete("1.0", tk.END)
        prompt_info["prompt_text"].insert("1.0", str(prompt_source or ""))

        prompt_info["prompt_name_entry"].bind(
            "<KeyRelease>",
            lambda event, info=prompt_info, notebook=prompts_notebook: self._sync_prompt_tab_title(
                info,
                notebook,
            ),
            add="+",
        )

        if bind_dirty and hasattr(self, "_bind_dirty_tracking_for_widget"):
            self._bind_dirty_tracking_for_widget(tab_info, prompt_info["frame"])

        self._refresh_prompts_empty_state(tab_info)

        if select:
            prompts_notebook.select(prompt_info["frame"])

        return prompt_info

    def _sync_prompt_tab_title(
        self,
        prompt_info: dict,
        prompts_notebook: ttk.Notebook,
    ) -> None:
        title = prompt_info["prompt_name_entry"].get().strip() or "Untitled"
        prompts_notebook.tab(prompt_info["frame"], text=title)

    def _get_current_prompt_tab_info(self, tab_info: dict) -> dict:
        prompts_notebook = tab_info["prompts_notebook"]
        current_tab_id = prompts_notebook.select()

        if not current_tab_id:
            raise ValueError("No prompt is selected.")

        current_frame = self.root.nametowidget(current_tab_id)

        for prompt_info in tab_info["prompt_tabs"]:
            if prompt_info["frame"] == current_frame:
                return prompt_info

        raise ValueError("Could not find selected prompt.")

    def _handle_add_prompt_tab(self, tab_info: dict) -> None:
        self._create_new_prompt_tab(tab_info, bind_dirty=True, select=True)
        self._mark_tab_dirty(tab_info)

    def _handle_delete_prompt_tab(self, tab_info: dict) -> None:
        prompt_tabs = tab_info.get("prompt_tabs", [])

        if not prompt_tabs:
            messagebox.showerror("No Prompt", "There are no prompts to delete.")
            return

        try:
            prompt_info = self._get_current_prompt_tab_info(tab_info)
        except Exception as e:
            messagebox.showerror("Delete Prompt Failed", str(e))
            return

        prompt_name = prompt_info["prompt_name_entry"].get().strip() or "Untitled"

        confirmed = messagebox.askyesno(
            "Delete Prompt",
            f"Are you sure you want to delete prompt '{prompt_name}'?",
        )

        if not confirmed:
            return

        prompts_notebook = tab_info["prompts_notebook"]
        prompts_notebook.forget(prompt_info["frame"])
        prompt_tabs.remove(prompt_info)

        self._refresh_prompts_empty_state(tab_info)
        self._mark_tab_dirty(tab_info)

    def _collect_prompts_from_tab(self, tab_info: dict) -> list[dict]:
        collected_prompts: list[dict] = []

        for prompt_info in tab_info.get("prompt_tabs", []):
            prompt_name = prompt_info["prompt_name_entry"].get().strip()
            prompt_source = prompt_info["prompt_text"].get("1.0", "end-1c")

            if not prompt_name and not prompt_source:
                continue

            collected_prompts.append(
                {
                    "name": prompt_name or f"Prompt {len(collected_prompts) + 1}",
                    "prompt_source": prompt_source,
                }
            )

        return collected_prompts

    def _load_prompts_into_tab(self, tab_info: dict, prompts: object) -> None:
        prompts_notebook = tab_info["prompts_notebook"]

        for prompt_info in tab_info.get("prompt_tabs", []):
            prompts_notebook.forget(prompt_info["frame"])

        tab_info["prompt_tabs"] = []

        if prompts in (None, ""):
            prompts = []

        if not isinstance(prompts, list):
            raise ValueError("Saved prompts must be a list.")

        for prompt_entry in prompts:
            if not isinstance(prompt_entry, dict):
                continue

            self._create_new_prompt_tab(
                tab_info=tab_info,
                name=str(prompt_entry.get("name", "")).strip()
                or f"Prompt {len(tab_info['prompt_tabs']) + 1}",
                prompt_source=str(prompt_entry.get("prompt_source", "")),
                bind_dirty=False,
                select=False,
            )

        self._refresh_prompts_empty_state(tab_info)

        if tab_info["prompt_tabs"]:
            prompts_notebook.select(tab_info["prompt_tabs"][0]["frame"])
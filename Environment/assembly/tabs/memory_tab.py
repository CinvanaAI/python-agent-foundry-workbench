import tkinter as tk
from tkinter import messagebox, ttk


class MemoryTabMixin:
    """
    Memory tab UI.

    Owns:
        - building the Memory tab
        - adding/removing memory entries
        - loading memory entries into the UI
        - collecting memory entries from the UI
        - staging memory-file deletion for Save Agent

    Does not own:
        - memory file creation
        - memory file path migration
        - backend memory validation
    """

    def _build_memory_tab(
        self,
        inner_notebook: ttk.Notebook,
        tab_info: dict,
    ) -> None:
        memory_tab = tk.Frame(inner_notebook, padx=8, pady=8)
        inner_notebook.add(memory_tab, text="Memory")

        controls_row = tk.Frame(memory_tab)
        controls_row.pack(fill="x", pady=(0, 8))

        tk.Button(
            controls_row,
            text="Add Memory",
            width=12,
            command=lambda info=tab_info: self._handle_add_memory_tab(info),
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            controls_row,
            text="Delete Memory",
            width=12,
            command=lambda info=tab_info: self._handle_delete_memory_tab(info),
        ).pack(side="right")

        memory_body = tk.Frame(memory_tab)
        memory_body.pack(fill="both", expand=True)

        memory_notebook = ttk.Notebook(memory_body)
        memory_notebook.pack(fill="both", expand=True)

        empty_frame = tk.Frame(memory_body, padx=24, pady=24)

        empty_label = tk.Label(
            empty_frame,
            text="No memory entries yet.",
            font=("Segoe UI", 12, "bold"),
            fg="gray30",
        )
        empty_label.pack(pady=(0, 12))

        tk.Button(
            empty_frame,
            text="Create First Memory",
            width=22,
            command=lambda info=tab_info: self._handle_add_memory_tab(info),
        ).pack()

        tab_info["memory_tab"] = memory_tab
        tab_info["memory_body"] = memory_body
        tab_info["memory_notebook"] = memory_notebook
        tab_info["memory_empty_frame"] = empty_frame
        tab_info["memory_tabs"] = []
        tab_info.setdefault("pending_memory_file_deletions", [])

        self._refresh_memory_empty_state(tab_info)

    def _refresh_memory_empty_state(self, tab_info: dict) -> None:
        memory_notebook = tab_info.get("memory_notebook")
        empty_frame = tab_info.get("memory_empty_frame")
        memory_tabs = tab_info.get("memory_tabs", [])

        if memory_notebook is None or empty_frame is None:
            return

        if memory_tabs:
            empty_frame.pack_forget()
            memory_notebook.pack(fill="both", expand=True)
            return

        memory_notebook.pack_forget()
        empty_frame.pack(fill="both", expand=True)

    def _get_pending_memory_file_deletions(self, tab_info: dict) -> list[str]:
        pending = tab_info.setdefault("pending_memory_file_deletions", [])

        if not isinstance(pending, list):
            pending = []
            tab_info["pending_memory_file_deletions"] = pending

        return pending

    def _stage_memory_file_deletion(self, tab_info: dict, file_path: object) -> None:
        path_text = str(file_path or "").strip()
        if not path_text:
            return

        pending = self._get_pending_memory_file_deletions(tab_info)
        if path_text not in pending:
            pending.append(path_text)

    def _unstage_memory_file_deletion(self, tab_info: dict, file_path: object) -> None:
        path_text = str(file_path or "").strip()
        if not path_text:
            return

        pending = self._get_pending_memory_file_deletions(tab_info)
        while path_text in pending:
            pending.remove(path_text)

    def _create_single_memory_tab(
        self,
        tab_info: dict,
        name: str = "",
        content: str = "",
        file_path: str = "",
        has_file: bool = False,
        bind_dirty: bool = True,
        select: bool = True,
    ) -> dict:
        memory_notebook = tab_info["memory_notebook"]

        memory_frame = tk.Frame(memory_notebook, padx=8, pady=8)

        name_row = tk.Frame(memory_frame)
        name_row.pack(fill="x", pady=(0, 8))

        tk.Label(name_row, text="Memory Name").pack(side="left")

        memory_name_entry = tk.Entry(name_row, font=("Segoe UI", 11))
        memory_name_entry.pack(side="left", fill="x", expand=True, padx=(8, 0))
        memory_name_entry.insert(0, name or f"Memory {len(tab_info['memory_tabs']) + 1}")

        file_row = tk.Frame(memory_frame)
        file_row.pack(fill="x", pady=(0, 8))

        has_file_var = tk.BooleanVar(value=bool(has_file))

        has_file_check = tk.Checkbutton(
            file_row,
            text="Back this memory with a file",
            variable=has_file_var,
        )
        has_file_check.pack(side="left")

        file_path_label_var = tk.StringVar(value=str(file_path or "").strip())

        file_path_label = tk.Label(
            file_row,
            textvariable=file_path_label_var,
            anchor="w",
            justify="left",
            fg="gray40",
        )
        file_path_label.pack(side="left", fill="x", expand=True, padx=(12, 0))

        content_label = tk.Label(memory_frame, text="Content")
        content_label.pack(anchor="w", padx=4, pady=(4, 0))

        memory_text_frame = tk.Frame(memory_frame, padx=4, pady=4)
        memory_text_frame.pack(fill="both", expand=True)

        memory_text = tk.Text(
            memory_text_frame,
            wrap="none",
            undo=True,
            font=("Consolas", 11),
            height=12,
        )
        memory_text.pack(side="left", fill="both", expand=True)
        memory_text.insert("1.0", str(content or ""))

        memory_y_scroll = tk.Scrollbar(
            memory_text_frame,
            orient="vertical",
            command=memory_text.yview,
        )
        memory_y_scroll.pack(side="right", fill="y")
        memory_text.configure(yscrollcommand=memory_y_scroll.set)

        memory_x_scroll_frame = tk.Frame(memory_frame, padx=4)
        memory_x_scroll_frame.pack(fill="x", pady=(0, 4))

        memory_x_scroll = tk.Scrollbar(
            memory_x_scroll_frame,
            orient="horizontal",
            command=memory_text.xview,
        )
        memory_x_scroll.pack(fill="x")
        memory_text.configure(xscrollcommand=memory_x_scroll.set)

        memory_info = {
            "frame": memory_frame,
            "name_entry": memory_name_entry,
            "text": memory_text,
            "has_file_var": has_file_var,
            "has_file_check": has_file_check,
            "file_path": str(file_path or "").strip(),
            "file_path_label_var": file_path_label_var,
        }

        def _refresh_file_path_display() -> None:
            if bool(has_file_var.get()):
                current_path = str(memory_info.get("file_path", "") or "").strip()
                file_path_label_var.set(current_path or "File will be created on save.")
                file_path_label.configure(fg="gray40")
            else:
                file_path_label_var.set("No file backing.")
                file_path_label.configure(fg="gray50")

        def _handle_has_file_toggled() -> None:
            old_path = str(memory_info.get("file_path", "") or "").strip()

            if not bool(has_file_var.get()):
                if old_path:
                    confirmed = messagebox.askyesno(
                        "Remove Memory File",
                        (
                            "This memory entry currently has a file.\n\n"
                            "Unchecking this box will delete that file the next time "
                            "you save the agent.\n\nContinue?"
                        ),
                    )

                    if not confirmed:
                        has_file_var.set(True)
                        _refresh_file_path_display()
                        return

                    self._stage_memory_file_deletion(tab_info, old_path)

                memory_info["file_path"] = ""
                _refresh_file_path_display()
                self._mark_tab_dirty(tab_info)
                return

            self._unstage_memory_file_deletion(tab_info, old_path)
            _refresh_file_path_display()
            self._mark_tab_dirty(tab_info)

        has_file_check.configure(command=_handle_has_file_toggled)

        tab_info["memory_tabs"].append(memory_info)
        memory_notebook.add(
            memory_frame,
            text=memory_name_entry.get().strip() or "Untitled",
        )

        memory_name_entry.bind(
            "<KeyRelease>",
            lambda event, info=tab_info, mem_info=memory_info: self._sync_memory_tab_title(
                info,
                mem_info,
            ),
            add="+",
        )

        if bind_dirty and hasattr(self, "_bind_dirty_tracking_for_widget"):
            self._bind_dirty_tracking_for_widget(tab_info, memory_frame)

        _refresh_file_path_display()
        self._refresh_memory_empty_state(tab_info)

        if select:
            memory_notebook.select(memory_frame)

        return memory_info

    def _sync_memory_tab_title(self, tab_info: dict, memory_info: dict) -> None:
        memory_notebook = tab_info["memory_notebook"]
        title = memory_info["name_entry"].get().strip() or "Untitled"
        memory_notebook.tab(memory_info["frame"], text=title)

    def _get_current_memory_tab_info(self, tab_info: dict) -> dict:
        memory_notebook = tab_info["memory_notebook"]
        current_tab_id = memory_notebook.select()

        if not current_tab_id:
            raise ValueError("No memory tab is selected.")

        current_frame = self.root.nametowidget(current_tab_id)

        for memory_info in tab_info["memory_tabs"]:
            if memory_info["frame"] == current_frame:
                return memory_info

        raise ValueError("Could not find selected memory tab.")

    def _handle_add_memory_tab(self, tab_info: dict) -> None:
        memory_info = self._create_single_memory_tab(
            tab_info,
            name=f"Memory {len(tab_info['memory_tabs']) + 1}",
            content="",
            file_path="",
            has_file=False,
            bind_dirty=True,
            select=True,
        )
        tab_info["memory_notebook"].select(memory_info["frame"])
        self._mark_tab_dirty(tab_info)

    def _handle_delete_memory_tab(self, tab_info: dict) -> None:
        memory_tabs = tab_info.get("memory_tabs", [])

        if not memory_tabs:
            messagebox.showerror("No Memory", "There are no memory tabs to delete.")
            return

        try:
            memory_info = self._get_current_memory_tab_info(tab_info)
        except Exception as e:
            messagebox.showerror("Delete Memory Failed", str(e))
            return

        memory_name = memory_info["name_entry"].get().strip() or "Untitled"
        file_path = str(memory_info.get("file_path", "") or "").strip()
        has_file = bool(memory_info.get("has_file_var").get()) if memory_info.get("has_file_var") is not None else bool(file_path)

        if has_file and file_path:
            confirmed = messagebox.askyesno(
                "Delete Memory",
                (
                    f"Delete memory '{memory_name}'?\n\n"
                    "This memory entry has a file. Deleting this tab will delete "
                    "that file the next time you save the agent.\n\nContinue?"
                ),
            )
        else:
            confirmed = messagebox.askyesno(
                "Delete Memory",
                f"Are you sure you want to delete memory '{memory_name}'?",
            )

        if not confirmed:
            return

        if has_file and file_path:
            self._stage_memory_file_deletion(tab_info, file_path)

        tab_info["memory_notebook"].forget(memory_info["frame"])
        memory_tabs.remove(memory_info)

        self._refresh_memory_empty_state(tab_info)
        self._mark_tab_dirty(tab_info)

    def _collect_memory_from_tab(self, tab_info: dict) -> list[dict]:
        collected_memory: list[dict] = []

        for index, memory_info in enumerate(tab_info.get("memory_tabs", []), start=1):
            name = memory_info["name_entry"].get().strip() or f"Memory {index}"
            content = memory_info["text"].get("1.0", "end-1c")
            has_file_var = memory_info.get("has_file_var")
            has_file = bool(has_file_var.get()) if has_file_var is not None else False
            file_path = str(memory_info.get("file_path", "") or "").strip()

            collected_memory.append(
                {
                    "name": name,
                    "has_file": has_file,
                    "file_path": file_path if has_file else "",
                    "content": content,
                }
            )

        return collected_memory

    def _load_memory_into_tab(self, tab_info: dict, memory: object) -> None:
        memory_notebook = tab_info["memory_notebook"]

        for memory_info in tab_info.get("memory_tabs", []):
            memory_notebook.forget(memory_info["frame"])

        tab_info["memory_tabs"] = []
        tab_info["pending_memory_file_deletions"] = []

        if memory in (None, ""):
            memory = []

        if not isinstance(memory, list):
            raise ValueError("Saved memory must be a list.")

        for index, item in enumerate(memory, start=1):
            if not isinstance(item, dict):
                continue

            item_name = str(item.get("name", "")).strip() or f"Memory {index}"
            item_content = str(item.get("content", ""))
            item_file_path = str(item.get("file_path", "") or "").strip()
            item_has_file = bool(item.get("has_file", bool(item_file_path)))

            self._create_single_memory_tab(
                tab_info,
                name=item_name,
                content=item_content,
                file_path=item_file_path if item_has_file else "",
                has_file=item_has_file,
                bind_dirty=False,
                select=False,
            )

        self._refresh_memory_empty_state(tab_info)

        if tab_info["memory_tabs"]:
            memory_notebook.select(tab_info["memory_tabs"][0]["frame"])
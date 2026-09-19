from __future__ import annotations

from pathlib import Path

import tkinter as tk
from tkinter import messagebox, ttk

from Environment.chatroom import ChatroomService
from Environment.chatroom import config


class ChatroomTabMixin:
    """
    Root-level Chatroom tab.

    This mixin is now a UI client for Environment.chatroom.ChatroomService.
    The backend owns chat paths, state, message files, compilation, cursors,
    locks, and archive/restore behavior.
    """

    CHATROOM_FOLDER_CHOICES = [config.ACTIVE_FOLDER, config.ARCHIVED_FOLDER]

    def _build_chatroom_tab(self) -> None:
        self.chatroom_root_dir = self._get_chatroom_root_dir()
        self.chatroom_service = ChatroomService(self.chatroom_root_dir)

        self.chatroom_selected_chat_id: str | None = None
        self.chatroom_loaded_data: dict | None = None
        self.chatroom_known_last_message_ids: dict[str, int] = {}
        self.chatroom_rendered_last_message_ids: dict[str, int] = {}
        self.chatroom_message_body_widgets: list[tk.Widget] = []
        self.chatroom_suppress_select_event = False

        outer = tk.Frame(self.chatroom_tab, padx=8, pady=8)
        outer.pack(fill="both", expand=True)

        self._build_chatroom_top_bar(outer)
        self._build_chatroom_body(outer)
        self._build_chatroom_status_bar()

        self._refresh_chatroom_file_list()
        self._set_chatroom_status(f"Chats root: {self.chatroom_root_dir}")

    def _get_collection_handoff_for_chatroom(self):
        if hasattr(self, "_get_collection_handoff") and callable(self._get_collection_handoff):
            handoff = self._get_collection_handoff()
            if handoff is not None:
                return handoff

        handoff = getattr(self, "collection_handoff", None)
        if handoff is not None:
            return handoff

        package_controller = getattr(self, "package_controller", None)
        if package_controller is not None:
            handoff = getattr(package_controller, "handoff", None)
            if handoff is not None:
                return handoff

        raise RuntimeError("CollectionHandoff is not available on the UI object.")

    def _get_chatroom_root_dir(self) -> Path:
        handoff = self._get_collection_handoff_for_chatroom()
        return Path(handoff.get_storage_entry_directory("chat_root")).expanduser().resolve()

    def _get_selected_chatroom_status(self) -> str:
        folder_var = getattr(self, "chatroom_folder_var", None)
        folder_name = str(folder_var.get() if folder_var is not None else "").strip()
        if folder_name == config.ARCHIVED_FOLDER:
            return "archived"
        return "active"

    def _get_selected_chatroom_root(self) -> Path:
        if self._get_selected_chatroom_status() == "archived":
            return self.chatroom_service.store.paths.archived_dir
        return self.chatroom_service.store.paths.active_dir

    def _build_chatroom_top_bar(self, parent: tk.Widget) -> None:
        top_bar = tk.Frame(parent)
        top_bar.pack(fill="x", pady=(0, 8))

        tk.Label(top_bar, text="Chatroom", font=("Segoe UI", 11, "bold")).pack(side="left")

        controls = tk.Frame(top_bar)
        controls.pack(side="right")

        tk.Label(controls, text="Folder").pack(side="left", padx=(0, 6))

        self.chatroom_folder_var = tk.StringVar(value=config.ACTIVE_FOLDER)
        self.chatroom_folder_dropdown = ttk.Combobox(
            controls,
            textvariable=self.chatroom_folder_var,
            values=self.CHATROOM_FOLDER_CHOICES,
            state="readonly",
            width=12,
        )
        self.chatroom_folder_dropdown.pack(side="left", padx=(0, 8))
        self.chatroom_folder_dropdown.bind(
            "<<ComboboxSelected>>",
            lambda event=None: self._handle_chatroom_folder_changed(),
        )

        tk.Button(
            controls,
            text="New Chat",
            width=12,
            command=self._handle_new_chatroom_chat,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            controls,
            text="Refresh",
            width=10,
            command=self._handle_chatroom_refresh,
        ).pack(side="left", padx=(0, 8))

        self.chatroom_archive_button = tk.Button(
            controls,
            text="Archive",
            width=10,
            command=self._handle_archive_or_restore_chatroom_chat,
        )
        self.chatroom_archive_button.pack(side="left")

    def _build_chatroom_body(self, parent: tk.Widget) -> None:
        body = tk.Frame(parent)
        body.pack(fill="both", expand=True)

        sidebar = tk.Frame(body, width=300)
        sidebar.pack(side="left", fill="y", padx=(0, 8))
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="Chats", anchor="w", font=("Segoe UI", 10, "bold")).pack(fill="x")

        tree_shell = tk.Frame(sidebar)
        tree_shell.pack(fill="both", expand=True, pady=(4, 0))

        self.chatroom_tree = ttk.Treeview(tree_shell, show="tree", selectmode="browse")
        self.chatroom_tree.pack(side="left", fill="both", expand=True)
        self.chatroom_tree.bind("<<TreeviewSelect>>", self._handle_chatroom_selected)
        self.chatroom_tree.tag_configure("unread", foreground="#0b5c8f", font=("Segoe UI", 9, "bold"))

        sidebar_scroll = tk.Scrollbar(tree_shell, orient="vertical", command=self.chatroom_tree.yview)
        sidebar_scroll.pack(side="right", fill="y")
        self.chatroom_tree.configure(yscrollcommand=sidebar_scroll.set)

        self.chatroom_tree_item_refs: dict[str, str] = {}
        self.chatroom_tree_item_kinds: dict[str, str] = {}

        main = tk.Frame(body)
        main.pack(side="left", fill="both", expand=True)

        self.chatroom_header_frame = tk.Frame(main)
        self.chatroom_header_frame.pack(fill="x", pady=(0, 8))

        self.chatroom_title_label = tk.Label(
            self.chatroom_header_frame,
            text="No chat selected",
            anchor="w",
            font=("Segoe UI", 12, "bold"),
        )
        self.chatroom_title_label.pack(fill="x")

        self.chatroom_meta_label = tk.Label(
            self.chatroom_header_frame,
            text="",
            anchor="w",
            fg="gray35",
        )
        self.chatroom_meta_label.pack(fill="x", pady=(2, 0))

        messages_shell = tk.Frame(main, relief="groove", bd=1)
        messages_shell.pack(fill="both", expand=True)

        self.chatroom_messages_canvas = tk.Canvas(messages_shell, highlightthickness=0)
        self.chatroom_messages_canvas.pack(side="left", fill="both", expand=True)

        messages_scroll = tk.Scrollbar(
            messages_shell,
            orient="vertical",
            command=self.chatroom_messages_canvas.yview,
        )
        messages_scroll.pack(side="right", fill="y")
        self.chatroom_messages_canvas.configure(yscrollcommand=messages_scroll.set)

        self.chatroom_messages_inner = tk.Frame(self.chatroom_messages_canvas)
        self.chatroom_messages_window = self.chatroom_messages_canvas.create_window(
            (0, 0),
            window=self.chatroom_messages_inner,
            anchor="nw",
        )

        def _sync_scrollregion(event=None) -> None:
            self.chatroom_messages_canvas.configure(
                scrollregion=self.chatroom_messages_canvas.bbox("all")
            )

        def _sync_inner_width(event=None) -> None:
            if event is not None:
                self.chatroom_messages_canvas.itemconfigure(
                    self.chatroom_messages_window,
                    width=event.width,
                )
                self._update_chatroom_message_wraps(event.width)

        self.chatroom_messages_inner.bind("<Configure>", _sync_scrollregion)
        self.chatroom_messages_canvas.bind("<Configure>", _sync_inner_width)

        self.chatroom_new_message_button = tk.Button(
            main,
            text="New messages",
            command=self._handle_chatroom_new_message_notice,
        )

        self._build_chatroom_composer(main)

    def _build_chatroom_composer(self, parent: tk.Widget) -> None:
        composer = tk.Frame(parent, pady=8)
        composer.pack(fill="x")

        controls_row = tk.Frame(composer)
        controls_row.pack(fill="x", pady=(0, 6))

        tk.Label(controls_row, text="Speaker").pack(side="left")
        self.chatroom_speaker_var = tk.StringVar(value="Avery")
        self.chatroom_speaker_dropdown = ttk.Combobox(
            controls_row,
            textvariable=self.chatroom_speaker_var,
            values=["Avery", "River", "Claude", "Codex"],
            state="normal",
            width=18,
        )
        self.chatroom_speaker_dropdown.pack(side="left", padx=(8, 16))

        tk.Label(controls_row, text="Kind").pack(side="left")
        self.chatroom_kind_var = tk.StringVar(value="message")
        self.chatroom_kind_dropdown = ttk.Combobox(
            controls_row,
            textvariable=self.chatroom_kind_var,
            values=sorted(config.ALLOWED_MESSAGE_KINDS),
            state="readonly",
            width=12,
        )
        self.chatroom_kind_dropdown.pack(side="left", padx=(8, 0))

        input_row = tk.Frame(composer)
        input_row.pack(fill="x")

        self.chatroom_message_text = tk.Text(
            input_row,
            height=3,
            wrap="word",
            undo=True,
            font=("Segoe UI", 10),
        )
        self.chatroom_message_text.pack(side="left", fill="x", expand=True)

        tk.Button(
            input_row,
            text="Send",
            width=12,
            command=self._handle_send_chatroom_message,
        ).pack(side="right", padx=(8, 0), fill="y")

        self.chatroom_message_text.bind(
            "<Control-Return>",
            lambda event=None: self._handle_send_chatroom_message(),
        )

    def _build_chatroom_status_bar(self) -> None:
        self.chatroom_status_label = tk.Label(
            self.chatroom_tab,
            text="",
            anchor="w",
            fg="gray25",
        )
        self.chatroom_status_label.pack(fill="x", pady=(10, 0))

    def _set_chatroom_status(self, text: str) -> None:
        if hasattr(self, "chatroom_status_label"):
            self.chatroom_status_label.config(text=str(text or ""))

    def _handle_chatroom_refresh(self) -> None:
        selected_chat_id = self.chatroom_selected_chat_id
        self._refresh_chatroom_file_list()
        if selected_chat_id:
            self._select_chatroom_chat_id(selected_chat_id)
            self._load_chatroom_chat(selected_chat_id, force_bottom=False, preserve_scroll=True)

    def _handle_chatroom_folder_changed(self) -> None:
        self.chatroom_selected_chat_id = None
        self.chatroom_loaded_data = None
        self._refresh_chatroom_file_list()
        self._refresh_chatroom_archive_button()
        self._render_chatroom_loaded_chat(force_bottom=True)

    def _refresh_chatroom_archive_button(self) -> None:
        if not hasattr(self, "chatroom_archive_button"):
            return
        if self._get_selected_chatroom_status() == "archived":
            self.chatroom_archive_button.config(text="Restore")
        else:
            self.chatroom_archive_button.config(text="Archive")

    def _refresh_chatroom_file_list(self) -> None:
        if not hasattr(self, "chatroom_tree"):
            return

        self._refresh_chatroom_archive_button()
        self.chatroom_tree.delete(*self.chatroom_tree.get_children())
        self.chatroom_tree_item_refs = {}
        self.chatroom_tree_item_kinds = {}

        status = self._get_selected_chatroom_status()
        root_dir = self._get_selected_chatroom_root()
        summaries = self.chatroom_service.list_chats(status=status)

        folder_items: dict[str, str] = {"": ""}
        for summary in summaries:
            try:
                relative_path = Path(summary.visible_path).resolve().relative_to(root_dir.resolve())
            except Exception:
                relative_path = Path(summary.visible_path.name)

            parent_item = ""
            folder_key = ""
            for folder_part in relative_path.parent.parts:
                folder_key = f"{folder_key}/{folder_part}" if folder_key else folder_part
                if folder_key not in folder_items:
                    item_id = f"folder:{status}:{folder_key}"
                    self.chatroom_tree.insert(parent_item, "end", iid=item_id, text=folder_part, open=False)
                    self.chatroom_tree_item_refs[item_id] = folder_key
                    self.chatroom_tree_item_kinds[item_id] = "folder"
                    folder_items[folder_key] = item_id
                parent_item = folder_items[folder_key]

            item_id = f"chat:{summary.chat_id}"
            label = summary.chat_title or relative_path.stem
            last_message_id = int(summary.last_message_id or 0)
            known_last_message_id = self.chatroom_known_last_message_ids.get(summary.chat_id)
            has_unread = known_last_message_id is not None and last_message_id > known_last_message_id
            if known_last_message_id is None:
                self.chatroom_known_last_message_ids[summary.chat_id] = last_message_id
            if has_unread:
                label = f"* {label}"
            self.chatroom_tree.insert(
                parent_item,
                "end",
                iid=item_id,
                text=label,
                open=False,
                tags=("unread",) if has_unread else (),
            )
            self.chatroom_tree_item_refs[item_id] = summary.chat_id
            self.chatroom_tree_item_kinds[item_id] = "chat"

        count = len(summaries)
        if count <= 0:
            self._set_chatroom_status(f"No chats found in {root_dir}")
            return
        self._set_chatroom_status(f"Loaded {count} chat(s) from {root_dir}")

    def _handle_chatroom_selected(self, event=None) -> None:
        if self.chatroom_suppress_select_event:
            return
        selection = self.chatroom_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        item_kind = self.chatroom_tree_item_kinds.get(item_id, "")
        item_ref = self.chatroom_tree_item_refs.get(item_id, "")
        if item_kind == "chat" and item_ref:
            self._load_chatroom_chat(item_ref)
            return
        if item_kind == "folder":
            self._set_chatroom_status(f"Selected folder: {item_ref}")

    def _load_chatroom_chat(
        self,
        chat_ref: str,
        *,
        force_bottom: bool = True,
        preserve_scroll: bool = False,
    ) -> None:
        try:
            loaded = self.chatroom_service.load_chat(chat_ref)
        except Exception as exc:
            messagebox.showerror("Chat Load Failed", str(exc))
            return

        self.chatroom_loaded_data = loaded
        self.chatroom_selected_chat_id = str(loaded["state"].get("chat_id", "") or "")
        self._render_chatroom_loaded_chat(force_bottom=force_bottom, preserve_scroll=preserve_scroll)
        self._set_chatroom_status(f"Loaded chat: {loaded.get('visible_path', '')}")

    def _render_chatroom_loaded_chat(
        self,
        *,
        force_bottom: bool = False,
        preserve_scroll: bool = False,
    ) -> None:
        previous_top = self._chatroom_scroll_top_fraction()
        was_near_bottom = self._is_chatroom_near_bottom()
        self.chatroom_message_body_widgets = []
        for widget in self.chatroom_messages_inner.winfo_children():
            widget.destroy()

        data = self.chatroom_loaded_data
        if not isinstance(data, dict):
            self.chatroom_title_label.config(text="No chat selected")
            self.chatroom_meta_label.config(text="")
            self._hide_chatroom_new_message_notice()
            tk.Label(
                self.chatroom_messages_inner,
                text="Choose or create a chat.",
                anchor="center",
                fg="gray35",
            ).pack(fill="both", expand=True, padx=12, pady=18)
            return

        state = data.get("state", {})
        messages = data.get("messages", [])
        if not isinstance(state, dict):
            state = {}
        if not isinstance(messages, list):
            messages = []

        chat_id = str(state.get("chat_id", "") or "")
        title = str(state.get("chat_title", "") or "Untitled Chat")
        status = str(state.get("status", "") or "")
        participants = state.get("participants", [])
        if not isinstance(participants, list):
            participants = []

        compile_info = state.get("compile", {})
        if not isinstance(compile_info, dict):
            compile_info = {}

        self.chatroom_title_label.config(text=title)
        self.chatroom_meta_label.config(
            text=(
                f"{status} | messages {len(messages)} | "
                f"last id {state.get('last_message_id', 0)} | "
                f"compile {compile_info.get('status', '')}"
            )
        )
        self._refresh_speaker_choices(participants)

        last_message_id = int(state.get("last_message_id", 0) or 0)
        if not last_message_id and messages:
            try:
                last_message_id = max(int(message.get("message_id", 0) or 0) for message in messages)
            except Exception:
                last_message_id = 0
        previous_rendered_last_id = self.chatroom_rendered_last_message_ids.get(chat_id, 0)
        has_new_messages = bool(previous_rendered_last_id and last_message_id > previous_rendered_last_id)

        if not messages:
            tk.Label(
                self.chatroom_messages_inner,
                text="No messages yet. Say hi.",
                anchor="center",
                fg="gray35",
            ).pack(fill="both", expand=True, padx=12, pady=18)
        else:
            for message_entry in messages:
                self._render_chatroom_message_bubble(message_entry)

        if chat_id:
            self.chatroom_rendered_last_message_ids[chat_id] = last_message_id
            self.chatroom_known_last_message_ids[chat_id] = last_message_id

        if force_bottom or was_near_bottom or not preserve_scroll:
            self._hide_chatroom_new_message_notice()
            self.chatroom_messages_canvas.after_idle(self._scroll_chatroom_to_bottom)
        else:
            if has_new_messages:
                self._show_chatroom_new_message_notice()
            else:
                self._hide_chatroom_new_message_notice()
            self.chatroom_messages_canvas.after_idle(lambda: self._restore_chatroom_scroll(previous_top))
        self.chatroom_messages_canvas.after_idle(self._update_chatroom_message_wraps)

    def _refresh_speaker_choices(self, participants: list[object]) -> None:
        values: list[str] = []
        for value in ["Avery", "River", "Claude", "Codex", *participants]:
            clean = str(value or "").strip()
            if clean and clean not in values:
                values.append(clean)
        if hasattr(self, "chatroom_speaker_dropdown"):
            self.chatroom_speaker_dropdown.configure(values=values)

    def _render_chatroom_message_bubble(self, message_entry: object) -> None:
        if not isinstance(message_entry, dict):
            return

        speaker = str(message_entry.get("speaker", "") or "Unknown")
        timestamp = str(message_entry.get("timestamp", "") or "")
        kind = str(message_entry.get("kind", "") or "message")
        message_id = str(message_entry.get("message_id", "") or "")
        message = str(message_entry.get("message", "") or "")
        accent, background = self._chatroom_speaker_style(speaker)

        outer = tk.Frame(self.chatroom_messages_inner)
        outer.pack(fill="x", padx=10, pady=6)

        header_text = f"#{message_id}  {speaker}  |  {kind}"
        if timestamp:
            header_text = f"{header_text}  |  {timestamp}"

        bubble = tk.Frame(outer, bg=background, relief="solid", bd=1)
        bubble.pack(fill="x")

        accent_bar = tk.Frame(bubble, width=5, bg=accent)
        accent_bar.pack(side="left", fill="y")

        content = tk.Frame(bubble, bg=background, padx=8, pady=6)
        content.pack(side="left", fill="x", expand=True)

        header_row = tk.Frame(content, bg=background)
        header_row.pack(fill="x")

        tk.Label(
            header_row,
            text=header_text,
            anchor="w",
            font=("Segoe UI", 9, "bold"),
            fg=accent,
            bg=background,
        ).pack(side="left", fill="x", expand=True)

        tk.Button(
            header_row,
            text="Copy",
            width=7,
            command=lambda value=message: self._copy_chatroom_message(value),
        ).pack(side="right", padx=(8, 0))

        body_label = tk.Label(
            content,
            text=message,
            anchor="w",
            justify="left",
            wraplength=self._chatroom_message_wraplength(),
            bg=background,
            fg="#1f1f1f",
        )
        body_label.pack(fill="x", pady=(4, 0))
        self.chatroom_message_body_widgets.append(body_label)

    def _chatroom_speaker_style(self, speaker: str) -> tuple[str, str]:
        clean = str(speaker or "").strip().lower()
        styles = {
            "avery": ("#6148a8", "#f4f1fb"),
            "river": ("#9a3f2f", "#fff2ef"),
            "claude": ("#1d6f5f", "#eef8f5"),
            "codex": ("#245f9f", "#eef5fc"),
            "system": ("#606060", "#f2f2f2"),
        }
        return styles.get(clean, ("#4f5b66", "#f7f7f7"))

    def _copy_chatroom_message(self, message: str) -> None:
        try:
            self.chatroom_tab.clipboard_clear()
            self.chatroom_tab.clipboard_append(str(message or ""))
            self._set_chatroom_status("Copied full message text.")
        except Exception as exc:
            messagebox.showerror("Copy Failed", str(exc))

    def _chatroom_message_wraplength(self, width: int | None = None) -> int:
        if width is None:
            width = self.chatroom_messages_canvas.winfo_width() if hasattr(self, "chatroom_messages_canvas") else 760
        return max(260, int(width) - 90)

    def _update_chatroom_message_wraps(self, width: int | None = None) -> None:
        wraplength = self._chatroom_message_wraplength(width)
        live_widgets: list[tk.Widget] = []
        for widget in getattr(self, "chatroom_message_body_widgets", []):
            try:
                if widget.winfo_exists():
                    widget.configure(wraplength=wraplength)
                    live_widgets.append(widget)
            except Exception:
                continue
        self.chatroom_message_body_widgets = live_widgets

    def _chatroom_scroll_top_fraction(self) -> float:
        if not hasattr(self, "chatroom_messages_canvas"):
            return 0.0
        try:
            return float(self.chatroom_messages_canvas.yview()[0])
        except Exception:
            return 0.0

    def _is_chatroom_near_bottom(self) -> bool:
        if not hasattr(self, "chatroom_messages_canvas"):
            return True
        try:
            return float(self.chatroom_messages_canvas.yview()[1]) >= 0.98
        except Exception:
            return True

    def _restore_chatroom_scroll(self, top_fraction: float) -> None:
        if hasattr(self, "chatroom_messages_canvas"):
            self.chatroom_messages_canvas.configure(
                scrollregion=self.chatroom_messages_canvas.bbox("all")
            )
            self.chatroom_messages_canvas.yview_moveto(max(0.0, min(1.0, float(top_fraction))))

    def _show_chatroom_new_message_notice(self) -> None:
        if not hasattr(self, "chatroom_new_message_button"):
            return
        if not self.chatroom_new_message_button.winfo_manager():
            self.chatroom_new_message_button.pack(fill="x", pady=(4, 0))

    def _hide_chatroom_new_message_notice(self) -> None:
        if hasattr(self, "chatroom_new_message_button"):
            self.chatroom_new_message_button.pack_forget()

    def _handle_chatroom_new_message_notice(self) -> None:
        self._hide_chatroom_new_message_notice()
        self._scroll_chatroom_to_bottom()

    def _scroll_chatroom_to_bottom(self) -> None:
        if hasattr(self, "chatroom_messages_canvas"):
            self.chatroom_messages_canvas.configure(
                scrollregion=self.chatroom_messages_canvas.bbox("all")
            )
            self.chatroom_messages_canvas.yview_moveto(1.0)

    def _handle_new_chatroom_chat(self) -> None:
        details = self._ask_new_chatroom_details()
        if details is None:
            return
        title, folder = details
        try:
            loaded = self.chatroom_service.create_chat(title, folder=folder, participants=[])
        except Exception as exc:
            messagebox.showerror("New Chat Failed", str(exc))
            return
        self._refresh_chatroom_file_list()
        self.chatroom_loaded_data = loaded
        self.chatroom_selected_chat_id = loaded["state"]["chat_id"]
        self._select_chatroom_chat_id(self.chatroom_selected_chat_id)
        self._render_chatroom_loaded_chat(force_bottom=True)
        self._set_chatroom_status(f"Created chat: {loaded.get('visible_path', '')}")

    def _ask_new_chatroom_details(self) -> tuple[str, str] | None:
        dialog = tk.Toplevel(self.chatroom_tab)
        dialog.title("New Chat")
        dialog.resizable(False, False)
        dialog.transient(self.chatroom_tab)
        dialog.grab_set()

        result: dict[str, tuple[str, str] | None] = {"value": None}

        outer = tk.Frame(dialog, padx=12, pady=12)
        outer.pack(fill="both", expand=True)

        tk.Label(outer, text="Chat title:", anchor="w").grid(row=0, column=0, sticky="w")
        title_var = tk.StringVar()
        title_entry = tk.Entry(outer, textvariable=title_var, width=42)
        title_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 10))

        tk.Label(outer, text="Active folder:", anchor="w").grid(row=2, column=0, sticky="w")
        folder_var = tk.StringVar(value=config.DEFAULT_NEW_CHAT_FOLDER)
        folder_entry = tk.Entry(outer, textvariable=folder_var, width=42)
        folder_entry.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(2, 10))

        button_row = tk.Frame(outer)
        button_row.grid(row=4, column=0, columnspan=2, sticky="ew")

        def confirm() -> None:
            title = title_var.get().strip()
            folder = folder_var.get().strip() or config.DEFAULT_NEW_CHAT_FOLDER
            if not title:
                messagebox.showerror("Missing Title", "Chat title is required.", parent=dialog)
                return
            result["value"] = (title, folder)
            dialog.destroy()

        tk.Button(button_row, text="Create", width=12, command=confirm).pack(side="left")
        tk.Button(button_row, text="Cancel", width=12, command=dialog.destroy).pack(side="right")

        title_entry.focus_set()
        dialog.bind("<Return>", lambda event=None: confirm())
        self.chatroom_tab.wait_window(dialog)
        return result["value"]

    def _handle_send_chatroom_message(self) -> None:
        if not self.chatroom_selected_chat_id:
            messagebox.showinfo("No Chat Selected", "Choose or create a chat first.")
            return

        speaker = self.chatroom_speaker_var.get().strip()
        kind = self.chatroom_kind_var.get().strip() or "message"
        message = self.chatroom_message_text.get("1.0", "end-1c").strip()

        if not speaker:
            messagebox.showerror("Missing Speaker", "Choose or enter a speaker.")
            return
        if not message:
            return

        try:
            loaded = self.chatroom_service.post_message(
                self.chatroom_selected_chat_id,
                speaker,
                message,
                kind=kind,
                mentions=[],
                compile_after=True,
            )
        except Exception as exc:
            messagebox.showerror("Send Failed", str(exc))
            return

        self.chatroom_message_text.delete("1.0", tk.END)
        self.chatroom_loaded_data = loaded
        self.chatroom_selected_chat_id = loaded["state"]["chat_id"]
        self._refresh_chatroom_file_list()
        self._select_chatroom_chat_id(self.chatroom_selected_chat_id)
        self._render_chatroom_loaded_chat(force_bottom=True)
        self._set_chatroom_status(f"Saved message to {loaded.get('visible_path', '')}")

    def _handle_archive_or_restore_chatroom_chat(self) -> None:
        if not self.chatroom_selected_chat_id:
            messagebox.showinfo("No Chat Selected", "Choose a chat first.")
            return

        try:
            if self._get_selected_chatroom_status() == "archived":
                loaded = self.chatroom_service.restore_chat(self.chatroom_selected_chat_id)
                action = "restored"
            else:
                loaded = self.chatroom_service.archive_chat(self.chatroom_selected_chat_id)
                action = "archived"
        except Exception as exc:
            messagebox.showerror("Chat Move Failed", str(exc))
            return

        self.chatroom_selected_chat_id = None
        self.chatroom_loaded_data = None
        self._refresh_chatroom_file_list()
        self._render_chatroom_loaded_chat(force_bottom=True)
        self._set_chatroom_status(f"Chat {action}: {loaded.get('visible_path', '')}")

    def _select_chatroom_chat_id(self, chat_id: str) -> None:
        if not hasattr(self, "chatroom_tree"):
            return
        item_id = f"chat:{chat_id}"
        if item_id not in self.chatroom_tree.get_children(""):
            for candidate in self.chatroom_tree_item_refs:
                if self.chatroom_tree_item_refs.get(candidate) == chat_id:
                    item_id = candidate
                    break
        if item_id not in self.chatroom_tree_item_refs:
            return
        parent_id = self.chatroom_tree.parent(item_id)
        while parent_id:
            self.chatroom_tree.item(parent_id, open=True)
            parent_id = self.chatroom_tree.parent(parent_id)
        self.chatroom_suppress_select_event = True
        self.chatroom_tree.selection_set(item_id)
        self.chatroom_tree.see(item_id)
        self.chatroom_tree.after_idle(lambda: setattr(self, "chatroom_suppress_select_event", False))

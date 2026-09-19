from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable


NODE_AREA_CONTENT = "content"
NODE_AREA_CHILDREN = "children"
NODE_AREA_FUSED = "fused"

ROOT_PACKAGES_ID = "packages"

PACKAGE_SUFFIX_LOGIC = "Logic"
PACKAGE_SUFFIX_REQUIRED_REPLACEMENT_LIST = "Required Replacement List"
PACKAGE_SUFFIX_OPTIONAL_REPLACEMENT_LIST = "Optional Replacement List"
PACKAGE_SUFFIX_ARGUMENT_LIST = "Argument List"
PACKAGE_SUFFIX_RETURN_LIST = "Return List"
PACKAGE_SUFFIX_RECOGNITION_LIST = "Recognition List"

PACKAGE_SECTION_SUFFIXES = {
    "logic": PACKAGE_SUFFIX_LOGIC,
    "required_replacements": PACKAGE_SUFFIX_REQUIRED_REPLACEMENT_LIST,
    "optional_replacements": PACKAGE_SUFFIX_OPTIONAL_REPLACEMENT_LIST,
    "arguments": PACKAGE_SUFFIX_ARGUMENT_LIST,
    "returns": PACKAGE_SUFFIX_RETURN_LIST,
    "recognitions": PACKAGE_SUFFIX_RECOGNITION_LIST,
}


class AgentFoundryPackageVisualMixin:
    def _build_agent_foundry_packages_visual_node(
        self,
        *,
        parent: tk.Widget,
        frontend_object: dict[str, Any],
        packages_node: dict[str, Any],
    ) -> None:
        if not isinstance(frontend_object, dict):
            frontend_object = {}

        if not isinstance(packages_node, dict):
            self._build_package_visual_placeholder(
                parent=parent,
                title="Packages",
                body="No Packages node was available to render.",
            )
            return

        self._register_foundry_node_record(packages_node)

        package_nodes = self._get_package_visual_package_nodes(
            frontend_object=frontend_object,
            packages_node=packages_node,
        )

        shell = tk.Frame(parent)
        shell.pack(fill="both", expand=True)

        self._build_package_visual_root_header(
            parent=shell,
            packages_node=packages_node,
            package_count=len(package_nodes),
        )

        if not package_nodes:
            self._build_package_visual_placeholder(
                parent=shell,
                title="No imported packages",
                body=(
                    "The root Packages node exists, but it does not currently have any "
                    "imported package child tabs to render visually."
                ),
            )
            return

        package_notebook = ttk.Notebook(shell)
        package_notebook.pack(fill="both", expand=True)

        self._register_foundry_node_notebook(packages_node, package_notebook)

        packages_node_id = self._get_package_visual_node_id(packages_node)
        if packages_node_id:
            self.agent_foundry_detail_notebooks[packages_node_id] = package_notebook
            self.agent_foundry_detail_texts[packages_node_id] = {}

        for package_node in package_nodes:
            self._build_package_visual_package_tab(
                parent_notebook=package_notebook,
                frontend_object=frontend_object,
                package_node=package_node,
            )

    def _build_package_visual_root_header(
        self,
        *,
        parent: tk.Widget,
        packages_node: dict[str, Any],
        package_count: int,
    ) -> None:
        header = tk.Frame(parent)
        header.pack(fill="x", pady=(0, 8))

        title = self._get_package_visual_node_display_name(packages_node)
        if not title:
            title = "Packages"

        tk.Label(
            header,
            text=title,
            anchor="w",
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left")

        tk.Label(
            header,
            text=f"{package_count} package tab{'s' if package_count != 1 else ''}",
            anchor="e",
            fg="gray40",
        ).pack(side="right")

        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=(0, 8))

    def _build_package_visual_package_tab(
        self,
        *,
        parent_notebook: ttk.Notebook,
        frontend_object: dict[str, Any],
        package_node: dict[str, Any],
    ) -> None:
        self._register_foundry_node_record(package_node)

        package_name = self._get_package_visual_node_display_name(package_node)
        if not package_name:
            package_name = "Package"

        tab = tk.Frame(parent_notebook, padx=8, pady=8)
        parent_notebook.add(
            tab,
            text=self._shorten_foundry_tab_title(package_name),
        )

        section_nodes = self._get_package_visual_section_nodes(
            frontend_object=frontend_object,
            package_node=package_node,
        )

        top_row = tk.Frame(tab)
        top_row.pack(fill="x", pady=(0, 8))

        name_frame = tk.Frame(top_row)
        name_frame.pack(side="left", fill="x", expand=True, padx=(0, 12))

        tk.Label(name_frame, text="Name", anchor="w").pack(anchor="w")

        name_entry = tk.Entry(name_frame, font=("Segoe UI", 11))
        name_entry.pack(fill="x", pady=(4, 0))
        name_entry.insert(0, package_name)
        name_entry.configure(state="readonly")

        package_id = self._get_package_visual_node_id(package_node)

        id_frame = tk.Frame(top_row, width=260)
        id_frame.pack(side="left", fill="y")
        id_frame.pack_propagate(False)

        tk.Label(id_frame, text="Node ID", anchor="w").pack(anchor="w")

        id_entry = tk.Entry(id_frame, font=("Consolas", 10))
        id_entry.pack(fill="x", pady=(4, 0))
        id_entry.insert(0, package_id)
        id_entry.configure(state="readonly")

        package_inner_notebook = ttk.Notebook(tab)
        package_inner_notebook.pack(fill="both", expand=True)

        main_tab = tk.Frame(package_inner_notebook, padx=10, pady=10)
        additional_tab = tk.Frame(package_inner_notebook, padx=10, pady=10)
        recognitions_tab = tk.Frame(package_inner_notebook, padx=10, pady=10)

        package_inner_notebook.add(main_tab, text="Main")
        package_inner_notebook.add(additional_tab, text="Additional")
        package_inner_notebook.add(recognitions_tab, text="Recognitions")

        self._build_package_visual_main_tab(
            parent=main_tab,
            logic_node=section_nodes.get("logic"),
        )

        self._build_package_visual_additional_tab(
            parent=additional_tab,
            frontend_object=frontend_object,
            argument_container_node=section_nodes.get("arguments"),
            return_container_node=section_nodes.get("returns"),
            required_replacement_container_node=section_nodes.get("required_replacements"),
            optional_replacement_container_node=section_nodes.get("optional_replacements"),
        )

        self._build_package_visual_recognitions_tab(
            parent=recognitions_tab,
            frontend_object=frontend_object,
            recognition_container_node=section_nodes.get("recognitions"),
        )

    def _build_package_visual_main_tab(
        self,
        *,
        parent: tk.Widget,
        logic_node: dict[str, Any] | None,
    ) -> None:
        header_row = tk.Frame(parent)
        header_row.pack(fill="x", pady=(0, 6))

        tk.Label(
            header_row,
            text="Logic",
            anchor="w",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        if isinstance(logic_node, dict):
            edit_command = self._build_edit_command_for_node_id(
                self._get_package_visual_node_id(logic_node)
            )
            if edit_command is not None:
                tk.Button(
                    header_row,
                    text="Edit Logic Node",
                    width=16,
                    command=edit_command,
                ).pack(side="right")

        text_frame = tk.Frame(parent)
        text_frame.pack(fill="both", expand=True)

        logic_text = tk.Text(
            text_frame,
            wrap="none",
            undo=False,
            font=("Consolas", 11),
        )
        logic_text.pack(side="left", fill="both", expand=True)

        y_scroll = tk.Scrollbar(text_frame, orient="vertical", command=logic_text.yview)
        y_scroll.pack(side="right", fill="y")
        logic_text.configure(yscrollcommand=y_scroll.set)

        x_scroll_frame = tk.Frame(parent)
        x_scroll_frame.pack(fill="x", pady=(0, 8))

        x_scroll = tk.Scrollbar(x_scroll_frame, orient="horizontal", command=logic_text.xview)
        x_scroll.pack(fill="x")
        logic_text.configure(xscrollcommand=x_scroll.set)

        if isinstance(logic_node, dict):
            logic_text.insert(
                "1.0",
                self._strip_package_visual_outer_fence(
                    self._get_package_visual_node_content(logic_node)
                ),
            )
        else:
            logic_text.insert("1.0", "")

        logic_text.configure(state="disabled")

        if not isinstance(logic_node, dict):
            tk.Label(
                parent,
                text="No Logic node was found for this package.",
                anchor="w",
                fg="gray40",
            ).pack(fill="x")

    def _build_package_visual_additional_tab(
        self,
        *,
        parent: tk.Widget,
        frontend_object: dict[str, Any],
        argument_container_node: dict[str, Any] | None,
        return_container_node: dict[str, Any] | None,
        required_replacement_container_node: dict[str, Any] | None,
        optional_replacement_container_node: dict[str, Any] | None,
    ) -> None:
        controls_row = tk.Frame(parent)
        controls_row.pack(fill="x", pady=(0, 10))

        self._build_package_visual_mutation_button(
            parent=controls_row,
            text="Add Argument",
            target_node=argument_container_node,
        ).pack(side="left", padx=(0, 8))

        self._build_package_visual_mutation_button(
            parent=controls_row,
            text="Add Required Replacement",
            target_node=required_replacement_container_node,
            width=22,
        ).pack(side="left", padx=(0, 8))

        self._build_package_visual_mutation_button(
            parent=controls_row,
            text="Add Optional Replacement",
            target_node=optional_replacement_container_node,
            width=22,
        ).pack(side="left", padx=(0, 8))

        self._build_package_visual_mutation_button(
            parent=controls_row,
            text="Add Return",
            target_node=return_container_node,
        ).pack(side="left")

        canvas, inner = self._build_package_visual_scroll_body(parent)

        row = 0

        row = self._build_package_visual_collection_section(
            parent=inner,
            row=row,
            title="Arguments",
            container_node=argument_container_node,
            frontend_object=frontend_object,
            empty_text="No arguments added.",
            block_builder=self._build_package_visual_argument_block,
        )

        row = self._build_package_visual_collection_section(
            parent=inner,
            row=row,
            title="Returns",
            container_node=return_container_node,
            frontend_object=frontend_object,
            empty_text="No returns added.",
            block_builder=self._build_package_visual_return_block,
        )

        row = self._build_package_visual_collection_section(
            parent=inner,
            row=row,
            title="Required Replacements",
            container_node=required_replacement_container_node,
            frontend_object=frontend_object,
            empty_text="No required replacements added.",
            block_builder=lambda **kwargs: self._build_package_visual_replacement_block(
                replacement_kind="required",
                **kwargs,
            ),
        )

        row = self._build_package_visual_collection_section(
            parent=inner,
            row=row,
            title="Optional Replacements",
            container_node=optional_replacement_container_node,
            frontend_object=frontend_object,
            empty_text="No optional replacements added.",
            block_builder=lambda **kwargs: self._build_package_visual_replacement_block(
                replacement_kind="optional",
                **kwargs,
            ),
        )

        inner.grid_columnconfigure(0, weight=1)
        self._refresh_package_visual_scrollregion(canvas)

    def _build_package_visual_recognitions_tab(
        self,
        *,
        parent: tk.Widget,
        frontend_object: dict[str, Any],
        recognition_container_node: dict[str, Any] | None,
    ) -> None:
        controls_row = tk.Frame(parent)
        controls_row.pack(fill="x", pady=(0, 10))

        self._build_package_visual_mutation_button(
            parent=controls_row,
            text="Add Recognition",
            target_node=recognition_container_node,
        ).pack(side="left")

        canvas, inner = self._build_package_visual_scroll_body(parent)

        self._build_package_visual_collection_section(
            parent=inner,
            row=0,
            title="Recognitions",
            container_node=recognition_container_node,
            frontend_object=frontend_object,
            empty_text="No recognitions added.",
            block_builder=self._build_package_visual_recognition_block,
        )

        inner.grid_columnconfigure(0, weight=1)
        self._refresh_package_visual_scrollregion(canvas)

    def _build_package_visual_collection_section(
        self,
        *,
        parent: tk.Widget,
        row: int,
        title: str,
        container_node: dict[str, Any] | None,
        frontend_object: dict[str, Any],
        empty_text: str,
        block_builder: Callable[..., None],
    ) -> int:
        tk.Label(
            parent,
            text=title,
            anchor="w",
            font=("Segoe UI", 10, "bold"),
        ).grid(row=row, column=0, sticky="ew", padx=4, pady=(10 if row else 4, 6))
        row += 1

        if not isinstance(container_node, dict):
            tk.Label(
                parent,
                text=f"{title} node not found.",
                anchor="w",
                fg="gray40",
            ).grid(row=row, column=0, sticky="w", padx=6, pady=(0, 6))
            return row + 1

        self._register_foundry_node_record(container_node)

        item_nodes = self._get_package_visual_child_nodes(
            frontend_object=frontend_object,
            container_node=container_node,
        )

        if not item_nodes:
            tk.Label(
                parent,
                text=empty_text,
                anchor="w",
                fg="gray35",
            ).grid(row=row, column=0, sticky="w", padx=6, pady=(0, 6))
            return row + 1

        for index, item_node in enumerate(item_nodes):
            block_builder(
                parent=parent,
                row=row,
                item_node=item_node,
                index=index,
            )
            row += 1

        return row

    def _build_package_visual_argument_block(
        self,
        *,
        parent: tk.Widget,
        row: int,
        item_node: dict[str, Any],
        index: int,
    ) -> None:
        title = self._get_package_visual_node_display_name(item_node)
        if not title:
            title = f"Argument {index + 1}"

        container = self._build_package_visual_block_container(
            parent=parent,
            row=row,
            title=title,
        )

        fields = self._parse_package_visual_key_value_block(item_node)

        self._add_package_visual_text_field(
            parent=container,
            row=0,
            label="Argument Question:",
            value=fields.get("argument_question", ""),
            source_node=item_node,
            height=3,
        )

        self._add_package_visual_entry_field(
            parent=container,
            row=2,
            label="Argument Value Name:",
            value=fields.get("argument_value_name", title),
            source_node=item_node,
        )

        self._add_package_visual_entry_field(
            parent=container,
            row=4,
            label="Argument Fallback:",
            value=fields.get("argument_fallback", ""),
            source_node=item_node,
        )

        self._add_package_visual_entry_field(
            parent=container,
            row=6,
            label="Argument Hidden:",
            value=fields.get("argument_hidden", ""),
            source_node=item_node,
        )

        self._add_package_visual_remove_button(
            parent=container,
            row=8,
            target_node=item_node,
        )

    def _build_package_visual_return_block(
        self,
        *,
        parent: tk.Widget,
        row: int,
        item_node: dict[str, Any],
        index: int,
    ) -> None:
        title = self._get_package_visual_node_display_name(item_node)
        if not title:
            title = f"Return {index + 1}"

        container = self._build_package_visual_block_container(
            parent=parent,
            row=row,
            title=title,
        )

        fields = self._parse_package_visual_key_value_block(item_node)

        self._add_package_visual_entry_field(
            parent=container,
            row=0,
            label="Return Value Name:",
            value=fields.get("return_value_name", title),
            source_node=item_node,
        )

        self._add_package_visual_text_field(
            parent=container,
            row=2,
            label="Return Description:",
            value=fields.get("return_description", ""),
            source_node=item_node,
            height=3,
        )

        self._add_package_visual_remove_button(
            parent=container,
            row=4,
            target_node=item_node,
        )

    def _build_package_visual_replacement_block(
        self,
        *,
        parent: tk.Widget,
        row: int,
        item_node: dict[str, Any],
        index: int,
        replacement_kind: str,
    ) -> None:
        title = self._get_package_visual_node_display_name(item_node)
        if not title:
            title = f"Replacement {index + 1}"

        container = self._build_package_visual_block_container(
            parent=parent,
            row=row,
            title=title,
        )
        container.grid_columnconfigure(1, weight=1)

        fields = self._parse_package_visual_key_value_block(item_node)

        self._add_package_visual_entry_field(
            parent=container,
            row=0,
            label="To Be Replaced:",
            value=fields.get("to_be_replaced", title),
            source_node=item_node,
            label_column=0,
            value_column=1,
        )

        self._add_package_visual_text_field(
            parent=container,
            row=2,
            label="Anchor:",
            value=fields.get("anchor", ""),
            source_node=item_node,
            height=3,
            label_column=0,
            value_column=1,
        )

        self._add_package_visual_remove_button(
            parent=container,
            row=4,
            target_node=item_node,
            columnspan=2,
        )

    def _build_package_visual_recognition_block(
        self,
        *,
        parent: tk.Widget,
        row: int,
        item_node: dict[str, Any],
        index: int,
    ) -> None:
        title = self._get_package_visual_node_display_name(item_node)
        if not title:
            title = f"Recognition {index + 1}"

        container = self._build_package_visual_block_container(
            parent=parent,
            row=row,
            title=title,
        )

        fields = self._parse_package_visual_key_value_block(item_node)

        self._add_package_visual_entry_field(
            parent=container,
            row=0,
            label="Propagate To Outputs:",
            value=fields.get("propagate_to_outputs", ""),
            source_node=item_node,
        )

        self._add_package_visual_entry_field(
            parent=container,
            row=2,
            label="Recognition Name:",
            value=fields.get("recognition_name", title),
            source_node=item_node,
        )

        self._add_package_visual_entry_field(
            parent=container,
            row=4,
            label="Recognition Kind:",
            value=fields.get("recognition_kind", ""),
            source_node=item_node,
        )

        self._add_package_visual_text_field(
            parent=container,
            row=6,
            label="Recognition Text:",
            value=fields.get("recognition_text", ""),
            source_node=item_node,
            height=3,
        )

        self._add_package_visual_entry_field(
            parent=container,
            row=8,
            label="Recognition URL:",
            value=fields.get("recognition_url", ""),
            source_node=item_node,
        )

        self._add_package_visual_remove_button(
            parent=container,
            row=10,
            target_node=item_node,
        )

    def _build_package_visual_mutation_button(
        self,
        *,
        parent: tk.Widget,
        text: str,
        target_node: dict[str, Any] | None,
        width: int = 18,
    ) -> tk.Button:
        command = None
        state = "disabled"

        if isinstance(target_node, dict):
            command_builder = getattr(
                self,
                "_build_package_visual_add_item_command",
                None,
            )
            if callable(command_builder):
                command = command_builder(target_node=target_node, item_label=text)
                state = "normal" if callable(command) else "disabled"

        return tk.Button(
            parent,
            text=text,
            width=width,
            state=state,
            command=command,
        )

    def _add_package_visual_remove_button(
        self,
        *,
        parent: tk.Widget,
        row: int,
        target_node: dict[str, Any],
        columnspan: int = 1,
    ) -> None:
        button_row = tk.Frame(parent)
        button_row.grid(
            row=row,
            column=0,
            columnspan=columnspan,
            sticky="e",
            pady=(8, 0),
        )

        command = None
        state = "disabled"

        command_builder = getattr(
            self,
            "_build_package_visual_remove_item_command",
            None,
        )
        if callable(command_builder):
            command = command_builder(target_node=target_node)
            state = "normal" if callable(command) else "disabled"

        tk.Button(
            button_row,
            text="Remove",
            width=10,
            state=state,
            command=command,
        ).pack(side="right")

    def _add_package_visual_entry_field(
        self,
        *,
        parent: tk.Widget,
        row: int,
        label: str,
        value: Any,
        source_node: dict[str, Any],
        label_column: int = 0,
        value_column: int = 0,
    ) -> None:
        if label_column == value_column:
            tk.Label(parent, text=label, anchor="w").grid(
                row=row,
                column=value_column,
                sticky="w",
                pady=(0, 4),
            )
            entry_row = row + 1
        else:
            tk.Label(parent, text=label, anchor="w").grid(
                row=row,
                column=label_column,
                sticky="w",
                padx=(0, 8),
                pady=(0, 6),
            )
            entry_row = row

        entry = tk.Entry(parent, font=("Consolas", 10))
        entry.grid(row=entry_row, column=value_column, sticky="ew", pady=(0, 6))
        entry.insert(0, self._format_package_visual_value(value))
        entry.configure(state="readonly")

        self._attach_package_visual_field_context(
            widget=entry,
            source_node=source_node,
            field_label=label,
        )

    def _add_package_visual_text_field(
        self,
        *,
        parent: tk.Widget,
        row: int,
        label: str,
        value: Any,
        source_node: dict[str, Any],
        height: int = 4,
        label_column: int = 0,
        value_column: int = 0,
    ) -> None:
        if label_column == value_column:
            tk.Label(parent, text=label, anchor="w").grid(
                row=row,
                column=value_column,
                sticky="w",
                pady=(0, 4),
            )
            text_row = row + 1
        else:
            tk.Label(parent, text=label, anchor="nw").grid(
                row=row,
                column=label_column,
                sticky="nw",
                padx=(0, 8),
                pady=(0, 6),
            )
            text_row = row

        text_frame = tk.Frame(parent)
        text_frame.grid(row=text_row, column=value_column, sticky="ew", pady=(0, 6))
        text_frame.grid_columnconfigure(0, weight=1)

        text_box = tk.Text(
            text_frame,
            height=max(1, int(height or 4)),
            wrap="word",
            undo=False,
            font=("Consolas", 10),
        )
        text_box.grid(row=0, column=0, sticky="ew")
        text_box.insert("1.0", self._format_package_visual_value(value))

        y_scroll = tk.Scrollbar(text_frame, orient="vertical", command=text_box.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        text_box.configure(yscrollcommand=y_scroll.set)

        text_box.configure(state="disabled")

        self._attach_package_visual_field_context(
            widget=text_box,
            source_node=source_node,
            field_label=label,
        )

    def _attach_package_visual_field_context(
        self,
        *,
        widget: tk.Widget,
        source_node: dict[str, Any],
        field_label: str,
    ) -> None:
        try:
            setattr(widget, "foundry_source_node_id", self._get_package_visual_node_id(source_node))
            setattr(widget, "foundry_field_label", str(field_label or "").strip())
        except Exception:
            pass

    def _build_package_visual_block_container(
        self,
        *,
        parent: tk.Widget,
        row: int,
        title: str,
    ) -> tk.LabelFrame:
        container = tk.LabelFrame(
            parent,
            text=str(title or "Item"),
            padx=10,
            pady=10,
        )
        container.grid(row=row, column=0, sticky="ew", padx=4, pady=4)
        container.grid_columnconfigure(0, weight=1)
        return container

    def _build_package_visual_scroll_body(
        self,
        parent: tk.Widget,
    ) -> tuple[tk.Canvas, tk.Frame]:
        canvas_frame = tk.Frame(parent)
        canvas_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        canvas.pack(side="left", fill="both", expand=True)

        scroll = tk.Scrollbar(
            canvas_frame,
            orient="vertical",
            command=canvas.yview,
        )
        scroll.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scroll.set)

        inner = tk.Frame(canvas)
        window_id = canvas.create_window(
            (0, 0),
            window=inner,
            anchor="nw",
        )

        def _sync_scrollregion(event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _sync_inner_width(event) -> None:
            canvas.itemconfigure(window_id, width=event.width)

        inner.bind("<Configure>", _sync_scrollregion)
        canvas.bind("<Configure>", _sync_inner_width)

        return canvas, inner

    def _refresh_package_visual_scrollregion(self, canvas: tk.Canvas) -> None:
        try:
            canvas.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))
        except Exception:
            pass

    def _build_package_visual_placeholder(
        self,
        *,
        parent: tk.Widget,
        title: str,
        body: str,
    ) -> None:
        box = tk.Frame(parent, padx=8, pady=8)
        box.pack(fill="both", expand=True)

        tk.Label(
            box,
            text=str(title or "Packages"),
            anchor="w",
            justify="left",
            font=("Segoe UI", 10, "bold"),
        ).pack(fill="x", anchor="nw", pady=(0, 8))

        ttk.Separator(box, orient="horizontal").pack(fill="x", pady=(0, 8))

        tk.Label(
            box,
            text=str(body or ""),
            anchor="nw",
            justify="left",
            fg="gray40",
            wraplength=900,
        ).pack(fill="x", anchor="nw")

    def _get_package_visual_package_nodes(
        self,
        *,
        frontend_object: dict[str, Any],
        packages_node: dict[str, Any],
    ) -> list[dict[str, Any]]:
        package_nodes: list[dict[str, Any]] = []

        for child_node_id in self._get_package_visual_node_child_ids(packages_node):
            child_node = self._get_frontend_node(
                frontend_object=frontend_object,
                node_id=child_node_id,
            )
            if not isinstance(child_node, dict):
                continue

            if not self._is_package_visual_package_node(child_node):
                continue

            package_nodes.append(child_node)

        return package_nodes

    def _is_package_visual_package_node(self, node: dict[str, Any]) -> bool:
        node_kind = self._get_package_visual_node_kind(node).lower()
        node_id = self._get_package_visual_node_id(node).lower()

        if node_id == ROOT_PACKAGES_ID:
            return False

        if node_kind == "package":
            return True

        if node_kind.endswith("_package"):
            return True

        return False

    def _get_package_visual_section_nodes(
        self,
        *,
        frontend_object: dict[str, Any],
        package_node: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        sections: dict[str, dict[str, Any]] = {}

        for key, suffix in PACKAGE_SECTION_SUFFIXES.items():
            node = self._find_package_visual_child_node_by_suffix(
                frontend_object=frontend_object,
                parent_node=package_node,
                suffix=suffix,
            )
            if isinstance(node, dict):
                sections[key] = node

        return sections

    def _find_package_visual_child_node_by_suffix(
        self,
        *,
        frontend_object: dict[str, Any],
        parent_node: dict[str, Any],
        suffix: str,
    ) -> dict[str, Any] | None:
        clean_suffix = str(suffix or "").strip().lower()
        if not clean_suffix:
            return None

        for child_node_id in self._get_package_visual_node_child_ids(parent_node):
            child_node = self._get_frontend_node(
                frontend_object=frontend_object,
                node_id=child_node_id,
            )
            if not isinstance(child_node, dict):
                continue

            child_name = self._get_package_visual_node_display_name(child_node).lower()
            child_kind = self._get_package_visual_node_kind(child_node).lower()

            if child_name == clean_suffix:
                return child_node

            if child_name.endswith(f" {clean_suffix}"):
                return child_node

            if child_kind == clean_suffix.replace(" ", "_"):
                return child_node

            if child_kind.endswith("_" + clean_suffix.replace(" ", "_")):
                return child_node

        return None

    def _get_package_visual_child_nodes(
        self,
        *,
        frontend_object: dict[str, Any],
        container_node: dict[str, Any],
    ) -> list[dict[str, Any]]:
        child_nodes: list[dict[str, Any]] = []

        for child_node_id in self._get_package_visual_node_child_ids(container_node):
            child_node = self._get_frontend_node(
                frontend_object=frontend_object,
                node_id=child_node_id,
            )
            if isinstance(child_node, dict):
                self._register_foundry_node_record(child_node)
                child_nodes.append(child_node)

        return child_nodes

    def _parse_package_visual_key_value_block(
        self,
        node: dict[str, Any],
    ) -> dict[str, str]:
        content = self._strip_package_visual_outer_fence(
            self._get_package_visual_node_content(node)
        )

        fields: dict[str, str] = {}
        current_key = ""
        current_lines: list[str] = []

        def _flush() -> None:
            nonlocal current_key, current_lines
            if not current_key:
                return
            fields[current_key] = "\n".join(current_lines).strip()
            current_key = ""
            current_lines = []

        for raw_line in str(content or "").splitlines():
            line = raw_line.rstrip()

            if ":" in line:
                possible_key, possible_value = line.split(":", 1)
                clean_key = self._normalize_package_visual_field_key(possible_key)
                if clean_key:
                    _flush()
                    current_key = clean_key
                    current_lines = [possible_value.strip()]
                    continue

            if current_key:
                current_lines.append(line)
            else:
                stripped = line.strip()
                if stripped and "value" not in fields:
                    fields["value"] = stripped

        _flush()

        return fields

    def _normalize_package_visual_field_key(self, value: Any) -> str:
        text = str(value or "").strip().lower()
        if not text:
            return ""

        text = text.replace("-", "_").replace(" ", "_")
        text = "".join(ch for ch in text if ch.isalnum() or ch == "_")
        while "__" in text:
            text = text.replace("__", "_")

        return text.strip("_")

    def _strip_package_visual_outer_fence(self, text: str) -> str:
        lines = [line.rstrip() for line in str(text or "").splitlines()]

        while lines and not lines[0].strip():
            lines.pop(0)

        while lines and not lines[-1].strip():
            lines.pop()

        if len(lines) < 2:
            return "\n".join(lines).strip()

        first = lines[0].strip()
        if not first.endswith(":"):
            return "\n".join(lines).strip()

        heading = first[:-1].strip()
        if not heading:
            return "\n".join(lines).strip()

        if lines[-1].strip() != f"End {heading}":
            return "\n".join(lines[1:-1]).strip()

        return "\n".join(lines).strip()

    def _format_package_visual_value(self, value: Any) -> str:
        if value is None:
            return ""

        if isinstance(value, bool):
            return "true" if value else "false"

        return str(value)

    def _get_package_visual_node_id(self, node: dict[str, Any]) -> str:
        getter = getattr(self, "_get_node_id", None)
        if callable(getter):
            try:
                return str(getter(node) or "").strip()
            except Exception:
                pass

        if not isinstance(node, dict):
            return ""

        return str(node.get("id", "") or "").strip()

    def _get_package_visual_node_kind(self, node: dict[str, Any]) -> str:
        getter = getattr(self, "_get_node_kind", None)
        if callable(getter):
            try:
                return str(getter(node) or "").strip()
            except Exception:
                pass

        if not isinstance(node, dict):
            return ""

        return str(node.get("kind", "") or "").strip()

    def _get_package_visual_node_display_name(self, node: dict[str, Any]) -> str:
        getter = getattr(self, "_get_node_display_name", None)
        if callable(getter):
            try:
                return str(getter(node) or "").strip()
            except Exception:
                pass

        if not isinstance(node, dict):
            return ""

        name = str(node.get("name", "") or "").strip()
        if name:
            return name

        return str(node.get("id", "") or "").strip()

    def _get_package_visual_node_content(self, node: dict[str, Any]) -> str:
        getter = getattr(self, "_get_node_content", None)
        if callable(getter):
            try:
                return str(getter(node) or "")
            except Exception:
                pass

        if not isinstance(node, dict):
            return ""

        return str(node.get("content", "") or "")

    def _get_package_visual_node_child_ids(self, node: dict[str, Any]) -> list[str]:
        getter = getattr(self, "_get_node_child_ids", None)
        if callable(getter):
            try:
                values = getter(node)
                if isinstance(values, list):
                    return [str(value or "").strip() for value in values if str(value or "").strip()]
            except Exception:
                pass

        if not isinstance(node, dict):
            return []

        children = node.get("children", [])
        if not isinstance(children, list):
            return []

        results: list[str] = []
        seen: set[str] = set()

        for value in children:
            clean_value = str(value or "").strip()
            if not clean_value or clean_value in seen:
                continue

            seen.add(clean_value)
            results.append(clean_value)

        return results
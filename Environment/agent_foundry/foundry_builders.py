from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from Environment.agent_foundry.foundry_blueprint_importer import (
    run_foundry_blueprint_import,
)

NODE_AREA_CONTENT = "content"
NODE_AREA_CHILDREN = "children"
NODE_AREA_FUSED = "fused"

ROOT_AGENT_ID = "agent"
ROOT_PACKAGES_ID = "packages"
ROOT_LEFTOVERS_ID = "leftovers"

SECTION_CONTROL_NAME = "Control"
SECTION_COMPOSE_NAME = "Compose"

UI_FILTER_STATE_ATTRIBUTE = "agent_foundry_control_filter_payload_state"
PACKAGES_VIEW_MODE_ATTRIBUTE = "agent_foundry_packages_view_mode"

PACKAGES_VIEW_MODE_TEXT = "Text"
PACKAGES_VIEW_MODE_VISUAL = "Visual"
PACKAGES_VIEW_MODE_VALUES = [
    PACKAGES_VIEW_MODE_TEXT,
    PACKAGES_VIEW_MODE_VISUAL,
]

HIDDEN_UI_ROOT_NODE_IDS = {
    ROOT_AGENT_ID,
}


class AgentFoundryBuildersMixin:
    SECTION_ENTRY_NAME = "Entry"
    SECTION_CONTROL_NAME = SECTION_CONTROL_NAME
    SECTION_COMPOSE_NAME = SECTION_COMPOSE_NAME

    def _build_agent_foundry_tab(self) -> None:
        self._initialize_agent_foundry_state()

        self.agent_foundry_tab.bind(
            "<Visibility>",
            self._handle_agent_foundry_tab_visible,
            add="+",
        )

        self._get_agent_foundry_root_container()
        self._show_agent_foundry_entry_screen()

    def _initialize_agent_foundry_state(self) -> None:
        self.agent_foundry_blueprint_path: Path | None = None
        self.agent_foundry_workspace_map: dict[str, Path] = {}
        self.agent_foundry_record_map: dict[str, dict[str, Any]] = {}
        self.agent_foundry_all_workspace_names: list[str] = []
        self.agent_foundry_loaded_name: str = ""

        self.agent_foundry_loaded_blueprint_text: str = ""
        self.agent_foundry_loaded_leftovers_text: str = ""
        self.agent_foundry_loaded_viewer_text: str = ""
        self.agent_foundry_last_saved_blueprint_text: str = ""
        self.agent_foundry_last_saved_leftovers_text: str = ""
        self.agent_foundry_last_saved_viewer_text: str = ""

        self.agent_foundry_dirty = False
        self.agent_foundry_suppress_picker_events = False
        self.agent_foundry_suppress_visibility_refresh = False

        self.agent_foundry_frontend_object: dict[str, Any] = {}

        self.agent_foundry_root_frame: tk.Frame | None = None
        self.agent_foundry_entry_frame: tk.Frame | None = None
        self.agent_foundry_loaded_workspace_frame: tk.Frame | None = None

        self.agent_foundry_workspace_var: tk.StringVar | None = None
        self.agent_foundry_workspace_picker: ttk.Combobox | None = None

        self.agent_foundry_notebook: ttk.Notebook | None = None

        self.agent_foundry_section_texts: dict[str, tk.Text] = {}
        self.agent_foundry_detail_notebooks: dict[str, ttk.Notebook] = {}
        self.agent_foundry_detail_texts: dict[str, dict[str, tk.Text]] = {}

        self.agent_foundry_control_filter_surface = None

        self.agent_foundry_edited_scopes: set[tuple[str, str]] = set()

        self.agent_foundry_node_text_widgets: dict[str, tk.Text] = {}
        self.agent_foundry_node_notebooks: dict[str, ttk.Notebook] = {}
        self.agent_foundry_node_records: dict[str, dict[str, Any]] = {}

        self.agent_foundry_map_tab_ids: list[str] = []

        self.agent_foundry_packages_view_mode_var: tk.StringVar | None = None
        setattr(self, PACKAGES_VIEW_MODE_ATTRIBUTE, PACKAGES_VIEW_MODE_TEXT)

    def _get_agent_foundry_root_container(self) -> tk.Frame:
        root = getattr(self, "agent_foundry_root_frame", None)
        if isinstance(root, tk.Frame):
            return root

        root = tk.Frame(self.agent_foundry_tab)
        root.pack(fill="both", expand=True)
        self.agent_foundry_root_frame = root
        return root

    def _clear_agent_foundry_root_container(self) -> None:
        root = self._get_agent_foundry_root_container()

        for child in list(root.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass

    def _clear_agent_foundry_loaded_workspace_handles(self) -> None:
        self.agent_foundry_entry_frame = None
        self.agent_foundry_loaded_workspace_frame = None

        self.agent_foundry_workspace_var = None
        self.agent_foundry_workspace_picker = None

        self.agent_foundry_notebook = None

        self.agent_foundry_section_texts = {}
        self.agent_foundry_detail_notebooks = {}
        self.agent_foundry_detail_texts = {}

        self.agent_foundry_control_filter_surface = None

        self.agent_foundry_node_text_widgets = {}
        self.agent_foundry_node_notebooks = {}
        self.agent_foundry_node_records = {}

        self.agent_foundry_map_tab_ids = []

        self.agent_foundry_packages_view_mode_var = None

    def _build_agent_foundry_entry_screen(self) -> None:
        root = self._get_agent_foundry_root_container()

        entry_shell = tk.Frame(root, padx=8, pady=8)
        entry_shell.pack(fill="both", expand=True)

        self.agent_foundry_notebook = ttk.Notebook(entry_shell)
        self.agent_foundry_notebook.pack(fill="both", expand=True)

        entry_frame = tk.Frame(
            self.agent_foundry_notebook,
            padx=24,
            pady=24,
        )
        self.agent_foundry_notebook.add(entry_frame, text=self.SECTION_ENTRY_NAME)

        self.agent_foundry_entry_frame = entry_frame

        center = tk.Frame(entry_frame)
        center.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            center,
            text="Agent Foundry",
            anchor="center",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(fill="x", pady=(0, 18))

        tk.Button(
            center,
            text="Create",
            width=24,
            command=self._handle_agent_foundry_entry_create,
        ).pack(fill="x", pady=(0, 14))

        tk.Button(
            center,
            text="Import",
            width=24,
            command=lambda: run_foundry_blueprint_import(
                parent=self.agent_foundry_tab,
                foundry_ui=self,
            ),
        ).pack(fill="x", pady=(0, 14))

        self.agent_foundry_workspace_var = tk.StringVar(value="")

        self.agent_foundry_workspace_picker = ttk.Combobox(
            center,
            textvariable=self.agent_foundry_workspace_var,
            state="normal",
            width=42,
        )
        self.agent_foundry_workspace_picker.pack(fill="x", pady=(0, 10))

        self.agent_foundry_workspace_picker.bind(
            "<KeyRelease>",
            self._filter_agent_foundry_workspace_picker,
        )
        self.agent_foundry_workspace_picker.bind(
            "<<ComboboxSelected>>",
            self._handle_agent_foundry_entry_picker_selected,
        )
        self.agent_foundry_workspace_picker.bind(
            "<Return>",
            self._handle_agent_foundry_entry_load,
        )

        tk.Button(
            center,
            text="Load",
            width=24,
            command=self._handle_agent_foundry_entry_load,
        ).pack(fill="x", pady=(0, 30))

        tk.Button(
            center,
            text="Resync",
            width=24,
            command=self._handle_agent_foundry_entry_resync,
        ).pack(fill="x")

    def _activate_agent_foundry_loaded_workspace_shell(self) -> None:
        self._clear_agent_foundry_root_container()
        self._clear_agent_foundry_loaded_workspace_handles()

        root = self._get_agent_foundry_root_container()

        workspace_frame = tk.Frame(root, padx=8, pady=8)
        workspace_frame.pack(fill="both", expand=True)

        self.agent_foundry_loaded_workspace_frame = workspace_frame

        self._build_agent_foundry_top_level_tabs(workspace_frame)

    def _build_agent_foundry_top_level_tabs(self, parent: tk.Widget) -> None:
        self.agent_foundry_notebook = ttk.Notebook(parent)
        self.agent_foundry_notebook.pack(fill="both", expand=True)

        self._build_agent_foundry_control_tab()
        self._build_agent_foundry_compose_tab()

    def _build_agent_foundry_control_tab(self) -> None:
        if self.agent_foundry_notebook is None:
            return

        section_frame = tk.Frame(
            self.agent_foundry_notebook,
            padx=8,
            pady=8,
        )
        self.agent_foundry_notebook.add(section_frame, text=self.SECTION_CONTROL_NAME)

        self._build_agent_foundry_control_button_surface(section_frame)
        self._build_agent_foundry_control_filter_body(section_frame)

        self.agent_foundry_detail_texts[self.SECTION_CONTROL_NAME] = {}

    def _build_agent_foundry_compose_tab(self) -> None:
        if self.agent_foundry_notebook is None:
            return

        section_frame = tk.Frame(
            self.agent_foundry_notebook,
            padx=8,
            pady=8,
        )
        self.agent_foundry_notebook.add(section_frame, text=self.SECTION_COMPOSE_NAME)

        text_box = self._build_read_only_box_with_buttons(
            parent=section_frame,
            copy_command=lambda: self._copy_visible_foundry_text_widget(
                self.agent_foundry_section_texts.get(self.SECTION_COMPOSE_NAME)
            ),
            edit_command=None,
            help_path=[self.SECTION_COMPOSE_NAME],
            help_node=None,
        )

        self.agent_foundry_section_texts[self.SECTION_COMPOSE_NAME] = text_box
        self.agent_foundry_detail_texts[self.SECTION_COMPOSE_NAME] = {}

    def _build_agent_foundry_control_button_surface(self, parent: tk.Widget) -> None:
        button_row = tk.Frame(parent)
        button_row.pack(fill="x", anchor="nw", pady=(0, 6))

        tk.Button(
            button_row,
            text="Back To Selection Screen",
            width=24,
            command=self._handle_agent_foundry_back_to_entry,
        ).pack(side="left", padx=(0, 6))

        reset_filter_command = getattr(self, "_reset_agent_foundry_control_filter_state", None)
        if callable(reset_filter_command):
            tk.Button(
                button_row,
                text="Reset Filter",
                width=12,
                command=reset_filter_command,
            ).pack(side="left", padx=(0, 6))

        tk.Button(
            button_row,
            text="Copy Compose",
            width=12,
            command=lambda: self._copy_visible_foundry_text_widget(
                self.agent_foundry_section_texts.get(self.SECTION_COMPOSE_NAME)
            ),
        ).pack(side="left", padx=(0, 6))

        help_command = self._build_agent_foundry_help_button_command(
            help_path=[self.SECTION_CONTROL_NAME],
            help_node=None,
        )
        if help_command is not None:
            tk.Button(
                button_row,
                text="?",
                width=3,
                command=help_command,
            ).pack(side="left")

        helper_text = tk.Label(
            parent,
            text=(
                "Use the filter below to control what appears on the Compose tab "
                "and which map-driven tabs are visible in the workspace."
            ),
            anchor="w",
            justify="left",
            fg="gray40",
            wraplength=1000,
        )
        helper_text.pack(fill="x", anchor="nw", pady=(8, 8))

    def _build_agent_foundry_control_filter_body(self, parent: tk.Widget) -> None:
        filter_container = tk.Frame(parent)
        filter_container.pack(fill="both", expand=True)

        self._build_agent_foundry_control_render_strategy_surface(filter_container)

        build_filter_surface = getattr(self, "_build_agent_foundry_control_filter_surface", None)
        if callable(build_filter_surface):
            build_filter_surface(filter_container)
            return

        tk.Label(
            filter_container,
            text="Control filter surface is not available.",
            anchor="w",
            justify="left",
            fg="gray40",
        ).pack(fill="x", anchor="nw")

    def _build_agent_foundry_control_render_strategy_surface(
        self,
        parent: tk.Widget,
    ) -> None:
        surface = tk.LabelFrame(
            parent,
            text="Node Render Options",
            padx=8,
            pady=8,
        )
        surface.pack(fill="x", anchor="nw", pady=(0, 8))

        row = tk.Frame(surface)
        row.pack(fill="x", anchor="nw")

        tk.Label(
            row,
            text="Packages View:",
            anchor="w",
        ).pack(side="left", padx=(0, 8))

        current_mode = self._get_agent_foundry_packages_view_mode()
        self.agent_foundry_packages_view_mode_var = tk.StringVar(value=current_mode)

        dropdown = ttk.Combobox(
            row,
            textvariable=self.agent_foundry_packages_view_mode_var,
            values=PACKAGES_VIEW_MODE_VALUES,
            state="readonly",
            width=14,
        )
        dropdown.pack(side="left")

        dropdown.bind(
            "<<ComboboxSelected>>",
            self._handle_agent_foundry_packages_view_mode_changed,
        )

        tk.Label(
            surface,
            text=(
                "Text renders the Packages node through the normal Foundry node-map tabs. "
                "Visual lets the Packages node use a package-specific renderer."
            ),
            anchor="w",
            justify="left",
            fg="gray40",
            wraplength=1000,
        ).pack(fill="x", anchor="nw", pady=(6, 0))

    def _handle_agent_foundry_packages_view_mode_changed(
        self,
        event: tk.Event | None = None,
    ) -> None:
        mode_var = getattr(self, "agent_foundry_packages_view_mode_var", None)
        mode = mode_var.get() if mode_var is not None else PACKAGES_VIEW_MODE_TEXT

        self._set_agent_foundry_packages_view_mode(mode)
        self._rerender_agent_foundry_current_frontend_object_for_filter()

    def _get_agent_foundry_packages_view_mode(self) -> str:
        mode = str(
            getattr(self, PACKAGES_VIEW_MODE_ATTRIBUTE, PACKAGES_VIEW_MODE_TEXT)
            or PACKAGES_VIEW_MODE_TEXT
        ).strip()

        if mode not in PACKAGES_VIEW_MODE_VALUES:
            return PACKAGES_VIEW_MODE_TEXT

        return mode

    def _set_agent_foundry_packages_view_mode(self, mode: Any) -> str:
        clean_mode = str(mode or "").strip()
        if clean_mode not in PACKAGES_VIEW_MODE_VALUES:
            clean_mode = PACKAGES_VIEW_MODE_TEXT

        setattr(self, PACKAGES_VIEW_MODE_ATTRIBUTE, clean_mode)

        mode_var = getattr(self, "agent_foundry_packages_view_mode_var", None)
        if mode_var is not None:
            try:
                mode_var.set(clean_mode)
            except Exception:
                pass

        return clean_mode

    def _render_agent_foundry_frontend_object(
        self,
        *,
        frontend_object: dict[str, Any],
    ) -> None:
        if not isinstance(frontend_object, dict):
            frontend_object = {}

        self.agent_foundry_frontend_object = frontend_object

        self._clear_map_driven_foundry_ui()

        self._refresh_agent_foundry_control_filter_from_map()
        self._refresh_agent_foundry_compose_text_from_map(
            frontend_object=frontend_object,
        )

        root_node_ids = self._get_frontend_root_node_ids(frontend_object)

        for node_id in root_node_ids:
            self._render_foundry_node_as_tab(
                parent_notebook=self.agent_foundry_notebook,
                frontend_object=frontend_object,
                node_id=node_id,
                is_top_level=True,
                visited_node_ids=set(),
            )

    def _rerender_agent_foundry_current_frontend_object_for_filter(self) -> None:
        frontend_object = getattr(self, "agent_foundry_frontend_object", None)
        if not isinstance(frontend_object, dict):
            frontend_object = {}

        self._render_agent_foundry_frontend_object(
            frontend_object=frontend_object,
        )

    def _clear_map_driven_foundry_ui(self) -> None:
        notebook = getattr(self, "agent_foundry_notebook", None)
        if notebook is not None:
            for tab_id in list(getattr(self, "agent_foundry_map_tab_ids", []) or []):
                try:
                    notebook.forget(tab_id)
                except Exception:
                    pass

        self.agent_foundry_map_tab_ids = []

        self.agent_foundry_detail_notebooks = {}
        self.agent_foundry_detail_texts = {}

        self.agent_foundry_node_text_widgets = {}
        self.agent_foundry_node_notebooks = {}
        self.agent_foundry_node_records = {}

    def _refresh_agent_foundry_control_filter_from_map(self) -> None:
        refresh_filter_surface = getattr(self, "_refresh_agent_foundry_control_filter_surface", None)
        if callable(refresh_filter_surface):
            refresh_filter_surface()

    def _refresh_agent_foundry_control_text_from_map(
        self,
        *,
        frontend_object: dict[str, Any],
    ) -> None:
        if isinstance(frontend_object, dict):
            self.agent_foundry_frontend_object = frontend_object

        self._rerender_agent_foundry_current_frontend_object_for_filter()

    def _refresh_agent_foundry_compose_text_from_map(
        self,
        *,
        frontend_object: dict[str, Any],
    ) -> None:
        text_widget = self.agent_foundry_section_texts.get(self.SECTION_COMPOSE_NAME)
        if text_widget is None:
            return

        compose = getattr(self, "_compose_agent_foundry_control_display_text", None)
        if not callable(compose):
            return

        try:
            compose_text = compose(frontend_object=frontend_object)
        except Exception:
            compose_text = ""

        self._set_text_widget_value(
            text_widget,
            str(compose_text or "").rstrip()
            + ("\n" if str(compose_text or "").strip() else ""),
        )

    def _render_foundry_node_as_tab(
        self,
        *,
        parent_notebook: ttk.Notebook | None,
        frontend_object: dict[str, Any],
        node_id: str,
        is_top_level: bool = False,
        visited_node_ids: set[str] | None = None,
    ) -> None:
        if parent_notebook is None:
            return

        clean_node_id = self._normalize_node_id(node_id)
        if not clean_node_id:
            return

        if visited_node_ids is None:
            visited_node_ids = set()

        if clean_node_id in visited_node_ids:
            return

        visited_node_ids.add(clean_node_id)

        node = self._get_frontend_node(
            frontend_object=frontend_object,
            node_id=clean_node_id,
        )
        if not isinstance(node, dict):
            return

        self._register_foundry_node_record(node)

        node_name = self._get_node_display_name(node)
        node_area = self._get_node_area(node)

        tab_frame = tk.Frame(parent_notebook, padx=8, pady=8)
        parent_notebook.add(
            tab_frame,
            text=self._shorten_foundry_tab_title(node_name),
        )

        if is_top_level:
            try:
                self.agent_foundry_map_tab_ids.append(str(tab_frame))
            except Exception:
                pass

        if self._should_render_foundry_node_with_special_renderer(node):
            self._render_foundry_node_with_special_renderer(
                parent=tab_frame,
                frontend_object=frontend_object,
                node=node,
            )
            return

        if node_area == NODE_AREA_CHILDREN:
            child_notebook = self._build_node_children_only_body(
                parent=tab_frame,
                node=node,
            )
        elif node_area == NODE_AREA_FUSED:
            child_notebook = self._build_node_fused_body(
                parent=tab_frame,
                node=node,
            )
        else:
            child_notebook = self._build_node_content_body(
                parent=tab_frame,
                node=node,
            )

        if child_notebook is None:
            return

        for child_node_id in self._get_node_child_ids(node):
            self._render_foundry_node_as_tab(
                parent_notebook=child_notebook,
                frontend_object=frontend_object,
                node_id=child_node_id,
                is_top_level=False,
                visited_node_ids=set(visited_node_ids),
            )

    def _should_render_foundry_node_with_special_renderer(
        self,
        node: dict[str, Any],
    ) -> bool:
        node_id = self._get_node_id(node)

        if node_id == ROOT_PACKAGES_ID:
            return self._get_agent_foundry_packages_view_mode() == PACKAGES_VIEW_MODE_VISUAL

        return False

    def _render_foundry_node_with_special_renderer(
        self,
        *,
        parent: tk.Widget,
        frontend_object: dict[str, Any],
        node: dict[str, Any],
    ) -> None:
        node_id = self._get_node_id(node)

        if node_id == ROOT_PACKAGES_ID:
            renderer = getattr(self, "_build_agent_foundry_packages_visual_node", None)
            if callable(renderer):
                renderer(
                    parent=parent,
                    frontend_object=frontend_object,
                    packages_node=node,
                )
                return

            self._build_special_renderer_placeholder(
                parent=parent,
                title="Packages Visual Renderer",
                body=(
                    "Packages View is set to Visual, but the package visual renderer "
                    "has not been installed yet."
                ),
            )
            return

        self._build_special_renderer_placeholder(
            parent=parent,
            title=self._get_node_display_name(node),
            body="No special renderer is available for this node.",
        )

    def _build_special_renderer_placeholder(
        self,
        *,
        parent: tk.Widget,
        title: str,
        body: str,
    ) -> None:
        tk.Label(
            parent,
            text=str(title or "Special Renderer"),
            anchor="w",
            justify="left",
            font=("TkDefaultFont", 10, "bold"),
        ).pack(fill="x", anchor="nw", pady=(0, 8))

        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=(0, 8))

        tk.Label(
            parent,
            text=str(body or ""),
            anchor="nw",
            justify="left",
            fg="gray40",
            wraplength=900,
        ).pack(fill="x", anchor="nw")

    def _build_node_content_body(
        self,
        *,
        parent: tk.Widget,
        node: dict[str, Any],
    ) -> ttk.Notebook | None:
        node_id = self._get_node_id(node)
        text = self._get_node_content(node)

        text_box = self._build_read_only_box_with_buttons(
            parent=parent,
            copy_command=self._build_copy_command_for_node_id(node_id),
            edit_command=self._build_edit_command_for_node_id(node_id),
            help_path=None,
            help_node=node,
        )

        self._set_text_widget_value(
            text_box,
            text.rstrip() + ("\n" if text.strip() else ""),
        )
        self._register_foundry_node_text_widget(node, text_box)

        return None

    def _build_node_children_only_body(
        self,
        *,
        parent: tk.Widget,
        node: dict[str, Any],
    ) -> ttk.Notebook:
        node_id = self._get_node_id(node)

        child_notebook = ttk.Notebook(parent)
        child_notebook.pack(fill="both", expand=True)

        self._register_foundry_node_notebook(node, child_notebook)
        self.agent_foundry_detail_notebooks[node_id] = child_notebook
        self.agent_foundry_detail_texts[node_id] = {}

        return child_notebook

    def _build_node_fused_body(
        self,
        *,
        parent: tk.Widget,
        node: dict[str, Any],
    ) -> ttk.Notebook:
        node_id = self._get_node_id(node)
        text = self._get_node_content(node)

        vertical_pane = tk.PanedWindow(
            parent,
            orient=tk.VERTICAL,
            sashrelief=tk.RAISED,
        )
        vertical_pane.pack(fill="both", expand=True)

        parent_frame = tk.LabelFrame(
            vertical_pane,
            text="Parent Area",
            padx=6,
            pady=6,
        )
        child_frame = tk.LabelFrame(
            vertical_pane,
            text="Child Tabs",
            padx=6,
            pady=6,
        )

        vertical_pane.add(parent_frame, minsize=150)
        vertical_pane.add(child_frame, minsize=270)

        text_box = self._build_read_only_box_with_buttons(
            parent=parent_frame,
            copy_command=self._build_copy_command_for_node_id(node_id),
            edit_command=self._build_edit_command_for_node_id(node_id),
            help_path=None,
            help_node=node,
        )

        self._set_text_widget_value(
            text_box,
            text.rstrip() + ("\n" if text.strip() else ""),
        )
        self._register_foundry_node_text_widget(node, text_box)

        child_notebook = ttk.Notebook(child_frame)
        child_notebook.pack(fill="both", expand=True)

        self._register_foundry_node_notebook(node, child_notebook)
        self.agent_foundry_detail_notebooks[node_id] = child_notebook
        self.agent_foundry_detail_texts[node_id] = {}

        return child_notebook

    def _get_frontend_root_node_ids(
        self,
        frontend_object: dict[str, Any],
    ) -> list[str]:
        if not isinstance(frontend_object, dict):
            return []

        root_node_ids = frontend_object.get("root_node_ids", [])
        if not isinstance(root_node_ids, list):
            return []

        visible_root_node_ids = [
            node_id
            for node_id in root_node_ids
            if self._normalize_node_id(node_id) not in HIDDEN_UI_ROOT_NODE_IDS
        ]

        return self._filter_foundry_node_ids_for_current_ui_payload(
            frontend_object=frontend_object,
            node_ids=self._unique_node_ids(visible_root_node_ids),
        )

    def _filter_foundry_node_ids_for_current_ui_payload(
        self,
        *,
        frontend_object: dict[str, Any],
        node_ids: list[Any] | tuple[Any, ...] | set[Any],
    ) -> list[str]:
        clean_node_ids = self._unique_node_ids(node_ids)

        payload = self._get_current_foundry_ui_filter_payload()
        mode = str(payload.get("mode", "") or "all").strip().lower()

        if mode == "all":
            return clean_node_ids

        included_node_ids = {
            self._normalize_node_id(node_id)
            for node_id in list(payload.get("included_node_ids", []) or [])
            if self._normalize_node_id(node_id)
        }

        if not included_node_ids:
            return []

        return [
            node_id
            for node_id in clean_node_ids
            if self._should_render_foundry_node_for_current_ui_filter(
                frontend_object=frontend_object,
                node_id=node_id,
                included_node_ids=included_node_ids,
            )
        ]

    def _should_render_foundry_node_for_current_ui_filter(
        self,
        *,
        frontend_object: dict[str, Any],
        node_id: str,
        included_node_ids: set[str],
    ) -> bool:
        clean_node_id = self._normalize_node_id(node_id)
        if not clean_node_id:
            return False

        if clean_node_id in HIDDEN_UI_ROOT_NODE_IDS:
            return False

        if clean_node_id in included_node_ids:
            return True

        for descendant_node_id in self._get_frontend_descendant_node_ids(
            frontend_object=frontend_object,
            node_id=clean_node_id,
        ):
            if descendant_node_id in included_node_ids:
                return True

        return False

    def _get_frontend_descendant_node_ids(
        self,
        *,
        frontend_object: dict[str, Any],
        node_id: str,
    ) -> list[str]:
        descendants: list[str] = []
        seen: set[str] = set()

        self._append_frontend_descendant_node_ids(
            frontend_object=frontend_object,
            node_id=node_id,
            descendants=descendants,
            seen=seen,
        )

        return descendants

    def _append_frontend_descendant_node_ids(
        self,
        *,
        frontend_object: dict[str, Any],
        node_id: str,
        descendants: list[str],
        seen: set[str],
    ) -> None:
        node = self._get_frontend_node(
            frontend_object=frontend_object,
            node_id=node_id,
        )
        if not isinstance(node, dict):
            return

        for child_node_id in self._get_raw_node_child_ids(node):
            clean_child_node_id = self._normalize_node_id(child_node_id)
            if not clean_child_node_id or clean_child_node_id in seen:
                continue

            seen.add(clean_child_node_id)
            descendants.append(clean_child_node_id)

            self._append_frontend_descendant_node_ids(
                frontend_object=frontend_object,
                node_id=clean_child_node_id,
                descendants=descendants,
                seen=seen,
            )

    def _get_current_foundry_ui_filter_payload(self) -> dict[str, Any]:
        payload = getattr(self, UI_FILTER_STATE_ATTRIBUTE, None)
        if not isinstance(payload, dict):
            return {
                "mode": "all",
                "included_node_ids": [],
            }

        mode = str(payload.get("mode", "") or "all").strip().lower()
        if mode not in {"all", "dropdowns", "checkboxes"}:
            mode = "all"

        included_node_ids = []

        raw_included_node_ids = payload.get("included_node_ids", [])
        if isinstance(raw_included_node_ids, (list, tuple, set)):
            seen: set[str] = set()
            for raw_node_id in raw_included_node_ids:
                clean_node_id = self._normalize_node_id(raw_node_id)
                if not clean_node_id or clean_node_id in seen:
                    continue

                seen.add(clean_node_id)
                included_node_ids.append(clean_node_id)

        return {
            "mode": mode,
            "included_node_ids": included_node_ids,
        }

    def _get_frontend_node(
        self,
        *,
        frontend_object: dict[str, Any],
        node_id: str,
    ) -> dict[str, Any] | None:
        if not isinstance(frontend_object, dict):
            return None

        nodes = frontend_object.get("nodes", {})
        if not isinstance(nodes, dict):
            return None

        node = nodes.get(self._normalize_node_id(node_id))
        if isinstance(node, dict):
            return node

        return None

    def _get_node_id(self, node: dict[str, Any]) -> str:
        if not isinstance(node, dict):
            return ""

        return self._normalize_node_id(node.get("id", ""))

    def _get_node_display_name(self, node: dict[str, Any]) -> str:
        if not isinstance(node, dict):
            return "Node"

        name = str(node.get("name", "") or "").strip()
        if name:
            return name

        node_id = self._get_node_id(node)
        if node_id:
            return node_id

        return "Node"

    def _get_node_area(self, node: dict[str, Any]) -> str:
        if not isinstance(node, dict):
            return NODE_AREA_CONTENT

        area = str(node.get("area", "") or "").strip().lower()
        if area in {NODE_AREA_CONTENT, NODE_AREA_CHILDREN, NODE_AREA_FUSED}:
            return area

        return NODE_AREA_CONTENT

    def _get_node_kind(self, node: dict[str, Any]) -> str:
        if not isinstance(node, dict):
            return ""

        return str(node.get("kind", "") or "").strip()

    def _get_node_content(self, node: dict[str, Any]) -> str:
        if not isinstance(node, dict):
            return ""

        return str(node.get("content", "") or "")

    def _get_node_child_ids(self, node: dict[str, Any]) -> list[str]:
        raw_child_node_ids = self._get_raw_node_child_ids(node)

        frontend_object = getattr(self, "agent_foundry_frontend_object", {})
        if not isinstance(frontend_object, dict):
            frontend_object = {}

        return self._filter_foundry_node_ids_for_current_ui_payload(
            frontend_object=frontend_object,
            node_ids=raw_child_node_ids,
        )

    def _get_raw_node_child_ids(self, node: dict[str, Any]) -> list[str]:
        if not isinstance(node, dict):
            return []

        children = node.get("children", [])
        if not isinstance(children, list):
            return []

        return self._unique_node_ids(children)

    def _unique_node_ids(self, values: list[Any] | tuple[Any, ...] | set[Any]) -> list[str]:
        results: list[str] = []
        seen: set[str] = set()

        for value in list(values or []):
            clean_value = self._normalize_node_id(value)
            if not clean_value or clean_value in seen:
                continue

            seen.add(clean_value)
            results.append(clean_value)

        return results

    def _normalize_node_id(self, value: Any) -> str:
        return str(value or "").strip()

    def _register_foundry_node_record(self, node: dict[str, Any]) -> str:
        node_id = self._get_node_id(node)
        if not node_id:
            return ""

        self.agent_foundry_node_records[node_id] = node
        return node_id

    def _register_foundry_node_text_widget(
        self,
        node: dict[str, Any],
        text_widget: tk.Text,
    ) -> str:
        node_id = self._register_foundry_node_record(node)
        if not node_id:
            return ""

        self.agent_foundry_node_text_widgets[node_id] = text_widget

        node_area = self._get_node_area(node)
        if node_area in {NODE_AREA_CONTENT, NODE_AREA_FUSED}:
            self.agent_foundry_detail_texts.setdefault(node_id, {})
            self.agent_foundry_detail_texts[node_id][node_id] = text_widget

        return node_id

    def _register_foundry_node_notebook(
        self,
        node: dict[str, Any],
        notebook: ttk.Notebook,
    ) -> str:
        node_id = self._register_foundry_node_record(node)
        if not node_id:
            return ""

        self.agent_foundry_node_notebooks[node_id] = notebook
        return node_id

    def _get_foundry_node_type_by_id(self, node_id: str) -> str:
        clean_node_id = self._normalize_node_id(node_id)
        if not clean_node_id:
            return ""

        node = self.agent_foundry_node_records.get(clean_node_id, {})
        if isinstance(node, dict):
            return self._get_node_kind(node)

        return ""

    def _build_read_only_box_with_buttons(
        self,
        *,
        parent: tk.Widget,
        copy_command: Callable[[], None],
        edit_command: Callable[[], None] | None,
        help_path: list[str] | tuple[str, ...] | None = None,
        help_node: dict[str, Any] | None = None,
        leading_command: Callable[[], None] | None = None,
        leading_button_text: str = "",
        leading_button_width: int = 8,
        filter_command: Callable[[], None] | None = None,
        reset_filter_command: Callable[[], None] | None = None,
    ) -> tk.Text:
        outer = tk.Frame(parent)
        outer.pack(fill="both", expand=True)

        button_row = tk.Frame(outer)
        button_row.pack(fill="x", pady=(0, 6))

        if leading_command is not None:
            tk.Button(
                button_row,
                text=str(leading_button_text or "Back"),
                width=int(leading_button_width or 8),
                command=leading_command,
            ).pack(side="left", padx=(0, 6))

        if filter_command is not None:
            tk.Button(
                button_row,
                text="Filter",
                width=8,
                command=filter_command,
            ).pack(side="left", padx=(0, 6))

        if reset_filter_command is not None:
            tk.Button(
                button_row,
                text="Reset Filter",
                width=12,
                command=reset_filter_command,
            ).pack(side="left", padx=(0, 6))

        tk.Button(
            button_row,
            text="Copy",
            width=8,
            command=copy_command,
        ).pack(side="left", padx=(0, 6))

        if edit_command is not None:
            tk.Button(
                button_row,
                text="Edit",
                width=8,
                command=edit_command,
            ).pack(side="left", padx=(0, 6))

        help_command = self._build_agent_foundry_help_button_command(
            help_path=help_path,
            help_node=help_node,
        )
        if help_command is not None:
            tk.Button(
                button_row,
                text="?",
                width=3,
                command=help_command,
            ).pack(side="left")

        return self._build_read_only_text_box(parent=outer)

    def _build_read_only_text_box(
        self,
        *,
        parent: tk.Widget,
    ) -> tk.Text:
        text_container = tk.Frame(parent)
        text_container.pack(fill="both", expand=True)

        vertical_scrollbar = tk.Scrollbar(text_container, orient="vertical")
        vertical_scrollbar.pack(side="right", fill="y")

        horizontal_scrollbar = tk.Scrollbar(text_container, orient="horizontal")
        horizontal_scrollbar.pack(side="bottom", fill="x")

        text_box = tk.Text(
            text_container,
            wrap="none",
            undo=False,
            font=("Consolas", 10),
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )
        text_box.pack(side="left", fill="both", expand=True)

        vertical_scrollbar.config(command=text_box.yview)
        horizontal_scrollbar.config(command=text_box.xview)

        text_box.configure(state="disabled")

        return text_box

    def _build_agent_foundry_help_button_command(
        self,
        *,
        help_path: list[str] | tuple[str, ...] | None = None,
        help_node: dict[str, Any] | None = None,
    ) -> Callable[[], None] | None:
        if isinstance(help_node, dict):
            return lambda node=help_node: self._show_agent_foundry_help_for_node(node)

        clean_help_path = self._normalize_agent_foundry_builder_help_path(help_path)
        if clean_help_path:
            return lambda help_path=clean_help_path: self._show_agent_foundry_help_for_path(help_path)

        return None

    def _normalize_agent_foundry_builder_help_path(
        self,
        help_path: list[str] | tuple[str, ...] | None,
    ) -> tuple[str, ...]:
        if not isinstance(help_path, (list, tuple)):
            return ()

        return tuple(
            str(part or "").strip()
            for part in list(help_path or [])
            if str(part or "").strip()
        )

    def _copy_visible_foundry_text_widget(self, text_widget: tk.Text | None) -> None:
        if text_widget is None:
            self._copy_to_clipboard("")
            return

        self._copy_to_clipboard(self._read_text_widget_value(text_widget))

    def _read_text_widget_value(self, text_widget: tk.Text) -> str:
        try:
            return str(text_widget.get("1.0", "end-1c") or "")
        except Exception:
            return ""

    def _handle_agent_foundry_tab_visible(self, event: tk.Event | None = None) -> None:
        if self.agent_foundry_suppress_visibility_refresh:
            return

        try:
            if event is not None and event.widget is not self.agent_foundry_tab:
                return
        except Exception:
            return

        self._refresh_agent_foundry_workspaces()

    def _set_named_foundry_section_text(self, section_name: str, text: str) -> None:
        clean_section_name = self._normalize_agent_foundry_section_key(section_name)
        text_widget = self.agent_foundry_section_texts.get(clean_section_name)
        if text_widget is None:
            return

        self._set_text_widget_value(
            text_widget,
            str(text or "").rstrip() + ("\n" if str(text or "").strip() else ""),
        )

    def _get_named_detail_notebook(self, section_name: str) -> ttk.Notebook | None:
        clean_section_name = self._normalize_agent_foundry_section_key(section_name)
        return getattr(self, "agent_foundry_detail_notebooks", {}).get(clean_section_name)

    def _clear_notebook_tabs(self, notebook: ttk.Notebook) -> None:
        for tab_id in notebook.tabs():
            notebook.forget(tab_id)

    def _normalize_agent_foundry_section_key(self, value: Any) -> str:
        return str(value or "").strip()

    def _shorten_foundry_tab_title(self, value: Any, max_length: int = 40) -> str:
        clean_value = str(value or "").strip()
        if not clean_value:
            return "Node"

        if len(clean_value) <= max_length:
            return clean_value

        return clean_value[: max_length - 1].rstrip() + "…"
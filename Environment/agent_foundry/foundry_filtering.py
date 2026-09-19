from __future__ import annotations

import copy
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable


NODE_AREA_CONTENT = "content"
NODE_AREA_CHILDREN = "children"
NODE_AREA_FUSED = "fused"

ROOT_AGENT_ID = "agent"

SECTION_CONTROL_NAME = "Control"
SECTION_COMPOSE_NAME = "Compose"

VIRTUAL_COMPOSE_NODE_ID = "__compose__"

FILTER_EXCLUDED_NODE_IDS = {
    ROOT_AGENT_ID,
}


class AgentFoundryNodeMapFilterSurface(tk.Frame):
    OWNER_FILTER_STATE_ATTRIBUTE = "agent_foundry_control_filter_payload_state"

    def __init__(
        self,
        parent: tk.Widget,
        owner: Any,
        *,
        initial_mode: str = "",
        initial_dropdown_node_id: str = "",
        initial_checkbox_node_ids: list[str] | tuple[str, ...] | None = None,
        initial_include_children_node_ids: list[str] | tuple[str, ...] | None = None,
        on_apply: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        super().__init__(parent)

        self.parent = parent
        self.owner = owner
        self.on_apply = on_apply

        self.frontend_object = self._get_owner_frontend_object()
        self.node_index = self._build_node_inventory(self.frontend_object)

        saved_payload = self.get_owner_filter_state(owner)

        clean_initial_mode = str(initial_mode or "").strip().lower()
        if not clean_initial_mode:
            clean_initial_mode = str(saved_payload.get("mode", "") or "").strip().lower()

        if not initial_dropdown_node_id:
            initial_dropdown_node_id = str(saved_payload.get("dropdown_node_id", "") or "").strip()

        if initial_checkbox_node_ids is None:
            initial_checkbox_node_ids = saved_payload.get("checkbox_node_ids", [])

        if initial_include_children_node_ids is None:
            initial_include_children_node_ids = saved_payload.get("include_children_node_ids", [])

        self.dropdown_enabled_var = tk.BooleanVar(value=clean_initial_mode != "checkboxes")
        self.checkbox_enabled_var = tk.BooleanVar(value=clean_initial_mode == "checkboxes")

        self.filter_content_area: tk.Frame | None = None

        self.dropdown_area: tk.Frame | None = None
        self.dropdown_rows_frame: tk.Frame | None = None
        self.dropdown_vars: list[tk.StringVar] = []
        self.dropdowns: list[ttk.Combobox] = []
        self.dropdown_label_maps: list[dict[str, str]] = []
        self.dropdown_row_frames: list[tk.Frame] = []

        self.checkbox_area: tk.Frame | None = None
        self.checkbox_canvas: tk.Canvas | None = None
        self.checkbox_scroll_frame: tk.Frame | None = None
        self.checkbox_vertical_scrollbar: tk.Scrollbar | None = None
        self.checkbox_canvas_window: int | None = None

        self.checkbox_vars_by_node_id: dict[str, tk.BooleanVar] = {}
        self.include_children_vars_by_node_id: dict[str, tk.BooleanVar] = {}

        self.selected_checkbox_node_ids: set[str] = {
            self._normalize_id(node_id)
            for node_id in list(initial_checkbox_node_ids or [])
            if self._normalize_id(node_id)
        }
        self.include_children_node_ids: set[str] = {
            self._normalize_id(node_id)
            for node_id in list(initial_include_children_node_ids or [])
            if self._normalize_id(node_id)
        }
        self.exclude_children_node_ids: set[str] = {
            self._normalize_id(node_id)
            for node_id in list(saved_payload.get("exclude_children_node_ids", []) or [])
            if self._normalize_id(node_id)
        }

        self.initial_dropdown_node_id = self._normalize_id(initial_dropdown_node_id)

        self._build_ui()
        self._restore_initial_dropdown_node()
        self._restore_checkbox_state()

    @classmethod
    def get_owner_filter_state(cls, owner: Any) -> dict[str, Any]:
        payload = getattr(owner, cls.OWNER_FILTER_STATE_ATTRIBUTE, None)
        if not isinstance(payload, dict):
            return cls._empty_filter_payload()

        return cls._normalize_filter_payload(payload)

    @classmethod
    def save_owner_filter_state(
        cls,
        owner: Any,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        clean_payload = cls._normalize_filter_payload(payload)

        try:
            setattr(owner, cls.OWNER_FILTER_STATE_ATTRIBUTE, copy.deepcopy(clean_payload))
        except Exception:
            pass

        return clean_payload

    @classmethod
    def reset_owner_filter_state(cls, owner: Any) -> dict[str, Any]:
        payload = cls._empty_filter_payload()

        try:
            setattr(owner, cls.OWNER_FILTER_STATE_ATTRIBUTE, copy.deepcopy(payload))
        except Exception:
            pass

        refresh_callable = getattr(owner, "_refresh_agent_foundry_control_display", None)
        if callable(refresh_callable):
            refresh_callable()

        filter_refresh_callable = getattr(owner, "_refresh_agent_foundry_control_filter_surface", None)
        if callable(filter_refresh_callable):
            filter_refresh_callable()

        return payload

    @classmethod
    def _empty_filter_payload(cls) -> dict[str, Any]:
        return {
            "mode": "all",
            "dropdown_node_id": "",
            "checkbox_node_ids": [],
            "include_children_node_ids": [],
            "exclude_children_node_ids": [],
            "included_node_ids": [],
        }

    @classmethod
    def _normalize_filter_payload(cls, payload: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return cls._empty_filter_payload()

        mode = str(payload.get("mode", "") or "all").strip().lower()
        if mode not in {"all", "dropdowns", "checkboxes"}:
            mode = "all"

        checkbox_node_ids = cls._normalize_id_collection(payload.get("checkbox_node_ids", []))
        include_children_node_ids = cls._normalize_id_collection(
            payload.get("include_children_node_ids", [])
        )
        exclude_children_node_ids = cls._normalize_id_collection(
            payload.get("exclude_children_node_ids", [])
        )
        included_node_ids = cls._normalize_id_collection(payload.get("included_node_ids", []))

        return {
            "mode": mode,
            "dropdown_node_id": str(payload.get("dropdown_node_id", "") or "").strip(),
            "checkbox_node_ids": checkbox_node_ids,
            "include_children_node_ids": include_children_node_ids,
            "exclude_children_node_ids": exclude_children_node_ids,
            "included_node_ids": included_node_ids,
        }

    @classmethod
    def _normalize_id_collection(cls, value: Any) -> list[str]:
        if not isinstance(value, (list, tuple, set)):
            return []

        results: list[str] = []
        seen: set[str] = set()

        for raw_id in list(value or []):
            clean_id = str(raw_id or "").strip()
            if not clean_id or clean_id in seen:
                continue

            seen.add(clean_id)
            results.append(clean_id)

        return results

    def refresh_from_owner(self) -> None:
        saved_payload = self.get_owner_filter_state(self.owner)

        self.frontend_object = self._get_owner_frontend_object()
        self.node_index = self._build_node_inventory(self.frontend_object)

        self.initial_dropdown_node_id = self._normalize_id(saved_payload.get("dropdown_node_id", ""))

        mode = str(saved_payload.get("mode", "") or "all").strip().lower()
        self.dropdown_enabled_var.set(mode != "checkboxes")
        self.checkbox_enabled_var.set(mode == "checkboxes")

        self.selected_checkbox_node_ids = {
            self._normalize_id(node_id)
            for node_id in list(saved_payload.get("checkbox_node_ids", []) or [])
            if self._normalize_id(node_id)
        }
        self.include_children_node_ids = {
            self._normalize_id(node_id)
            for node_id in list(saved_payload.get("include_children_node_ids", []) or [])
            if self._normalize_id(node_id)
        }
        self.exclude_children_node_ids = {
            self._normalize_id(node_id)
            for node_id in list(saved_payload.get("exclude_children_node_ids", []) or [])
            if self._normalize_id(node_id)
        }

        self._refresh_filter_mode_visibility()
        self._reset_dropdowns_to_top_level()
        self._restore_initial_dropdown_node()
        self._restore_checkbox_state()

    def _build_ui(self) -> None:
        outer = tk.Frame(self, padx=12, pady=12)
        outer.pack(fill="both", expand=True)

        mode_row = tk.Frame(outer)
        mode_row.pack(fill="x", pady=(0, 10))

        tk.Label(
            mode_row,
            text="Filter Mode:",
            anchor="w",
            font=("TkDefaultFont", 10, "bold"),
        ).pack(side="left", padx=(0, 10))

        tk.Checkbutton(
            mode_row,
            text="Dropdowns",
            variable=self.dropdown_enabled_var,
            command=self._select_dropdown_mode,
        ).pack(side="left", padx=(0, 12))

        tk.Checkbutton(
            mode_row,
            text="Checkboxes",
            variable=self.checkbox_enabled_var,
            command=self._select_checkbox_mode,
        ).pack(side="left", padx=(0, 12))

        self.filter_content_area = tk.Frame(outer)
        self.filter_content_area.pack(fill="both", expand=True)

        self.dropdown_area = tk.LabelFrame(
            self.filter_content_area,
            text="Dropdown Filter",
            padx=10,
            pady=10,
        )

        self.dropdown_rows_frame = tk.Frame(self.dropdown_area)
        self.dropdown_rows_frame.pack(fill="x", anchor="nw")

        self.checkbox_area = tk.LabelFrame(
            self.filter_content_area,
            text="Checkbox Filter",
            padx=10,
            pady=10,
        )
        self._build_checkbox_scroll_area(self.checkbox_area)

        button_row = tk.Frame(outer)
        button_row.pack(fill="x", pady=(10, 0))

        tk.Button(
            button_row,
            text="Apply",
            width=12,
            command=self._handle_apply,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            button_row,
            text="Clear",
            width=12,
            command=self._handle_clear,
        ).pack(side="left", padx=(0, 8))

        self._refresh_filter_mode_visibility()
        self._reset_dropdowns_to_top_level()
        self._rebuild_checkbox_tree()

    def _build_checkbox_scroll_area(self, parent: tk.Widget) -> None:
        container = tk.Frame(parent)
        container.pack(fill="both", expand=True)

        self.checkbox_canvas = tk.Canvas(
            container,
            borderwidth=0,
            highlightthickness=0,
        )
        self.checkbox_canvas.pack(side="left", fill="both", expand=True)

        self.checkbox_vertical_scrollbar = tk.Scrollbar(
            container,
            orient="vertical",
            command=self.checkbox_canvas.yview,
        )
        self.checkbox_vertical_scrollbar.pack(side="right", fill="y")

        self.checkbox_canvas.configure(
            yscrollcommand=self.checkbox_vertical_scrollbar.set,
        )

        self.checkbox_scroll_frame = tk.Frame(self.checkbox_canvas)
        self.checkbox_canvas_window = self.checkbox_canvas.create_window(
            (0, 0),
            window=self.checkbox_scroll_frame,
            anchor="nw",
        )

        self.checkbox_scroll_frame.bind(
            "<Configure>",
            self._handle_checkbox_scroll_frame_configured,
        )
        self.checkbox_canvas.bind(
            "<Configure>",
            self._handle_checkbox_canvas_configured,
        )

    def _handle_checkbox_scroll_frame_configured(
        self,
        event: tk.Event | None = None,
    ) -> None:
        if self.checkbox_canvas is None:
            return

        self.checkbox_canvas.configure(
            scrollregion=self.checkbox_canvas.bbox("all"),
        )

    def _handle_checkbox_canvas_configured(
        self,
        event: tk.Event | None = None,
    ) -> None:
        if self.checkbox_canvas is None:
            return

        try:
            width = int(event.width) if event is not None else int(self.checkbox_canvas.winfo_width())
        except Exception:
            width = 1

        if self.checkbox_canvas_window is None:
            return

        try:
            self.checkbox_canvas.itemconfig(
                self.checkbox_canvas_window,
                width=width,
            )
        except Exception:
            pass

    def _select_dropdown_mode(self) -> None:
        if bool(self.dropdown_enabled_var.get()):
            self.checkbox_enabled_var.set(False)
        elif not bool(self.checkbox_enabled_var.get()):
            self.dropdown_enabled_var.set(True)

        self._refresh_filter_mode_visibility()

    def _select_checkbox_mode(self) -> None:
        if bool(self.checkbox_enabled_var.get()):
            self.dropdown_enabled_var.set(False)
        elif not bool(self.dropdown_enabled_var.get()):
            self.dropdown_enabled_var.set(True)

        self._refresh_filter_mode_visibility()

    def _refresh_filter_mode_visibility(self) -> None:
        if self.dropdown_area is not None:
            if bool(self.dropdown_enabled_var.get()):
                if not self.dropdown_area.winfo_ismapped():
                    self.dropdown_area.pack(fill="x", anchor="nw", pady=(0, 10))
            else:
                self.dropdown_area.pack_forget()

        if self.checkbox_area is not None:
            if bool(self.checkbox_enabled_var.get()):
                if not self.checkbox_area.winfo_ismapped():
                    self.checkbox_area.pack(fill="both", expand=True, anchor="nw", pady=(0, 10))
                self._rebuild_checkbox_tree()
            else:
                self.checkbox_area.pack_forget()

    def _reset_dropdowns_to_top_level(self) -> None:
        self._clear_dropdown_widgets()
        self._add_dropdown(
            level=0,
            node_ids=self._get_top_level_filter_node_ids(),
        )

    def _clear_dropdown_widgets(self) -> None:
        for dropdown in list(self.dropdowns or []):
            try:
                dropdown.destroy()
            except Exception:
                pass

        for row_frame in list(self.dropdown_row_frames or []):
            try:
                row_frame.destroy()
            except Exception:
                pass

        self.dropdown_vars = []
        self.dropdowns = []
        self.dropdown_label_maps = []
        self.dropdown_row_frames = []

    def _restore_initial_dropdown_node(self) -> None:
        if not self.initial_dropdown_node_id:
            return

        node_path = self._get_node_ancestor_path(self.initial_dropdown_node_id)
        if not node_path:
            return

        self._reset_dropdowns_to_top_level()

        for level, node_id in enumerate(node_path):
            if level >= len(self.dropdowns):
                break

            label = self._find_dropdown_label_for_node_id(
                self.dropdown_label_maps[level],
                node_id,
            )
            if not label:
                break

            self.dropdown_vars[level].set(label)
            self._handle_dropdown_selected(level)

    def _find_dropdown_label_for_node_id(
        self,
        label_map: dict[str, str],
        node_id: str,
    ) -> str:
        clean_node_id = self._normalize_id(node_id)
        if not clean_node_id:
            return ""

        for label, mapped_id in dict(label_map or {}).items():
            if mapped_id == clean_node_id:
                return label

        return ""

    def _add_dropdown(
        self,
        *,
        level: int,
        node_ids: list[str],
    ) -> ttk.Combobox | None:
        if self.dropdown_rows_frame is None:
            return None

        clean_node_ids = self._unique_node_ids(node_ids)
        if not clean_node_ids:
            return None

        label_map = self._build_dropdown_label_map(clean_node_ids)
        values = [""] + list(label_map.keys())

        row_frame = tk.Frame(self.dropdown_rows_frame)
        row_frame.pack(fill="x", anchor="nw", pady=(0, 6))

        tk.Label(
            row_frame,
            text=f"Level {int(level) + 1}:",
            width=10,
            anchor="w",
            font=("TkDefaultFont", 9, "bold"),
        ).pack(side="left", padx=(0, 6))

        variable = tk.StringVar(value="")
        dropdown = ttk.Combobox(
            row_frame,
            textvariable=variable,
            state="readonly",
            width=70,
            values=values,
        )
        dropdown.pack(side="left", fill="x", expand=True)

        dropdown.bind(
            "<<ComboboxSelected>>",
            lambda event=None, level=level: self._handle_dropdown_selected(level),
        )

        self.dropdown_vars.append(variable)
        self.dropdowns.append(dropdown)
        self.dropdown_label_maps.append(label_map)
        self.dropdown_row_frames.append(row_frame)

        return dropdown

    def _build_dropdown_label_map(self, node_ids: list[str]) -> dict[str, str]:
        label_map: dict[str, str] = {}
        used_labels: set[str] = set()

        for node_id in self._unique_node_ids(node_ids):
            label = self._build_node_display_label(node_id)
            if not label:
                continue

            unique_label = label
            suffix = 2

            while unique_label in used_labels:
                unique_label = f"{label} ({suffix})"
                suffix += 1

            used_labels.add(unique_label)
            label_map[unique_label] = node_id

        return label_map

    def _handle_dropdown_selected(self, level: int) -> None:
        self._destroy_dropdowns_after_level(level)

        selected_node_id = self.get_selected_dropdown_node_id()
        if not selected_node_id:
            return

        child_node_ids = self._get_child_node_ids(selected_node_id)
        if child_node_ids:
            self._add_dropdown(
                level=len(self.dropdown_vars),
                node_ids=child_node_ids,
            )

    def _destroy_dropdowns_after_level(self, level: int) -> None:
        keep_count = max(0, int(level) + 1)

        for dropdown in self.dropdowns[keep_count:]:
            try:
                dropdown.destroy()
            except Exception:
                pass

        for row_frame in self.dropdown_row_frames[keep_count:]:
            try:
                row_frame.destroy()
            except Exception:
                pass

        self.dropdowns = self.dropdowns[:keep_count]
        self.dropdown_vars = self.dropdown_vars[:keep_count]
        self.dropdown_label_maps = self.dropdown_label_maps[:keep_count]
        self.dropdown_row_frames = self.dropdown_row_frames[:keep_count]

    def get_selected_dropdown_node_id(self) -> str:
        selected_node_id = ""

        for index, variable in enumerate(list(self.dropdown_vars or [])):
            try:
                label = str(variable.get() or "").strip()
            except Exception:
                label = ""

            if not label:
                break

            label_map = self.dropdown_label_maps[index] if index < len(self.dropdown_label_maps) else {}
            selected_node_id = str(label_map.get(label, "") or "").strip()

        return selected_node_id

    def _restore_checkbox_state(self) -> None:
        self.selected_checkbox_node_ids = {
            node_id
            for node_id in self.selected_checkbox_node_ids
            if node_id in self.node_index
        }
        self.include_children_node_ids = {
            node_id
            for node_id in self.include_children_node_ids
            if node_id in self.node_index
        }
        self.exclude_children_node_ids = {
            node_id
            for node_id in self.exclude_children_node_ids
            if node_id in self.node_index
        }

        for node_id in list(self.include_children_node_ids):
            self.selected_checkbox_node_ids.add(node_id)

        self._rebuild_checkbox_tree()

    def _reset_checkbox_tree(self) -> None:
        self.selected_checkbox_node_ids.clear()
        self.include_children_node_ids.clear()
        self.exclude_children_node_ids.clear()
        self._rebuild_checkbox_tree()

    def _clear_checkbox_widgets(self) -> None:
        if self.checkbox_scroll_frame is None:
            return

        for child in list(self.checkbox_scroll_frame.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass

        self.checkbox_vars_by_node_id = {}
        self.include_children_vars_by_node_id = {}

    def _rebuild_checkbox_tree(self) -> None:
        self._clear_checkbox_widgets()

        if self.checkbox_scroll_frame is None:
            return

        title_row = tk.Frame(self.checkbox_scroll_frame)
        title_row.pack(fill="x", anchor="nw", pady=(0, 8))

        tk.Label(
            title_row,
            text="Full Node List",
            anchor="w",
            font=("TkDefaultFont", 9, "bold"),
        ).pack(side="left", fill="x", expand=True)

        self._add_checkbox_subtree_rows(
            parent_node_id="",
            node_ids=self._get_top_level_filter_node_ids(),
            depth=0,
        )

    def _add_checkbox_subtree_rows(
        self,
        *,
        parent_node_id: str,
        node_ids: list[str],
        depth: int,
    ) -> None:
        for node_id in self._unique_node_ids(node_ids):
            self._add_checkbox_node_row(
                node_id=node_id,
                depth=depth,
            )

            child_node_ids = self._get_child_node_ids(node_id)
            if child_node_ids:
                self._add_checkbox_subtree_rows(
                    parent_node_id=node_id,
                    node_ids=child_node_ids,
                    depth=depth + 1,
                )

    def _add_checkbox_node_row(
        self,
        *,
        node_id: str,
        depth: int,
    ) -> None:
        if self.checkbox_scroll_frame is None:
            return

        clean_node_id = self._normalize_id(node_id)
        if not clean_node_id:
            return

        row_frame = tk.Frame(self.checkbox_scroll_frame)
        row_frame.pack(fill="x", anchor="nw", pady=(0, 2), padx=(max(0, int(depth)) * 24, 0))

        variable = tk.BooleanVar(
            value=clean_node_id in self.selected_checkbox_node_ids,
        )
        self.checkbox_vars_by_node_id[clean_node_id] = variable

        tk.Checkbutton(
            row_frame,
            text=self._build_node_display_label(clean_node_id),
            variable=variable,
            command=lambda node_id=clean_node_id: self._handle_checkbox_toggled(node_id),
            anchor="w",
        ).pack(side="left", anchor="w")

        if self._get_child_node_ids(clean_node_id):
            include_children_var = tk.BooleanVar(
                value=clean_node_id in self.include_children_node_ids,
            )
            self.include_children_vars_by_node_id[clean_node_id] = include_children_var

            tk.Checkbutton(
                row_frame,
                text="Include children",
                variable=include_children_var,
                command=lambda node_id=clean_node_id: self._handle_include_children_toggled(node_id),
                anchor="w",
            ).pack(side="left", padx=(18, 0), anchor="w")

    def _handle_checkbox_toggled(self, node_id: str) -> None:
        clean_node_id = self._normalize_id(node_id)
        if not clean_node_id:
            return

        variable = self.checkbox_vars_by_node_id.get(clean_node_id)

        try:
            is_selected = bool(variable.get()) if variable is not None else False
        except Exception:
            is_selected = False

        if is_selected:
            self.selected_checkbox_node_ids.add(clean_node_id)
            for ancestor_id in self._get_node_ancestor_path(clean_node_id)[:-1]:
                self.selected_checkbox_node_ids.add(ancestor_id)
        else:
            self._remove_checkbox_node_and_descendants(clean_node_id)

        self._rebuild_checkbox_tree()

    def _handle_include_children_toggled(self, node_id: str) -> None:
        clean_node_id = self._normalize_id(node_id)
        if not clean_node_id:
            return

        variable = self.include_children_vars_by_node_id.get(clean_node_id)

        try:
            is_selected = bool(variable.get()) if variable is not None else False
        except Exception:
            is_selected = False

        if is_selected:
            self._select_node_and_entire_subtree(clean_node_id)
        else:
            self._clear_include_children_for_node(clean_node_id)

        self._rebuild_checkbox_tree()

    def _select_node_and_entire_subtree(self, node_id: str) -> None:
        clean_node_id = self._normalize_id(node_id)
        if not clean_node_id:
            return

        self.selected_checkbox_node_ids.add(clean_node_id)
        self.include_children_node_ids.add(clean_node_id)
        self.exclude_children_node_ids.discard(clean_node_id)

        for ancestor_id in self._get_node_ancestor_path(clean_node_id)[:-1]:
            self.selected_checkbox_node_ids.add(ancestor_id)

        for descendant_id in self._get_descendant_node_ids(clean_node_id):
            if descendant_id in self.exclude_children_node_ids:
                continue

            self.selected_checkbox_node_ids.add(descendant_id)

            if self._get_child_node_ids(descendant_id):
                self.include_children_node_ids.add(descendant_id)

    def _clear_include_children_for_node(self, node_id: str) -> None:
        clean_node_id = self._normalize_id(node_id)
        if not clean_node_id:
            return

        descendant_ids = set(self._get_descendant_node_ids(clean_node_id))

        self.include_children_node_ids = {
            selected_id
            for selected_id in self.include_children_node_ids
            if selected_id != clean_node_id and selected_id not in descendant_ids
        }

        self.selected_checkbox_node_ids = {
            selected_id
            for selected_id in self.selected_checkbox_node_ids
            if selected_id not in descendant_ids
        }

        self.exclude_children_node_ids.add(clean_node_id)
        self.exclude_children_node_ids = {
            selected_id
            for selected_id in self.exclude_children_node_ids
            if selected_id == clean_node_id or selected_id not in descendant_ids
        }

        self.selected_checkbox_node_ids.add(clean_node_id)

    def _remove_checkbox_node_and_descendants(self, node_id: str) -> None:
        clean_node_id = self._normalize_id(node_id)
        if not clean_node_id:
            return

        removed_ids = {clean_node_id}
        removed_ids.update(self._get_descendant_node_ids(clean_node_id))

        self.selected_checkbox_node_ids = {
            selected_id
            for selected_id in self.selected_checkbox_node_ids
            if selected_id not in removed_ids
        }

        self.include_children_node_ids = {
            selected_id
            for selected_id in self.include_children_node_ids
            if selected_id not in removed_ids
        }

        self.exclude_children_node_ids = {
            selected_id
            for selected_id in self.exclude_children_node_ids
            if selected_id not in removed_ids
        }

    def _build_checkbox_row_label(self, node_id: str) -> str:
        clean_node_id = self._normalize_id(node_id)
        if not clean_node_id:
            return "Full Node List"

        record = self.node_index.get(clean_node_id, {})
        display_path = record.get("display_path", [])
        if isinstance(display_path, list) and display_path:
            return " > ".join(str(part) for part in display_path if str(part).strip())

        return self._build_node_display_label(clean_node_id)

    def get_selected_checkbox_node_ids(self) -> list[str]:
        return self._ordered_node_ids(self.selected_checkbox_node_ids)

    def get_include_children_node_ids(self) -> list[str]:
        return self._ordered_node_ids(self.include_children_node_ids)

    def get_exclude_children_node_ids(self) -> list[str]:
        return self._ordered_node_ids(self.exclude_children_node_ids)

    def _ordered_node_ids(
        self,
        node_ids: set[str] | list[str] | tuple[str, ...],
    ) -> list[str]:
        wanted = {
            self._normalize_id(node_id)
            for node_id in list(node_ids or [])
            if self._normalize_id(node_id)
        }

        ordered: list[str] = []
        for node_id in self._build_full_filter_node_inventory():
            if node_id in wanted:
                ordered.append(node_id)

        for node_id in sorted(wanted):
            if node_id not in ordered:
                ordered.append(node_id)

        return ordered

    def _build_filter_payload(self) -> dict[str, Any]:
        if bool(self.checkbox_enabled_var.get()):
            included_node_ids = self._build_checkbox_included_node_ids()
            if not included_node_ids:
                return self._empty_filter_payload()

            return {
                "mode": "checkboxes",
                "dropdown_node_id": "",
                "checkbox_node_ids": self.get_selected_checkbox_node_ids(),
                "include_children_node_ids": self.get_include_children_node_ids(),
                "exclude_children_node_ids": self.get_exclude_children_node_ids(),
                "included_node_ids": included_node_ids,
            }

        dropdown_node_id = self.get_selected_dropdown_node_id()
        if dropdown_node_id:
            included_node_ids = self._build_dropdown_included_node_ids(dropdown_node_id)
            return {
                "mode": "dropdowns",
                "dropdown_node_id": dropdown_node_id,
                "checkbox_node_ids": [],
                "include_children_node_ids": [],
                "exclude_children_node_ids": [],
                "included_node_ids": included_node_ids,
            }

        return self._empty_filter_payload()

    def _build_dropdown_included_node_ids(self, node_id: str) -> list[str]:
        clean_node_id = self._normalize_id(node_id)
        if not clean_node_id:
            return []

        included = [clean_node_id]
        included.extend(self._get_descendant_node_ids(clean_node_id))
        return self._ordered_node_ids(included)

    def _build_checkbox_included_node_ids(self) -> list[str]:
        return self._ordered_node_ids(self.selected_checkbox_node_ids)

    def _handle_apply(self) -> None:
        payload = self._build_filter_payload()

        self.save_owner_filter_state(
            self.owner,
            payload,
        )

        if self.on_apply is not None:
            self.on_apply(payload)
            return

        refresh_callable = getattr(
            self.owner,
            "_refresh_agent_foundry_control_display_from_filter_payload",
            None,
        )
        if callable(refresh_callable):
            refresh_callable(payload)

    def _handle_clear(self) -> None:
        self._reset_dropdowns_to_top_level()
        self._reset_checkbox_tree()

        payload = self.save_owner_filter_state(
            self.owner,
            self._empty_filter_payload(),
        )

        if self.on_apply is not None:
            self.on_apply(payload)
            return

        refresh_callable = getattr(
            self.owner,
            "_refresh_agent_foundry_control_display_from_filter_payload",
            None,
        )
        if callable(refresh_callable):
            refresh_callable(payload)

    def _get_owner_frontend_object(self) -> dict[str, Any]:
        getter = getattr(self.owner, "_get_current_foundry_frontend_object", None)
        if callable(getter):
            frontend_object = getter()
            if isinstance(frontend_object, dict):
                return frontend_object

        frontend_object = getattr(self.owner, "agent_foundry_frontend_object", None)
        if isinstance(frontend_object, dict):
            return frontend_object

        return self._empty_frontend_object()

    def _empty_frontend_object(self) -> dict[str, Any]:
        return {
            "object_type": "agent_foundry_frontend_object",
            "schema_version": "node_map.v1",
            "root_node_ids": [],
            "nodes": {},
        }

    def _build_node_inventory(
        self,
        frontend_object: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        source_object = frontend_object if isinstance(frontend_object, dict) else self._empty_frontend_object()

        inventory: dict[str, dict[str, Any]] = {}
        seen: set[str] = set()

        self._add_virtual_compose_node_to_index(inventory)

        for root_node_id in self._get_real_frontend_root_node_ids(source_object):
            self._add_node_and_descendants_to_index(
                frontend_object=source_object,
                node_id=root_node_id,
                parent_id="",
                display_path=[],
                inventory=inventory,
                seen=seen,
            )

        return inventory

    def _add_virtual_compose_node_to_index(
        self,
        inventory: dict[str, dict[str, Any]],
    ) -> None:
        inventory[VIRTUAL_COMPOSE_NODE_ID] = {
            "id": VIRTUAL_COMPOSE_NODE_ID,
            "node": {
                "id": VIRTUAL_COMPOSE_NODE_ID,
                "name": SECTION_COMPOSE_NAME,
                "kind": "virtual",
                "area": NODE_AREA_CONTENT,
                "children": [],
                "content": "",
            },
            "parent_id": "",
            "children": [],
            "name": SECTION_COMPOSE_NAME,
            "kind": "virtual",
            "area": NODE_AREA_CONTENT,
            "display_path": [SECTION_COMPOSE_NAME],
        }

    def _add_node_and_descendants_to_index(
        self,
        *,
        frontend_object: dict[str, Any],
        node_id: str,
        parent_id: str,
        display_path: list[str],
        inventory: dict[str, dict[str, Any]],
        seen: set[str],
    ) -> None:
        clean_node_id = self._normalize_id(node_id)
        if not clean_node_id or clean_node_id in seen:
            return

        if self._is_filter_excluded_node_id(clean_node_id):
            return

        node = self._get_frontend_node(
            frontend_object=frontend_object,
            node_id=clean_node_id,
        )
        if not isinstance(node, dict):
            return

        seen.add(clean_node_id)

        name = self._get_node_display_name(node)
        children = [
            child_id
            for child_id in self._get_node_child_ids(node)
            if not self._is_filter_excluded_node_id(child_id)
        ]
        current_path = list(display_path or [])
        current_path.append(name or clean_node_id)

        inventory[clean_node_id] = {
            "id": clean_node_id,
            "node": node,
            "parent_id": parent_id,
            "children": children,
            "name": name,
            "kind": self._get_node_kind(node),
            "area": self._get_node_area(node),
            "display_path": current_path,
        }

        for child_id in children:
            self._add_node_and_descendants_to_index(
                frontend_object=frontend_object,
                node_id=child_id,
                parent_id=clean_node_id,
                display_path=current_path,
                inventory=inventory,
                seen=seen,
            )

    def _get_top_level_filter_node_ids(self) -> list[str]:
        return self._unique_node_ids(
            [
                node_id
                for node_id, record in self.node_index.items()
                if not record.get("parent_id")
                and not self._is_filter_excluded_node_id(node_id)
            ]
        )

    def _build_full_filter_node_inventory(self) -> list[str]:
        inventory: list[str] = []
        seen: set[str] = set()

        for node_id in self._get_top_level_filter_node_ids():
            self._add_node_and_descendants_to_inventory(
                node_id=node_id,
                inventory=inventory,
                seen=seen,
            )

        return inventory

    def _add_node_and_descendants_to_inventory(
        self,
        *,
        node_id: str,
        inventory: list[str],
        seen: set[str],
    ) -> None:
        clean_node_id = self._normalize_id(node_id)
        if not clean_node_id:
            return

        if self._is_filter_excluded_node_id(clean_node_id):
            return

        if clean_node_id not in seen:
            seen.add(clean_node_id)
            inventory.append(clean_node_id)

        for child_id in self._get_child_node_ids(clean_node_id):
            self._add_node_and_descendants_to_inventory(
                node_id=child_id,
                inventory=inventory,
                seen=seen,
            )

    def _get_descendant_node_ids(self, node_id: str) -> list[str]:
        descendants: list[str] = []
        seen: set[str] = set()

        for child_id in self._get_child_node_ids(node_id):
            self._add_node_and_descendants_to_inventory(
                node_id=child_id,
                inventory=descendants,
                seen=seen,
            )

        return descendants

    def _get_child_node_ids(self, node_id: str) -> list[str]:
        clean_node_id = self._normalize_id(node_id)
        if not clean_node_id:
            return []

        record = self.node_index.get(clean_node_id, {})
        children = record.get("children", [])
        if isinstance(children, list):
            return self._unique_node_ids(
                [
                    child_id
                    for child_id in children
                    if not self._is_filter_excluded_node_id(child_id)
                ]
            )

        return []

    def _get_node_ancestor_path(self, node_id: str) -> list[str]:
        clean_node_id = self._normalize_id(node_id)
        if not clean_node_id or clean_node_id not in self.node_index:
            return []

        path: list[str] = []
        current_id = clean_node_id
        safety = 0

        while current_id and safety < 1000:
            safety += 1
            path.append(current_id)

            current_record = self.node_index.get(current_id, {})
            parent_id = self._normalize_id(current_record.get("parent_id", ""))
            if not parent_id:
                break

            current_id = parent_id

        path.reverse()
        return path

    def _build_node_display_label(self, node_id: str) -> str:
        clean_node_id = self._normalize_id(node_id)
        record = self.node_index.get(clean_node_id, {})
        if not isinstance(record, dict):
            return clean_node_id

        name = str(record.get("name", "") or "").strip()
        kind = str(record.get("kind", "") or "").strip()
        area = str(record.get("area", "") or "").strip()
        label = name or clean_node_id

        details = [detail for detail in (kind, area) if detail]
        if details:
            return f"{label} ({', '.join(details)})"

        return label

    def _get_frontend_root_node_ids(
        self,
        frontend_object: dict[str, Any],
    ) -> list[str]:
        return self._get_filter_frontend_root_node_ids(frontend_object)

    def _get_filter_frontend_root_node_ids(
        self,
        frontend_object: dict[str, Any],
    ) -> list[str]:
        node_ids: list[str] = [VIRTUAL_COMPOSE_NODE_ID]
        node_ids.extend(self._get_real_frontend_root_node_ids(frontend_object))
        return self._unique_node_ids(node_ids)

    def _get_real_frontend_root_node_ids(
        self,
        frontend_object: dict[str, Any],
    ) -> list[str]:
        if not isinstance(frontend_object, dict):
            return []

        root_node_ids = frontend_object.get("root_node_ids", [])
        if not isinstance(root_node_ids, list):
            return []

        return self._unique_node_ids(
            [
                node_id
                for node_id in root_node_ids
                if not self._is_filter_excluded_node_id(node_id)
            ]
        )

    def _get_frontend_node(
        self,
        *,
        frontend_object: dict[str, Any],
        node_id: str,
    ) -> dict[str, Any] | None:
        clean_node_id = self._normalize_id(node_id)
        if clean_node_id == VIRTUAL_COMPOSE_NODE_ID:
            return {
                "id": VIRTUAL_COMPOSE_NODE_ID,
                "name": SECTION_COMPOSE_NAME,
                "kind": "virtual",
                "area": NODE_AREA_CONTENT,
                "children": [],
                "content": "",
            }

        if not isinstance(frontend_object, dict):
            return None

        nodes = frontend_object.get("nodes", {})
        if not isinstance(nodes, dict):
            return None

        node = nodes.get(clean_node_id)
        if isinstance(node, dict):
            return node

        return None

    def _get_node_display_name(self, node: dict[str, Any]) -> str:
        if not isinstance(node, dict):
            return "Node"

        name = str(node.get("name", "") or "").strip()
        if name:
            return name

        node_id = self._normalize_id(node.get("id", ""))
        if node_id:
            return node_id

        return "Node"

    def _get_node_kind(self, node: dict[str, Any]) -> str:
        if not isinstance(node, dict):
            return ""

        return str(node.get("kind", "") or "").strip()

    def _get_node_area(self, node: dict[str, Any]) -> str:
        if not isinstance(node, dict):
            return NODE_AREA_CONTENT

        area = str(node.get("area", "") or "").strip().lower()
        if area in {NODE_AREA_CONTENT, NODE_AREA_CHILDREN, NODE_AREA_FUSED}:
            return area

        return NODE_AREA_CONTENT

    def _get_node_child_ids(self, node: dict[str, Any]) -> list[str]:
        if not isinstance(node, dict):
            return []

        children = node.get("children", [])
        if not isinstance(children, list):
            return []

        return self._unique_node_ids(
            [
                child_id
                for child_id in children
                if not self._is_filter_excluded_node_id(child_id)
            ]
        )

    def _is_filter_excluded_node_id(self, node_id: str) -> bool:
        return self._normalize_id(node_id) in FILTER_EXCLUDED_NODE_IDS

    def _unique_node_ids(
        self,
        node_ids: list[Any] | tuple[Any, ...] | set[Any],
    ) -> list[str]:
        results: list[str] = []
        seen: set[str] = set()

        for node_id in list(node_ids or []):
            clean_node_id = self._normalize_id(node_id)
            if not clean_node_id or clean_node_id in seen:
                continue

            if self._is_filter_excluded_node_id(clean_node_id):
                continue

            seen.add(clean_node_id)
            results.append(clean_node_id)

        return results

    def _normalize_id(self, value: Any) -> str:
        return str(value or "").strip()


class AgentFoundryFilteringMixin:
    def _build_agent_foundry_control_filter_surface(
        self,
        parent: tk.Widget,
    ) -> AgentFoundryNodeMapFilterSurface:
        surface = AgentFoundryNodeMapFilterSurface(
            parent=parent,
            owner=self,
            on_apply=self._refresh_agent_foundry_control_display_from_filter_payload,
        )
        surface.pack(fill="both", expand=True)

        try:
            self.agent_foundry_control_filter_surface = surface
        except Exception:
            pass

        return surface

    def _refresh_agent_foundry_control_filter_surface(self) -> None:
        surface = getattr(self, "agent_foundry_control_filter_surface", None)
        if isinstance(surface, AgentFoundryNodeMapFilterSurface):
            surface.refresh_from_owner()

    def _open_agent_foundry_blueprint_filter_popup(self) -> None:
        self._open_agent_foundry_control_filter_popup()

    def _reset_agent_foundry_blueprint_filter_state(self) -> None:
        self._reset_agent_foundry_control_filter_state()

    def _open_agent_foundry_control_filter_popup(self) -> None:
        self._refresh_agent_foundry_control_filter_surface()

        notebook = getattr(self, "agent_foundry_notebook", None)
        if notebook is not None:
            try:
                for tab_id in notebook.tabs():
                    if str(notebook.tab(tab_id, "text")) == SECTION_CONTROL_NAME:
                        notebook.select(tab_id)
                        break
            except Exception:
                pass

    def _reset_agent_foundry_control_filter_state(self) -> None:
        AgentFoundryNodeMapFilterSurface.reset_owner_filter_state(self)
from __future__ import annotations

import json
from pathlib import Path
import re
import tkinter as tk
from typing import Any, Callable


NODE_AREA_CONTENT = "content"
NODE_AREA_CHILDREN = "children"
NODE_AREA_FUSED = "fused"

ROOT_AGENT_ID = "agent"
ROOT_LEFTOVERS_ID = "leftovers"
ROOT_VIEWER_ID = "viewer"

ROOT_AGENT_NAME = "Agent"

GRAMMAR_SUFFIX_ID = "ID"
GRAMMAR_SUFFIX_SEEDED_DEFAULT_RETURNS = "Seeded Default Returns"
GRAMMAR_SUFFIX_SEEDED_GROUPS = "Seeded Groups"
GRAMMAR_SUFFIX_GROUPS = "Groups"
GRAMMAR_SUFFIX_TASKS = "Tasks"
GRAMMAR_SUFFIX_PACKAGES = "Packages"
GRAMMAR_SUFFIX_IMPORTED_PACKAGES = "Imported Packages"
GRAMMAR_SUFFIX_NEW_PACKAGES = "New Packages"

REGISTRY_IMPORTED_DEFAULT_RETURNS_SEED_NAME = "registry_imported_default_returns_seed"

PROTECTED_AGENT_SEEDED_DEFAULT_RETURN_NAMES = {
    "self_agent_name",
}


class AgentFoundryEditPopup(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        initial_text: str,
        on_save: Callable[[str], None],
    ) -> None:
        super().__init__(parent)

        self.parent = parent
        self.on_save = on_save

        self.title(title)
        self.geometry("950x700")
        self.minsize(750, 500)
        self.transient(parent)
        self.grab_set()

        self._build_ui(initial_text=initial_text)
        self.focus_force()

    def _build_ui(self, initial_text: str) -> None:
        outer = tk.Frame(self, padx=12, pady=12)
        outer.pack(fill="both", expand=True)

        text_container = tk.Frame(outer)
        text_container.pack(fill="both", expand=True)

        vertical_scrollbar = tk.Scrollbar(text_container, orient="vertical")
        vertical_scrollbar.pack(side="right", fill="y")

        horizontal_scrollbar = tk.Scrollbar(text_container, orient="horizontal")
        horizontal_scrollbar.pack(side="bottom", fill="x")

        self.editor_text = tk.Text(
            text_container,
            wrap="none",
            undo=True,
            font=("Consolas", 10),
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )
        self.editor_text.pack(side="left", fill="both", expand=True)

        vertical_scrollbar.config(command=self.editor_text.yview)
        horizontal_scrollbar.config(command=self.editor_text.xview)

        self.editor_text.insert("1.0", str(initial_text or ""))

        button_row = tk.Frame(outer)
        button_row.pack(fill="x", pady=(10, 0))

        tk.Button(
            button_row,
            text="OK",
            width=12,
            command=self._handle_ok,
        ).pack(side="left")

        tk.Button(
            button_row,
            text="Cancel",
            width=12,
            command=self.destroy,
        ).pack(side="right")

    def _handle_ok(self) -> None:
        self.on_save(self.editor_text.get("1.0", "end-1c"))
        self.destroy()


class AgentFoundryEditingMixin:
    def _copy_to_clipboard(self, text: str) -> None:
        root = self.agent_foundry_tab.winfo_toplevel()
        root.clipboard_clear()
        root.clipboard_append(str(text or ""))

    def _build_copy_command_for_node_id(self, node_id: str) -> Callable[[], None]:
        clean_node_id = self._normalize_foundry_edit_node_id(node_id)

        return lambda node_id=clean_node_id: self._copy_to_clipboard(
            self._get_foundry_frontend_node_text_by_id(node_id)
        )

    def _get_foundry_frontend_node_text_by_id(self, node_id: str) -> str:
        node = self._get_foundry_frontend_node_by_id(node_id)
        if not isinstance(node, dict):
            return ""

        return self._get_foundry_frontend_node_text(node)

    def _build_edit_command_for_node_id(
        self,
        node_id: str,
    ) -> Callable[[], None] | None:
        clean_node_id = self._normalize_foundry_edit_node_id(node_id)
        if not clean_node_id:
            return None

        return lambda node_id=clean_node_id: self._open_agent_foundry_edit_for_node_id(
            node_id
        )

    def _open_agent_foundry_edit_for_node_id(self, node_id: str) -> None:
        clean_node_id = self._normalize_foundry_edit_node_id(node_id)
        if not clean_node_id:
            return

        node = self._get_foundry_frontend_node_by_id(clean_node_id)
        if not isinstance(node, dict):
            return

        if not self._is_foundry_frontend_node_editable(node):
            return

        current_text = self._get_foundry_frontend_node_text(node)

        AgentFoundryEditPopup(
            parent=self.agent_foundry_tab,
            title=self._build_foundry_node_edit_title(node),
            initial_text=current_text.rstrip() + ("\n" if current_text.strip() else ""),
            on_save=lambda new_text, node_id=clean_node_id: (
                self._apply_foundry_node_edit(
                    node_id=node_id,
                    new_text=new_text,
                )
            ),
        )

    def _apply_foundry_node_edit(
        self,
        *,
        node_id: str,
        new_text: str,
    ) -> None:
        clean_node_id = self._normalize_foundry_edit_node_id(node_id)
        if not clean_node_id:
            return

        node = self._get_foundry_frontend_node_by_id(clean_node_id)
        if not isinstance(node, dict):
            return

        if not self._is_foundry_frontend_node_editable(node):
            return

        before_text = self._get_foundry_frontend_node_text(node).rstrip()

        final_text = str(new_text or "").rstrip()

        if before_text == final_text:
            return

        self._set_foundry_frontend_node_text(node, final_text)
        self._mark_agent_foundry_dirty_scope(("node", clean_node_id))
        self._restart_agent_foundry_lifecycle_after_direct_mutation()

    def _get_current_foundry_frontend_object(self) -> dict[str, Any]:
        frontend_object = getattr(self, "agent_foundry_frontend_object", None)
        if isinstance(frontend_object, dict):
            return frontend_object

        frontend_object = {
            "object_type": "agent_foundry_frontend_object",
            "schema_version": "node_map.v1",
            "root_node_ids": [],
            "nodes": {},
        }
        self.agent_foundry_frontend_object = frontend_object
        return frontend_object

    def _get_foundry_frontend_nodes(self) -> dict[str, dict[str, Any]]:
        frontend_object = self._get_current_foundry_frontend_object()
        nodes = frontend_object.get("nodes", {})
        if isinstance(nodes, dict):
            return nodes

        return {}

    def _get_foundry_frontend_node_by_id(self, node_id: str) -> dict[str, Any] | None:
        clean_node_id = self._normalize_foundry_edit_node_id(node_id)
        if not clean_node_id:
            return None

        rendered_records = getattr(self, "agent_foundry_node_records", None)
        if isinstance(rendered_records, dict):
            rendered_node = rendered_records.get(clean_node_id)
            if isinstance(rendered_node, dict):
                return rendered_node

        node = self._get_foundry_frontend_nodes().get(clean_node_id)
        if isinstance(node, dict):
            return node

        return None

    def _get_foundry_frontend_node_id(self, node: dict[str, Any]) -> str:
        if not isinstance(node, dict):
            return ""

        return self._normalize_foundry_edit_node_id(node.get("id", ""))

    def _get_foundry_frontend_node_type(self, node: dict[str, Any]) -> str:
        if not isinstance(node, dict):
            return ""

        return self._normalize_foundry_edit_text(node.get("kind", ""))

    def _get_foundry_frontend_node_name(self, node: dict[str, Any]) -> str:
        if not isinstance(node, dict):
            return ""

        return self._normalize_foundry_edit_text(node.get("name", ""))

    def _get_foundry_frontend_node_area(self, node: dict[str, Any]) -> str:
        if not isinstance(node, dict):
            return NODE_AREA_CONTENT

        area = str(node.get("area", "") or "").strip().lower()
        if area in {NODE_AREA_CONTENT, NODE_AREA_CHILDREN, NODE_AREA_FUSED}:
            return area

        return NODE_AREA_CONTENT

    def _get_foundry_frontend_node_data(self, node: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(node, dict):
            return {}

        data = node.get("data", {})
        if isinstance(data, dict):
            return data

        return {}

    def _get_foundry_frontend_node_child_ids(self, node: dict[str, Any]) -> list[str]:
        if not isinstance(node, dict):
            return []

        children = node.get("children", [])
        if not isinstance(children, list):
            return []

        results: list[str] = []
        seen: set[str] = set()

        for value in children:
            clean_value = self._normalize_foundry_edit_node_id(value)
            if not clean_value or clean_value in seen:
                continue

            seen.add(clean_value)
            results.append(clean_value)

        return results

    def _iter_foundry_frontend_nodes_in_order(self) -> list[dict[str, Any]]:
        frontend_object = self._get_current_foundry_frontend_object()
        root_node_ids = frontend_object.get("root_node_ids", [])
        if not isinstance(root_node_ids, list):
            root_node_ids = []

        ordered: list[dict[str, Any]] = []
        seen: set[str] = set()

        for root_node_id in root_node_ids:
            self._append_foundry_node_and_descendants_in_order(
                node_id=str(root_node_id or "").strip(),
                ordered=ordered,
                seen=seen,
            )

        for node_id in self._get_foundry_frontend_nodes().keys():
            self._append_foundry_node_and_descendants_in_order(
                node_id=node_id,
                ordered=ordered,
                seen=seen,
            )

        return ordered

    def _append_foundry_node_and_descendants_in_order(
        self,
        *,
        node_id: str,
        ordered: list[dict[str, Any]],
        seen: set[str],
    ) -> None:
        clean_node_id = self._normalize_foundry_edit_node_id(node_id)
        if not clean_node_id or clean_node_id in seen:
            return

        node = self._get_foundry_frontend_node_by_id(clean_node_id)
        if not isinstance(node, dict):
            return

        seen.add(clean_node_id)
        ordered.append(node)

        for child_node_id in self._get_foundry_frontend_node_child_ids(node):
            self._append_foundry_node_and_descendants_in_order(
                node_id=child_node_id,
                ordered=ordered,
                seen=seen,
            )

    def _run_agent_foundry_mutation_checkpoint_before_render(
        self,
        *,
        frontend_object: dict[str, Any],
    ) -> bool:
        target_object = frontend_object
        if not isinstance(target_object, dict):
            target_object = self._get_current_foundry_frontend_object()

        if not isinstance(target_object, dict):
            return False

        self.agent_foundry_frontend_object = target_object
        self.agent_foundry_dirty = False

        self._sync_seeded_frontend_object_before_hydrate(
            frontend_object=target_object,
        )

        return bool(getattr(self, "agent_foundry_dirty", False))

    def _restart_agent_foundry_lifecycle_after_direct_mutation(self) -> None:
        save_callable = getattr(self, "_save_agent_foundry_current_frontend_object_to_files", None)
        if not callable(save_callable):
            self._hydrate_agent_foundry_ui_from_frontend_object()
            return

        foundry_name = str(getattr(self, "agent_foundry_loaded_name", "") or "").strip()
        if not foundry_name:
            self._hydrate_agent_foundry_ui_from_frontend_object()
            return

        save_callable()

        load_callable = getattr(self, "_load_agent_foundry_blueprint_by_name_or_raise", None)
        if callable(load_callable):
            load_callable(foundry_name)
            return

        self._hydrate_agent_foundry_ui_from_frontend_object()

    def _sync_seeded_frontend_object_before_hydrate(
        self,
        frontend_object: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        target_object = frontend_object
        if not isinstance(target_object, dict):
            target_object = self._get_current_foundry_frontend_object()

        if not isinstance(target_object, dict):
            return {}

        self.agent_foundry_frontend_object = target_object

        if bool(getattr(self, "agent_foundry_resync_batch_active", False)):
            self.agent_foundry_resync_seed_changed = False

        seed_result = self._sync_foundry_seeded_default_returns_by_grammar()

        imported_package_result = self._sync_foundry_imported_packages_by_grammar(
            agent_names=self._extract_foundry_agent_names_for_seed(),
        )
        self._merge_foundry_seed_result(
            aggregate=seed_result,
            item_result=imported_package_result,
        )

        changed = bool(seed_result.get("changed", False))
        leftovers_changed = bool(seed_result.get("leftovers_changed", False))

        self.agent_foundry_seed_sync_leftovers_changed = leftovers_changed
        self.agent_foundry_seed_sync_pending_apply = leftovers_changed

        if changed:
            self.agent_foundry_dirty = True

        if bool(getattr(self, "agent_foundry_resync_batch_active", False)) and changed:
            self.agent_foundry_resync_seed_changed = True

        return target_object

    def _sync_foundry_seeded_default_returns_by_grammar(self) -> dict[str, Any]:
        result = {
            "changed": False,
            "leftovers_changed": False,
            "agent_seeded_count": 0,
            "group_seeded_count": 0,
            "task_seeded_count": 0,
            "registry_added_count": 0,
            "registry_removed_count": 0,
            "registry_updated_count": 0,
            "registry_error_count": 0,
        }

        agent_names = self._extract_foundry_agent_names_for_seed()

        registry_result = self._sync_registry_imported_default_returns_by_grammar(
            agent_names=agent_names,
        )
        self._merge_foundry_seed_result(
            aggregate=result,
            item_result=registry_result,
        )
        result["registry_added_count"] = int(registry_result.get("added_count", 0) or 0)
        result["registry_removed_count"] = int(registry_result.get("removed_count", 0) or 0)
        result["registry_updated_count"] = int(registry_result.get("updated_count", 0) or 0)
        result["registry_error_count"] = int(registry_result.get("error_count", 0) or 0)

        for agent_name in agent_names:
            seed_result = self._ensure_foundry_seeded_default_return_by_parser_grammar(
                list_heading=self._build_seeded_default_returns_heading(agent_name),
                item_name="self_agent_name",
                return_description="Agent Name",
                return_value=agent_name,
            )
            self._merge_foundry_seed_result(
                aggregate=result,
                item_result=seed_result,
            )
            if bool(seed_result.get("changed", False)):
                result["agent_seeded_count"] += 1

            group_names = self._extract_foundry_group_names_for_seed(agent_name)
            for group_name in group_names:
                group_seed_result = self._ensure_foundry_seeded_default_return_by_parser_grammar(
                    list_heading=self._build_seeded_default_returns_heading(group_name),
                    item_name="self_group_name",
                    return_description="This group's name",
                    return_value=group_name,
                )
                self._merge_foundry_seed_result(
                    aggregate=result,
                    item_result=group_seed_result,
                )
                if bool(group_seed_result.get("changed", False)):
                    result["group_seeded_count"] += 1

                task_names = self._extract_foundry_task_names_for_seed(group_name)
                for task_name in task_names:
                    task_seed_result = self._ensure_foundry_seeded_default_return_by_parser_grammar(
                        list_heading=self._build_seeded_default_returns_heading(task_name),
                        item_name="self_task_name",
                        return_description="This task's name",
                        return_value=task_name,
                    )
                    self._merge_foundry_seed_result(
                        aggregate=result,
                        item_result=task_seed_result,
                    )
                    if bool(task_seed_result.get("changed", False)):
                        result["task_seeded_count"] += 1

        return result

    def _sync_foundry_imported_packages_by_grammar(
        self,
        *,
        agent_names: list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        result = {
            "changed": False,
            "leftovers_changed": False,
            "imported_package_count": 0,
            "imported_package_block_count": 0,
            "imported_package_error_count": 0,
            "promoted_new_package_count": 0,
            "remaining_new_package_count": 0,
        }

        clean_agent_names = self._unique_foundry_seed_values(list(agent_names or []))
        if not clean_agent_names:
            return result

        package_names = self._extract_foundry_imported_package_names_for_seed()
        package_names = self._unique_foundry_seed_values(package_names)

        promoted_package_names: list[str] = []

        for agent_name in clean_agent_names:
            promotion_result = self._promote_existing_new_packages_for_agent(
                agent_name=agent_name,
            )
            self._merge_foundry_seed_result(
                aggregate=result,
                item_result=promotion_result,
            )

            promoted = list(promotion_result.get("promoted_package_names", []) or [])
            remaining = list(promotion_result.get("remaining_package_names", []) or [])

            promoted_package_names.extend(promoted)
            result["promoted_new_package_count"] += len(promoted)
            result["remaining_new_package_count"] += len(remaining)

        package_names = self._unique_foundry_seed_values(
            list(package_names or []) + list(promoted_package_names or [])
        )

        if not package_names:
            return result

        for agent_name in clean_agent_names:
            list_heading = self._build_imported_packages_heading(agent_name)
            if not list_heading:
                continue

            list_result = self._replace_or_append_foundry_global_fenced_list_values(
                list_heading=list_heading,
                values=package_names,
                append_missing_to_leftovers=True,
            )
            self._merge_foundry_seed_result(
                aggregate=result,
                item_result=list_result,
            )

        for package_name in package_names:
            try:
                package_blocks = self._load_foundry_imported_package_blocks_by_name(
                    package_name=package_name,
                )
            except Exception:
                result["imported_package_error_count"] += 1
                continue

            clean_blocks = [
                str(block or "").strip()
                for block in list(package_blocks or [])
                if str(block or "").strip()
            ]

            if clean_blocks:
                result["imported_package_count"] += 1

            for block_text in clean_blocks:
                block_result = self._ensure_foundry_imported_package_block(
                    block_text=block_text,
                )
                self._merge_foundry_seed_result(
                    aggregate=result,
                    item_result=block_result,
                )
                if bool(block_result.get("changed", False)) or bool(
                    block_result.get("leftovers_changed", False)
                ):
                    result["imported_package_block_count"] += 1

        return result

    def _extract_foundry_imported_package_names_for_seed(self) -> list[str]:
        package_names = self._extract_foundry_task_package_reference_names_for_seed()

        return self._unique_foundry_seed_values(package_names)

    def _extract_foundry_task_package_reference_names_for_seed(self) -> list[str]:
        package_names: list[str] = []

        for node in self._iter_foundry_frontend_nodes_in_order():
            if not isinstance(node, dict):
                continue

            if self._get_foundry_frontend_node_type(node) != "package":
                continue

            data = self._get_foundry_frontend_node_data(node)
            source_container_name = self._normalize_foundry_edit_text(
                data.get("source_container_name", "")
            )

            if not source_container_name:
                continue

            if not source_container_name.endswith(f" {GRAMMAR_SUFFIX_PACKAGES}"):
                continue

            if source_container_name.endswith(f" {GRAMMAR_SUFFIX_IMPORTED_PACKAGES}"):
                continue

            if source_container_name.endswith(f" {GRAMMAR_SUFFIX_NEW_PACKAGES}"):
                continue

            package_name = self._normalize_foundry_task_package_alignment_name(
                self._get_foundry_frontend_node_name(node)
            )
            if package_name:
                package_names.append(package_name)

        return self._unique_foundry_seed_values(package_names)

    def _promote_existing_new_packages_for_agent(
        self,
        *,
        agent_name: str,
    ) -> dict[str, Any]:
        result = {
            "changed": False,
            "leftovers_changed": False,
            "found": False,
            "promoted_package_names": [],
            "remaining_package_names": [],
        }

        new_packages_heading = self._build_new_packages_heading(agent_name)
        if not new_packages_heading:
            return result

        current_values = self._extract_foundry_global_fenced_list_values(
            list_heading=new_packages_heading,
        )
        current_values = self._unique_foundry_seed_values(current_values)

        if not current_values:
            return result

        result["found"] = True

        promoted: list[str] = []
        remaining: list[str] = []

        for package_name in current_values:
            clean_package_name = self._normalize_foundry_edit_text(package_name)
            if not clean_package_name:
                continue

            if self._foundry_package_blueprint_exists_for_seed(
                package_name=clean_package_name,
            ):
                promoted.append(clean_package_name)
            else:
                remaining.append(clean_package_name)

        result["promoted_package_names"] = self._unique_foundry_seed_values(promoted)
        result["remaining_package_names"] = self._unique_foundry_seed_values(remaining)

        if result["promoted_package_names"]:
            replace_result = self._replace_or_append_foundry_global_fenced_list_values(
                list_heading=new_packages_heading,
                values=result["remaining_package_names"],
                append_missing_to_leftovers=False,
            )
            self._merge_foundry_seed_result(
                aggregate=result,
                item_result=replace_result,
            )

        return result

    def _foundry_package_blueprint_exists_for_seed(
        self,
        *,
        package_name: str,
    ) -> bool:
        blueprint_file = self._find_foundry_package_blueprint_file_for_seed(
            package_name=package_name,
        )
        return blueprint_file is not None and blueprint_file.exists() and blueprint_file.is_file()

    def _extract_foundry_package_index_key_from_blueprint_text(
        self,
        *,
        blueprint_text: str,
    ) -> str:
        source_text = str(blueprint_text or "").strip()
        if not source_text:
            return ""

        generic_values = self._extract_foundry_fenced_list_items_from_block(
            block_text=source_text,
            start_heading="Package Index ID",
            strict=False,
        )
        if generic_values:
            return self._normalize_foundry_edit_text(generic_values[0])

        for block_text in self._split_foundry_package_blueprint_text_into_seed_blocks(
            blueprint_text=source_text,
        ):
            parsed_block = self._parse_foundry_seed_block_text(block_text)
            if not parsed_block:
                continue

            heading = self._normalize_foundry_edit_text(
                parsed_block.get("heading", "")
            )
            if not heading.endswith(" Package Index ID"):
                continue

            values = self._extract_foundry_fenced_list_items_from_block(
                block_text=block_text,
                start_heading=heading,
                strict=False,
            )
            if values:
                return self._normalize_foundry_edit_text(values[0])

        return ""

    def _extract_foundry_package_name_from_blueprint_filename(
        self,
        *,
        blueprint_file: Path,
    ) -> str:
        try:
            file_name = Path(blueprint_file).name
        except Exception:
            file_name = str(blueprint_file or "")

        clean_file_name = self._normalize_foundry_edit_text(file_name)
        if not clean_file_name:
            return ""

        if clean_file_name.endswith(".blueprint.txt"):
            clean_file_name = clean_file_name[: -len(".blueprint.txt")]
        elif clean_file_name.endswith(".txt"):
            clean_file_name = clean_file_name[: -len(".txt")]

        return self._normalize_foundry_edit_text(clean_file_name)

    def _extract_foundry_package_key_from_blueprint_filename(
        self,
        *,
        blueprint_file: Path,
    ) -> str:
        package_name = self._extract_foundry_package_name_from_blueprint_filename(
            blueprint_file=blueprint_file,
        )

        if re.match(r"^package_\d{6}$", package_name):
            return package_name

        return ""

    def _extract_foundry_all_task_names_for_seed(self) -> list[str]:
        task_names: list[str] = []

        for node in self._iter_foundry_frontend_nodes_in_order():
            if not isinstance(node, dict):
                continue

            if self._get_foundry_frontend_node_type(node) != "task":
                continue

            task_name = self._get_foundry_frontend_node_name(node)
            if task_name:
                task_names.append(task_name)

        return self._unique_foundry_seed_values(task_names)

    def _normalize_foundry_task_package_alignment_name(self, value: str) -> str:
        clean_value = self._normalize_foundry_edit_text(value)
        if not clean_value:
            return ""

        return re.sub(r"\s+\d+\s*$", "", clean_value).strip()

    def _build_imported_packages_heading(self, owner_name: str) -> str:
        clean_owner_name = self._normalize_foundry_edit_text(owner_name)
        if not clean_owner_name:
            return ""

        return f"{clean_owner_name} {GRAMMAR_SUFFIX_IMPORTED_PACKAGES}"

    def _build_new_packages_heading(self, owner_name: str) -> str:
        clean_owner_name = self._normalize_foundry_edit_text(owner_name)
        if not clean_owner_name:
            return ""

        return f"{clean_owner_name} {GRAMMAR_SUFFIX_NEW_PACKAGES}"

    def _load_foundry_imported_package_blocks_by_name(
        self,
        *,
        package_name: str,
    ) -> list[str]:
        clean_package_name = self._normalize_foundry_edit_text(package_name)
        if not clean_package_name:
            return []

        blueprint_file = self._find_foundry_package_blueprint_file_for_seed(
            package_name=clean_package_name,
        )
        if blueprint_file is None or not blueprint_file.exists():
            return []

        try:
            blueprint_text = blueprint_file.read_text(encoding="utf-8")
        except Exception:
            return []

        return self._split_foundry_package_blueprint_text_into_seed_blocks(
            blueprint_text=blueprint_text,
        )

    def _load_foundry_package_index_records_for_seed(self) -> list[dict[str, Any]]:
        package_index_file = self._get_foundry_package_index_file_for_seed()
        if package_index_file is None or not package_index_file.exists():
            return []

        try:
            raw_text = package_index_file.read_text(encoding="utf-8").strip()
            if not raw_text:
                return []

            package_index = json.loads(raw_text)
        except Exception:
            return []

        if not isinstance(package_index, dict):
            return []

        packages = package_index.get("packages", [])
        if not isinstance(packages, list):
            return []

        return [
            dict(package_record)
            for package_record in packages
            if isinstance(package_record, dict)
        ]

    def _get_foundry_package_index_file_for_seed(self) -> Path | None:
        handoff = self._get_foundry_seed_collection_handoff()
        if handoff is None:
            return None

        for method_name in (
            "get_agent_foundry_package_index_file",
            "get_package_index_file",
        ):
            method = getattr(handoff, method_name, None)
            if not callable(method):
                continue

            try:
                raw_path = method()
            except Exception:
                continue

            if raw_path:
                try:
                    return Path(raw_path).expanduser().resolve()
                except Exception:
                    return Path(str(raw_path))

        return None

    def _get_foundry_packages_directory_for_seed(self) -> Path | None:
        handoff = self._get_foundry_seed_collection_handoff()
        if handoff is None:
            return None

        for method_name in (
            "get_agent_foundry_packages_directory",
            "get_agent_foundry_packages_dir",
            "get_packages_directory",
        ):
            method = getattr(handoff, method_name, None)
            if not callable(method):
                continue

            try:
                raw_path = method()
            except Exception:
                continue

            if raw_path:
                try:
                    return Path(raw_path).expanduser().resolve()
                except Exception:
                    return Path(str(raw_path))

        return None

    def _find_foundry_package_blueprint_file_for_seed(
        self,
        *,
        package_name: str,
    ) -> Path | None:
        clean_package_name = self._normalize_foundry_edit_text(package_name)
        if not clean_package_name:
            return None

        package_records = self._load_foundry_package_index_records_for_seed()
        package_lookup_key = clean_package_name.lower()

        for record in package_records:
            if not isinstance(record, dict):
                continue

            record_names = [
                record.get("package_name", ""),
                record.get("requested_package_name", ""),
                record.get("name", ""),
                record.get("package_key", ""),
                record.get("package_index_key", ""),
            ]
            record_keys = {
                self._normalize_foundry_edit_text(value).lower()
                for value in record_names
                if self._normalize_foundry_edit_text(value)
            }

            if package_lookup_key not in record_keys:
                continue

            blueprint_value = self._normalize_foundry_edit_text(
                record.get("blueprint_file", "")
                or record.get("package_blueprint_file", "")
                or record.get("path", "")
            )
            if not blueprint_value:
                continue

            try:
                blueprint_path = Path(blueprint_value).expanduser().resolve()
            except Exception:
                blueprint_path = Path(blueprint_value)

            if blueprint_path.exists() and blueprint_path.is_file():
                return blueprint_path

        packages_dir = self._get_foundry_packages_directory_for_seed()
        if packages_dir is None or not packages_dir.exists():
            return None

        direct_candidates = [
            packages_dir / f"{clean_package_name}.blueprint.txt",
            packages_dir / f"{clean_package_name}.txt",
        ]

        for candidate_path in direct_candidates:
            try:
                resolved_candidate = candidate_path.expanduser().resolve()
            except Exception:
                resolved_candidate = candidate_path

            if resolved_candidate.exists() and resolved_candidate.is_file():
                return resolved_candidate

        for blueprint_file in sorted(packages_dir.glob("*.blueprint.txt")):
            try:
                blueprint_text = blueprint_file.read_text(encoding="utf-8")
            except Exception:
                continue

            blueprint_package_name = self._extract_foundry_package_name_from_blueprint_text(
                blueprint_text=blueprint_text,
            )
            blueprint_package_key = self._extract_foundry_package_index_key_from_blueprint_text(
                blueprint_text=blueprint_text,
            )

            possible_values = {
                self._normalize_foundry_edit_text(blueprint_package_name).lower(),
                self._normalize_foundry_edit_text(blueprint_package_key).lower(),
                self._normalize_foundry_edit_text(
                    self._extract_foundry_package_name_from_blueprint_filename(
                        blueprint_file=blueprint_file,
                    )
                ).lower(),
            }

            if package_lookup_key in possible_values:
                return blueprint_file.expanduser().resolve()

        return None

    def _extract_foundry_package_name_from_blueprint_text(
        self,
        *,
        blueprint_text: str,
    ) -> str:
        source_text = str(blueprint_text or "").strip()
        if not source_text:
            return ""

        generic_values = self._extract_foundry_fenced_list_items_from_block(
            block_text=source_text,
            start_heading="Package ID",
            strict=False,
        )
        if generic_values:
            return self._normalize_foundry_edit_text(generic_values[0])

        for block_text in self._split_foundry_package_blueprint_text_into_seed_blocks(
            blueprint_text=source_text,
        ):
            parsed_block = self._parse_foundry_seed_block_text(block_text)
            if not parsed_block:
                continue

            heading = self._normalize_foundry_edit_text(
                parsed_block.get("heading", "")
            )
            if not heading.endswith(" Package ID"):
                continue

            values = self._extract_foundry_fenced_list_items_from_block(
                block_text=block_text,
                start_heading=heading,
                strict=False,
            )
            if values:
                return self._normalize_foundry_edit_text(values[0])

        return ""

    def _split_foundry_package_blueprint_text_into_seed_blocks(
        self,
        *,
        blueprint_text: str,
    ) -> list[str]:
        source_text = str(blueprint_text or "").strip()
        if not source_text:
            return []

        lines = source_text.splitlines()
        blocks: list[str] = []
        index = 0

        while index < len(lines):
            heading_line = str(lines[index] or "").strip()
            if not heading_line.endswith(":"):
                index += 1
                continue

            heading = heading_line[:-1].strip()
            if not heading:
                index += 1
                continue

            end_line = f"End {heading}"
            end_index = index + 1

            while end_index < len(lines):
                if str(lines[end_index] or "").strip() == end_line:
                    block_text = "\n".join(lines[index : end_index + 1]).strip()
                    if block_text:
                        blocks.append(block_text)

                    index = end_index + 1
                    break

                end_index += 1
            else:
                index += 1

        return blocks

    def _ensure_foundry_imported_package_block(
        self,
        *,
        block_text: str,
    ) -> dict[str, Any]:
        return self._upsert_foundry_global_fenced_block_from_text(
            block_text=block_text,
            append_missing_to_leftovers=True,
        )

    def _upsert_foundry_global_fenced_block_from_text(
        self,
        *,
        block_text: str,
        append_missing_to_leftovers: bool = True,
    ) -> dict[str, Any]:
        clean_block_text = str(block_text or "").strip()

        result = {
            "found": False,
            "changed": False,
            "leftovers_changed": False,
            "appended_to_leftovers": False,
            "replaced_existing": False,
            "heading": "",
            "node": None,
        }

        if not clean_block_text:
            return result

        parsed_block = self._parse_foundry_seed_block_text(clean_block_text)
        if not parsed_block:
            return result

        heading = self._normalize_foundry_edit_text(parsed_block.get("heading", ""))
        if not heading:
            return result

        result["heading"] = heading

        existing_block = self._find_foundry_global_fenced_block(
            start_heading=heading,
        )

        if bool(existing_block.get("found", False)):
            result["found"] = True
            result["node"] = existing_block.get("node")

            current_block_text = str(
                existing_block.get("block_text", "") or ""
            ).strip()

            if current_block_text == clean_block_text:
                return result

            replaced = self._replace_foundry_block_in_node(
                node=existing_block.get("node"),
                block_range=existing_block.get("range"),
                replacement_block=clean_block_text,
            )

            result["changed"] = bool(replaced)
            result["replaced_existing"] = bool(replaced)
            return result

        if append_missing_to_leftovers:
            appended = self._append_foundry_seed_text_to_leftovers(
                clean_block_text,
            )
            result["changed"] = bool(appended)
            result["leftovers_changed"] = bool(appended)
            result["appended_to_leftovers"] = bool(appended)

        return result

    def _parse_foundry_seed_block_text(self, block_text: str) -> dict[str, str]:
        clean_block_text = str(block_text or "").strip()
        if not clean_block_text:
            return {}

        lines = clean_block_text.splitlines()
        if len(lines) < 2:
            return {}

        heading_line = lines[0].strip()
        if not heading_line.endswith(":"):
            return {}

        heading = heading_line[:-1].strip()
        if not heading:
            return {}

        end_line = f"End {heading}"
        if lines[-1].strip() != end_line:
            return {}

        inner_text = "\n".join(lines[1:-1]).strip()

        return {
            "heading": heading,
            "inner_text": inner_text,
        }

    def _merge_foundry_seed_result(
        self,
        *,
        aggregate: dict[str, Any],
        item_result: dict[str, Any],
    ) -> None:
        if bool(item_result.get("changed", False)):
            aggregate["changed"] = True

        if bool(item_result.get("leftovers_changed", False)):
            aggregate["leftovers_changed"] = True

    def _sync_registry_imported_default_returns_by_grammar(
        self,
        *,
        agent_names: list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        result = {
            "changed": False,
            "leftovers_changed": False,
            "added_count": 0,
            "removed_count": 0,
            "updated_count": 0,
            "error_count": 0,
        }

        clean_agent_names = self._unique_foundry_seed_values(list(agent_names or []))
        if not clean_agent_names:
            return result

        support = _AgentFoundryEditingSeedSupport(
            handoff=self._get_foundry_seed_collection_handoff(),
        )

        registry_records = support.load_storage_registry_default_return_records()
        registry_records = support.dedupe_records(list(registry_records or []))

        if not registry_records:
            result["error_count"] += 1
            return result

        registry_names = [
            str(record.get("name", "") or "").strip()
            for record in registry_records
            if isinstance(record, dict)
            and str(record.get("name", "") or "").strip()
        ]

        registry_records_by_name = {
            str(record.get("name", "") or "").strip().lower(): record
            for record in registry_records
            if isinstance(record, dict)
            and str(record.get("name", "") or "").strip()
        }

        for agent_name in clean_agent_names:
            agent_seeded_list_heading = self._build_seeded_default_returns_heading(agent_name)
            if not agent_seeded_list_heading:
                continue

            current_values_result = self._get_or_create_foundry_global_fenced_list_values(
                list_heading=agent_seeded_list_heading,
            )

            self._merge_foundry_seed_result(
                aggregate=result,
                item_result=current_values_result,
            )

            current_values = list(current_values_result.get("values", []) or [])

            synced_values = self._sync_agent_seeded_default_return_list_values_for_registry(
                current_values=current_values,
                registry_names=registry_names,
            )

            removed_count = max(0, len(current_values) - len(synced_values))
            added_count = max(0, len(synced_values) - len(current_values))

            if synced_values != current_values:
                list_update_result = self._replace_or_append_foundry_global_fenced_list_values(
                    list_heading=agent_seeded_list_heading,
                    values=synced_values,
                    append_missing_to_leftovers=True,
                )
                self._merge_foundry_seed_result(
                    aggregate=result,
                    item_result=list_update_result,
                )
                result["added_count"] += added_count
                result["removed_count"] += removed_count

            for registry_name in registry_names:
                clean_registry_name = str(registry_name or "").strip()
                if not clean_registry_name:
                    continue

                record = registry_records_by_name.get(clean_registry_name.lower())
                if not isinstance(record, dict):
                    continue

                detail_heading = self._build_foundry_parser_detail_heading(
                    list_heading=agent_seeded_list_heading,
                    item_name=clean_registry_name,
                )

                detail_result = self._ensure_foundry_global_detail_block(
                    detail_heading=detail_heading,
                    body_text=str(record.get("text", "") or "").strip(),
                )

                self._merge_foundry_seed_result(
                    aggregate=result,
                    item_result=detail_result,
                )

                if bool(detail_result.get("changed", False)):
                    result["updated_count"] += 1

        return result

    def _sync_agent_seeded_default_return_list_values_for_registry(
        self,
        *,
        current_values: list[str],
        registry_names: list[str],
    ) -> list[str]:
        current_clean_values = self._unique_foundry_seed_values(current_values)
        registry_clean_names = self._unique_foundry_seed_values(registry_names)

        registry_keys = {
            value.lower()
            for value in registry_clean_names
            if value
        }

        protected_keys = {
            value.lower()
            for value in PROTECTED_AGENT_SEEDED_DEFAULT_RETURN_NAMES
            if value
        }

        updated_values: list[str] = []

        for current_value in current_clean_values:
            clean_current_value = self._normalize_foundry_edit_text(current_value)
            if not clean_current_value:
                continue

            current_key = clean_current_value.lower()

            if current_key in registry_keys:
                updated_values.append(clean_current_value)
                continue

            if current_key in protected_keys:
                updated_values.append(clean_current_value)
                continue

            continue

        existing_keys = {
            value.lower()
            for value in updated_values
            if value
        }

        for registry_name in registry_clean_names:
            registry_key = registry_name.lower()
            if not registry_key or registry_key in existing_keys:
                continue

            updated_values.append(registry_name)
            existing_keys.add(registry_key)

        return updated_values

    def _get_foundry_seed_collection_handoff(self) -> Any:
        for accessor_name in (
            "_get_agent_foundry_collection_handoff",
            "_get_collection_handoff",
        ):
            accessor = getattr(self, accessor_name, None)
            if callable(accessor):
                try:
                    handoff = accessor()
                    if handoff is not None:
                        return handoff
                except Exception:
                    pass

        for attribute_name in (
            "collection_handoff",
            "handoff",
            "_handoff",
        ):
            handoff = getattr(self, attribute_name, None)
            if handoff is not None:
                return handoff

        return None

    def _ensure_foundry_seeded_default_return_by_parser_grammar(
        self,
        *,
        list_heading: str,
        item_name: str,
        return_description: str,
        return_value: str,
    ) -> dict[str, Any]:
        body_text = self._build_foundry_default_return_body(
            return_value_name=item_name,
            return_description=return_description,
            return_value=return_value,
        )

        detail_heading = self._build_foundry_parser_detail_heading(
            list_heading=list_heading,
            item_name=item_name,
        )

        return self._ensure_foundry_seeded_list_item_by_global_grammar(
            list_heading=list_heading,
            item_name=item_name,
            detail_heading=detail_heading,
            detail_body_text=body_text,
        )

    def _build_seeded_default_returns_heading(self, owner_name: str) -> str:
        clean_owner_name = self._normalize_foundry_edit_text(owner_name)
        if not clean_owner_name:
            return ""

        return f"{clean_owner_name} {GRAMMAR_SUFFIX_SEEDED_DEFAULT_RETURNS}"

    def _build_foundry_parser_detail_heading(
        self,
        *,
        list_heading: str,
        item_name: str,
    ) -> str:
        clean_list_heading = self._normalize_foundry_edit_text(list_heading)
        clean_item_name = self._normalize_foundry_edit_text(item_name)
        if not clean_list_heading or not clean_item_name:
            return ""

        return f"{clean_list_heading} {clean_item_name}"

    def _build_foundry_default_return_body(
        self,
        *,
        return_value_name: str,
        return_description: str,
        return_value: str,
    ) -> str:
        return (
            f"return_value_name: {str(return_value_name or '').strip()}\n"
            f"return_description: {str(return_description or '').strip()}\n"
            f"return_value: {str(return_value or '').strip()}"
        ).rstrip()

    def _extract_foundry_agent_names_for_seed(self) -> list[str]:
        names = self._extract_foundry_global_fenced_list_values(
            list_heading=f"{ROOT_AGENT_NAME} {GRAMMAR_SUFFIX_ID}",
        )
        if names:
            return self._unique_foundry_seed_values(names)

        for node in self._iter_foundry_frontend_nodes_in_order():
            if not isinstance(node, dict):
                continue

            if self._get_foundry_frontend_node_type(node) != "agent":
                continue

            node_name = self._get_foundry_frontend_node_name(node)
            if node_name:
                names.append(node_name)

        return self._unique_foundry_seed_values(names)

    def _extract_foundry_group_names_for_seed(self, agent_name: str) -> list[str]:
        clean_agent_name = self._normalize_foundry_edit_text(agent_name)
        if not clean_agent_name:
            return []

        names: list[str] = []

        for heading in (
            f"{clean_agent_name} {GRAMMAR_SUFFIX_GROUPS}",
            f"{clean_agent_name} {GRAMMAR_SUFFIX_SEEDED_GROUPS}",
        ):
            names.extend(
                self._extract_foundry_global_fenced_list_values(
                    list_heading=heading,
                )
            )

        return self._unique_foundry_seed_values(names)

    def _extract_foundry_task_names_for_seed(self, group_name: str) -> list[str]:
        clean_group_name = self._normalize_foundry_edit_text(group_name)
        if not clean_group_name:
            return []

        return self._extract_foundry_global_fenced_list_values(
            list_heading=f"{clean_group_name} {GRAMMAR_SUFFIX_TASKS}",
        )

    def _extract_first_nonempty_value_after_heading(
        self,
        *,
        source_text: str,
        heading: str,
    ) -> str:
        source = str(source_text or "")
        clean_heading = self._normalize_foundry_edit_text(heading)
        if not source.strip() or not clean_heading:
            return ""

        heading_match = re.search(
            rf"(?im)^\s*{re.escape(clean_heading)}\s*:?\s*$",
            source,
        )
        if heading_match is None:
            return ""

        for raw_line in source[heading_match.end():].splitlines():
            line = str(raw_line or "").strip()
            if not line:
                continue

            if line.endswith(":"):
                return ""

            if re.match(r"(?i)^End\s+", line):
                return ""

            if line.startswith("- "):
                return line[2:].strip()

            return line

        return ""

    def _ensure_foundry_seeded_list_item_by_global_grammar(
        self,
        *,
        list_heading: str,
        item_name: str,
        detail_heading: str = "",
        detail_body_text: str = "",
    ) -> dict[str, Any]:
        clean_list_heading = self._normalize_foundry_edit_text(list_heading)
        clean_item_name = self._normalize_foundry_edit_text(item_name)
        clean_detail_heading = self._normalize_foundry_edit_text(detail_heading)
        clean_detail_body = str(detail_body_text or "").strip()

        result = {
            "list_found": False,
            "list_changed": False,
            "list_appended_to_leftovers": False,
            "detail_found": False,
            "detail_changed": False,
            "detail_appended_to_leftovers": False,
            "changed": False,
            "leftovers_changed": False,
        }

        if not clean_list_heading or not clean_item_name:
            return result

        list_result = self._ensure_foundry_global_fenced_list_contains_item(
            list_heading=clean_list_heading,
            item_name=clean_item_name,
            append_missing_to_leftovers=True,
        )

        result["list_found"] = bool(list_result.get("found", False))
        result["list_changed"] = bool(list_result.get("changed", False))
        result["list_appended_to_leftovers"] = bool(
            list_result.get("appended_to_leftovers", False)
        )

        if clean_detail_heading and clean_detail_body:
            detail_result = self._ensure_foundry_global_detail_block(
                detail_heading=clean_detail_heading,
                body_text=clean_detail_body,
            )

            result["detail_found"] = bool(detail_result.get("found", False))
            result["detail_changed"] = bool(detail_result.get("changed", False))
            result["detail_appended_to_leftovers"] = bool(
                detail_result.get("leftovers_changed", False)
            )

        result["changed"] = (
            result["list_changed"]
            or result["list_appended_to_leftovers"]
            or result["detail_changed"]
            or result["detail_appended_to_leftovers"]
        )
        result["leftovers_changed"] = (
            result["list_appended_to_leftovers"]
            or result["detail_appended_to_leftovers"]
        )

        return result

    def _ensure_foundry_global_fenced_list_contains_item(
        self,
        *,
        list_heading: str,
        item_name: str,
        append_missing_to_leftovers: bool = False,
    ) -> dict[str, Any]:
        clean_list_heading = self._normalize_foundry_edit_text(list_heading)
        clean_item_name = self._normalize_foundry_edit_text(item_name)

        result = {
            "found": False,
            "changed": False,
            "appended_to_leftovers": False,
            "node": None,
            "values": [],
        }

        if not clean_list_heading or not clean_item_name:
            return result

        block = self._find_foundry_global_fenced_block(
            start_heading=clean_list_heading,
        )

        if not bool(block.get("found", False)):
            replacement_block = self._compose_foundry_fenced_list_block(
                list_heading=clean_list_heading,
                values=[clean_item_name],
            )

            if append_missing_to_leftovers:
                result["appended_to_leftovers"] = self._append_foundry_seed_text_to_leftovers(
                    replacement_block
                )

            result["values"] = [clean_item_name]
            result["changed"] = bool(result["appended_to_leftovers"])
            return result

        node = block.get("node")
        block_range = block.get("range")
        block_text = str(block.get("block_text", "") or "")

        values = self._extract_foundry_fenced_list_items_from_block(
            block_text=block_text,
            start_heading=clean_list_heading,
        )

        updated_values = self._unique_foundry_seed_values(
            list(values or []) + [clean_item_name],
        )

        result["found"] = True
        result["node"] = node
        result["values"] = updated_values

        if updated_values == values:
            return result

        replacement_block = self._compose_foundry_fenced_list_block(
            list_heading=clean_list_heading,
            values=updated_values,
        )

        changed = self._replace_foundry_block_in_node(
            node=node,
            block_range=block_range,
            replacement_block=replacement_block,
        )

        result["changed"] = bool(changed)
        return result

    def _get_or_create_foundry_global_fenced_list_values(
        self,
        *,
        list_heading: str,
    ) -> dict[str, Any]:
        clean_list_heading = self._normalize_foundry_edit_text(list_heading)

        result = {
            "found": False,
            "changed": False,
            "leftovers_changed": False,
            "values": [],
        }

        if not clean_list_heading:
            return result

        block = self._find_foundry_global_fenced_block(
            start_heading=clean_list_heading,
        )

        if bool(block.get("found", False)):
            result["found"] = True
            result["values"] = self._extract_foundry_fenced_list_items_from_block(
                block_text=str(block.get("block_text", "") or ""),
                start_heading=clean_list_heading,
                strict=False,
            )
            return result

        list_block = self._compose_foundry_fenced_list_block(
            list_heading=clean_list_heading,
            values=[],
        )
        changed = self._append_foundry_seed_text_to_leftovers(list_block)

        result["changed"] = bool(changed)
        result["leftovers_changed"] = bool(changed)
        result["values"] = []
        return result

    def _replace_or_append_foundry_global_fenced_list_values(
        self,
        *,
        list_heading: str,
        values: list[str],
        append_missing_to_leftovers: bool = True,
    ) -> dict[str, Any]:
        clean_list_heading = self._normalize_foundry_edit_text(list_heading)
        clean_values = self._unique_foundry_seed_values(values)

        result = {
            "found": False,
            "changed": False,
            "leftovers_changed": False,
            "appended_to_leftovers": False,
            "values": clean_values,
        }

        if not clean_list_heading:
            return result

        replacement_block = self._compose_foundry_fenced_list_block(
            list_heading=clean_list_heading,
            values=clean_values,
        )

        block = self._find_foundry_global_fenced_block(
            start_heading=clean_list_heading,
        )

        if bool(block.get("found", False)):
            result["found"] = True
            changed = self._replace_foundry_block_in_node(
                node=block.get("node"),
                block_range=block.get("range"),
                replacement_block=replacement_block,
            )
            result["changed"] = bool(changed)
            return result

        if append_missing_to_leftovers:
            changed = self._append_foundry_seed_text_to_leftovers(replacement_block)
            result["changed"] = bool(changed)
            result["leftovers_changed"] = bool(changed)
            result["appended_to_leftovers"] = bool(changed)

        return result

    def _ensure_foundry_global_detail_block(
        self,
        *,
        detail_heading: str,
        body_text: str,
    ) -> dict[str, Any]:
        clean_detail_heading = self._normalize_foundry_edit_text(detail_heading)
        clean_body_text = str(body_text or "").strip()

        result = {
            "found": False,
            "changed": False,
            "leftovers_changed": False,
            "node": None,
        }

        if not clean_detail_heading or not clean_body_text:
            return result

        expected_block = self._compose_foundry_detail_block(
            detail_heading=clean_detail_heading,
            body_text=clean_body_text,
        )

        block = self._find_foundry_global_fenced_block(
            start_heading=clean_detail_heading,
        )

        if bool(block.get("found", False)):
            result["found"] = True
            result["node"] = block.get("node")

            current_block = str(block.get("block_text", "") or "").strip()
            if current_block == expected_block:
                return result

            changed = self._replace_foundry_block_in_node(
                node=block.get("node"),
                block_range=block.get("range"),
                replacement_block=expected_block,
            )
            result["changed"] = bool(changed)
            return result

        leftovers_changed = self._append_foundry_seed_text_to_leftovers(expected_block)
        result["leftovers_changed"] = bool(leftovers_changed)
        return result

    def _extract_foundry_global_fenced_list_values(
        self,
        *,
        list_heading: str,
    ) -> list[str]:
        clean_list_heading = self._normalize_foundry_edit_text(list_heading)
        if not clean_list_heading:
            return []

        block = self._find_foundry_global_fenced_block(
            start_heading=clean_list_heading,
        )
        if not bool(block.get("found", False)):
            return []

        return self._extract_foundry_fenced_list_items_from_block(
            block_text=str(block.get("block_text", "") or ""),
            start_heading=clean_list_heading,
            strict=False,
        )

    def _find_foundry_global_fenced_block(
        self,
        *,
        start_heading: str,
        end_heading: str | None = None,
    ) -> dict[str, Any]:
        clean_start_heading = self._normalize_foundry_edit_text(start_heading)
        clean_end_heading = (
            self._normalize_foundry_edit_text(end_heading)
            if end_heading is not None
            else f"End {clean_start_heading}"
        )

        if not clean_start_heading or not clean_end_heading:
            return self._empty_foundry_fenced_block_result()

        for target_node in self._iter_foundry_parser_search_content_nodes():
            content = self._get_foundry_frontend_node_text(target_node)

            block = self._find_foundry_fenced_block_in_text(
                source_text=content,
                start_heading=clean_start_heading,
                end_heading=clean_end_heading,
            )
            if not isinstance(block, dict):
                continue

            return {
                "found": True,
                "node": target_node,
                "block_text": str(block.get("block_text", "") or "").rstrip(),
                "inner_text": str(block.get("inner_text", "") or "").rstrip(),
                "range": block.get("range"),
            }

        return self._empty_foundry_fenced_block_result()

    def _empty_foundry_fenced_block_result(self) -> dict[str, Any]:
        return {
            "found": False,
            "node": None,
            "block_text": "",
            "inner_text": "",
            "range": None,
        }

    def _iter_foundry_parser_search_content_nodes(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        for node in self._iter_foundry_frontend_nodes_in_order():
            if not isinstance(node, dict):
                continue

            if self._get_foundry_frontend_node_area(node) not in {
                NODE_AREA_CONTENT,
                NODE_AREA_FUSED,
            }:
                continue

            if "content" not in node:
                continue

            data = self._get_foundry_frontend_node_data(node)
            if bool(data.get("parser_search_exclude", False)):
                continue

            results.append(node)

        return results

    def _find_foundry_fenced_block_in_text(
        self,
        *,
        source_text: str,
        start_heading: str,
        end_heading: str,
    ) -> dict[str, Any] | None:
        source = str(source_text or "")
        clean_start_heading = self._normalize_foundry_edit_text(start_heading)
        clean_end_heading = self._normalize_foundry_edit_text(end_heading)

        if not source.strip() or not clean_start_heading or not clean_end_heading:
            return None

        start_pattern = rf"(?im)^\s*{re.escape(clean_start_heading)}\s*:\s*$"
        start_match = re.search(start_pattern, source)
        if start_match is None:
            return None

        end_pattern = rf"(?im)^\s*{re.escape(clean_end_heading)}\s*$"
        end_match = re.search(end_pattern, source[start_match.end():])
        if end_match is None:
            return None

        inner_start = start_match.end()
        inner_end = start_match.end() + end_match.start()
        block_end = start_match.end() + end_match.end()

        return {
            "block_text": source[start_match.start():block_end].strip(),
            "inner_text": source[inner_start:inner_end].strip(),
            "range": (start_match.start(), block_end),
        }

    def _extract_foundry_fenced_list_items_from_block(
        self,
        *,
        block_text: str,
        start_heading: str,
        end_heading: str | None = None,
        strict: bool = True,
    ) -> list[str]:
        clean_start_heading = self._normalize_foundry_edit_text(start_heading)
        clean_end_heading = (
            self._normalize_foundry_edit_text(end_heading)
            if end_heading is not None
            else f"End {clean_start_heading}"
        )

        block = self._find_foundry_fenced_block_in_text(
            source_text=block_text,
            start_heading=clean_start_heading,
            end_heading=clean_end_heading,
        )
        if not isinstance(block, dict):
            return []

        inner_text = str(block.get("inner_text", "") or "")
        results: list[str] = []

        for raw_line in inner_text.splitlines():
            line = str(raw_line or "").strip()
            if not line:
                continue

            bullet_match = re.match(r"^[-*]\s+(?P<value>.*)$", line)
            if bullet_match is None:
                if strict:
                    return []
                continue

            value = str(bullet_match.group("value") or "").strip()
            if value:
                results.append(value)

        return results

    def _compose_foundry_fenced_list_block(
        self,
        *,
        list_heading: str,
        values: list[str],
    ) -> str:
        clean_list_heading = self._normalize_foundry_edit_text(list_heading)
        clean_values = self._unique_foundry_seed_values(values)

        if clean_values:
            body = "\n".join(
                f"- {value}"
                for value in clean_values
                if str(value or "").strip()
            )
            return (
                f"{clean_list_heading}:\n"
                f"{body}\n"
                f"End {clean_list_heading}"
            ).rstrip()

        return (
            f"{clean_list_heading}:\n"
            f"End {clean_list_heading}"
        ).rstrip()

    def _replace_foundry_block_in_node(
        self,
        *,
        node: Any,
        block_range: Any,
        replacement_block: str,
    ) -> bool:
        if not isinstance(node, dict):
            return False

        if not isinstance(block_range, tuple) or len(block_range) != 2:
            return False

        start, end = block_range
        try:
            start = int(start)
            end = int(end)
        except Exception:
            return False

        current_content = self._get_foundry_frontend_node_text(node)
        clean_replacement = str(replacement_block or "").strip()
        if not clean_replacement:
            return False

        updated_content = (
            current_content[:start].rstrip()
            + "\n\n"
            + clean_replacement
            + "\n\n"
            + current_content[end:].lstrip()
        ).strip()

        if updated_content == current_content.rstrip():
            return False

        self._set_foundry_frontend_node_text(node, updated_content)
        return True

    def _append_foundry_seed_text_to_leftovers(self, text: str) -> bool:
        clean_text = str(text or "").strip()
        if not clean_text:
            return False

        leftovers_node = self._get_foundry_frontend_node_by_id(ROOT_LEFTOVERS_ID)
        if not isinstance(leftovers_node, dict):
            return False

        current_text = self._get_foundry_frontend_node_text(leftovers_node).rstrip()
        if clean_text in current_text:
            return False

        if current_text:
            updated_text = f"{current_text}\n\n{clean_text}".rstrip()
        else:
            updated_text = clean_text

        self._set_foundry_frontend_node_text(leftovers_node, updated_text)
        return True

    def _compose_foundry_detail_block(
        self,
        *,
        detail_heading: str,
        body_text: str,
    ) -> str:
        clean_detail_heading = self._normalize_foundry_edit_text(detail_heading)
        clean_body = str(body_text or "").strip()

        if not clean_detail_heading or not clean_body:
            return ""

        return (
            f"{clean_detail_heading}:\n"
            f"{clean_body}\n"
            f"End {clean_detail_heading}"
        ).rstrip()

    def _unique_foundry_seed_values(self, values: list[str]) -> list[str]:
        results: list[str] = []
        seen: set[str] = set()

        for value in list(values or []):
            clean_value = self._normalize_foundry_edit_text(value)
            if not clean_value:
                continue

            key = clean_value.lower()
            if key in seen:
                continue

            seen.add(key)
            results.append(clean_value)

        return results

    def _is_foundry_frontend_node_editable(self, node: dict[str, Any]) -> bool:
        if not isinstance(node, dict):
            return False

        node_id = self._get_foundry_frontend_node_id(node)
        if not node_id:
            return False

        if self._get_foundry_frontend_node_area(node) not in {
            NODE_AREA_CONTENT,
            NODE_AREA_FUSED,
        }:
            return False

        if "content" not in node:
            return False

        data = self._get_foundry_frontend_node_data(node)

        if data.get("editable") is False:
            return False

        if data.get("source") == "agent_schema_file":
            return False

        if node_id == ROOT_VIEWER_ID:
            return False

        return True

    def _get_foundry_frontend_node_text_field(self, node: dict[str, Any]) -> str:
        if not isinstance(node, dict):
            return ""

        if "content" in node:
            return "content"

        return ""

    def _get_foundry_frontend_node_text(self, node: dict[str, Any]) -> str:
        if not isinstance(node, dict):
            return ""

        return str(node.get("content", "") or "")

    def _set_foundry_frontend_node_text(
        self,
        node: dict[str, Any],
        new_text: str,
    ) -> None:
        if not isinstance(node, dict):
            return

        if "content" not in node:
            return

        node["content"] = str(new_text or "").rstrip()

    def _hydrate_agent_foundry_ui_from_frontend_object(self) -> None:
        frontend_object = self._get_current_foundry_frontend_object()

        render = getattr(self, "_render_agent_foundry_frontend_object", None)
        if callable(render):
            render(frontend_object=frontend_object)

    def _build_foundry_node_edit_title(self, node: dict[str, Any]) -> str:
        node_name = self._get_foundry_frontend_node_name(node)
        node_type = self._get_foundry_frontend_node_type(node)

        if node_name and node_type:
            return f"Edit {node_name} ({node_type})"

        if node_name:
            return f"Edit {node_name}"

        if node_type:
            return f"Edit {node_type}"

        node_id = self._get_foundry_frontend_node_id(node)
        if node_id:
            return f"Edit {node_id}"

        return "Edit Agent Foundry Node"

    def _mark_agent_foundry_dirty_scope(self, scope: tuple[str, str]) -> None:
        self.agent_foundry_dirty = True

        edited_scopes = getattr(self, "agent_foundry_edited_scopes", None)
        if not isinstance(edited_scopes, set):
            edited_scopes = set()
            self.agent_foundry_edited_scopes = edited_scopes

        edited_scopes.add(scope)

    def _normalize_foundry_edit_node_id(self, value: Any) -> str:
        return str(value or "").strip()

    def _normalize_foundry_edit_text(self, value: Any) -> str:
        return str(value or "").strip()


class _AgentFoundryEditingSeedSupport:
    def __init__(self, *, handoff: Any = None) -> None:
        self._handoff = handoff

    def load_storage_registry_default_return_records(self) -> list[dict[str, str]]:
        entries = self.load_storage_registry_entries_for_default_returns()
        if not entries:
            return []

        all_entries = self.load_storage_registry_entries_raw()
        repo_root = self.extract_repo_root_from_registry_entries(all_entries)

        records: list[dict[str, str]] = []

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            key = str(entry.get("key", "") or "").strip()
            if not key:
                continue

            label = str(entry.get("label", "") or "").strip()
            if not label:
                label = key

            value = self.resolve_storage_registry_entry_path(
                entry=entry,
                repo_root=repo_root,
            )
            value = self.normalize_registry_path(value)

            records.append(
                self.build_default_return_record(
                    return_value_name=key,
                    return_description=label,
                    return_value=value,
                )
            )

        return self.dedupe_records(records)

    def load_storage_registry_entries_for_default_returns(self) -> list[dict[str, Any]]:
        entries = self.load_storage_registry_entries_raw()
        results: list[dict[str, Any]] = []

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            key = str(entry.get("key", "") or "").strip()
            if not key:
                continue

            if key == "repo_root":
                continue

            if bool(entry.get("agent_foundry_default_excluded", False)):
                continue

            if bool(entry.get("read_only", False)) and not bool(
                entry.get("agent_foundry_default_include_read_only", False)
            ):
                continue

            results.append(dict(entry))

        return results

    def load_storage_registry_entries_raw(self) -> list[dict[str, Any]]:
        registry_data = self.load_storage_registry_data()
        entries = registry_data.get("entries", [])
        if not isinstance(entries, list):
            return []

        return [
            dict(entry)
            for entry in entries
            if isinstance(entry, dict)
        ]

    def load_storage_registry_data(self) -> dict[str, Any]:
        handoff = self._handoff

        if handoff is not None:
            for method_name in (
                "get_storage_registry",
                "load_storage_registry",
                "load_storage_registry_data",
                "load_registry",
            ):
                method = getattr(handoff, method_name, None)
                if not callable(method):
                    continue

                try:
                    registry_data = method()
                except Exception:
                    continue

                if isinstance(registry_data, dict):
                    return registry_data

        registry_path = self.find_storage_registry_path()
        if registry_path is None:
            return {}

        try:
            raw_text = registry_path.read_text(encoding="utf-8")
            parsed_json = json.loads(raw_text)
        except Exception:
            return {}

        if not isinstance(parsed_json, dict):
            return {}

        return parsed_json

    def find_storage_registry_path(self) -> Path | None:
        candidate_paths: list[Path] = []

        handoff = self._handoff

        if handoff is not None:
            for method_name in (
                "get_storage_registry_path",
                "get_storage_registry_file",
                "get_registry_path",
                "get_registry_file",
            ):
                method = getattr(handoff, method_name, None)
                if not callable(method):
                    continue

                try:
                    raw_path = method()
                    if raw_path:
                        candidate_paths.append(Path(str(raw_path)))
                except Exception:
                    pass

            get_base_dir = getattr(handoff, "get_base_dir", None)
            if callable(get_base_dir):
                try:
                    base_dir = Path(get_base_dir()).expanduser().resolve()
                    candidate_paths.append(
                        base_dir
                        / "Storage"
                        / "Generated Artifacts"
                        / "System"
                        / "storage_registry.json"
                    )
                except Exception:
                    pass

        for candidate_path in candidate_paths:
            try:
                resolved_path = Path(candidate_path).expanduser().resolve()
            except Exception:
                continue

            if resolved_path.exists() and resolved_path.is_file():
                return resolved_path

        return None

    def extract_repo_root_from_registry_entries(
        self,
        entries: list[dict[str, Any]],
    ) -> Path | None:
        for entry in list(entries or []):
            if not isinstance(entry, dict):
                continue

            key = str(entry.get("key", "") or "").strip()
            if key != "repo_root":
                continue

            for value_key in ("path", "value", "default", "resolved_path"):
                raw_path = str(entry.get(value_key, "") or "").strip()
                if not raw_path:
                    continue

                try:
                    return Path(raw_path).expanduser().resolve()
                except Exception:
                    return Path(raw_path)

        handoff = self._handoff
        if handoff is not None:
            get_repo_root = getattr(handoff, "get_repo_root", None)
            if callable(get_repo_root):
                try:
                    return Path(get_repo_root()).expanduser().resolve()
                except Exception:
                    return None

        return None

    def resolve_storage_registry_entry_path(
        self,
        *,
        entry: dict[str, Any],
        repo_root: Path | None,
    ) -> str:
        raw_path = ""

        for key in ("path", "value", "default", "resolved_path"):
            value = str(entry.get(key, "") or "").strip()
            if value:
                raw_path = value
                break

        if not raw_path:
            return ""

        raw_path = raw_path.replace("__repo_root__", str(repo_root or ""))
        raw_path = raw_path.replace("{repo_root}", str(repo_root or ""))

        uses_repo_root = bool(entry.get("uses_repo_root", False))

        try:
            if uses_repo_root and repo_root is not None:
                return str((repo_root / Path(raw_path)).expanduser().resolve())

            return str(Path(raw_path).expanduser().resolve())
        except Exception:
            if uses_repo_root and repo_root is not None:
                return str(repo_root / Path(raw_path))

            return raw_path

    def normalize_registry_path(self, value: str) -> str:
        clean_value = str(value or "").strip()
        if not clean_value:
            return ""

        previous_value = None
        normalized_value = clean_value

        while previous_value != normalized_value:
            previous_value = normalized_value
            normalized_value = normalized_value.replace("\\\\", "\\")

        return normalized_value

    def build_default_return_record(
        self,
        *,
        return_value_name: str,
        return_description: str,
        return_value: str,
    ) -> dict[str, str]:
        clean_name = str(return_value_name or "").strip()
        clean_description = str(return_description or "").strip()
        clean_value = str(return_value or "").strip()

        body_text = (
            f"return_value_name: {clean_name}\n"
            f"return_description: {clean_description}\n"
            f"return_value: {clean_value}"
        ).rstrip()

        return {
            "name": clean_name,
            "text": body_text,
        }

    @staticmethod
    def dedupe_records(records: list[dict[str, str]]) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        seen: set[str] = set()

        for record in list(records or []):
            if not isinstance(record, dict):
                continue

            name = str(record.get("name", "") or "").strip()
            text = str(record.get("text", "") or "").strip()
            if not name or not text:
                continue

            key = name.lower()
            if key in seen:
                continue

            seen.add(key)
            results.append(
                {
                    "name": name,
                    "text": text,
                }
            )

        return results
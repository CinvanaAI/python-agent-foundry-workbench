from __future__ import annotations

import json
import re
from typing import Any

from Environment.agent_foundry.foundry_filtering import AgentFoundryNodeMapFilterSurface


NODE_AREA_CONTENT = "content"
NODE_AREA_CHILDREN = "children"
NODE_AREA_FUSED = "fused"

ROOT_AGENT_ID = "agent"
ROOT_LEFTOVERS_ID = "leftovers"
ROOT_VIEWER_ID = "viewer"

SECTION_CONTROL_NAME = "Control"
SECTION_COMPOSE_NAME = "Compose"
SECTION_BLUEPRINT_NAME = "Blueprint"

VIRTUAL_COMPOSE_NODE_ID = "__compose__"

COMPOSE_OUTPUT_EXCLUDED_NODE_IDS = {
    ROOT_AGENT_ID,
    VIRTUAL_COMPOSE_NODE_ID,
}

SAVE_BLUEPRINT_EXCLUDED_NODE_IDS = {
    ROOT_LEFTOVERS_ID,
    ROOT_VIEWER_ID,
    VIRTUAL_COMPOSE_NODE_ID,
}

DEFAULT_RUNTIME_FILE_NAME = "runtime.json"

KIND_TASK = "task"
KIND_PACKAGE = "package"

GRAMMAR_SUFFIX_WORKFLOW = "Workflow"
GRAMMAR_SUFFIX_PACKAGE_LOGIC = "Logic"
GRAMMAR_SUFFIX_NEW_PACKAGES = "New Packages"

NEW_PACKAGE_CONTAINER_KINDS = {
    "new_packages",
    "agent_new_packages",
}

NEW_PACKAGE_CONTAINER_NAMES = {
    "new packages",
}


class AgentFoundryComposerMixin:
    def _sync_blueprint_from_current_foundry(self) -> str:
        return self._refresh_agent_foundry_control_display()

    def _refresh_agent_foundry_blueprint_tab(self) -> str:
        return self._refresh_agent_foundry_control_display()

    def _refresh_agent_foundry_blueprint_display_from_filter_payload(
        self,
        filter_payload: dict[str, Any] | None,
    ) -> str:
        return self._refresh_agent_foundry_control_display_from_filter_payload(
            filter_payload,
        )

    def _refresh_agent_foundry_blueprint_display_from_navigation_path(
        self,
        navigation_path: list[str] | tuple[str, ...] | None,
    ) -> str:
        return self._refresh_agent_foundry_control_display()

    def _refresh_agent_foundry_control_display(self) -> str:
        payload = AgentFoundryNodeMapFilterSurface.get_owner_filter_state(self)
        return self._refresh_agent_foundry_control_display_from_filter_payload(payload)

    def _refresh_agent_foundry_control_display_from_filter_payload(
        self,
        filter_payload: dict[str, Any] | None,
    ) -> str:
        output_text = self._compose_agent_foundry_control_display_text(
            filter_payload=filter_payload,
        )

        self._set_agent_foundry_control_display_text(output_text)
        return output_text

    def _set_agent_foundry_control_display_text(self, output_text: str) -> None:
        text = str(output_text or "").rstrip()
        if text:
            text += "\n"

        for section_name in (SECTION_COMPOSE_NAME, SECTION_BLUEPRINT_NAME):
            setter = getattr(self, "_set_named_foundry_section_text", None)
            if callable(setter):
                try:
                    setter(section_name, text)
                    continue
                except Exception:
                    pass

            legacy_setter = getattr(self, "_set_foundry_section_text", None)
            if callable(legacy_setter):
                try:
                    legacy_setter(section_name, text)
                except Exception:
                    pass

    def _compose_agent_foundry_save_texts_from_frontend_object(
        self,
        *,
        frontend_object: dict[str, Any] | None = None,
        materialize_new_packages: bool = True,
    ) -> tuple[str, str, str, dict[str, Any]]:
        source_object = self._get_composer_frontend_object(frontend_object=frontend_object)

        if materialize_new_packages:
            self._materialize_new_packages_from_frontend_object(
                frontend_object=source_object,
            )

        blueprint_text = self._compose_agent_foundry_node_map_text(
            frontend_object=source_object,
            filter_payload=AgentFoundryNodeMapFilterSurface._empty_filter_payload(),
            excluded_node_ids=SAVE_BLUEPRINT_EXCLUDED_NODE_IDS,
        )

        leftovers_text = self._get_composer_root_node_content(
            frontend_object=source_object,
            node_id=ROOT_LEFTOVERS_ID,
        )

        runtime_file = build_foundry_runtime_file_from_frontend_object(
            frontend_object=source_object,
        )

        return (
            blueprint_text.rstrip(),
            leftovers_text.rstrip(),
            "",
            runtime_file,
        )

    def _compose_agent_foundry_blueprint_text_from_frontend_object(
        self,
        *,
        frontend_object: dict[str, Any],
    ) -> str:
        blueprint_text, _leftovers_text, _agent_json_text, _runtime_file = (
            self._compose_agent_foundry_save_texts_from_frontend_object(
                frontend_object=frontend_object,
                materialize_new_packages=False,
            )
        )
        return blueprint_text

    def _compose_agent_foundry_agent_json_text_from_frontend_object(
        self,
        *,
        frontend_object: dict[str, Any] | None = None,
    ) -> str:
        return ""

    def _compose_agent_foundry_agent_schema_from_frontend_object(
        self,
        *,
        frontend_object: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {}

    def _compose_blueprint_from_foundry(
        self,
        *,
        frontend_object: dict[str, Any] | None = None,
    ) -> str:
        return self._compose_agent_foundry_control_display_text(
            frontend_object=frontend_object,
            filter_payload=AgentFoundryNodeMapFilterSurface.get_owner_filter_state(self),
        )

    def _compose_agent_foundry_control_display_text(
        self,
        *,
        frontend_object: dict[str, Any] | None = None,
        filter_payload: dict[str, Any] | None = None,
    ) -> str:
        source_object = self._get_composer_frontend_object(frontend_object=frontend_object)

        return self._compose_agent_foundry_node_map_text(
            frontend_object=source_object,
            filter_payload=filter_payload,
            excluded_node_ids=COMPOSE_OUTPUT_EXCLUDED_NODE_IDS,
        )

    def _compose_agent_foundry_node_map_text(
        self,
        *,
        frontend_object: dict[str, Any],
        filter_payload: dict[str, Any] | None = None,
        excluded_node_ids: set[str] | None = None,
    ) -> str:
        source_object = self._get_composer_frontend_object(frontend_object=frontend_object)
        payload = AgentFoundryNodeMapFilterSurface._normalize_filter_payload(filter_payload)

        clean_excluded_node_ids = {
            self._normalize_composer_node_id(node_id)
            for node_id in set(excluded_node_ids or set())
            if self._normalize_composer_node_id(node_id)
        }

        mode = str(payload.get("mode", "") or "all").strip().lower()
        included_node_ids = {
            self._normalize_composer_node_id(node_id)
            for node_id in list(payload.get("included_node_ids", []) or [])
            if self._normalize_composer_node_id(node_id)
        }

        content_blocks: list[str] = []
        visited_node_ids: set[str] = set()

        for root_node_id in self._get_composer_root_node_ids(
            source_object,
            excluded_node_ids=clean_excluded_node_ids,
        ):
            self._append_control_display_blocks_in_order(
                frontend_object=source_object,
                node_id=root_node_id,
                content_blocks=content_blocks,
                visited_node_ids=visited_node_ids,
                mode=mode,
                included_node_ids=included_node_ids,
                excluded_node_ids=clean_excluded_node_ids,
            )

        display_text = "\n\n".join(
            block.strip()
            for block in content_blocks
            if str(block or "").strip()
        ).rstrip()

        if display_text:
            display_text += "\n"

        return display_text

    def _compose_single_foundry_node_subtree_text(
        self,
        *,
        frontend_object: dict[str, Any],
        node_id: str,
    ) -> str:
        clean_node_id = self._normalize_composer_node_id(node_id)
        if not clean_node_id:
            return ""

        content_blocks: list[str] = []
        visited_node_ids: set[str] = set()

        self._append_control_display_blocks_in_order(
            frontend_object=frontend_object,
            node_id=clean_node_id,
            content_blocks=content_blocks,
            visited_node_ids=visited_node_ids,
            mode="all",
            included_node_ids=set(),
            excluded_node_ids=set(),
        )

        return "\n\n".join(
            block.strip()
            for block in content_blocks
            if str(block or "").strip()
        ).rstrip()

    def _append_control_display_blocks_in_order(
        self,
        *,
        frontend_object: dict[str, Any],
        node_id: str,
        content_blocks: list[str],
        visited_node_ids: set[str],
        mode: str,
        included_node_ids: set[str],
        excluded_node_ids: set[str] | None = None,
    ) -> None:
        clean_excluded_node_ids = {
            self._normalize_composer_node_id(value)
            for value in set(excluded_node_ids or set())
            if self._normalize_composer_node_id(value)
        }

        clean_node_id = self._normalize_composer_node_id(node_id)
        if not clean_node_id:
            return

        if clean_node_id in clean_excluded_node_ids:
            return

        if clean_node_id in visited_node_ids:
            return

        visited_node_ids.add(clean_node_id)

        node = self._get_composer_node(
            frontend_object=frontend_object,
            node_id=clean_node_id,
        )
        if not isinstance(node, dict):
            return

        include_node = mode == "all" or clean_node_id in included_node_ids
        if include_node:
            content = get_node_content(node).strip()
            if content:
                content_blocks.append(content)

        for child_node_id in self._get_composer_child_node_ids(
            node,
            excluded_node_ids=clean_excluded_node_ids,
        ):
            self._append_control_display_blocks_in_order(
                frontend_object=frontend_object,
                node_id=child_node_id,
                content_blocks=content_blocks,
                visited_node_ids=visited_node_ids,
                mode=mode,
                included_node_ids=included_node_ids,
                excluded_node_ids=clean_excluded_node_ids,
            )

    def _materialize_new_packages_from_frontend_object(
        self,
        *,
        frontend_object: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Create Package Foundry blueprint files from parsed New Packages nodes.

        The parser stores list membership as child nodes. Some older/raw paths may
        still keep bullet text in container content, so this materializer supports
        both shapes:
            - New Packages container content containing bullet items
            - New Packages container children containing package nodes
        """
        package_requests = self._collect_new_package_requests_from_frontend_object(
            frontend_object=frontend_object,
        )

        if not package_requests:
            self.agent_foundry_last_new_package_materialization = []
            return []

        create_callable = getattr(
            self,
            "_create_package_foundry_blueprint_file",
            None,
        )
        if not callable(create_callable):
            raise AttributeError(
                "Workspace must expose _create_package_foundry_blueprint_file(...) "
                "before New Packages can be materialized."
            )

        results: list[dict[str, Any]] = []

        for request in package_requests:
            package_name = normalize_text(request.get("package_name", ""))
            if not package_name:
                continue

            package_node_id = normalize_text(request.get("package_node_id", ""))
            if not package_node_id:
                results.append(
                    {
                        "status": "error",
                        "error": normalize_text(
                            request.get("error", "No matching package node was found.")
                        ),
                        "package_name": package_name,
                        "requested_package_name": package_name,
                        "source_node_id": normalize_text(
                            request.get("source_node_id", "")
                        ),
                        "package_node_id": "",
                    }
                )
                continue

            blueprint_text = self._compose_single_foundry_node_subtree_text(
                frontend_object=frontend_object,
                node_id=package_node_id,
            )

            try:
                created = create_callable(
                    package_name=package_name,
                    blueprint_text=blueprint_text,
                )
                if not isinstance(created, dict):
                    created = {}

                results.append(
                    {
                        "status": normalize_text(created.get("status", "created"))
                        or "created",
                        "package_name": normalize_text(
                            created.get("package_name", package_name)
                        ),
                        "requested_package_name": package_name,
                        "blueprint_file": normalize_text(
                            created.get("blueprint_file", "")
                        ),
                        "source_node_id": normalize_text(
                            request.get("source_node_id", "")
                        ),
                        "package_node_id": package_node_id,
                        "workspace_result": created,
                    }
                )
            except FileExistsError as exc:
                results.append(
                    {
                        "status": "skipped",
                        "reason": str(exc),
                        "package_name": package_name,
                        "requested_package_name": package_name,
                        "source_node_id": normalize_text(
                            request.get("source_node_id", "")
                        ),
                        "package_node_id": package_node_id,
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "status": "error",
                        "error": str(exc),
                        "package_name": package_name,
                        "requested_package_name": package_name,
                        "source_node_id": normalize_text(
                            request.get("source_node_id", "")
                        ),
                        "package_node_id": package_node_id,
                    }
                )

        self.agent_foundry_last_new_package_materialization = results
        return results

    def _collect_new_package_requests_from_frontend_object(
        self,
        *,
        frontend_object: dict[str, Any],
    ) -> list[dict[str, Any]]:
        nodes = get_frontend_nodes(frontend_object)

        requests: list[dict[str, Any]] = []
        seen_package_names: set[str] = set()

        for node_id, node in nodes.items():
            if not self._is_new_package_container_node(node):
                continue

            package_names = self._extract_new_package_names_from_container_node(
                frontend_object=frontend_object,
                container_node=node,
            )

            for package_name in package_names:
                clean_package_name = normalize_text(package_name)
                if not clean_package_name:
                    continue

                package_name_key = normalize_lookup_key(clean_package_name)
                if not package_name_key:
                    continue

                if package_name_key in seen_package_names:
                    continue

                package_node = self._find_package_node_by_name(
                    frontend_object=frontend_object,
                    package_name=clean_package_name,
                )
                if not isinstance(package_node, dict):
                    requests.append(
                        {
                            "package_name": clean_package_name,
                            "package_node_id": "",
                            "source_node_id": normalize_text(node_id),
                            "error": "No matching package node was found.",
                        }
                    )
                    seen_package_names.add(package_name_key)
                    continue

                seen_package_names.add(package_name_key)

                requests.append(
                    {
                        "package_name": clean_package_name,
                        "package_node_id": get_node_id(package_node),
                        "source_node_id": normalize_text(node_id),
                    }
                )

        return requests

    def _extract_new_package_names_from_container_node(
        self,
        *,
        frontend_object: dict[str, Any],
        container_node: dict[str, Any],
    ) -> list[str]:
        """Return package names from a New Packages container.

        Parser-built list containers usually have empty content and store their
        list items as child package nodes. Older/direct content paths may still
        contain a fenced bullet list, so preserve that as the first fallback.
        """
        package_names = extract_list_items_from_node(container_node)
        if package_names:
            return unique_preserve_order(package_names)

        child_names: list[str] = []

        for child_node in get_child_nodes(
            frontend_object=frontend_object,
            node=container_node,
        ):
            if not isinstance(child_node, dict):
                continue

            if get_node_kind(child_node) != KIND_PACKAGE:
                continue

            child_name = get_node_display_name(child_node)
            if child_name:
                child_names.append(child_name)

        if child_names:
            return unique_preserve_order(child_names)

        return []

    def _is_new_package_container_node(self, node: dict[str, Any] | None) -> bool:
        if not isinstance(node, dict):
            return False

        node_kind = normalize_lookup_key(get_node_kind(node)).replace(" ", "_")
        if node_kind in NEW_PACKAGE_CONTAINER_KINDS:
            return True

        node_name = normalize_lookup_key(get_node_display_name(node))
        if node_name in NEW_PACKAGE_CONTAINER_NAMES:
            return True

        outer_heading = normalize_lookup_key(
            extract_outer_fence_heading(get_node_content(node))
        )
        if outer_heading == normalize_lookup_key(GRAMMAR_SUFFIX_NEW_PACKAGES):
            return True

        if outer_heading.endswith(
            " " + normalize_lookup_key(GRAMMAR_SUFFIX_NEW_PACKAGES)
        ):
            return True

        return False

    def _find_package_node_by_name(
        self,
        *,
        frontend_object: dict[str, Any],
        package_name: str,
    ) -> dict[str, Any] | None:
        package_name_key = normalize_lookup_key(package_name)
        if not package_name_key:
            return None

        for node in get_frontend_nodes(frontend_object).values():
            if get_node_kind(node) != KIND_PACKAGE:
                continue

            if normalize_lookup_key(get_node_display_name(node)) == package_name_key:
                return node

        return None

    def _get_composer_frontend_object(
        self,
        *,
        frontend_object: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if isinstance(frontend_object, dict):
            return frontend_object

        getter = getattr(self, "_get_current_foundry_frontend_object", None)
        if callable(getter):
            current_object = getter()
            if isinstance(current_object, dict):
                return current_object

        current_object = getattr(self, "agent_foundry_frontend_object", None)
        if isinstance(current_object, dict):
            return current_object

        return self._empty_composer_frontend_object()

    def _empty_composer_frontend_object(self) -> dict[str, Any]:
        return empty_frontend_object()

    def _get_composer_root_node_ids(
        self,
        frontend_object: dict[str, Any],
        *,
        excluded_node_ids: set[str] | None = None,
    ) -> list[str]:
        if not isinstance(frontend_object, dict):
            return []

        root_node_ids = frontend_object.get("root_node_ids", [])
        if not isinstance(root_node_ids, list):
            return []

        clean_excluded_node_ids = {
            self._normalize_composer_node_id(node_id)
            for node_id in set(excluded_node_ids or COMPOSE_OUTPUT_EXCLUDED_NODE_IDS)
            if self._normalize_composer_node_id(node_id)
        }

        return self._unique_composer_node_ids(
            [
                node_id
                for node_id in root_node_ids
                if self._normalize_composer_node_id(node_id) not in clean_excluded_node_ids
            ],
            excluded_node_ids=clean_excluded_node_ids,
        )

    def _get_composer_node(
        self,
        *,
        frontend_object: dict[str, Any],
        node_id: str,
    ) -> dict[str, Any] | None:
        clean_node_id = self._normalize_composer_node_id(node_id)
        if clean_node_id == VIRTUAL_COMPOSE_NODE_ID:
            return None

        return get_frontend_node(
            frontend_object=frontend_object,
            node_id=clean_node_id,
        )

    def _get_composer_root_node_content(
        self,
        *,
        frontend_object: dict[str, Any],
        node_id: str,
    ) -> str:
        node = self._get_composer_node(
            frontend_object=frontend_object,
            node_id=node_id,
        )
        if not isinstance(node, dict):
            return ""

        return get_node_content(node).rstrip()

    def _get_composer_child_node_ids(
        self,
        node: dict[str, Any],
        *,
        excluded_node_ids: set[str] | None = None,
    ) -> list[str]:
        if not isinstance(node, dict):
            return []

        children = node.get("children", [])
        if not isinstance(children, list):
            return []

        clean_excluded_node_ids = {
            self._normalize_composer_node_id(node_id)
            for node_id in set(excluded_node_ids or COMPOSE_OUTPUT_EXCLUDED_NODE_IDS)
            if self._normalize_composer_node_id(node_id)
        }

        return self._unique_composer_node_ids(
            [
                node_id
                for node_id in children
                if self._normalize_composer_node_id(node_id) not in clean_excluded_node_ids
            ],
            excluded_node_ids=clean_excluded_node_ids,
        )

    def _unique_composer_node_ids(
        self,
        node_ids: list[Any] | tuple[Any, ...] | set[Any],
        *,
        excluded_node_ids: set[str] | None = None,
    ) -> list[str]:
        results: list[str] = []
        seen: set[str] = set()
        clean_excluded_node_ids = {
            self._normalize_composer_node_id(node_id)
            for node_id in set(excluded_node_ids or COMPOSE_OUTPUT_EXCLUDED_NODE_IDS)
            if self._normalize_composer_node_id(node_id)
        }

        for node_id in list(node_ids or []):
            clean_node_id = self._normalize_composer_node_id(node_id)
            if not clean_node_id or clean_node_id in seen:
                continue

            if clean_node_id in clean_excluded_node_ids:
                continue

            seen.add(clean_node_id)
            results.append(clean_node_id)

        return results

    def _normalize_composer_node_id(self, value: Any) -> str:
        return str(value or "").strip()

    def _get_document_frontend_object(
        self,
        *,
        frontend_object: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._get_composer_frontend_object(frontend_object=frontend_object)

    def _empty_document_frontend_object(self) -> dict[str, Any]:
        return self._empty_composer_frontend_object()

    def _get_document_root_node_ids(
        self,
        frontend_object: dict[str, Any],
    ) -> list[str]:
        return self._get_composer_root_node_ids(frontend_object)

    def _get_document_node(
        self,
        *,
        frontend_object: dict[str, Any],
        node_id: str,
    ) -> dict[str, Any] | None:
        return self._get_composer_node(
            frontend_object=frontend_object,
            node_id=node_id,
        )

    def _get_document_child_node_ids(
        self,
        node: dict[str, Any],
    ) -> list[str]:
        return self._get_composer_child_node_ids(node)

    def _unique_document_node_ids(
        self,
        node_ids: list[Any] | tuple[Any, ...] | set[Any],
    ) -> list[str]:
        return self._unique_composer_node_ids(node_ids)

    def _normalize_document_node_id(self, value: Any) -> str:
        return self._normalize_composer_node_id(value)


def build_foundry_runtime_file_from_frontend_object(
    *,
    frontend_object: dict[str, Any],
) -> dict[str, Any]:
    runtime_data = build_foundry_runtime_data_from_frontend_object(
        frontend_object=frontend_object,
    )

    return {
        "file_name": DEFAULT_RUNTIME_FILE_NAME,
        "content": json.dumps(
            runtime_data,
            indent=2,
            ensure_ascii=False,
            sort_keys=False,
        ).rstrip(),
        "data": runtime_data,
    }


def build_foundry_runtime_data_from_frontend_object(
    *,
    frontend_object: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(frontend_object, dict):
        frontend_object = empty_frontend_object()

    ordered_nodes = get_frontend_nodes_in_order(frontend_object)

    tasks: list[dict[str, Any]] = []
    packages: list[dict[str, Any]] = []

    seen_task_names: set[str] = set()
    seen_package_names: set[str] = set()

    for node in ordered_nodes:
        node_kind = get_node_kind(node)

        if node_kind == KIND_TASK:
            task_row = build_runtime_task_from_node(node)
            task_name_key = normalize_lookup_key(task_row.get("task_name", ""))

            if task_name_key and task_name_key not in seen_task_names:
                seen_task_names.add(task_name_key)
                tasks.append(task_row)

            continue

        if node_kind == KIND_PACKAGE:
            package_row = build_runtime_package_from_node(node)

            package_name_key = normalize_lookup_key(package_row.get("package_name", ""))
            logic_source = normalize_text(package_row.get("logic_source", ""))

            if not package_name_key:
                continue

            if not logic_source:
                continue

            if package_name_key in seen_package_names:
                continue

            seen_package_names.add(package_name_key)
            packages.append(package_row)

    return {
        "tasks": tasks,
        "packages": packages,
    }


def build_runtime_task_from_node(node: dict[str, Any]) -> dict[str, Any]:
    task_name = get_node_display_name(node)

    workflow_source = extract_owned_suffix_block_body(
        node=node,
        suffix=GRAMMAR_SUFFIX_WORKFLOW,
    )

    return {
        "task_name": task_name,
        "file_name": build_workflow_file_name(task_name),
        "workflow_source": workflow_source,
    }


def build_runtime_package_from_node(node: dict[str, Any]) -> dict[str, Any]:
    package_name = get_node_display_name(node)

    logic_source = extract_owned_suffix_block_body(
        node=node,
        suffix=GRAMMAR_SUFFIX_PACKAGE_LOGIC,
    )

    return {
        "package_name": package_name,
        "file_name": build_package_logic_file_name(package_name),
        "logic_source": logic_source,
    }


def empty_frontend_object() -> dict[str, Any]:
    return {
        "object_type": "agent_foundry_frontend_object",
        "schema_version": "node_map.v1",
        "root_node_ids": [],
        "nodes": {},
    }


def get_frontend_nodes(frontend_object: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(frontend_object, dict):
        return {}

    nodes = frontend_object.get("nodes", {})
    if not isinstance(nodes, dict):
        return {}

    return {
        normalize_text(node_id): node
        for node_id, node in nodes.items()
        if normalize_text(node_id) and isinstance(node, dict)
    }


def get_frontend_node(
    *,
    frontend_object: dict[str, Any],
    node_id: str,
) -> dict[str, Any] | None:
    clean_node_id = normalize_text(node_id)
    if not clean_node_id:
        return None

    return get_frontend_nodes(frontend_object).get(clean_node_id)


def get_frontend_nodes_in_order(
    frontend_object: dict[str, Any],
) -> list[dict[str, Any]]:
    nodes = get_frontend_nodes(frontend_object)
    root_node_ids = frontend_object.get("root_node_ids", [])
    if not isinstance(root_node_ids, list):
        root_node_ids = []

    ordered: list[dict[str, Any]] = []
    seen_node_ids: set[str] = set()

    for root_node_id in root_node_ids:
        append_node_and_descendants(
            frontend_object=frontend_object,
            node_id=normalize_text(root_node_id),
            ordered=ordered,
            seen_node_ids=seen_node_ids,
        )

    for node_id in nodes.keys():
        append_node_and_descendants(
            frontend_object=frontend_object,
            node_id=node_id,
            ordered=ordered,
            seen_node_ids=seen_node_ids,
        )

    return ordered


def append_node_and_descendants(
    *,
    frontend_object: dict[str, Any],
    node_id: str,
    ordered: list[dict[str, Any]],
    seen_node_ids: set[str],
) -> None:
    clean_node_id = normalize_text(node_id)
    if not clean_node_id:
        return

    if clean_node_id in seen_node_ids:
        return

    node = get_frontend_node(
        frontend_object=frontend_object,
        node_id=clean_node_id,
    )
    if not isinstance(node, dict):
        return

    seen_node_ids.add(clean_node_id)
    ordered.append(node)

    for child_node_id in get_node_child_ids(node):
        append_node_and_descendants(
            frontend_object=frontend_object,
            node_id=child_node_id,
            ordered=ordered,
            seen_node_ids=seen_node_ids,
        )


def get_node_id(node: dict[str, Any] | None) -> str:
    if not isinstance(node, dict):
        return ""

    return normalize_text(node.get("id", ""))


def get_node_display_name(node: dict[str, Any] | None) -> str:
    if not isinstance(node, dict):
        return ""

    name = normalize_text(node.get("name", ""))
    if name:
        return name

    return get_node_id(node)


def get_node_kind(node: dict[str, Any] | None) -> str:
    if not isinstance(node, dict):
        return ""

    return normalize_text(node.get("kind", ""))


def get_node_area(node: dict[str, Any] | None) -> str:
    if not isinstance(node, dict):
        return NODE_AREA_CONTENT

    area = normalize_text(node.get("area", "")).lower()
    if area in {NODE_AREA_CONTENT, NODE_AREA_CHILDREN, NODE_AREA_FUSED}:
        return area

    return NODE_AREA_CONTENT


def get_node_content(node: dict[str, Any] | None) -> str:
    if not isinstance(node, dict):
        return ""

    return str(node.get("content", "") or "")


def get_node_data(node: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(node, dict):
        return {}

    data = node.get("data", {})
    if not isinstance(data, dict):
        return {}

    return data


def get_node_data_text(
    data: dict[str, Any] | None,
    key: str,
) -> str:
    if not isinstance(data, dict):
        return ""

    return normalize_text(data.get(key, ""))


def get_node_child_ids(node: dict[str, Any] | None) -> list[str]:
    if not isinstance(node, dict):
        return []

    children = node.get("children", [])
    if not isinstance(children, list):
        return []

    results: list[str] = []
    seen: set[str] = set()

    for raw_child_id in children:
        child_id = normalize_text(raw_child_id)
        if not child_id:
            continue

        if child_id in seen:
            continue

        seen.add(child_id)
        results.append(child_id)

    return results


def get_child_nodes(
    *,
    frontend_object: dict[str, Any],
    node: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for child_id in get_node_child_ids(node):
        child_node = get_frontend_node(
            frontend_object=frontend_object,
            node_id=child_id,
        )
        if isinstance(child_node, dict):
            results.append(child_node)

    return results


def extract_owned_suffix_block_body(
    *,
    node: dict[str, Any] | None,
    suffix: str,
) -> str:
    if not isinstance(node, dict):
        return ""

    owner_name = get_node_display_name(node)
    clean_suffix = normalize_heading(suffix)
    if not owner_name or not clean_suffix:
        return ""

    return extract_fenced_body_by_heading(
        text=get_node_content(node),
        heading=f"{owner_name} {clean_suffix}",
    )


def extract_fenced_body_by_heading(
    *,
    text: str,
    heading: str,
) -> str:
    source = str(text or "")
    clean_heading = normalize_heading(heading)

    if not source or not clean_heading:
        return ""

    pattern = re.compile(
        rf"(?ims)"
        rf"^\s*{re.escape(clean_heading)}\s*:\s*\n"
        rf"(?P<body>.*?)"
        rf"(?:\n)?^\s*End\s+{re.escape(clean_heading)}\s*$"
    )

    match = pattern.search(source)
    if not match:
        return ""

    return str(match.group("body") or "").strip()


def extract_outer_fence_heading(text: str) -> str:
    lines = [line.rstrip() for line in str(text or "").splitlines()]
    lines = trim_blank_edge_lines(lines)

    if not lines:
        return ""

    match = re.match(r"^\s*(?P<heading>.+?)\s*:\s*$", lines[0])
    if not match:
        return ""

    heading = normalize_heading(match.group("heading"))

    if len(lines) < 2:
        return heading

    final_line = lines[-1].strip()
    if final_line == f"End {heading}":
        return heading

    return ""


def strip_outer_fence(text: str) -> str:
    lines = [line.rstrip() for line in str(text or "").splitlines()]
    lines = trim_blank_edge_lines(lines)

    if len(lines) < 2:
        return "\n".join(lines).strip()

    first_match = re.match(r"^\s*(?P<heading>.+?)\s*:\s*$", lines[0])
    if not first_match:
        return "\n".join(lines).strip()

    heading = normalize_heading(first_match.group("heading"))
    final_line = lines[-1].strip()

    if final_line != f"End {heading}":
        return "\n".join(lines).strip()

    return "\n".join(lines[1:-1]).strip()


def extract_bullet_items_from_text(text: str) -> list[str]:
    results: list[str] = []

    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        bullet_match = re.match(r"^[-*]\s+(?P<value>.+?)\s*$", line)
        if not bullet_match:
            continue

        value = normalize_text(bullet_match.group("value"))
        if value:
            results.append(value)

    return unique_preserve_order(results)


def extract_list_items_from_node(node: dict[str, Any] | None) -> list[str]:
    return extract_bullet_items_from_text(strip_outer_fence(get_node_content(node)))


def build_workflow_file_name(task_name: str) -> str:
    stem = sanitize_runtime_file_stem(task_name)
    if not stem:
        stem = "workflow"

    return f"{stem}_workflow.py"


def build_package_logic_file_name(package_name: str) -> str:
    stem = sanitize_runtime_file_stem(package_name)
    if not stem:
        stem = "package_logic"

    return f"{stem}.py"


def sanitize_runtime_file_stem(value: Any) -> str:
    text = normalize_text(value).strip().lower()
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def normalize_heading(value: Any) -> str:
    text = normalize_text(value)
    text = text.replace("\r", " ").replace("\n", " ")

    while "  " in text:
        text = text.replace("  ", " ")

    return text.strip().rstrip(":")


def normalize_lookup_key(value: Any) -> str:
    text = normalize_text(value).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def trim_blank_edge_lines(lines: list[str]) -> list[str]:
    results = list(lines or [])

    while results and not str(results[0] or "").strip():
        results.pop(0)

    while results and not str(results[-1] or "").strip():
        results.pop()

    return results


def unique_preserve_order(values: list[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()

    for value in values:
        clean_value = normalize_text(value)
        if not clean_value:
            continue

        key = clean_value.lower()
        if key in seen:
            continue

        seen.add(key)
        results.append(clean_value)

    return results
from __future__ import annotations

import re
from typing import Any


NODE_AREA_CONTENT = "content"
NODE_AREA_CHILDREN = "children"
NODE_AREA_FUSED = "fused"

ROOT_AGENT_ID = "agent"
ROOT_TASK_PACKAGE_ALIGNMENT_ID = "task_package_alignment"
ROOT_PACKAGES_ID = "packages"
ROOT_LEFTOVERS_ID = "leftovers"
ROOT_VIEWER_ID = "viewer"

ROOT_AGENT_NAME = "Agent"
ROOT_TASK_PACKAGE_ALIGNMENT_NAME = "Task Package Alignment"
ROOT_PACKAGES_NAME = "Packages"
ROOT_LEFTOVERS_NAME = "Leftovers"
ROOT_VIEWER_NAME = "Viewer"

GRAMMAR_SUFFIX_ID = "ID"
GRAMMAR_SUFFIX_METADATA = "Metadata"
GRAMMAR_SUFFIX_TRIGGERS = "Triggers"
GRAMMAR_SUFFIX_SEEDED_DEFAULT_RETURNS = "Seeded Default Returns"
GRAMMAR_SUFFIX_DEFAULT_RETURNS = "Default Returns"
GRAMMAR_SUFFIX_SEEDED_GROUPS = "Seeded Groups"
GRAMMAR_SUFFIX_GROUPS = "Groups"
GRAMMAR_SUFFIX_TASKS = "Tasks"
GRAMMAR_SUFFIX_WORKFLOW = "Workflow"
GRAMMAR_SUFFIX_PROMPTS = "Prompts"
GRAMMAR_SUFFIX_MEMORY = "Memory"
GRAMMAR_SUFFIX_PACKAGES = "Packages"
GRAMMAR_SUFFIX_IMPORTED_PACKAGES = "Imported Packages"
GRAMMAR_SUFFIX_NEW_PACKAGES = "New Packages"

GRAMMAR_SUFFIX_LOGIC_SOURCE = "Logic Source"
GRAMMAR_SUFFIX_ARGUMENTS = "Arguments"
GRAMMAR_SUFFIX_RETURNS = "Returns"

GRAMMAR_SUFFIX_PACKAGE_ID = "Package ID"
GRAMMAR_SUFFIX_PACKAGE_INDEX_ID = "Package Index ID"
GRAMMAR_SUFFIX_PACKAGE_LOGIC = "Logic"
GRAMMAR_SUFFIX_PACKAGE_REQUIRED_REPLACEMENT_LIST = "Required Replacement List"
GRAMMAR_SUFFIX_PACKAGE_OPTIONAL_REPLACEMENT_LIST = "Optional Replacement List"
GRAMMAR_SUFFIX_PACKAGE_ARGUMENT_LIST = "Argument List"
GRAMMAR_SUFFIX_PACKAGE_RETURN_LIST = "Return List"
GRAMMAR_SUFFIX_PACKAGE_RECOGNITION_LIST = "Recognition List"

GRAMMAR_PACKAGE_CONTENT_SUFFIXES = [
    GRAMMAR_SUFFIX_PACKAGE_ID,
    GRAMMAR_SUFFIX_PACKAGE_INDEX_ID,
    GRAMMAR_SUFFIX_PACKAGE_LOGIC,
    GRAMMAR_SUFFIX_PACKAGE_REQUIRED_REPLACEMENT_LIST,
    GRAMMAR_SUFFIX_PACKAGE_OPTIONAL_REPLACEMENT_LIST,
    GRAMMAR_SUFFIX_PACKAGE_ARGUMENT_LIST,
    GRAMMAR_SUFFIX_PACKAGE_RETURN_LIST,
    GRAMMAR_SUFFIX_PACKAGE_RECOGNITION_LIST,
]


class AgentFoundryParsingMixin:
    def _build_raw_foundry_frontend_object(
        self,
        *,
        source_text: str = "",
        viewer_content: str = "",
    ) -> tuple[dict[str, Any], str]:
        frontend_object = self._build_empty_frontend_object(
            leftovers_content=str(source_text or "").rstrip(),
            viewer_content=str(viewer_content or "").rstrip(),
        )

        self.agent_foundry_frontend_object = frontend_object

        self._run_mapping_group(
            mapping_group={
                "shared": {
                    "owner_node_id": ROOT_AGENT_ID,
                },
                "items": [
                    {
                        "list_suffix": GRAMMAR_SUFFIX_ID,
                        "container_kind": "agent_ids",
                        "item_kind": "agent",
                        "child_area": NODE_AREA_FUSED,
                        "mount_at_root": True,
                        "item_content_suffixes": [
                            GRAMMAR_SUFFIX_SEEDED_DEFAULT_RETURNS,
                            GRAMMAR_SUFFIX_DEFAULT_RETURNS,
                            GRAMMAR_SUFFIX_IMPORTED_PACKAGES,
                            GRAMMAR_SUFFIX_NEW_PACKAGES,
                            GRAMMAR_SUFFIX_SEEDED_GROUPS,
                            GRAMMAR_SUFFIX_GROUPS,
                        ],
                        "child_mapping_group": {
                            "items": [
                                {
                                    "shared": {
                                        "item_kind": "default_return",
                                        "child_area": NODE_AREA_CONTENT,
                                        "include_container_name_in_item_search": True,
                                    },
                                    "items": [
                                        {
                                            "list_suffix": GRAMMAR_SUFFIX_SEEDED_DEFAULT_RETURNS,
                                            "container_kind": "agent_seeded_default_returns",
                                        },
                                        {
                                            "list_suffix": GRAMMAR_SUFFIX_DEFAULT_RETURNS,
                                            "container_kind": "agent_default_returns",
                                        },
                                    ],
                                },
                                {
                                    "shared": {
                                        "item_kind": "package",
                                        "child_area": NODE_AREA_FUSED,
                                        "mount_node_id": ROOT_PACKAGES_ID,
                                        "item_content_suffixes": GRAMMAR_PACKAGE_CONTENT_SUFFIXES,
                                        "child_mapping_group": {
                                            "items": [
                                                {
                                                    "list_suffix": GRAMMAR_SUFFIX_PACKAGE_REQUIRED_REPLACEMENT_LIST,
                                                    "container_kind": "package_required_replacements",
                                                    "item_kind": "replacement",
                                                    "child_area": NODE_AREA_CONTENT,
                                                    "include_container_name_in_item_search": True,
                                                },
                                                {
                                                    "list_suffix": GRAMMAR_SUFFIX_PACKAGE_OPTIONAL_REPLACEMENT_LIST,
                                                    "container_kind": "package_optional_replacements",
                                                    "item_kind": "replacement",
                                                    "child_area": NODE_AREA_CONTENT,
                                                    "include_container_name_in_item_search": True,
                                                },
                                                {
                                                    "list_suffix": GRAMMAR_SUFFIX_PACKAGE_ARGUMENT_LIST,
                                                    "container_kind": "package_arguments",
                                                    "item_kind": "argument",
                                                    "child_area": NODE_AREA_CONTENT,
                                                    "include_container_name_in_item_search": True,
                                                },
                                                {
                                                    "list_suffix": GRAMMAR_SUFFIX_PACKAGE_RETURN_LIST,
                                                    "container_kind": "package_returns",
                                                    "item_kind": "return",
                                                    "child_area": NODE_AREA_CONTENT,
                                                    "include_container_name_in_item_search": True,
                                                },
                                                {
                                                    "list_suffix": GRAMMAR_SUFFIX_PACKAGE_RECOGNITION_LIST,
                                                    "container_kind": "package_recognitions",
                                                    "item_kind": "recognition",
                                                    "child_area": NODE_AREA_CONTENT,
                                                    "include_container_name_in_item_search": True,
                                                },
                                            ],
                                        },
                                    },
                                    "items": [
                                        {
                                            "list_suffix": GRAMMAR_SUFFIX_IMPORTED_PACKAGES,
                                            "container_kind": "imported_packages",
                                        },
                                        {
                                            "list_suffix": GRAMMAR_SUFFIX_NEW_PACKAGES,
                                            "container_kind": "agent_new_packages",
                                        },
                                    ],
                                },
                                {
                                    "shared": {
                                        "item_kind": "group",
                                        "child_area": NODE_AREA_FUSED,
                                        "mount_at_root": True,
                                        "item_content_suffixes": [
                                            GRAMMAR_SUFFIX_METADATA,
                                            GRAMMAR_SUFFIX_SEEDED_DEFAULT_RETURNS,
                                            GRAMMAR_SUFFIX_DEFAULT_RETURNS,
                                            GRAMMAR_SUFFIX_TASKS,
                                        ],
                                        "child_mapping_group": {
                                            "items": [
                                                {
                                                    "shared": {
                                                        "item_kind": "default_return",
                                                        "child_area": NODE_AREA_CONTENT,
                                                        "include_container_name_in_item_search": True,
                                                    },
                                                    "items": [
                                                        {
                                                            "list_suffix": GRAMMAR_SUFFIX_SEEDED_DEFAULT_RETURNS,
                                                            "container_kind": "group_seeded_default_returns",
                                                        },
                                                        {
                                                            "list_suffix": GRAMMAR_SUFFIX_DEFAULT_RETURNS,
                                                            "container_kind": "group_default_returns",
                                                        },
                                                    ],
                                                },
                                                {
                                                    "list_suffix": GRAMMAR_SUFFIX_TASKS,
                                                    "container_kind": "tasks",
                                                    "item_kind": "task",
                                                    "child_area": NODE_AREA_FUSED,
                                                    "mount_at_root": True,
                                                    "item_content_suffixes": [
                                                        GRAMMAR_SUFFIX_METADATA,
                                                        GRAMMAR_SUFFIX_TRIGGERS,
                                                        GRAMMAR_SUFFIX_WORKFLOW,
                                                        GRAMMAR_SUFFIX_SEEDED_DEFAULT_RETURNS,
                                                        GRAMMAR_SUFFIX_DEFAULT_RETURNS,
                                                        GRAMMAR_SUFFIX_PROMPTS,
                                                        GRAMMAR_SUFFIX_MEMORY,
                                                        GRAMMAR_SUFFIX_PACKAGES,
                                                    ],
                                                    "child_mapping_group": {
                                                        "items": [
                                                            {
                                                                "shared": {
                                                                    "item_kind": "default_return",
                                                                    "child_area": NODE_AREA_CONTENT,
                                                                    "include_container_name_in_item_search": True,
                                                                },
                                                                "items": [
                                                                    {
                                                                        "list_suffix": GRAMMAR_SUFFIX_SEEDED_DEFAULT_RETURNS,
                                                                        "container_kind": "task_seeded_default_returns",
                                                                    },
                                                                    {
                                                                        "list_suffix": GRAMMAR_SUFFIX_DEFAULT_RETURNS,
                                                                        "container_kind": "task_default_returns",
                                                                    },
                                                                ],
                                                            },
                                                            {
                                                                "list_suffix": GRAMMAR_SUFFIX_PROMPTS,
                                                                "container_kind": "prompts",
                                                                "item_kind": "prompt",
                                                                "child_area": NODE_AREA_CONTENT,
                                                                "include_container_name_in_item_search": True,
                                                            },
                                                            {
                                                                "list_suffix": GRAMMAR_SUFFIX_MEMORY,
                                                                "container_kind": "memory",
                                                                "item_kind": "memory",
                                                                "child_area": NODE_AREA_CONTENT,
                                                                "include_container_name_in_item_search": True,
                                                            },
                                                            {
                                                                "list_suffix": GRAMMAR_SUFFIX_PACKAGES,
                                                                "container_kind": "packages",
                                                                "item_kind": "package",
                                                                "child_area": NODE_AREA_FUSED,
                                                                "mount_node_id": ROOT_TASK_PACKAGE_ALIGNMENT_ID,
                                                                "item_content_suffixes": GRAMMAR_PACKAGE_CONTENT_SUFFIXES,
                                                                "child_mapping_group": {
                                                                    "items": [
                                                                        {
                                                                            "list_suffix": GRAMMAR_SUFFIX_PACKAGE_REQUIRED_REPLACEMENT_LIST,
                                                                            "container_kind": "package_required_replacements",
                                                                            "item_kind": "replacement",
                                                                            "child_area": NODE_AREA_CONTENT,
                                                                            "include_container_name_in_item_search": True,
                                                                        },
                                                                        {
                                                                            "list_suffix": GRAMMAR_SUFFIX_PACKAGE_OPTIONAL_REPLACEMENT_LIST,
                                                                            "container_kind": "package_optional_replacements",
                                                                            "item_kind": "replacement",
                                                                            "child_area": NODE_AREA_CONTENT,
                                                                            "include_container_name_in_item_search": True,
                                                                        },
                                                                        {
                                                                            "list_suffix": GRAMMAR_SUFFIX_PACKAGE_ARGUMENT_LIST,
                                                                            "container_kind": "package_arguments",
                                                                            "item_kind": "argument",
                                                                            "child_area": NODE_AREA_CONTENT,
                                                                            "include_container_name_in_item_search": True,
                                                                        },
                                                                        {
                                                                            "list_suffix": GRAMMAR_SUFFIX_PACKAGE_RETURN_LIST,
                                                                            "container_kind": "package_returns",
                                                                            "item_kind": "return",
                                                                            "child_area": NODE_AREA_CONTENT,
                                                                            "include_container_name_in_item_search": True,
                                                                        },
                                                                        {
                                                                            "list_suffix": GRAMMAR_SUFFIX_PACKAGE_RECOGNITION_LIST,
                                                                            "container_kind": "package_recognitions",
                                                                            "item_kind": "recognition",
                                                                            "child_area": NODE_AREA_CONTENT,
                                                                            "include_container_name_in_item_search": True,
                                                                        },
                                                                    ],
                                                                },
                                                            },
                                                        ],
                                                    },
                                                },
                                            ],
                                        },
                                    },
                                    "items": [
                                        {
                                            "list_suffix": GRAMMAR_SUFFIX_SEEDED_GROUPS,
                                            "container_kind": "agent_seeded_groups",
                                        },
                                        {
                                            "list_suffix": GRAMMAR_SUFFIX_GROUPS,
                                            "container_kind": "agent_groups",
                                        },
                                    ],
                                },
                            ],
                        },
                    },
                ],
            },
        )

        leftovers_content = self._get_current_leftovers_content()

        return frontend_object, leftovers_content

    def _build_empty_frontend_object(
        self,
        *,
        leftovers_content: str = "",
        viewer_content: str = "",
    ) -> dict[str, Any]:
        frontend_object = {
            "object_type": "agent_foundry_frontend_object",
            "schema_version": "node_map.v1",
            "next_node_number": 1,
            "root_node_ids": [
                ROOT_AGENT_ID,
                ROOT_TASK_PACKAGE_ALIGNMENT_ID,
                ROOT_PACKAGES_ID,
                ROOT_LEFTOVERS_ID,
                ROOT_VIEWER_ID,
            ],
            "nodes": {},
        }

        self._add_node(
            frontend_object=frontend_object,
            node={
                "id": ROOT_AGENT_ID,
                "name": ROOT_AGENT_NAME,
                "kind": "static",
                "area": NODE_AREA_FUSED,
                "content": "",
                "children": [],
                "data": {},
            },
        )

        self._add_node(
            frontend_object=frontend_object,
            node={
                "id": ROOT_TASK_PACKAGE_ALIGNMENT_ID,
                "name": ROOT_TASK_PACKAGE_ALIGNMENT_NAME,
                "kind": "static",
                "area": NODE_AREA_CHILDREN,
                "content": "",
                "children": [],
                "data": {},
            },
        )

        self._add_node(
            frontend_object=frontend_object,
            node={
                "id": ROOT_PACKAGES_ID,
                "name": ROOT_PACKAGES_NAME,
                "kind": "static",
                "area": NODE_AREA_CHILDREN,
                "content": "",
                "children": [],
                "data": {},
            },
        )

        self._add_node(
            frontend_object=frontend_object,
            node={
                "id": ROOT_LEFTOVERS_ID,
                "name": ROOT_LEFTOVERS_NAME,
                "kind": "static",
                "area": NODE_AREA_CONTENT,
                "content": str(leftovers_content or "").rstrip(),
                "children": [],
                "data": {},
            },
        )

        self._add_node(
            frontend_object=frontend_object,
            node={
                "id": ROOT_VIEWER_ID,
                "name": ROOT_VIEWER_NAME,
                "kind": "static",
                "area": NODE_AREA_CONTENT,
                "content": str(viewer_content or "").rstrip(),
                "children": [],
                "data": {
                    "source": "agent_schema_file",
                    "parser_search_exclude": True,
                    "save_exclude": True,
                },
            },
        )

        return frontend_object

    def _run_mapping_group(
        self,
        *,
        mapping_group: dict[str, Any],
        inherited_shared: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if not isinstance(mapping_group, dict):
            return []

        inherited = dict(inherited_shared or {})
        local_shared = dict(mapping_group.get("shared", {}) or {})

        active_shared = dict(inherited)
        active_shared.update(local_shared)

        results: list[dict[str, Any]] = []

        for raw_item in list(mapping_group.get("items", []) or []):
            if not isinstance(raw_item, dict):
                continue

            if "items" in raw_item:
                nested_shared = dict(active_shared)
                nested_shared.update(dict(raw_item.get("shared", {}) or {}))

                results.extend(
                    self._run_mapping_group(
                        mapping_group=raw_item,
                        inherited_shared=nested_shared,
                    )
                )
                continue

            payload = dict(active_shared)
            payload.update(raw_item)

            child_mapping_group = payload.pop("child_mapping_group", None)

            result = self._build_list_container_nodes(
                **payload,
            )
            results.append(result)

            if not isinstance(child_mapping_group, dict):
                continue

            for child_node in list(result.get("child_nodes", []) or []):
                if not isinstance(child_node, dict):
                    continue

                child_node_id = str(child_node.get("id", "") or "").strip()
                if not child_node_id:
                    continue

                self._run_mapping_group(
                    mapping_group=child_mapping_group,
                    inherited_shared={
                        "owner_node_id": child_node_id,
                    },
                )

        return results

    def _create_node(
        self,
        *,
        name: str,
        kind: str,
        area: str,
        content: str = "",
        data: dict[str, Any] | None = None,
        node_id: str = "",
    ) -> dict[str, Any]:
        frontend_object = self._get_current_foundry_frontend_object()

        clean_name = self._normalize_node_name(name)
        clean_kind = self._normalize_node_name(kind) or "node"
        clean_area = self._normalize_node_area(area)
        clean_node_id = str(node_id or "").strip()

        if not clean_node_id:
            clean_node_id = self._next_generated_node_id(
                frontend_object=frontend_object,
            )

        node = {
            "id": clean_node_id,
            "name": clean_name,
            "kind": clean_kind,
            "area": clean_area,
            "content": str(content or "").rstrip(),
            "children": [],
            "data": dict(data or {}),
        }

        self._add_node(
            frontend_object=frontend_object,
            node=node,
        )

        return node

    def _add_node(
        self,
        *,
        frontend_object: dict[str, Any],
        node: dict[str, Any],
    ) -> None:
        if not isinstance(frontend_object, dict):
            return

        if not isinstance(node, dict):
            return

        node_id = str(node.get("id", "") or "").strip()
        if not node_id:
            return

        nodes = frontend_object.setdefault("nodes", {})
        if not isinstance(nodes, dict):
            frontend_object["nodes"] = {}
            nodes = frontend_object["nodes"]

        nodes[node_id] = node

    def _attach_child_node(
        self,
        *,
        parent_node_id: str,
        child_node_id: str,
    ) -> None:
        parent = self._get_node(
            node_id=parent_node_id,
        )
        if not isinstance(parent, dict):
            return

        clean_child_id = str(child_node_id or "").strip()
        if not clean_child_id:
            return

        children = parent.setdefault("children", [])
        if not isinstance(children, list):
            parent["children"] = []
            children = parent["children"]

        if clean_child_id not in children:
            children.append(clean_child_id)

    def _attach_root_node(
        self,
        *,
        node_id: str,
    ) -> None:
        frontend_object = self._get_current_foundry_frontend_object()

        clean_node_id = str(node_id or "").strip()
        if not clean_node_id:
            return

        root_node_ids = frontend_object.setdefault("root_node_ids", [])
        if not isinstance(root_node_ids, list):
            frontend_object["root_node_ids"] = []
            root_node_ids = frontend_object["root_node_ids"]

        if clean_node_id not in root_node_ids:
            root_node_ids.append(clean_node_id)

    def _get_node(
        self,
        *,
        node_id: str,
    ) -> dict[str, Any] | None:
        frontend_object = self._get_current_foundry_frontend_object()

        nodes = frontend_object.get("nodes", {})
        if not isinstance(nodes, dict):
            return None

        node = nodes.get(str(node_id or "").strip())
        if isinstance(node, dict):
            return node

        return None

    def _next_generated_node_id(
        self,
        *,
        frontend_object: dict[str, Any],
    ) -> str:
        try:
            next_number = int(frontend_object.get("next_node_number", 1))
        except Exception:
            next_number = 1

        if next_number < 1:
            next_number = 1

        frontend_object["next_node_number"] = next_number + 1
        return f"node_{next_number:06d}"

    def _build_list_container_nodes(
        self,
        *,
        owner_node_id: str,
        list_suffix: str,
        container_kind: str,
        item_kind: str,
        child_area: str,
        mount_node_id: str | None = None,
        mount_at_root: bool = False,
        item_content_suffixes: list[str] | tuple[str, ...] | str | None = None,
        include_container_name_in_item_search: bool = False,
    ) -> dict[str, Any]:
        owner_node = self._get_node(
            node_id=owner_node_id,
        )
        if not isinstance(owner_node, dict):
            return {
                "container_node": None,
                "child_nodes": [],
            }

        owner_name = self._normalize_node_name(owner_node.get("name", ""))
        clean_list_suffix = self._normalize_node_name(list_suffix)
        clean_child_area = self._normalize_node_area(child_area)

        if not owner_name or not clean_list_suffix:
            return {
                "container_node": None,
                "child_nodes": [],
            }

        container_name = f"{owner_name} {clean_list_suffix}"

        list_block = self._find_exact_frontend_block(
            start_heading=container_name,
        )
        if not bool(list_block.get("found", False)):
            return {
                "container_node": None,
                "child_nodes": [],
            }

        child_names = self._extract_fenced_list_items_from_block(
            block_text=str(list_block.get("block_text", "") or ""),
            start_heading=container_name,
        )
        if not child_names:
            return {
                "container_node": None,
                "child_nodes": [],
            }

        if (
            str(owner_node_id or "").strip() == ROOT_AGENT_ID
            and clean_list_suffix == GRAMMAR_SUFFIX_ID
        ):
            for heading in (
                container_name,
                "Agent Index ID",
            ):
                cut_result = self._cut_exact_frontend_block(
                    start_heading=heading,
                )
                block_text = str(cut_result.get("block_text", "") or "").rstrip()
                if block_text:
                    self._append_to_node_content(
                        node=owner_node,
                        text=block_text,
                    )

        container_node = self._create_node(
            name=container_name,
            kind=container_kind,
            area=NODE_AREA_CHILDREN,
            content="",
            data={
                "owner_node_id": str(owner_node_id or "").strip(),
                "list_suffix": clean_list_suffix,
                "container_name": container_name,
            },
        )

        if mount_at_root:
            self._attach_root_node(
                node_id=str(container_node.get("id", "") or ""),
            )
        else:
            target_mount_node_id = str(
                mount_node_id
                if mount_node_id is not None
                else owner_node_id
            ).strip()

            self._attach_child_node(
                parent_node_id=target_mount_node_id,
                child_node_id=str(container_node.get("id", "") or ""),
            )

        item_suffixes = self._normalize_suffixes(item_content_suffixes)

        child_nodes: list[dict[str, Any]] = []
        seen_children: set[str] = set()

        for raw_child_name in child_names:
            child_name = self._normalize_node_name(raw_child_name)
            if not child_name:
                continue

            child_key = child_name.lower()
            if child_key in seen_children:
                continue

            seen_children.add(child_key)

            moved_content = self._cut_content_blocks_for_item(
                container_name=container_name,
                item_name=child_name,
                content_suffixes=item_suffixes,
                include_container_name_in_search=include_container_name_in_item_search,
            )

            child_node = self._create_node(
                name=child_name,
                kind=item_kind,
                area=clean_child_area,
                content="\n\n".join(moved_content).rstrip(),
                data={
                    "source_container_node_id": str(container_node.get("id", "") or ""),
                    "source_container_name": container_name,
                },
            )

            self._attach_child_node(
                parent_node_id=str(container_node.get("id", "") or ""),
                child_node_id=str(child_node.get("id", "") or ""),
            )

            child_nodes.append(child_node)

        return {
            "container_node": container_node,
            "child_nodes": child_nodes,
        }

    def _move_existing_blocks_into_node(
        self,
        *,
        target_node_id: str,
        item_name: str,
        content_suffixes: list[str] | tuple[str, ...] | str | None = None,
        container_name: str = "",
        include_container_name_in_search: bool = False,
    ) -> dict[str, Any]:
        target_node = self._get_node(
            node_id=target_node_id,
        )
        if not isinstance(target_node, dict):
            return {
                "moved_blocks": [],
            }

        headings = self._build_content_headings(
            container_name=container_name,
            item_name=item_name,
            content_suffixes=content_suffixes,
            include_container_name_in_search=include_container_name_in_search,
        )

        moved_blocks: list[str] = []

        for heading in headings:
            cut_result = self._cut_exact_frontend_block(
                start_heading=heading,
            )
            if not bool(cut_result.get("found", False)):
                continue

            block_text = str(cut_result.get("block_text", "") or "").rstrip()
            if not block_text:
                continue

            self._append_to_node_content(
                node=target_node,
                text=block_text,
            )
            moved_blocks.append(block_text)

        return {
            "moved_blocks": moved_blocks,
        }

    def _cut_content_blocks_for_item(
        self,
        *,
        container_name: str,
        item_name: str,
        content_suffixes: list[str] | tuple[str, ...] | str | None = None,
        include_container_name_in_search: bool = False,
    ) -> list[str]:
        headings = self._build_content_headings(
            container_name=container_name,
            item_name=item_name,
            content_suffixes=content_suffixes,
            include_container_name_in_search=include_container_name_in_search,
        )

        moved_blocks: list[str] = []

        for heading in headings:
            cut_result = self._cut_exact_frontend_block(
                start_heading=heading,
            )
            if not bool(cut_result.get("found", False)):
                continue

            block_text = str(cut_result.get("block_text", "") or "").rstrip()
            if block_text:
                moved_blocks.append(block_text)

        return moved_blocks

    def _build_content_headings(
        self,
        *,
        item_name: str,
        content_suffixes: list[str] | tuple[str, ...] | str | None = None,
        container_name: str = "",
        include_container_name_in_search: bool = False,
    ) -> list[str]:
        clean_item_name = self._normalize_node_name(item_name)
        clean_container_name = self._normalize_node_name(container_name)

        if not clean_item_name:
            return []

        if include_container_name_in_search and clean_container_name:
            base_heading = f"{clean_container_name} {clean_item_name}"
        else:
            base_heading = clean_item_name

        headings = [base_heading]

        for suffix in self._normalize_suffixes(content_suffixes):
            headings.append(f"{base_heading} {suffix}")

        return headings

    def _iter_content_targets(self) -> list[dict[str, Any]]:
        frontend_object = self._get_current_foundry_frontend_object()

        nodes = frontend_object.get("nodes", {})
        if not isinstance(nodes, dict):
            return []

        results: list[dict[str, Any]] = []

        for node in nodes.values():
            if not isinstance(node, dict):
                continue

            data = node.get("data", {})
            if isinstance(data, dict) and bool(data.get("parser_search_exclude", False)):
                continue

            if str(node.get("area", "") or "").strip() not in {
                NODE_AREA_CONTENT,
                NODE_AREA_FUSED,
            }:
                continue

            results.append(
                {
                    "node": node,
                    "content": str(node.get("content", "") or ""),
                }
            )

        return results

    def _find_exact_frontend_block(
        self,
        *,
        start_heading: str,
        end_heading: str | None = None,
    ) -> dict[str, Any]:
        clean_start_heading = self._normalize_node_name(start_heading)
        clean_end_heading = (
            self._normalize_node_name(end_heading)
            if end_heading is not None
            else f"End {clean_start_heading}"
        )

        if not clean_start_heading or not clean_end_heading:
            return {
                "found": False,
                "node": None,
                "block_text": "",
                "inner_text": "",
                "range": None,
            }

        for target in self._iter_content_targets():
            node = target.get("node")
            content = str(target.get("content", "") or "")

            block = self._find_exact_fenced_block_in_text(
                source_text=content,
                start_heading=clean_start_heading,
                end_heading=clean_end_heading,
            )
            if not isinstance(block, dict):
                continue

            return {
                "found": True,
                "node": node,
                "block_text": str(block.get("block_text", "") or "").rstrip(),
                "inner_text": str(block.get("inner_text", "") or "").rstrip(),
                "range": block.get("range"),
            }

        return {
            "found": False,
            "node": None,
            "block_text": "",
            "inner_text": "",
            "range": None,
        }

    def _cut_exact_frontend_block(
        self,
        *,
        start_heading: str,
        end_heading: str | None = None,
    ) -> dict[str, Any]:
        found = self._find_exact_frontend_block(
            start_heading=start_heading,
            end_heading=end_heading,
        )

        if not bool(found.get("found", False)):
            return found

        node = found.get("node")
        block_range = found.get("range")

        if not isinstance(node, dict):
            return found

        if not isinstance(block_range, tuple) or len(block_range) != 2:
            return found

        current_content = str(node.get("content", "") or "")
        start, end = block_range

        node["content"] = (
            current_content[:start].rstrip()
            + "\n\n"
            + current_content[end:].lstrip()
        ).strip()

        return found

    def _find_exact_fenced_block_in_text(
        self,
        *,
        source_text: str,
        start_heading: str,
        end_heading: str,
    ) -> dict[str, Any] | None:
        source = str(source_text or "")
        clean_start_heading = self._normalize_node_name(start_heading)
        clean_end_heading = self._normalize_node_name(end_heading)

        if not clean_start_heading or not clean_end_heading:
            return None

        start_pattern = rf"(?im)^\s*{re.escape(clean_start_heading)}\s*:\s*$"
        start_match = re.search(start_pattern, source)
        if not start_match:
            return None

        end_pattern = rf"(?im)^\s*{re.escape(clean_end_heading)}\s*$"
        end_match = re.search(end_pattern, source[start_match.end():])
        if not end_match:
            return None

        inner_start = start_match.end()
        inner_end = start_match.end() + end_match.start()
        block_end = start_match.end() + end_match.end()

        return {
            "block_text": source[start_match.start():block_end].strip(),
            "inner_text": source[inner_start:inner_end].strip(),
            "range": (start_match.start(), block_end),
        }

    def _extract_fenced_list_items_from_block(
        self,
        *,
        block_text: str,
        start_heading: str,
        end_heading: str | None = None,
        strict: bool = True,
    ) -> list[str]:
        clean_start_heading = self._normalize_node_name(start_heading)
        clean_end_heading = (
            self._normalize_node_name(end_heading)
            if end_heading is not None
            else f"End {clean_start_heading}"
        )

        block = self._find_exact_fenced_block_in_text(
            source_text=block_text,
            start_heading=clean_start_heading,
            end_heading=clean_end_heading,
        )
        if not isinstance(block, dict):
            return []

        inner_text = str(block.get("inner_text") or "")
        results: list[str] = []

        for raw_line in inner_text.splitlines():
            line = str(raw_line or "").strip()
            if not line:
                continue

            bullet_match = re.match(r"^[-*]\s+(?P<value>.*)$", line)
            if not bullet_match:
                if strict:
                    return []
                continue

            value = str(bullet_match.group("value") or "").strip()
            if value:
                results.append(value)

        return results

    def _append_to_node_content(
        self,
        *,
        node: dict[str, Any],
        text: str,
    ) -> None:
        if not isinstance(node, dict):
            return

        clean_text = str(text or "").rstrip()
        if not clean_text:
            return

        existing_content = str(node.get("content", "") or "").rstrip()
        if existing_content:
            node["content"] = f"{existing_content}\n\n{clean_text}".rstrip()
        else:
            node["content"] = clean_text

    def _get_current_leftovers_content(self) -> str:
        leftovers_node = self._get_node(
            node_id=ROOT_LEFTOVERS_ID,
        )

        if not isinstance(leftovers_node, dict):
            return ""

        return str(leftovers_node.get("content", "") or "").rstrip()

    def _normalize_node_area(self, value: str) -> str:
        clean_value = str(value or "").strip().lower()
        if clean_value in {
            NODE_AREA_CONTENT,
            NODE_AREA_CHILDREN,
            NODE_AREA_FUSED,
        }:
            return clean_value

        return NODE_AREA_CONTENT

    def _normalize_node_name(self, value: Any) -> str:
        return str(value or "").strip()

    def _normalize_suffixes(
        self,
        suffixes: list[str] | tuple[str, ...] | str | None,
    ) -> list[str]:
        if suffixes is None:
            return []

        if isinstance(suffixes, str):
            raw_suffixes = [suffixes]
        elif isinstance(suffixes, (list, tuple)):
            raw_suffixes = list(suffixes)
        else:
            return []

        return [
            self._normalize_node_name(suffix)
            for suffix in raw_suffixes
            if self._normalize_node_name(suffix)
        ]

    def _get_current_foundry_frontend_object(self) -> dict[str, Any]:
        frontend_object = getattr(self, "agent_foundry_frontend_object", None)
        if isinstance(frontend_object, dict):
            return frontend_object

        frontend_object = self._build_empty_frontend_object()
        self.agent_foundry_frontend_object = frontend_object
        return frontend_object
from __future__ import annotations

import tkinter as tk
from typing import Any


# =============================================================================
# Agent Foundry grammar / help vocabulary
# =============================================================================
#
# Help does not own Parser's behavior.
# Help reads Parser's frontend node map and explains the grammar that Parser
# already made visible through node names, kinds, child links, and node data.
#
# Parser remains independent. Help stays downstream from Parser.


ROOT_AGENT_NAME = "Agent"

# Current parser suffix vocabulary.
GRAMMAR_SUFFIX_ID = "ID"
GRAMMAR_SUFFIX_SEEDED_DEFAULT_RETURNS = "Seeded Default Returns"
GRAMMAR_SUFFIX_DEFAULT_RETURNS = "Default Returns"
GRAMMAR_SUFFIX_SEEDED_GROUPS = "Seeded Groups"
GRAMMAR_SUFFIX_GROUPS = "Groups"
GRAMMAR_SUFFIX_TASKS = "Tasks"
GRAMMAR_SUFFIX_WORKFLOW = "Workflow"
GRAMMAR_SUFFIX_PROMPTS = "Prompts"
GRAMMAR_SUFFIX_MEMORY = "Memory"
GRAMMAR_SUFFIX_PACKAGES = "Packages"

# Current agent-root grammar.
AGENT_ID_LIST_HEADING = f"{ROOT_AGENT_NAME} {GRAMMAR_SUFFIX_ID}"
AGENT_ID_LIST_END_HEADING = f"End {AGENT_ID_LIST_HEADING}"

AGENT_DEFAULT_RETURN_DETAIL_MARKER = "Agent Default Return"
GROUP_DEFAULT_RETURN_DETAIL_MARKER = "Group Default Return"
TASK_DEFAULT_RETURN_DETAIL_MARKER = "Task Default Return"

GROUP_DEFAULT_RETURN_LIST_LABEL = GRAMMAR_SUFFIX_DEFAULT_RETURNS
GROUP_SEEDED_DEFAULT_RETURN_LIST_LABEL = GRAMMAR_SUFFIX_SEEDED_DEFAULT_RETURNS

TASK_WORKFLOW_LABEL = GRAMMAR_SUFFIX_WORKFLOW
TASK_DEFAULT_RETURNS_LABEL = GRAMMAR_SUFFIX_DEFAULT_RETURNS
TASK_SEEDED_DEFAULT_RETURN_LIST_LABEL = GRAMMAR_SUFFIX_SEEDED_DEFAULT_RETURNS
TASK_PACKAGES_LABEL = GRAMMAR_SUFFIX_PACKAGES
TASK_PROMPTS_LABEL = GRAMMAR_SUFFIX_PROMPTS
TASK_MEMORY_LABEL = GRAMMAR_SUFFIX_MEMORY


HELP_KEY_BY_STATIC_PATH: dict[tuple[str, ...], str] = {
    ("Blueprint",): "blueprint",
    ("Control",): "blueprint",
    ("Viewer",): "viewer",
    ("Agent",): "agent",
    ("Groups",): "top_level_collection",
    ("Tasks",): "top_level_collection",
    ("Package Blueprint",): "package_blueprint",
    ("Leftovers",): "leftovers",
}


HELP_KEY_BY_NODE_KIND: dict[str, str] = {
    "static": "parent_area",

    "agent_ids": "agent_id_container",
    "agent": "agent",

    "agent_seeded_groups": "top_level_collection",
    "agent_groups": "top_level_collection",
    "seeded_groups": "top_level_collection",
    "groups": "top_level_collection",
    "tasks": "top_level_collection",

    "group": "group",
    "task": "task",

    "agent_seeded_default_returns": "default_return_container",
    "agent_default_returns": "default_return_container",
    "seeded_default_returns": "default_return_container",
    "default_returns": "default_return_container",
    "group_seeded_default_returns": "default_return_container",
    "group_default_returns": "default_return_container",
    "task_seeded_default_returns": "default_return_container",
    "task_default_returns": "default_return_container",

    "default_return": "default_return",

    "prompts": "prompt_container",
    "prompt": "prompt",

    "memory": "memory_container",
    "memory_item": "memory",
    "memory_entry": "memory",

    "packages": "package_container",
    "package": "package",
}


HELP_TITLE_BY_KEY: dict[str, str] = {
    "blueprint": "Help: Blueprint",
    "viewer": "Help: Viewer",
    "frontend_object": "Help: Frontend Object",

    "agent": "Help: Agent",
    "agent_id_container": "Help: Agent ID List",
    "parent_area": "Help: Parent Area",
    "top_level_collection": "Help: Collection",
    "top_level_text": "Help: Text Section",

    "group": "Help: Group",
    "task": "Help: Task",

    "default_return_container": "Help: Default Return List",
    "default_return": "Help: Default Return",

    "prompt_container": "Help: Prompt List",
    "prompt": "Help: Prompt",

    "memory_container": "Help: Memory List",
    "memory": "Help: Memory",

    "package_blueprint": "Help: Package Blueprint",
    "package_container": "Help: Package List",
    "package": "Help: Package",

    "leftovers": "Help: Leftovers",
}


AGENT_FOUNDRY_HELP_MANUAL_TEXT: dict[str, str] = {
    "blueprint": """
Blueprint / Control Display

This area is the read-only composed view of the current Agent Foundry frontend object.

Parser builds the frontend object.
Document composes the display from that object.
Editing should happen through the node Edit buttons, not by typing directly into the composed display.

Use this area to verify that Agent ID, agent nodes, groups, tasks, containers, item tabs, Viewer, and Leftovers all reflect the current parsed object.
""".strip(),

    "viewer": """
Viewer

Viewer is the read-only JSON/schema display for the current Agent Foundry draft.

It is not the editable source of truth.
It does not define the Blueprint.
It only shows the current generated schema file when one is available.
""".strip(),

    "frontend_object": """
Frontend Object

The frontend object is Parser's live UI-facing state after raw Blueprint and Leftovers text have been loaded.

It contains nodes, root node ids, child links, node names, node kinds, node areas, node content, and node data.
Help reads this object to explain the current grammar for each tab.
""".strip(),

    "agent": """
Agent

Agent is the root owner for agent records.

Current agent list fence:

Agent ID:
- agent_000001
End Agent ID

Each listed agent becomes an agent node. Agent-level lists then use the listed agent name as the owner.

Common agent-level fences:

agent_000001 Seeded Groups:
- Outcasts
End agent_000001 Seeded Groups

agent_000001 Groups:
- Some Group Name
End agent_000001 Groups

agent_000001 Seeded Default Returns:
- self_agent_name
End agent_000001 Seeded Default Returns

agent_000001 Default Returns:
- some_agent_return_name
End agent_000001 Default Returns
""".strip(),

    "agent_id_container": """
Agent ID List

The Agent ID list declares the active agent node or agent nodes in this draft.

Current fence:

Agent ID:
- agent_000001
End Agent ID

Each item listed here becomes an agent node. The parser then looks for agent-owned lists using that exact item name.
""".strip(),

    "parent_area": """
Parent Area

A parent area is the main text area for a structured node.

Parent areas hold:
- List fences that declare child records.
- Notes or metadata that belong directly to the node.
- For tasks, workflow text remains ordinary task parent content.

Child records are created from lists inside parent areas or from globally found parser fences.
""".strip(),

    "top_level_collection": """
Collection

A collection node is generated from a parsed list fence.

Examples:
- Agent ID
- agent_000001 Seeded Groups
- agent_000001 Groups
- Outcasts Tasks
- Some Task Prompts

The collection node organizes child records. The list fence itself remains in the owner parent area.
""".strip(),

    "top_level_text": """
Text Section

A text section contains content but does not organize children.

The main examples are Viewer and Leftovers.
""".strip(),

    "group": """
Group

A group is created from a name listed in an agent's Groups or Seeded Groups list.

Example:

agent_000001 Groups:
- Some Group Name
End agent_000001 Groups

A group can have:
- Seeded Default Returns
- Default Returns
- Tasks

The group's child lists use the group name as the owner.
""".strip(),

    "task": """
Task

A task is created from a name listed in a group's Tasks list.

A task can have:
- Workflow
- Seeded Default Returns
- Default Returns
- Prompts
- Memory
- Packages, when package support is active

Workflow is task parent-area text, not a special child tab in the current parser.
""".strip(),

    "default_return_container": """
Default Return List

A default-return container declares default-return item names.

The exact fence depends on the owner node. Help can generate the current exact fence from the node map.
""".strip(),

    "default_return": """
Default Return

A default return is an item created from a default-return list.

The listed item name should match the content/detail block associated with that return.
""".strip(),

    "prompt_container": """
Prompt List

A prompt container declares prompt item names for a task.

The exact fence depends on the task name. Help can generate the current exact fence from the node map.
""".strip(),

    "prompt": """
Prompt

A prompt is an item created from a task prompt list.

The prompt name should match the listed item name.
Prompt text can be multiline.
""".strip(),

    "memory_container": """
Memory List

A memory container declares memory item names for a task.

The exact fence depends on the task name. Help can generate the current exact fence from the node map.
""".strip(),

    "memory": """
Memory

A memory item stores task-specific context, notes, constraints, or remembered facts.
""".strip(),

    "package_blueprint": """
Package Blueprint

Package support is still parked/early.

Use package help as a placeholder until the package parser and package detail grammar are finalized.
""".strip(),

    "package_container": """
Package List

A package container declares package item names for a task.

Package detail parsing is still parked, so treat this as early grammar.
""".strip(),

    "package": """
Package

A package item is a package-list entry.

Full package detail parsing/editing is parked for later.
""".strip(),

    "leftovers": """
Leftovers

Leftovers contains raw text Parser could not confidently claim into the structured frontend object.

Leftovers is not trash. It is a safety net.

Common causes:
- Misspelled fence heading.
- Missing end fence.
- Detail block name does not match a listed item.
- Group not listed under the relevant agent.
- Task not listed in a group Tasks list.
- Grammar area not supported yet.
""".strip(),
}


def build_foundry_fence_heading(owner_name: str, suffix: str = "") -> str:
    owner = str(owner_name or "").strip()
    clean_suffix = str(suffix or "").strip()

    if owner and clean_suffix:
        return f"{owner} {clean_suffix}"

    return owner or clean_suffix


def build_foundry_fence_start(owner_name: str, suffix: str = "") -> str:
    heading = build_foundry_fence_heading(owner_name, suffix)
    return f"{heading}:" if heading else ""


def build_foundry_fence_end(owner_name: str, suffix: str = "") -> str:
    heading = build_foundry_fence_heading(owner_name, suffix)
    return f"End {heading}" if heading else ""


def build_foundry_list_fence_example(
    *,
    owner_name: str,
    suffix: str,
    item_name: str = "item_name",
) -> str:
    start = build_foundry_fence_start(owner_name, suffix)
    end = build_foundry_fence_end(owner_name, suffix)
    clean_item_name = str(item_name or "").strip() or "item_name"

    if not start or not end:
        return ""

    return f"{start}\n- {clean_item_name}\n{end}"


def build_foundry_content_fence_example(
    *,
    item_name: str,
    suffix: str = "",
    body: str = "...",
) -> str:
    start = build_foundry_fence_start(item_name, suffix)
    end = build_foundry_fence_end(item_name, suffix)
    clean_body = str(body or "").strip() or "..."

    if not start or not end:
        return ""

    return f"{start}\n{clean_body}\n{end}"


class AgentFoundryHelpPopup(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        help_text: str,
    ) -> None:
        super().__init__(parent)

        self.parent = parent

        self.title(title)
        self.geometry("820x620")
        self.minsize(620, 420)
        self.transient(parent)
        self.grab_set()

        self._build_ui(help_text=help_text)
        self.focus_force()

    def _build_ui(self, help_text: str) -> None:
        outer = tk.Frame(self, padx=12, pady=12)
        outer.pack(fill="both", expand=True)

        text_container = tk.Frame(outer)
        text_container.pack(fill="both", expand=True)

        vertical_scrollbar = tk.Scrollbar(text_container, orient="vertical")
        vertical_scrollbar.pack(side="right", fill="y")

        text_widget = tk.Text(
            text_container,
            wrap="word",
            undo=False,
            font=("Segoe UI", 10),
            yscrollcommand=vertical_scrollbar.set,
        )
        text_widget.pack(side="left", fill="both", expand=True)
        vertical_scrollbar.config(command=text_widget.yview)

        text_widget.insert("1.0", str(help_text or "No help text is available."))
        text_widget.configure(state="disabled")

        button_row = tk.Frame(outer)
        button_row.pack(fill="x", pady=(10, 0))

        tk.Button(
            button_row,
            text="Close",
            width=12,
            command=self.destroy,
        ).pack(side="right")


class AgentFoundryHelpMixin:
    # -------------------------------------------------------------------------
    # Public help entry points
    # -------------------------------------------------------------------------

    def _show_agent_foundry_help_for_node(
        self,
        node: dict[str, Any],
    ) -> None:
        """Open Help for a Parser frontend-object node."""
        if not isinstance(node, dict):
            return

        help_key = self._get_agent_foundry_help_key_for_node(node)
        if not help_key:
            help_key = "parent_area"

        self._open_agent_foundry_help_popup_for_node(
            help_key=help_key,
            node=node,
        )

    def _show_agent_foundry_help_for_path(
        self,
        help_path: list[str] | tuple[str, ...],
    ) -> None:
        """Open Help for static shell paths."""
        help_key = self._get_agent_foundry_help_key_for_path(help_path)
        if not help_key:
            return

        self._open_agent_foundry_help_popup_for_key(help_key)

    # -------------------------------------------------------------------------
    # Popup builders
    # -------------------------------------------------------------------------

    def _open_agent_foundry_help_popup_for_key(self, help_key: str) -> None:
        clean_help_key = str(help_key or "").strip()
        if not clean_help_key:
            return

        help_text = self._load_agent_foundry_help_text(clean_help_key)
        title = self._get_agent_foundry_help_title(clean_help_key)

        AgentFoundryHelpPopup(
            parent=self.agent_foundry_tab,
            title=title,
            help_text=help_text,
        )

    def _open_agent_foundry_help_popup_for_node(
        self,
        *,
        help_key: str,
        node: dict[str, Any],
    ) -> None:
        clean_help_key = str(help_key or "").strip()
        if not clean_help_key:
            return

        manual_text = self._load_agent_foundry_help_text(clean_help_key)
        dynamic_text = self._build_agent_foundry_dynamic_help_text_for_node(node)

        if dynamic_text:
            help_text = f"{manual_text}\n\n{dynamic_text}".strip()
        else:
            help_text = manual_text

        title = self._build_agent_foundry_help_title_for_node(
            help_key=clean_help_key,
            node=node,
        )

        AgentFoundryHelpPopup(
            parent=self.agent_foundry_tab,
            title=title,
            help_text=help_text,
        )

    def _load_agent_foundry_help_text(self, help_key: str) -> str:
        clean_help_key = str(help_key or "").strip()
        if not clean_help_key:
            return "No help text is available."

        manual_text = AGENT_FOUNDRY_HELP_MANUAL_TEXT.get(clean_help_key, "")
        if manual_text:
            return manual_text

        return self._build_missing_agent_foundry_help_text(clean_help_key)

    def _build_missing_agent_foundry_help_text(self, help_key: str) -> str:
        title = self._get_agent_foundry_help_title(help_key)
        return (
            f"{title}\n\n"
            "No detailed help text has been written for this node kind yet.\n\n"
            "This Help route exists, but its manual page has not been filled in."
        )

    def _get_agent_foundry_help_title(self, help_key: str) -> str:
        clean_help_key = str(help_key or "").strip()
        return HELP_TITLE_BY_KEY.get(clean_help_key, "Help")

    def _build_agent_foundry_help_title_for_node(
        self,
        *,
        help_key: str,
        node: dict[str, Any],
    ) -> str:
        base_title = self._get_agent_foundry_help_title(help_key)
        node_name = self._get_agent_foundry_help_node_name(node)
        if not node_name:
            return base_title

        return f"{base_title}: {node_name}"

    # -------------------------------------------------------------------------
    # Dynamic node-map help
    # -------------------------------------------------------------------------

    def _build_agent_foundry_dynamic_help_text_for_node(
        self,
        node: dict[str, Any],
    ) -> str:
        if not isinstance(node, dict):
            return ""

        parts: list[str] = []

        identity_text = self._build_agent_foundry_node_identity_help(node)
        if identity_text:
            parts.append(identity_text)

        grammar_text = self._build_agent_foundry_node_grammar_help(node)
        if grammar_text:
            parts.append(grammar_text)

        child_text = self._build_agent_foundry_node_children_help(node)
        if child_text:
            parts.append(child_text)

        return "\n\n".join(
            part.strip()
            for part in parts
            if str(part or "").strip()
        ).strip()

    def _build_agent_foundry_node_identity_help(
        self,
        node: dict[str, Any],
    ) -> str:
        node_id = self._get_agent_foundry_help_node_id(node)
        node_name = self._get_agent_foundry_help_node_name(node)
        node_kind = self._get_agent_foundry_help_node_kind(node)
        node_area = self._get_agent_foundry_help_node_area(node)
        parent_node = self._get_agent_foundry_help_parent_node(node)
        parent_name = self._get_agent_foundry_help_node_name(parent_node)

        lines = [
            "Current node",
            f"- Name: {node_name or '(blank)'}",
            f"- Kind: {node_kind or '(blank)'}",
            f"- Area: {node_area or '(blank)'}",
        ]

        if node_id:
            lines.append(f"- Node id: {node_id}")

        if parent_name:
            lines.append(f"- Parent/owner: {parent_name}")

        return "\n".join(lines)

    def _build_agent_foundry_node_grammar_help(
        self,
        node: dict[str, Any],
    ) -> str:
        node_kind = self._get_agent_foundry_help_node_kind(node)

        if self._is_agent_foundry_help_static_node(node):
            return self._build_agent_foundry_static_node_grammar_help(node)

        if self._is_agent_foundry_help_container_node(node):
            return self._build_agent_foundry_container_node_grammar_help(node)

        if node_kind == "agent":
            return self._build_agent_foundry_agent_item_grammar_help(node)

        if node_kind in {"group", "task"}:
            return self._build_agent_foundry_item_block_grammar_help(node)

        if node_kind in {"default_return", "prompt", "memory", "package"}:
            return self._build_agent_foundry_detail_item_grammar_help(node)

        return ""

    def _build_agent_foundry_static_node_grammar_help(
        self,
        node: dict[str, Any],
    ) -> str:
        node_name = self._get_agent_foundry_help_node_name(node)

        if node_name == "Agent":
            return (
                "Agent is the root owner for agent records.\n\n"
                "Use this list fence:\n\n"
                f"{build_foundry_list_fence_example(owner_name=node_name, suffix=GRAMMAR_SUFFIX_ID, item_name='agent_000001')}"
            ).strip()

        if node_name in {"Leftovers", "Viewer"}:
            return "This node is system-managed. It does not need a manual source fence."

        if node_name:
            return (
                "Use this outer fence:\n\n"
                f"{build_foundry_content_fence_example(item_name=node_name)}"
            ).strip()

        return ""

    def _build_agent_foundry_agent_item_grammar_help(
        self,
        node: dict[str, Any],
    ) -> str:
        node_name = self._get_agent_foundry_help_node_name(node)
        if not node_name:
            return ""

        examples = "\n\n".join(
            example.strip()
            for example in [
                build_foundry_list_fence_example(
                    owner_name=node_name,
                    suffix=GRAMMAR_SUFFIX_SEEDED_DEFAULT_RETURNS,
                    item_name="self_agent_name",
                ),
                build_foundry_list_fence_example(
                    owner_name=node_name,
                    suffix=GRAMMAR_SUFFIX_DEFAULT_RETURNS,
                    item_name="agent_return_name",
                ),
                build_foundry_list_fence_example(
                    owner_name=node_name,
                    suffix=GRAMMAR_SUFFIX_SEEDED_GROUPS,
                    item_name="Outcasts",
                ),
                build_foundry_list_fence_example(
                    owner_name=node_name,
                    suffix=GRAMMAR_SUFFIX_GROUPS,
                    item_name="Some Group Name",
                ),
            ]
            if str(example or "").strip()
        )

        return (
            "This agent was created from the Agent ID list.\n\n"
            "Common child list fences for this agent:\n\n"
            f"{examples}"
        ).strip()

    def _build_agent_foundry_container_node_grammar_help(
        self,
        node: dict[str, Any],
    ) -> str:
        owner_node = self._get_agent_foundry_help_owner_node_for_container(node)
        owner_name = self._get_agent_foundry_help_node_name(owner_node)
        list_suffix = self._get_agent_foundry_help_container_list_suffix(node)
        example_item = self._get_agent_foundry_help_example_item_name_for_container(node)

        if not owner_name or not list_suffix:
            return ""

        return (
            "Use this list fence in the owner parent area:\n\n"
            f"{build_foundry_list_fence_example(owner_name=owner_name, suffix=list_suffix, item_name=example_item)}"
        ).strip()

    def _build_agent_foundry_item_block_grammar_help(
        self,
        node: dict[str, Any],
    ) -> str:
        node_name = self._get_agent_foundry_help_node_name(node)
        if not node_name:
            return ""

        child_examples = self._build_agent_foundry_child_list_examples_for_owner(node)
        outer = (
            "Use this outer block for this item:\n\n"
            f"{build_foundry_content_fence_example(item_name=node_name)}"
        ).strip()

        if not child_examples:
            return outer

        return f"{outer}\n\nCommon child list fences for this item:\n\n{child_examples}"

    def _build_agent_foundry_detail_item_grammar_help(
        self,
        node: dict[str, Any],
    ) -> str:
        node_name = self._get_agent_foundry_help_node_name(node)
        container_node = self._get_agent_foundry_help_source_container_node(node)
        container_name = self._get_agent_foundry_help_node_name(container_node)

        list_text = ""
        owner_node = self._get_agent_foundry_help_owner_node_for_container(container_node)
        owner_name = self._get_agent_foundry_help_node_name(owner_node)
        list_suffix = self._get_agent_foundry_help_container_list_suffix(container_node)

        if owner_name and list_suffix and node_name:
            list_text = (
                "This item should be listed in its source list fence:\n\n"
                f"{build_foundry_list_fence_example(owner_name=owner_name, suffix=list_suffix, item_name=node_name)}"
            ).strip()

        detail_text = ""
        if node_name and container_name:
            detail_text = (
                "Optional detail/content block for this item:\n\n"
                f"{build_foundry_content_fence_example(item_name=container_name, suffix=node_name)}"
            ).strip()

        return "\n\n".join(
            part.strip()
            for part in [list_text, detail_text]
            if str(part or "").strip()
        ).strip()

    def _build_agent_foundry_child_list_examples_for_owner(
        self,
        owner_node: dict[str, Any],
    ) -> str:
        owner_name = self._get_agent_foundry_help_node_name(owner_node)
        owner_kind = self._get_agent_foundry_help_node_kind(owner_node)

        if not owner_name:
            return ""

        examples: list[str] = []

        if owner_kind == "agent":
            examples.extend(
                [
                    build_foundry_list_fence_example(
                        owner_name=owner_name,
                        suffix=GRAMMAR_SUFFIX_SEEDED_DEFAULT_RETURNS,
                        item_name="self_agent_name",
                    ),
                    build_foundry_list_fence_example(
                        owner_name=owner_name,
                        suffix=GRAMMAR_SUFFIX_DEFAULT_RETURNS,
                        item_name="agent_return_name",
                    ),
                    build_foundry_list_fence_example(
                        owner_name=owner_name,
                        suffix=GRAMMAR_SUFFIX_SEEDED_GROUPS,
                        item_name="Outcasts",
                    ),
                    build_foundry_list_fence_example(
                        owner_name=owner_name,
                        suffix=GRAMMAR_SUFFIX_GROUPS,
                        item_name="Some Group Name",
                    ),
                ]
            )

        elif owner_kind == "group":
            examples.extend(
                [
                    build_foundry_list_fence_example(
                        owner_name=owner_name,
                        suffix=GRAMMAR_SUFFIX_SEEDED_DEFAULT_RETURNS,
                        item_name="self_group_name",
                    ),
                    build_foundry_list_fence_example(
                        owner_name=owner_name,
                        suffix=GRAMMAR_SUFFIX_DEFAULT_RETURNS,
                        item_name="group_return_name",
                    ),
                    build_foundry_list_fence_example(
                        owner_name=owner_name,
                        suffix=GRAMMAR_SUFFIX_TASKS,
                        item_name="Some Task",
                    ),
                ]
            )

        elif owner_kind == "task":
            examples.extend(
                [
                    build_foundry_content_fence_example(
                        item_name=owner_name,
                        suffix=GRAMMAR_SUFFIX_WORKFLOW,
                        body="Describe the task workflow here.",
                    ),
                    build_foundry_list_fence_example(
                        owner_name=owner_name,
                        suffix=GRAMMAR_SUFFIX_SEEDED_DEFAULT_RETURNS,
                        item_name="self_task_name",
                    ),
                    build_foundry_list_fence_example(
                        owner_name=owner_name,
                        suffix=GRAMMAR_SUFFIX_DEFAULT_RETURNS,
                        item_name="task_return_name",
                    ),
                    build_foundry_list_fence_example(
                        owner_name=owner_name,
                        suffix=GRAMMAR_SUFFIX_PROMPTS,
                        item_name="main_prompt",
                    ),
                    build_foundry_list_fence_example(
                        owner_name=owner_name,
                        suffix=GRAMMAR_SUFFIX_MEMORY,
                        item_name="known_context",
                    ),
                    build_foundry_list_fence_example(
                        owner_name=owner_name,
                        suffix=GRAMMAR_SUFFIX_PACKAGES,
                        item_name="package_name",
                    ),
                ]
            )

        return "\n\n".join(
            example.strip()
            for example in examples
            if str(example or "").strip()
        ).strip()

    def _build_agent_foundry_node_children_help(
        self,
        node: dict[str, Any],
    ) -> str:
        child_nodes = self._get_agent_foundry_help_child_nodes(node)
        if not child_nodes:
            return ""

        child_names = [
            self._get_agent_foundry_help_node_name(child)
            for child in child_nodes
            if self._get_agent_foundry_help_node_name(child)
        ]

        if not child_names:
            return ""

        preview = "\n".join(f"- {name}" for name in child_names[:30])
        extra_count = max(0, len(child_names) - 30)

        if extra_count:
            preview += f"\n- ...and {extra_count} more"

        return f"Child nodes currently under this node:\n{preview}"

    # -------------------------------------------------------------------------
    # Node-map walking helpers
    # -------------------------------------------------------------------------

    def _get_agent_foundry_help_frontend_object(self) -> dict[str, Any]:
        frontend_object = getattr(self, "agent_foundry_frontend_object", None)
        if isinstance(frontend_object, dict):
            return frontend_object

        return {
            "object_type": "agent_foundry_frontend_object",
            "schema_version": "node_map.v1",
            "root_node_ids": [],
            "nodes": {},
        }

    def _get_agent_foundry_help_nodes(self) -> dict[str, dict[str, Any]]:
        frontend_object = self._get_agent_foundry_help_frontend_object()
        nodes = frontend_object.get("nodes", {})
        if isinstance(nodes, dict):
            return nodes

        return {}

    def _get_agent_foundry_help_node_by_id(
        self,
        node_id: Any,
    ) -> dict[str, Any] | None:
        clean_node_id = str(node_id or "").strip()
        if not clean_node_id:
            return None

        node = self._get_agent_foundry_help_nodes().get(clean_node_id)
        if isinstance(node, dict):
            return node

        return None

    def _get_agent_foundry_help_parent_node(
        self,
        node: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(node, dict):
            return None

        node_id = self._get_agent_foundry_help_node_id(node)
        if not node_id:
            return None

        for possible_parent in self._get_agent_foundry_help_nodes().values():
            if not isinstance(possible_parent, dict):
                continue

            child_ids = possible_parent.get("children", [])
            if not isinstance(child_ids, list):
                continue

            if node_id in [str(child_id or "").strip() for child_id in child_ids]:
                return possible_parent

        return None

    def _get_agent_foundry_help_child_nodes(
        self,
        node: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        if not isinstance(node, dict):
            return []

        child_ids = node.get("children", [])
        if not isinstance(child_ids, list):
            return []

        results: list[dict[str, Any]] = []

        for child_id in child_ids:
            child_node = self._get_agent_foundry_help_node_by_id(child_id)
            if isinstance(child_node, dict):
                results.append(child_node)

        return results

    def _get_agent_foundry_help_owner_node_for_container(
        self,
        node: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(node, dict):
            return None

        data = self._get_agent_foundry_help_node_data(node)
        owner_node = self._get_agent_foundry_help_node_by_id(data.get("owner_node_id", ""))
        if isinstance(owner_node, dict):
            return owner_node

        return self._get_agent_foundry_help_parent_node(node)

    def _get_agent_foundry_help_source_container_node(
        self,
        node: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(node, dict):
            return None

        data = self._get_agent_foundry_help_node_data(node)
        container_node = self._get_agent_foundry_help_node_by_id(
            data.get("source_container_node_id", "")
        )
        if isinstance(container_node, dict):
            return container_node

        return self._get_agent_foundry_help_parent_node(node)

    def _get_agent_foundry_help_node_id(
        self,
        node: dict[str, Any] | None,
    ) -> str:
        if not isinstance(node, dict):
            return ""

        return str(node.get("id", "") or "").strip()

    def _get_agent_foundry_help_node_name(
        self,
        node: dict[str, Any] | None,
    ) -> str:
        if not isinstance(node, dict):
            return ""

        return str(node.get("name", "") or "").strip()

    def _get_agent_foundry_help_node_kind(
        self,
        node: dict[str, Any] | None,
    ) -> str:
        if not isinstance(node, dict):
            return ""

        return str(node.get("kind", "") or "").strip().lower()

    def _get_agent_foundry_help_node_area(
        self,
        node: dict[str, Any] | None,
    ) -> str:
        if not isinstance(node, dict):
            return ""

        return str(node.get("area", "") or "").strip().lower()

    def _get_agent_foundry_help_node_data(
        self,
        node: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not isinstance(node, dict):
            return {}

        data = node.get("data", {})
        if isinstance(data, dict):
            return data

        return {}

    def _get_agent_foundry_help_container_list_suffix(
        self,
        node: dict[str, Any] | None,
    ) -> str:
        if not isinstance(node, dict):
            return ""

        data = self._get_agent_foundry_help_node_data(node)
        list_suffix = str(data.get("list_suffix", "") or "").strip()
        if list_suffix:
            return list_suffix

        node_name = self._get_agent_foundry_help_node_name(node)
        owner_node = self._get_agent_foundry_help_owner_node_for_container(node)
        owner_name = self._get_agent_foundry_help_node_name(owner_node)

        if owner_name and node_name.startswith(owner_name + " "):
            return node_name[len(owner_name):].strip()

        return ""

    def _get_agent_foundry_help_example_item_name_for_container(
        self,
        node: dict[str, Any],
    ) -> str:
        node_kind = self._get_agent_foundry_help_node_kind(node)
        list_suffix = self._get_agent_foundry_help_container_list_suffix(node)

        if node_kind == "agent_ids" or list_suffix == GRAMMAR_SUFFIX_ID:
            return "agent_000001"

        if node_kind in {"agent_seeded_groups", "seeded_groups"} or list_suffix == GRAMMAR_SUFFIX_SEEDED_GROUPS:
            return "Outcasts"

        if node_kind in {"agent_groups", "groups"} or list_suffix == GRAMMAR_SUFFIX_GROUPS:
            return "Some Group Name"

        if node_kind == "tasks" or list_suffix == GRAMMAR_SUFFIX_TASKS:
            return "Some Task"

        if "prompt" in node_kind or list_suffix == GRAMMAR_SUFFIX_PROMPTS:
            return "main_prompt"

        if "memory" in node_kind or list_suffix == GRAMMAR_SUFFIX_MEMORY:
            return "known_context"

        if "package" in node_kind or list_suffix == GRAMMAR_SUFFIX_PACKAGES:
            return "package_name"

        if "seeded" in node_kind and "default" in node_kind:
            owner_node = self._get_agent_foundry_help_owner_node_for_container(node)
            owner_kind = self._get_agent_foundry_help_node_kind(owner_node)
            if owner_kind == "group":
                return "self_group_name"
            if owner_kind == "task":
                return "self_task_name"
            return "self_agent_name"

        if "default" in node_kind or list_suffix == GRAMMAR_SUFFIX_DEFAULT_RETURNS:
            return "return_name"

        return "item_name"

    def _is_agent_foundry_help_static_node(
        self,
        node: dict[str, Any],
    ) -> bool:
        return self._get_agent_foundry_help_node_kind(node) == "static"

    def _is_agent_foundry_help_container_node(
        self,
        node: dict[str, Any],
    ) -> bool:
        data = self._get_agent_foundry_help_node_data(node)
        if str(data.get("list_suffix", "") or "").strip():
            return True

        node_kind = self._get_agent_foundry_help_node_kind(node)
        return node_kind in {
            "agent_ids",
            "agent_seeded_groups",
            "agent_groups",
            "seeded_groups",
            "groups",
            "tasks",
            "agent_seeded_default_returns",
            "agent_default_returns",
            "seeded_default_returns",
            "default_returns",
            "group_seeded_default_returns",
            "group_default_returns",
            "task_seeded_default_returns",
            "task_default_returns",
            "prompts",
            "memory",
            "packages",
        }

    # -------------------------------------------------------------------------
    # Help-key resolution
    # -------------------------------------------------------------------------

    def _get_agent_foundry_help_key_for_node(
        self,
        node: dict[str, Any],
    ) -> str:
        if not isinstance(node, dict):
            return ""

        node_name = self._get_agent_foundry_help_node_name(node)
        node_kind = self._get_agent_foundry_help_node_kind(node)

        if node_kind == "static":
            static_key = self._get_agent_foundry_help_key_for_static_name(node_name)
            if static_key:
                return static_key
            return "parent_area"

        if node_kind:
            direct_key = HELP_KEY_BY_NODE_KIND.get(node_kind, "")
            if direct_key:
                return direct_key

            return self._infer_agent_foundry_help_key_from_node_kind(node_kind)

        return ""

    def _infer_agent_foundry_help_key_from_node_kind(
        self,
        node_kind: str,
    ) -> str:
        clean_node_kind = str(node_kind or "").strip().lower()
        if not clean_node_kind:
            return ""

        if clean_node_kind == "agent":
            return "agent"

        if clean_node_kind == "agent_ids":
            return "agent_id_container"

        if clean_node_kind.endswith("_container"):
            if "default_return" in clean_node_kind:
                return "default_return_container"
            if "prompt" in clean_node_kind:
                return "prompt_container"
            if "memory" in clean_node_kind:
                return "memory_container"
            if "package" in clean_node_kind:
                return "package_container"
            return "top_level_collection"

        if clean_node_kind in {
            "agent_seeded_groups",
            "agent_groups",
            "seeded_groups",
            "groups",
            "tasks",
        }:
            return "top_level_collection"

        if "default_return" in clean_node_kind or clean_node_kind == "default_return":
            return "default_return"

        if "prompt" in clean_node_kind:
            return "prompt"

        if "memory" in clean_node_kind:
            return "memory"

        if "package" in clean_node_kind:
            return "package"

        if clean_node_kind == "group":
            return "group"

        if clean_node_kind == "task":
            return "task"

        return ""

    def _get_agent_foundry_help_key_for_path(
        self,
        help_path: list[str] | tuple[str, ...],
    ) -> str:
        clean_path = self._normalize_agent_foundry_help_path(help_path)
        if not clean_path:
            return ""

        static_key = HELP_KEY_BY_STATIC_PATH.get(clean_path)
        if static_key:
            return static_key

        if len(clean_path) == 1:
            return self._get_agent_foundry_help_key_for_static_name(clean_path[0])

        return ""

    def _get_agent_foundry_help_key_for_static_name(
        self,
        value: Any,
    ) -> str:
        clean_name = str(value or "").strip()

        if clean_name in {"Blueprint", "Control"}:
            return "blueprint"

        if clean_name == "Viewer":
            return "viewer"

        if clean_name == "Agent":
            return "agent"

        if clean_name in {"Groups", "Tasks"}:
            return "top_level_collection"

        if clean_name == "Package Blueprint":
            return "package_blueprint"

        if clean_name == "Leftovers":
            return "leftovers"

        return ""

    # -------------------------------------------------------------------------
    # Normalization
    # -------------------------------------------------------------------------

    def _normalize_agent_foundry_help_path(
        self,
        help_path: list[str] | tuple[str, ...],
    ) -> tuple[str, ...]:
        if not isinstance(help_path, (list, tuple)):
            return ()

        return tuple(
            str(part or "").strip()
            for part in list(help_path or [])
            if str(part or "").strip()
        )
from __future__ import annotations

from Environment.agent_foundry.foundry_builders import AgentFoundryBuildersMixin
from Environment.agent_foundry.foundry_composer import AgentFoundryComposerMixin
from Environment.agent_foundry.foundry_editing import AgentFoundryEditingMixin
from Environment.agent_foundry.foundry_filtering import AgentFoundryFilteringMixin
from Environment.agent_foundry.foundry_help import AgentFoundryHelpMixin
from Environment.agent_foundry.foundry_package_visual import AgentFoundryPackageVisualMixin
from Environment.agent_foundry.foundry_parsing import AgentFoundryParsingMixin
from Environment.agent_foundry.foundry_utils import AgentFoundryUtilsMixin
from Environment.agent_foundry.foundry_workspace import AgentFoundryWorkspaceMixin


class AgentFoundryTabMixin(
    AgentFoundryBuildersMixin,
    AgentFoundryWorkspaceMixin,
    AgentFoundryFilteringMixin,
    AgentFoundryComposerMixin,
    AgentFoundryEditingMixin,
    AgentFoundryPackageVisualMixin,
    AgentFoundryHelpMixin,
    AgentFoundryParsingMixin,
    AgentFoundryUtilsMixin,
):
    pass
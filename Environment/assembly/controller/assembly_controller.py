from __future__ import annotations

from Environment.assembly.controller.agent_task_lookup_controller import AgentTaskLookupControllerMixin
from Environment.assembly.controller.dirty_controller import DirtyControllerMixin
from Environment.assembly.controller.load_controller import LoadControllerMixin
from Environment.assembly.controller.save_controller import SaveControllerMixin
from Environment.assembly.controller.selection_controller import SelectionControllerMixin
from Environment.assembly.controller.user_approval_lookup_controller import UserApprovalLookupControllerMixin

from Environment.assembly.packages.package_controls import PackageControlsMixin
from Environment.assembly.packages.package_hydration import PackageHydrationMixin
from Environment.assembly.packages.package_mapping import PackageMappingInspectionMixin
from Environment.assembly.packages.package_mapping_row import PackageMappingRowMixin
from Environment.assembly.packages.package_mapping_state import PackageMappingStateMixin
from Environment.assembly.packages.package_row_helpers import PackageRowHelpersMixin
from Environment.assembly.packages.package_special_source_state import PackageSpecialSourceStateMixin
from Environment.assembly.packages.package_special_source_ui import PackageSpecialSourceUiMixin
from Environment.assembly.packages.package_special_sources import PackageSpecialSourcesMixin

from Environment.assembly.state.agent_document_state import AssemblyTasksNormalizationMixin

from Environment.assembly.tabs.defaults_tab import DefaultsTabMixin
from Environment.assembly.tabs.groups_tab import GroupsTabMixin
from Environment.assembly.tabs.memory_tab import MemoryTabMixin
from Environment.assembly.tabs.packages_tab import PackagesTabMixin
from Environment.assembly.tabs.prompts_tab import PromptsTabMixin
from Environment.assembly.tabs.returns_tab import ReturnsTabMixin
from Environment.assembly.tabs.task_tabs import TaskTabsMixin
from Environment.assembly.tabs.triggers_tab import TriggersTabMixin
from Environment.assembly.tabs.workflow_tab import WorkflowTabMixin

from Environment.assembly.widgets.item_picker import ItemPickerMixin
from Environment.assembly.widgets.notebook_helpers import NotebookHelpersMixin


class AssemblyControllerMixin(
    # Generic widget helpers.
    NotebookHelpersMixin,
    ItemPickerMixin,

    # Frontend state / adapter helpers.
    AssemblyTasksNormalizationMixin,

    # Package-specific helpers.
    PackageControlsMixin,
    PackageMappingInspectionMixin,
    PackageMappingStateMixin,
    PackageMappingRowMixin,
    PackageRowHelpersMixin,
    PackageHydrationMixin,
    PackageSpecialSourceStateMixin,
    PackageSpecialSourceUiMixin,
    PackageSpecialSourcesMixin,

    # Controller behavior.
    SelectionControllerMixin,
    AgentTaskLookupControllerMixin,
    UserApprovalLookupControllerMixin,
    SaveControllerMixin,
    LoadControllerMixin,
    DirtyControllerMixin,

    # UI tab surfaces.
    GroupsTabMixin,
    TaskTabsMixin,
    DefaultsTabMixin,
    PackagesTabMixin,
    ReturnsTabMixin,
    WorkflowTabMixin,
    PromptsTabMixin,
    TriggersTabMixin,
    MemoryTabMixin,
):
    """
    Main Assembly editor controller composition.

    This mixin composes the frontend Assembly editor from responsibility-based
    modules:

        - tabs/       : visible Tkinter tab surfaces
        - controller/ : save/load/dirty/selection/lookup orchestration
        - packages/   : package controls, mapping, hydration, and generated package behavior
        - state/      : frontend canonical-agent adapter helpers
        - widgets/    : reusable Tkinter mechanics

    Operations/assembly remains the backend authority for canonical schema,
    disk paths, normalization, validation, projections, and memory file handling.
    """

    pass
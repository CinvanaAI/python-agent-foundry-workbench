class PackageSpecialSourceUiMixin:
    """
    Legacy special-source UI placeholder.

    Mapping now owns the agent/task dropdown branches for:

        - friendship.friendship_agent_name
        - friendship.friendship_task_name
        - append_entry_to_user_approval_report.approval_agent_name
        - append_entry_to_user_approval_report.approval_task_name

    This mixin intentionally does not render source-agent/source-task rows.

    The remaining old special-source state/save cleanup is handled separately.
    """

    def _build_special_runtime_payload_editor(
        self,
        tab_info: dict,
        package_entry: dict,
        package_name: str,
        package_index: int,
        row: int,
        available_previous_return_options: list[str],
        indent: int = 40,
    ) -> int:
        return row

    def _build_special_package_source_row(
        self,
        tab_info: dict,
        package_entry: dict,
        package_name: str,
        package_index: int,
        row: int,
        available_previous_return_options: list[str],
        indent: int = 40,
    ) -> int:
        return row
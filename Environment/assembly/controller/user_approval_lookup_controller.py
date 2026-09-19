from __future__ import annotations


class UserApprovalLookupControllerMixin:
    """
    Generic User Approval lookup helpers for Assembly UI selectors.

    Owns:
        - exposing User Approval target-list names to mapping dropdowns

    Does not own:
        - rendering mapping rows
        - package-specific behavior
        - User Approval report execution
        - saving/mutating agent files
    """

    def _get_user_approval_action_list_map_for_lookup(self) -> dict:
        provider = getattr(self, "_get_user_approval_action_list_map_from_user_control", None)

        if not callable(provider):
            provider = getattr(self, "get_user_approval_action_list_map", None)

        if not callable(provider):
            provider = getattr(self, "_get_user_approval_action_list_map", None)

        if not callable(provider):
            return {}

        result = provider()

        if not isinstance(result, dict):
            return {}

        return result

    def _get_user_approval_target_list_options(self) -> list[str]:
        raw_map = self._get_user_approval_action_list_map_for_lookup()

        options: list[str] = []

        for raw_key in raw_map.keys():
            clean_key = str(raw_key or "").strip()
            if clean_key and clean_key not in options:
                options.append(clean_key)

        return options
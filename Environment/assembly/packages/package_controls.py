from __future__ import annotations

import copy
from tkinter import messagebox


class PackageControlsMixin:
    """
    Package control actions.

    Owns:
        - adding packages from the package manager list
        - adding a selected package snapshot into a task/default scope
        - removing selected packages
        - moving selected packages up/down
        - selected package index state
        - hidden package argument visibility state
        - keeping package-indexed package-control state aligned after remove/move
        - notifying Returns when package-list structure changes

    Does not own:
        - package editor rendering
        - package row construction
        - generic item picker UI
        - backend persistence
        - return list ownership
        - return visibility/friendship ownership
    """

    def _refresh_returns_after_package_list_change(self, tab_info: dict | None) -> None:
        if not isinstance(tab_info, dict):
            return

        if hasattr(self, "_refresh_returns_panel"):
            self._refresh_returns_panel(tab_info)

    def _mark_package_controls_dirty(self, tab_info: dict | None) -> None:
        self._mark_tab_dirty(tab_info)

    def _handle_add_package(self, tab_info: dict) -> None:
        try:
            self._sync_package_directory_state()
            package_names = self.package_controller.get_package_list()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            return

        if not package_names:
            messagebox.showinfo("No Packages", "There are no saved packages yet.")
            return

        self._open_item_picker(
            title_text="Package",
            item_names=package_names,
            on_select=lambda package_name: self._add_package(tab_info, package_name),
        )

    def _add_package(self, tab_info: dict, package_name: str) -> None:
        if not isinstance(tab_info, dict):
            raise ValueError("tab_info must be a dict.")

        packages = tab_info.setdefault("packages", [])
        if not isinstance(packages, list):
            raise ValueError("tab_info['packages'] must be a list.")

        package_snapshot = self._load_full_package_snapshot(package_name)

        if not isinstance(package_snapshot, dict):
            raise ValueError(f"Package '{package_name}' did not load as a dict.")

        packages.append(copy.deepcopy(package_snapshot))

        self._mark_package_controls_dirty(tab_info)
        self._refresh_package_editor(tab_info)
        self._set_selected_package_index(tab_info, len(packages) - 1)
        self._refresh_returns_after_package_list_change(tab_info)

    def _handle_draft_package_list(self, tab_info: dict) -> None:
        self._set_assembly_status(
            "Draft Package List is not wired yet. No package-list draft was created."
        )
        messagebox.showinfo(
            "Draft Package List",
            "This action is not wired yet.\n\nNo files were created or changed.",
        )

    def _set_selected_package_index(self, tab_info: dict, index: int | None) -> None:
        if not isinstance(tab_info, dict):
            return

        tab_info["selected_package_index"] = index
        self._apply_package_selection_styles(tab_info)

    def _get_show_hidden_package_arguments(
        self,
        tab_info: dict,
        package_index: int,
    ) -> bool:
        state_map = tab_info.setdefault("show_hidden_package_arguments", {})

        if not isinstance(state_map, dict):
            state_map = {}
            tab_info["show_hidden_package_arguments"] = state_map

        return bool(state_map.get(package_index, state_map.get(str(package_index), False)))

    def _set_show_hidden_package_arguments(
        self,
        tab_info: dict,
        package_index: int,
        show_hidden: bool,
    ) -> None:
        state_map = tab_info.setdefault("show_hidden_package_arguments", {})

        if not isinstance(state_map, dict):
            state_map = {}
            tab_info["show_hidden_package_arguments"] = state_map

        state_map[package_index] = bool(show_hidden)

    def _toggle_show_hidden_package_arguments(
        self,
        tab_info: dict,
        package_index: int,
    ) -> None:
        current = self._get_show_hidden_package_arguments(tab_info, package_index)
        self._set_show_hidden_package_arguments(tab_info, package_index, not current)

        self._mark_package_controls_dirty(tab_info)
        self._refresh_package_editor(tab_info)

    def _require_selected_package_index(self, tab_info: dict) -> int:
        if not isinstance(tab_info, dict):
            raise ValueError("Package tab state is missing.")

        packages = tab_info.get("packages", [])
        if not isinstance(packages, list):
            raise ValueError("Package list is invalid.")

        index = tab_info.get("selected_package_index")

        if index is None:
            raise ValueError("Click a package name first.")

        if not isinstance(index, int):
            raise ValueError("Selected package index is invalid.")

        if index < 0 or index >= len(packages):
            raise ValueError("Selected package is out of range.")

        return index

    def _reindex_show_hidden_package_arguments_after_remove(
        self,
        tab_info: dict,
        removed_index: int,
    ) -> None:
        show_hidden_state = tab_info.setdefault("show_hidden_package_arguments", {})

        if not isinstance(show_hidden_state, dict):
            tab_info["show_hidden_package_arguments"] = {}
            return

        rebuilt_state: dict[int, bool] = {}

        for raw_old_index, state in show_hidden_state.items():
            try:
                old_index = int(raw_old_index)
            except Exception:
                continue

            if old_index == removed_index:
                continue

            if old_index > removed_index:
                rebuilt_state[old_index - 1] = bool(state)
            else:
                rebuilt_state[old_index] = bool(state)

        tab_info["show_hidden_package_arguments"] = rebuilt_state

    def _swap_show_hidden_package_arguments(
        self,
        tab_info: dict,
        first_index: int,
        second_index: int,
    ) -> None:
        state_map = tab_info.setdefault("show_hidden_package_arguments", {})

        if not isinstance(state_map, dict):
            state_map = {}
            tab_info["show_hidden_package_arguments"] = state_map

        first_state = bool(state_map.get(first_index, state_map.get(str(first_index), False)))
        second_state = bool(state_map.get(second_index, state_map.get(str(second_index), False)))

        state_map[first_index] = second_state
        state_map[second_index] = first_state

    def _handle_remove_package(self, tab_info: dict) -> None:
        try:
            index = self._require_selected_package_index(tab_info)
        except Exception as exc:
            messagebox.showerror("Remove Failed", str(exc))
            return

        packages = tab_info["packages"]
        del packages[index]

        self._remove_special_package_source(tab_info, index)
        self._reindex_special_package_sources_after_remove(tab_info, index)

        self._reindex_show_hidden_package_arguments_after_remove(tab_info, index)

        if not packages:
            tab_info["selected_package_index"] = None
        elif index >= len(packages):
            tab_info["selected_package_index"] = len(packages) - 1
        else:
            tab_info["selected_package_index"] = index

        self._mark_package_controls_dirty(tab_info)
        self._refresh_package_editor(tab_info)
        self._refresh_returns_after_package_list_change(tab_info)

    def _move_package_up(self, tab_info: dict) -> None:
        try:
            index = self._require_selected_package_index(tab_info)
        except Exception as exc:
            messagebox.showerror("No Selection", str(exc))
            return

        if index == 0:
            return

        packages = tab_info["packages"]

        packages[index - 1], packages[index] = (
            packages[index],
            packages[index - 1],
        )

        self._swap_special_package_sources(tab_info, index - 1, index)
        self._swap_show_hidden_package_arguments(tab_info, index - 1, index)

        self._mark_package_controls_dirty(tab_info)
        self._refresh_package_editor(tab_info)
        self._set_selected_package_index(tab_info, index - 1)
        self._refresh_returns_after_package_list_change(tab_info)

    def _move_package_down(self, tab_info: dict) -> None:
        try:
            index = self._require_selected_package_index(tab_info)
        except Exception as exc:
            messagebox.showerror("No Selection", str(exc))
            return

        packages = tab_info["packages"]

        if index >= len(packages) - 1:
            return

        packages[index], packages[index + 1] = (
            packages[index + 1],
            packages[index],
        )

        self._swap_special_package_sources(tab_info, index, index + 1)
        self._swap_show_hidden_package_arguments(tab_info, index, index + 1)

        self._mark_package_controls_dirty(tab_info)
        self._refresh_package_editor(tab_info)
        self._set_selected_package_index(tab_info, index + 1)
        self._refresh_returns_after_package_list_change(tab_info)
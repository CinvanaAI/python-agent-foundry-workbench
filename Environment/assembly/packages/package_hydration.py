from __future__ import annotations

import copy


class PackageHydrationMixin:
    """
    Refreshes package definitions from disk, then overlays task-local values.

    Owns:
        - package argument mapping overlay
        - package argument fallback/hidden overlay
        - required/optional replacement value overlay
        - package return flag overlay
        - package rehydration before canonical save

    Does not own:
        - special package source extraction
        - approval action source behavior
        - trigger stamp merging
    """

    FRIENDSHIP_PACKAGE_NAME = "friendship"

    def _apply_argument_overlay_to_fresh_package(
        self,
        fresh_package_entry: dict,
        current_package_entry: dict,
    ) -> None:
        if not isinstance(fresh_package_entry, dict):
            raise ValueError("fresh_package_entry must be a dict.")

        if not isinstance(current_package_entry, dict):
            raise ValueError("current_package_entry must be a dict.")

        fresh_arguments = fresh_package_entry.get("arguments", [])
        if fresh_arguments in (None, ""):
            fresh_arguments = []
            fresh_package_entry["arguments"] = fresh_arguments

        if not isinstance(fresh_arguments, list):
            raise ValueError("Fresh package arguments must be a list.")

        current_arguments = current_package_entry.get("arguments", [])
        if current_arguments in (None, ""):
            current_arguments = []

        if not isinstance(current_arguments, list):
            raise ValueError("Current package arguments must be a list.")

        current_argument_map: dict[str, dict] = {}

        for index, argument_entry in enumerate(current_arguments, start=1):
            if not isinstance(argument_entry, dict):
                raise ValueError(f"Current package argument {index} must be a dict.")

            argument_value_name = str(argument_entry.get("argument_value_name", "")).strip()
            if not argument_value_name:
                raise ValueError(f"Current package argument {index} is missing argument_value_name.")

            current_argument_map[argument_value_name] = copy.deepcopy(argument_entry)

        for index, fresh_argument_entry in enumerate(fresh_arguments, start=1):
            if not isinstance(fresh_argument_entry, dict):
                raise ValueError(f"Fresh package argument {index} must be a dict.")

            argument_value_name = str(fresh_argument_entry.get("argument_value_name", "")).strip()
            if not argument_value_name:
                raise ValueError(f"Fresh package argument {index} is missing argument_value_name.")

            current_argument_entry = current_argument_map.get(argument_value_name)
            if current_argument_entry is None:
                continue

            if "task_argument_mapping" in current_argument_entry:
                mapping = current_argument_entry.get("task_argument_mapping")
                if not isinstance(mapping, dict):
                    raise ValueError(
                        f"Argument '{argument_value_name}' task_argument_mapping must be a dict."
                    )

                fresh_argument_entry["task_argument_mapping"] = copy.deepcopy(mapping)

            if "argument_fallback" in current_argument_entry:
                fallback_value = current_argument_entry.get("argument_fallback", "")
                fresh_argument_entry["argument_fallback"] = (
                    "" if fallback_value is None else str(fallback_value)
                )

            if "argument_hidden" in current_argument_entry:
                fresh_argument_entry["argument_hidden"] = bool(
                    current_argument_entry.get("argument_hidden", False)
                )

    def _apply_replacement_overlay_to_fresh_package(
        self,
        fresh_package_entry: dict,
        current_package_entry: dict,
        section_name: str,
    ) -> None:
        if section_name not in {"required_replacements", "optional_replacements"}:
            raise ValueError(f"Unknown replacement section: {section_name}")

        fresh_section = fresh_package_entry.get(section_name, [])
        if fresh_section in (None, ""):
            fresh_section = []
            fresh_package_entry[section_name] = fresh_section

        if not isinstance(fresh_section, list):
            raise ValueError(f"Fresh package {section_name} must be a list.")

        current_section = current_package_entry.get(section_name, [])
        if current_section in (None, ""):
            current_section = []

        if not isinstance(current_section, list):
            raise ValueError(f"Current package {section_name} must be a list.")

        current_value_map: dict[str, str] = {}

        for index, entry in enumerate(current_section, start=1):
            if not isinstance(entry, dict):
                raise ValueError(f"Current {section_name} entry {index} must be a dict.")

            label = str(entry.get("to_be_replaced", "")).strip()
            if not label:
                raise ValueError(f"Current {section_name} entry {index} is missing to_be_replaced.")

            value = entry.get("value", "")
            current_value_map[label] = "" if value is None else str(value)

        for index, fresh_entry in enumerate(fresh_section, start=1):
            if not isinstance(fresh_entry, dict):
                raise ValueError(f"Fresh {section_name} entry {index} must be a dict.")

            label = str(fresh_entry.get("to_be_replaced", "")).strip()
            if not label:
                raise ValueError(f"Fresh {section_name} entry {index} is missing to_be_replaced.")

            if label in current_value_map:
                fresh_entry["value"] = current_value_map[label]

    def _normalize_return_flag_overlay_state(self, return_entry: dict) -> dict[str, bool]:
        if not isinstance(return_entry, dict):
            return {
                "visible": True,
                "friendship": False,
            }

        return {
            "visible": bool(return_entry.get("visible", True)),
            "friendship": bool(return_entry.get("friendship", False)),
        }

    def _apply_return_overlay_to_fresh_package(
        self,
        fresh_package_entry: dict,
        current_package_entry: dict,
    ) -> None:
        if not isinstance(fresh_package_entry, dict):
            raise ValueError("fresh_package_entry must be a dict.")

        if not isinstance(current_package_entry, dict):
            raise ValueError("current_package_entry must be a dict.")

        fresh_returns = fresh_package_entry.get("returns", [])
        if fresh_returns in (None, ""):
            fresh_returns = []
            fresh_package_entry["returns"] = fresh_returns

        if not isinstance(fresh_returns, list):
            raise ValueError("Fresh package returns must be a list.")

        current_returns = current_package_entry.get("returns", [])
        if current_returns in (None, ""):
            current_returns = []

        if not isinstance(current_returns, list):
            raise ValueError("Current package returns must be a list.")

        current_return_flag_map: dict[str, dict[str, bool]] = {}

        for index, current_return_entry in enumerate(current_returns, start=1):
            if not isinstance(current_return_entry, dict):
                raise ValueError(f"Current package return {index} must be a dict.")

            return_value_name = str(current_return_entry.get("return_value_name", "")).strip()
            if not return_value_name:
                raise ValueError(f"Current package return {index} is missing return_value_name.")

            current_return_flag_map[return_value_name] = self._normalize_return_flag_overlay_state(
                current_return_entry
            )

        for index, fresh_return_entry in enumerate(fresh_returns, start=1):
            if not isinstance(fresh_return_entry, dict):
                raise ValueError(f"Fresh package return {index} must be a dict.")

            return_value_name = str(fresh_return_entry.get("return_value_name", "")).strip()
            if not return_value_name:
                raise ValueError(f"Fresh package return {index} is missing return_value_name.")

            current_flags = current_return_flag_map.get(return_value_name)

            if current_flags is None:
                fresh_return_entry["visible"] = bool(fresh_return_entry.get("visible", True))
                fresh_return_entry["friendship"] = bool(fresh_return_entry.get("friendship", False))
                continue

            fresh_return_entry["visible"] = bool(current_flags.get("visible", True))
            fresh_return_entry["friendship"] = bool(current_flags.get("friendship", False))

    def _apply_friendship_generated_returns_to_fresh_package(
        self,
        fresh_package_entry: dict,
        current_package_entry: dict,
    ) -> None:
        """
        Friendship returns are generated into the task-local package instance.

        The base package file may have no returns, so normal return overlay would
        otherwise wipe them during rehydration. Preserve the current generated
        return list as the fresh package return list.
        """
        package_name = str(current_package_entry.get("name", "")).strip().lower()
        if package_name != self.FRIENDSHIP_PACKAGE_NAME:
            return

        current_returns = current_package_entry.get("returns", [])
        if current_returns in (None, ""):
            current_returns = []

        if not isinstance(current_returns, list):
            raise ValueError("Current Friendship package returns must be a list.")

        fresh_package_entry["returns"] = copy.deepcopy(current_returns)

    def _rehydrate_packages_from_disk_for_save(self, packages: list[dict]) -> list[dict]:
        if packages in (None, ""):
            return []

        if not isinstance(packages, list):
            raise ValueError("packages must be a list.")

        rebuilt_packages: list[dict] = []

        for index, current_package_entry in enumerate(packages, start=1):
            if not isinstance(current_package_entry, dict):
                raise ValueError(f"Package entry {index} must be a dict.")

            package_name = str(current_package_entry.get("name", "")).strip()
            if not package_name:
                raise ValueError(f"Package entry {index} is missing name.")

            fresh_package_entry = self._load_full_package_snapshot(package_name)

            self._apply_argument_overlay_to_fresh_package(
                fresh_package_entry=fresh_package_entry,
                current_package_entry=current_package_entry,
            )

            self._apply_replacement_overlay_to_fresh_package(
                fresh_package_entry=fresh_package_entry,
                current_package_entry=current_package_entry,
                section_name="required_replacements",
            )

            self._apply_replacement_overlay_to_fresh_package(
                fresh_package_entry=fresh_package_entry,
                current_package_entry=current_package_entry,
                section_name="optional_replacements",
            )

            self._apply_return_overlay_to_fresh_package(
                fresh_package_entry=fresh_package_entry,
                current_package_entry=current_package_entry,
            )

            self._apply_friendship_generated_returns_to_fresh_package(
                fresh_package_entry=fresh_package_entry,
                current_package_entry=current_package_entry,
            )

            rebuilt_packages.append(fresh_package_entry)

        return rebuilt_packages
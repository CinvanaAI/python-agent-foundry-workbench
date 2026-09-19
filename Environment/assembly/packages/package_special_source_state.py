from __future__ import annotations

import copy


class PackageSpecialSourceStateMixin:
    """
    Generated special-package field helpers.

    This file no longer owns a task-level friendship/package_sources side channel.

    Owns:
        - reading selected source agent/task from package arguments
        - loading the selected source task
        - discovering external argument fields from the selected source task
        - printing generated payload arguments into the package runtime_payload argument
        - discovering friendship-approved returns from the selected source task
        - printing generated returns into the Friendship package instance

    Does not own:
        - special source row rendering
        - save-time package hydration
        - backend persistence
        - generic argument row rendering
    """

    FRIENDSHIP_PACKAGE_NAME = "friendship"
    APPEND_PACKAGE_NAME = "append_entry_to_user_approval_report"

    FRIENDSHIP_AGENT_ARGUMENT_NAME = "friendship_agent_name"
    FRIENDSHIP_TASK_ARGUMENT_NAME = "friendship_task_name"

    APPEND_AGENT_ARGUMENT_NAME = "approval_agent_name"
    APPEND_TASK_ARGUMENT_NAME = "approval_task_name"
    APPEND_TARGET_LIST_ARGUMENT_NAME = "target_list_name"

    RUNTIME_PAYLOAD_ARGUMENT_NAME = "runtime_payload"

    def _get_special_package_source_config_map(self) -> dict[str, dict]:
        """
        Compatibility config for callers that ask whether a package has generated
        package-local behavior.

        Mapping rows own dropdown rendering.
        This helper owns generated runtime_payload fields and Friendship returns.
        """
        return {
            self.FRIENDSHIP_PACKAGE_NAME: {
                "title": "Friendship Source",
                "agent_argument_name": self.FRIENDSHIP_AGENT_ARGUMENT_NAME,
                "task_argument_name": self.FRIENDSHIP_TASK_ARGUMENT_NAME,
                "target_list_argument_name": "",
                "payload_argument_name": self.RUNTIME_PAYLOAD_ARGUMENT_NAME,
                "supports_payload_import": True,
                "supports_generated_returns": True,
            },
            self.APPEND_PACKAGE_NAME: {
                "title": "Approval Action Source",
                "agent_argument_name": self.APPEND_AGENT_ARGUMENT_NAME,
                "task_argument_name": self.APPEND_TASK_ARGUMENT_NAME,
                "target_list_argument_name": self.APPEND_TARGET_LIST_ARGUMENT_NAME,
                "payload_argument_name": self.RUNTIME_PAYLOAD_ARGUMENT_NAME,
                "supports_payload_import": True,
                "supports_generated_returns": False,
            },
        }

    def _get_special_package_source_config(self, package_name: str) -> dict | None:
        clean_name = str(package_name or "").strip().lower()
        if not clean_name:
            return None

        return self._get_special_package_source_config_map().get(clean_name)

    def _get_special_package_source_agent_options(self) -> list[str]:
        if hasattr(self, "_get_agent_lookup_options"):
            try:
                return self._get_agent_lookup_options()
            except Exception:
                return []

        try:
            return self.assembly_manager.list_agents()
        except Exception:
            return []

    def _get_special_package_source_task_options(self, source_agent: str) -> list[str]:
        clean_agent = str(source_agent or "").strip()
        if not clean_agent:
            return []

        if hasattr(self, "_get_task_lookup_options"):
            try:
                return self._get_task_lookup_options(clean_agent)
            except Exception:
                return []

        try:
            return self.assembly_manager.get_task_names(clean_agent)
        except Exception:
            return []

    def _get_user_approval_action_list_map(self) -> dict:
        provider = getattr(self, "_get_user_approval_action_list_map_from_user_control", None)

        if not callable(provider):
            provider = getattr(self, "get_user_approval_action_list_map", None)

        if not callable(provider):
            raise RuntimeError(
                "User approval action list map provider is missing. "
                "Expected _get_user_approval_action_list_map_from_user_control "
                "or get_user_approval_action_list_map."
            )

        result = provider()

        if not isinstance(result, dict):
            raise ValueError("User approval action list map provider must return a dict.")

        cleaned: dict[str, dict] = {}

        for raw_key, raw_value in result.items():
            clean_key = str(raw_key or "").strip()

            if not clean_key:
                raise ValueError("User approval action list map provider returned a blank action-list key.")

            if raw_value is None:
                clean_value = {}
            elif isinstance(raw_value, dict):
                clean_value = dict(raw_value)
            else:
                raise ValueError(
                    f"User approval action-list metadata for '{clean_key}' must be a dict or None."
                )

            cleaned[clean_key] = clean_value

        return cleaned

    def _get_user_approval_target_list_options(self) -> list[str]:
        """
        Temporary compatibility provider until the dedicated controller helper is
        added in the next batch with task/group tabs.

        Mapping rows call this method name. The later controller can own it
        cleanly without changing mapping again.
        """
        raw_map = self._get_user_approval_action_list_map()

        options: list[str] = []

        for key in raw_map.keys():
            clean_key = str(key).strip()
            if clean_key and clean_key not in options:
                options.append(clean_key)

        return options

    def _get_special_package_target_list_options(self, package_name: str) -> list[str]:
        config = self._get_special_package_source_config(package_name)
        if not config:
            return []

        target_list_argument_name = str(config.get("target_list_argument_name", "")).strip()
        if not target_list_argument_name:
            return []

        return self._get_user_approval_target_list_options()

    # ---------------------------------------------------------------------
    # Legacy source-state compatibility no-ops.
    # ---------------------------------------------------------------------

    def _get_special_package_sources_map(self, tab_info: dict) -> dict:
        return {}

    def _get_special_package_source(self, tab_info: dict, package_index: int) -> dict:
        return {
            "source_agent": "",
            "source_task": "",
            "target_list_name": "",
            "imported_payload_fields": [],
        }

    def _set_special_package_source(
        self,
        tab_info: dict,
        package_index: int,
        source_agent: str = "",
        source_task: str = "",
        target_list_name: str = "",
        imported_payload_fields: list | None = None,
        mark_dirty: bool = True,
    ) -> None:
        return

    def _remove_special_package_source(self, tab_info: dict, package_index: int) -> None:
        return

    def _reindex_special_package_sources_after_remove(self, tab_info: dict, removed_index: int) -> None:
        return

    def _swap_special_package_sources(
        self,
        tab_info: dict,
        first_index: int,
        second_index: int,
    ) -> None:
        return

    def _sync_special_package_payload_imports(
        self,
        tab_info: dict,
        package_entry: dict,
        package_name: str,
        package_index: int,
    ) -> None:
        return

    def _apply_special_package_values_to_arguments(
        self,
        tab_info: dict,
        package_entry: dict,
        package_name: str,
        package_index: int,
    ) -> None:
        return

    # ---------------------------------------------------------------------
    # Package argument lookup helpers.
    # ---------------------------------------------------------------------

    def _get_package_argument_entry(
        self,
        package_entry: dict,
        argument_value_name: str,
    ) -> dict | None:
        clean_argument_value_name = str(argument_value_name or "").strip()

        if not isinstance(package_entry, dict) or not clean_argument_value_name:
            return None

        raw_arguments = package_entry.get("arguments", [])
        if not isinstance(raw_arguments, list):
            return None

        for argument_entry in raw_arguments:
            if not isinstance(argument_entry, dict):
                continue

            current_value_name = str(argument_entry.get("argument_value_name", "")).strip()
            if not current_value_name:
                current_value_name = str(argument_entry.get("argument_question", "")).strip()

            if current_value_name == clean_argument_value_name:
                return argument_entry

        return None

    def _upsert_package_argument_entry(
        self,
        package_entry: dict,
        argument_value_name: str,
        argument_question: str = "",
        argument_hidden: bool = True,
    ) -> dict:
        if not isinstance(package_entry, dict):
            raise ValueError("package_entry must be a dict.")

        clean_argument_value_name = str(argument_value_name or "").strip()
        if not clean_argument_value_name:
            raise ValueError("argument_value_name is required.")

        raw_arguments = package_entry.get("arguments", [])
        if raw_arguments in (None, ""):
            raw_arguments = []
            package_entry["arguments"] = raw_arguments

        if not isinstance(raw_arguments, list):
            raise ValueError("package arguments must be a list.")

        existing_entry = self._get_package_argument_entry(
            package_entry=package_entry,
            argument_value_name=clean_argument_value_name,
        )

        if existing_entry is not None:
            if not str(existing_entry.get("argument_question", "")).strip():
                existing_entry["argument_question"] = argument_question or clean_argument_value_name

            existing_entry["argument_value_name"] = clean_argument_value_name

            if "argument_fallback" not in existing_entry:
                existing_entry["argument_fallback"] = ""

            if "argument_hidden" not in existing_entry:
                existing_entry["argument_hidden"] = bool(argument_hidden)

            if not isinstance(existing_entry.get("task_argument_mapping"), dict):
                existing_entry["task_argument_mapping"] = {
                    "source_type": "manual",
                    "manual_value": "",
                }

            return existing_entry

        new_entry = {
            "argument_question": argument_question or clean_argument_value_name,
            "argument_value_name": clean_argument_value_name,
            "argument_fallback": "",
            "argument_hidden": bool(argument_hidden),
            "task_argument_mapping": {
                "source_type": "manual",
                "manual_value": "",
            },
        }
        raw_arguments.append(new_entry)
        return new_entry

    def _get_special_package_argument_manual_value(
        self,
        package_entry: dict,
        argument_value_name: str,
    ) -> str:
        argument_entry = self._get_package_argument_entry(package_entry, argument_value_name)
        if not isinstance(argument_entry, dict):
            return ""

        mapping = argument_entry.get("task_argument_mapping", {})
        if not isinstance(mapping, dict):
            return ""

        if str(mapping.get("source_type", "")).strip() != "manual":
            return ""

        return str(mapping.get("manual_value", "")).strip()

    def _get_special_package_source_from_arguments(
        self,
        package_entry: dict,
        package_name: str,
    ) -> tuple[str, str]:
        config = self._get_special_package_source_config(package_name)
        if not config:
            return "", ""

        agent_argument_name = str(config.get("agent_argument_name", "")).strip()
        task_argument_name = str(config.get("task_argument_name", "")).strip()

        if not agent_argument_name or not task_argument_name:
            return "", ""

        source_agent = self._get_special_package_argument_manual_value(
            package_entry,
            agent_argument_name,
        )
        source_task = self._get_special_package_argument_manual_value(
            package_entry,
            task_argument_name,
        )

        return source_agent, source_task

    def _get_friendship_source_from_package(self, package_entry: dict) -> tuple[str, str]:
        return self._get_special_package_source_from_arguments(
            package_entry=package_entry,
            package_name=self.FRIENDSHIP_PACKAGE_NAME,
        )

    # ---------------------------------------------------------------------
    # Source task loading.
    # ---------------------------------------------------------------------

    def _load_special_source_task_payload(self, source_agent: str, source_task: str) -> dict | None:
        clean_agent = str(source_agent or "").strip()
        clean_task = str(source_task or "").strip()

        if not clean_agent or not clean_task:
            return None

        if hasattr(self, "_get_task_data_for_lookup"):
            try:
                payload = self._get_task_data_for_lookup(clean_agent, clean_task)
                if isinstance(payload, dict):
                    return payload
            except Exception:
                return None

        manager = getattr(self, "assembly_manager", None)

        if manager is None:
            return None

        if hasattr(manager, "load_task_data") and callable(manager.load_task_data):
            try:
                payload = manager.load_task_data(
                    agent_name=clean_agent,
                    task_name=clean_task,
                )
                if isinstance(payload, dict):
                    return payload
            except Exception:
                return None

        return None

    # ---------------------------------------------------------------------
    # External payload field discovery.
    # ---------------------------------------------------------------------

    def _is_external_marker_text(self, value: object) -> bool:
        if not isinstance(value, str):
            return False

        clean_value = value.strip().lower()
        return clean_value == "external" or clean_value.startswith("external=")

    def _extract_external_name_from_marker(self, value: object, default_name: str) -> str:
        clean_default_name = str(default_name or "").strip()

        if not isinstance(value, str):
            return clean_default_name

        clean_value = value.strip()
        lowered_value = clean_value.lower()

        if lowered_value.startswith("external="):
            external_name = clean_value.split("=", 1)[1].strip()
            if external_name:
                return external_name

        return clean_default_name

    def _build_external_payload_field(
        self,
        argument_value_name: str,
        argument_question: str = "",
        argument_hidden: bool = False,
        external_value_name: str = "",
    ) -> dict:
        clean_argument_value_name = str(argument_value_name or "").strip()
        clean_external_value_name = str(external_value_name or "").strip() or clean_argument_value_name
        clean_argument_question = str(argument_question or "").strip() or clean_argument_value_name

        if not clean_argument_value_name:
            raise ValueError("argument_value_name is required.")

        return {
            "argument_question": clean_argument_question,
            "argument_value_name": clean_argument_value_name,
            "argument_fallback": "",
            "argument_hidden": bool(argument_hidden),
            "task_argument_mapping": {
                "source_type": "external",
                "external_value_name": clean_external_value_name,
            },
        }

    def _extract_nested_external_payload_fields(
        self,
        raw_value: object,
        fallback_name: str = "",
        argument_hidden: bool = False,
    ) -> list[dict]:
        discovered: list[dict] = []

        def walk(value: object, current_name: str = "") -> None:
            clean_current_name = str(current_name or "").strip()

            if isinstance(value, str):
                if not self._is_external_marker_text(value):
                    return

                external_value_name = self._extract_external_name_from_marker(
                    value,
                    clean_current_name,
                )
                argument_value_name = external_value_name or clean_current_name

                if not argument_value_name:
                    return

                discovered.append(
                    self._build_external_payload_field(
                        argument_value_name=argument_value_name,
                        argument_question=argument_value_name,
                        argument_hidden=argument_hidden,
                        external_value_name=external_value_name or argument_value_name,
                    )
                )
                return

            if isinstance(value, dict):
                for raw_key, child_value in value.items():
                    child_name = str(raw_key or "").strip() or clean_current_name
                    walk(child_value, child_name)
                return

            if isinstance(value, list):
                for child_value in value:
                    walk(child_value, clean_current_name)

        walk(raw_value, fallback_name)
        return discovered

    def _extract_external_arguments_from_task_payload(self, task_payload: dict) -> list[dict]:
        results: list[dict] = []
        seen_value_names: set[str] = set()

        def add_result(item: dict) -> None:
            if not isinstance(item, dict):
                return

            argument_value_name = str(item.get("argument_value_name", "")).strip()
            argument_question = str(item.get("argument_question", "")).strip()

            if not argument_value_name:
                argument_value_name = argument_question

            if not argument_question:
                argument_question = argument_value_name

            if not argument_value_name:
                return

            if argument_value_name in seen_value_names:
                return

            seen_value_names.add(argument_value_name)

            mapping = item.get("task_argument_mapping", {})
            if not isinstance(mapping, dict):
                mapping = {}

            external_value_name = str(mapping.get("external_value_name", "")).strip() or argument_value_name

            results.append(
                {
                    "argument_question": argument_question,
                    "argument_value_name": argument_value_name,
                    "argument_fallback": "",
                    "argument_hidden": bool(item.get("argument_hidden", False)),
                    "task_argument_mapping": {
                        "source_type": "external",
                        "external_value_name": external_value_name,
                    },
                }
            )

        if not isinstance(task_payload, dict):
            return results

        raw_packages = task_payload.get("packages", [])
        if not isinstance(raw_packages, list):
            raw_packages = []

        for package_entry in raw_packages:
            if not isinstance(package_entry, dict):
                continue

            raw_arguments = package_entry.get("arguments", [])
            if not isinstance(raw_arguments, list):
                continue

            for argument_entry in raw_arguments:
                if not isinstance(argument_entry, dict):
                    continue

                argument_value_name = str(argument_entry.get("argument_value_name", "")).strip()
                argument_question = str(argument_entry.get("argument_question", "")).strip()

                if not argument_value_name:
                    argument_value_name = argument_question

                if not argument_question:
                    argument_question = argument_value_name

                if not argument_value_name:
                    continue

                mapping = argument_entry.get("task_argument_mapping", {})
                if not isinstance(mapping, dict):
                    mapping = {}

                source_type = str(mapping.get("source_type", "")).strip().lower()
                manual_value = mapping.get("manual_value", "")
                external_value_name = str(mapping.get("external_value_name", "")).strip()

                if source_type == "external":
                    add_result(
                        self._build_external_payload_field(
                            argument_value_name=argument_value_name,
                            argument_question=argument_question,
                            argument_hidden=bool(argument_entry.get("argument_hidden", False)),
                            external_value_name=external_value_name or argument_value_name,
                        )
                    )

                for nested_field in self._extract_nested_external_payload_fields(
                    raw_value=manual_value,
                    fallback_name=argument_value_name,
                    argument_hidden=bool(argument_entry.get("argument_hidden", False)),
                ):
                    add_result(nested_field)

        return results

    def _get_imported_external_payload_fields(self, source_agent: str, source_task: str) -> list[dict]:
        clean_agent = str(source_agent or "").strip()
        clean_task = str(source_task or "").strip()

        if not clean_agent or not clean_task:
            return []

        task_payload = self._load_special_source_task_payload(clean_agent, clean_task)

        if not isinstance(task_payload, dict):
            return []

        return self._extract_external_arguments_from_task_payload(task_payload)

    # ---------------------------------------------------------------------
    # Friendship return discovery.
    # ---------------------------------------------------------------------

    def _normalize_friendship_return_item(self, raw_item: object) -> dict | None:
        if isinstance(raw_item, str):
            return_value_name = raw_item.strip()
            if not return_value_name:
                return None

            return {
                "return_value_name": return_value_name,
                "return_description": "",
                "visible": True,
                "friendship": False,
            }

        if not isinstance(raw_item, dict):
            return None

        return_value_name = str(raw_item.get("return_value_name", "")).strip()
        if not return_value_name:
            return_value_name = str(raw_item.get("name", "")).strip()

        if not return_value_name:
            return None

        return {
            "return_value_name": return_value_name,
            "return_description": str(raw_item.get("return_description", "")).strip(),
            "visible": bool(raw_item.get("visible", True)),
            "friendship": bool(raw_item.get("friendship", False)),
        }

    def _extract_friendship_returns_from_task_data(self, source_task_data: dict) -> list[dict]:
        """
        Extract returns that Friendship is allowed to borrow from a saved source task.

        Rule:
            - source_task_data["default_returns"] are always friendship-enabled.
            - source_task_data["packages"][...]["returns"][...] are borrowed only
              when return_entry["friendship"] is True.
        """
        if not isinstance(source_task_data, dict):
            return []

        collected_returns: list[dict] = []
        seen_return_names: set[str] = set()

        default_returns = source_task_data.get("default_returns", [])
        if default_returns in (None, ""):
            default_returns = []

        if isinstance(default_returns, list):
            for default_entry in default_returns:
                normalized_default = self._normalize_friendship_return_item(default_entry)
                if normalized_default is None:
                    continue

                return_value_name = str(normalized_default.get("return_value_name", "")).strip()
                if not return_value_name or return_value_name in seen_return_names:
                    continue

                seen_return_names.add(return_value_name)
                normalized_default["visible"] = True
                normalized_default["friendship"] = False
                collected_returns.append(normalized_default)

        packages = source_task_data.get("packages", [])
        if packages in (None, ""):
            packages = []

        if not isinstance(packages, list):
            return collected_returns

        for package_entry in packages:
            if not isinstance(package_entry, dict):
                continue

            raw_returns = package_entry.get("returns", [])
            if raw_returns in (None, ""):
                raw_returns = []

            if not isinstance(raw_returns, list):
                continue

            for return_entry in raw_returns:
                if not isinstance(return_entry, dict):
                    continue

                if not bool(return_entry.get("friendship", False)):
                    continue

                normalized_return = self._normalize_friendship_return_item(return_entry)
                if normalized_return is None:
                    continue

                return_value_name = str(normalized_return.get("return_value_name", "")).strip()
                if not return_value_name or return_value_name in seen_return_names:
                    continue

                seen_return_names.add(return_value_name)
                normalized_return["visible"] = True
                normalized_return["friendship"] = False
                collected_returns.append(normalized_return)

        return collected_returns

    # ---------------------------------------------------------------------
    # Generated package sync.
    # ---------------------------------------------------------------------

    def _normalize_payload_argument_item(self, item: object) -> dict | None:
        if not isinstance(item, dict):
            return None

        argument_value_name = str(item.get("argument_value_name", "")).strip()
        argument_question = str(item.get("argument_question", "")).strip()

        if not argument_value_name:
            argument_value_name = argument_question

        if not argument_question:
            argument_question = argument_value_name

        if not argument_value_name:
            return None

        mapping = item.get("task_argument_mapping", {})
        if not isinstance(mapping, dict):
            mapping = {
                "source_type": "external",
                "external_value_name": argument_value_name,
            }

        return {
            "argument_question": argument_question,
            "argument_value_name": argument_value_name,
            "argument_fallback": str(item.get("argument_fallback", "") or ""),
            "argument_hidden": bool(item.get("argument_hidden", False)),
            "task_argument_mapping": copy.deepcopy(mapping),
        }

    def _merge_payload_arguments(
        self,
        existing_arguments: object,
        generated_arguments: list[dict],
    ) -> list[dict]:
        existing_by_name: dict[str, dict] = {}

        if isinstance(existing_arguments, list):
            for existing_item in existing_arguments:
                normalized_existing = self._normalize_payload_argument_item(existing_item)
                if normalized_existing is None:
                    continue

                existing_by_name[normalized_existing["argument_value_name"]] = normalized_existing

        merged: list[dict] = []

        for generated_item in generated_arguments:
            normalized_generated = self._normalize_payload_argument_item(generated_item)
            if normalized_generated is None:
                continue

            value_name = normalized_generated["argument_value_name"]
            existing_item = existing_by_name.get(value_name)

            if existing_item is not None:
                normalized_generated["task_argument_mapping"] = copy.deepcopy(
                    existing_item.get(
                        "task_argument_mapping",
                        normalized_generated["task_argument_mapping"],
                    )
                )
                normalized_generated["argument_hidden"] = bool(
                    existing_item.get(
                        "argument_hidden",
                        normalized_generated["argument_hidden"],
                    )
                )
                normalized_generated["argument_fallback"] = str(
                    existing_item.get(
                        "argument_fallback",
                        normalized_generated.get("argument_fallback", ""),
                    )
                    or ""
                )

            merged.append(normalized_generated)

        return merged

    def _get_payload_mapping_arguments(self, payload_argument_entry: dict) -> list[dict]:
        if not isinstance(payload_argument_entry, dict):
            return []

        mapping = payload_argument_entry.get("task_argument_mapping", {})
        if not isinstance(mapping, dict):
            return []

        if str(mapping.get("source_type", "")).strip() != "payload":
            return []

        raw_arguments = mapping.get("arguments", [])
        if not isinstance(raw_arguments, list):
            return []

        return raw_arguments

    def _set_payload_mapping_arguments(
        self,
        payload_argument_entry: dict,
        payload_arguments: list[dict],
    ) -> None:
        if not isinstance(payload_argument_entry, dict):
            raise ValueError("payload_argument_entry must be a dict.")

        payload_argument_entry["task_argument_mapping"] = {
            "source_type": "payload",
            "arguments": copy.deepcopy(payload_arguments),
        }
        payload_argument_entry["argument_fallback"] = ""

    def _merge_friendship_generated_returns(
        self,
        package_entry: dict,
        generated_returns: list[dict],
    ) -> list[dict]:
        existing_returns = package_entry.get("returns", [])
        if not isinstance(existing_returns, list):
            existing_returns = []

        existing_by_name: dict[str, dict] = {}

        for existing_return in existing_returns:
            if not isinstance(existing_return, dict):
                continue

            return_value_name = str(existing_return.get("return_value_name", "")).strip()
            if not return_value_name:
                continue

            existing_by_name[return_value_name] = existing_return

        merged_returns: list[dict] = []

        for generated_return in generated_returns:
            if not isinstance(generated_return, dict):
                continue

            return_value_name = str(generated_return.get("return_value_name", "")).strip()
            if not return_value_name:
                continue

            existing_return = existing_by_name.get(return_value_name, {})

            merged_returns.append(
                {
                    "return_value_name": return_value_name,
                    "return_description": str(
                        generated_return.get(
                            "return_description",
                            existing_return.get("return_description", ""),
                        )
                        or ""
                    ),
                    "visible": bool(existing_return.get("visible", generated_return.get("visible", True))),
                    "friendship": bool(existing_return.get("friendship", generated_return.get("friendship", False))),
                }
            )

        return merged_returns

    def _sync_special_package_generated_fields(
        self,
        tab_info: dict | None,
        package_entry: dict,
        package_index: int = 0,
        mark_dirty_on_change: bool = True,
    ) -> bool:
        if not isinstance(package_entry, dict):
            return False

        package_name = str(package_entry.get("name", "")).strip().lower()
        config = self._get_special_package_source_config(package_name)

        if not config:
            return False

        supports_payload_import = bool(config.get("supports_payload_import", False))
        supports_generated_returns = bool(config.get("supports_generated_returns", False))
        payload_argument_name = str(config.get("payload_argument_name", "")).strip()

        if not supports_payload_import or not payload_argument_name:
            return False

        source_agent, source_task = self._get_special_package_source_from_arguments(
            package_entry=package_entry,
            package_name=package_name,
        )

        if not source_agent or not source_task:
            return False

        source_task_payload = self._load_special_source_task_payload(source_agent, source_task)
        if not isinstance(source_task_payload, dict):
            return False

        before_package = copy.deepcopy(package_entry)

        generated_payload_arguments = self._extract_external_arguments_from_task_payload(source_task_payload)

        payload_argument_entry = self._upsert_package_argument_entry(
            package_entry=package_entry,
            argument_value_name=payload_argument_name,
            argument_question="Runtime Payload",
            argument_hidden=True,
        )

        existing_payload_arguments = self._get_payload_mapping_arguments(payload_argument_entry)
        merged_payload_arguments = self._merge_payload_arguments(
            existing_arguments=existing_payload_arguments,
            generated_arguments=generated_payload_arguments,
        )

        self._set_payload_mapping_arguments(
            payload_argument_entry=payload_argument_entry,
            payload_arguments=merged_payload_arguments,
        )

        if supports_generated_returns and package_name == self.FRIENDSHIP_PACKAGE_NAME:
            generated_returns = self._extract_friendship_returns_from_task_data(source_task_payload)
            package_entry["returns"] = self._merge_friendship_generated_returns(
                package_entry=package_entry,
                generated_returns=generated_returns,
            )

        changed = before_package != package_entry

        if changed and mark_dirty_on_change and isinstance(tab_info, dict):
            self._mark_tab_dirty(tab_info)

        return changed

    def _sync_friendship_package_generated_fields(
        self,
        tab_info: dict | None,
        package_entry: dict,
        package_index: int = 0,
        mark_dirty_on_change: bool = True,
    ) -> bool:
        return self._sync_special_package_generated_fields(
            tab_info=tab_info,
            package_entry=package_entry,
            package_index=package_index,
            mark_dirty_on_change=mark_dirty_on_change,
        )
from __future__ import annotations

import copy


class PackageSpecialSourcesMixin:
    """
    Save-time Friendship trigger stamping.

    Generated payload behavior now happens in the UI package instance:
        - selected source agent/task are normal package arguments
        - runtime_payload is a payload mapping with nested normal argument mappings
        - Friendship borrowed returns are printed into package["returns"]

    This mixin no longer injects source arguments or builds runtime payloads from
    a task-level friendship/package_sources side channel.
    """

    FRIENDSHIP_PACKAGE_NAME = "friendship"
    FRIENDSHIP_AGENT_ARGUMENT_NAME = "friendship_agent_name"
    FRIENDSHIP_TASK_ARGUMENT_NAME = "friendship_task_name"

    def _get_argument_manual_value_from_package(
        self,
        package_entry: dict,
        argument_value_name: str,
    ) -> str:
        clean_argument_value_name = str(argument_value_name or "").strip()

        if not isinstance(package_entry, dict) or not clean_argument_value_name:
            return ""

        arguments = package_entry.get("arguments", [])
        if not isinstance(arguments, list):
            return ""

        for argument_entry in arguments:
            if not isinstance(argument_entry, dict):
                continue

            current_value_name = str(argument_entry.get("argument_value_name", "")).strip()
            if not current_value_name:
                current_value_name = str(argument_entry.get("argument_question", "")).strip()

            if current_value_name != clean_argument_value_name:
                continue

            mapping = argument_entry.get("task_argument_mapping", {})
            if not isinstance(mapping, dict):
                return ""

            if str(mapping.get("source_type", "")).strip() != "manual":
                return ""

            return str(mapping.get("manual_value", "")).strip()

        return ""

    def _parse_borrower_friendship_trigger_block(self, trigger_text: str) -> list[dict]:
        raw_text = str(trigger_text or "")
        start_marker = "# === AUTO FRIENDSHIP BORROWS FROM START ==="
        end_marker = "# === AUTO FRIENDSHIP BORROWS FROM END ==="

        if start_marker not in raw_text or end_marker not in raw_text:
            return []

        try:
            _, remainder = raw_text.split(start_marker, 1)
            block_text, _ = remainder.split(end_marker, 1)
        except ValueError:
            return []

        parsed_items: list[dict] = []

        for raw_line in block_text.splitlines():
            line = raw_line.strip()
            if not line.startswith("friendship_borrows_from:"):
                continue

            payload = line.split(":", 1)[1].strip()
            pieces = [piece.strip() for piece in payload.split("|")]

            item: dict[str, str] = {}

            for piece in pieces:
                if "=" not in piece:
                    continue

                key, value = piece.split("=", 1)
                item[key.strip()] = value.strip()

            source_agent = str(item.get("source_agent", "")).strip()
            source_task = str(item.get("source_task", "")).strip()
            local_task = str(item.get("local_task", "")).strip()

            if source_agent and source_task:
                parsed_items.append(
                    {
                        "source_agent": source_agent,
                        "source_task": source_task,
                        "local_task": local_task,
                    }
                )

        return parsed_items

    def _build_friendship_borrower_trigger_block(self, trigger_items: list[dict]) -> str:
        if not trigger_items:
            return ""

        lines = [
            "# === AUTO FRIENDSHIP BORROWS FROM START ===",
        ]

        for item in trigger_items:
            source_agent = str(item.get("source_agent", "")).strip()
            source_task = str(item.get("source_task", "")).strip()
            local_task = str(item.get("local_task", "")).strip()

            if not source_agent or not source_task:
                continue

            if local_task:
                lines.append(
                    f"friendship_borrows_from: source_agent={source_agent} | source_task={source_task} | local_task={local_task}"
                )
            else:
                lines.append(
                    f"friendship_borrows_from: source_agent={source_agent} | source_task={source_task}"
                )

        lines.append("# === AUTO FRIENDSHIP BORROWS FROM END ===")
        return "\n".join(lines)

    def _merge_manual_and_auto_triggers(
        self,
        existing_text: str,
        auto_trigger_items: list[dict],
    ) -> str:
        raw_text = str(existing_text or "").strip()

        old_markers = [
            ("# === AUTO FRIENDSHIP TRIGGERS START ===", "# === AUTO FRIENDSHIP TRIGGERS END ==="),
            ("# === AUTO FRIENDSHIP BORROWS FROM START ===", "# === AUTO FRIENDSHIP BORROWS FROM END ==="),
        ]

        manual_text = raw_text

        for start_marker, end_marker in old_markers:
            if start_marker in manual_text and end_marker in manual_text:
                before, remainder = manual_text.split(start_marker, 1)
                _, after = remainder.split(end_marker, 1)
                manual_parts = [before.strip(), after.strip()]
                manual_text = "\n\n".join(part for part in manual_parts if part)

        auto_block = self._build_friendship_borrower_trigger_block(auto_trigger_items)

        parts = []

        if manual_text:
            parts.append(manual_text)

        if auto_block:
            parts.append(auto_block)

        return "\n\n".join(parts).rstrip()

    def _build_friendship_borrowed_by_block(self, borrowed_by_items: list[dict]) -> str:
        if not borrowed_by_items:
            return ""

        lines = [
            "# === AUTO FRIENDSHIP BORROWED BY START ===",
        ]

        for item in borrowed_by_items:
            borrower_agent = str(item.get("borrower_agent", "")).strip()
            borrower_task = str(item.get("borrower_task", "")).strip()

            if not borrower_agent or not borrower_task:
                continue

            lines.append(
                f"friendship_borrowed_by: borrower_agent={borrower_agent} | borrower_task={borrower_task}"
            )

        lines.append("# === AUTO FRIENDSHIP BORROWED BY END ===")
        return "\n".join(lines)

    def _replace_friendship_borrowed_by_block(
        self,
        existing_text: str,
        borrowed_by_items: list[dict],
    ) -> str:
        raw_text = str(existing_text or "").strip()

        start_marker = "# === AUTO FRIENDSHIP BORROWED BY START ==="
        end_marker = "# === AUTO FRIENDSHIP BORROWED BY END ==="

        manual_text = raw_text

        if start_marker in manual_text and end_marker in manual_text:
            before, remainder = manual_text.split(start_marker, 1)
            _, after = remainder.split(end_marker, 1)
            manual_parts = [before.strip(), after.strip()]
            manual_text = "\n\n".join(part for part in manual_parts if part)

        auto_block = self._build_friendship_borrowed_by_block(borrowed_by_items)

        parts = []

        if manual_text:
            parts.append(manual_text)

        if auto_block:
            parts.append(auto_block)

        return "\n\n".join(parts).rstrip()

    def _parse_friendship_borrowed_by_block(self, trigger_text: str) -> list[dict]:
        raw_text = str(trigger_text or "")
        start_marker = "# === AUTO FRIENDSHIP BORROWED BY START ==="
        end_marker = "# === AUTO FRIENDSHIP BORROWED BY END ==="

        if start_marker not in raw_text or end_marker not in raw_text:
            return []

        try:
            _, remainder = raw_text.split(start_marker, 1)
            block_text, _ = remainder.split(end_marker, 1)
        except ValueError:
            return []

        parsed_items: list[dict] = []

        for raw_line in block_text.splitlines():
            line = raw_line.strip()
            if not line.startswith("friendship_borrowed_by:"):
                continue

            payload = line.split(":", 1)[1].strip()
            pieces = [piece.strip() for piece in payload.split("|")]

            item: dict[str, str] = {}

            for piece in pieces:
                if "=" not in piece:
                    continue

                key, value = piece.split("=", 1)
                item[key.strip()] = value.strip()

            borrower_agent = str(item.get("borrower_agent", "")).strip()
            borrower_task = str(item.get("borrower_task", "")).strip()

            if borrower_agent and borrower_task:
                parsed_items.append(
                    {
                        "borrower_agent": borrower_agent,
                        "borrower_task": borrower_task,
                    }
                )

        return parsed_items

    def _find_task_in_agent_payload(
        self,
        agent_payload: dict,
        task_name: str,
    ) -> dict | None:
        clean_task_name = str(task_name or "").strip()

        if not isinstance(agent_payload, dict) or not clean_task_name:
            return None

        groups = agent_payload.get("groups", [])
        if not isinstance(groups, list):
            return None

        for group in groups:
            if not isinstance(group, dict):
                continue

            tasks = group.get("tasks", [])
            if not isinstance(tasks, list):
                continue

            for task_entry in tasks:
                if not isinstance(task_entry, dict):
                    continue

                current_name = str(task_entry.get("name", "")).strip()
                if current_name == clean_task_name:
                    return task_entry

        return None

    def _update_reverse_friendship_stamps(
        self,
        borrower_agent_name: str,
        borrower_task_name: str,
        old_sources: list[dict],
        new_sources: list[dict],
    ) -> None:
        borrower_agent_name = str(borrower_agent_name or "").strip()
        borrower_task_name = str(borrower_task_name or "").strip()

        if not borrower_agent_name or not borrower_task_name:
            return

        old_source_keys = {
            (
                str(item.get("source_agent", "")).strip(),
                str(item.get("source_task", "")).strip(),
            )
            for item in old_sources
            if str(item.get("source_agent", "")).strip()
            and str(item.get("source_task", "")).strip()
        }

        new_source_keys = {
            (
                str(item.get("source_agent", "")).strip(),
                str(item.get("source_task", "")).strip(),
            )
            for item in new_sources
            if str(item.get("source_agent", "")).strip()
            and str(item.get("source_task", "")).strip()
        }

        affected_source_keys = old_source_keys | new_source_keys

        for source_agent, source_task in affected_source_keys:
            try:
                source_agent_payload = self.assembly_manager.load_agent_data(source_agent)
            except Exception:
                continue

            source_task_entry = self._find_task_in_agent_payload(
                agent_payload=source_agent_payload,
                task_name=source_task,
            )

            if source_task_entry is None:
                continue

            existing_triggers = str(source_task_entry.get("Triggers", ""))
            borrowed_by_items = self._parse_friendship_borrowed_by_block(existing_triggers)

            borrowed_by_items = [
                item
                for item in borrowed_by_items
                if not (
                    str(item.get("borrower_agent", "")).strip() == borrower_agent_name
                    and str(item.get("borrower_task", "")).strip() == borrower_task_name
                )
            ]

            if (source_agent, source_task) in new_source_keys:
                borrowed_by_items.append(
                    {
                        "borrower_agent": borrower_agent_name,
                        "borrower_task": borrower_task_name,
                    }
                )

            deduped_items: list[dict] = []
            seen: set[tuple[str, str]] = set()

            for item in borrowed_by_items:
                key = (
                    str(item.get("borrower_agent", "")).strip(),
                    str(item.get("borrower_task", "")).strip(),
                )

                if not key[0] or not key[1] or key in seen:
                    continue

                seen.add(key)
                deduped_items.append(
                    {
                        "borrower_agent": key[0],
                        "borrower_task": key[1],
                    }
                )

            updated_triggers = self._replace_friendship_borrowed_by_block(
                existing_text=existing_triggers,
                borrowed_by_items=deduped_items,
            )

            if updated_triggers == existing_triggers.strip():
                continue

            source_task_entry["Triggers"] = updated_triggers

            try:
                self.assembly_manager.save_agent(
                    agent_name=source_agent,
                    agent_payload=source_agent_payload,
                )
            except Exception:
                continue

    def _get_friendship_source_from_package_for_save(self, package_entry: dict) -> tuple[str, str]:
        source_agent = self._get_argument_manual_value_from_package(
            package_entry,
            self.FRIENDSHIP_AGENT_ARGUMENT_NAME,
        )
        source_task = self._get_argument_manual_value_from_package(
            package_entry,
            self.FRIENDSHIP_TASK_ARGUMENT_NAME,
        )
        return source_agent, source_task

    def _hydrate_special_packages_for_task(
        self,
        task_name: str,
        packages: list[dict],
        friendship_state: object,
        existing_triggers_text: str,
    ) -> tuple[list[dict], str, list[dict], list[dict]]:
        """
        Preserve the old save-controller call signature, but ignore friendship_state.

        Generated arguments/returns are already stored directly on package
        instances by UI refresh/sync. Save-time work only updates Friendship
        trigger stamps and reverse borrowed-by stamps.
        """
        clean_task_name = str(task_name or "").strip()

        if not clean_task_name:
            raise ValueError("Task name is required before hydrating special packages.")

        if packages in (None, ""):
            packages = []

        if not isinstance(packages, list):
            raise ValueError("packages must be a list.")

        hydrated_packages = copy.deepcopy(packages)
        previous_auto_trigger_items = self._parse_borrower_friendship_trigger_block(
            existing_triggers_text
        )

        auto_trigger_items: list[dict] = []

        for package_index, package_entry in enumerate(hydrated_packages):
            if not isinstance(package_entry, dict):
                raise ValueError(f"Package entry {package_index + 1} must be a dict.")

            package_name = str(package_entry.get("name", "")).strip().lower()

            if package_name != self.FRIENDSHIP_PACKAGE_NAME:
                continue

            source_agent, source_task = self._get_friendship_source_from_package_for_save(package_entry)

            if not source_agent or not source_task:
                continue

            auto_trigger_items.append(
                {
                    "source_agent": source_agent,
                    "source_task": source_task,
                    "local_task": clean_task_name,
                }
            )

        updated_triggers = self._merge_manual_and_auto_triggers(
            existing_text=existing_triggers_text,
            auto_trigger_items=auto_trigger_items,
        )

        return hydrated_packages, updated_triggers, previous_auto_trigger_items, auto_trigger_items
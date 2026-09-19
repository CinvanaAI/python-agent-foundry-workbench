from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re
import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import Any

from Environment.agent_foundry.foundry_workspace_verification import (
    AgentFoundryWorkspaceVerificationMixin,
)
from Environment.agent_foundry.foundry_workspace_index import (
    AgentFoundryWorkspaceIndexMixin,
    create_foundry_draft,
    load_or_create_package_index,
    save_package_index,
    validate_package_index,
)


AGENT_FOUNDRY_RESYNC_MAX_PASSES = 3
AGENT_FOUNDRY_MUTATION_RELOAD_MAX_PASSES = 3


class AgentFoundryWorkspaceMixin(
    AgentFoundryWorkspaceVerificationMixin,
    AgentFoundryWorkspaceIndexMixin,
):
    def _agent_foundry_msg(self, kind: str, title: str, body: object) -> None:
        getattr(messagebox, kind)(title, str(body), parent=self.agent_foundry_tab)

    def _agent_foundry_error(self, title: str, exc: Exception) -> None:
        self._agent_foundry_msg("showerror", title, exc)

    def _refresh_agent_foundry_workspaces_or_error(self) -> None:
        try:
            self._refresh_agent_foundry_workspaces()
        except Exception as exc:
            self._agent_foundry_error("Agent Foundry Refresh Failed", exc)

    def _safe_show_agent_foundry_entry_screen(self) -> None:
        try:
            self._clear_agent_foundry_loaded_workspace_state()
            self._show_agent_foundry_entry_screen()
        except Exception:
            pass

    def _now_agent_foundry_text(self) -> str:
        return datetime.now().isoformat(timespec="seconds")

    def _resolve_agent_foundry_agent_name_for_save(
        self,
        *,
        foundry_name: str,
        record: dict[str, Any],
        frontend_object: dict[str, Any],
    ) -> str:
        return (
            self._get_agent_foundry_agent_name_from_frontend_object(
                frontend_object=frontend_object,
            )
            or str(record.get("agent_name", "") or "").strip()
            or foundry_name
        )

    def _show_agent_foundry_entry_screen(self) -> None:
        self._clear_agent_foundry_root_container()
        self._clear_agent_foundry_loaded_workspace_handles()
        self._build_agent_foundry_entry_screen()
        self._refresh_agent_foundry_workspaces_or_error()

    def _handle_agent_foundry_entry_create(self) -> None:
        self._create_blank_agent_foundry_workspace()

    def _handle_agent_foundry_entry_load(self, event: tk.Event | None = None) -> None:
        requested_name = self._resolve_agent_foundry_entry_workspace_name()
        if not requested_name:
            self._agent_foundry_msg(
                "showinfo",
                "Agent Foundry Load",
                "Choose an Agent Foundry workspace to load.",
            )
            return

        picker_var = getattr(self, "agent_foundry_workspace_var", None)
        if picker_var is not None:
            picker_var.set(requested_name)

        self._load_agent_foundry_blueprint_by_name(requested_name)

    def _handle_agent_foundry_entry_picker_selected(
        self,
        event: tk.Event | None = None,
    ) -> None:
        return None

    def _handle_agent_foundry_entry_resync(self) -> None:
        self._resync_all_agent_foundry_drafts()
        self._refresh_agent_foundry_workspaces_or_error()

    def _resolve_agent_foundry_entry_workspace_name(self) -> str:
        picker_var = getattr(self, "agent_foundry_workspace_var", None)
        requested_name = ""
        if picker_var is not None:
            requested_name = str(picker_var.get() or "").strip()

        if not requested_name:
            return ""

        workspace_map = getattr(self, "agent_foundry_workspace_map", {})
        if isinstance(workspace_map, dict) and requested_name in workspace_map:
            return requested_name

        all_names = getattr(self, "agent_foundry_all_workspace_names", [])
        if not isinstance(all_names, list):
            all_names = []

        exact_matches = [
            name
            for name in all_names
            if str(name or "").strip().lower() == requested_name.lower()
        ]
        if len(exact_matches) == 1:
            return str(exact_matches[0])

        partial_matches = [
            name
            for name in all_names
            if requested_name.lower() in str(name or "").lower()
        ]
        if len(partial_matches) == 1:
            return str(partial_matches[0])

        return ""

    def _filter_agent_foundry_workspace_picker(
        self,
        event: tk.Event | None = None,
    ) -> None:
        if self.agent_foundry_suppress_picker_events:
            return

        picker = getattr(self, "agent_foundry_workspace_picker", None)
        picker_var = getattr(self, "agent_foundry_workspace_var", None)
        if picker is None or picker_var is None:
            return

        ignored_keys = {
            "Up",
            "Down",
            "Left",
            "Right",
            "Escape",
            "Return",
            "Tab",
            "Shift_L",
            "Shift_R",
            "Control_L",
            "Control_R",
            "Alt_L",
            "Alt_R",
        }

        if event is not None and str(getattr(event, "keysym", "")) in ignored_keys:
            return

        typed_text = picker_var.get().strip().lower()

        if not typed_text:
            filtered_names = list(self.agent_foundry_all_workspace_names)
        else:
            filtered_names = [
                name
                for name in self.agent_foundry_all_workspace_names
                if typed_text in name.lower()
            ]

        picker.configure(values=filtered_names)

        try:
            picker.event_generate("<Down>")
        except Exception:
            pass

    def _prompt_agent_foundry_new_agent_name(self) -> str:
        try:
            requested_name = simpledialog.askstring(
                "Create Agent",
                "Agent name:",
                parent=self.agent_foundry_tab,
            )
        except Exception:
            requested_name = ""

        return str(requested_name or "").strip()

    def _prompt_agent_foundry_new_package_name(self) -> str:
        try:
            requested_name = simpledialog.askstring(
                "Create Package",
                "Package name:",
                parent=self.agent_foundry_tab,
            )
        except Exception:
            requested_name = ""

        return str(requested_name or "").strip()

    def _handle_agent_foundry_create_package_blueprint(self) -> None:
        requested_package_name = self._prompt_agent_foundry_new_package_name()
        if not requested_package_name:
            return

        try:
            result = self._create_package_foundry_blueprint_file(
                package_name=requested_package_name,
            )

            message = (
                "Created Package Foundry blueprint:\n\n"
                f"Package name: {result['package_name']}\n"
                f"Package index id: {result['package_key']}\n"
                f"Numeric index: {int(result['package_id']):06d}\n\n"
                f"Blueprint:\n{result['blueprint_file']}\n\n"
                f"Package index:\n{result['package_index_file']}"
            )

            self._agent_foundry_msg(
                "showinfo",
                "Package Foundry Blueprint Created",
                message,
            )

        except Exception as exc:
            self._agent_foundry_error("Package Foundry Create Failed", exc)

    def _create_package_foundry_blueprint_file(
        self,
        *,
        package_name: str,
        blueprint_text: str = "",
    ) -> dict[str, Any]:
        """Create one Package Foundry blueprint file and package index entry."""
        requested_package_name = str(package_name or "").strip()
        if not requested_package_name:
            raise ValueError("Package name is required.")

        handoff = self._get_agent_foundry_collection_handoff()

        package_index_file = Path(
            handoff.get_agent_foundry_package_index_file()
        ).expanduser().resolve()

        packages_dir = Path(
            handoff.get_agent_foundry_packages_directory()
        ).expanduser().resolve()

        packages_dir.mkdir(parents=True, exist_ok=True)
        package_index_file.parent.mkdir(parents=True, exist_ok=True)

        clean_package_name = self._normalize_agent_foundry_package_display_name(
            requested_package_name
        )
        if not clean_package_name:
            raise ValueError(
                f"Package name normalized blank: {requested_package_name!r}"
            )

        package_file_stem = self._sanitize_agent_foundry_package_file_stem(
            clean_package_name
        )
        if not package_file_stem:
            raise ValueError(
                f"Package file name sanitized blank: {requested_package_name!r}"
            )

        package_index = self._load_or_create_agent_foundry_package_index(
            package_index_file,
        )

        existing_name_match = self._find_agent_foundry_package_index_entry_by_name(
            package_index=package_index,
            package_name=clean_package_name,
        )
        if existing_name_match is not None:
            raise FileExistsError(
                f"Package name is already registered in the package index: "
                f"{clean_package_name}"
            )

        package_id = self._reserve_next_agent_foundry_package_id(package_index)
        package_key = f"package_{package_id:06d}"

        self._assert_agent_foundry_package_id_is_not_registered(
            package_index=package_index,
            package_id=package_id,
        )

        blueprint_file = (
            packages_dir / f"{package_file_stem}.blueprint.txt"
        ).expanduser().resolve()

        if blueprint_file.exists():
            raise FileExistsError(
                f"Package Foundry blueprint already exists: {blueprint_file}"
            )

        now_text = self._now_agent_foundry_text()
        incoming_blueprint_text = str(blueprint_text or "").strip()

        if incoming_blueprint_text:
            package_blueprint_text = self._prepare_created_package_blueprint_text(
                blueprint_text=incoming_blueprint_text,
                package_name=clean_package_name,
                package_index_key=package_key,
            )
        else:
            package_blueprint_text = self._build_created_package_blueprint_seed(
                package_name=clean_package_name,
                package_index_key=package_key,
            )

        blueprint_file.write_text(
            self._normalize_agent_foundry_text_file_content(package_blueprint_text),
            encoding="utf-8",
        )

        self._register_agent_foundry_package_id(
            package_index=package_index,
            package_id=package_id,
            package_key=package_key,
            package_name=clean_package_name,
            requested_package_name=requested_package_name,
            blueprint_file=blueprint_file,
            created_at=now_text,
        )
        self._save_agent_foundry_package_index(
            package_index_file,
            package_index,
        )

        return {
            "status": "created",
            "package_id": package_id,
            "package_key": package_key,
            "package_index_key": package_key,
            "package_name": clean_package_name,
            "requested_package_name": requested_package_name,
            "package_file_stem": package_file_stem,
            "blueprint_file": str(blueprint_file.resolve()),
            "package_index_file": str(package_index_file.resolve()),
            "packages_dir": str(packages_dir.resolve()),
            "package_index": package_index,
        }

    def _normalize_agent_foundry_package_display_name(self, value: object) -> str:
        clean_value = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        clean_value = " ".join(clean_value.split())
        return clean_value

    def _sanitize_agent_foundry_package_file_stem(self, value: object) -> str:
        clean_value = self._normalize_agent_foundry_package_display_name(value)
        if not clean_value:
            return ""

        clean_value = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", clean_value)
        clean_value = re.sub(r"\s+", "_", clean_value)
        clean_value = re.sub(r"_+", "_", clean_value)
        clean_value = clean_value.strip(" ._")

        reserved_names = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        }

        if clean_value.upper() in reserved_names:
            clean_value = f"{clean_value}_package"

        return clean_value

    def _prepare_created_package_blueprint_text(
        self,
        *,
        blueprint_text: str,
        package_name: str,
        package_index_key: str,
    ) -> str:
        prepared_text = self._ensure_package_id_block_in_blueprint(
            blueprint_text=blueprint_text,
            package_name=package_name,
        )

        prepared_text = self._ensure_package_index_id_block_in_blueprint(
            blueprint_text=prepared_text,
            package_index_key=package_index_key,
            package_name=package_name,
        )

        return self._normalize_agent_foundry_text_file_content(prepared_text)

    def _build_created_package_blueprint_seed(
        self,
        *,
        package_name: str,
        package_index_key: str,
    ) -> str:
        clean_package_name = self._normalize_agent_foundry_package_display_name(
            package_name
        )
        if not clean_package_name:
            clean_package_name = "UnnamedPackage"

        clean_package_index_key = str(package_index_key or "").strip()
        if not clean_package_index_key:
            clean_package_index_key = "package_000000"

        parts = [
            (
                f"{clean_package_name} Package ID:\n"
                f"- {clean_package_name}\n"
                f"End {clean_package_name} Package ID"
            ),
            (
                f"{clean_package_name} Package Index ID:\n"
                f"- {clean_package_index_key}\n"
                f"End {clean_package_name} Package Index ID"
            ),
            (
                f"{clean_package_name} Logic:\n"
                "(enter package logic here)\n"
                f"End {clean_package_name} Logic"
            ),
        ]

        return "\n\n".join(
            part.strip()
            for part in parts
            if str(part or "").strip()
        ).rstrip() + "\n"

    def _ensure_package_id_block_in_blueprint(
        self,
        *,
        blueprint_text: str,
        package_name: str,
    ) -> str:
        source_text = str(blueprint_text or "").rstrip()

        clean_package_name = self._normalize_agent_foundry_package_display_name(
            package_name
        )
        if not clean_package_name:
            clean_package_name = self._extract_package_name_from_blueprint_text(
                source_text,
            )

        if not clean_package_name:
            clean_package_name = "UnnamedPackage"

        block_heading = f"{clean_package_name} Package ID"
        block_text = (
            f"{block_heading}:\n"
            f"- {clean_package_name}\n"
            f"End {block_heading}"
        )

        if self._agent_foundry_fenced_block_exists(
            source_text=source_text,
            block_heading=block_heading,
        ):
            return self._normalize_agent_foundry_text_file_content(source_text)

        if source_text:
            return self._normalize_agent_foundry_text_file_content(
                block_text + "\n\n" + source_text
            )

        return self._normalize_agent_foundry_text_file_content(block_text)

    def _ensure_package_index_id_block_in_blueprint(
        self,
        *,
        blueprint_text: str,
        package_index_key: str,
        package_name: str = "",
    ) -> str:
        source_text = str(blueprint_text or "").rstrip()

        clean_package_index_key = str(package_index_key or "").strip()
        if not clean_package_index_key:
            return self._normalize_agent_foundry_text_file_content(source_text)

        clean_package_name = self._normalize_agent_foundry_package_display_name(
            package_name
        )
        if not clean_package_name:
            clean_package_name = self._extract_package_name_from_blueprint_text(
                source_text,
            )

        if not clean_package_name:
            clean_package_name = "UnnamedPackage"

        block_heading = f"{clean_package_name} Package Index ID"
        block_text = (
            f"{block_heading}:\n"
            f"- {clean_package_index_key}\n"
            f"End {block_heading}"
        )

        start_pattern = re.compile(
            rf"(?im)^\s*{re.escape(block_heading)}\s*:\s*$"
        )
        start_match = start_pattern.search(source_text)

        if start_match is None:
            if source_text:
                return self._normalize_agent_foundry_text_file_content(
                    source_text + "\n\n" + block_text
                )
            return self._normalize_agent_foundry_text_file_content(block_text)

        end_pattern = re.compile(
            rf"(?im)^\s*End\s+{re.escape(block_heading)}\s*$"
        )
        end_match = end_pattern.search(source_text, start_match.end())

        if end_match is None:
            if source_text:
                return self._normalize_agent_foundry_text_file_content(
                    source_text + "\n\n" + block_text
                )
            return self._normalize_agent_foundry_text_file_content(block_text)

        updated_text = (
            source_text[:start_match.start()].rstrip()
            + ("\n\n" if source_text[:start_match.start()].strip() else "")
            + block_text
            + ("\n\n" if source_text[end_match.end():].strip() else "")
            + source_text[end_match.end():].lstrip()
        )

        return self._normalize_agent_foundry_text_file_content(updated_text)

    def _agent_foundry_fenced_block_exists(
        self,
        *,
        source_text: str,
        block_heading: str,
    ) -> bool:
        clean_source_text = str(source_text or "")
        clean_block_heading = str(block_heading or "").strip()
        if not clean_source_text.strip() or not clean_block_heading:
            return False

        start_pattern = re.compile(
            rf"(?im)^\s*{re.escape(clean_block_heading)}\s*:\s*$"
        )
        start_match = start_pattern.search(clean_source_text)
        if start_match is None:
            return False

        end_pattern = re.compile(
            rf"(?im)^\s*End\s+{re.escape(clean_block_heading)}\s*$"
        )
        return end_pattern.search(clean_source_text, start_match.end()) is not None

    def _extract_package_name_from_blueprint_text(self, blueprint_text: str) -> str:
        source_text = str(blueprint_text or "")
        if not source_text.strip():
            return ""

        generic_start_pattern = re.compile(
            r"(?im)^\s*Package ID\s*:\s*$"
        )
        generic_start_match = generic_start_pattern.search(source_text)
        if generic_start_match is not None:
            generic_end_pattern = re.compile(
                r"(?im)^\s*End\s+Package ID\s*$"
            )
            generic_end_match = generic_end_pattern.search(
                source_text,
                generic_start_match.end(),
            )
            if generic_end_match is not None:
                inner_text = source_text[
                    generic_start_match.end():generic_end_match.start()
                ]
                for line in inner_text.splitlines():
                    clean_line = str(line or "").strip()
                    if not clean_line.startswith("-"):
                        continue

                    value = clean_line[1:].strip()
                    if value:
                        return value

        for start_match in re.finditer(
            r"(?im)^\s*(.+?)\s+Package ID\s*:\s*$",
            source_text,
        ):
            heading_owner = str(start_match.group(1) or "").strip()
            if not heading_owner:
                continue

            end_pattern = re.compile(
                rf"(?im)^\s*End\s+{re.escape(heading_owner)}\s+Package ID\s*$"
            )
            end_match = end_pattern.search(source_text, start_match.end())
            if end_match is None:
                continue

            inner_text = source_text[start_match.end():end_match.start()]
            for line in inner_text.splitlines():
                clean_line = str(line or "").strip()
                if not clean_line.startswith("-"):
                    continue

                value = line[1:].strip()
                if value:
                    return value

            return heading_owner

        return ""

    def _normalize_agent_foundry_text_file_content(self, value: object) -> str:
        text = str(value or "").rstrip()
        if text:
            return text + "\n"
        return ""

    def _load_or_create_agent_foundry_package_index(
        self,
        index_path: str | Path,
    ) -> dict[str, Any]:
        return load_or_create_package_index(index_path)

    def _validate_agent_foundry_package_index(
        self,
        package_index: dict[str, Any],
        index_path: Path | None = None,
    ) -> None:
        validate_package_index(package_index, index_path)

    def _save_agent_foundry_package_index(
        self,
        index_path: str | Path,
        package_index: dict[str, Any],
    ) -> Path:
        return save_package_index(index_path, package_index)

    def _reserve_next_agent_foundry_package_id(
        self,
        package_index: dict[str, Any],
    ) -> int:
        self._validate_agent_foundry_package_index(package_index)
        current_id = int(package_index.get("last_package_number", 0) or 0)
        next_id = current_id + 1
        package_index["last_package_number"] = next_id
        return next_id

    def _assert_agent_foundry_package_id_is_not_registered(
        self,
        *,
        package_index: dict[str, Any],
        package_id: int,
    ) -> None:
        self._validate_agent_foundry_package_index(package_index)

        for entry in package_index["packages"]:
            if not isinstance(entry, dict):
                continue

            if int(entry.get("package_id", -1)) == int(package_id):
                raise ValueError(f"Package id is already registered: {package_id}")

    def _find_agent_foundry_package_index_entry_by_name(
        self,
        *,
        package_index: dict[str, Any],
        package_name: str,
    ) -> dict[str, Any] | None:
        self._validate_agent_foundry_package_index(package_index)

        clean_package_name = str(package_name or "").strip().lower()
        if not clean_package_name:
            return None

        for entry in package_index["packages"]:
            if not isinstance(entry, dict):
                continue

            entry_name = str(entry.get("package_name", "") or "").strip().lower()
            if entry_name == clean_package_name:
                return entry

        return None

    def _register_agent_foundry_package_id(
        self,
        *,
        package_index: dict[str, Any],
        package_id: int,
        package_key: str,
        package_name: str,
        requested_package_name: str,
        blueprint_file: Path,
        created_at: str,
    ) -> dict[str, Any]:
        self._validate_agent_foundry_package_index(package_index)
        self._assert_agent_foundry_package_id_is_not_registered(
            package_index=package_index,
            package_id=package_id,
        )

        entry = {
            "package_id": int(package_id),
            "package_key": str(package_key or ""),
            "package_index_key": str(package_key or ""),
            "package_name": str(package_name or ""),
            "requested_package_name": str(requested_package_name or ""),
            "blueprint_file": str(Path(blueprint_file).expanduser().resolve()),
            "created_at": str(created_at or ""),
            "updated_at": str(created_at or ""),
            "last_updated_in_foundry": str(created_at or ""),
        }

        package_index["packages"].append(entry)
        package_index["last_package_number"] = max(
            int(package_index.get("last_package_number", 0) or 0),
            int(package_id),
        )
        return entry

    def _resync_all_agent_foundry_drafts(self) -> None:
        self.agent_foundry_resync_batch_active = True
        self.agent_foundry_resync_seed_changed = False

        try:
            self._refresh_agent_foundry_workspaces()

            pending_names = [
                str(name or "").strip()
                for name in list(getattr(self, "agent_foundry_all_workspace_names", []) or [])
                if str(name or "").strip()
            ]

            if not pending_names:
                self._agent_foundry_msg(
                    "showinfo",
                    "Agent Foundry Resync",
                    "No Agent Foundry drafts were found to resync.",
                )
                return

            failed_names: list[str] = []
            updated_names: set[str] = set()
            clean_names: set[str] = set()
            completed_passes = 0

            for pass_index in range(1, AGENT_FOUNDRY_RESYNC_MAX_PASSES + 1):
                if not pending_names:
                    break

                completed_passes = pass_index
                next_pending_names: list[str] = []

                for foundry_name in list(pending_names):
                    try:
                        self.agent_foundry_resync_seed_changed = False

                        self._load_agent_foundry_blueprint_by_name_or_raise(foundry_name)

                        loaded_name = str(
                            getattr(self, "agent_foundry_loaded_name", "") or ""
                        ).strip()
                        if loaded_name != foundry_name:
                            raise RuntimeError(
                                f"Load did not activate the requested draft: {foundry_name}"
                            )

                        seed_changed = bool(
                            getattr(self, "agent_foundry_resync_seed_changed", False)
                        )

                        self._commit_agent_foundry_exit_to_entry_or_raise()

                        if seed_changed:
                            updated_names.add(foundry_name)
                            next_pending_names.append(foundry_name)
                        else:
                            clean_names.add(foundry_name)

                    except Exception:
                        failed_names.append(foundry_name)
                        self._safe_show_agent_foundry_entry_screen()

                failed_lookup = {str(name or "").strip() for name in failed_names}
                pending_names = [
                    name
                    for name in next_pending_names
                    if str(name or "").strip()
                    and str(name or "").strip() not in failed_lookup
                ]

            try:
                self._refresh_agent_foundry_workspaces()
            except Exception:
                pass

            unresolved_names = [
                name
                for name in pending_names
                if str(name or "").strip()
            ]

            if failed_names or unresolved_names:
                parts = [
                    "Agent Foundry Resync finished with issues.",
                    "",
                    f"Passes run: {completed_passes}",
                    f"Updated during resync: {len(updated_names)}",
                    f"Clean/settled: {len(clean_names)}",
                    f"Failed: {len(failed_names)}",
                    f"Still reporting seed changes after hard stop: {len(unresolved_names)}",
                ]

                if failed_names:
                    parts.extend(
                        [
                            "",
                            "Failed drafts:",
                            *[f"- {name}" for name in failed_names],
                        ]
                    )

                if unresolved_names:
                    parts.extend(
                        [
                            "",
                            "Still reporting seed changes:",
                            *[f"- {name}" for name in unresolved_names],
                        ]
                    )

                self._agent_foundry_msg(
                    "showwarning",
                    "Agent Foundry Resync Complete",
                    "\n".join(parts),
                )
                return

            self._agent_foundry_msg(
                "showinfo",
                "Agent Foundry Resync Complete",
                "Agent Foundry Resync complete.\n\n"
                f"Passes run: {completed_passes}\n"
                f"Updated during resync: {len(updated_names)}\n"
                f"Clean/settled: {len(clean_names)}",
            )

        except Exception as exc:
            self._agent_foundry_error("Agent Foundry Resync Failed", exc)
        finally:
            self.agent_foundry_resync_batch_active = False
            self.agent_foundry_resync_seed_changed = False

    def _handle_agent_foundry_back_to_entry(self) -> None:
        self._commit_agent_foundry_exit_to_entry()

    def _commit_agent_foundry_exit_to_entry(self) -> None:
        try:
            self._commit_agent_foundry_exit_to_entry_or_raise()
        except Exception as exc:
            self._agent_foundry_error("Agent Foundry Exit Save Failed", exc)

    def _commit_agent_foundry_exit_to_entry_or_raise(self) -> None:
        self._save_agent_foundry_current_frontend_object_to_files()
        self._clear_agent_foundry_loaded_workspace_state()
        self._show_agent_foundry_entry_screen()

    def _clear_agent_foundry_loaded_workspace_state(self) -> None:
        self.agent_foundry_loaded_name = ""
        self.agent_foundry_loaded_blueprint_text = ""
        self.agent_foundry_loaded_blueprint_only_text = ""
        self.agent_foundry_loaded_leftovers_text = ""
        self.agent_foundry_loaded_viewer_text = ""
        self.agent_foundry_blueprint_path = None
        self.agent_foundry_frontend_object = {}
        self.agent_foundry_parser_blueprint_text = ""
        self.agent_foundry_parser_leftovers_text = ""
        self.agent_foundry_source_verification_passed = True
        self.agent_foundry_source_verification_report = {}
        self.agent_foundry_dirty = False

        edited_scopes = getattr(self, "agent_foundry_edited_scopes", None)
        if isinstance(edited_scopes, set):
            edited_scopes.clear()

    def _create_blank_agent_foundry_workspace(self) -> None:
        requested_agent_name = self._prompt_agent_foundry_new_agent_name()
        if not requested_agent_name:
            return

        try:
            result = create_foundry_draft(
                handoff=self._get_agent_foundry_collection_handoff(),
                agent_name=requested_agent_name,
            )

            foundry_name = str(result["foundry_name"])
            workspace_dir = Path(result["workspace_dir"]).expanduser().resolve()
            blueprint_file = Path(result["blueprint_file"]).expanduser().resolve()
            packages_dir = Path(
                result.get("agent_foundry_packages_dir")
                or result.get("packages_dir")
                or ""
            ).expanduser().resolve()
            metadata_file = Path(result["metadata_file"]).expanduser().resolve()
            leftovers_file = self._coerce_optional_path(result.get("leftovers_file"))
            runtime_file = self._coerce_optional_path(result.get("runtime_file"))
            agent_name = str(result.get("agent_name", "") or "")
            agent_key = str(result.get("agent_key", "") or "")
            agent_id = int(result["agent_id"])

            self._refresh_agent_foundry_workspaces()

            picker_var = getattr(self, "agent_foundry_workspace_var", None)
            if picker_var is not None:
                picker_var.set(foundry_name)

            self._load_agent_foundry_blueprint_by_name_or_raise(foundry_name)

            agent_label = agent_name if agent_name else foundry_name

            message = (
                "Created Agent Foundry draft:\n\n"
                f"Agent name: {agent_label}\n"
                f"Agent index id: {agent_key}\n"
                f"Numeric index: {agent_id:06d}\n"
                f"Draft key: {foundry_name}\n\n"
                f"Workspace:\n{workspace_dir}\n\n"
                f"Blueprint:\n{blueprint_file}\n\n"
                f"Packages folder:\n{packages_dir}\n\n"
                f"Metadata:\n{metadata_file}"
            )

            if leftovers_file is not None:
                message += f"\n\nLeftovers:\n{leftovers_file}"

            if runtime_file is not None:
                message += f"\n\nRuntime:\n{runtime_file}"

            self._agent_foundry_msg("showinfo", "Agent Foundry Draft Created", message)

        except Exception as exc:
            self._agent_foundry_error("Agent Foundry Create Failed", exc)

    def _load_agent_foundry_blueprint_by_name(self, foundry_name: str) -> None:
        try:
            self._load_agent_foundry_blueprint_by_name_or_raise(foundry_name)
        except Exception as exc:
            self._agent_foundry_error("Agent Foundry Load Failed", exc)

    def _load_agent_foundry_blueprint_by_name_or_raise(self, foundry_name: str) -> None:
        record = self.agent_foundry_record_map.get(foundry_name)
        if not isinstance(record, dict):
            raise ValueError(f"Agent Foundry workspace was not found: {foundry_name}")

        blueprint_path = self._get_blueprint_path_for_foundry(
            foundry_name=foundry_name,
            record=record,
        )

        blueprint_text = blueprint_path.read_text(encoding="utf-8")
        leftovers_text = self._load_leftovers_text_for_foundry_record(
            foundry_name=foundry_name,
            record=record,
        )
        viewer_content = self._load_agent_schema_viewer_text_for_foundry(
            foundry_name=foundry_name,
            record=record,
        )
        raw_source_text = self._combine_blueprint_and_leftovers_for_load(
            blueprint_text=blueprint_text,
            leftovers_text=leftovers_text,
        )

        self.agent_foundry_suppress_visibility_refresh = True
        try:
            self._activate_agent_foundry_loaded_workspace_shell()

            self.agent_foundry_blueprint_path = blueprint_path
            self.agent_foundry_loaded_name = foundry_name

            picker_var = getattr(self, "agent_foundry_workspace_var", None)
            if picker_var is not None:
                picker_var.set(foundry_name)

            self.agent_foundry_loaded_blueprint_only_text = blueprint_text
            self.agent_foundry_loaded_blueprint_text = raw_source_text
            self.agent_foundry_loaded_leftovers_text = leftovers_text
            self.agent_foundry_loaded_viewer_text = viewer_content

            self._load_agent_foundry_raw_source_into_frontend_object(
                raw_source_text=raw_source_text,
                viewer_content=viewer_content,
                original_blueprint_text=blueprint_text,
                original_leftovers_text=leftovers_text,
                foundry_name=foundry_name,
                record=record,
            )

            self.agent_foundry_last_saved_blueprint_text = self.agent_foundry_loaded_blueprint_only_text
            self.agent_foundry_last_saved_leftovers_text = self.agent_foundry_loaded_leftovers_text
            self.agent_foundry_last_saved_viewer_text = self.agent_foundry_loaded_viewer_text
        finally:
            self.agent_foundry_suppress_visibility_refresh = False

    def _load_agent_foundry_raw_source_into_frontend_object(
        self,
        *,
        raw_source_text: str,
        viewer_content: str = "",
        original_blueprint_text: str = "",
        original_leftovers_text: str = "",
        foundry_name: str = "",
        record: dict[str, Any] | None = None,
        mutation_reload_pass: int = 0,
    ) -> None:
        source_text = str(raw_source_text or "").rstrip()
        clean_viewer_content = str(viewer_content or "").rstrip()

        frontend_object, parser_leftovers_text = self._build_raw_foundry_frontend_object(
            source_text=source_text,
            viewer_content=clean_viewer_content,
        )

        self.agent_foundry_frontend_object = frontend_object
        parser_blueprint_text = self._compose_agent_foundry_blueprint_text_from_frontend_object(
            frontend_object=frontend_object,
        )
        self.agent_foundry_parser_blueprint_text = parser_blueprint_text
        self.agent_foundry_parser_leftovers_text = parser_leftovers_text

        self._verify_agent_foundry_parser_source_conservation_or_fail_load(
            foundry_name=foundry_name,
            record=record or {},
            original_blueprint_text=original_blueprint_text,
            original_leftovers_text=original_leftovers_text,
            parser_blueprint_text=parser_blueprint_text,
            parser_leftovers_text=parser_leftovers_text,
        )

        mutator_changed = self._run_agent_foundry_mutation_checkpoint_after_parser(
            frontend_object=frontend_object,
        )

        if mutator_changed:
            if mutation_reload_pass >= AGENT_FOUNDRY_MUTATION_RELOAD_MAX_PASSES:
                raise RuntimeError(
                    "Agent Foundry mutation checkpoint did not settle after "
                    f"{AGENT_FOUNDRY_MUTATION_RELOAD_MAX_PASSES} parser reload passes."
                )

            self._save_agent_foundry_current_frontend_object_to_files()

            saved_raw_source_text = str(
                getattr(self, "agent_foundry_loaded_blueprint_text", "") or ""
            ).rstrip()
            saved_blueprint_text = str(
                getattr(self, "agent_foundry_loaded_blueprint_only_text", "") or ""
            ).rstrip()
            saved_leftovers_text = str(
                getattr(self, "agent_foundry_loaded_leftovers_text", "") or ""
            ).rstrip()
            saved_viewer_text = str(
                getattr(self, "agent_foundry_loaded_viewer_text", "")
                or clean_viewer_content
                or ""
            ).rstrip()

            updated_record = self._get_current_agent_foundry_record_for_reload(
                foundry_name=foundry_name,
                fallback_record=record or {},
            )

            self._load_agent_foundry_raw_source_into_frontend_object(
                raw_source_text=saved_raw_source_text,
                viewer_content=saved_viewer_text,
                original_blueprint_text=saved_blueprint_text,
                original_leftovers_text=saved_leftovers_text,
                foundry_name=foundry_name,
                record=updated_record,
                mutation_reload_pass=mutation_reload_pass + 1,
            )
            return

        self._render_agent_foundry_frontend_object(
            frontend_object=frontend_object,
        )

    def _run_agent_foundry_mutation_checkpoint_after_parser(
        self,
        *,
        frontend_object: dict[str, Any],
    ) -> bool:
        checkpoint_callable = getattr(
            self,
            "_run_agent_foundry_mutation_checkpoint_before_render",
            None,
        )
        if not callable(checkpoint_callable):
            return False

        self.agent_foundry_dirty = False
        return bool(checkpoint_callable(frontend_object=frontend_object))

    def _get_current_agent_foundry_record_for_reload(
        self,
        *,
        foundry_name: str,
        fallback_record: dict[str, Any],
    ) -> dict[str, Any]:
        record_map = getattr(self, "agent_foundry_record_map", None)
        if isinstance(record_map, dict):
            record = record_map.get(str(foundry_name or "").strip())
            if isinstance(record, dict):
                return record

        return dict(fallback_record or {})

    def _refresh_agent_foundry_workspaces(self) -> None:
        try:
            workspaces_root = self._get_agent_foundry_workspaces_root_from_handoff()

            workspace_map: dict[str, Path] = {}
            record_map: dict[str, dict[str, Any]] = {}

            if workspaces_root.exists():
                workspace_dirs = [
                    path
                    for path in workspaces_root.iterdir()
                    if path.is_dir()
                ]

                for workspace_dir in sorted(
                    workspace_dirs,
                    key=lambda path: path.name.lower(),
                ):
                    workspace_dir = workspace_dir.expanduser().resolve()
                    foundry_name = str(workspace_dir.name or "").strip()
                    if not foundry_name:
                        continue

                    blueprint_file = self._find_agent_foundry_workspace_blueprint_file(
                        workspace_dir,
                    )
                    if blueprint_file is None:
                        continue

                    metadata_file = self._find_agent_foundry_workspace_metadata_file(
                        workspace_dir,
                    )
                    leftovers_file = self._find_agent_foundry_workspace_leftovers_file(
                        workspace_dir,
                    )
                    runtime_file = self._find_agent_foundry_workspace_runtime_file(
                        workspace_dir,
                    )

                    metadata = self._load_agent_foundry_workspace_metadata_if_present(
                        metadata_file,
                    )
                    metadata_record = self._extract_agent_foundry_metadata_record(
                        metadata,
                    )

                    record = dict(metadata_record)
                    record["foundry_name"] = foundry_name
                    record["workspace_dir"] = str(workspace_dir)
                    record["blueprint_file"] = str(blueprint_file)

                    if metadata_file is not None:
                        record["metadata_file"] = str(metadata_file)

                    if leftovers_file is not None:
                        record["leftovers_file"] = str(leftovers_file)

                    if runtime_file is not None:
                        record["runtime_file"] = str(runtime_file)

                    workspace_map[foundry_name] = workspace_dir
                    record_map[foundry_name] = record

            workspace_names = sorted(workspace_map.keys(), key=str.lower)

            self.agent_foundry_workspace_map = workspace_map
            self.agent_foundry_record_map = record_map
            self.agent_foundry_all_workspace_names = workspace_names

            picker = getattr(self, "agent_foundry_workspace_picker", None)
            picker_var = getattr(self, "agent_foundry_workspace_var", None)

            if picker is None or picker_var is None:
                return

            picker.configure(values=workspace_names)

            current_text = picker_var.get().strip()
            loaded_name = str(self.agent_foundry_loaded_name or "").strip()

            self.agent_foundry_suppress_picker_events = True
            try:
                if loaded_name and loaded_name in workspace_map:
                    picker_var.set(loaded_name)
                elif current_text and current_text in workspace_map:
                    picker_var.set(current_text)
                else:
                    picker_var.set("")
            finally:
                self.agent_foundry_suppress_picker_events = False

        except Exception as exc:
            self._agent_foundry_error("Agent Foundry Refresh Failed", exc)

    def _get_agent_foundry_workspaces_root_from_handoff(self) -> Path:
        handoff = self._get_agent_foundry_collection_handoff()

        method_names = (
            "get_agent_foundry_workspaces_root",
            "get_agent_foundry_workspace_root",
            "get_agent_foundry_workspaces_directory",
            "get_agent_foundry_workspace_directory",
            "get_agent_foundry_drafts_root",
            "get_agent_foundry_drafts_directory",
        )

        for method_name in method_names:
            method = getattr(handoff, method_name, None)
            if not callable(method):
                continue

            try:
                resolved_value = method()
            except TypeError:
                continue

            clean_value = str(resolved_value or "").strip()
            if clean_value:
                return Path(clean_value).expanduser().resolve()

        key_names = (
            "agent_foundry_workspaces_root",
            "agent_foundry_workspace_root",
            "agent_foundry_workspaces_directory",
            "agent_foundry_workspace_directory",
            "agent_foundry_drafts_root",
            "agent_foundry_drafts_directory",
        )

        for key_name in key_names:
            resolved_value = self._try_resolve_agent_foundry_handoff_key(
                handoff=handoff,
                key_name=key_name,
            )
            clean_value = str(resolved_value or "").strip()
            if clean_value:
                return Path(clean_value).expanduser().resolve()

        raise RuntimeError(
            "Collection handoff does not expose an Agent Foundry workspaces root."
        )

    def _try_resolve_agent_foundry_handoff_key(
        self,
        *,
        handoff: object,
        key_name: str,
    ) -> object:
        method_names = (
            "get_path",
            "resolve_path",
            "get_registry_path",
            "resolve_registry_path",
            "get_collection_path",
            "resolve_collection_path",
            "get",
        )

        for method_name in method_names:
            method = getattr(handoff, method_name, None)
            if not callable(method):
                continue

            try:
                return method(key_name)
            except Exception:
                continue

        registry = getattr(handoff, "registry", None)
        if isinstance(registry, dict):
            value = registry.get(key_name)
            if value:
                return value

        paths = getattr(handoff, "paths", None)
        if isinstance(paths, dict):
            value = paths.get(key_name)
            if value:
                return value

        return ""

    def _find_agent_foundry_workspace_metadata_file(
        self,
        workspace_dir: Path,
    ) -> Path | None:
        preferred_names = (
            ".agent_foundry.json",
            "agent_foundry.json",
            "metadata.agent_foundry.json",
            "agent_foundry.metadata.json",
            "foundry_metadata.json",
        )

        for file_name in preferred_names:
            candidate = workspace_dir / file_name
            if candidate.is_file():
                return candidate.resolve()

        candidates = [
            path
            for path in workspace_dir.glob("*.json")
            if path.is_file()
            and "agent_foundry" in path.name.lower()
            and "index" not in path.name.lower()
        ]
        if candidates:
            return sorted(candidates, key=lambda path: path.name.lower())[0].resolve()

        return None

    def _load_agent_foundry_workspace_metadata_if_present(
        self,
        metadata_file: Path | None,
    ) -> dict[str, Any]:
        if metadata_file is None:
            return {}

        try:
            loaded = json.loads(metadata_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

        if isinstance(loaded, dict):
            return loaded

        return {}

    def _extract_agent_foundry_metadata_record(
        self,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(metadata, dict):
            return {}

        record = metadata.get("record")
        if isinstance(record, dict):
            return dict(record)

        return dict(metadata)

    def _find_agent_foundry_workspace_blueprint_file(
        self,
        workspace_dir: Path,
    ) -> Path | None:
        preferred_names = (
            "blueprint.txt",
            "agent.blueprint.txt",
            f"{workspace_dir.name}.blueprint.txt",
        )

        for file_name in preferred_names:
            candidate = workspace_dir / file_name
            if candidate.is_file():
                return candidate.resolve()

        candidates = [
            path
            for path in workspace_dir.glob("*.blueprint.txt")
            if path.is_file()
        ]
        if candidates:
            return sorted(candidates, key=lambda path: path.name.lower())[0].resolve()

        txt_candidates = [
            path
            for path in workspace_dir.glob("*.txt")
            if path.is_file()
            and "blueprint" in path.name.lower()
        ]
        if txt_candidates:
            return sorted(txt_candidates, key=lambda path: path.name.lower())[0].resolve()

        return None

    def _find_agent_foundry_workspace_leftovers_file(
        self,
        workspace_dir: Path,
    ) -> Path | None:
        preferred_names = (
            ".leftovers.agent_foundry.txt",
            "leftovers.agent_foundry.txt",
            "agent_foundry.leftovers.txt",
            "leftovers.txt",
        )

        for file_name in preferred_names:
            candidate = workspace_dir / file_name
            if candidate.is_file():
                return candidate.resolve()

        candidates = [
            path
            for path in workspace_dir.glob("*.txt")
            if path.is_file()
            and "leftover" in path.name.lower()
        ]
        if candidates:
            return sorted(candidates, key=lambda path: path.name.lower())[0].resolve()

        return None

    def _find_agent_foundry_workspace_runtime_file(
        self,
        workspace_dir: Path,
    ) -> Path | None:
        preferred_names = (
            "runtime.py",
            "agent_runtime.py",
            "foundry_runtime.py",
            f"{workspace_dir.name}.runtime.py",
        )

        for file_name in preferred_names:
            candidate = workspace_dir / file_name
            if candidate.is_file():
                return candidate.resolve()

        candidates = [
            path
            for path in workspace_dir.glob("*.py")
            if path.is_file()
            and "runtime" in path.name.lower()
        ]
        if candidates:
            return sorted(candidates, key=lambda path: path.name.lower())[0].resolve()

        return None
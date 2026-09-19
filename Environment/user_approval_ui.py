from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from Operations.task_runner import run_task


class UserApprovalTabMixin:
    def _build_user_approval_tab(self) -> None:
        self.user_approval_root_dir = self._get_user_approval_root_dir()

        self.user_approval_state_order = ["Pending", "Investigate", "Resolved"]
        self.user_approval_category_order = ["Tasks", "Packages", "Agents", "System"]
        self.user_approval_tab_registry: dict[str, dict[str, dict]] = {}

        self.user_approval_resolved_default_days_back = 30
        self.user_approval_resolved_hard_limit = 500

        outer = tk.Frame(self.user_approval_tab)
        outer.pack(fill="both", expand=True)

        self.user_control_notebook = ttk.Notebook(outer)
        self.user_control_notebook.pack(fill="both", expand=True)

        self.user_reports_tab = tk.Frame(self.user_control_notebook, padx=8, pady=8)
        self.user_storage_tab = tk.Frame(self.user_control_notebook, padx=8, pady=8)

        self.user_control_notebook.add(self.user_reports_tab, text="User Reports")
        self.user_control_notebook.add(self.user_storage_tab, text="Storage")

        self.user_approval_state_notebook = ttk.Notebook(self.user_reports_tab)
        self.user_approval_state_notebook.pack(fill="both", expand=True)

        for state_name in self.user_approval_state_order:
            state_frame = tk.Frame(self.user_approval_state_notebook, padx=8, pady=8)
            self.user_approval_state_notebook.add(state_frame, text=state_name)
            self.user_approval_tab_registry[state_name] = {}
            self._build_user_approval_state_tab(state_frame, state_name)

        self._build_user_storage_tab(self.user_storage_tab)

        self.user_approval_status_label = tk.Label(
            self.user_approval_tab,
            text="",
            anchor="w",
            fg="gray25",
        )
        self.user_approval_status_label.pack(fill="x", pady=(10, 0))

        self._refresh_all_user_approval_tabs()
        self._refresh_user_storage_tab()
        self._set_user_approval_status(f"User Control root: {self.user_approval_root_dir}")

    def _get_collection_handoff_for_storage(self):
        if hasattr(self, "_get_collection_handoff") and callable(self._get_collection_handoff):
            handoff = self._get_collection_handoff()
            if handoff is not None:
                return handoff

        handoff = getattr(self, "collection_handoff", None)
        if handoff is not None:
            return handoff

        package_controller = getattr(self, "package_controller", None)
        if package_controller is not None:
            handoff = getattr(package_controller, "handoff", None)
            if handoff is not None:
                return handoff

        raise RuntimeError("CollectionHandoff is not available on the UI object.")

    def _get_user_approval_root_dir(self) -> Path:
        handoff = self._get_collection_handoff_for_storage()
        return Path(handoff.get_storage_entry_directory("user_approval_root")).expanduser().resolve()

    def _get_user_approval_base_dir(self) -> str:
        handoff = self._get_collection_handoff_for_storage()

        if hasattr(handoff, "get_base_dir") and callable(handoff.get_base_dir):
            base_dir = str(handoff.get_base_dir()).strip()
            if base_dir:
                return base_dir

        package_controller = getattr(self, "package_controller", None)
        if package_controller is not None:
            base_dir = str(getattr(package_controller, "base_dir", "") or "").strip()
            if base_dir:
                return base_dir

        raise RuntimeError("Could not determine base_dir for user approval task execution.")

    def _get_user_approval_action_list_map(self) -> dict:
        return {
            "actions": {
                "button_alignment": "approve",
                "label": "Approve Follow Up Actions",
                "description": "Tasks to run when the item is approved and follow-up work should happen.",
            },
            "nothing": {
                "button_alignment": "resolve",
                "label": "Approve Resolve Actions",
                "description": "Tasks to run when the item is approved as resolved without applying the main follow-up action.",
            },
            "rollback": {
                "button_alignment": "rollback",
                "label": "Rollback Actions",
                "description": "Tasks to run when the item is rolled back.",
            },
        }

    def _build_user_storage_tab(self, parent: tk.Widget) -> None:
        outer = tk.Frame(parent)
        outer.pack(fill="both", expand=True)

        controls_row = tk.Frame(outer)
        controls_row.pack(fill="x", pady=(0, 8))

        tk.Label(
            controls_row,
            text="Storage Registry",
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(side="left")

        tk.Button(
            controls_row,
            text="Refresh",
            width=12,
            command=self._refresh_user_storage_tab,
        ).pack(side="right")

        list_frame = tk.Frame(outer)
        list_frame.pack(fill="both", expand=True)

        self.user_storage_canvas = tk.Canvas(list_frame, highlightthickness=0)
        self.user_storage_canvas.pack(side="left", fill="both", expand=True)

        self.user_storage_scrollbar = tk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.user_storage_canvas.yview,
        )
        self.user_storage_scrollbar.pack(side="right", fill="y")
        self.user_storage_canvas.configure(yscrollcommand=self.user_storage_scrollbar.set)

        self.user_storage_inner = tk.Frame(self.user_storage_canvas)
        self.user_storage_inner_window = self.user_storage_canvas.create_window(
            (0, 0),
            window=self.user_storage_inner,
            anchor="nw",
        )

        def _sync_scrollregion(event=None) -> None:
            self.user_storage_canvas.configure(scrollregion=self.user_storage_canvas.bbox("all"))

        def _sync_inner_width(event) -> None:
            self.user_storage_canvas.itemconfigure(self.user_storage_inner_window, width=event.width)

        self.user_storage_inner.bind("<Configure>", _sync_scrollregion)
        self.user_storage_canvas.bind("<Configure>", _sync_inner_width)

    def _refresh_user_storage_tab(self) -> None:
        if not hasattr(self, "user_storage_inner"):
            return

        for widget in self.user_storage_inner.winfo_children():
            widget.destroy()

        try:
            handoff = self._get_collection_handoff_for_storage()
            entries = handoff.list_storage_registry_entries()
        except Exception as exc:
            tk.Label(
                self.user_storage_inner,
                text=f"Storage registry could not be loaded: {exc}",
                anchor="w",
                fg="red3",
                justify="left",
            ).pack(fill="x", padx=6, pady=6)
            self._set_user_approval_status(f"Storage registry load failed: {exc}")
            return

        if not entries:
            tk.Label(
                self.user_storage_inner,
                text="No storage registry entries found.",
                anchor="w",
                fg="gray35",
            ).pack(fill="x", padx=6, pady=6)
            return

        for entry in entries:
            self._build_user_storage_entry_row(self.user_storage_inner, entry)

    def _build_user_storage_entry_row(self, parent: tk.Widget, entry: dict) -> None:
        outer = tk.Frame(parent, relief="groove", bd=1, padx=8, pady=8)
        outer.pack(fill="x", padx=6, pady=6)

        key = str(entry.get("key", "")).strip()
        label = str(entry.get("label", "")).strip() or key or "<unnamed>"
        resolved_path = str(entry.get("resolved_path", "")).strip()
        can_migrate = bool(entry.get("can_migrate", False))

        row = tk.Frame(outer)
        row.pack(fill="x")

        line_text = f"{label} : {resolved_path}"

        line_widget = tk.Entry(
            row,
            font=("Consolas", 10),
            relief="solid",
            bd=1,
            readonlybackground="white",
        )
        line_widget.pack(side="left", fill="x", expand=True, padx=(0, 8))
        line_widget.insert(0, line_text)
        line_widget.configure(state="readonly")

        if can_migrate:
            tk.Button(
                row,
                text="Migrate",
                width=12,
                command=lambda entry_key=key, entry_label=label, current_path=resolved_path: self._handle_migrate_storage_entry(
                    entry_key=entry_key,
                    entry_label=entry_label,
                    current_path=current_path,
                ),
            ).pack(side="right")
        else:
            spacer = tk.Label(
                row,
                text="",
                width=12,
            )
            spacer.pack(side="right")

    def _handle_migrate_storage_entry(
        self,
        entry_key: str,
        entry_label: str,
        current_path: str,
    ) -> None:
        try:
            handoff = self._get_collection_handoff_for_storage()

            chosen_directory = filedialog.askdirectory(
                parent=getattr(self, "user_approval_tab", self.root),
                title=f"Select new directory for {entry_label}",
                mustexist=False,
                initialdir=str(Path(current_path).expanduser().resolve().parent)
                if str(current_path).strip()
                else None,
            )

            chosen_directory = str(chosen_directory).strip()
            if not chosen_directory:
                return

            current_directory = Path(current_path).expanduser().resolve()
            target_directory = Path(chosen_directory).expanduser().resolve()

            if target_directory == current_directory:
                raise ValueError("The new directory must be different from the current directory.")

            if target_directory.exists():
                raise ValueError("Directory already exists. Choose a new empty directory for migration.")

            migration_result = handoff.migrate_storage_entry(entry_key, target_directory)

            self._sync_storage_dependent_ui_state(entry_key)
            self._refresh_user_storage_tab()

            moved_count = int(migration_result.get("moved_count", 0))
            final_target_directory = str(migration_result.get("target_directory", target_directory))

            success_message = (
                f"{entry_label} migrated successfully.\n\n"
                f"Moved items: {moved_count}\n"
                f"New directory:\n{final_target_directory}"
            )

            self._set_user_approval_status(success_message.replace("\n", " | "))
            messagebox.showinfo("Storage Migration Complete", success_message)

        except Exception as exc:
            messagebox.showerror("Storage Migration Failed", str(exc))

    def _sync_storage_dependent_ui_state(self, entry_key: str) -> None:
        clean_key = str(entry_key).strip()

        if clean_key == "package_root":
            try:
                handoff = self._get_collection_handoff_for_storage()
                live_directory = Path(handoff.get_storage_entry_directory("package_root")).expanduser().resolve()

                self.packages_dir = live_directory

                package_controller = getattr(self, "package_controller", None)
                if package_controller is not None:
                    if hasattr(package_controller, "packages_dir"):
                        package_controller.packages_dir = live_directory
                    if hasattr(package_controller, "base_dir"):
                        package_controller.base_dir = live_directory.parent
                    if hasattr(package_controller, "package_dir"):
                        package_controller.package_dir = live_directory

                if hasattr(self, "_refresh_package_directory_path"):
                    self._refresh_package_directory_path()

                if hasattr(self, "_set_package_status"):
                    self._set_package_status(f"Packages folder: {live_directory}")

            except Exception as exc:
                self._set_user_approval_status(f"Package storage refresh failed: {exc}")
            return

        if clean_key == "assembly_root":
            try:
                assembly_manager = getattr(self, "assembly_manager", None)
                if assembly_manager is not None:
                    self.assemblies_dir = assembly_manager.get_assemblies_dir()
                else:
                    handoff = self._get_collection_handoff_for_storage()
                    self.assemblies_dir = handoff.get_storage_entry_directory("assembly_root")

                if hasattr(self, "_set_assembly_status"):
                    self._set_assembly_status(f"Agents folder: {self.assemblies_dir}")

            except Exception as exc:
                self._set_user_approval_status(f"Agent storage refresh failed: {exc}")
            return

        if clean_key == "user_approval_root":
            try:
                self.user_approval_root_dir = self._get_user_approval_root_dir()

                for state_name in self.user_approval_state_order:
                    state_registry = self.user_approval_tab_registry.get(state_name, {})
                    for category_name in self.user_approval_category_order:
                        tab_info = state_registry.get(category_name)
                        if isinstance(tab_info, dict):
                            tab_info["folder_path"] = self._get_user_approval_folder_path(
                                state_name,
                                category_name,
                            )

                self._refresh_all_user_approval_tabs()
                self._set_user_approval_status(f"User Control root: {self.user_approval_root_dir}")

            except Exception as exc:
                self._set_user_approval_status(f"User Control storage refresh failed: {exc}")
            return

    def _build_user_approval_state_tab(self, parent: tk.Widget, state_name: str) -> None:
        inner_notebook = ttk.Notebook(parent)
        inner_notebook.pack(fill="both", expand=True)

        for category_name in self.user_approval_category_order:
            category_frame = tk.Frame(inner_notebook, padx=8, pady=8)
            inner_notebook.add(category_frame, text=category_name)
            tab_info = self._create_user_approval_category_tab(category_frame, state_name, category_name)
            self.user_approval_tab_registry[state_name][category_name] = tab_info

    def _create_user_approval_category_tab(
        self,
        parent: tk.Widget,
        state_name: str,
        category_name: str,
    ) -> dict:
        folder_path = self._get_user_approval_folder_path(state_name, category_name)
        folder_path.mkdir(parents=True, exist_ok=True)

        controls_row = tk.Frame(parent)
        controls_row.pack(fill="x", pady=(0, 8))

        resolved_from_var = None
        resolved_to_var = None

        if state_name == "Resolved":
            default_to = self._get_today_date_string()
            default_from = self._get_date_string_days_ago(self.user_approval_resolved_default_days_back)

            tk.Label(controls_row, text="From").pack(side="left")

            resolved_from_var = tk.StringVar(value=default_from)
            tk.Entry(
                controls_row,
                textvariable=resolved_from_var,
                width=12,
                font=("Consolas", 10),
            ).pack(side="left", padx=(6, 12))

            tk.Label(controls_row, text="To").pack(side="left")

            resolved_to_var = tk.StringVar(value=default_to)
            tk.Entry(
                controls_row,
                textvariable=resolved_to_var,
                width=12,
                font=("Consolas", 10),
            ).pack(side="left", padx=(6, 12))

            tk.Label(
                controls_row,
                text=f"(YYYY-MM-DD, capped at {self.user_approval_resolved_hard_limit})",
                fg="gray35",
            ).pack(side="left")

        tk.Button(
            controls_row,
            text="Refresh",
            width=12,
            command=lambda s=state_name, c=category_name: self._refresh_user_approval_category_tab(s, c),
        ).pack(side="right")

        list_frame = tk.Frame(parent)
        list_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(list_frame, highlightthickness=0)
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)

        inner = tk.Frame(canvas)
        inner_window = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _sync_scrollregion(event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _sync_inner_width(event) -> None:
            canvas.itemconfigure(inner_window, width=event.width)

        inner.bind("<Configure>", _sync_scrollregion)
        canvas.bind("<Configure>", _sync_inner_width)

        return {
            "state_name": state_name,
            "category_name": category_name,
            "folder_path": folder_path,
            "frame": parent,
            "canvas": canvas,
            "inner": inner,
            "resolved_from_var": resolved_from_var,
            "resolved_to_var": resolved_to_var,
        }

    def _get_user_approval_folder_path(self, state_name: str, category_name: str) -> Path:
        return self.user_approval_root_dir / state_name / category_name

    def _set_user_approval_status(self, text: str) -> None:
        if hasattr(self, "user_approval_status_label"):
            self.user_approval_status_label.config(text=text)

    def _refresh_all_user_approval_tabs(self) -> None:
        for state_name in self.user_approval_state_order:
            for category_name in self.user_approval_category_order:
                self._refresh_user_approval_category_tab(state_name, category_name)

    def _refresh_user_approval_category_tab(self, state_name: str, category_name: str) -> None:
        tab_info = self.user_approval_tab_registry[state_name][category_name]
        inner = tab_info["inner"]
        folder_path: Path = tab_info["folder_path"]

        folder_path.mkdir(parents=True, exist_ok=True)

        for widget in inner.winfo_children():
            widget.destroy()

        file_paths = self._get_sorted_user_approval_files(tab_info)

        if not file_paths:
            tk.Label(
                inner,
                text="No approval items found.",
                anchor="w",
                fg="gray35",
            ).pack(fill="x", padx=6, pady=6)
            return

        for file_path in file_paths:
            item_data = self._load_user_approval_item(file_path)
            self._build_user_approval_item_card(
                parent=inner,
                state_name=state_name,
                category_name=category_name,
                item_data=item_data,
            )

    def _get_sorted_user_approval_files(self, tab_info: dict) -> list[Path]:
        folder_path: Path = tab_info["folder_path"]
        state_name = tab_info["state_name"]

        file_paths = [path for path in folder_path.iterdir() if path.is_file()]

        loaded_items: list[dict] = []
        for file_path in file_paths:
            loaded_items.append(self._load_user_approval_item(file_path))

        if state_name == "Resolved":
            date_range = self._get_resolved_date_range(tab_info)

            filtered_items = [
                item
                for item in loaded_items
                if self._is_within_resolved_date_range(item["created_timestamp"], date_range)
            ]

            filtered_items.sort(
                key=lambda item: (
                    -item["created_timestamp"],
                    item["file_path"].name.lower(),
                )
            )

            if len(filtered_items) > self.user_approval_resolved_hard_limit:
                self._set_user_approval_status(
                    f"Resolved results exceeded {self.user_approval_resolved_hard_limit}. Showing newest {self.user_approval_resolved_hard_limit}."
                )

            return [
                item["file_path"]
                for item in filtered_items[: self.user_approval_resolved_hard_limit]
            ]

        loaded_items.sort(
            key=lambda item: (
                item["is_valid"],
                item["sort_priority"],
                -item["created_timestamp"],
                item["file_path"].name.lower(),
            )
        )

        return [item["file_path"] for item in loaded_items]

    def _get_resolved_date_range(self, tab_info: dict) -> tuple[float, float]:
        default_to_date = datetime.now().date()
        default_from_date = default_to_date - timedelta(days=self.user_approval_resolved_default_days_back)

        from_raw = ""
        to_raw = ""

        from_var = tab_info.get("resolved_from_var")
        to_var = tab_info.get("resolved_to_var")

        if from_var is not None:
            from_raw = str(from_var.get()).strip()
        if to_var is not None:
            to_raw = str(to_var.get()).strip()

        try:
            from_date = datetime.strptime(from_raw, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            from_date = default_from_date
            if from_var is not None:
                from_var.set(from_date.isoformat())
            self._set_user_approval_status(
                f"Resolved From date was invalid. Using default: {from_date.isoformat()}"
            )

        try:
            to_date = datetime.strptime(to_raw, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            to_date = default_to_date
            if to_var is not None:
                to_var.set(to_date.isoformat())
            self._set_user_approval_status(
                f"Resolved To date was invalid. Using default: {to_date.isoformat()}"
            )

        if from_date > to_date:
            from_date, to_date = to_date, from_date
            if from_var is not None:
                from_var.set(from_date.isoformat())
            if to_var is not None:
                to_var.set(to_date.isoformat())
            self._set_user_approval_status(
                f"Resolved date range was reversed. Swapped to {from_date.isoformat()} through {to_date.isoformat()}."
            )

        start_dt = datetime.combine(from_date, datetime.min.time())
        end_dt = datetime.combine(to_date, datetime.max.time())

        return (start_dt.timestamp(), end_dt.timestamp())

    def _is_within_resolved_date_range(self, created_timestamp: float, date_range: tuple[float, float]) -> bool:
        if created_timestamp <= 0:
            return False

        start_ts, end_ts = date_range
        return start_ts <= created_timestamp <= end_ts

    def _get_today_date_string(self) -> str:
        return datetime.now().date().isoformat()

    def _get_date_string_days_ago(self, days_back: int) -> str:
        return (datetime.now().date() - timedelta(days=days_back)).isoformat()

    def _format_user_approval_created_at(self, created_timestamp: float) -> str:
        if not created_timestamp or created_timestamp <= 0:
            return "unknown"

        try:
            return datetime.fromtimestamp(created_timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "unknown"

    def _format_user_approval_priority(self, priority: object, is_valid: bool) -> str:
        if not is_valid:
            return "invalid"

        try:
            numeric_priority = float(priority)
        except (TypeError, ValueError):
            return "invalid"

        if numeric_priority.is_integer():
            return str(int(numeric_priority))

        return str(numeric_priority)

    def _load_user_approval_item(self, file_path: Path) -> dict:
        created_timestamp = self._get_file_creation_timestamp(file_path)

        broken_result = {
            "file_path": file_path,
            "is_valid": False,
            "summary_text": f"{file_path.name} is broken",
            "details_text": "",
            "priority": float("inf"),
            "sort_priority": float("inf"),
            "created_timestamp": created_timestamp,
        }

        try:
            raw_text = file_path.read_text(encoding="utf-8")
        except Exception:
            return broken_result

        try:
            parsed_json = json.loads(
                raw_text,
                object_pairs_hook=self._build_json_object_with_duplicate_detection,
            )
        except Exception:
            return broken_result

        if not isinstance(parsed_json, dict):
            return broken_result

        required_fields = ("User Summary", "Priority", "User Details")
        for field_name in required_fields:
            if field_name not in parsed_json:
                return broken_result

        raw_priority = parsed_json.get("Priority")
        if isinstance(raw_priority, bool):
            return broken_result

        try:
            numeric_priority = float(raw_priority)
        except (TypeError, ValueError):
            return broken_result

        summary_text = self._stringify_user_approval_value(parsed_json.get("User Summary"))
        details_text = self._stringify_user_approval_value(parsed_json.get("User Details"))

        return {
            "file_path": file_path,
            "is_valid": True,
            "summary_text": summary_text,
            "details_text": details_text,
            "priority": numeric_priority,
            "sort_priority": numeric_priority,
            "created_timestamp": created_timestamp,
        }

    def _build_json_object_with_duplicate_detection(self, pairs: list[tuple[object, object]]) -> dict:
        result: dict[str, object] = {}
        seen_keys: set[str] = set()

        for raw_key, value in pairs:
            key = str(raw_key)
            if key in seen_keys:
                raise ValueError(f"Duplicate JSON field detected: {key}")
            seen_keys.add(key)
            result[key] = value

        return result

    def _get_file_creation_timestamp(self, file_path: Path) -> float:
        try:
            return file_path.stat().st_ctime
        except Exception:
            return 0.0

    def _stringify_user_approval_value(self, value: object) -> str:
        if isinstance(value, str):
            return value

        if isinstance(value, (dict, list)):
            return json.dumps(value, indent=2, ensure_ascii=False)

        if value is None:
            return "None"

        return str(value)

    def _load_json_object(self, file_path: Path) -> dict:
        raw_text = file_path.read_text(encoding="utf-8")
        parsed_json = json.loads(
            raw_text,
            object_pairs_hook=self._build_json_object_with_duplicate_detection,
        )

        if not isinstance(parsed_json, dict):
            raise ValueError(f"Approval file is not a JSON object: {file_path}")

        return parsed_json

    def _normalize_user_approval_runtime_payload(
        self,
        raw_value: object,
        file_path: Path,
        list_name: str,
        entry_index: int,
    ) -> dict:
        if raw_value is None:
            return {}

        if isinstance(raw_value, dict):
            return dict(raw_value)

        if isinstance(raw_value, str):
            text = raw_value.strip()
            if not text:
                return {}

            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{list_name} entry #{entry_index} has invalid JSON in runtime_payload: {file_path}"
                ) from exc

            if not isinstance(parsed, dict):
                raise ValueError(
                    f"{list_name} entry #{entry_index} runtime_payload must resolve to a JSON object: {file_path}"
                )

            return dict(parsed)

        raise ValueError(
            f"{list_name} entry #{entry_index} runtime_payload must be a dict, JSON string, or blank: {file_path}"
        )

    def _normalize_user_approval_task_entries(
        self,
        parsed_json: dict,
        file_path: Path,
        list_name: str,
    ) -> list[dict]:
        clean_list_name = str(list_name or "").strip()
        if not clean_list_name:
            raise ValueError("list_name is required.")

        raw_entries = parsed_json.get(clean_list_name, [])

        if raw_entries in (None, ""):
            return []

        if not isinstance(raw_entries, list):
            raise ValueError(f"Approval file field '{clean_list_name}' must be a list: {file_path}")

        normalized_entries: list[dict] = []

        for index, raw_entry in enumerate(raw_entries, start=1):
            if not isinstance(raw_entry, dict):
                raise ValueError(f"{clean_list_name} entry #{index} must be a JSON object: {file_path}")

            agent_name = str(raw_entry.get("agent_name", "") or "").strip()
            task_name = str(raw_entry.get("task_name", "") or "").strip()

            if not agent_name:
                raise ValueError(f"{clean_list_name} entry #{index} is missing 'agent_name': {file_path}")

            if not task_name:
                raise ValueError(f"{clean_list_name} entry #{index} is missing 'task_name': {file_path}")

            runtime_payload = self._normalize_user_approval_runtime_payload(
                raw_value=raw_entry.get("runtime_payload"),
                file_path=file_path,
                list_name=clean_list_name,
                entry_index=index,
            )

            normalized_entries.append(
                {
                    "agent_name": agent_name,
                    "task_name": task_name,
                    "runtime_payload": runtime_payload,
                }
            )

        return normalized_entries

    def _execute_user_approval_list_from_report(
        self,
        source_file_path: Path,
        list_name: str,
    ) -> int:
        parsed_json = self._load_json_object(source_file_path)

        entries = self._normalize_user_approval_task_entries(
            parsed_json=parsed_json,
            file_path=source_file_path,
            list_name=list_name,
        )

        if not entries:
            return 0

        base_dir = self._get_user_approval_base_dir()

        for index, entry in enumerate(entries, start=1):
            runtime_payload = entry.get("runtime_payload", {})

            if not isinstance(runtime_payload, dict):
                raise ValueError(
                    f"{list_name} entry #{index} did not produce a dict runtime_payload: {source_file_path}"
                )

            run_task(
                base_dir=base_dir,
                agent_name=entry["agent_name"],
                task_name=entry["task_name"],
                runtime_payload=runtime_payload,
            )

        return len(entries)

    def _move_user_approval_file(
        self,
        source_file_path: Path,
        state_name: str,
        category_name: str,
        destination_state: str,
    ) -> Path:
        destination_folder = self._get_user_approval_folder_path(destination_state, category_name)
        destination_folder.mkdir(parents=True, exist_ok=True)

        destination_file_path = destination_folder / source_file_path.name

        if destination_file_path.exists():
            raise FileExistsError(
                f"Destination file already exists:\n{destination_file_path}"
            )

        shutil.move(str(source_file_path), str(destination_file_path))
        return destination_file_path

    def _build_user_approval_item_card(
        self,
        parent: tk.Widget,
        state_name: str,
        category_name: str,
        item_data: dict,
    ) -> None:
        outer = tk.Frame(parent, relief="groove", bd=1, padx=10, pady=10)
        outer.pack(fill="x", padx=6, pady=6)

        header_row = tk.Frame(outer)
        header_row.pack(fill="x", pady=(0, 8))
        header_row.grid_columnconfigure(0, weight=1)
        header_row.grid_columnconfigure(1, weight=0)
        header_row.grid_columnconfigure(2, weight=0)

        file_name = item_data["file_path"].name
        priority_text = self._format_user_approval_priority(
            priority=item_data.get("priority"),
            is_valid=bool(item_data.get("is_valid", False)),
        )
        created_at_text = self._format_user_approval_created_at(
            float(item_data.get("created_timestamp", 0.0) or 0.0)
        )

        filename_label = tk.Label(
            header_row,
            text=f"File name: {file_name}",
            anchor="w",
            justify="left",
            font=("Segoe UI", 9, "bold"),
            fg="gray20",
            wraplength=620,
        )
        filename_label.grid(row=0, column=0, sticky="ew", padx=(0, 12))

        priority_label = tk.Label(
            header_row,
            text=f"Priority: {priority_text}",
            anchor="center",
            justify="center",
            font=("Segoe UI", 9, "bold"),
            fg="gray20",
            width=14,
        )
        priority_label.grid(row=0, column=1, sticky="e", padx=(0, 12))

        created_label = tk.Label(
            header_row,
            text=f"Created at: {created_at_text}",
            anchor="e",
            justify="right",
            font=("Segoe UI", 9),
            fg="gray25",
            width=26,
        )
        created_label.grid(row=0, column=2, sticky="e")

        summary_text = tk.Text(
            outer,
            wrap="word",
            height=5,
            font=("Segoe UI", 10),
            relief="solid",
            bd=1,
        )
        summary_text.pack(fill="x", expand=False)
        summary_text.insert("1.0", item_data["summary_text"])
        summary_text.configure(state="disabled")

        button_row = tk.Frame(outer)
        button_row.pack(fill="x", pady=(8, 0))

        details_container = tk.Frame(outer)
        details_container.pack(fill="x", pady=(8, 0))

        if not item_data["is_valid"]:
            tk.Button(
                button_row,
                text="Show Details",
                width=14,
                state="disabled",
            ).pack(side="left")

            for action_spec in reversed(self._get_user_approval_action_specs(state_name, category_name)):
                tk.Button(
                    button_row,
                    text=action_spec["label"],
                    width=action_spec["width"],
                    state="disabled",
                    fg=action_spec.get("fg"),
                ).pack(side="right", padx=(8, 0))

            return

        details_visible = {"value": False}

        details_text_widget = tk.Text(
            details_container,
            wrap="word",
            height=10,
            font=("Consolas", 10),
            relief="solid",
            bd=1,
        )

        details_scrollbar = tk.Scrollbar(
            details_container,
            orient="vertical",
            command=details_text_widget.yview,
        )
        details_text_widget.configure(yscrollcommand=details_scrollbar.set)

        details_text_widget.insert("1.0", item_data["details_text"])
        details_text_widget.configure(state="disabled")

        toggle_button = tk.Button(
            button_row,
            text="Show Details",
            width=14,
            command=lambda: self._toggle_user_approval_details(
                details_visible=details_visible,
                details_text_widget=details_text_widget,
                details_scrollbar=details_scrollbar,
                toggle_button=toggle_button,
            ),
        )
        toggle_button.pack(side="left")

        action_specs = self._get_user_approval_action_specs(state_name, category_name)

        for action_spec in reversed(action_specs):
            tk.Button(
                button_row,
                text=action_spec["label"],
                width=action_spec["width"],
                command=lambda spec=action_spec, path=item_data["file_path"]: self._handle_user_approval_action(
                    source_file_path=path,
                    state_name=state_name,
                    category_name=category_name,
                    action_name=spec["action_name"],
                    destination_state=spec["destination_state"],
                ),
                fg=action_spec.get("fg"),
            ).pack(side="right", padx=(8, 0))

    def _toggle_user_approval_details(
        self,
        details_visible: dict,
        details_text_widget: tk.Text,
        details_scrollbar: tk.Scrollbar,
        toggle_button: tk.Button,
    ) -> None:
        if details_visible["value"]:
            details_text_widget.pack_forget()
            details_scrollbar.pack_forget()
            toggle_button.config(text="Show Details")
            details_visible["value"] = False
            return

        details_text_widget.pack(side="left", fill="both", expand=True)
        details_scrollbar.pack(side="right", fill="y")
        toggle_button.config(text="Hide Details")
        details_visible["value"] = True

    def _get_user_approval_action_specs(self, state_name: str, category_name: str) -> list[dict]:
        _ = category_name

        if state_name == "Pending":
            return [
                {
                    "label": "Approve Follow Up",
                    "width": 18,
                    "action_name": "approve",
                    "destination_state": "Resolved",
                    "fg": "green4",
                },
                {
                    "label": "Approve Resolve",
                    "width": 18,
                    "action_name": "resolve",
                    "destination_state": "Resolved",
                    "fg": "green4",
                },
                {
                    "label": "Deny",
                    "width": 10,
                    "action_name": "investigate",
                    "destination_state": "Investigate",
                    "fg": "red3",
                },
            ]

        if state_name == "Investigate":
            return [
                {
                    "label": "Approve Follow Up",
                    "width": 18,
                    "action_name": "approve",
                    "destination_state": "Resolved",
                    "fg": "green4",
                },
                {
                    "label": "Approve Resolve",
                    "width": 18,
                    "action_name": "resolve",
                    "destination_state": "Resolved",
                    "fg": "green4",
                },
                {
                    "label": "Rollback",
                    "width": 12,
                    "action_name": "rollback",
                    "destination_state": "Resolved",
                    "fg": "dark orange",
                },
            ]

        if state_name == "Resolved":
            return [
                {
                    "label": "Reopen",
                    "width": 12,
                    "action_name": "reopen",
                    "destination_state": "Investigate",
                }
            ]

        return []

    def _handle_user_approval_action(
        self,
        source_file_path: Path,
        state_name: str,
        category_name: str,
        action_name: str,
        destination_state: str,
    ) -> None:
        try:
            executed_action_count = 0
            executed_list_name = ""

            if action_name == "approve":
                executed_list_name = "actions"
                executed_action_count = self._execute_user_approval_list_from_report(
                    source_file_path=source_file_path,
                    list_name="actions",
                )

            elif action_name == "resolve":
                executed_list_name = "nothing"
                executed_action_count = self._execute_user_approval_list_from_report(
                    source_file_path=source_file_path,
                    list_name="nothing",
                )

            elif action_name == "rollback":
                executed_list_name = "rollback"
                executed_action_count = self._execute_user_approval_list_from_report(
                    source_file_path=source_file_path,
                    list_name="rollback",
                )

            self._move_user_approval_file(
                source_file_path=source_file_path,
                state_name=state_name,
                category_name=category_name,
                destination_state=destination_state,
            )

            self._refresh_user_approval_category_tab(state_name, category_name)
            self._refresh_user_approval_category_tab(destination_state, category_name)

            if executed_list_name:
                self._set_user_approval_status(
                    f"Ran {executed_action_count} '{executed_list_name}' action(s) from {source_file_path.name} "
                    f"and moved it from {state_name}/{category_name} to {destination_state}/{category_name}"
                )
            else:
                self._set_user_approval_status(
                    f"Moved {source_file_path.name} from {state_name}/{category_name} to {destination_state}/{category_name}"
                )

        except Exception as e:
            messagebox.showerror("User Approval Action Failed", str(e))
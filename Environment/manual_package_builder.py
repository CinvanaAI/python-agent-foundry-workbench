from pathlib import Path

import tkinter as tk
from tkinter import messagebox, ttk

from Environment.package_ui import PackageTabMixin
from Environment.assembly.assembly_ui import AssemblyTabMixin
from Environment.package_environment import PackageEnvironmentView
from Environment.user_approval_ui import UserApprovalTabMixin
from Environment.agent_foundry.agent_foundry_ui import AgentFoundryTabMixin
from Environment.chatroom_ui import ChatroomTabMixin

from collection_handoff import CollectionHandoff
from package_manager import PackageEditorController
from Operations.assembly.assembly_manager import AssemblyManager


class ItemPicker(tk.Toplevel):
    def __init__(self, parent, title_text: str, item_names, on_select) -> None:
        super().__init__(parent)
        self.title(title_text)
        self.geometry("420x420")
        self.minsize(320, 300)

        self.item_names = item_names
        self.on_select = on_select
        self.title_text = title_text

        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._populate_list()

    def _build_ui(self) -> None:
        outer = tk.Frame(self, padx=12, pady=12)
        outer.pack(fill="both", expand=True)

        tk.Label(outer, text=f"Choose a {self.title_text.lower()}").pack(anchor="w", pady=(0, 8))

        self.listbox = tk.Listbox(outer, font=("Consolas", 11))
        self.listbox.pack(fill="both", expand=True)

        self.listbox.bind("<Double-Button-1>", self._confirm_selection)

        button_row = tk.Frame(outer)
        button_row.pack(fill="x", pady=(10, 0))

        tk.Button(
            button_row,
            text="Open",
            width=12,
            command=self._confirm_selection,
        ).pack(side="left")

        tk.Button(
            button_row,
            text="Cancel",
            width=12,
            command=self.destroy,
        ).pack(side="right")

    def _populate_list(self) -> None:
        self.listbox.delete(0, tk.END)
        for item_name in self.item_names:
            self.listbox.insert(tk.END, item_name)

    def _confirm_selection(self, event=None) -> None:
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showerror("No Selection", f"Please choose a {self.title_text.lower()}.")
            return

        item_name = self.listbox.get(selection[0])
        self.on_select(item_name)
        self.destroy()


class StartupDestinationPicker(tk.Toplevel):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.parent = parent
        self.choice: str | None = None

        self.title("Start")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._handle_close)

        self._build_ui()
        self._center_on_parent()
        self.focus_force()

    def _build_ui(self) -> None:
        outer = tk.Frame(self, padx=20, pady=20)
        outer.pack(fill="both", expand=True)

        tk.Label(
            outer,
            text="Where do you want to go?",
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=(0, 14))

        tk.Button(
            outer,
            text="Package",
            width=22,
            command=lambda: self._select("package"),
        ).pack(pady=4)

        tk.Button(
            outer,
            text="Packages Environment",
            width=22,
            command=lambda: self._select("packages_environment"),
        ).pack(pady=4)

        tk.Button(
            outer,
            text="Agent",
            width=22,
            command=lambda: self._select("agent"),
        ).pack(pady=4)

        tk.Button(
            outer,
            text="Agent Foundry",
            width=22,
            command=lambda: self._select("agent_foundry"),
        ).pack(pady=4)

        tk.Button(
            outer,
            text="User Control",
            width=22,
            command=lambda: self._select("user_control"),
        ).pack(pady=4)

        tk.Button(
            outer,
            text="Chatroom",
            width=22,
            command=lambda: self._select("chatroom"),
        ).pack(pady=4)

        tk.Button(
            outer,
            text="Everywhere",
            width=22,
            command=lambda: self._select("everywhere"),
        ).pack(pady=4)

    def _center_on_parent(self) -> None:
        self.update_idletasks()

        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()

        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()

        x = parent_x + max((parent_w - width) // 2, 0)
        y = parent_y + max((parent_h - height) // 2, 0)

        self.geometry(f"{width}x{height}+{x}+{y}")

    def _select(self, choice: str) -> None:
        self.choice = choice
        self.destroy()

    def _handle_close(self) -> None:
        self.choice = None
        self.destroy()


class ManualPackageBuilderUI(
    PackageTabMixin,
    AssemblyTabMixin,
    AgentFoundryTabMixin,
    UserApprovalTabMixin,
    ChatroomTabMixin,
):
    def __init__(self, root: tk.Tk, base_dir: str | None = None) -> None:
        self.root = root
        self.root.title("Manual Package Builder")
        self.root.geometry("1100x760")
        self.root.minsize(900, 600)

        self.collection_handoff = CollectionHandoff(base_dir=base_dir)
        self.collection_handoff.initialize_storage_registry()
        self.package_controller = PackageEditorController(handoff=self.collection_handoff)
        self.assembly_manager = AssemblyManager(handoff=self.collection_handoff)

        self.packages_dir = Path(
            self.collection_handoff.get_storage_entry_directory("package_root")
        ).resolve()
        self.assemblies_dir = self.assembly_manager.get_agents_dir()
        self.base_dir = Path(self.collection_handoff.get_base_dir()).resolve()

        self.current_parent_name = None
        self.assembly_tabs: list[dict] = []

        self.package_required_replacement_rows: list[dict] = []
        self.package_optional_replacement_rows: list[dict] = []
        self.package_argument_rows: list[dict] = []
        self.package_return_rows: list[dict] = []
        self.package_recognition_rows: list[dict] = []

        self.item_picker_class = ItemPicker

        self._sync_package_directory_state()

        self._build_ui()
        self._set_package_status(f"Packages folder: {self.packages_dir}")
        self._set_assembly_status(f"Agents folder: {self.assemblies_dir}")

        self._create_new_task_tab()

    def _get_collection_handoff(self) -> CollectionHandoff:
        return self.collection_handoff

    def _get_live_package_directory(self) -> Path:
        return Path(
            self._get_collection_handoff().get_storage_entry_directory("package_root")
        ).resolve()

    def _get_package_file_path(self, package_name: str, directory: Path | None = None) -> Path:
        base_directory = directory.resolve() if directory is not None else self._get_live_package_directory()
        clean_name = self.collection_handoff.sanitize_name("package_record", package_name)
        if not clean_name:
            raise ValueError("Package name cannot be blank.")
        return base_directory / f"{clean_name}.package.json"

    def _sync_package_directory_state(self) -> Path:
        live_directory = self._get_live_package_directory()
        self.packages_dir = live_directory

        if hasattr(self, "package_controller") and self.package_controller is not None:
            if hasattr(self.package_controller, "packages_dir"):
                self.package_controller.packages_dir = live_directory
            if hasattr(self.package_controller, "base_dir"):
                self.package_controller.base_dir = live_directory.parent
            if hasattr(self.package_controller, "package_dir"):
                self.package_controller.package_dir = live_directory

        return live_directory

    def _set_live_package_directory(self, new_directory: Path) -> Path:
        resolved_directory = Path(
            self._get_collection_handoff().set_storage_entry_directory("package_root", new_directory)
        ).resolve()

        self.packages_dir = resolved_directory
        self._sync_package_directory_state()
        self._refresh_package_directory_path()

        return resolved_directory

    def _refresh_package_directory_path(self) -> None:
        directory_path = str(self._get_live_package_directory()).strip()
        if hasattr(self, "package_directory_var"):
            self.package_directory_var.set(directory_path)

    def _build_ui(self) -> None:
        main_frame = tk.Frame(self.root, padx=12, pady=12)
        main_frame.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True)

        self.package_tab = tk.Frame(self.notebook, padx=12, pady=12)
        self.package_environment_tab = tk.Frame(self.notebook, padx=0, pady=0)
        self.assembly_tab = tk.Frame(self.notebook, padx=12, pady=12)
        self.agent_foundry_tab = tk.Frame(self.notebook, padx=12, pady=12)
        self.user_approval_tab = tk.Frame(self.notebook, padx=12, pady=12)
        self.chatroom_tab = tk.Frame(self.notebook, padx=12, pady=12)

        self.notebook.add(self.package_tab, text="Package")
        self.notebook.add(self.package_environment_tab, text="Packages Environment")
        self.notebook.add(self.assembly_tab, text="Agent")
        self.notebook.add(self.agent_foundry_tab, text="Agent Foundry")
        self.notebook.add(self.user_approval_tab, text="User Control")
        self.notebook.add(self.chatroom_tab, text="Chatroom")

        self.package_environment_view = PackageEnvironmentView(self.package_environment_tab)

        self._build_package_tab()
        self._build_assembly_tab()
        self._build_agent_foundry_tab()
        self._build_user_approval_tab()
        self._build_chatroom_tab()

    def _show_startup_destination_picker(self) -> str | None:
        picker = StartupDestinationPicker(self.root)
        self.root.wait_window(picker)
        return picker.choice

    def _hide_tab(self, tab_widget: tk.Widget) -> None:
        try:
            self.notebook.hide(tab_widget)
        except tk.TclError:
            pass

    def _show_tab(self, tab_widget: tk.Widget, text: str) -> None:
        try:
            self.notebook.add(tab_widget, text=text)
        except tk.TclError:
            pass

    def _apply_startup_destination(self, choice: str) -> None:
        for tab_widget in (
            self.package_tab,
            self.package_environment_tab,
            self.assembly_tab,
            self.agent_foundry_tab,
            self.user_approval_tab,
            self.chatroom_tab,
        ):
            self._hide_tab(tab_widget)

        if choice == "package":
            self._show_tab(self.package_tab, "Package")
            self.notebook.select(self.package_tab)
            return

        if choice == "packages_environment":
            self._show_tab(self.package_environment_tab, "Packages Environment")
            self.notebook.select(self.package_environment_tab)
            return

        if choice == "agent":
            self._show_tab(self.assembly_tab, "Agent")
            self.notebook.select(self.assembly_tab)
            return

        if choice == "agent_foundry":
            self._show_tab(self.agent_foundry_tab, "Agent Foundry")
            self.notebook.select(self.agent_foundry_tab)
            return

        if choice == "user_control":
            self._show_tab(self.user_approval_tab, "User Control")
            self.notebook.select(self.user_approval_tab)
            return

        if choice == "chatroom":
            self._show_tab(self.chatroom_tab, "Chatroom")
            self.notebook.select(self.chatroom_tab)
            return

        self._show_tab(self.package_tab, "Package")
        self._show_tab(self.package_environment_tab, "Packages Environment")
        self._show_tab(self.assembly_tab, "Agent")
        self._show_tab(self.agent_foundry_tab, "Agent Foundry")
        self._show_tab(self.user_approval_tab, "User Control")
        self._show_tab(self.chatroom_tab, "Chatroom")
        self.notebook.select(self.package_tab)

    def launch(self) -> None:
        self.root.update_idletasks()

        choice = self._show_startup_destination_picker()
        if choice is None:
            self.root.destroy()
            return

        self._apply_startup_destination(choice)
        self.root.lift()
        self.root.focus_force()

    def _handle_edit_assembly(self) -> None:
        try:
            item_names = self.assembly_manager.list_agents()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        if not item_names:
            messagebox.showinfo("No Agents", "There are no saved agents yet.")
            return

        self._open_item_picker(
            title_text="Agent",
            item_names=item_names,
            on_select=self._load_selected_assembly,
        )

"""Launch-path regressions using disposable storage; no provider is invoked."""
import importlib
import tkinter as tk

import pytest


def test_desktop_and_runner_modules_import_without_private_connector():
    entrypoint = importlib.import_module("main")
    runner = importlib.import_module("Operations.task_runner_core")
    assert callable(entrypoint.main)
    assert callable(runner.run_task)


def test_workbench_constructs_all_tabs_and_launches_without_connector(tmp_path, monkeypatch):
    from collection_handoff import CollectionHandoff
    import Environment.manual_package_builder as builder
    try:
        root = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f"Tk display unavailable: {type(error).__name__}")
    root.withdraw()
    try:
        app = builder.ManualPackageBuilderUI(root, base_dir=str(tmp_path))
        monkeypatch.setattr(app, "_show_startup_destination_picker", lambda: "everywhere")
        monkeypatch.setattr(root, "lift", lambda: None)
        monkeypatch.setattr(root, "focus_force", lambda: None)
        app.launch()
        root.update_idletasks()
        assert len(app.notebook.tabs()) == 6
        assert len(app.assembly_tabs) >= 1
        assert app.base_dir == tmp_path.resolve()
    finally:
        root.destroy()


def test_fresh_registry_is_local_and_existing_registry_is_preserved(tmp_path):
    from collection_handoff import CollectionHandoff
    handoff = CollectionHandoff(str(tmp_path))
    handoff.initialize_storage_registry()
    for key in ("package_root", "assembly_root", "user_approval_root", "chat_root"):
        assert __import__('pathlib').Path(handoff.get_storage_entry_directory(key)).is_relative_to(tmp_path)
    registry_path = __import__('pathlib').Path(handoff.get_storage_registry_path())
    before = registry_path.read_bytes()
    handoff.initialize_storage_registry()
    assert registry_path.read_bytes() == before

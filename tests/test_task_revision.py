"""Saved package revisions cannot reuse another run's cached Python module."""
import sys
import types
from examples.revision_walkthrough import demonstrate


def test_saved_package_revision_is_executed_and_host_module_restored(tmp_path):
    previous = sys.modules.get("revision_probe")
    host = types.ModuleType("revision_probe")
    host.value = lambda: "host value"
    sys.modules["revision_probe"] = host
    try:
        assert demonstrate(tmp_path)["observed_outputs"] == ["first", "second"]
        assert sys.modules["revision_probe"] is host
    finally:
        if previous is None:
            sys.modules.pop("revision_probe", None)
        else:
            sys.modules["revision_probe"] = previous


def test_failed_run_restores_host_module_and_removes_materialized_runtime(tmp_path):
    import pytest
    from collection_handoff import CollectionHandoff
    from Operations.assembly.assembly_manager import AssemblyManager
    from Operations.task_runner import TaskRunner
    from Operations.task_runner_paths import get_running_task_dir

    handoff = CollectionHandoff(str(tmp_path))
    handoff.initialize_storage_registry()
    task = {
        "name": "Fail", "task_status": "On Demand",
        "packages": [{"name": "revision_failure", "package_status": "Active", "logic": {"logic_source": "def value(): return 'fixture'"}}],
        "workflow": {"workflow_source": "from revision_failure import value\ndef run_workflow(payload):\n    raise ValueError(value())"},
    }
    AssemblyManager(handoff=handoff).save_agent("DemoAgent", {"name": "DemoAgent", "default_returns": [], "groups": [{"name": "Outcasts", "tasks": [task]}]})
    previous = sys.modules.get("revision_failure")
    host = types.ModuleType("revision_failure")
    sys.modules["revision_failure"] = host
    try:
        with pytest.raises(ValueError, match="fixture"):
            TaskRunner(tmp_path, handoff).run_task("DemoAgent", "Fail", {})
        assert sys.modules["revision_failure"] is host
        assert not get_running_task_dir(tmp_path, handoff, "DemoAgent", "Fail").exists()
    finally:
        if previous is None:
            sys.modules.pop("revision_failure", None)
        else:
            sys.modules["revision_failure"] = previous

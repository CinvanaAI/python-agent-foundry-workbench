"""Save and run two task revisions; each uses the source saved in that revision."""
import json
import tempfile
from pathlib import Path
from collection_handoff import CollectionHandoff
from Operations.assembly.assembly_manager import AssemblyManager
from Operations.task_runner import run_task


def demonstrate(root):
    handoff = CollectionHandoff(str(root))
    handoff.initialize_storage_registry()
    manager = AssemblyManager(handoff=handoff)
    outputs = []
    for value in ("first", "second"):
        source = f"def value():\n    return {value!r}"
        task = {"name": "Inspect", "task_status": "On Demand", "packages": [{"name": "revision_probe", "package_status": "Active", "logic": {"logic_source": source}}], "workflow": {"workflow_source": "from revision_probe import value\ndef run_workflow(payload):\n    return value()"}}
        agent = {"name": "DemoAgent", "default_returns": [], "groups": [{"name": "Outcasts", "tasks": [task]}]}
        path = Path(manager.save_agent("DemoAgent", agent))
        assert value in path.read_text(encoding="utf-8")
        outputs.append(run_task(root, "DemoAgent", "Inspect", {}, handoff=handoff))
    assert outputs == ["first", "second"]
    return {"synthetic": True, "saved_task_revisions": 2, "observed_outputs": outputs, "latest_saved_source_matches_second_run": True}


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="foundry-revisions-") as temporary:
        print(json.dumps(demonstrate(Path(temporary)), indent=2))

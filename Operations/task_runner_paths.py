from __future__ import annotations

import shutil
from pathlib import Path

from collection_handoff import CollectionHandoff
from Operations.task_runner_process import kill_active_run_if_present


def sanitize_agent_or_task_name(handoff: CollectionHandoff, raw_name: str) -> str:
    return handoff.sanitize_name("assembly", raw_name)


def get_assemblies_root(
    handoff: CollectionHandoff,
) -> Path:
    assemblies_root = Path(handoff.get_storage_entry_directory("assembly_root")).resolve()

    if not assemblies_root.exists():
        raise FileNotFoundError(f"Assemblies root does not exist: {assemblies_root}")

    if not assemblies_root.is_dir():
        raise NotADirectoryError(f"Assemblies root is not a folder: {assemblies_root}")

    return assemblies_root


def get_agent_dir(
    base_dir: str | Path,
    handoff: CollectionHandoff,
    agent_name: str,
) -> Path:
    _ = base_dir

    agent_dir = get_assemblies_root(handoff) / sanitize_agent_or_task_name(handoff, agent_name)

    if not agent_dir.exists():
        raise FileNotFoundError(f"Agent folder does not exist: {agent_dir}")

    if not agent_dir.is_dir():
        raise NotADirectoryError(f"Agent path is not a folder: {agent_dir}")

    return agent_dir


def get_running_task_dir(
    base_dir: str | Path,
    handoff: CollectionHandoff,
    agent_name: str,
    task_name: str,
) -> Path:
    agent_dir = get_agent_dir(
        base_dir=base_dir,
        handoff=handoff,
        agent_name=agent_name,
    )
    return agent_dir / f"running_{sanitize_agent_or_task_name(handoff, task_name)}"


def get_pid_file_path(running_dir: Path) -> Path:
    return running_dir / "__task_runner_pid__.txt"


def prepare_running_task_dir(
    base_dir: str | Path,
    handoff: CollectionHandoff,
    agent_name: str,
    task_name: str,
) -> Path:
    running_dir = get_running_task_dir(
        base_dir=base_dir,
        handoff=handoff,
        agent_name=agent_name,
        task_name=task_name,
    )

    if running_dir.exists():
        kill_active_run_if_present(running_dir)
        shutil.rmtree(running_dir)

    running_dir.mkdir(parents=False, exist_ok=False)
    return running_dir
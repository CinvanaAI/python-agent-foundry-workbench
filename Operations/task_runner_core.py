from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path
from typing import Optional

from Operations.assembly.assembly_reader import AssemblyReader
from collection_handoff import CollectionHandoff
from Operations.task_runner_materializer import (
    write_package_scripts_from_child_data,
    write_workflow_script_from_child_data,
)
from Operations.task_runner_paths import (
    get_running_task_dir,
    prepare_running_task_dir,
    sanitize_agent_or_task_name,
)


class TaskRunner:
    def __init__(
        self,
        base_dir: str | Path,
        handoff: Optional[CollectionHandoff] = None,
    ) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.handoff = handoff or CollectionHandoff(base_dir=str(self.base_dir))
        self.assembly_reader = AssemblyReader(handoff=self.handoff)

    def _load_workflow_callable(
        self,
        workflow_path: Path,
        agent_name: str,
        task_name: str,
    ):
        module_name = (
            f"_generated_workflow_"
            f"{sanitize_agent_or_task_name(self.handoff, agent_name)}__"
            f"{sanitize_agent_or_task_name(self.handoff, task_name)}"
        )

        spec = importlib.util.spec_from_file_location(module_name, workflow_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load workflow module from: {workflow_path}")

        module = importlib.util.module_from_spec(spec)

        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(module_name, None)
            raise

        workflow_callable = getattr(module, "run_workflow", None)
        if not callable(workflow_callable):
            sys.modules.pop(module_name, None)
            raise ValueError(
                f"Workflow file must define a callable 'run_workflow(payload_package)': {workflow_path}"
            )

        return module_name, workflow_callable

    def _get_task_workflow_path(
        self,
        running_dir: Path,
        agent_name: str,
        task_name: str,
    ) -> Path:
        return running_dir / (
            f"{sanitize_agent_or_task_name(self.handoff, agent_name)}__"
            f"{sanitize_agent_or_task_name(self.handoff, task_name)}_workflow.py"
        )

    def _load_task_data(
        self,
        agent_name: str,
        task_name: str,
    ) -> dict:
        task_data = self.assembly_reader.load_task_data(
            parent_name=agent_name,
            task_name=task_name,
        )
        if not isinstance(task_data, dict):
            raise ValueError("Loaded task data must be a dict.")
        return task_data

    def _get_task_status(self, task_data: dict) -> str:
        raw_status = task_data.get("task_status", "On Demand")
        task_status = str(raw_status).strip() or "On Demand"
        return task_status

    def _materialize_task_into_dir(
        self,
        running_dir: Path,
        agent_name: str,
        task_name: str,
        task_data: dict,
    ) -> Path:
        workflow_path = self._get_task_workflow_path(
            running_dir=running_dir,
            agent_name=agent_name,
            task_name=task_name,
        )

        write_package_scripts_from_child_data(
            handoff=self.handoff,
            child_data=task_data,
            task_name=task_name,
            output_dir=running_dir,
        )

        write_workflow_script_from_child_data(
            child_data=task_data,
            task_name=task_name,
            output_path=workflow_path,
        )

        return workflow_path

    def materialize_system_task(
        self,
        agent_name: str,
        task_name: str,
    ) -> Path:
        clean_agent_name = str(agent_name).strip()
        clean_task_name = str(task_name).strip()

        if not clean_agent_name:
            raise ValueError("Enter or load an agent name first.")
        if not clean_task_name:
            raise ValueError("Current task is missing a name.")

        task_data = self._load_task_data(
            agent_name=clean_agent_name,
            task_name=clean_task_name,
        )
        task_status = self._get_task_status(task_data)
        if task_status != "System":
            raise ValueError(
                f"Task '{clean_task_name}' is not marked as System and cannot be materialized as a system task."
            )

        running_dir = prepare_running_task_dir(
            base_dir=self.base_dir,
            handoff=self.handoff,
            agent_name=clean_agent_name,
            task_name=clean_task_name,
        )

        self._materialize_task_into_dir(
            running_dir=running_dir,
            agent_name=clean_agent_name,
            task_name=clean_task_name,
            task_data=task_data,
        )

        return running_dir

    def _execute_workflow_from_dir(
        self,
        running_dir: Path,
        agent_name: str,
        task_name: str,
        runtime_payload: object,
    ) -> object:
        inserted_sys_path = False
        loaded_module_name: str | None = None

        try:
            workflow_path = self._get_task_workflow_path(
                running_dir=running_dir,
                agent_name=agent_name,
                task_name=task_name,
            )

            if not workflow_path.exists():
                raise FileNotFoundError(f"Workflow file does not exist: {workflow_path}")

            running_dir_str = str(running_dir)
            if running_dir_str not in sys.path:
                sys.path.insert(0, running_dir_str)
                inserted_sys_path = True

            loaded_module_name, workflow_callable = self._load_workflow_callable(
                workflow_path=workflow_path,
                agent_name=agent_name,
                task_name=task_name,
            )

            return workflow_callable(runtime_payload)

        finally:
            if loaded_module_name:
                sys.modules.pop(loaded_module_name, None)

            if inserted_sys_path:
                running_dir_str = str(running_dir)
                try:
                    sys.path.remove(running_dir_str)
                except ValueError:
                    pass

    def run_system_task(
        self,
        agent_name: str,
        task_name: str,
        runtime_payload: object,
        timeout_seconds: float | None = None,
    ) -> object:
        _ = timeout_seconds

        clean_agent_name = str(agent_name).strip()
        clean_task_name = str(task_name).strip()

        if not clean_agent_name:
            raise ValueError("Enter or load an agent name first.")
        if not clean_task_name:
            raise ValueError("Current task is missing a name.")

        task_data = self._load_task_data(
            agent_name=clean_agent_name,
            task_name=clean_task_name,
        )
        task_status = self._get_task_status(task_data)
        if task_status != "System":
            raise ValueError(
                f"Task '{clean_task_name}' is not marked as System and cannot be run as a system task."
            )

        running_dir = get_running_task_dir(
            base_dir=self.base_dir,
            handoff=self.handoff,
            agent_name=clean_agent_name,
            task_name=clean_task_name,
        )

        if not running_dir.exists():
            running_dir = self.materialize_system_task(
                agent_name=clean_agent_name,
                task_name=clean_task_name,
            )

        return self._execute_workflow_from_dir(
            running_dir=running_dir,
            agent_name=clean_agent_name,
            task_name=clean_task_name,
            runtime_payload=runtime_payload,
        )

    def run_task(
        self,
        agent_name: str,
        task_name: str,
        runtime_payload: object,
        timeout_seconds: float | None = None,
    ) -> object:
        running_dir: Path | None = None
        should_cleanup_running_dir = False

        clean_agent_name = str(agent_name).strip()
        clean_task_name = str(task_name).strip()

        if not clean_agent_name:
            raise ValueError("Enter or load an agent name first.")
        if not clean_task_name:
            raise ValueError("Current task is missing a name.")
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than 0 when provided.")

        task_data = self._load_task_data(
            agent_name=clean_agent_name,
            task_name=clean_task_name,
        )
        task_status = self._get_task_status(task_data)

        if task_status == "System":
            return self.run_system_task(
                agent_name=clean_agent_name,
                task_name=clean_task_name,
                runtime_payload=runtime_payload,
                timeout_seconds=timeout_seconds,
            )

        try:
            running_dir = prepare_running_task_dir(
                base_dir=self.base_dir,
                handoff=self.handoff,
                agent_name=clean_agent_name,
                task_name=clean_task_name,
            )
            should_cleanup_running_dir = True

            self._materialize_task_into_dir(
                running_dir=running_dir,
                agent_name=clean_agent_name,
                task_name=clean_task_name,
                task_data=task_data,
            )

            return self._execute_workflow_from_dir(
                running_dir=running_dir,
                agent_name=clean_agent_name,
                task_name=clean_task_name,
                runtime_payload=runtime_payload,
            )

        finally:
            if should_cleanup_running_dir and running_dir and running_dir.exists():
                try:
                    shutil.rmtree(running_dir)
                except Exception as exc:
                    print(
                        f"TaskRunner cleanup warning: failed to remove '{running_dir}': {exc}",
                        file=sys.stderr,
                    )


def run_task(
    base_dir: str | Path,
    agent_name: str,
    task_name: str,
    runtime_payload: object,
    timeout_seconds: float | None = None,
    handoff: Optional[CollectionHandoff] = None,
) -> object:
    runner = TaskRunner(base_dir=base_dir, handoff=handoff)
    return runner.run_task(
        agent_name=agent_name,
        task_name=task_name,
        runtime_payload=runtime_payload,
        timeout_seconds=timeout_seconds,
    )

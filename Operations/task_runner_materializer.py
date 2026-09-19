from __future__ import annotations

from pathlib import Path


def _extract_package_logic_source(
    package_entry: dict,
    package_name: str,
    task_name: str,
) -> str:
    raw_logic = package_entry.get("logic", {})

    if not isinstance(raw_logic, dict):
        raise ValueError(
            f"Package '{package_name}' in task '{task_name}' must store logic as "
            "{'logic_source': '...'}."
        )

    if "logic_source" not in raw_logic:
        raise ValueError(
            f"Package '{package_name}' in task '{task_name}' is missing logic.logic_source."
        )

    logic_source = raw_logic.get("logic_source", "")

    if not isinstance(logic_source, str):
        raise ValueError(
            f"Package '{package_name}' in task '{task_name}' logic.logic_source must be a string."
        )

    if not logic_source.strip():
        raise ValueError(
            f"Package logic is empty in task snapshot for package: {package_name}"
        )

    return logic_source


def write_package_scripts_from_child_data(
    handoff,
    child_data: dict,
    task_name: str,
    output_dir: str | Path,
) -> list[str]:
    raw_packages = child_data.get("packages", [])

    if not isinstance(raw_packages, list):
        raise ValueError(f"Task packages must be a list: {task_name}")

    output_dir_obj = Path(output_dir)
    output_dir_obj.mkdir(parents=True, exist_ok=True)

    written_paths: list[str] = []
    written_by_safe_name: dict[str, str] = {}

    for index, package_entry in enumerate(raw_packages, start=1):
        if not isinstance(package_entry, dict):
            raise ValueError(
                f"Package entry {index} in task '{task_name}' must be a dict."
            )

        package_name = str(package_entry.get("name", "")).strip()
        if not package_name:
            raise ValueError(
                f"Package entry {index} in task '{task_name}' is missing 'name'."
            )

        logic_source = _extract_package_logic_source(
            package_entry=package_entry,
            package_name=package_name,
            task_name=task_name,
        )

        safe_package_name = handoff.sanitize_name("package_record", package_name)
        if not safe_package_name:
            raise ValueError(f"Invalid package name: {package_name}")

        package_path = output_dir_obj / f"{safe_package_name}.py"
        package_path_str = str(package_path)

        if safe_package_name in written_by_safe_name:
            existing_path = written_by_safe_name[safe_package_name]
            if existing_path != package_path_str:
                raise ValueError(
                    f"Sanitized package name collision produced different paths for package: {package_name}"
                )
            continue

        package_path.write_text(logic_source.rstrip() + "\n", encoding="utf-8")
        written_by_safe_name[safe_package_name] = package_path_str
        written_paths.append(package_path_str)

    return written_paths


def _normalize_future_imports(script_text: str) -> str:
    lines = script_text.splitlines()

    future_lines: list[str] = []
    non_future_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("from __future__ import "):
            if line not in future_lines:
                future_lines.append(line)
            continue
        non_future_lines.append(line)

    if not future_lines:
        return script_text.rstrip() + "\n"

    rebuilt_lines: list[str] = []
    rebuilt_lines.extend(future_lines)

    if non_future_lines:
        rebuilt_lines.append("")
        rebuilt_lines.extend(non_future_lines)

    return "\n".join(rebuilt_lines).rstrip() + "\n"


def build_workflow_script_from_child_data(
    child_data: dict,
    task_name: str,
    parent_data: dict | None = None,
) -> str:
    _ = parent_data

    raw_workflow = child_data.get("workflow", {})
    if raw_workflow in (None, ""):
        raw_workflow = {}

    if not isinstance(raw_workflow, dict):
        raise ValueError(f"Task workflow must be a dict: {task_name}")

    workflow_source = raw_workflow.get("workflow_source", "")

    if not isinstance(workflow_source, str):
        raise ValueError(f"Task workflow.workflow_source must be a string: {task_name}")

    if not workflow_source.strip():
        raise ValueError(f"Task is missing workflow.workflow_source: {task_name}")

    return _normalize_future_imports(workflow_source)


def write_workflow_script_from_child_data(
    child_data: dict,
    task_name: str,
    output_path: str | Path,
    parent_data: dict | None = None,
) -> str:
    workflow_script = build_workflow_script_from_child_data(
        child_data=child_data,
        task_name=task_name,
        parent_data=parent_data,
    )

    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    output_path_obj.write_text(workflow_script, encoding="utf-8")

    return str(output_path_obj)
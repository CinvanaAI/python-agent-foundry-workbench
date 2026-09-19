from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


OLD_PACKAGE_ROOT = (
    Path(__file__).resolve().parents[2]
    / "Storage"
    / "Generated Artifacts"
    / "packages"
)

GRAMMAR_SUFFIX_PACKAGE_ID = "Package ID"
GRAMMAR_SUFFIX_PACKAGE_LOGIC = "Logic"

GRAMMAR_SUFFIX_REQUIRED_REPLACEMENT_LIST = "Required Replacement List"
GRAMMAR_SUFFIX_OPTIONAL_REPLACEMENT_LIST = "Optional Replacement List"
GRAMMAR_SUFFIX_PACKAGE_ARGUMENT_LIST = "Argument List"
GRAMMAR_SUFFIX_PACKAGE_RETURN_LIST = "Return List"
GRAMMAR_SUFFIX_PACKAGE_RECOGNITION_LIST = "Recognition List"


# =============================================================================
# Public UI-facing API
# =============================================================================


def run_foundry_blueprint_import(
    *,
    parent: Any = None,
    foundry_ui: Any = None,
) -> str:
    """One-time old Package JSON -> Package Foundry import.

    This importer is intentionally dumb.

    It only:
        - reads old package JSON files from the known old package folder
        - converts each package JSON into Package Foundry blueprint text
        - hands that blueprint text to Workspace package creation

    It does not use CollectionHandoff.
    It does not resolve registry paths.
    It does not own final Foundry storage.
    """

    from tkinter import messagebox

    try:
        result = sync_packages_into_foundry(
            foundry_ui=foundry_ui,
            force=False,
        )
    except Exception as exc:
        messagebox.showerror(
            "Import Failed",
            f"Foundry could not import packages.\n\n{exc}",
            parent=parent,
        )
        return ""

    summary = compose_package_import_summary(result)

    messagebox.showinfo(
        "Import Complete",
        summary,
        parent=parent,
    )

    return summary


def sync_packages_into_foundry(
    *,
    foundry_ui: Any,
    force: bool = False,
) -> dict[str, Any]:
    """Import old package records into Package Foundry through Workspace."""

    if foundry_ui is None:
        raise ValueError("foundry_ui is required.")

    create_callable = getattr(
        foundry_ui,
        "_create_package_foundry_blueprint_file",
        None,
    )
    if not callable(create_callable):
        raise AttributeError(
            "Workspace must expose _create_package_foundry_blueprint_file(...) "
            "before packages can be imported into Foundry."
        )

    package_root = OLD_PACKAGE_ROOT.expanduser().resolve()
    package_records = discover_package_records_from_filesystem(
        package_root=package_root,
    )

    now = utc_now_iso()

    result: dict[str, Any] = {
        "source": "one_time_old_package_import",
        "package_root": str(package_root),
        "force": bool(force),
        "import_timestamp": now,
        "scanned_count": len(package_records),
        "created": [],
        "updated": [],
        "skipped": [],
        "errors": [],
    }

    for package_record in package_records:
        try:
            item_result = sync_one_package_into_foundry(
                create_callable=create_callable,
                package_record=package_record,
                force=force,
            )
        except Exception as exc:
            result["errors"].append(
                {
                    "package_name": normalize_text(package_record.get("name", "")),
                    "record_path": normalize_text(package_record.get("__record_path__", "")),
                    "error": str(exc),
                }
            )
            continue

        status = normalize_text(item_result.get("status", ""))
        if status == "created":
            result["created"].append(item_result)
        elif status == "updated":
            result["updated"].append(item_result)
        elif status == "skipped":
            result["skipped"].append(item_result)
        else:
            result["errors"].append(item_result)

    return result


def sync_one_package_into_foundry(
    *,
    create_callable: Any,
    package_record: dict[str, Any],
    force: bool = False,
) -> dict[str, Any]:
    """Create one Package Foundry blueprint through Workspace."""

    if not isinstance(package_record, dict):
        raise ValueError("package_record must be a dictionary.")

    package_name = normalize_text(package_record.get("name", ""))
    if not package_name:
        raise ValueError("Package record is missing name.")

    blueprint_text = build_foundry_package_blueprint_from_package_record(
        package_record=package_record,
    )

    try:
        create_result = create_callable(
            package_name=package_name,
            blueprint_text=blueprint_text,
        )
    except FileExistsError as exc:
        if not force:
            return {
                "status": "skipped",
                "reason": str(exc),
                "package_name": package_name,
                "requested_package_name": package_name,
                "record_path": normalize_text(package_record.get("__record_path__", "")),
            }
        raise

    if not isinstance(create_result, dict):
        create_result = {}

    status = normalize_text(create_result.get("status", ""))
    if not status:
        status = "created"

    return {
        "status": status,
        "package_name": normalize_text(
            create_result.get("package_name", package_name),
        ),
        "requested_package_name": package_name,
        "blueprint_file": normalize_text(create_result.get("blueprint_file", "")),
        "record_path": normalize_text(package_record.get("__record_path__", "")),
        "workspace_result": create_result,
    }


# =============================================================================
# Package discovery
# =============================================================================


def discover_package_records_from_filesystem(
    *,
    package_root: Path,
) -> list[dict[str, Any]]:
    package_root = Path(package_root).expanduser().resolve()

    if not package_root.exists() or not package_root.is_dir():
        raise FileNotFoundError(f"Old package folder not found: {package_root}")

    candidate_paths: list[Path] = []

    candidate_paths.extend(package_root.rglob("*.package.json"))
    candidate_paths.extend(package_root.rglob("*.json"))

    results: list[dict[str, Any]] = []
    seen_paths: set[str] = set()

    for path in sorted(candidate_paths, key=lambda item: str(item).lower()):
        try:
            path = path.expanduser().resolve()
        except Exception:
            continue

        path_key = str(path).lower()
        if path_key in seen_paths:
            continue
        seen_paths.add(path_key)

        if not should_consider_package_json_path(path):
            continue

        try:
            data = load_json_object(path)
        except Exception:
            continue

        if not looks_like_package_record(data):
            continue

        record = dict(data)

        if not normalize_text(record.get("name", "")):
            fallback_name = path.name
            if fallback_name.lower().endswith(".package.json"):
                fallback_name = fallback_name[: -len(".package.json")]
            elif fallback_name.lower().endswith(".json"):
                fallback_name = fallback_name[: -len(".json")]
            record["name"] = fallback_name

        record["__record_path__"] = str(path)

        results.append(record)

    return dedupe_package_records(results)


def should_consider_package_json_path(path: Path) -> bool:
    name = path.name.lower()

    excluded_suffixes = (
        ".agent_foundry.json",
        ".metadata.json",
        "agent_index.json",
        "package_index.json",
        "task_index.json",
        "group_index.json",
    )

    if any(name.endswith(suffix) for suffix in excluded_suffixes):
        return False

    return name.endswith(".package.json") or name.endswith(".json")


def looks_like_package_record(data: Any) -> bool:
    if not isinstance(data, dict):
        return False

    name = normalize_text(data.get("name", ""))
    if not name:
        return False

    has_package_shape = any(
        key in data
        for key in (
            "required_replacements",
            "optional_replacements",
            "arguments",
            "returns",
            "recognitions",
            "logic",
        )
    )

    if not has_package_shape:
        return False

    logic = data.get("logic", "")
    if isinstance(logic, str) and logic.strip():
        return True

    if isinstance(logic, dict):
        logic_source = normalize_text(logic.get("logic_source", ""))
        if logic_source:
            return True

    if isinstance(data.get("arguments", None), list):
        return True

    if isinstance(data.get("returns", None), list):
        return True

    if isinstance(data.get("required_replacements", None), list):
        return True

    if isinstance(data.get("optional_replacements", None), list):
        return True

    if isinstance(data.get("recognitions", None), list):
        return True

    return False


def dedupe_package_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    seen_paths: set[str] = set()

    for record in records:
        if not isinstance(record, dict):
            continue

        name = normalize_text(record.get("name", ""))
        path_text = normalize_text(record.get("__record_path__", ""))

        if not name:
            continue

        name_key = name.lower()
        path_key = path_text.lower()

        if path_key and path_key in seen_paths:
            continue

        if name_key in seen_names:
            continue

        seen_names.add(name_key)
        if path_key:
            seen_paths.add(path_key)

        results.append(dict(record))

    return results


# =============================================================================
# Package blueprint composition
# =============================================================================


def build_foundry_package_blueprint_from_package_record(
    *,
    package_record: dict[str, Any],
) -> str:
    """Convert one package record into Package Foundry fenced blueprint text."""

    if not isinstance(package_record, dict):
        raise ValueError("package_record must be a dictionary.")

    package_name = normalize_text(package_record.get("name", ""))
    if not package_name:
        raise ValueError("Package record is missing name.")

    blocks: list[str] = []

    blocks.append(
        compose_fenced_list_block(
            heading=f"{package_name} {GRAMMAR_SUFFIX_PACKAGE_ID}",
            values=[package_name],
        )
    )

    append_replacement_collection_blocks(
        blocks=blocks,
        package_name=package_name,
        suffix=GRAMMAR_SUFFIX_REQUIRED_REPLACEMENT_LIST,
        replacements=normalize_list_of_dicts(
            package_record.get("required_replacements", [])
        ),
    )

    append_replacement_collection_blocks(
        blocks=blocks,
        package_name=package_name,
        suffix=GRAMMAR_SUFFIX_OPTIONAL_REPLACEMENT_LIST,
        replacements=normalize_list_of_dicts(
            package_record.get("optional_replacements", [])
        ),
    )

    append_package_logic_block(
        blocks=blocks,
        package_name=package_name,
        package_record=package_record,
    )

    append_argument_collection_blocks(
        blocks=blocks,
        package_name=package_name,
        arguments=normalize_list_of_dicts(package_record.get("arguments", [])),
    )

    append_return_collection_blocks(
        blocks=blocks,
        package_name=package_name,
        returns=normalize_list_of_dicts(package_record.get("returns", [])),
    )

    append_recognition_collection_blocks(
        blocks=blocks,
        package_name=package_name,
        recognitions=normalize_list_of_dicts(package_record.get("recognitions", [])),
    )

    return "\n\n".join(
        block.strip()
        for block in blocks
        if normalize_text(block)
    ).rstrip()


def append_package_logic_block(
    *,
    blocks: list[str],
    package_name: str,
    package_record: dict[str, Any],
) -> None:
    logic = package_record.get("logic", "")
    logic_source = ""

    if isinstance(logic, str):
        logic_source = normalize_multiline_text(logic)
    elif isinstance(logic, dict):
        logic_source = normalize_multiline_text(
            logic.get(
                "logic_source",
                logic.get("source", ""),
            )
        )

    if not logic_source:
        return

    blocks.append(
        compose_detail_block(
            heading=f"{package_name} {GRAMMAR_SUFFIX_PACKAGE_LOGIC}",
            body=logic_source,
        )
    )


def append_replacement_collection_blocks(
    *,
    blocks: list[str],
    package_name: str,
    suffix: str,
    replacements: list[dict[str, Any]],
) -> None:
    clean_suffix = normalize_text(suffix)
    if not clean_suffix or not replacements:
        return

    heading = f"{package_name} {clean_suffix}"

    replacement_names: list[str] = []
    for index, replacement in enumerate(replacements, start=1):
        replacement_name = resolve_replacement_name(replacement, index)
        if replacement_name:
            replacement_names.append(replacement_name)

    if not replacement_names:
        return

    blocks.append(
        compose_fenced_list_block(
            heading=heading,
            values=replacement_names,
        )
    )

    for index, replacement in enumerate(replacements, start=1):
        replacement_name = resolve_replacement_name(replacement, index)
        if not replacement_name:
            continue

        blocks.append(
            compose_detail_block(
                heading=f"{heading} {replacement_name}",
                body=compose_replacement_body(replacement),
            )
        )


def append_argument_collection_blocks(
    *,
    blocks: list[str],
    package_name: str,
    arguments: list[dict[str, Any]],
) -> None:
    if not arguments:
        return

    heading = f"{package_name} {GRAMMAR_SUFFIX_PACKAGE_ARGUMENT_LIST}"

    argument_names: list[str] = []
    for index, argument in enumerate(arguments, start=1):
        argument_name = resolve_argument_name(argument, index)
        if argument_name:
            argument_names.append(argument_name)

    if not argument_names:
        return

    blocks.append(
        compose_fenced_list_block(
            heading=heading,
            values=argument_names,
        )
    )

    for index, argument in enumerate(arguments, start=1):
        argument_name = resolve_argument_name(argument, index)
        if not argument_name:
            continue

        blocks.append(
            compose_detail_block(
                heading=f"{heading} {argument_name}",
                body=compose_argument_body(argument),
            )
        )


def append_return_collection_blocks(
    *,
    blocks: list[str],
    package_name: str,
    returns: list[dict[str, Any]],
) -> None:
    if not returns:
        return

    heading = f"{package_name} {GRAMMAR_SUFFIX_PACKAGE_RETURN_LIST}"

    return_names: list[str] = []
    for index, return_record in enumerate(returns, start=1):
        return_name = resolve_return_name(return_record, index)
        if return_name:
            return_names.append(return_name)

    if not return_names:
        return

    blocks.append(
        compose_fenced_list_block(
            heading=heading,
            values=return_names,
        )
    )

    for index, return_record in enumerate(returns, start=1):
        return_name = resolve_return_name(return_record, index)
        if not return_name:
            continue

        blocks.append(
            compose_detail_block(
                heading=f"{heading} {return_name}",
                body=compose_return_body(return_record),
            )
        )


def append_recognition_collection_blocks(
    *,
    blocks: list[str],
    package_name: str,
    recognitions: list[dict[str, Any]],
) -> None:
    if not recognitions:
        return

    heading = f"{package_name} {GRAMMAR_SUFFIX_PACKAGE_RECOGNITION_LIST}"

    recognition_names: list[str] = []
    for index, recognition in enumerate(recognitions, start=1):
        recognition_name = resolve_recognition_name(recognition, index)
        if recognition_name:
            recognition_names.append(recognition_name)

    if not recognition_names:
        return

    blocks.append(
        compose_fenced_list_block(
            heading=heading,
            values=recognition_names,
        )
    )

    for index, recognition in enumerate(recognitions, start=1):
        recognition_name = resolve_recognition_name(recognition, index)
        if not recognition_name:
            continue

        blocks.append(
            compose_detail_block(
                heading=f"{heading} {recognition_name}",
                body=compose_recognition_body(recognition),
            )
        )


def resolve_replacement_name(replacement: dict[str, Any], index: int) -> str:
    for key in (
        "anchor",
        "to_be_replaced",
        "name",
        "replacement_name",
    ):
        value = normalize_text(replacement.get(key, ""))
        if value:
            return value

    return f"replacement_{index:03d}"


def resolve_argument_name(argument: dict[str, Any], index: int) -> str:
    for key in (
        "argument_value_name",
        "argument_name",
        "name",
        "argument_question",
    ):
        value = normalize_text(argument.get(key, ""))
        if value:
            return value

    return f"argument_{index:03d}"


def resolve_return_name(return_record: dict[str, Any], index: int) -> str:
    for key in (
        "return_value_name",
        "return_name",
        "name",
    ):
        value = normalize_text(return_record.get(key, ""))
        if value:
            return value

    return f"return_{index:03d}"


def resolve_recognition_name(recognition: dict[str, Any], index: int) -> str:
    for key in (
        "recognition_name",
        "name",
        "recognition_kind",
        "recognition_text",
        "recognition_url",
    ):
        value = normalize_text(recognition.get(key, ""))
        if value:
            return value

    return f"recognition_{index:03d}"


def compose_replacement_body(replacement: dict[str, Any]) -> str:
    lines = [
        f"anchor: {stringify_scalar(replacement.get('anchor', ''))}",
        f"to_be_replaced: {stringify_scalar(replacement.get('to_be_replaced', ''))}",
    ]

    return "\n".join(lines).rstrip()


def compose_argument_body(argument: dict[str, Any]) -> str:
    lines = [
        f"argument_question: {stringify_scalar(argument.get('argument_question', ''))}",
        f"argument_value_name: {stringify_scalar(argument.get('argument_value_name', ''))}",
        f"argument_fallback: {stringify_scalar(argument.get('argument_fallback', ''))}",
        f"argument_hidden: {stringify_scalar(argument.get('argument_hidden', False))}",
    ]

    if "task_argument_mapping" in argument:
        append_json_field(
            lines=lines,
            label="task_argument_mapping_json",
            value=argument.get("task_argument_mapping", {}),
        )

    return "\n".join(lines).rstrip()


def compose_return_body(return_record: dict[str, Any]) -> str:
    lines = [
        f"return_value_name: {stringify_scalar(return_record.get('return_value_name', ''))}",
        f"return_description: {stringify_scalar(return_record.get('return_description', ''))}",
    ]

    if "return_value" in return_record:
        lines.append(
            f"return_value: {stringify_scalar(return_record.get('return_value', ''))}"
        )

    if "visible" in return_record:
        lines.append(f"visible: {stringify_scalar(return_record.get('visible', ''))}")

    if "friendship" in return_record:
        lines.append(
            f"friendship: {stringify_scalar(return_record.get('friendship', ''))}"
        )

    return "\n".join(lines).rstrip()


def compose_recognition_body(recognition: dict[str, Any]) -> str:
    lines = [
        f"recognition_name: {stringify_scalar(recognition.get('recognition_name', ''))}",
        f"recognition_text: {stringify_scalar(recognition.get('recognition_text', ''))}",
        f"recognition_url: {stringify_scalar(recognition.get('recognition_url', ''))}",
        f"recognition_kind: {stringify_scalar(recognition.get('recognition_kind', ''))}",
        f"propagate_to_outputs: {stringify_scalar(recognition.get('propagate_to_outputs', False))}",
    ]

    return "\n".join(lines).rstrip()


# =============================================================================
# Text / block helpers
# =============================================================================


def compose_fenced_list_block(
    *,
    heading: str,
    values: list[str],
) -> str:
    clean_heading = normalize_text(heading)
    if not clean_heading:
        return ""

    clean_values = unique_preserve_order(
        [
            normalize_text(value)
            for value in list(values or [])
            if normalize_text(value)
        ]
    )

    lines = [f"{clean_heading}:"]

    for value in clean_values:
        lines.append(f"- {value}")

    lines.append(f"End {clean_heading}")

    return "\n".join(lines).rstrip()


def compose_detail_block(
    *,
    heading: str,
    body: str,
) -> str:
    clean_heading = normalize_text(heading)
    if not clean_heading:
        return ""

    clean_body = normalize_multiline_text(body)

    lines = [f"{clean_heading}:"]
    if clean_body:
        lines.append(clean_body)
    lines.append(f"End {clean_heading}")

    return "\n".join(lines).rstrip()


def append_json_field(
    *,
    lines: list[str],
    label: str,
    value: Any,
) -> None:
    clean_label = normalize_text(label)
    if not clean_label:
        return

    lines.append(f"{clean_label}:")
    lines.append(stable_json(value))


def stable_json(value: Any) -> str:
    return json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    ).rstrip()


def normalize_multiline_text(value: object) -> str:
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def normalize_text(value: object) -> str:
    return str(value or "").strip()


def stringify_scalar(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, (list, dict)):
        return stable_json(value)

    return str(value)


def normalize_list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    return [
        dict(item)
        for item in value
        if isinstance(item, dict)
    ]


def unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []

    for value in values:
        clean_value = normalize_text(value)
        if not clean_value:
            continue

        key = clean_value.lower()
        if key in seen:
            continue

        seen.add(key)
        results.append(clean_value)

    return results


def load_json_object(path: str | Path) -> dict[str, Any]:
    source_path = Path(path).expanduser().resolve()

    try:
        data = json.loads(source_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON file is invalid: {source_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {source_path}")

    return data


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# =============================================================================
# Summary
# =============================================================================


def compose_package_import_summary(result: dict[str, Any]) -> str:
    if not isinstance(result, dict):
        return "Package import finished."

    scanned_count = int(result.get("scanned_count", 0) or 0)
    created = result.get("created", [])
    updated = result.get("updated", [])
    skipped = result.get("skipped", [])
    errors = result.get("errors", [])

    if not isinstance(created, list):
        created = []
    if not isinstance(updated, list):
        updated = []
    if not isinstance(skipped, list):
        skipped = []
    if not isinstance(errors, list):
        errors = []

    lines = [
        "Package Foundry import finished.",
        "",
        f"Package root: {normalize_text(result.get('package_root', ''))}",
        f"Scanned: {scanned_count}",
        f"Created: {len(created)}",
        f"Updated: {len(updated)}",
        f"Skipped: {len(skipped)}",
        f"Errors: {len(errors)}",
    ]

    if created:
        lines.append("")
        lines.append("Created packages:")
        for item in created[:20]:
            package_name = normalize_text(item.get("package_name", ""))
            lines.append(f"- {package_name}")

        if len(created) > 20:
            lines.append(f"- ...and {len(created) - 20} more")

    if updated:
        lines.append("")
        lines.append("Updated packages:")
        for item in updated[:20]:
            package_name = normalize_text(item.get("package_name", ""))
            lines.append(f"- {package_name}")

        if len(updated) > 20:
            lines.append(f"- ...and {len(updated) - 20} more")

    if skipped:
        lines.append("")
        lines.append("Skipped packages:")
        for item in skipped[:10]:
            package_name = normalize_text(item.get("package_name", ""))
            reason = normalize_text(item.get("reason", ""))

            if reason:
                lines.append(f"- {package_name}: {reason}")
            else:
                lines.append(f"- {package_name}")

        if len(skipped) > 10:
            lines.append(f"- ...and {len(skipped) - 10} more")

    if errors:
        lines.append("")
        lines.append("Errors:")
        for item in errors[:10]:
            package_name = normalize_text(item.get("package_name", ""))
            error = normalize_text(item.get("error", ""))
            lines.append(f"- {package_name}: {error}")

        if len(errors) > 10:
            lines.append(f"- ...and {len(errors) - 10} more")

    return "\n".join(lines).rstrip()

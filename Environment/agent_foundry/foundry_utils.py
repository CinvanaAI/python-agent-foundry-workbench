from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import tkinter as tk
from typing import Any


class AgentFoundryUtilsMixin:
    def _set_foundry_section_text(self, section_key: str, text: str) -> None:
        clean_section_key = str(section_key or "").strip()
        if not clean_section_key:
            return

        text_box = self.agent_foundry_section_texts.get(clean_section_key)
        if text_box is None:
            return

        self._set_text_widget_value(text_box, str(text or ""))

    def _set_text_widget_value(self, text_widget: tk.Text, text: str) -> None:
        original_state = str(text_widget.cget("state"))

        if original_state == "disabled":
            text_widget.configure(state="normal")

        text_widget.delete("1.0", tk.END)
        text_widget.insert("1.0", str(text or ""))
        text_widget.edit_modified(False)

        if original_state == "disabled":
            text_widget.configure(state="disabled")

    def _set_agent_foundry_status(self, message: str) -> None:
        return None

    def _shorten_foundry_tab_title(self, title: str) -> str:
        clean_title = str(title or "").strip()
        if not clean_title:
            return "Item"

        if len(clean_title) <= 24:
            return clean_title

        return clean_title[:21].rstrip() + "..."

    def _unique_preserve_order(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        results: list[str] = []

        for value in values:
            clean_value = str(value or "").strip()
            if not clean_value:
                continue

            identity = clean_value.lower()
            if identity in seen:
                continue

            seen.add(identity)
            results.append(clean_value)

        return results

    def _find_exact_fenced_block(
        self,
        *,
        source_text: str,
        start_heading: str,
        end_heading: str,
    ) -> dict[str, Any] | None:
        matches = self._find_all_exact_fenced_blocks(
            source_text=source_text,
            start_heading=start_heading,
            end_heading=end_heading,
        )

        if not matches:
            return None

        return matches[0]

    def _find_all_exact_fenced_blocks(
        self,
        *,
        source_text: str,
        start_heading: str,
        end_heading: str,
    ) -> list[dict[str, Any]]:
        source = str(source_text or "")
        clean_start_heading = str(start_heading or "").strip()
        clean_end_heading = str(end_heading or "").strip()

        if not clean_start_heading or not clean_end_heading:
            return []

        results: list[dict[str, Any]] = []

        for start_match in re.finditer(
            rf"(?im)^\s*{re.escape(clean_start_heading)}\s*:\s*$",
            source,
        ):
            end_match = re.search(
                rf"(?im)^\s*{re.escape(clean_end_heading)}\s*$",
                source[start_match.end():],
            )
            if not end_match:
                continue

            inner_start = start_match.end()
            inner_end = start_match.end() + end_match.start()
            block_end = start_match.end() + end_match.end()

            results.append(
                {
                    "text": source[start_match.start():block_end].strip(),
                    "inner_text": source[inner_start:inner_end].strip(),
                    "range": (start_match.start(), block_end),
                    "start_heading": clean_start_heading,
                    "end_heading": clean_end_heading,
                }
            )

        return results

    def _extract_fenced_list_items(
        self,
        *,
        source_text: str,
        start_heading: str,
        end_heading: str,
        strict: bool = True,
    ) -> list[str]:
        block = self._find_exact_fenced_block(
            source_text=source_text,
            start_heading=start_heading,
            end_heading=end_heading,
        )
        if block is None:
            return []

        inner_text = str(block.get("inner_text", "") or "")
        return self._extract_bullet_items_from_fence_inner_text(
            inner_text,
            strict=strict,
        )

    def _extract_bullet_items_from_fence_inner_text(
        self,
        inner_text: str,
        *,
        strict: bool = True,
    ) -> list[str]:
        results: list[str] = []

        for raw_line in str(inner_text or "").splitlines():
            line = str(raw_line or "").strip()
            if not line:
                continue

            bullet_match = re.match(r"^[-*]\s+(?P<value>.*)$", line)
            if not bullet_match:
                if strict:
                    return []
                continue

            value = str(bullet_match.group("value") or "").strip()
            if value:
                results.append(value)

        return results

    def _find_named_detail_block_records(
        self,
        *,
        source_text: str,
        marker: str,
        require_end_marker: bool = False,
    ) -> list[dict[str, Any]]:
        source = str(source_text or "")
        clean_marker = str(marker or "").strip()
        if not clean_marker:
            return []

        start_matches = list(
            re.finditer(
                rf"(?im)^\s*{re.escape(clean_marker)}\s*:\s*(?P<name>.+?)\s*$",
                source,
            )
        )
        if not start_matches:
            return []

        records: list[dict[str, Any]] = []

        for index, start_match in enumerate(start_matches):
            item_name = str(start_match.group("name") or "").strip()
            if not item_name:
                continue

            end_pattern = re.compile(
                rf"(?im)^\s*End\s+{re.escape(clean_marker)}\s*:\s*{re.escape(item_name)}\s*$"
            )
            end_match = re.search(end_pattern, source[start_match.end():])

            if end_match:
                block_end = start_match.end() + end_match.end()
                body_start = start_match.end()
                body_end = start_match.end() + end_match.start()
                inner_text = source[body_start:body_end].strip()
            elif require_end_marker:
                continue
            else:
                if index + 1 < len(start_matches):
                    block_end = start_matches[index + 1].start()
                else:
                    block_end = len(source)

                inner_text = source[start_match.end():block_end].strip()

            block_text = source[start_match.start():block_end].strip()

            records.append(
                {
                    "name": item_name,
                    "text": block_text,
                    "inner_text": inner_text,
                    "range": (start_match.start(), block_end),
                    "marker": clean_marker,
                }
            )

        return records

    def _extract_named_child_blocks_by_allowed_names(
        self,
        *,
        source_text: str,
        allowed_names: list[str],
    ) -> dict[str, str]:
        source = str(source_text or "").strip()
        allowed = [
            str(name or "").strip()
            for name in allowed_names
            if str(name or "").strip()
        ]

        if not source or not allowed:
            return {}

        blocks: dict[str, str] = {}

        for child_name in allowed:
            start_match = re.search(
                rf"(?im)^\s*{re.escape(child_name)}\s*$",
                source,
            )
            if not start_match:
                continue

            end_match = re.search(
                rf"(?im)^\s*End\s+{re.escape(child_name)}\s*$",
                source[start_match.end():],
            )

            if end_match:
                body_start = start_match.end()
                body_end = start_match.end() + end_match.start()
                body_text = source[body_start:body_end].strip()
            else:
                body_start = start_match.end()
                next_match = self._find_next_allowed_heading_match(
                    source_text=source,
                    search_start=body_start,
                    allowed_names=allowed,
                    current_name=child_name,
                )
                body_end = next_match.start() if next_match is not None else len(source)
                body_text = source[body_start:body_end].strip()

            blocks[child_name.lower()] = body_text

        return blocks

    def _find_next_allowed_heading_match(
        self,
        *,
        source_text: str,
        search_start: int,
        allowed_names: list[str],
        current_name: str,
    ):
        matches: list[tuple[int, Any]] = []

        for allowed_name in allowed_names:
            clean_allowed_name = str(allowed_name or "").strip()
            if not clean_allowed_name:
                continue

            if clean_allowed_name.lower() == str(current_name or "").strip().lower():
                continue

            match = re.search(
                rf"(?im)^\s*{re.escape(clean_allowed_name)}\s*$",
                str(source_text or "")[search_start:],
            )
            if match:
                matches.append((search_start + match.start(), match))

        if not matches:
            return None

        matches.sort(key=lambda item: item[0])
        return matches[0][1]

    def _collect_unclaimed_text(
        self,
        *,
        source_text: str,
        claimed_ranges: list[tuple[int, int]],
    ) -> str:
        source = str(source_text or "")

        if not source.strip():
            return ""

        if not claimed_ranges:
            return source.strip()

        merged_ranges = self._merge_ranges(claimed_ranges)

        chunks: list[str] = []
        cursor = 0

        for start, end in merged_ranges:
            if cursor < start:
                chunk = source[cursor:start].strip()
                if chunk:
                    chunks.append(chunk)
            cursor = max(cursor, end)

        if cursor < len(source):
            chunk = source[cursor:].strip()
            if chunk:
                chunks.append(chunk)

        return "\n\n".join(chunks).rstrip()

    def _merge_ranges(self, ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
        clean_ranges = sorted(
            [
                (int(start), int(end))
                for start, end in list(ranges or [])
                if int(end) > int(start)
            ],
            key=lambda item: item[0],
        )

        if not clean_ranges:
            return []

        merged: list[tuple[int, int]] = [clean_ranges[0]]

        for start, end in clean_ranges[1:]:
            last_start, last_end = merged[-1]

            if start <= last_end:
                merged[-1] = (last_start, max(last_end, end))
            else:
                merged.append((start, end))

        return merged

    def _load_agent_foundry_module(self, module_name: str, module_path: Path):
        resolved_module_path = Path(module_path).resolve()

        if not resolved_module_path.exists():
            raise FileNotFoundError(f"Agent Foundry script not found: {resolved_module_path}")

        if not resolved_module_path.is_file():
            raise ValueError(f"Agent Foundry script path is not a file: {resolved_module_path}")

        spec = importlib.util.spec_from_file_location(
            module_name,
            resolved_module_path,
        )

        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load module from: {resolved_module_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        return module

    def _get_agent_foundry_collection_handoff(self):
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
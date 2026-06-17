"""Loader/parser for Docs/FOLK_Agent_Prompts_v2.md.

Extracts the shared preamble and per-role / per-phase prompt blocks so the
council, judges, and narrative engine can assemble calls. Token injection uses
the {{TOKEN}} placeholders documented in the file's Section 0.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from folk.config import get_settings
from folk.models.enums import AgentRole, JudgeRole

_FENCE = re.compile(r"```[a-zA-Z]*\n(.*?)```", re.DOTALL)
_HEADING = re.compile(r"^#{2,4}\s+(.*)$")


def _bucket_for(title: str) -> str | None:
    t = title.lower()
    if "shared_system_preamble" in t:
        return "preamble"
    if "narrative validator" in t:
        return "narrative_validator"
    if "narrative engine" in t:
        return "narrative"
    if "methodology judge" in t:
        return JudgeRole.METHODOLOGY.value
    if "cultural validity judge" in t:
        return JudgeRole.CULTURAL_VALIDITY.value
    if "statistician" in t:
        return AgentRole.STATISTICIAN.value
    if "comparativist" in t:
        return AgentRole.COMPARATIVIST.value
    if "country specialist" in t:
        return AgentRole.COUNTRY_SPECIALIST.value
    if "devil's advocate" in t or "devils advocate" in t:
        return AgentRole.DEVILS_ADVOCATE.value
    if "integrator" in t:
        return AgentRole.INTEGRATOR.value
    if "extension country protocol" in t:
        return "extension"
    return None


class PromptLibrary:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or get_settings().prompts_path
        self._blocks: dict[str, list[str]] = self._parse()

    def _parse(self) -> dict[str, list[str]]:
        text = self.path.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        blocks: dict[str, list[str]] = {}
        # Slice the document into heading-delimited sections, then capture the
        # fenced code blocks inside each section that maps to a known bucket.
        section_title: str | None = None
        section_start = 0
        spans: list[tuple[str, int, int]] = []
        for idx, line in enumerate(lines):
            hm = _HEADING.match(line)
            if hm:
                if section_title is not None:
                    spans.append((section_title, section_start, idx))
                section_title = hm.group(1).strip()
                section_start = idx
        if section_title is not None:
            spans.append((section_title, section_start, len(lines)))

        for title, start, end in spans:
            bucket = _bucket_for(title)
            if bucket is None:
                continue
            chunk = "".join(lines[start:end])
            found = [m.group(1).strip() for m in _FENCE.finditer(chunk)]
            if found:
                blocks.setdefault(bucket, []).extend(found)
        return blocks

    # ------------------------------------------------------------------ #
    def preamble(self) -> str:
        b = self._blocks.get("preamble")
        return b[0] if b else "You are a member of the FOLK AI Council. Respond with JSON only."

    def agent_prompt(self, role: AgentRole, phase: int) -> str:
        blocks = self._blocks.get(role.value, [])
        if not blocks:
            return f"Act as the {role.value}. Respond with valid JSON only."
        idx = min(max(phase - 1, 0), len(blocks) - 1)
        return blocks[idx]

    def judge_prompt(self, role: JudgeRole) -> str:
        blocks = self._blocks.get(role.value, [])
        return blocks[0] if blocks else f"Act as the {role.value} judge. Respond with JSON only."

    def narrative_prompt(self) -> str:
        b = self._blocks.get("narrative")
        return b[0] if b else "Write the country narrative as JSON only."

    def narrative_validator_prompt(self) -> str:
        b = self._blocks.get("narrative_validator")
        return b[0] if b else "Validate the narrative. Respond with JSON only."

    def extension_addendum(self) -> str:
        b = self._blocks.get("extension")
        return b[0] if b else ""


@lru_cache
def get_prompt_library(path_str: str | None = None) -> PromptLibrary:
    return PromptLibrary(Path(path_str) if path_str else None)

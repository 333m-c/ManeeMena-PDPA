"""Shared rule metadata and replacements; no web or file-system dependencies."""

from dataclasses import dataclass
import re
from typing import Callable


@dataclass(frozen=True)
class Edit:
    """A replacement inside a regex match, using Unicode code-point offsets."""

    start: int
    end: int
    replacement: str


def group_edit(match: re.Match, group: str, replacement: str) -> Edit:
    return Edit(match.start(group) - match.start(), match.end(group) - match.start(), replacement)


@dataclass(frozen=True)
class Rule:
    key: str
    label: str
    pattern: re.Pattern
    description: str
    tokens: tuple[tuple[str, str], ...]
    sample: str
    edits: Callable[[re.Match], tuple[Edit, ...]]

    def replace(self, match: re.Match) -> str:
        source = match.group()
        pieces = []
        cursor = 0
        for edit in self.edits(match):
            pieces.extend((source[cursor:edit.start], edit.replacement))
            cursor = edit.end
        pieces.append(source[cursor:])
        return "".join(pieces)

    def mask(self, text: str) -> str:
        return self.pattern.sub(self.replace, text)

    def public(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "pattern": self.pattern.pattern,
            "description": self.description,
            "tokens": [{"syntax": syntax, "meaning": meaning} for syntax, meaning in self.tokens],
            "sample": self.sample,
        }


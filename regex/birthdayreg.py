"""Reuse DOB's two-digit year prefix, without import-time file operations."""

import re
from .rule import Rule, group_edit

# Horizontal whitespace only: a label must not consume the next log line.
PATTERN = re.compile(r"(?<!\w)DOB:[ \t]*(?P<day>[0-9]{2})/(?P<month>[0-9]{2})/(?P<century>[0-9]{2})(?P<year_end>[0-9]{2})(?![\w/])")


def _edits(match):
    return tuple(group_edit(match, group, "XX") for group in ("day", "month", "year_end"))


RULE = Rule(
    "dob", "Date of Birth", PATTERN,
    "Match DD/MM/YYYY only after the case-sensitive DOB: label. Keep spacing, slashes and the year's first two digits. The rule checks a date format, not calendar validity or the calendar system.",
    ((r"(?<!\w)", "The label must not be part of a larger word."),
     ("DOB:", "The exact, case-sensitive label."),
     (r"[ \t]*", "Zero or more spaces or tabs, without crossing a line break."),
     ("(?P<day>[0-9]{2})", "Capture exactly two digits for the day; similarly for month and year parts."),
     ("/", "Preserve literal date separators."),
     (r"(?![\w/])", "Prevent matching the beginning of a longer date-like value.")),
    "DOB: 25/12/2549", _edits,
)


def mask_dob(text):
    return RULE.mask(text)

"""Reuse DOB's two-digit year prefix, without import-time file operations."""

import re
from .rule import Rule, Step, group_edit, literal

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
    (Step(r"(?<!\w)", "Left boundary: the label may not sit inside a longer word.", guard=True),
     *literal("DOB:", "A character of the case-sensitive label DOB:"),
     Step(r"[ \t]", "Spaces or tabs, any number of them, but never a line break.", loop=True, optional=True),
     Step("[0-9]", "Day digit, replaced with X.", times=2, masked=True, row=True),
     Step(r"\/", "Literal date separator, kept in the output."),
     Step("[0-9]", "Month digit, replaced with X.", times=2, masked=True, row=True),
     Step(r"\/", "Literal date separator, kept in the output."),
     Step("[0-9]", "Century digit, kept so the era stays readable.", times=2, row=True),
     Step("[0-9]", "Year digit, replaced with X.", times=2, masked=True),
     Step(r"(?![\w/])", "Right boundary: stops a longer date-like value from matching.", guard=True)),
)


def mask_dob(text):
    return RULE.mask(text)

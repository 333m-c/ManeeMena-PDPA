"""Extend the original phone exercise to the assignment's hyphenated format."""

import re
from .rule import Rule, Step, group_edit

PATTERN = re.compile(r"(?<![\w-])(?P<first>[0-9]{3})-(?P<second>[0-9]{3})-(?P<last>[0-9]{4})(?![\w-])")


def _edits(match):
    return tuple(group_edit(match, group, "XXX") for group in ("first", "second"))


RULE = Rule(
    "phone", "Phone Number", PATTERN,
    "Match the assignment's 3-3-4 digit format anywhere in a log. Hide the first six digits and keep the last four. Unformatted numbers are outside this rule.",
    ((r"(?<![\w-])", "Prevent a match inside a word or longer hyphenated number."),
     ("[0-9]{3}", "Exactly three ASCII digits."),
     ("(?P<last>[0-9]{4})", "Capture the four digits that stay visible."),
     (r"(?![\w-])", "Require the complete number to end here.")),
    "Phone: 093-245-7894", _edits,
    (Step(r"(?<![\w-])", "Left boundary: no word character or hyphen before the number.", guard=True),
     Step("[0-9]", "Area digit, replaced with X.", times=3, masked=True),
     Step(r"\-", "Literal hyphen, kept in the output.", row=True),
     Step("[0-9]", "Prefix digit, replaced with X.", times=3, masked=True),
     Step(r"\-", "Literal hyphen, kept in the output.", row=True),
     Step("[0-9]", "Line digit, the four that stay visible.", times=4),
     Step(r"(?![\w-])", "Right boundary: the number has to end here.", guard=True)),
)


def mask_phone(text):
    return RULE.mask(text)

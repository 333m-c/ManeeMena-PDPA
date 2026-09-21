"""Reuse the original four groups and preserve the final four digits."""

import re
from .rule import Rule, Step, group_edit

PATTERN = re.compile(r"(?<![\w-])(?P<first>[0-9]{4})-(?P<second>[0-9]{4})-(?P<third>[0-9]{4})-(?P<last>[0-9]{4})(?![\w-])")


def _edits(match):
    return tuple(group_edit(match, group, "XXXX") for group in ("first", "second", "third"))


RULE = Rule(
    "credit_card", "Credit Card", PATTERN,
    "Match four groups of four digits separated by hyphens. Hide the first three groups; keep the final four digits. This checks the format, not card validity.",
    ((r"(?<![\w-])", "Do not start inside a word or a longer hyphenated number."),
     ("[0-9]{4}", "Exactly four ASCII digits."),
     ("(?P<first>...)", "Name a capture group so its location can be masked."),
     ("-", "A literal hyphen, preserved in the result."),
     (r"(?![\w-])", "Do not end inside a word or a longer hyphenated number.")),
    "Card: 1234-5678-9012-3456", _edits,
    (Step(r"(?<![\w-])", "Left boundary: the match may not start inside a word or a longer hyphenated number.", guard=True),
     Step("[0-9]", "Group 1 digit, replaced with X.", times=4, masked=True),
     Step(r"\-", "Literal hyphen, kept in the output.", row=True),
     Step("[0-9]", "Group 2 digit, replaced with X.", times=4, masked=True),
     Step(r"\-", "Literal hyphen, kept in the output.", row=True),
     Step("[0-9]", "Group 3 digit, replaced with X.", times=4, masked=True),
     Step(r"\-", "Literal hyphen, kept in the output.", row=True),
     Step("[0-9]", "Group 4 digit, the four that stay visible.", times=4),
     Step(r"(?![\w-])", "Right boundary: the number has to end here.", guard=True)),
)


def mask_credit_card(text):
    return RULE.mask(text)

"""Keep the original house-number rule without requiring a full Thai address."""

import re
from .rule import Rule, group_edit

PATTERN = re.compile(r"(?<!\w)Address:[ \t]*(?P<house>[0-9]+(?:/[0-9]+)?)(?![\w/\-])")


def _edits(match):
    return (group_edit(match, "house", "XXX"),)


RULE = Rule(
    "address", "Address", PATTERN,
    "Replace only the house number immediately after Address: with XXX. Support plain numbers and numbers such as 99/12. Keep all street, district and province text unchanged.",
    ((r"(?<!\w)", "The label must not be part of a larger word."),
     (r"Address:[ \t]*", "The exact label followed by optional horizontal whitespace."),
     ("[0-9]+", "One or more digits in the house number."),
     ("(?:/[0-9]+)?", "An optional slash and more digits; ?: is a noncapturing group and ? makes it optional."),
     ("(?P<house>...)", "Capture only the house number for replacement."),
     (r"(?![\w/\-])", "Do not hide just a prefix of a longer house-number token.")),
    "Address: 99/12 ถนนสุขุมวิท เขตวัฒนา กรุงเทพฯ", _edits,
)


def mask_address(text):
    return RULE.mask(text)


def censor_house_number(inp):
    """Compatibility helper; unmatched text now passes through unchanged."""
    return mask_address(inp)

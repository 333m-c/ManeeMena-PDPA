"""Keep the original house-number rule without requiring a full Thai address."""

import re
from .rule import Edit, Maybe, Rule, Step, literal

PATTERN = re.compile(r"(?<!\w)Address:[ \t]*(?P<house>[0-9]+(?:/[0-9]+)?)(?![\w/\-])")


def _edits(match):
    """One X per digit, so the masked number keeps its original length.

    Each run of digits is its own edit, which leaves the slash of a number such
    as 99/12 visible and out of the masked-character count, the way the card,
    phone and date rules already treat their separators.
    """
    offset = match.start("house") - match.start()
    return tuple(Edit(offset + run.start(), offset + run.end(), "X" * (run.end() - run.start()))
                 for run in re.finditer("[0-9]+", match.group("house")))


RULE = Rule(
    "address", "Address", PATTERN,
    "Replace each digit of the house number immediately after Address: with one X, so 689 becomes XXX and 99/12 becomes XX/XX. Keep the slash, and all street, district and province text, unchanged.",
    ((r"(?<!\w)", "The label must not be part of a larger word."),
     (r"Address:[ \t]*", "The exact label followed by optional horizontal whitespace."),
     ("[0-9]+", "One or more digits in the house number."),
     ("(?:/[0-9]+)?", "An optional slash and more digits; ?: is a noncapturing group and ? makes it optional."),
     ("(?P<house>...)", "Capture only the house number; each digit in it becomes one X."),
     (r"(?![\w/\-])", "Do not hide just a prefix of a longer house-number token.")),
    "Address: 99/12 ถนนสุขุมวิท เขตวัฒนา กรุงเทพฯ", _edits,
    (Step(r"(?<!\w)", "Left boundary: the label may not sit inside a longer word.", guard=True),
     *literal("Address:", "A character of the case-sensitive label Address:", wrap=4),
     Step(r"[ \t]", "Spaces or tabs, any number of them, but never a line break.", loop=True, optional=True),
     Step("[0-9]", "House-number digit, replaced with one X.", loop=True, masked=True, row=True),
     Maybe((Step(r"\/", "The slash of a number such as 99/12."),
            Step("[0-9]", "Digit after the slash, also one X each.", loop=True, masked=True)),
           "Numbers such as 689 skip the slash part entirely."),
     Step(r"(?![\w/\-])", "Right boundary: stops a prefix of a longer token from matching.", guard=True)),
)


def mask_address(text):
    return RULE.mask(text)


def censor_house_number(inp):
    """Compatibility helper; unmatched text now passes through unchanged."""
    return mask_address(inp)

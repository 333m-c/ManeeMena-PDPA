"""Mask the house number only when the full Thai address format is present."""

import re
from .rule import Edit, Maybe, Rule, Step, literal


PATTERN = re.compile(
    r"(?<![\w/\-])Address:[ \t]*"
    r"(?P<house>[0-9]+(?:/[0-9]+)?)[ \t]+"
    r"(?:ซอย[ \t]*[\u0E00-\u0E7F]+(?:[ \t]+[0-9]+)?[ \t]+)?"
    r"ถนน[ \t]*[\u0E00-\u0E7F]+[ \t]+"
    r"(?:แขวง|ตำบล)[ \t]*[\u0E00-\u0E7F]+[ \t]+"
    r"(?:เขต|อำเภอ)[ \t]*[\u0E00-\u0E7F]+"
    r"(?:[ \t]*จังหวัด)?[ \t]+"
    r"[\u0E00-\u0E7F]+"
)


def _edits(match):
    """Mask each digit of the house number while keeping separators unchanged."""
    offset = match.start("house") - match.start()

    return tuple(
        Edit(
            offset + run.start(),
            offset + run.end(),
            "X" * (run.end() - run.start())
        )
        for run in re.finditer("[0-9]+", match.group("house"))
    )


RULE = Rule(
    "address",
    "Address",
    PATTERN,
    "Replace each digit of the house number only when the text matches the full Thai address format. Keep the slash in house numbers such as 99/12 and keep the rest of the address unchanged.",
    (
        (r"(?<!\w)", "The label must not be part of a larger word."),
        (r"Address:[ \t]*", "The address must start with the exact label Address: followed by optional horizontal whitespace."),
        ("[0-9]+", "One or more digits in the house number."),
        ("(?:/[0-9]+)?", "An optional slash followed by more digits."),
        ("[ \t]+", "Whitespace separating the house number from the address."),
        ("(?:ซอย ...)?", "An optional soi followed by a Thai name and optional soi number."),
        ("ถนน ...", "The address must contain a road name."),
        ("(?:แขวง|ตำบล) ...", "The address must contain a subdistrict."),
        ("(?:เขต|อำเภอ) ...", "The address must contain a district."),
        ("(?:จังหวัด)? ...", "The province label is optional, but the province name is required."),
        (r"(?![\w/\-])", "Do not match only a prefix of a longer address token."),
    ),
    "Address: 99/12 ซอยสุขุมวิท 12 ถนนสุขุมวิท แขวงคลองตัน เขตคลองเตย กรุงเทพฯ",
    _edits,
    (
        Step(
            r"(?<!\w)",
            "Left boundary: Address: may not be inside a larger word.",
            guard=True
        ),
        *literal(
            "Address:",
            "A character of the case-sensitive label Address:",
            wrap=4
        ),
        Step(
            r"[ \t]",
            "Spaces or tabs after Address:",
            loop=True,
            optional=True
        ),
        Step(
            "[0-9]",
            "House-number digit, replaced with one X.",
            loop=True,
            masked=True,
            row=True
        ),
        Maybe(
            (
                Step(
                    r"\/",
                    "The slash of a number such as 99/12."
                ),
                Step(
                    "[0-9]",
                    "Digit after the slash, also replaced with X.",
                    loop=True,
                    masked=True
                ),
            ),
            "Numbers such as 689 do not contain the optional slash part."
        ),
        Step(
            r"[ \t]+",
            "Whitespace separating the house number from the rest of the address.",
            loop=True
        ),
        Step(
            r".+",
            "The remaining address must contain soi (optional), road, subdistrict, district and province."
        ),
        Step(
            r"(?![\w/\-])",
            "Right boundary: prevents matching only part of a longer token.",
            guard=True
        ),
    ),
)


def mask_address(text):
    return RULE.mask(text)


def censor_house_number(inp):
    """Compatibility helper; unmatched text passes through unchanged."""
    return mask_address(inp)
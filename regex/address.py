"""Mask the house number only when the full Thai address format is present."""

import re
from .rule import Choice, Edit, Maybe, Rule, Step, literal


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
            r"(?<![\w/\-])",
            "Left boundary: Address: may not follow a word character, slash or hyphen.",
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
            r"[ \t]",
            "Whitespace separating the house number from the rest of the address.",
            loop=True
        ),
        Maybe(
            (
                *literal("ซอย", "A character of the optional soi label.", row=True),
                Step(r"[ \t]", "Spaces or tabs after the soi label.", loop=True, optional=True),
                Step(r"[\u0E00-\u0E7F]", "Thai character in the soi name.", loop=True),
                Maybe(
                    (
                        Step(r"[ \t]", "Whitespace before the soi number.", loop=True, row=True),
                        Step("[0-9]", "Soi-number digit, kept in the output.", loop=True),
                    ),
                    "The soi number may be absent."
                ),
                Step(r"[ \t]", "Whitespace after the soi.", loop=True),
            ),
            "The entire soi may be absent."
        ),
        *literal("ถนน", "A character of the required road label.", row=True),
        Step(r"[ \t]", "Spaces or tabs after the road label.", loop=True, optional=True),
        Step(r"[\u0E00-\u0E7F]", "Thai character in the road name.", loop=True),
        Step(r"[ \t]", "Whitespace after the road name.", loop=True),
        Choice(
            (
                literal("แขวง", "A character of the subdistrict label แขวง."),
                literal("ตำบล", "A character of the subdistrict label ตำบล."),
            ),
            "The subdistrict label is either แขวง or ตำบล."
        ),
        Step(r"[ \t]", "Spaces or tabs after the subdistrict label.", loop=True, optional=True),
        Step(r"[\u0E00-\u0E7F]", "Thai character in the subdistrict name.", loop=True),
        Step(r"[ \t]", "Whitespace after the subdistrict name.", loop=True),
        Choice(
            (
                literal("เขต", "A character of the district label เขต."),
                literal("อำเภอ", "A character of the district label อำเภอ."),
            ),
            "The district label is either เขต or อำเภอ."
        ),
        Step(r"[ \t]", "Spaces or tabs after the district label.", loop=True, optional=True),
        Step(r"[\u0E00-\u0E7F]", "Thai character in the district name.", loop=True),
        Maybe(
            (
                Step(r"[ \t]", "Spaces or tabs before the province label.", loop=True, optional=True, row=True),
                *literal("จังหวัด", "A character of the optional province label.", wrap=4),
            ),
            "The province label and its preceding whitespace may be absent."
        ),
        Step(r"[ \t]", "Required whitespace before the province name.", loop=True, row=True),
        Step(r"[\u0E00-\u0E7F]", "Thai character in the required province name.", loop=True),
    ),
)


def mask_address(text):
    return RULE.mask(text)


def censor_house_number(inp):
    """Compatibility helper; unmatched text passes through unchanged."""
    return mask_address(inp)

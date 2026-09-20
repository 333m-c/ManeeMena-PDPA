"""Detect once on the original text, then build output and consistent metadata."""

from bisect import bisect_right
import re

from .address import RULE as ADDRESS
from .birthdayreg import RULE as DOB
from .creditcardreg import RULE as CREDIT_CARD
from .gmailreg import RULE as EMAIL
from .phonereg import RULE as PHONE

RULES = (CREDIT_CARD, EMAIL, PHONE, DOB, ADDRESS)
RULE_MAP = {rule.key: rule for rule in RULES}


def mask_text(text: str, enabled_rules=None) -> dict:
    """Return JSON-ready results. All offsets are Unicode code points, end-exclusive.

    Overlaps are resolved leftmost first, longest at the same position. This
    makes a card-shaped email username one email detection rather than two.
    Rules disabled by the caller do not participate in detection or risk counts.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    enabled = set(RULE_MAP if enabled_rules is None else enabled_rules)
    if enabled - RULE_MAP.keys():
        raise ValueError("Unknown masking rule")

    candidates = []
    for rule in RULES:
        if rule.key in enabled:
            candidates.extend((match.start(), match.end(), rule, match)
                              for match in rule.pattern.finditer(text))
    candidates.sort(key=lambda item: (item[0], -(item[1] - item[0])))

    line_starts = [0] + [match.end() for match in re.finditer(r"\r\n|\r|\n", text)]
    counts = dict.fromkeys(RULE_MAP, 0)
    detections, pieces = [], []
    cursor = output_length = masked_characters = 0
    for start, end, rule, match in candidates:
        if start < cursor:
            continue
        prefix = text[cursor:start]
        pieces.append(prefix)
        output_length += len(prefix)
        # The replacement is performed by the same re.sub rule used by the
        # standalone helpers. Metadata is derived from its exact capture spans.
        replacement = rule.mask(match.group())
        changes = []
        delta = 0
        for edit in rule.edits(match):
            output_start = output_length + edit.start + delta
            changes.append({"start": start + edit.start, "end": start + edit.end,
                            "output_start": output_start,
                            "output_end": output_start + len(edit.replacement)})
            masked_characters += edit.end - edit.start
            delta += len(edit.replacement) - (edit.end - edit.start)
        detections.append({
            "id": len(detections), "rule": rule.key,
            "start": start, "end": end,
            "output_start": output_length, "output_end": output_length + len(replacement),
            "line": bisect_right(line_starts, start),
            "masked_preview": replacement, "changes": changes,
        })
        counts[rule.key] += 1
        pieces.append(replacement)
        output_length += len(replacement)
        cursor = end
    pieces.append(text[cursor:])
    return {"masked_text": "".join(pieces), "total_detected": len(detections),
            "counts": counts, "detections": detections,
            "masked_characters": masked_characters}

"""Reuse the original email character classes and first/last-character policy."""

import re
from .rule import Edit, Rule, Step

# The left guard also excludes '*', so already-masked usernames are not
# reinterpreted as a shorter email starting after the masking characters.
PATTERN = re.compile(r"(?<![A-Za-z0-9._%+@*\-])(?P<username>[A-Za-z0-9._%+\-]+)@(?P<domain>[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![A-Za-z0-9_@\-])")


def _edits(match):
    length = len(match.group("username"))
    if length <= 2:
        return ()
    return (Edit(1, length - 1, "*" * (length - 2)),)


RULE = Rule(
    "email", "Email Address", PATTERN,
    "Keep the username's first and last characters and the whole domain. Replace each middle character with *. One- and two-character usernames remain unchanged under this assignment policy.",
    ((r"(?<![A-Za-z0-9._%+@*\-])", "Avoid matching a suffix of an email, including an already-masked one."),
     (r"[A-Za-z0-9._%+\-]+", "One or more allowed username characters; + means one or more."),
     ("(?P<username>...)", "Capture the username for masking."),
     ("@", "The literal separator between username and domain."),
     (r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "A domain with a literal dot and a suffix of at least two letters."),
     (r"(?![A-Za-z0-9_@\-])", "Prevent a partial match before another email character.")),
    "Email: somchai.d@company.com", _edits,
    (Step(r"(?<![A-Za-z0-9._%+@*\-])", "Left boundary: not the tail of a longer or already-masked address.", guard=True),
     Step(r"[A-Za-z0-9._%+\-]", "Username character; the loop is the + quantifier. Only the middle ones become *.", loop=True, masked=True),
     Step("@", "The literal separator.", row=True),
     Step("[A-Za-z0-9.-]", "Domain character; this class also contains the dot, which is what makes the machine nondeterministic.", loop=True),
     Step(r"\.", "The dot in front of the suffix."),
     Step("[A-Za-z]", "Suffix letter; two are required and the loop allows more.", times=2, loop=True, row=True),
     Step(r"(?![A-Za-z0-9_@\-])", "Right boundary: the address has to end here.", guard=True)),
)


def mask_email(text):
    return RULE.mask(text)


def email_parse(email):
    """Keep the old single-email helper available without interactive input."""
    return mask_email(email) if PATTERN.fullmatch(email) else "Invalid email"

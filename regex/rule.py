"""Shared rule metadata and replacements; no web or file-system dependencies."""

from dataclasses import dataclass
import re
from typing import Callable


@dataclass(frozen=True)
class Edit:
    """A replacement inside a regex match, using Unicode code-point offsets."""

    start: int
    end: int
    replacement: str


def group_edit(match: re.Match, group: str, replacement: str) -> Edit:
    return Edit(match.start(group) - match.start(), match.end(group) - match.start(), replacement)


@dataclass(frozen=True)
class Step:
    r"""One move of a rule's finite-state machine, drawn on the Playground.

    ``symbol`` is the single-character language the transition reads, written in
    regex form so the browser can reuse it: a class such as ``[0-9]`` or an
    escaped literal such as ``\.``. ``guard`` steps are lookarounds: they test a
    position and read nothing, so they annotate a state instead of adding one.
    """

    symbol: str
    meaning: str
    times: int = 1
    loop: bool = False
    optional: bool = False
    masked: bool = False
    guard: bool = False
    row: bool = False


_SPECIAL = frozenset(r"\^$.|?*+()[]{}/-")


def literal(text: str, meaning: str, row: bool = False, wrap: int = 0) -> tuple:
    """One state per character, the way a string-matching automaton is drawn."""
    return tuple(Step("\\" + character if character in _SPECIAL else character, meaning,
                      row=bool(row and index == 0 or wrap and index and index % wrap == 0))
                 for index, character in enumerate(text))


@dataclass(frozen=True)
class Maybe:
    """A run of steps the machine may skip entirely, drawn as a bypass arc."""

    steps: tuple[Step, ...]
    meaning: str


def build_machine(steps) -> dict:
    """Expand an authored step list into states and transitions.

    Every ``{n}`` repetition becomes ``n`` real states, so the drawing is a
    genuine machine rather than a picture of the pattern's source text.
    """
    states = [{"id": "q0", "kind": "start", "row": 0, "guards": []}]
    edges = []
    row = 0

    def add_state():
        states.append({"id": f"q{len(states)}", "kind": "read", "row": row, "guards": []})
        return len(states) - 1

    def walk(items):
        nonlocal row
        for item in items:
            if isinstance(item, Maybe):
                entry = len(states) - 1
                walk(item.steps)
                edges.append({"from": entry, "to": len(states) - 1, "symbol": "ε",
                              "meaning": item.meaning, "kind": "skip", "masked": False})
                continue
            if item.row:
                row += 1
            if item.guard:
                states[-1]["guards"].append({"symbol": item.symbol, "meaning": item.meaning})
                continue
            entry = len(states) - 1
            for _ in range(item.times):
                source = len(states) - 1
                target = add_state()
                edges.append({"from": source, "to": target, "symbol": item.symbol,
                              "meaning": item.meaning, "kind": "read", "masked": item.masked})
            if item.loop:
                edges.append({"from": len(states) - 1, "to": len(states) - 1, "symbol": item.symbol,
                              "meaning": f"{item.meaning} (repeat)", "kind": "loop", "masked": item.masked})
            if item.optional:
                edges.append({"from": entry, "to": len(states) - 1, "symbol": "ε",
                              "meaning": f"{item.meaning} (may be absent)", "kind": "skip", "masked": False})

    walk(steps)
    states[-1]["kind"] = "accept"
    return {"states": states, "edges": edges}


def trace_machine(machine: dict, text: str, start: int) -> list:
    """Replay ``text`` through the machine, preferring the next required read.

    Transitions are tried forward, then as a repeat, then as a bypass, which
    reproduces the engine's result for the bundled samples; the test-suite
    checks the replay against the real match for every rule.
    """
    edges = machine["edges"]
    accept = len(machine["states"]) - 1
    position, state, moves = start, 0, []
    for _ in range(len(text) + len(edges) + 1):
        options = [index for index, edge in enumerate(edges) if edge["from"] == state]
        order = [index for kind in ("read", "loop", "skip")
                 for index in options if edges[index]["kind"] == kind and (kind != "read" or edges[index]["to"] != state)]
        for index in order:
            edge = edges[index]
            if edge["kind"] == "skip":
                moves.append({"edge": index, "to": edge["to"], "start": position, "end": position, "text": ""})
                state = edge["to"]
                break
            if position < len(text) and re.fullmatch(edge["symbol"], text[position]):
                moves.append({"edge": index, "to": edge["to"], "start": position,
                              "end": position + 1, "text": text[position]})
                state, position = edge["to"], position + 1
                break
        else:
            break
        if state == accept and not any(edge["from"] == accept and edge["kind"] == "loop" for edge in edges):
            break
    return moves


@dataclass(frozen=True)
class Rule:
    key: str
    label: str
    pattern: re.Pattern
    description: str
    tokens: tuple[tuple[str, str], ...]
    sample: str
    edits: Callable[[re.Match], tuple[Edit, ...]]
    steps: tuple = ()

    def replace(self, match: re.Match) -> str:
        source = match.group()
        pieces = []
        cursor = 0
        for edit in self.edits(match):
            pieces.extend((source[cursor:edit.start], edit.replacement))
            cursor = edit.end
        pieces.append(source[cursor:])
        return "".join(pieces)

    def mask(self, text: str) -> str:
        return self.pattern.sub(self.replace, text)

    def machine(self) -> dict:
        """States, transitions and a replay of this rule's own sample."""
        machine = build_machine(self.steps)
        match = self.pattern.search(self.sample)
        machine["input"] = self.sample
        machine["offset"] = match.start() if match else 0
        machine["trace"] = trace_machine(machine, self.sample, machine["offset"]) if match else []
        return machine

    def public(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "pattern": self.pattern.pattern,
            "description": self.description,
            "tokens": [{"syntax": syntax, "meaning": meaning} for syntax, meaning in self.tokens],
            "sample": self.sample,
        }

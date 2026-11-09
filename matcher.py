"""Matching a deck list against bulks, and formatting the result as text."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Iterable, Mapping

from parser import Card, normalize_name


@dataclass
class Hit:
    """A deck card that one person has."""

    name: str
    need: int           # how many the deck wants
    have: int           # how many this person has
    also: list[str] = field(default_factory=list)  # who else has it

    @property
    def give(self) -> int:
        """How many copies are actually needed from this person (at most what the deck wants)."""
        return min(self.have, self.need)

    @property
    def partial(self) -> bool:
        return self.have < self.need


@dataclass
class Line:
    name: str
    qty: int


@dataclass
class CheckResult:
    owners: list[str]                     # group order
    groups: dict[str, list[Hit]]          # owner -> cards
    missing: list[Line]                   # need to get
    ignored: list[Line]                   # skipped (basic lands etc.)
    deck_cards: int                       # total copies in the deck (excluding skipped)

    @property
    def covered_cards(self) -> int:
        return self.deck_cards - sum(m.qty for m in self.missing)


def aggregate(cards: Iterable[Card]) -> dict[str, Line]:
    """Merge identical cards (e.g. the same card from two sets) into one line."""
    out: dict[str, Line] = {}
    for c in cards:
        key = c.key
        if key in out:
            out[key].qty += c.qty
        else:
            out[key] = Line(c.name, c.qty)
    return out


def build_index(bulks: Mapping[str, Iterable[Card]]) -> dict[str, dict[str, int]]:
    """name -> {owner: copies}"""
    index: dict[str, dict[str, int]] = {}
    for owner, cards in bulks.items():
        for c in cards:
            per_owner = index.setdefault(c.key, {})
            per_owner[owner] = per_owner.get(owner, 0) + c.qty
    return index


def check_deck(
    deck: Iterable[Card],
    bulks: Mapping[str, Iterable[Card]],
    ignored_names: Iterable[str] = (),
) -> CheckResult:
    """For every deck card find who has it and what is still missing.

    Groups follow the order of `bulks`.
    """
    owners = list(bulks)
    index = build_index(bulks)
    ignored_keys = {normalize_name(n) for n in ignored_names}

    groups: dict[str, list[Hit]] = {o: [] for o in owners}
    missing: list[Line] = []
    ignored: list[Line] = []
    deck_cards = 0

    for key, line in aggregate(deck).items():
        if key in ignored_keys:
            ignored.append(line)
            continue
        deck_cards += line.qty
        holders = index.get(key, {})
        for owner, have in holders.items():
            others = [o for o in holders if o != owner]
            groups[owner].append(Hit(line.name, line.qty, have, others))
        short = line.qty - sum(holders.values())
        if short > 0:
            missing.append(Line(line.name, short))

    by_name = lambda x: x.name.casefold()  # noqa: E731
    for hits in groups.values():
        hits.sort(key=by_name)
    missing.sort(key=by_name)
    ignored.sort(key=by_name)
    return CheckResult(owners, groups, missing, ignored, deck_cards)


# --- text export --------------------------------------------------------------------

def cards_word(n: int) -> str:
    return "card" if n == 1 else "cards"


def format_lines(lines: Iterable[tuple[int, str]]) -> str:
    return "\n".join(f"{qty} {name}" for qty, name in lines)


def format_result(
    result: CheckResult,
    deck_name: str,
    labels: Mapping[str, str],
    date: dt.date | None = None,
) -> str:
    """The result as plain text, ready to send or paste back into Moxfield."""
    date = date or dt.date.today()
    missing = format_lines((m.qty, m.name) for m in result.missing) or "(nothing)"
    parts = [
        f"Deck: {deck_name} – checked {date:%Y-%m-%d}",
        f"Need to get ({len(result.missing)}):\n{missing}",
    ]
    for owner in result.owners:
        hits = result.groups[owner]
        if hits:
            body = format_lines((h.give, h.name) for h in hits)
            parts.append(f"{labels.get(owner, owner)} has ({len(hits)}):\n{body}")
    return "\n\n".join(parts) + "\n"

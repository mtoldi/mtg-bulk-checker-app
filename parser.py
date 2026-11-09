"""Reading deck lists and bulk lists.

Supported line format is what Moxfield, Archidekt, MTG Arena and Cardmarket
export, e.g.:

    1 Molten Gatekeeper (MH3) 128
    1 Kinbinding (ECL) 407 *F*
    1 Empty the Warrens (PLST) DMR-118
    1x Sol Ring (CMM) 410 [Ramp]
    1 Gold Myr
    Gold Myr

Set, collector number and foil are read when present but never used:
cards are matched purely by normalized name (see `normalize_name`).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Card:
    name: str
    qty: int = 1
    set_code: str | None = None
    number: str | None = None
    foil: bool = False
    owner: str | None = None

    @property
    def key(self) -> str:
        """Matching key (normalized name of the front face)."""
        return normalize_name(self.name)


# --- regular expressions ------------------------------------------------------

LINE_RE = re.compile(
    r"""^
    (?:(?P<qty>\d+)\s*[xX]?\s+)?              # quantity: "1 ", "1x ", "1 x "
    (?P<name>.+?)                              # card name
    (?:\s+\((?P<set>[A-Za-z0-9]{2,6})\)        # set: (MH3)
        (?:\s+(?P<num>[^\s*]+))?               # number: 128, DMR-118, 128a, ★
    )?
    (?P<flags>(?:\s+\*[A-Za-z]+\*)*)           # *F*, *E* ...
    \s*$""",
    re.VERBOSE,
)

# Archidekt adds categories "[Ramp]" and tags "^Have,#37d67a^"
_ARCHIDEKT_EXTRA_RE = re.compile(r"\s*(\[[^\]]*\]|\^[^^]*\^)")
# Cardmarket version tags: "Arcane Signet (V.2)"
_VERSION_RE = re.compile(r"\s*\(\s*v\.?\s*\d+\s*\)", re.IGNORECASE)
# Headers with a count: "Creatures (12)", "Sideboard (15)"
_COUNTED_HEADER_RE = re.compile(r"^[A-Za-z][A-Za-z ]*\(\d+\)\s*:?$")
_FACE_SPLIT_RE = re.compile(r"\s*/{1,2}\s*")

SECTION_HEADERS = {
    "about", "deck", "main", "mainboard", "main deck", "maindeck",
    "sideboard", "side", "commander", "commanders", "companion",
    "maybeboard", "maybe", "considering", "tokens", "token",
}

_APOSTROPHES = "‘’ʼ`´′"
_DASHES = "‐‑‒–—―−"
_TRANSLATE = {ord(c): "'" for c in _APOSTROPHES} | {ord(c): "-" for c in _DASHES}


# --- normalization --------------------------------------------------------------

def clean_name(name: str) -> str:
    """Display name: without the Cardmarket version tag and extra whitespace."""
    name = _VERSION_RE.sub("", name)
    name = _FACE_SPLIT_RE.sub(" // ", name) if "/" in name else name
    return " ".join(name.split())


def normalize_name(name: str) -> str:
    """Key used to compare two names.

    - lowercase, collapsed whitespace
    - all apostrophes and dashes unified to ' and -
    - accents and Æ removed (Lórien == Lorien, Æther == Aether)
    - Cardmarket "(V.2)" removed
    - for double-faced cards ("A // B") only the front face counts, so
      "A // B" and "A" find each other
    """
    s = unicodedata.normalize("NFKC", name).translate(_TRANSLATE)
    s = s.replace("Æ", "Ae").replace("æ", "ae")
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = _VERSION_RE.sub("", s)
    s = _FACE_SPLIT_RE.split(s, maxsplit=1)[0]
    return " ".join(s.split()).casefold()


# --- parsing ----------------------------------------------------------------------

def _is_header(line: str) -> bool:
    bare = line.rstrip(":").strip().casefold()
    return bare in SECTION_HEADERS or bool(_COUNTED_HEADER_RE.match(line))


def parse_line(line: str, owner: str | None = None) -> Card | None:
    """Parse one line; returns None for blank lines, comments and headers."""
    line = line.strip().lstrip("﻿")
    if not line or line.startswith(("#", "//")) or _is_header(line):
        return None
    line = _ARCHIDEKT_EXTRA_RE.sub("", line).strip()
    m = LINE_RE.match(line)
    if not m:
        return None
    name = clean_name(m["name"])
    if not name:
        return None
    qty = int(m["qty"]) if m["qty"] else 1
    if qty <= 0:
        return None
    flags = m["flags"].upper()
    return Card(
        name=name,
        qty=qty,
        set_code=m["set"].upper() if m["set"] else None,
        number=m["num"],
        foil="*F*" in flags or "*E*" in flags,
        owner=owner,
    )


def parse_text(text: str, owner: str | None = None) -> list[Card]:
    """Parse a whole list. The Arena "About / Name ..." block is skipped."""
    cards: list[Card] = []
    in_about = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.casefold().rstrip(":") == "about":
            in_about = True
            continue
        if in_about:
            if not line:
                in_about = False
            continue
        card = parse_line(line, owner)
        if card:
            cards.append(card)
    return cards


def detect_deck_name(text: str) -> str | None:
    """Deck name from an Arena export ("About" / "Name Goblin tokens"), if present."""
    in_about = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.casefold().rstrip(":") == "about":
            in_about = True
        elif in_about and line.casefold().startswith("name "):
            return line[5:].strip() or None
        elif in_about and not line:
            in_about = False
    return None


def read_text_file(path: Path) -> str:
    """Read a .txt whether it was saved as UTF-8 or a legacy Windows codepage."""
    data = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "cp1250"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def parse_file(path: Path, owner: str | None = None) -> list[Card]:
    return parse_text(read_text_file(path), owner)

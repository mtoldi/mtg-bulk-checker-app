"""Everything that touches the disk: folders, config.toml, saved bulks, results and remembered settings."""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
import unicodedata
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

from parser import Card, parse_file

# When frozen/bundled, folders live next to the executable, not in a temp dir.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

BULKS_DIR = BASE_DIR / "bulks"
DECKS_DIR = BASE_DIR / "decks"
RESULTS_DIR = BASE_DIR / "results"
CONFIG_PATH = BASE_DIR / "config.toml"
STATE_PATH = BASE_DIR / ".settings.json"

def load_ignored_cards() -> list[str]:
    """Cards skipped by default (config.toml → ignored_cards)."""
    if not CONFIG_PATH.exists():
        return []
    with CONFIG_PATH.open("rb") as f:
        return list(tomllib.load(f).get("ignored_cards", []))


# --- bulks -------------------------------------------------------------------------

def slugify(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def owner_label(owner: str) -> str:
    """'alice' -> 'Alice', 'ZukaBugar' -> 'ZukaBugar', 'ivan_k' -> 'Ivan k'"""
    label = re.sub(r"[-_]+", " ", owner).strip()
    return label[:1].upper() + label[1:]


def bulk_files() -> dict[str, Path]:
    """owner (file name without .txt) -> path, alphabetically."""
    if not BULKS_DIR.exists():
        return {}
    return {p.stem: p for p in sorted(BULKS_DIR.glob("*.txt"), key=lambda p: p.stem.lower())}


def load_bulk(owner: str, path: Path) -> list[Card]:
    return parse_file(path, owner)


def safe_name(name: str) -> str:
    """Turn a typed name into a safe file name, keeping letters and their case."""
    return " ".join(re.sub(r"[^\w\- ]+", "", name).split()).strip(".-")


def save_bulk(name: str, text: str) -> tuple[str, bool]:
    """Write a bulk to bulks/<name>.txt. Returns (owner, replaced_existing).

    An existing file with the same name in a different case is replaced.
    """
    owner = safe_name(name)
    if not owner:
        raise ValueError("The name must contain at least one letter or digit.")
    BULKS_DIR.mkdir(exist_ok=True)
    existing = [p for p in BULKS_DIR.glob("*.txt") if p.stem.lower() == owner.lower()]
    for p in existing:
        p.unlink()
    (BULKS_DIR / f"{owner}.txt").write_text(text.replace("\r\n", "\n"), encoding="utf-8")
    return owner, bool(existing)


# --- decks and results ----------------------------------------------------------------

def deck_files() -> dict[str, Path]:
    if not DECKS_DIR.exists():
        return {}
    return {p.stem: p for p in sorted(DECKS_DIR.glob("*.txt"))}


def result_filename(deck_name: str, date: dt.date | None = None) -> str:
    date = date or dt.date.today()
    return f"{slugify(deck_name) or 'deck'}_{date:%Y-%m-%d}.txt"


def save_result(text: str, deck_name: str, date: dt.date | None = None) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / result_filename(deck_name, date)
    path.write_text(text, encoding="utf-8")
    return path


def result_files() -> list[Path]:
    """Saved results, newest first."""
    if not RESULTS_DIR.exists():
        return []
    return sorted(RESULTS_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)


def delete_result(name: str) -> None:
    """Delete a saved result by file name (only inside the results/ folder)."""
    path = RESULTS_DIR / Path(name).name
    if path.is_file():
        path.unlink()


# --- remembered UI settings -------------------------------------------------------------

def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(**values) -> None:
    state = load_state() | values
    try:
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass  # not critical if it can't be remembered

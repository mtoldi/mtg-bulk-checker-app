import pytest

from parser import detect_deck_name, normalize_name, parse_line, parse_text


@pytest.mark.parametrize(
    "line, qty, name, set_code, number, foil",
    [
        ("1 Molten Gatekeeper (MH3) 128", 1, "Molten Gatekeeper", "MH3", "128", False),
        ("3 Evolving Wilds (FIC) 389", 3, "Evolving Wilds", "FIC", "389", False),
        ("1 Kinbinding (ECL) 407 *F*", 1, "Kinbinding", "ECL", "407", True),
        ("1 Empty the Warrens (PLST) DMR-118", 1, "Empty the Warrens", "PLST", "DMR-118", False),
        ("1 Gold Myr", 1, "Gold Myr", None, None, False),
        ("Gold Myr", 1, "Gold Myr", None, None, False),
        ("4x Lightning Bolt", 4, "Lightning Bolt", None, None, False),
        ("1 Sol Ring (CMM) 410 [Ramp] ^Have,#37d67a^", 1, "Sol Ring", "CMM", "410", False),
        ("1 Sol Ring (cmm)", 1, "Sol Ring", "CMM", None, False),
        ("1 Arcane Signet (V.2)", 1, "Arcane Signet", None, None, False),
        ("1 Spiritcall Enthusiast // Scrollboost (DSK) 1", 1, "Spiritcall Enthusiast // Scrollboost", "DSK", "1", False),
        ("1 Fire/Ice", 1, "Fire // Ice", None, None, False),
        ("2 Krenko, Tin Street Kingpin", 2, "Krenko, Tin Street Kingpin", None, None, False),
    ],
)
def test_parse_line(line, qty, name, set_code, number, foil):
    card = parse_line(line)
    assert (card.qty, card.name, card.set_code, card.number, card.foil) == (qty, name, set_code, number, foil)


@pytest.mark.parametrize("line", ["", "   ", "# comment", "// comment", "Sideboard", "SIDEBOARD:", "Commander", "Deck", "Creatures (12)"])
def test_skipped_lines(line):
    assert parse_line(line) is None


def test_parse_text_arena_export():
    text = "About\nName Goblin tokens\n\nCommander\n1 Krenko, Mob Boss\n\nDeck\n1 Sol Ring\n8 Mountain\n\nSideboard\n1 Gold Myr\n"
    cards = parse_text(text, owner="bob")
    assert [(c.qty, c.name) for c in cards] == [(1, "Krenko, Mob Boss"), (1, "Sol Ring"), (8, "Mountain"), (1, "Gold Myr")]
    assert all(c.owner == "bob" for c in cards)
    assert detect_deck_name(text) == "Goblin tokens"


@pytest.mark.parametrize(
    "a, b",
    [
        ("Arcane Signet (V.2)", "arcane signet"),
        ("  Sol   RING ", "Sol Ring"),
        ("Urza’s Saga", "Urza's Saga"),
        ("Spiritcall Enthusiast // Scrollboost", "Spiritcall Enthusiast"),
        ("Fire/Ice", "Fire // Ice"),
        ("Lórien Revealed", "Lorien Revealed"),
        ("Æther Vial", "Aether Vial"),
        ("Jace – the Mind Sculptor", "Jace - the Mind Sculptor"),
    ],
)
def test_normalize_name_equal(a, b):
    assert normalize_name(a) == normalize_name(b)


def test_normalize_name_different():
    assert normalize_name("Gold Myr") != normalize_name("Silver Myr")

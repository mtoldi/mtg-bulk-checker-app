import datetime as dt

from matcher import cards_word, check_deck, format_result
from parser import parse_text

DECK = parse_text(
    """1 Sol Ring
1 Arcane Signet
1 Command Tower
1 Splitskin Doll
2 Unsettling Twins
1 Molten Gatekeeper (MH3) 128
1 Rumor Gatherer
8 Mountain
1 Island
"""
)

BULKS = {
    "carol": parse_text("3 Mountain\n"),
    "bob": parse_text("1 Command Tower (CMM) 1\n1 Splitskin Doll\n5 Unsettling Twins (DSK) 38\n2 Mountain\n"),
    "alice": parse_text("1 Molten Gatekeeper (MH3) 128\n1 Rumor Gatherer\n1 Command Tower\n"),
}
LABELS = {"carol": "Carol", "bob": "Bob", "alice": "Alice"}


def test_groups_and_missing():
    r = check_deck(DECK, BULKS, ignored_names=["Island"])
    assert r.owners == ["carol", "bob", "alice"]
    assert [(h.name, h.give) for h in r.groups["bob"]] == [
        ("Command Tower", 1), ("Mountain", 2), ("Splitskin Doll", 1), ("Unsettling Twins", 2),
    ]
    assert [(h.name, h.have, h.need) for h in r.groups["carol"]] == [("Mountain", 3, 8)]
    # Mountain: deck wants 8, Carol 3 + Bob 2 -> 3 missing
    assert [(m.name, m.qty) for m in r.missing] == [("Arcane Signet", 1), ("Mountain", 3), ("Sol Ring", 1)]
    assert [(i.name, i.qty) for i in r.ignored] == [("Island", 1)]
    tower = next(h for h in r.groups["alice"] if h.name == "Command Tower")
    assert tower.also == ["bob"]
    assert r.deck_cards == 16
    assert r.covered_cards == 11


def test_duplicate_deck_lines_are_summed():
    deck = parse_text("2 Mountain (FDN) 1\n3 Mountain (DSK) 2\n")
    r = check_deck(deck, {"carol": parse_text("10 Mountain")})
    assert [(h.need, h.give) for h in r.groups["carol"]] == [(5, 5)]
    assert r.missing == []


def test_double_faced_front_face_matches():
    deck = parse_text("1 Spiritcall Enthusiast // Scrollboost (DSK) 1\n")
    r = check_deck(deck, {"alice": parse_text("1 Spiritcall Enthusiast")})
    assert len(r.groups["alice"]) == 1 and r.missing == []


def test_no_bulks_everything_missing():
    r = check_deck(parse_text("1 Sol Ring\n"), {})
    assert [(m.name, m.qty) for m in r.missing] == [("Sol Ring", 1)]


def test_format_result():
    r = check_deck(DECK, BULKS, ignored_names=["Island"])
    text = format_result(r, "Goblin tokens", LABELS, date=dt.date(2026, 11, 9))
    assert text.startswith(
        "Deck: Goblin tokens – checked 2026-11-09\n\nNeed to get (3):\n1 Arcane Signet\n3 Mountain\n1 Sol Ring\n"
    )
    assert "\n\nCarol has (1):\n3 Mountain\n" in text
    assert "\n\nAlice has (3):\n1 Command Tower\n1 Molten Gatekeeper\n1 Rumor Gatherer\n" in text


def test_cards_word():
    assert [cards_word(n) for n in (0, 1, 2, 11)] == ["cards", "card", "cards", "cards"]

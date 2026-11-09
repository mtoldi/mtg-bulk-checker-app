# 🃏 Bulk Checker

A small app for your Magic: The Gathering group. Paste a deck list and it tells you which cards
someone in your group already has in their bulk, and which ones you still need to get.

- Runs on your own computer, **offline**, with no database or account.
- Matches **by card name only**. Set and foil are ignored.
- Understands exports from **Moxfield, Archidekt and MTG Arena**, plus plain lists (`1 Sol Ring`, `Sol Ring`).

## Getting started

**Easiest (Windows, nothing to install):**
1. Download `BulkChecker-windows.zip` from [Releases](../../releases) and unzip it.
2. Put your bulk lists into the `bulks/` folder (see below).
3. Double-click **`start.bat`**. The app opens in your browser; close the black window to stop it.

**With Python (Windows, Mac, Linux):**
1. Install Python 3.10+ from [python.org](https://www.python.org/downloads/). On Windows, tick **"Add Python to PATH"**.
2. Click **Code → Download ZIP** and unzip it.
3. Double-click **`start.bat`** (Windows) or run `./start.sh` (Mac/Linux). The first run takes a minute or two.

## Bulks: one file = one person

The file name is the person's name in the results:

```
bulks/
├── alice.txt  → "Alice has"
└── bob.txt    → "Bob has"
```

Everyone exports their bulk from Moxfield, Archidekt or Arena as a `.txt` and shares it with the group.
When someone sends a new version, overwrite their file (or upload it in the app via **➕ Add or replace a bulk**)
and click **🔄 Refresh**. Pick whose bulks to search in the dropdown; the app remembers your choice.

**Example bulks:** `bulks/Krleza.txt` and `bulks/ZukaBugar.txt` are two real-world example bulks so you can try
the app right away (load `decks/example-deck.txt` and click **Check deck**). Delete them once you add your own lists.
Any other file you put in `bulks/` is in `.gitignore`, so nobody's list gets published to GitHub by accident.

## The result

You get a list per person of the cards they have, plus a **🛒 Need to get** list:

- The number next to a card is how many copies that person can give for this deck, never more than the deck needs.
- "Need to get" counts the whole group: the deck needs 8 Mountain, Bob has 3, Alice has 2, so you need 3.
- "Not enough: Mountain 3 / 8" and "Also with: …" show partial and shared cards.
- Every list has a copy icon (it appears when you hover over the list), so you can paste it straight into Moxfield.
- **💾 Save as .txt** saves the whole result to the `results/` folder, e.g. `example-deck_2026-11-09.txt`.
  The **📂 Saved results** tab lists everything you've saved (newest first), so you can view, copy, download or delete it.

**Skip cards:** cards you don't need to look for, such as basic lands. The list that gets pre-selected lives in
`config.toml`; you can change it for a single deck in the app.
**Adding a deck:** paste the list into the text box, or drag & drop a deck `.txt` file onto the upload box above it
(the deck name is taken from the file name). Decks you check often can go into the `decks/` folder and be loaded from the dropdown.

**Dark / light mode:** the app starts in dark mode. To switch, open the **⋮** menu (top right) and pick
**Light**, **Dark** or **System**. Your browser remembers the choice.

## Line format

| Line | What the app reads |
| --- | --- |
| `1 Molten Gatekeeper (MH3) 128` | 1× Molten Gatekeeper |
| `1 Kinbinding (ECL) 407 *F*` | 1× Kinbinding |
| `1 Empty the Warrens (PLST) DMR-118` | 1× Empty the Warrens |
| `1x Sol Ring (CMM) 410 [Ramp]` | 1× Sol Ring |
| `1 Arcane Signet (V.2)` | 1× Arcane Signet |
| `Gold Myr` | 1× Gold Myr |

Blank lines, comments (`#`, `//`) and headers (`Sideboard`, `Commander`, `Deck`…) are skipped.
Double-faced cards match by their full name or by the front face alone, and different apostrophes, dashes and accents don't matter.

## For developers

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt      # Mac/Linux: .venv/bin/pip
.venv/Scripts/python -m pytest
.venv/Scripts/streamlit run app.py
```

| File | Purpose |
| --- | --- |
| `parser.py` | reading lists and normalizing names |
| `matcher.py` | matching, result text and messages |
| `storage.py` | folders, `config.toml`, saving bulks and results |
| `app.py` | the UI (Streamlit) |
| `tools/build-portable.ps1` | portable Windows ZIP (embedded Python + Streamlit) |

**New release:** `git tag v1.0.0 && git push --tags`. GitHub Actions runs the tests, builds
`BulkChecker-windows.zip` and publishes it under Releases. To build the ZIP locally, run
`powershell -ExecutionPolicy Bypass -File tools\build-portable.ps1`.

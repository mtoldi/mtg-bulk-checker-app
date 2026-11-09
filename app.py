"""Bulk Checker – user interface (Streamlit).

Run with:  start.bat / start.sh   (or: streamlit run app.py)
"""

from __future__ import annotations

import datetime as dt

import streamlit as st
import streamlit.components.v1 as components

import storage
from matcher import CheckResult, aggregate, cards_word, check_deck, format_lines, format_result
from parser import decode_text, detect_deck_name, normalize_name, parse_text, read_text_file

st.set_page_config(page_title="Bulk Checker", page_icon="🃏", layout="wide")


# --- dark mode by default -------------------------------------------------------------
# Streamlit remembers the theme picked in the ⋮ menu under this localStorage key and
# otherwise follows the OS (it stores "System" itself on first load). On a browser's first
# visit we switch it to "Dark" once, mark that we did, and reload; after that the user's
# own choice (Light/Dark/System) is always respected.
# If a future Streamlit renames the key, this silently falls back to the OS theme.
_DARK_BY_DEFAULT = """
<script>
  const w = window.parent;
  const themeKey = "stActiveTheme-" + w.location.pathname + "-v2";
  const doneKey = "bulkChecker.darkDefaultApplied";
  try {
    if (!w.localStorage.getItem(doneKey)) {
      w.localStorage.setItem(doneKey, "1");
      w.localStorage.setItem(themeKey, JSON.stringify("Dark"));
      w.location.reload();
    }
  } catch (e) {}
</script>
"""
if not st.session_state.get("_theme_checked"):
    components.html(_DARK_BY_DEFAULT, height=0)
    st.session_state._theme_checked = True


# --- loading bulks -------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _load_bulk_cached(owner: str, path: str, mtime: float):
    return storage.load_bulk(owner, storage.Path(path))


all_bulks = {
    owner: _load_bulk_cached(owner, str(path), path.stat().st_mtime)
    for owner, path in storage.bulk_files().items()
}
owners = list(all_bulks)
labels = {o: storage.owner_label(o) for o in owners}


def describe(owner: str) -> str:
    n = sum(c.qty for c in all_bulks[owner])
    return f"{labels[owner]} · {n} {cards_word(n)}"


# --- session state ---------------------------------------------------------------------

ss = st.session_state
if "selected" not in ss:
    remembered = storage.load_state().get("selected")
    ss.selected = [o for o in owners if not remembered or o in remembered]
else:
    ss.selected = [o for o in ss.selected if o in owners]  # deleted bulks
if (new_owner := ss.pop("select_new", None)) and new_owner in owners and new_owner not in ss.selected:
    ss.selected = ss.selected + [new_owner]
    storage.save_state(selected=ss.selected)
ss.setdefault("deck_text", "")
ss.setdefault("deck_name", "")


def remember() -> None:
    storage.save_state(selected=ss.selected)


def load_saved_deck() -> None:
    if name := ss.get("saved_deck"):
        ss.deck_text = read_text_file(storage.deck_files()[name])
        ss.deck_name = detect_deck_name(ss.deck_text) or storage.owner_label(name)


def load_uploaded_deck() -> None:
    # removing the file (×) keeps whatever is in the text box
    if upload := ss.get("deck_upload"):
        ss.deck_text = decode_text(upload.getvalue())
        ss.deck_name = detect_deck_name(ss.deck_text) or storage.owner_label(storage.Path(upload.name).stem)


# --- bulks ---------------------------------------------------------------------------------

st.title("🃏 Bulk Checker")
st.caption("Paste or drop a deck list and see who in your group has which card, and what you still need to get.")

tab_check, tab_results = st.tabs(["🔍 Check deck", "📂 Saved results"])

with tab_check:
    col_sel, col_refresh = st.columns([5, 1], vertical_alignment="bottom")
    with col_sel:
        st.multiselect(
            "Bulks (every .txt file in the bulks/ folder is one person)",
            options=owners,
            key="selected",
            format_func=describe,
            on_change=remember,
            placeholder="No bulk selected",
        )
    with col_refresh:
        if st.button("🔄 Refresh", use_container_width=True, help="Re-read the bulks/ folder"):
            _load_bulk_cached.clear()
            st.rerun()

    with st.expander("➕ Add or replace a bulk"):
        with st.form("add_bulk", clear_on_submit=True):
            new_name = st.text_input("Person's name", placeholder="e.g. Alice (empty = file name)")
            upload = st.file_uploader("File (.txt)", type=["txt"])
            pasted = st.text_area("…or paste the list", height=120)
            submitted = st.form_submit_button("Save bulk")
        if submitted:
            name = new_name.strip() or (upload.name.rsplit(".", 1)[0] if upload else "")
            text = decode_text(upload.getvalue()) if upload else pasted
            if not name:
                st.error("Enter the person's name.")
            elif not parse_text(text):
                st.error("No cards found in the list.")
            else:
                try:
                    owner, replaced = storage.save_bulk(name, text)
                except ValueError as e:
                    st.error(str(e))
                else:
                    ss.select_new = owner
                    ss.flash = f"Bulk **{storage.owner_label(owner)}** {'replaced' if replaced else 'added'}."
                    st.rerun()

    if msg := ss.pop("flash", None):
        st.success(msg)


    # --- deck ------------------------------------------------------------------------------------

    st.subheader("Deck list")
    st.file_uploader(
        "Drag & drop a deck .txt file here, or paste the list below",
        type=["txt"],
        key="deck_upload",
        on_change=load_uploaded_deck,
    )
    if decks := storage.deck_files():
        st.selectbox(
            "Load a saved deck from the decks/ folder",
            options=list(decks),
            index=None,
            key="saved_deck",
            on_change=load_saved_deck,
            placeholder="— or pick a saved deck —",
            label_visibility="collapsed",
        )

    st.text_area(
        "Deck list",
        key="deck_text",
        height=260,
        label_visibility="collapsed",
        placeholder="1 Sol Ring (CMM) 410\n1 Command Tower\n8 Mountain\n…",
    )

    deck = parse_text(ss.deck_text)
    deck_names = [line.name for line in aggregate(deck).values()]
    default_skip = {normalize_name(n) for n in storage.load_ignored_cards()}

    c1, c2 = st.columns([1, 2])
    with c1:
        st.text_input("Deck name", key="deck_name", placeholder="e.g. Goblin tokens")
    with c2:
        skip = st.multiselect(
            "Skip cards",
            options=deck_names,
            default=[n for n in deck_names if normalize_name(n) in default_skip],
            # a new deck means a new list, so it starts over from config.toml
            key=f"skip_{hash(tuple(deck_names))}",
            placeholder="Cards you don't need to look for (e.g. basic lands)",
        )

    if st.button("Check deck", type="primary", disabled=not deck):
        chosen = {o: all_bulks[o] for o in owners if o in ss.selected}
        ss.result = check_deck(deck, chosen, ignored_names=skip)
        ss.result_deck = ss.deck_name.strip() or detect_deck_name(ss.deck_text) or "Deck"
        ss.result_date = dt.date.today()


# --- result --------------------------------------------------------------------------------------

def render_result(result: CheckResult, deck_name: str, date: dt.date) -> None:
    st.divider()
    st.subheader(f"Result: {deck_name}")

    m1, m2, m3 = st.columns(3)
    m1.metric("Cards in deck", result.deck_cards)
    m2.metric("Someone has", result.covered_cards)
    m3.metric("Need to get", sum(m.qty for m in result.missing))

    if not result.missing:
        st.success("Someone in the selected bulks has every card in this deck. 🎉")

    cols = st.columns(3)
    i = 0

    if result.missing:
        with cols[i % 3].container(border=True):
            n = len(result.missing)
            st.markdown(f"**🛒 Need to get** · {n} {cards_word(n)}")
            st.code(format_lines((m.qty, m.name) for m in result.missing), language="text")
        i += 1

    for owner in result.owners:
        hits = result.groups[owner]
        if not hits:
            continue
        label = labels.get(owner, owner)
        with cols[i % 3].container(border=True):
            st.markdown(f"**🤝 {label} has** · {len(hits)} {cards_word(len(hits))}")
            st.code(format_lines((h.give, h.name) for h in hits), language="text")
            if partial := [f"{h.name} {h.have} / {h.need}" for h in hits if h.partial]:
                st.caption("Not enough: " + ", ".join(partial))
            if shared := [f"{h.name} ({', '.join(labels.get(o, o) for o in h.also)})" for h in hits if h.also]:
                st.caption("Also with: " + "; ".join(shared))
        i += 1

    if result.ignored:
        with st.expander(f"Skipped cards ({len(result.ignored)})"):
            st.code(format_lines((l.qty, l.name) for l in result.ignored), language="text")

    text = format_result(result, deck_name, labels, date=date)
    s1, s2, _ = st.columns([1, 1, 3])
    with s1:
        if st.button("💾 Save as .txt", use_container_width=True):
            path = storage.save_result(text, deck_name, date)
            ss.saved_result = path.name  # show it in the "Saved results" tab
            st.toast(f"Saved to results/{path.name} – see the 📂 Saved results tab")
    with s2:
        st.download_button(
            "⬇️ Download",
            text,
            file_name=storage.result_filename(deck_name, date),
            mime="text/plain",
            use_container_width=True,
            key="download_result",
        )


with tab_check:
    if "result" in ss:
        render_result(ss.result, ss.result_deck, ss.result_date)


# --- saved results -------------------------------------------------------------------------------

def delete_saved_result(name: str) -> None:
    storage.delete_result(name)
    ss.pop("saved_result", None)
    ss.flash_results = f"Deleted {name}."


with tab_results:
    files = {p.name: p for p in storage.result_files()}
    if msg := ss.pop("flash_results", None):
        st.success(msg)
    if not files:
        st.info("No saved results yet. Check a deck and click **💾 Save as .txt** – it will show up here.")
    else:
        chosen = st.selectbox(
            "Saved result",
            options=list(files),
            key="saved_result",
            format_func=lambda n: f"{files[n].stem} · saved {dt.datetime.fromtimestamp(files[n].stat().st_mtime):%Y-%m-%d %H:%M}",
            help="Files from the results/ folder, newest first",
        )
        text = read_text_file(files[chosen])
        st.code(text, language="text")
        r1, r2, _ = st.columns([1, 1, 3])
        with r1:
            st.download_button(
                "⬇️ Download", text, file_name=chosen, mime="text/plain", use_container_width=True, key="download_saved"
            )
        with r2:
            st.button("🗑️ Delete", on_click=delete_saved_result, args=(chosen,), use_container_width=True)

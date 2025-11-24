"""
Prioritizer - Interactive Impact Ranking Tool

A Streamlit application for ranking ideas through pairwise comparisons.
Supports three ranking strategies:
- Binary Insertion Sort (fewest comparisons)
- Elo Tournament (rating-based)
- Swiss Rounds (batch-style tournament)

Usage:
    streamlit run app.py
"""

import io
import random
from typing import List, Dict, Optional, Tuple

import pandas as pd
import streamlit as st


# --- Configuration ---
APP_TITLE = "Prioritizer"
APP_ICON = "⚖️"
DEBUG = False  # Set to True for verbose state logging

STRATEGY_BINARY = "binary"
STRATEGY_ELO = "elo"
STRATEGY_SWISS = "swiss"

STRATEGY_LABELS = {
    STRATEGY_BINARY: "Interactive sort (fewest comparisons)",
    STRATEGY_ELO: "Elo tournament (rating-based)",
    STRATEGY_SWISS: "Swiss rounds (batch-style)",
}


# --- Debug Helper ---
def debug(msg: str):
    """Log debug message if DEBUG is enabled."""
    if DEBUG:
        if "debug_log" not in st.session_state:
            st.session_state.debug_log = []
        st.session_state.debug_log.append(msg)


# --- Page Configuration ---
st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")
st.title(f"{APP_ICON} {APP_TITLE}")
st.caption("Upload ideas, compare two at a time, and get a unique impact ranking.")


# --- State Initialization ---
def init_state():
    """Initialize all session state with defaults."""
    ss = st.session_state

    # Data / mapping
    ss.setdefault("df", None)
    ss.setdefault("id_col", None)
    ss.setdefault("name_col", None)
    ss.setdefault("desc_col", None)

    # Global mode
    ss.setdefault("rating_strategy", STRATEGY_BINARY)
    ss.setdefault("in_rating_mode", False)

    # Binary state
    ss.setdefault("binary_order", [])
    ss.setdefault("binary_sorted", [])
    ss.setdefault("binary_i", 0)
    ss.setdefault("binary_low", None)
    ss.setdefault("binary_high", None)
    ss.setdefault("binary_mid", None)
    ss.setdefault("binary_candidate", None)
    ss.setdefault("binary_comparisons", 0)

    # Elo state
    ss.setdefault("elo_pairs", [])
    ss.setdefault("elo_idx", 0)
    ss.setdefault("elo_ratings", {})
    ss.setdefault("elo_done", False)

    # Swiss state
    ss.setdefault("swiss_points", {})
    ss.setdefault("swiss_round", 1)
    ss.setdefault("swiss_rounds_total", 3)
    ss.setdefault("swiss_pairs", [])
    ss.setdefault("swiss_idx", 0)
    ss.setdefault("swiss_done", False)


init_state()
ss = st.session_state


# --- Utility Functions ---
def reset_all():
    """Clear all session state."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_state()


def get_n_items() -> int:
    """Get number of items in DataFrame."""
    if ss.df is None:
        return 0
    return len(ss.df)


def get_card(idx: int) -> Dict:
    """Get item info by index."""
    row = ss.df.iloc[idx]
    return {
        "id": row[ss.id_col],
        "name": row[ss.name_col],
        "desc": row[ss.desc_col],
    }


def build_ranked_df(ordering: List[int]) -> pd.DataFrame:
    """Build DataFrame with ranking column."""
    ranks = [None] * len(ss.df)
    for rank, idx in enumerate(ordering, start=1):
        ranks[idx] = rank
    out = ss.df.copy()
    out["ranking"] = ranks
    return out.sort_values(by="ranking")


def download_excel(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to Excel bytes."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        df.to_excel(w, index=False)
    return buf.getvalue()


# --- Binary Strategy ---
def binary_start():
    """Initialize binary insertion sort."""
    n = get_n_items()
    if n == 0:
        return

    order = list(range(n))
    random.shuffle(order)

    # First item goes directly to sorted list
    ss.binary_order = order
    ss.binary_sorted = [order[0]]
    ss.binary_i = 1
    ss.binary_candidate = None
    ss.binary_low = None
    ss.binary_high = None
    ss.binary_mid = None
    ss.binary_comparisons = 0
    ss.in_rating_mode = True

    # Setup first comparison
    if n > 1:
        binary_setup_next()


def binary_setup_next():
    """Setup next candidate for comparison."""
    if ss.binary_i >= len(ss.binary_order):
        ss.binary_candidate = None
        return

    candidate = ss.binary_order[ss.binary_i]
    n_sorted = len(ss.binary_sorted)

    ss.binary_candidate = candidate
    ss.binary_low = 0
    ss.binary_high = n_sorted - 1
    ss.binary_mid = (0 + n_sorted - 1) // 2


def binary_get_pair() -> Optional[Tuple[int, int]]:
    """Get current pair to compare."""
    if ss.binary_candidate is None:
        binary_setup_next()

    if ss.binary_candidate is None or ss.binary_mid is None:
        return None

    return (ss.binary_candidate, ss.binary_sorted[ss.binary_mid])


def binary_record(left_wins: bool):
    """Record comparison result."""
    ss.binary_comparisons += 1

    if left_wins:
        ss.binary_high = ss.binary_mid - 1
    else:
        ss.binary_low = ss.binary_mid + 1

    if ss.binary_low > ss.binary_high:
        # Found position
        sorted_list = list(ss.binary_sorted)
        sorted_list.insert(ss.binary_low, ss.binary_candidate)
        ss.binary_sorted = sorted_list
        ss.binary_i += 1
        ss.binary_candidate = None
        ss.binary_low = None
        ss.binary_high = None
        ss.binary_mid = None
        binary_setup_next()
    else:
        ss.binary_mid = (ss.binary_low + ss.binary_high) // 2


def binary_is_done() -> bool:
    """Check if binary sort is complete."""
    return len(ss.binary_sorted) == get_n_items()


# --- Elo Strategy ---
def elo_start():
    """Initialize Elo tournament."""
    n = get_n_items()
    if n == 0:
        return

    games_per = ss.get("elo_games_per_idea", 5)
    total = max(n * games_per // 2, n - 1)

    pairs = []
    while len(pairs) < total:
        i, j = random.sample(range(n), 2)
        pairs.append((i, j))

    ss.elo_pairs = pairs
    ss.elo_idx = 0
    ss.elo_ratings = {i: 1500.0 for i in range(n)}
    ss.elo_done = False
    ss.in_rating_mode = True


def elo_get_pair() -> Optional[Tuple[int, int]]:
    """Get current Elo pair."""
    if ss.elo_done or ss.elo_idx >= len(ss.elo_pairs):
        return None
    return ss.elo_pairs[ss.elo_idx]


def elo_record(left_wins: bool):
    """Record Elo result."""
    if ss.elo_done:
        return

    i, j = ss.elo_pairs[ss.elo_idx]
    winner = i if left_wins else j

    # Elo update
    ra, rb = ss.elo_ratings[i], ss.elo_ratings[j]
    qa = 10 ** (ra / 400)
    qb = 10 ** (rb / 400)
    ea = qa / (qa + qb)
    eb = qb / (qa + qb)
    k = 32

    if winner == i:
        ss.elo_ratings[i] = ra + k * (1 - ea)
        ss.elo_ratings[j] = rb + k * (0 - eb)
    else:
        ss.elo_ratings[i] = ra + k * (0 - ea)
        ss.elo_ratings[j] = rb + k * (1 - eb)

    ss.elo_idx += 1
    if ss.elo_idx >= len(ss.elo_pairs):
        ss.elo_done = True


def elo_finish():
    ss.elo_done = True


def elo_ordering() -> List[int]:
    """Get Elo ordering."""
    return sorted(ss.elo_ratings.keys(), key=lambda i: ss.elo_ratings[i], reverse=True)


# --- Swiss Strategy ---
def swiss_start():
    """Initialize Swiss tournament."""
    n = get_n_items()
    if n == 0:
        return

    ss.swiss_points = {i: 0 for i in range(n)}
    ss.swiss_round = 1
    ss.swiss_idx = 0
    ss.swiss_done = False
    ss.in_rating_mode = True
    swiss_build_pairs()


def swiss_build_pairs():
    """Build pairs for current round."""
    n = get_n_items()
    indices = list(range(n))
    random.shuffle(indices)
    indices.sort(key=lambda i: ss.swiss_points[i], reverse=True)

    pairs = []
    i = 0
    while i < n - 1:
        pairs.append((indices[i], indices[i + 1]))
        i += 2

    # Bye for odd number
    if i == n - 1:
        ss.swiss_points[indices[i]] += 1

    ss.swiss_pairs = pairs
    ss.swiss_idx = 0


def swiss_get_pair() -> Optional[Tuple[int, int]]:
    """Get current Swiss pair."""
    if ss.swiss_done:
        return None

    if ss.swiss_idx >= len(ss.swiss_pairs):
        if ss.swiss_round < ss.swiss_rounds_total:
            ss.swiss_round += 1
            swiss_build_pairs()
        else:
            ss.swiss_done = True
            return None

    if ss.swiss_idx >= len(ss.swiss_pairs):
        return None

    return ss.swiss_pairs[ss.swiss_idx]


def swiss_record(left_wins: bool):
    """Record Swiss result."""
    if ss.swiss_done:
        return

    i, j = ss.swiss_pairs[ss.swiss_idx]
    winner = i if left_wins else j
    ss.swiss_points[winner] += 1
    ss.swiss_idx += 1

    if ss.swiss_idx >= len(ss.swiss_pairs):
        if ss.swiss_round >= ss.swiss_rounds_total:
            ss.swiss_done = True


def swiss_finish():
    ss.swiss_done = True


def swiss_ordering() -> List[int]:
    """Get Swiss ordering."""
    return sorted(ss.swiss_points.keys(), key=lambda i: (ss.swiss_points[i], -i), reverse=True)


# --- Sidebar ---
with st.sidebar:
    st.header("1) Upload ideas")
    file = st.file_uploader("Upload Excel/CSV", type=["xlsx", "csv"])

    if file:
        try:
            if file.name.lower().endswith(".csv"):
                ss.df = pd.read_csv(file)
            else:
                ss.df = pd.read_excel(file)
            st.success(f"Loaded {len(ss.df)} ideas.")
        except Exception as e:
            st.error(f"Error: {e}")

    if ss.df is not None:
        cols = list(ss.df.columns)

        st.header("2) Map columns")
        ss.id_col = st.selectbox("ID column", cols, index=0)
        ss.name_col = st.selectbox("Name column", cols, index=min(1, len(cols) - 1))
        ss.desc_col = st.selectbox("Description column", cols, index=min(2, len(cols) - 1))

        st.header("3) Choose ranking type")
        labels = list(STRATEGY_LABELS.values())
        keys = list(STRATEGY_LABELS.keys())
        idx = keys.index(ss.rating_strategy)
        label = st.radio("Strategy", labels, index=idx)
        ss.rating_strategy = keys[labels.index(label)]

        if ss.rating_strategy == STRATEGY_ELO:
            ss.elo_games_per_idea = st.slider("Games per idea", 2, 10, 5)
        elif ss.rating_strategy == STRATEGY_SWISS:
            ss.swiss_rounds_total = st.slider("Number of rounds", 2, 10, 3)

        st.header("4) Start / reset")
        if not ss.in_rating_mode:
            if st.button("Start rating mode", type="primary", use_container_width=True):
                if ss.rating_strategy == STRATEGY_BINARY:
                    binary_start()
                elif ss.rating_strategy == STRATEGY_ELO:
                    elo_start()
                elif ss.rating_strategy == STRATEGY_SWISS:
                    swiss_start()
                st.rerun()
        else:
            if st.button("Reset app", use_container_width=True):
                reset_all()
                st.rerun()


# --- Main Content ---
if ss.df is None:
    st.info("Upload an Excel/CSV file in the sidebar to begin.")
    st.stop()

with st.expander("Preview uploaded data"):
    st.dataframe(ss.df[[ss.id_col, ss.name_col, ss.desc_col]].head(20), use_container_width=True)

st.divider()

if not ss.in_rating_mode:
    st.warning("Choose a ranking type and click **Start rating mode** in the sidebar.")
    st.stop()

n_total = get_n_items()


# --- Binary UI ---
if ss.rating_strategy == STRATEGY_BINARY:
    st.subheader("Interactive sort (fewest comparisons)")

    n_sorted = len(ss.binary_sorted)
    c1, c2, c3 = st.columns(3)
    c1.metric("Ideas total", n_total)
    c2.metric("Already placed", n_sorted)
    c3.metric("Comparisons", ss.binary_comparisons)
    st.progress(n_sorted / n_total if n_total > 0 else 0)

    if binary_is_done():
        st.success("All ideas have a **unique ranking**!")
        ranked = build_ranked_df(ss.binary_sorted)
        st.dataframe(ranked, use_container_width=True, height=400)
        st.download_button("Download Excel", download_excel(ranked), "ranking_binary.xlsx")
        st.stop()

    pair = binary_get_pair()
    if pair is None:
        st.info("Preparing...")
        st.rerun()

    left_idx, right_idx = pair
    left = get_card(left_idx)
    right = get_card(right_idx)

    st.markdown("**Choose which idea has MORE impact**")
    col1, col2 = st.columns(2)

    # Use on_click callbacks to avoid button state persistence bug
    def handle_bin_left():
        binary_record(left_wins=True)

    def handle_bin_right():
        binary_record(left_wins=False)

    with col1:
        st.markdown(f"#### Candidate\n**{left['id']} — {left['name']}**")
        st.write(left["desc"])
        st.button("This one has more impact", key="bin_left", use_container_width=True, on_click=handle_bin_left)

    with col2:
        st.markdown(f"#### Current position\n**{right['id']} — {right['name']}**")
        st.write(right["desc"])
        st.button("This one has more impact", key="bin_right", use_container_width=True, on_click=handle_bin_right)


# --- Elo UI ---
elif ss.rating_strategy == STRATEGY_ELO:
    st.subheader("Elo tournament (rating-based)")

    total = len(ss.elo_pairs)
    done = min(ss.elo_idx, total)
    c1, c2, c3 = st.columns(3)
    c1.metric("Ideas total", n_total)
    c2.metric("Matches done", done)
    c3.metric("Planned", total)
    st.progress(done / total if total > 0 else 0)

    if ss.elo_done or st.button("Finish Elo ranking now"):
        elo_finish()
        ordering = elo_ordering()
        ranked = build_ranked_df(ordering)
        ranked["elo_rating"] = [ss.elo_ratings[i] for i in range(len(ss.df))]
        st.success("Elo ranking computed.")
        st.dataframe(ranked, use_container_width=True, height=400)
        st.download_button("Download Excel", download_excel(ranked), "ranking_elo.xlsx")
        st.stop()

    pair = elo_get_pair()
    if pair is None:
        st.info("No more matches.")
        st.stop()

    left_idx, right_idx = pair
    left = get_card(left_idx)
    right = get_card(right_idx)

    st.markdown("**Which idea has MORE impact?**")
    col1, col2 = st.columns(2)

    # Use on_click callbacks to avoid button state persistence bug
    def handle_elo_left():
        elo_record(left_wins=True)

    def handle_elo_right():
        elo_record(left_wins=False)

    with col1:
        st.markdown(f"#### Left\n**{left['id']} — {left['name']}**")
        st.write(left["desc"])
        st.caption(f"Elo: {ss.elo_ratings[left_idx]:.0f}")
        st.button("This one has more impact", key="elo_left", use_container_width=True, on_click=handle_elo_left)

    with col2:
        st.markdown(f"#### Right\n**{right['id']} — {right['name']}**")
        st.write(right["desc"])
        st.caption(f"Elo: {ss.elo_ratings[right_idx]:.0f}")
        st.button("This one has more impact", key="elo_right", use_container_width=True, on_click=handle_elo_right)


# --- Swiss UI ---
elif ss.rating_strategy == STRATEGY_SWISS:
    st.subheader("Swiss rounds (batch-style)")

    c1, c2, c3 = st.columns(3)
    c1.metric("Ideas total", n_total)
    c2.metric("Current round", ss.swiss_round)
    c3.metric("Total rounds", ss.swiss_rounds_total)
    if len(ss.swiss_pairs) > 0:
        st.progress(ss.swiss_idx / len(ss.swiss_pairs))

    if ss.swiss_done or st.button("Finish Swiss ranking now"):
        swiss_finish()
        ordering = swiss_ordering()
        ranked = build_ranked_df(ordering)
        ranked["points"] = [ss.swiss_points[i] for i in range(len(ss.df))]
        st.success("Swiss ranking computed.")
        st.dataframe(ranked, use_container_width=True, height=400)
        st.download_button("Download Excel", download_excel(ranked), "ranking_swiss.xlsx")
        st.stop()

    pair = swiss_get_pair()
    if pair is None:
        st.info("Processing next round...")
        st.rerun()

    left_idx, right_idx = pair
    left = get_card(left_idx)
    right = get_card(right_idx)

    st.markdown(f"**Round {ss.swiss_round}/{ss.swiss_rounds_total} — Which has MORE impact?**")
    col1, col2 = st.columns(2)

    # Use on_click callbacks to avoid button state persistence bug
    def handle_swiss_left():
        swiss_record(left_wins=True)

    def handle_swiss_right():
        swiss_record(left_wins=False)

    with col1:
        st.markdown(f"#### Left\n**{left['id']} — {left['name']}**")
        st.write(left["desc"])
        st.caption(f"Points: {ss.swiss_points[left_idx]}")
        st.button("This one has more impact", key="swiss_left", use_container_width=True, on_click=handle_swiss_left)

    with col2:
        st.markdown(f"#### Right\n**{right['id']} — {right['name']}**")
        st.write(right["desc"])
        st.caption(f"Points: {ss.swiss_points[right_idx]}")
        st.button("This one has more impact", key="swiss_right", use_container_width=True, on_click=handle_swiss_right)


# --- Debug Log Display ---
if DEBUG and "debug_log" in st.session_state and st.session_state.debug_log:
    st.divider()
    with st.expander("Debug Log (last 30 entries)", expanded=False):
        st.code("\n".join(st.session_state.debug_log[-30:]))

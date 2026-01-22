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
import json
import os
import random
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

import pandas as pd
import qrcode
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

# Sessions directory
SESSIONS_DIR = Path(__file__).parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)


# --- Debug Helper ---
def debug(msg: str):
    """Log debug message if DEBUG is enabled."""
    if DEBUG:
        if "debug_log" not in st.session_state:
            st.session_state.debug_log = []
        st.session_state.debug_log.append(msg)


# --- Session Management ---
def create_session(name: str, strategy: str, df: pd.DataFrame,
                   id_col: str, name_col: str, desc_col: str,
                   settings: Dict[str, Any]) -> str:
    """Create a new ranking session and return its ID."""
    session_id = str(uuid.uuid4())[:8]
    session_data = {
        "id": session_id,
        "name": name,
        "strategy": strategy,
        "settings": settings,
        "columns": {
            "id": id_col,
            "name": name_col,
            "desc": desc_col,
        },
        "data": df.to_dict(orient="records"),
        "users": {},  # username -> {ordering: [...], completed: bool, ...}
        "expected_users": [],  # Optional list of expected usernames
    }
    session_path = SESSIONS_DIR / f"{session_id}.json"
    with open(session_path, "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=2, default=str)
    return session_id


def load_session(session_id: str) -> Optional[Dict]:
    """Load a session by ID."""
    session_path = SESSIONS_DIR / f"{session_id}.json"
    if not session_path.exists():
        return None
    with open(session_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_session(session_data: Dict):
    """Save session data back to file."""
    session_id = session_data["id"]
    session_path = SESSIONS_DIR / f"{session_id}.json"
    with open(session_path, "w", encoding="utf-8") as f:
        json.dump(session_data, f, indent=2, default=str)


def list_sessions() -> List[Dict]:
    """List all available sessions with basic info."""
    sessions = []
    for path in SESSIONS_DIR.glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                sessions.append({
                    "id": data["id"],
                    "name": data["name"],
                    "strategy": data["strategy"],
                    "items_count": len(data["data"]),
                    "users_completed": sum(1 for u in data["users"].values() if u.get("completed")),
                    "users_total": len(data["users"]),
                })
        except Exception:
            continue
    return sessions


def delete_session(session_id: str) -> bool:
    """Delete a session by ID."""
    session_path = SESSIONS_DIR / f"{session_id}.json"
    if session_path.exists():
        session_path.unlink()
        return True
    return False


def save_user_result(session_id: str, username: str, ordering: List[int],
                     extra_data: Optional[Dict] = None):
    """Save a user's ranking result to the session."""
    session = load_session(session_id)
    if session is None:
        return False

    user_data = {
        "ordering": ordering,
        "completed": True,
    }
    if extra_data:
        user_data.update(extra_data)

    session["users"][username] = user_data
    save_session(session)
    return True


def compute_average_ranking(session: Dict) -> pd.DataFrame:
    """Compute average ranking from all user results."""
    df = pd.DataFrame(session["data"])
    n_items = len(df)

    # Collect all user rankings
    user_rankings = {}
    for username, user_data in session["users"].items():
        if user_data.get("completed") and "ordering" in user_data:
            ordering = user_data["ordering"]
            # Convert ordering to ranks (1-indexed)
            ranks = [0] * n_items
            for rank, idx in enumerate(ordering, start=1):
                ranks[idx] = rank
            user_rankings[username] = ranks

    if not user_rankings:
        return df

    # Add individual user rank columns
    for username, ranks in user_rankings.items():
        df[f"rank_{username}"] = ranks

    # Compute average rank
    rank_cols = [f"rank_{u}" for u in user_rankings.keys()]
    df["avg_rank"] = df[rank_cols].mean(axis=1)
    df["rank_std"] = df[rank_cols].std(axis=1)

    # Sort by average rank
    df = df.sort_values("avg_rank")
    df["final_ranking"] = range(1, len(df) + 1)

    return df


def download_session_results(session: Dict) -> bytes:
    """Generate Excel file with individual and average rankings."""
    df = compute_average_ranking(session)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        # Sheet 1: Combined results
        df.to_excel(writer, sheet_name="Combined Rankings", index=False)

        # Sheet 2: Individual user results
        cols = session["columns"]
        for username, user_data in session["users"].items():
            if user_data.get("completed") and "ordering" in user_data:
                user_df = pd.DataFrame(session["data"])
                ordering = user_data["ordering"]
                ranks = [0] * len(user_df)
                for rank, idx in enumerate(ordering, start=1):
                    ranks[idx] = rank
                user_df["ranking"] = ranks
                user_df = user_df.sort_values("ranking")
                user_df.to_excel(writer, sheet_name=f"User_{username[:20]}", index=False)

    return buf.getvalue()


# --- Page Configuration ---
st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")
st.title(f"{APP_ICON} {APP_TITLE}")
st.caption("Upload ideas, compare two at a time, and get a unique impact ranking.")


# --- State Initialization ---
def init_state():
    """Initialize all session state with defaults."""
    ss = st.session_state

    # View mode: "home" | "create_session" | "join_session" | "rating" | "results" | "solo"
    ss.setdefault("view_mode", "home")

    # Session mode state
    ss.setdefault("current_session_id", None)
    ss.setdefault("current_user", None)

    # Data / mapping (used for solo mode and session creation)
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


def reset_rating_state():
    """Reset only rating-related state (keep session info)."""
    ss = st.session_state
    # Binary state
    ss.binary_order = []
    ss.binary_sorted = []
    ss.binary_i = 0
    ss.binary_low = None
    ss.binary_high = None
    ss.binary_mid = None
    ss.binary_candidate = None
    ss.binary_comparisons = 0
    # Elo state
    ss.elo_pairs = []
    ss.elo_idx = 0
    ss.elo_ratings = {}
    ss.elo_done = False
    # Swiss state
    ss.swiss_points = {}
    ss.swiss_round = 1
    ss.swiss_pairs = []
    ss.swiss_idx = 0
    ss.swiss_done = False
    ss.in_rating_mode = False


def go_home():
    """Navigate to home view."""
    reset_rating_state()
    ss = st.session_state
    ss.view_mode = "home"
    ss.current_session_id = None
    ss.current_user = None
    ss.df = None


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


def generate_session_qr(session_id: str) -> bytes:
    """Generate a QR code image for joining a session."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(session_id)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
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


# --- Helper: Load session data into state ---
def load_session_into_state(session_id: str) -> bool:
    """Load a session's data into session_state for rating."""
    session = load_session(session_id)
    if session is None:
        return False

    ss.df = pd.DataFrame(session["data"])
    ss.id_col = session["columns"]["id"]
    ss.name_col = session["columns"]["name"]
    ss.desc_col = session["columns"]["desc"]
    ss.rating_strategy = session["strategy"]

    # Load strategy-specific settings
    settings = session.get("settings", {})
    if "elo_games_per_idea" in settings:
        ss.elo_games_per_idea = settings["elo_games_per_idea"]
    if "swiss_rounds_total" in settings:
        ss.swiss_rounds_total = settings["swiss_rounds_total"]

    return True


def finish_session_rating():
    """Save the user's completed ranking to the session."""
    if ss.current_session_id is None or ss.current_user is None:
        return

    # Get the final ordering based on strategy
    if ss.rating_strategy == STRATEGY_BINARY:
        ordering = ss.binary_sorted
        extra = {"comparisons": ss.binary_comparisons}
    elif ss.rating_strategy == STRATEGY_ELO:
        ordering = elo_ordering()
        extra = {"elo_ratings": dict(ss.elo_ratings)}
    elif ss.rating_strategy == STRATEGY_SWISS:
        ordering = swiss_ordering()
        extra = {"swiss_points": dict(ss.swiss_points)}
    else:
        ordering = []
        extra = {}

    save_user_result(ss.current_session_id, ss.current_user, ordering, extra)


# =============================================================================
# VIEW: HOME
# =============================================================================
def render_home_view():
    """Render the home view with options to create, join, or use solo mode."""
    st.subheader("Choose how to rank")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### Create Session")
        st.write("Create a new ranking session for multiple users to participate.")
        if st.button("Create Session", type="primary", use_container_width=True):
            ss.view_mode = "create_session"
            st.rerun()

    with col2:
        st.markdown("### Join Session")
        st.write("Join an existing ranking session to submit your rankings.")
        if st.button("Join Session", type="primary", use_container_width=True):
            ss.view_mode = "join_session"
            st.rerun()

    with col3:
        st.markdown("### Solo Mode")
        st.write("Rank items by yourself without creating a session.")
        if st.button("Solo Mode", use_container_width=True):
            ss.view_mode = "solo"
            st.rerun()

    # Show existing sessions
    st.divider()
    st.subheader("Existing Sessions")

    sessions = list_sessions()
    if not sessions:
        st.info("No sessions created yet.")
    else:
        for sess in sessions:
            st.markdown("---")
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            c1.markdown(f"**{sess['name']}**")
            c2.write(f"Strategy: {STRATEGY_LABELS.get(sess['strategy'], sess['strategy'])}")
            c3.write(f"Users: {sess['users_completed']}/{sess['users_total']} completed")

            with c4:
                if st.button("View", key=f"view_{sess['id']}", use_container_width=True):
                    ss.current_session_id = sess["id"]
                    ss.view_mode = "results"
                    st.rerun()

                if st.button("Delete", key=f"del_{sess['id']}", use_container_width=True):
                    delete_session(sess["id"])
                    st.rerun()


# =============================================================================
# VIEW: CREATE SESSION
# =============================================================================
def render_create_session_view():
    """Render the session creation form."""
    st.subheader("Create New Ranking Session")

    if st.button("Back to Home"):
        go_home()
        st.rerun()

    st.divider()

    # Session name
    session_name = st.text_input("Session Name", placeholder="e.g., Q1 Feature Prioritization")

    # File upload
    st.markdown("#### Upload Ideas")
    file = st.file_uploader("Upload Excel/CSV", type=["xlsx", "csv"], key="create_file")

    temp_df = None
    if file:
        try:
            if file.name.lower().endswith(".csv"):
                temp_df = pd.read_csv(file)
            else:
                temp_df = pd.read_excel(file)
            st.success(f"Loaded {len(temp_df)} ideas.")

            with st.expander("Preview data"):
                st.dataframe(temp_df.head(10), use_container_width=True)
        except Exception as e:
            st.error(f"Error loading file: {e}")

    if temp_df is not None:
        cols = list(temp_df.columns)

        st.markdown("#### Map Columns")
        col1, col2, col3 = st.columns(3)
        with col1:
            id_col = st.selectbox("ID column", cols, index=0, key="create_id")
        with col2:
            name_col = st.selectbox("Name column", cols, index=min(1, len(cols) - 1), key="create_name")
        with col3:
            desc_col = st.selectbox("Description column", cols, index=min(2, len(cols) - 1), key="create_desc")

        st.markdown("#### Ranking Strategy")
        labels = list(STRATEGY_LABELS.values())
        keys = list(STRATEGY_LABELS.keys())
        label = st.radio("Strategy", labels, index=0, key="create_strategy")
        strategy = keys[labels.index(label)]

        settings = {}
        if strategy == STRATEGY_ELO:
            settings["elo_games_per_idea"] = st.slider("Games per idea", 2, 10, 5, key="create_elo")
        elif strategy == STRATEGY_SWISS:
            settings["swiss_rounds_total"] = st.slider("Number of rounds", 2, 10, 3, key="create_swiss")

        st.divider()

        if st.button("Create Session", type="primary", use_container_width=True, disabled=not session_name):
            if session_name:
                session_id = create_session(
                    name=session_name,
                    strategy=strategy,
                    df=temp_df,
                    id_col=id_col,
                    name_col=name_col,
                    desc_col=desc_col,
                    settings=settings,
                )
                st.success(f"Session created! ID: **{session_id}**")
                st.info("Share the session ID with participants or let them scan the QR code.")

                col_qr, col_info = st.columns([1, 2])
                with col_qr:
                    st.image(generate_session_qr(session_id), caption=f"Session: {session_id}", width=200)
                with col_info:
                    st.markdown("**How to join:**")
                    st.markdown("1. Open the app on your device")
                    st.markdown("2. Click **Join Session**")
                    st.markdown(f"3. Select **{session_name}**")

                if st.button("Go to Home"):
                    go_home()
                    st.rerun()
            else:
                st.error("Please enter a session name.")


# =============================================================================
# VIEW: JOIN SESSION
# =============================================================================
def render_join_session_view():
    """Render the session join form."""
    st.subheader("Join Ranking Session")

    if st.button("Back to Home"):
        go_home()
        st.rerun()

    st.divider()

    sessions = list_sessions()

    if not sessions:
        st.warning("No sessions available. Ask an admin to create one first.")
        return

    # Session selection
    session_names = {s["name"]: s["id"] for s in sessions}
    selected_name = st.selectbox("Select Session", list(session_names.keys()))
    selected_id = session_names[selected_name]

    # Show session info
    session = load_session(selected_id)
    if session:
        st.info(f"**Items to rank:** {len(session['data'])} | "
                f"**Strategy:** {STRATEGY_LABELS.get(session['strategy'], session['strategy'])} | "
                f"**Users completed:** {len([u for u in session['users'].values() if u.get('completed')])}")

    # Username input
    username = st.text_input("Your Name", placeholder="Enter your name")

    # Check if user already completed
    if session and username:
        if username in session["users"] and session["users"][username].get("completed"):
            st.warning(f"User '{username}' has already completed this session.")

    st.divider()

    if st.button("Start Ranking", type="primary", use_container_width=True, disabled=not username):
        if username:
            ss.current_session_id = selected_id
            ss.current_user = username
            if load_session_into_state(selected_id):
                ss.view_mode = "rating"
                # Start the rating process
                if ss.rating_strategy == STRATEGY_BINARY:
                    binary_start()
                elif ss.rating_strategy == STRATEGY_ELO:
                    elo_start()
                elif ss.rating_strategy == STRATEGY_SWISS:
                    swiss_start()
                st.rerun()
            else:
                st.error("Failed to load session.")
        else:
            st.error("Please enter your name.")


# =============================================================================
# VIEW: SOLO MODE
# =============================================================================
def render_solo_view():
    """Render the solo mode interface (original functionality)."""
    with st.sidebar:
        st.header("Solo Mode")
        if st.button("Back to Home", use_container_width=True):
            go_home()
            st.rerun()

        st.divider()

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
                if st.button("Reset", use_container_width=True):
                    reset_rating_state()
                    ss.df = None
                    st.rerun()

    # Main content for solo mode
    if ss.df is None:
        st.info("Upload an Excel/CSV file in the sidebar to begin.")
        return

    with st.expander("Preview uploaded data"):
        st.dataframe(ss.df[[ss.id_col, ss.name_col, ss.desc_col]].head(20), use_container_width=True)

    st.divider()

    if not ss.in_rating_mode:
        st.warning("Choose a ranking type and click **Start rating mode** in the sidebar.")
        return

    # Render ranking UI
    render_ranking_ui(is_session=False)


# =============================================================================
# VIEW: RATING (Session Mode)
# =============================================================================
def render_rating_view():
    """Render the rating interface for session mode."""
    session = load_session(ss.current_session_id)
    if session is None:
        st.error("Session not found.")
        if st.button("Go Home"):
            go_home()
            st.rerun()
        return

    # Header with session info
    st.markdown(f"**Session:** {session['name']} | **User:** {ss.current_user}")

    if st.button("Exit Session", use_container_width=False):
        go_home()
        st.rerun()

    st.divider()

    # Render the ranking UI
    render_ranking_ui(is_session=True)


# =============================================================================
# VIEW: RESULTS
# =============================================================================
def render_results_view():
    """Render the results view for a session."""
    session = load_session(ss.current_session_id)
    if session is None:
        st.error("Session not found.")
        if st.button("Go Home"):
            go_home()
            st.rerun()
        return

    st.subheader(f"Results: {session['name']}")

    if st.button("Back to Home"):
        go_home()
        st.rerun()

    st.divider()

    # Session info with QR code
    col_metrics, col_qr = st.columns([3, 1])

    with col_metrics:
        c1, c2, c3 = st.columns(3)
        c1.metric("Items", len(session["data"]))
        c2.metric("Users Participated", len(session["users"]))
        completed = len([u for u in session["users"].values() if u.get("completed")])
        c3.metric("Completed", completed)

    with col_qr:
        st.image(generate_session_qr(ss.current_session_id), caption="Scan to join", width=120)

    st.divider()

    # Show user status
    st.markdown("#### Participants")
    if session["users"]:
        for username, user_data in session["users"].items():
            status = "Completed" if user_data.get("completed") else "In Progress"
            st.write(f"- **{username}**: {status}")
    else:
        st.info("No users have participated yet.")

    st.divider()

    # Show combined results if anyone has completed
    if completed > 0:
        st.markdown("#### Combined Rankings")
        df = compute_average_ranking(session)
        st.dataframe(df, use_container_width=True, height=400)

        st.download_button(
            "Download Results (Excel)",
            download_session_results(session),
            f"ranking_{session['name'].replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("No completed rankings yet. Results will appear here once users finish.")


# =============================================================================
# RANKING UI (shared between solo and session modes)
# =============================================================================
def render_ranking_ui(is_session: bool = False):
    """Render the pairwise comparison UI."""
    n_total = get_n_items()

    def handle_completion(ordering, ranked_df, extra_col_name=None, extra_col_data=None):
        """Handle ranking completion - save to session if applicable."""
        if is_session:
            finish_session_rating()
            st.success("Your ranking has been saved!")
            st.balloons()
            st.dataframe(ranked_df, use_container_width=True, height=400)

            if st.button("View Session Results", type="primary"):
                ss.view_mode = "results"
                st.rerun()

            if st.button("Back to Home"):
                go_home()
                st.rerun()
        else:
            st.success("All ideas have a **unique ranking**!")
            st.dataframe(ranked_df, use_container_width=True, height=400)
            st.download_button("Download Excel", download_excel(ranked_df), "ranking.xlsx")

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
            ranked = build_ranked_df(ss.binary_sorted)
            handle_completion(ss.binary_sorted, ranked)
            return

        pair = binary_get_pair()
        if pair is None:
            st.info("Preparing...")
            st.rerun()

        left_idx, right_idx = pair
        left = get_card(left_idx)
        right = get_card(right_idx)

        st.markdown("**Choose which idea has MORE impact**")
        col1, col2 = st.columns(2)

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
            handle_completion(ordering, ranked)
            return

        pair = elo_get_pair()
        if pair is None:
            st.info("No more matches.")
            return

        left_idx, right_idx = pair
        left = get_card(left_idx)
        right = get_card(right_idx)

        st.markdown("**Which idea has MORE impact?**")
        col1, col2 = st.columns(2)

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
            handle_completion(ordering, ranked)
            return

        pair = swiss_get_pair()
        if pair is None:
            st.info("Processing next round...")
            st.rerun()

        left_idx, right_idx = pair
        left = get_card(left_idx)
        right = get_card(right_idx)

        st.markdown(f"**Round {ss.swiss_round}/{ss.swiss_rounds_total} — Which has MORE impact?**")
        col1, col2 = st.columns(2)

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


# =============================================================================
# MAIN VIEW ROUTER
# =============================================================================
if ss.view_mode == "home":
    render_home_view()
elif ss.view_mode == "create_session":
    render_create_session_view()
elif ss.view_mode == "join_session":
    render_join_session_view()
elif ss.view_mode == "solo":
    render_solo_view()
elif ss.view_mode == "rating":
    render_rating_view()
elif ss.view_mode == "results":
    render_results_view()
else:
    render_home_view()


# --- Debug Log Display ---
if DEBUG and "debug_log" in st.session_state and st.session_state.debug_log:
    st.divider()
    with st.expander("Debug Log (last 30 entries)", expanded=False):
        st.code("\n".join(st.session_state.debug_log[-30:]))

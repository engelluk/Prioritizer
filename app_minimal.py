"""
Minimal test - hardcoded data, no file upload.
Run with: streamlit run app_minimal.py
"""

import random
import streamlit as st

st.set_page_config(page_title="Minimal Test", layout="wide")
st.title("Minimal Prioritizer Test")

# Debug output
def debug(msg):
    if "debug_log" not in st.session_state:
        st.session_state.debug_log = []
    st.session_state.debug_log.append(msg)

# Initialize state - AVOID RESERVED NAMES like 'items', 'keys', 'values'
if "initialized" not in st.session_state:
    debug("Initializing state...")
    st.session_state.initialized = True
    st.session_state.started = False
    st.session_state.data_list = ["Item A", "Item B", "Item C", "Item D", "Item E"]
    st.session_state.order_list = []
    st.session_state.sorted_list = []
    st.session_state.current_idx = 0
    st.session_state.candidate_val = None
    st.session_state.low_val = None
    st.session_state.high_val = None
    st.session_state.mid_val = None
    st.session_state.comparison_count = 0
    st.session_state.debug_log = []
    st.session_state.needs_rerun = False  # Flag to handle rerun properly

debug(f"--- Page render ---")
debug(f"started={st.session_state.started}")
debug(f"sorted_list={st.session_state.sorted_list}")
debug(f"current_idx={st.session_state.current_idx}")
debug(f"needs_rerun={st.session_state.needs_rerun}")

# Handle pending rerun (clear the flag and stop - next render will show updated state)
if st.session_state.needs_rerun:
    debug("Clearing needs_rerun flag")
    st.session_state.needs_rerun = False
    st.rerun()

n_items = len(st.session_state.data_list)

# Sidebar
with st.sidebar:
    st.header("State")
    st.write(f"started: {st.session_state.started}")
    st.write(f"sorted_list: {st.session_state.sorted_list}")
    st.write(f"current_idx: {st.session_state.current_idx}")
    st.write(f"candidate_val: {st.session_state.candidate_val}")
    st.write(f"low/high/mid: {st.session_state.low_val}/{st.session_state.high_val}/{st.session_state.mid_val}")
    st.write(f"comparisons: {st.session_state.comparison_count}")

    st.divider()

    if not st.session_state.started:
        if st.button("START", type="primary"):
            debug("START clicked")
            order = list(range(n_items))
            random.shuffle(order)
            st.session_state.order_list = order
            st.session_state.sorted_list = [order[0]]
            st.session_state.current_idx = 1
            st.session_state.started = True
            st.session_state.comparison_count = 0

            # Setup first candidate
            if n_items > 1:
                st.session_state.candidate_val = order[1]
                st.session_state.low_val = 0
                st.session_state.high_val = 0
                st.session_state.mid_val = 0

            debug(f"After START: sorted_list={st.session_state.sorted_list}, candidate_val={st.session_state.candidate_val}")
            st.session_state.needs_rerun = True
            st.rerun()
    else:
        if st.button("RESET"):
            debug("RESET clicked")
            st.session_state.started = False
            st.session_state.sorted_list = []
            st.session_state.current_idx = 0
            st.session_state.candidate_val = None
            st.session_state.needs_rerun = True
            st.rerun()

# Main area
st.divider()

if not st.session_state.started:
    st.info("Click START in the sidebar")
    st.stop()

# Check if done
is_done = len(st.session_state.sorted_list) == n_items
debug(f"is_done={is_done} (sorted_list has {len(st.session_state.sorted_list)}, need {n_items})")

if is_done:
    st.success(f"DONE! Order: {st.session_state.sorted_list}")
    st.balloons()
    st.stop()

# Get current pair
candidate = st.session_state.candidate_val
mid = st.session_state.mid_val

debug(f"candidate={candidate}, mid={mid}")

if candidate is None or mid is None:
    st.warning("No candidate - setting up next...")
    if st.session_state.current_idx < len(st.session_state.order_list):
        st.session_state.candidate_val = st.session_state.order_list[st.session_state.current_idx]
        n_sorted = len(st.session_state.sorted_list)
        st.session_state.low_val = 0
        st.session_state.high_val = n_sorted - 1
        st.session_state.mid_val = (n_sorted - 1) // 2
        st.session_state.needs_rerun = True
        st.rerun()
    else:
        st.error("Something is wrong")
        st.stop()

left_idx = candidate
right_idx = st.session_state.sorted_list[mid]

st.subheader("Which is better?")
st.write(f"Comparing index {left_idx} vs index {right_idx}")

col1, col2 = st.columns(2)

# Use callbacks instead of checking button return value
def handle_left_click():
    debug("LEFT callback triggered")
    process_comparison(left_wins=True)

def handle_right_click():
    debug("RIGHT callback triggered")
    process_comparison(left_wins=False)

def process_comparison(left_wins):
    debug(f"Processing comparison: left_wins={left_wins}")

    st.session_state.comparison_count += 1

    if left_wins:
        st.session_state.high_val = st.session_state.mid_val - 1
    else:
        st.session_state.low_val = st.session_state.mid_val + 1

    debug(f"After update: low={st.session_state.low_val}, high={st.session_state.high_val}")

    if st.session_state.low_val > st.session_state.high_val:
        # Found position - insert
        debug(f"Inserting {st.session_state.candidate_val} at position {st.session_state.low_val}")
        new_sorted = list(st.session_state.sorted_list)
        new_sorted.insert(st.session_state.low_val, st.session_state.candidate_val)
        st.session_state.sorted_list = new_sorted
        st.session_state.current_idx += 1

        debug(f"New sorted_list: {st.session_state.sorted_list}, new current_idx: {st.session_state.current_idx}")

        # Setup next candidate
        if st.session_state.current_idx < len(st.session_state.order_list):
            next_candidate = st.session_state.order_list[st.session_state.current_idx]
            n_sorted = len(st.session_state.sorted_list)
            st.session_state.candidate_val = next_candidate
            st.session_state.low_val = 0
            st.session_state.high_val = n_sorted - 1
            st.session_state.mid_val = (n_sorted - 1) // 2
            debug(f"Next candidate: {next_candidate}, low=0, high={n_sorted-1}, mid={(n_sorted-1)//2}")
        else:
            st.session_state.candidate_val = None
            st.session_state.low_val = None
            st.session_state.high_val = None
            st.session_state.mid_val = None
            debug("No more candidates")
    else:
        st.session_state.mid_val = (st.session_state.low_val + st.session_state.high_val) // 2
        debug(f"Continue search, new mid={st.session_state.mid_val}")

with col1:
    st.markdown(f"### {st.session_state.data_list[left_idx]}")
    st.caption(f"(index {left_idx})")
    st.button("Choose LEFT", key="left", use_container_width=True, on_click=handle_left_click)

with col2:
    st.markdown(f"### {st.session_state.data_list[right_idx]}")
    st.caption(f"(index {right_idx})")
    st.button("Choose RIGHT", key="right", use_container_width=True, on_click=handle_right_click)

# Show debug log
st.divider()
st.subheader("Debug Log (last 30)")
if st.session_state.debug_log:
    st.code("\n".join(st.session_state.debug_log[-30:]))

st.caption(f"Progress: {len(st.session_state.sorted_list)}/{n_items}")

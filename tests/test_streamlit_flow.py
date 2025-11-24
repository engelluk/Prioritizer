"""
Test that simulates Streamlit's rerun flow.
This mimics what happens when the app.py script runs.

Run with: python test_streamlit_flow.py
"""

import sys
from typing import Optional, Tuple


class MockSessionState(dict):
    """Mock Streamlit session_state."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"No attribute '{key}'")

    def __setattr__(self, key, value):
        self[key] = value

    def setdefault(self, key, default):
        if key not in self:
            self[key] = default
        return self[key]

    def get(self, key, default=None):
        return self[key] if key in self else default


class MockStreamlit:
    """Mock Streamlit module."""

    def __init__(self):
        self.session_state = MockSessionState()
        self._rerun_requested = False

    def rerun(self):
        self._rerun_requested = True

    def should_rerun(self):
        result = self._rerun_requested
        self._rerun_requested = False
        return result


# Patch streamlit before imports
mock_st = MockStreamlit()
sys.modules['streamlit'] = mock_st

# Now import
from config import Strategy, Defaults
from state import StateManager
from strategies.binary import BinaryStrategy
from strategies.elo import EloStrategy
from strategies.swiss import SwissStrategy


def create_mock_df(n: int):
    """Create a mock DataFrame."""
    class MockDF:
        def __init__(self, n):
            self._n = n
            self.columns = ['id', 'name', 'desc']

        def __len__(self):
            return self._n

        def iloc(self, idx):
            class Row:
                def __getitem__(self, key):
                    return f"{key}_{idx}"
            return Row()

    return MockDF(n)


def simulate_app_run(click_button: Optional[str] = None):
    """
    Simulate one run of the Streamlit app.
    Returns what would happen in the UI.
    """
    # This simulates what app.py does on each run

    # --- Initialize State (happens every run) ---
    state = StateManager()

    # Check if we have data
    df = state.df
    if df is None:
        return {"status": "no_data"}

    # Check if rating mode active
    if not state.in_rating_mode:
        if click_button == "start":
            strategy = get_strategy(state)
            strategy.start()
            return {"status": "started", "rerun": True}
        return {"status": "not_started"}

    # Rating mode is active - get strategy and render UI
    strategy = get_strategy(state)

    # Check if done
    if strategy.is_done():
        return {"status": "done", "ordering": strategy.get_ordering()}

    # Get current pair
    pair = strategy.get_current_pair()
    if pair is None:
        return {"status": "no_pair", "rerun": True}

    # Handle button clicks
    if click_button == "left":
        strategy.record_result(left_wins=True)
        return {"status": "recorded", "rerun": True}
    elif click_button == "right":
        strategy.record_result(left_wins=False)
        return {"status": "recorded", "rerun": True}

    return {
        "status": "comparing",
        "pair": pair,
        "progress": strategy.get_progress()
    }


def get_strategy(state):
    """Get strategy instance."""
    strategy_map = {
        Strategy.BINARY: BinaryStrategy,
        Strategy.ELO: EloStrategy,
        Strategy.SWISS: SwissStrategy,
    }
    strategy_class = strategy_map.get(state.rating_strategy, BinaryStrategy)
    return strategy_class(state)


def test_full_binary_flow():
    """Test complete binary strategy flow through simulated app runs."""
    print("\n" + "="*60)
    print("TESTING FULL BINARY FLOW (Simulated Streamlit Runs)")
    print("="*60)

    # Reset state
    mock_st.session_state.clear()

    # Set up initial data (simulates file upload)
    mock_st.session_state["df"] = create_mock_df(5)
    mock_st.session_state["id_col"] = "id"
    mock_st.session_state["name_col"] = "name"
    mock_st.session_state["desc_col"] = "desc"
    mock_st.session_state["rating_strategy"] = Strategy.BINARY
    mock_st.session_state["in_rating_mode"] = False

    # Initialize other state
    mock_st.session_state.setdefault("binary_order_to_insert", [])
    mock_st.session_state.setdefault("binary_sorted_indices", [])
    mock_st.session_state.setdefault("binary_current_i", 0)
    mock_st.session_state.setdefault("binary_low", None)
    mock_st.session_state.setdefault("binary_high", None)
    mock_st.session_state.setdefault("binary_mid", None)
    mock_st.session_state.setdefault("binary_candidate_idx", None)
    mock_st.session_state.setdefault("binary_comparisons_done", 0)

    print("\n1. Initial state (before starting)")
    result = simulate_app_run()
    print(f"   Result: {result}")
    assert result["status"] == "not_started", f"Expected not_started, got {result}"

    print("\n2. Click 'Start' button")
    result = simulate_app_run(click_button="start")
    print(f"   Result: {result}")
    print(f"   Session state after start:")
    print(f"      in_rating_mode: {mock_st.session_state.get('in_rating_mode')}")
    print(f"      binary_sorted_indices: {mock_st.session_state.get('binary_sorted_indices')}")
    print(f"      binary_current_i: {mock_st.session_state.get('binary_current_i')}")
    print(f"      binary_candidate_idx: {mock_st.session_state.get('binary_candidate_idx')}")
    assert result["status"] == "started", f"Expected started, got {result}"

    print("\n3. After rerun (first comparison)")
    result = simulate_app_run()
    print(f"   Result: {result}")

    if result["status"] == "done":
        print("   ERROR: Strategy thinks it's done after start!")
        print(f"   binary_sorted_indices: {mock_st.session_state.get('binary_sorted_indices')}")
        print(f"   n_items check: len={len(mock_st.session_state.get('binary_sorted_indices', []))}")

        # Debug: Check what is_done sees
        state = StateManager()
        strategy = BinaryStrategy(state)
        print(f"   strategy.n_items: {strategy.n_items}")
        print(f"   strategy.is_done(): {strategy.is_done()}")
        return False

    if result["status"] != "comparing":
        print(f"   ERROR: Expected 'comparing', got '{result['status']}'")
        return False

    print(f"   Pair to compare: {result['pair']}")
    print(f"   Progress: {result['progress']}")

    # Simulate multiple comparisons
    comparison_count = 0
    max_comparisons = 20

    while comparison_count < max_comparisons:
        comparison_count += 1
        print(f"\n4.{comparison_count}. Click 'left' button")

        result = simulate_app_run(click_button="left")
        print(f"   Result after click: {result}")

        # Simulate rerun
        result = simulate_app_run()
        print(f"   Result after rerun: {result}")

        if result["status"] == "done":
            print(f"\n   COMPLETED after {comparison_count} comparisons")
            print(f"   Final ordering: {result['ordering']}")
            break

        if result["status"] != "comparing":
            print(f"   ERROR: Unexpected status '{result['status']}'")
            return False

        print(f"   Next pair: {result['pair']}")

    success = result["status"] == "done" and len(result.get("ordering", [])) == 5
    print(f"\n   TEST {'PASSED' if success else 'FAILED'}")
    return success


def test_issue_detection():
    """
    Specifically test for the issue: ranking finalized after first click.
    """
    print("\n" + "="*60)
    print("TESTING SPECIFIC ISSUE: Ranking finalized after first click")
    print("="*60)

    # Reset state completely
    mock_st.session_state.clear()

    # Manually set up state as app.py would
    mock_st.session_state["df"] = create_mock_df(5)
    mock_st.session_state["id_col"] = "id"
    mock_st.session_state["name_col"] = "name"
    mock_st.session_state["desc_col"] = "desc"
    mock_st.session_state["rating_strategy"] = Strategy.BINARY
    mock_st.session_state["in_rating_mode"] = False

    # Initialize binary state (this is what StateManager._init_state does)
    mock_st.session_state["binary_order_to_insert"] = []
    mock_st.session_state["binary_sorted_indices"] = []
    mock_st.session_state["binary_current_i"] = 0
    mock_st.session_state["binary_low"] = None
    mock_st.session_state["binary_high"] = None
    mock_st.session_state["binary_mid"] = None
    mock_st.session_state["binary_candidate_idx"] = None
    mock_st.session_state["binary_comparisons_done"] = 0

    # Step 1: Create strategy and start
    print("\n1. Starting strategy...")
    state = StateManager()
    strategy = BinaryStrategy(state)

    print(f"   Before start: n_items = {strategy.n_items}")
    print(f"   Before start: is_done = {strategy.is_done()}")

    strategy.start()

    print(f"\n   After start:")
    print(f"   - in_rating_mode: {mock_st.session_state['in_rating_mode']}")
    print(f"   - sorted_indices: {mock_st.session_state['binary_sorted_indices']}")
    print(f"   - current_i: {mock_st.session_state['binary_current_i']}")
    print(f"   - candidate_idx: {mock_st.session_state['binary_candidate_idx']}")

    # Step 2: Simulate rerun - create NEW strategy instance (this is what Streamlit does)
    print("\n2. Simulating rerun (new strategy instance)...")
    state2 = StateManager()
    strategy2 = BinaryStrategy(state2)

    print(f"   n_items: {strategy2.n_items}")
    print(f"   is_done: {strategy2.is_done()}")

    pair = strategy2.get_current_pair()
    print(f"   get_current_pair: {pair}")

    if pair is None:
        print("\n   BUG FOUND: get_current_pair() returns None!")
        print(f"   Debugging:")
        print(f"   - binary_candidate_idx: {mock_st.session_state['binary_candidate_idx']}")
        print(f"   - binary_mid: {mock_st.session_state['binary_mid']}")
        print(f"   - binary_sorted_indices: {mock_st.session_state['binary_sorted_indices']}")
        return False

    if strategy2.is_done():
        print("\n   BUG FOUND: is_done() returns True prematurely!")
        print(f"   sorted_indices length: {len(mock_st.session_state['binary_sorted_indices'])}")
        print(f"   n_items: {strategy2.n_items}")
        return False

    # Step 3: Record first result
    print(f"\n3. Recording first comparison result (left wins)...")
    strategy2.record_result(left_wins=True)

    print(f"   After record_result:")
    print(f"   - sorted_indices: {mock_st.session_state['binary_sorted_indices']}")
    print(f"   - current_i: {mock_st.session_state['binary_current_i']}")
    print(f"   - candidate_idx: {mock_st.session_state['binary_candidate_idx']}")

    # Step 4: Another rerun
    print("\n4. Simulating another rerun...")
    state3 = StateManager()
    strategy3 = BinaryStrategy(state3)

    print(f"   n_items: {strategy3.n_items}")
    print(f"   is_done: {strategy3.is_done()}")

    if strategy3.is_done():
        print("\n   BUG FOUND: is_done() returns True after just 1 comparison!")
        print(f"   sorted_indices: {mock_st.session_state['binary_sorted_indices']}")
        print(f"   expected 5 items, have {len(mock_st.session_state['binary_sorted_indices'])}")
        return False

    pair = strategy3.get_current_pair()
    print(f"   get_current_pair: {pair}")

    if pair is None:
        print("\n   BUG FOUND: No pair after first comparison!")
        return False

    print("\n   TEST PASSED: Strategy continues correctly after first comparison")
    return True


if __name__ == "__main__":
    print("\n" + "#"*60)
    print("# STREAMLIT FLOW SIMULATION TESTS")
    print("#"*60)

    results = {}
    results['issue_detection'] = test_issue_detection()
    results['full_flow'] = test_full_binary_flow()

    print("\n" + "#"*60)
    print("# SUMMARY")
    print("#"*60)

    for name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"   {name}: {status}")

    all_passed = all(results.values())
    print("\n" + "#"*60)
    if all_passed:
        print("# ALL TESTS PASSED - Bug is likely in Streamlit UI layer")
    else:
        print("# TESTS FAILED - Bug found in strategy logic")
    print("#"*60)

    sys.exit(0 if all_passed else 1)

"""
Test suite for Prioritizer strategies.
Run with: python test_strategies.py
"""

import sys
from unittest.mock import MagicMock, patch
from typing import Dict, Any


class MockSessionState(dict):
    """Mock Streamlit session_state that behaves like a dict with attribute access."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"'MockSessionState' has no attribute '{key}'")

    def __setattr__(self, key, value):
        self[key] = value

    def get(self, key, default=None):
        return self[key] if key in self else default


class MockStreamlit:
    """Mock Streamlit module."""

    def __init__(self):
        self.session_state = MockSessionState()

    def rerun(self):
        pass


# Create mock and patch before importing strategies
mock_st = MockStreamlit()
sys.modules['streamlit'] = mock_st

# Now import after patching
from config import Strategy, Defaults
from state import StateManager


def reset_session_state():
    """Reset session state to initial values."""
    mock_st.session_state.clear()
    mock_st.session_state.update({
        # Data
        "df": None,
        "id_col": None,
        "name_col": None,
        "desc_col": None,
        "rating_strategy": Strategy.BINARY,
        "in_rating_mode": False,

        # Binary state
        "binary_order_to_insert": [],
        "binary_sorted_indices": [],
        "binary_current_i": 0,
        "binary_low": None,
        "binary_high": None,
        "binary_mid": None,
        "binary_candidate_idx": None,
        "binary_comparisons_done": 0,

        # Elo state
        "elo_pairs": [],
        "elo_pair_idx": 0,
        "elo_ratings": {},
        "elo_comparisons": 0,
        "elo_games_per_idea": Defaults.ELO_GAMES_PER_IDEA,
        "elo_done": False,

        # Swiss state
        "swiss_points": {},
        "swiss_round": 1,
        "swiss_rounds_total": Defaults.SWISS_ROUNDS,
        "swiss_pairs": [],
        "swiss_pair_idx": 0,
        "swiss_done": False,
    })


def create_mock_dataframe(n_items: int):
    """Create a mock DataFrame with n items."""
    class MockDataFrame:
        def __init__(self, n):
            self.n = n
            self.data = {
                'id': list(range(n)),
                'name': [f'Item {i}' for i in range(n)],
                'desc': [f'Description {i}' for i in range(n)],
            }
            self.columns = list(self.data.keys())

        def __len__(self):
            return self.n

        def iloc(self, idx):
            return {k: v[idx] for k, v in self.data.items()}

    return MockDataFrame(n_items)


def test_binary_strategy():
    """Test Binary Insertion Sort strategy."""
    print("\n" + "="*60)
    print("TESTING BINARY STRATEGY")
    print("="*60)

    reset_session_state()

    # Create mock data with 5 items
    n_items = 5
    mock_df = create_mock_dataframe(n_items)
    mock_st.session_state["df"] = mock_df

    # Import strategy (reimport to get fresh module with mocked st)
    from strategies.binary import BinaryStrategy

    # Create state manager and strategy
    state = StateManager()
    strategy = BinaryStrategy(state)

    print(f"\n1. Starting with {n_items} items")
    print(f"   n_items from strategy: {strategy.n_items}")

    # Start the strategy
    strategy.start()

    print(f"\n2. After start():")
    print(f"   in_rating_mode: {mock_st.session_state.in_rating_mode}")
    print(f"   order_to_insert: {mock_st.session_state.binary_order_to_insert}")
    print(f"   sorted_indices: {mock_st.session_state.binary_sorted_indices}")
    print(f"   current_i: {mock_st.session_state.binary_current_i}")
    print(f"   candidate_idx: {mock_st.session_state.binary_candidate_idx}")
    print(f"   low: {mock_st.session_state.binary_low}")
    print(f"   high: {mock_st.session_state.binary_high}")
    print(f"   mid: {mock_st.session_state.binary_mid}")
    print(f"   is_done: {strategy.is_done()}")

    # Get first pair
    pair = strategy.get_current_pair()
    print(f"\n3. First pair to compare: {pair}")

    if pair is None:
        print("   ERROR: No pair returned! Strategy thinks it's done.")
        print(f"   sorted_indices length: {len(mock_st.session_state.binary_sorted_indices)}")
        print(f"   n_items: {strategy.n_items}")
        return False

    # Simulate a few comparisons
    comparison_count = 0
    max_comparisons = 20  # Safety limit

    while not strategy.is_done() and comparison_count < max_comparisons:
        pair = strategy.get_current_pair()
        if pair is None:
            print(f"\n   Comparison {comparison_count + 1}: No pair (preparing next...)")
            break

        comparison_count += 1
        left_idx, right_idx = pair

        print(f"\n   Comparison {comparison_count}: {left_idx} vs {right_idx}")
        print(f"      sorted_indices before: {mock_st.session_state.binary_sorted_indices}")
        print(f"      current_i: {mock_st.session_state.binary_current_i}")
        print(f"      low={mock_st.session_state.binary_low}, high={mock_st.session_state.binary_high}, mid={mock_st.session_state.binary_mid}")

        # Always pick left (arbitrary choice for testing)
        strategy.record_result(left_wins=True)

        print(f"      sorted_indices after: {mock_st.session_state.binary_sorted_indices}")
        print(f"      is_done: {strategy.is_done()}")

    print(f"\n4. Final state:")
    print(f"   Total comparisons: {comparison_count}")
    print(f"   sorted_indices: {mock_st.session_state.binary_sorted_indices}")
    print(f"   is_done: {strategy.is_done()}")

    # Verify
    success = len(mock_st.session_state.binary_sorted_indices) == n_items
    print(f"\n   TEST {'PASSED' if success else 'FAILED'}: Expected {n_items} items in sorted_indices, got {len(mock_st.session_state.binary_sorted_indices)}")

    return success


def test_elo_strategy():
    """Test Elo Tournament strategy."""
    print("\n" + "="*60)
    print("TESTING ELO STRATEGY")
    print("="*60)

    reset_session_state()

    # Create mock data with 5 items
    n_items = 5
    mock_df = create_mock_dataframe(n_items)
    mock_st.session_state["df"] = mock_df
    mock_st.session_state["elo_games_per_idea"] = 3

    from strategies.elo import EloStrategy

    state = StateManager()
    strategy = EloStrategy(state)

    print(f"\n1. Starting with {n_items} items")

    strategy.start()

    print(f"\n2. After start():")
    print(f"   elo_pairs count: {len(mock_st.session_state.elo_pairs)}")
    print(f"   elo_ratings: {mock_st.session_state.elo_ratings}")
    print(f"   elo_done: {mock_st.session_state.elo_done}")
    print(f"   is_done: {strategy.is_done()}")

    pair = strategy.get_current_pair()
    print(f"\n3. First pair: {pair}")

    if pair is None:
        print("   ERROR: No pair returned!")
        return False

    # Do a few comparisons
    for i in range(3):
        pair = strategy.get_current_pair()
        if pair is None:
            break
        print(f"\n   Comparison {i+1}: {pair}")
        strategy.record_result(left_wins=True)
        print(f"      elo_pair_idx: {mock_st.session_state.elo_pair_idx}")

    print(f"\n4. After 3 comparisons:")
    print(f"   elo_pair_idx: {mock_st.session_state.elo_pair_idx}")
    print(f"   is_done: {strategy.is_done()}")

    success = mock_st.session_state.elo_pair_idx == 3
    print(f"\n   TEST {'PASSED' if success else 'FAILED'}")

    return success


def test_swiss_strategy():
    """Test Swiss Tournament strategy."""
    print("\n" + "="*60)
    print("TESTING SWISS STRATEGY")
    print("="*60)

    reset_session_state()

    # Create mock data with 5 items
    n_items = 5
    mock_df = create_mock_dataframe(n_items)
    mock_st.session_state["df"] = mock_df
    mock_st.session_state["swiss_rounds_total"] = 2

    from strategies.swiss import SwissStrategy

    state = StateManager()
    strategy = SwissStrategy(state)

    print(f"\n1. Starting with {n_items} items")

    strategy.start()

    print(f"\n2. After start():")
    print(f"   swiss_pairs: {mock_st.session_state.swiss_pairs}")
    print(f"   swiss_points: {mock_st.session_state.swiss_points}")
    print(f"   swiss_round: {mock_st.session_state.swiss_round}")
    print(f"   is_done: {strategy.is_done()}")

    pair = strategy.get_current_pair()
    print(f"\n3. First pair: {pair}")

    if pair is None:
        print("   ERROR: No pair returned!")
        return False

    # Do comparisons until done
    comparison_count = 0
    max_comparisons = 20

    while not strategy.is_done() and comparison_count < max_comparisons:
        pair = strategy.get_current_pair()
        if pair is None:
            break

        comparison_count += 1
        print(f"\n   Comparison {comparison_count} (Round {mock_st.session_state.swiss_round}): {pair}")
        strategy.record_result(left_wins=True)

    print(f"\n4. Final state:")
    print(f"   Total comparisons: {comparison_count}")
    print(f"   swiss_points: {mock_st.session_state.swiss_points}")
    print(f"   is_done: {strategy.is_done()}")

    success = strategy.is_done()
    print(f"\n   TEST {'PASSED' if success else 'FAILED'}")

    return success


def test_state_manager_n_items():
    """Test that StateManager correctly reports n_items."""
    print("\n" + "="*60)
    print("TESTING STATE MANAGER n_items")
    print("="*60)

    reset_session_state()

    # Test with None df
    state = StateManager()
    print(f"\n1. With df=None:")
    print(f"   get_item_count(): {state.get_item_count()}")

    # Test with mock df
    mock_df = create_mock_dataframe(5)
    mock_st.session_state["df"] = mock_df

    print(f"\n2. With df having 5 items:")
    print(f"   get_item_count(): {state.get_item_count()}")

    success = state.get_item_count() == 5
    print(f"\n   TEST {'PASSED' if success else 'FAILED'}")

    return success


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "#"*60)
    print("# PRIORITIZER STRATEGY TESTS")
    print("#"*60)

    results = {}

    results['state_manager'] = test_state_manager_n_items()
    results['binary'] = test_binary_strategy()
    results['elo'] = test_elo_strategy()
    results['swiss'] = test_swiss_strategy()

    print("\n" + "#"*60)
    print("# SUMMARY")
    print("#"*60)

    all_passed = True
    for name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"   {name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "#"*60)
    if all_passed:
        print("# ALL TESTS PASSED")
    else:
        print("# SOME TESTS FAILED - SEE ABOVE FOR DETAILS")
    print("#"*60)

    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

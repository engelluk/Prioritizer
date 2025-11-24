"""
Test the simplified app.py logic.
"""

import sys


class MockSessionState(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def setdefault(self, key, default):
        if key not in self:
            self[key] = default
        return self[key]

    def get(self, key, default=None):
        return self[key] if key in self else default


class MockSt:
    def __init__(self):
        self.session_state = MockSessionState()

    def rerun(self):
        pass


mock_st = MockSt()
sys.modules['streamlit'] = mock_st

# Now import the functions from app.py by executing the relevant parts
exec("""
import random
from typing import List, Dict, Optional, Tuple

STRATEGY_BINARY = "binary"

def init_state():
    ss = mock_st.session_state
    ss.setdefault("df", None)
    ss.setdefault("in_rating_mode", False)
    ss.setdefault("binary_order", [])
    ss.setdefault("binary_sorted", [])
    ss.setdefault("binary_i", 0)
    ss.setdefault("binary_low", None)
    ss.setdefault("binary_high", None)
    ss.setdefault("binary_mid", None)
    ss.setdefault("binary_candidate", None)
    ss.setdefault("binary_comparisons", 0)
    ss.setdefault("rating_strategy", STRATEGY_BINARY)

init_state()
ss = mock_st.session_state

def get_n_items():
    if ss.df is None:
        return 0
    return len(ss.df)

def binary_start():
    n = get_n_items()
    if n == 0:
        return
    order = list(range(n))
    random.shuffle(order)
    ss.binary_order = order
    ss.binary_sorted = [order[0]]
    ss.binary_i = 1
    ss.binary_candidate = None
    ss.binary_low = None
    ss.binary_high = None
    ss.binary_mid = None
    ss.binary_comparisons = 0
    ss.in_rating_mode = True
    if n > 1:
        binary_setup_next()

def binary_setup_next():
    if ss.binary_i >= len(ss.binary_order):
        ss.binary_candidate = None
        return
    candidate = ss.binary_order[ss.binary_i]
    n_sorted = len(ss.binary_sorted)
    ss.binary_candidate = candidate
    ss.binary_low = 0
    ss.binary_high = n_sorted - 1
    ss.binary_mid = (0 + n_sorted - 1) // 2

def binary_get_pair():
    if ss.binary_candidate is None:
        binary_setup_next()
    if ss.binary_candidate is None or ss.binary_mid is None:
        return None
    return (ss.binary_candidate, ss.binary_sorted[ss.binary_mid])

def binary_record(left_wins):
    ss.binary_comparisons += 1
    if left_wins:
        ss.binary_high = ss.binary_mid - 1
    else:
        ss.binary_low = ss.binary_mid + 1
    if ss.binary_low > ss.binary_high:
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

def binary_is_done():
    return len(ss.binary_sorted) == get_n_items()
""")

# Create mock DataFrame
class MockDF:
    def __init__(self, n):
        self.n = n
    def __len__(self):
        return self.n

print("="*60)
print("Testing simplified app.py logic")
print("="*60)

# Test with 5 items
mock_st.session_state.df = MockDF(5)

print(f"\\n1. n_items = {get_n_items()}")
print(f"   is_done (before start) = {binary_is_done()}")

print("\\n2. Starting binary sort...")
binary_start()
print(f"   in_rating_mode = {mock_st.session_state.in_rating_mode}")
print(f"   binary_sorted = {mock_st.session_state.binary_sorted}")
print(f"   binary_candidate = {mock_st.session_state.binary_candidate}")

print("\\n3. Getting first pair...")
pair = binary_get_pair()
print(f"   pair = {pair}")
print(f"   is_done = {binary_is_done()}")

if pair is None:
    print("   ERROR: No pair!")
    sys.exit(1)

# Simulate comparisons
comparison_count = 0
max_comparisons = 20

print("\\n4. Running comparisons...")
while not binary_is_done() and comparison_count < max_comparisons:
    pair = binary_get_pair()
    if pair is None:
        break
    comparison_count += 1
    print(f"   Comparison {comparison_count}: {pair}, sorted={mock_st.session_state.binary_sorted}")
    binary_record(left_wins=True)

print(f"\\n5. Final state:")
print(f"   comparisons = {comparison_count}")
print(f"   binary_sorted = {mock_st.session_state.binary_sorted}")
print(f"   is_done = {binary_is_done()}")

if binary_is_done() and len(mock_st.session_state.binary_sorted) == 5:
    print("\\n" + "="*60)
    print("TEST PASSED!")
    print("="*60)
else:
    print("\\n" + "="*60)
    print("TEST FAILED!")
    print("="*60)
    sys.exit(1)

"""
Automated tests for Prioritizer app using Streamlit's AppTest.
Run with: python tests/test_auto.py (from project root)
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check_streamlit_testing():
    """Check if streamlit testing is available."""
    try:
        from streamlit.testing.v1 import AppTest
        return True
    except ImportError:
        return False


def test_with_app_test():
    """Test using Streamlit's AppTest framework."""
    print("="*60)
    print("Testing with Streamlit AppTest")
    print("="*60)

    try:
        from streamlit.testing.v1 import AppTest
    except ImportError:
        print("Streamlit testing not available. Install with:")
        print("  pip install streamlit>=1.28.0")
        return False

    # Test the minimal app
    print("\n1. Loading app_minimal.py...")
    try:
        at = AppTest.from_file(os.path.join(PARENT_DIR, "app_minimal.py"), default_timeout=10)
        at.run()
    except Exception as e:
        print(f"   ERROR loading app: {e}")
        import traceback
        traceback.print_exc()
        return False

    print(f"   App loaded successfully")

    # Check initial state
    print("\n2. Checking initial state...")
    print(f"   started: {at.session_state.started}")
    print(f"   sorted_list: {at.session_state.sorted_list}")

    # Find and click START button
    print("\n3. Clicking START button...")
    start_buttons = [b for b in at.button if "START" in str(b.label).upper()]
    if not start_buttons:
        print("   ERROR: No START button found")
        print(f"   Available buttons: {[b.label for b in at.button]}")
        return False

    start_buttons[0].click()
    at.run()

    print(f"   After START:")
    print(f"   started: {at.session_state.started}")
    print(f"   sorted_list: {at.session_state.sorted_list}")
    print(f"   candidate_val: {at.session_state.candidate_val}")
    print(f"   current_idx: {at.session_state.current_idx}")

    if not at.session_state.started:
        print("   ERROR: App did not start!")
        return False

    # Check if already done (shouldn't be)
    sorted_list = at.session_state.sorted_list
    if len(sorted_list) == 5:
        print("   ERROR: Already done after just starting!")
        return False

    # Simulate comparisons
    print("\n4. Running comparisons...")
    max_iterations = 20
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        sorted_list = at.session_state.sorted_list
        if len(sorted_list) == 5:
            print(f"   DONE after {iteration-1} button clicks!")
            print(f"   Final sorted_list: {sorted_list}")
            break

        # Find LEFT button
        left_buttons = [b for b in at.button if "LEFT" in str(b.label).upper()]
        if not left_buttons:
            print(f"   Iteration {iteration}: No LEFT button found")
            print(f"   Available buttons: {[b.label for b in at.button]}")
            # Maybe we need to rerun?
            at.run()
            left_buttons = [b for b in at.button if "LEFT" in str(b.label).upper()]
            if not left_buttons:
                print(f"   Still no LEFT button after rerun")
                break

        print(f"   Iteration {iteration}: sorted_list={sorted_list}, clicking LEFT...")
        left_buttons[0].click()
        at.run()

    # Verify result
    final_sorted = at.session_state.sorted_list
    success = len(final_sorted) == 5

    print(f"\n5. Final result:")
    print(f"   sorted_list: {final_sorted}")
    print(f"   length: {len(final_sorted)}")
    print(f"   TEST {'PASSED' if success else 'FAILED'}")

    return success


def test_simulation():
    """Test by simulating Streamlit's execution model exactly."""
    print("="*60)
    print("Testing with Execution Simulation")
    print("="*60)

    import random

    # Simulate session_state as a persistent dict
    session_state = {
        "initialized": True,
        "started": False,
        "data_list": ["A", "B", "C", "D", "E"],
        "order_list": [],
        "sorted_list": [],
        "current_idx": 0,
        "candidate_val": None,
        "low_val": None,
        "high_val": None,
        "mid_val": None,
        "comparison_count": 0,
    }

    n_items = 5

    def simulate_page_run(button_clicked=None):
        """Simulate one complete page run."""
        nonlocal session_state

        ss = session_state

        if not ss["started"]:
            if button_clicked == "START":
                order = list(range(n_items))
                random.shuffle(order)
                ss["order_list"] = order
                ss["sorted_list"] = [order[0]]
                ss["current_idx"] = 1
                ss["started"] = True
                ss["comparison_count"] = 0

                if n_items > 1:
                    ss["candidate_val"] = order[1]
                    ss["low_val"] = 0
                    ss["high_val"] = 0
                    ss["mid_val"] = 0

                return {"action": "rerun", "state": "started"}
            return {"action": "wait", "state": "not_started"}

        # Check if done
        if len(ss["sorted_list"]) == n_items:
            return {"action": "done", "sorted_list": ss["sorted_list"]}

        # Get current pair
        candidate = ss["candidate_val"]
        mid = ss["mid_val"]

        if candidate is None or mid is None:
            if ss["current_idx"] < len(ss["order_list"]):
                ss["candidate_val"] = ss["order_list"][ss["current_idx"]]
                n_sorted = len(ss["sorted_list"])
                ss["low_val"] = 0
                ss["high_val"] = n_sorted - 1
                ss["mid_val"] = (n_sorted - 1) // 2
                return {"action": "rerun", "state": "setup_candidate"}
            return {"action": "error", "state": "no_candidate"}

        # Handle button click
        if button_clicked in ["LEFT", "RIGHT"]:
            left_wins = (button_clicked == "LEFT")
            ss["comparison_count"] += 1

            if left_wins:
                ss["high_val"] = ss["mid_val"] - 1
            else:
                ss["low_val"] = ss["mid_val"] + 1

            if ss["low_val"] > ss["high_val"]:
                # Insert
                new_sorted = list(ss["sorted_list"])
                new_sorted.insert(ss["low_val"], ss["candidate_val"])
                ss["sorted_list"] = new_sorted
                ss["current_idx"] += 1

                # Setup next
                if ss["current_idx"] < len(ss["order_list"]):
                    ss["candidate_val"] = ss["order_list"][ss["current_idx"]]
                    n_sorted = len(ss["sorted_list"])
                    ss["low_val"] = 0
                    ss["high_val"] = n_sorted - 1
                    ss["mid_val"] = (n_sorted - 1) // 2
                else:
                    ss["candidate_val"] = None
                    ss["low_val"] = None
                    ss["high_val"] = None
                    ss["mid_val"] = None

                return {"action": "rerun", "state": "inserted"}
            else:
                ss["mid_val"] = (ss["low_val"] + ss["high_val"]) // 2
                return {"action": "rerun", "state": "continue_search"}

        return {
            "action": "wait_input",
            "pair": (candidate, ss["sorted_list"][mid]),
            "sorted_list": ss["sorted_list"],
        }

    # Run simulation
    print("\n1. Initial state")
    result = simulate_page_run()
    print(f"   Result: {result}")

    print("\n2. Click START")
    result = simulate_page_run("START")
    print(f"   Result: {result}")
    print(f"   sorted_list: {session_state['sorted_list']}")

    if result["action"] != "rerun":
        print("   ERROR: Expected rerun after START")
        return False

    print("\n3. After rerun (should show first comparison)")
    result = simulate_page_run()
    print(f"   Result: {result}")

    if result["action"] == "done":
        print("   ERROR: Done immediately after start!")
        return False

    print("\n4. Running comparisons...")
    comparison_count = 0
    max_comparisons = 20

    while comparison_count < max_comparisons:
        result = simulate_page_run()

        if result["action"] == "done":
            print(f"   DONE! Final sorted_list: {result['sorted_list']}")
            break

        if result["action"] == "wait_input":
            comparison_count += 1
            print(f"   Comparison {comparison_count}: pair={result['pair']}, sorted_list={result['sorted_list']}")
            result = simulate_page_run("LEFT")
            continue

        if result["action"] == "rerun":
            continue

        print(f"   Unexpected result: {result}")
        break

    final_sorted = session_state["sorted_list"]
    success = len(final_sorted) == 5

    print(f"\n5. Final state:")
    print(f"   sorted_list: {final_sorted}")
    print(f"   comparison_count: {session_state['comparison_count']}")
    print(f"   TEST {'PASSED' if success else 'FAILED'}")

    return success


def main():
    print("#"*60)
    print("# AUTOMATED PRIORITIZER TESTS")
    print("#"*60)

    results = {}

    # Test 1: Simulation
    results["simulation"] = test_simulation()

    # Test 2: AppTest (if available)
    if check_streamlit_testing():
        results["apptest"] = test_with_app_test()
    else:
        print("\n" + "="*60)
        print("Skipping AppTest (streamlit.testing not available)")
        print("="*60)
        results["apptest"] = None

    # Summary
    print("\n" + "#"*60)
    print("# SUMMARY")
    print("#"*60)

    all_passed = True
    for name, result in results.items():
        if result is None:
            status = "SKIPPED"
        elif result:
            status = "PASSED"
        else:
            status = "FAILED"
            all_passed = False
        print(f"   {name}: {status}")

    print("\n" + "#"*60)
    if all_passed:
        print("# ALL TESTS PASSED")
    else:
        print("# SOME TESTS FAILED")
    print("#"*60)

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

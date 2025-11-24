"""
Test the main app.py using Streamlit's AppTest.
Run with: python tests/test_main_app.py (from project root)
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_main_app():
    """Test main app.py with AppTest."""
    print("="*60)
    print("Testing main app.py")
    print("="*60)

    try:
        from streamlit.testing.v1 import AppTest
    except ImportError:
        print("Streamlit testing not available")
        return False

    # Create a test CSV file
    import tempfile
    import pandas as pd

    test_data = pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'name': ['Idea A', 'Idea B', 'Idea C', 'Idea D', 'Idea E'],
        'description': ['Desc A', 'Desc B', 'Desc C', 'Desc D', 'Desc E']
    })

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        test_data.to_csv(f, index=False)
        test_file = f.name

    print(f"\n1. Created test file: {test_file}")

    try:
        # Load app
        print("\n2. Loading app.py...")
        at = AppTest.from_file(os.path.join(PARENT_DIR, "app.py"), default_timeout=10)
        at.run()
        print("   App loaded")

        # Check initial state
        print("\n3. Checking initial state...")
        print(f"   df is None: {at.session_state.df is None}")
        print(f"   in_rating_mode: {at.session_state.in_rating_mode}")

        # We can't easily simulate file upload with AppTest
        # So let's directly set the session state
        print("\n4. Simulating file upload by setting session state...")

        # Set the dataframe directly
        at.session_state.df = test_data
        at.session_state.id_col = 'id'
        at.session_state.name_col = 'name'
        at.session_state.desc_col = 'description'
        at.run()

        print(f"   df set: {at.session_state.df is not None}")
        print(f"   rows: {len(at.session_state.df) if at.session_state.df is not None else 0}")

        # Find start button
        print("\n5. Looking for Start button...")
        all_buttons = list(at.button)
        print(f"   Found {len(all_buttons)} buttons")
        for b in all_buttons:
            print(f"      - {b.label}")

        start_buttons = [b for b in at.button if "start" in str(b.label).lower()]
        if not start_buttons:
            print("   No start button found - might need to rerun after setting df")
            at.run()
            start_buttons = [b for b in at.button if "start" in str(b.label).lower()]

        if not start_buttons:
            print("   ERROR: Still no start button")
            return False

        print(f"\n6. Clicking start button...")
        start_buttons[0].click()
        at.run()

        print(f"   in_rating_mode: {at.session_state.in_rating_mode}")
        print(f"   binary_sorted: {at.session_state.binary_sorted}")

        if not at.session_state.in_rating_mode:
            print("   ERROR: Rating mode not started!")
            return False

        # Run comparisons
        print("\n7. Running comparisons...")
        max_iterations = 20

        for i in range(max_iterations):
            sorted_list = at.session_state.binary_sorted
            if len(sorted_list) == 5:
                print(f"   DONE after {i} iterations!")
                print(f"   Final sorted: {sorted_list}")
                break

            # Find comparison buttons
            left_buttons = [b for b in at.button if "impact" in str(b.label).lower()]
            if len(left_buttons) >= 1:
                print(f"   Iteration {i+1}: sorted={sorted_list}, clicking...")
                left_buttons[0].click()
                at.run()
            else:
                print(f"   Iteration {i+1}: No comparison button found")
                print(f"   Available: {[b.label for b in at.button]}")
                at.run()

        final_sorted = at.session_state.binary_sorted
        success = len(final_sorted) == 5

        print(f"\n8. Final result:")
        print(f"   binary_sorted: {final_sorted}")
        print(f"   TEST {'PASSED' if success else 'FAILED'}")

        return success

    finally:
        # Cleanup
        os.unlink(test_file)


if __name__ == "__main__":
    success = test_main_app()
    sys.exit(0 if success else 1)

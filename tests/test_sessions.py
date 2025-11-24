"""
Test suite for session management functionality.
Run with: python tests/test_sessions.py (from project root)
"""

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock streamlit before importing app
class MockSessionState(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"No attribute '{key}'")

    def __setattr__(self, key, value):
        self[key] = value

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]


class MockStreamlit:
    def __init__(self):
        self.session_state = MockSessionState()
        self._config = {}

    def set_page_config(self, **kwargs):
        self._config = kwargs

    def title(self, *args, **kwargs): pass
    def caption(self, *args, **kwargs): pass
    def header(self, *args, **kwargs): pass
    def subheader(self, *args, **kwargs): pass
    def write(self, *args, **kwargs): pass
    def markdown(self, *args, **kwargs): pass
    def info(self, *args, **kwargs): pass
    def success(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
    def divider(self, *args, **kwargs): pass
    def stop(self, *args, **kwargs): pass
    def rerun(self, *args, **kwargs): pass
    def balloons(self, *args, **kwargs): pass
    def columns(self, *args, **kwargs): return [MockColumn() for _ in range(args[0] if args else 3)]
    def button(self, *args, **kwargs): return False
    def text_input(self, *args, **kwargs): return ""
    def selectbox(self, *args, **kwargs): return args[1][0] if len(args) > 1 and args[1] else None
    def radio(self, *args, **kwargs): return args[1][0] if len(args) > 1 and args[1] else None
    def slider(self, *args, **kwargs): return args[2] if len(args) > 2 else 0
    def file_uploader(self, *args, **kwargs): return None
    def download_button(self, *args, **kwargs): return False
    def dataframe(self, *args, **kwargs): pass
    def metric(self, *args, **kwargs): pass
    def progress(self, *args, **kwargs): pass
    def expander(self, *args, **kwargs): return MockExpander()
    def container(self, *args, **kwargs): return MockContainer()
    def sidebar(self): return MockSidebar()
    def code(self, *args, **kwargs): pass


class MockColumn:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def markdown(self, *args, **kwargs): pass
    def write(self, *args, **kwargs): pass
    def metric(self, *args, **kwargs): pass
    def button(self, *args, **kwargs): return False


class MockExpander:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def dataframe(self, *args, **kwargs): pass
    def code(self, *args, **kwargs): pass


class MockContainer:
    def __enter__(self): return self
    def __exit__(self, *args): pass


class MockSidebar:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def header(self, *args, **kwargs): pass
    def button(self, *args, **kwargs): return False
    def divider(self, *args, **kwargs): pass
    def file_uploader(self, *args, **kwargs): return None
    def selectbox(self, *args, **kwargs): return None
    def radio(self, *args, **kwargs): return None
    def slider(self, *args, **kwargs): return 0
    def success(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass


# Install mock
mock_st = MockStreamlit()
sys.modules['streamlit'] = mock_st

# Now we can import the functions we need to test
import pandas as pd
import io


def setup_test_sessions_dir():
    """Create a temporary sessions directory for testing."""
    test_dir = Path(tempfile.mkdtemp())
    return test_dir


def cleanup_test_dir(test_dir: Path):
    """Remove test directory."""
    shutil.rmtree(test_dir, ignore_errors=True)


def test_create_session():
    """Test session creation."""
    print("\n" + "="*60)
    print("TEST: create_session")
    print("="*60)

    # Setup temp directory
    test_dir = setup_test_sessions_dir()

    try:
        # Import after mock and temporarily override SESSIONS_DIR
        import app
        original_dir = app.SESSIONS_DIR
        app.SESSIONS_DIR = test_dir

        # Create test data
        test_df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Idea A', 'Idea B', 'Idea C'],
            'description': ['Desc A', 'Desc B', 'Desc C']
        })

        # Create session
        session_id = app.create_session(
            name="Test Session",
            strategy="binary",
            df=test_df,
            id_col="id",
            name_col="name",
            desc_col="description",
            settings={"test_setting": True}
        )

        print(f"Created session: {session_id}")

        # Verify file was created
        session_file = test_dir / f"{session_id}.json"
        assert session_file.exists(), "Session file not created"
        print(f"Session file exists: {session_file}")

        # Load and verify contents
        with open(session_file, 'r') as f:
            data = json.load(f)

        assert data["name"] == "Test Session"
        assert data["strategy"] == "binary"
        assert len(data["data"]) == 3
        assert data["columns"]["id"] == "id"
        assert data["settings"]["test_setting"] == True
        print("Session data verified")

        # Restore
        app.SESSIONS_DIR = original_dir

        print("\nTEST PASSED")
        return True

    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        cleanup_test_dir(test_dir)


def test_load_session():
    """Test session loading."""
    print("\n" + "="*60)
    print("TEST: load_session")
    print("="*60)

    test_dir = setup_test_sessions_dir()

    try:
        import app
        original_dir = app.SESSIONS_DIR
        app.SESSIONS_DIR = test_dir

        # Create a session file manually
        session_id = "test1234"
        session_data = {
            "id": session_id,
            "name": "Load Test",
            "strategy": "elo",
            "settings": {},
            "columns": {"id": "id", "name": "name", "desc": "desc"},
            "data": [{"id": 1, "name": "A", "desc": "B"}],
            "users": {}
        }

        with open(test_dir / f"{session_id}.json", 'w') as f:
            json.dump(session_data, f)

        # Load it
        loaded = app.load_session(session_id)

        assert loaded is not None, "Session not loaded"
        assert loaded["name"] == "Load Test"
        assert loaded["strategy"] == "elo"
        print("Session loaded successfully")

        # Test loading non-existent session
        missing = app.load_session("nonexistent")
        assert missing is None, "Should return None for missing session"
        print("Non-existent session returns None")

        app.SESSIONS_DIR = original_dir

        print("\nTEST PASSED")
        return True

    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        cleanup_test_dir(test_dir)


def test_list_sessions():
    """Test listing sessions."""
    print("\n" + "="*60)
    print("TEST: list_sessions")
    print("="*60)

    test_dir = setup_test_sessions_dir()

    try:
        import app
        original_dir = app.SESSIONS_DIR
        app.SESSIONS_DIR = test_dir

        # Create multiple session files
        for i in range(3):
            session_data = {
                "id": f"sess{i}",
                "name": f"Session {i}",
                "strategy": "binary",
                "settings": {},
                "columns": {"id": "id", "name": "name", "desc": "desc"},
                "data": [{"id": j} for j in range(i + 1)],
                "users": {f"user{j}": {"completed": j % 2 == 0} for j in range(i)}
            }
            with open(test_dir / f"sess{i}.json", 'w') as f:
                json.dump(session_data, f)

        # List sessions
        sessions = app.list_sessions()

        assert len(sessions) == 3, f"Expected 3 sessions, got {len(sessions)}"
        print(f"Found {len(sessions)} sessions")

        for sess in sessions:
            print(f"  - {sess['name']}: {sess['items_count']} items, {sess['users_completed']}/{sess['users_total']} users")

        app.SESSIONS_DIR = original_dir

        print("\nTEST PASSED")
        return True

    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        cleanup_test_dir(test_dir)


def test_delete_session():
    """Test session deletion."""
    print("\n" + "="*60)
    print("TEST: delete_session")
    print("="*60)

    test_dir = setup_test_sessions_dir()

    try:
        import app
        original_dir = app.SESSIONS_DIR
        app.SESSIONS_DIR = test_dir

        # Create a session file
        session_id = "todelete"
        with open(test_dir / f"{session_id}.json", 'w') as f:
            json.dump({"id": session_id}, f)

        assert (test_dir / f"{session_id}.json").exists()
        print("Session file created")

        # Delete it
        result = app.delete_session(session_id)
        assert result == True, "Delete should return True"
        assert not (test_dir / f"{session_id}.json").exists(), "File should be deleted"
        print("Session deleted successfully")

        # Try to delete non-existent
        result = app.delete_session("nonexistent")
        assert result == False, "Should return False for missing session"
        print("Non-existent delete returns False")

        app.SESSIONS_DIR = original_dir

        print("\nTEST PASSED")
        return True

    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        cleanup_test_dir(test_dir)


def test_save_user_result():
    """Test saving user ranking results."""
    print("\n" + "="*60)
    print("TEST: save_user_result")
    print("="*60)

    test_dir = setup_test_sessions_dir()

    try:
        import app
        original_dir = app.SESSIONS_DIR
        app.SESSIONS_DIR = test_dir

        # Create a session
        session_id = "usertest"
        session_data = {
            "id": session_id,
            "name": "User Result Test",
            "strategy": "binary",
            "settings": {},
            "columns": {"id": "id", "name": "name", "desc": "desc"},
            "data": [{"id": i} for i in range(5)],
            "users": {}
        }
        with open(test_dir / f"{session_id}.json", 'w') as f:
            json.dump(session_data, f)

        # Save user result
        ordering = [2, 0, 4, 1, 3]
        extra = {"comparisons": 10}

        result = app.save_user_result(session_id, "alice", ordering, extra)
        assert result == True, "Save should return True"
        print("User result saved")

        # Verify
        loaded = app.load_session(session_id)
        assert "alice" in loaded["users"]
        assert loaded["users"]["alice"]["ordering"] == ordering
        assert loaded["users"]["alice"]["completed"] == True
        assert loaded["users"]["alice"]["comparisons"] == 10
        print("User result verified")

        # Add another user
        app.save_user_result(session_id, "bob", [1, 2, 3, 4, 0])
        loaded = app.load_session(session_id)
        assert len(loaded["users"]) == 2
        print("Second user added")

        app.SESSIONS_DIR = original_dir

        print("\nTEST PASSED")
        return True

    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        cleanup_test_dir(test_dir)


def test_compute_average_ranking():
    """Test computing average rankings from multiple users."""
    print("\n" + "="*60)
    print("TEST: compute_average_ranking")
    print("="*60)

    try:
        import app

        # Create a session with multiple user results
        session = {
            "id": "avgtest",
            "name": "Average Test",
            "strategy": "binary",
            "columns": {"id": "id", "name": "name", "desc": "description"},
            "data": [
                {"id": 1, "name": "A", "description": "Item A"},
                {"id": 2, "name": "B", "description": "Item B"},
                {"id": 3, "name": "C", "description": "Item C"},
            ],
            "users": {
                "alice": {"completed": True, "ordering": [0, 1, 2]},  # A=1, B=2, C=3
                "bob": {"completed": True, "ordering": [2, 0, 1]},    # C=1, A=2, B=3
                "carol": {"completed": True, "ordering": [1, 2, 0]},  # B=1, C=2, A=3
            }
        }

        # Compute average ranking
        df = app.compute_average_ranking(session)

        print(f"Result DataFrame:\n{df.to_string()}")

        # Verify columns exist
        assert "avg_rank" in df.columns, "avg_rank column missing"
        assert "rank_std" in df.columns, "rank_std column missing"
        assert "final_ranking" in df.columns, "final_ranking column missing"
        print("Required columns present")

        # Check individual user ranks are included
        assert "rank_alice" in df.columns
        assert "rank_bob" in df.columns
        assert "rank_carol" in df.columns
        print("User rank columns present")

        # Verify average calculation
        # Item A: ranks 1, 2, 3 -> avg 2.0
        # Item B: ranks 2, 3, 1 -> avg 2.0
        # Item C: ranks 3, 1, 2 -> avg 2.0
        # All items have same average rank
        print(f"\nAverage ranks: {df['avg_rank'].tolist()}")

        print("\nTEST PASSED")
        return True

    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_download_session_results():
    """Test generating Excel download with results."""
    print("\n" + "="*60)
    print("TEST: download_session_results")
    print("="*60)

    try:
        import app

        session = {
            "id": "downloadtest",
            "name": "Download Test",
            "strategy": "binary",
            "columns": {"id": "id", "name": "name", "desc": "description"},
            "data": [
                {"id": 1, "name": "A", "description": "Item A"},
                {"id": 2, "name": "B", "description": "Item B"},
            ],
            "users": {
                "alice": {"completed": True, "ordering": [0, 1]},
                "bob": {"completed": True, "ordering": [1, 0]},
            }
        }

        # Generate Excel
        excel_bytes = app.download_session_results(session)

        assert isinstance(excel_bytes, bytes), "Should return bytes"
        assert len(excel_bytes) > 0, "Should not be empty"
        print(f"Generated Excel: {len(excel_bytes)} bytes")

        # Verify it's valid Excel by reading it back
        excel_df = pd.read_excel(io.BytesIO(excel_bytes), sheet_name=None)

        assert "Combined Rankings" in excel_df, "Missing Combined Rankings sheet"
        print(f"Sheets: {list(excel_df.keys())}")

        # Check for user sheets
        user_sheets = [k for k in excel_df.keys() if k.startswith("User_")]
        assert len(user_sheets) == 2, f"Expected 2 user sheets, got {len(user_sheets)}"
        print(f"User sheets: {user_sheets}")

        print("\nTEST PASSED")
        return True

    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_session_workflow():
    """Test complete workflow: create -> join -> rank -> results."""
    print("\n" + "="*60)
    print("TEST: full_session_workflow")
    print("="*60)

    test_dir = setup_test_sessions_dir()

    try:
        import app
        original_dir = app.SESSIONS_DIR
        app.SESSIONS_DIR = test_dir

        # 1. Admin creates session
        print("\n1. Admin creates session")
        test_df = pd.DataFrame({
            'id': [1, 2, 3, 4],
            'name': ['Feature A', 'Feature B', 'Feature C', 'Feature D'],
            'desc': ['Desc A', 'Desc B', 'Desc C', 'Desc D']
        })

        session_id = app.create_session(
            name="Q1 Prioritization",
            strategy="binary",
            df=test_df,
            id_col="id",
            name_col="name",
            desc_col="desc",
            settings={}
        )
        print(f"   Session created: {session_id}")

        # 2. Verify session appears in list
        print("\n2. Verify session in list")
        sessions = app.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["name"] == "Q1 Prioritization"
        print(f"   Found: {sessions[0]['name']}")

        # 3. User 1 completes ranking
        print("\n3. User 1 completes ranking")
        user1_ordering = [0, 2, 1, 3]  # A > C > B > D
        app.save_user_result(session_id, "alice", user1_ordering)
        print("   Alice submitted ranking")

        # 4. User 2 completes ranking
        print("\n4. User 2 completes ranking")
        user2_ordering = [2, 0, 3, 1]  # C > A > D > B
        app.save_user_result(session_id, "bob", user2_ordering)
        print("   Bob submitted ranking")

        # 5. Check completion status
        print("\n5. Check completion status")
        session = app.load_session(session_id)
        completed = sum(1 for u in session["users"].values() if u.get("completed"))
        assert completed == 2
        print(f"   Users completed: {completed}")

        # 6. Generate combined results
        print("\n6. Generate combined results")
        results_df = app.compute_average_ranking(session)
        print(f"   Results:\n{results_df[['name', 'rank_alice', 'rank_bob', 'avg_rank']].to_string()}")

        # 7. Download Excel
        print("\n7. Download Excel")
        excel = app.download_session_results(session)
        assert len(excel) > 0
        print(f"   Excel size: {len(excel)} bytes")

        app.SESSIONS_DIR = original_dir

        print("\nTEST PASSED")
        return True

    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        cleanup_test_dir(test_dir)


def run_all_tests():
    """Run all session tests."""
    print("\n" + "#"*60)
    print("# SESSION MANAGEMENT TESTS")
    print("#"*60)

    results = {}

    results['create_session'] = test_create_session()
    results['load_session'] = test_load_session()
    results['list_sessions'] = test_list_sessions()
    results['delete_session'] = test_delete_session()
    results['save_user_result'] = test_save_user_result()
    results['compute_average_ranking'] = test_compute_average_ranking()
    results['download_session_results'] = test_download_session_results()
    results['full_session_workflow'] = test_full_session_workflow()

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
        print("# SOME TESTS FAILED")
    print("#"*60)

    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

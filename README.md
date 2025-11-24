# Prioritizer - Interactive Impact Ranking Tool

An intelligent Streamlit application for ranking ideas and items through pairwise comparisons. Supports both solo ranking and multi-user collaborative sessions with three distinct ranking strategies.

## Table of Contents

- [Features](#features)
- [Ranking Strategies](#ranking-strategies)
- [Installation](#installation)
- [Usage](#usage)
- [Multi-User Sessions](#multi-user-sessions)
- [Solo Mode](#solo-mode)
- [File Format](#file-format)
- [Technical Details](#technical-details)
- [Testing](#testing)
- [Project Structure](#project-structure)

## Features

### Core Capabilities

- **Three Ranking Strategies**: Binary Insertion Sort, Elo Tournament, and Swiss Rounds
- **Multi-User Sessions**: Create collaborative ranking sessions for team decision-making
- **Solo Mode**: Quick individual ranking without session management
- **Average Rankings**: Automatically compute consensus rankings from multiple users
- **Excel Export**: Download individual and combined rankings in Excel format
- **Session Management**: Create, join, view, and delete ranking sessions
- **Progress Tracking**: Visual progress bars and metrics during ranking
- **Data Preview**: Review uploaded data before starting the ranking process

### User Modes

1. **Create Session**: Set up a new ranking session for multiple participants
2. **Join Session**: Participate in an existing session with your rankings
3. **Solo Mode**: Rank items independently without creating a session

## Ranking Strategies

### 1. Interactive Sort (Binary Insertion Sort)
**Best for: Minimal comparisons and fastest completion**

- Uses binary search to insert each item into a sorted list
- **Fewest comparisons** of all strategies (O(n log n))
- Progressive placement - items are ranked one at a time
- Clear progress tracking showing items placed vs. remaining
- Ideal for small to medium datasets (5-50 items)

**How it works:**
- Takes one item (candidate) and finds its position in the already-sorted list
- Uses binary search to minimize comparisons
- Each comparison narrows down the insertion position by half
- Continues until all items are placed in order

**Example:** With 10 items, expect approximately 25-30 comparisons

### 2. Elo Tournament (Rating-Based)
**Best for: Statistical ranking with flexible completion**

- Assigns Elo ratings to each item (starts at 1500)
- Ratings increase when items win, decrease when they lose
- Can stop early for quick results or continue for more accuracy
- Shows current Elo rating during comparisons
- Suitable for larger datasets or when you want statistical confidence

**How it works:**
- Generates random pairings between items
- Updates Elo ratings after each comparison using the standard formula
- Higher-rated items are expected to beat lower-rated items
- Upsets (lower-rated beating higher-rated) cause larger rating changes
- Final ranking is based on Elo ratings

**Configuration:**
- **Games per idea**: Number of comparisons each item participates in (default: 5)
- More games = more accurate rankings but more time

**Example:** With 10 items and 5 games per idea, expect approximately 25 comparisons

### 3. Swiss Rounds (Batch-Style Tournament)
**Best for: Structured tournament format with clear rounds**

- Organizes ranking into discrete rounds
- Pairs items with similar performance in each round
- Awards points for wins (1 point per win)
- Clear round-by-round structure
- Good for competitive ranking scenarios

**How it works:**
- **Round 1**: Random pairings
- **Subsequent rounds**: Items paired by similar point totals
- Items with odd numbers get a "bye" (automatic point)
- After all rounds, items are ranked by total points
- Tiebreakers use item index

**Configuration:**
- **Number of rounds**: How many rounds to conduct (default: 3)
- More rounds = better separation between items

**Example:** With 10 items and 3 rounds, expect approximately 15 comparisons (5 per round)

## Installation

### Requirements

- Python 3.7 or higher
- pip (Python package manager)

### Setup

1. **Clone or download the repository**
   ```bash
   cd prroritizer
   ```

2. **Install dependencies**
   ```bash
   pip install streamlit pandas xlsxwriter
   ```

   Or use a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install streamlit pandas xlsxwriter
   ```

### Verify Installation

Run the application to verify everything is working:
```bash
streamlit run app.py
```

Your browser should open automatically to `http://localhost:8501`

## Usage

### Quick Start

1. **Run the application**
   ```bash
   streamlit run app.py
   ```

2. **Choose your mode:**
   - **Create Session**: For team ranking sessions
   - **Join Session**: To participate in an existing session
   - **Solo Mode**: For individual ranking

3. **Upload your data** (Excel or CSV file)

4. **Map your columns** (ID, Name, Description)

5. **Select ranking strategy** and configure parameters

6. **Start comparing** items pairwise

7. **Download results** when complete

## Multi-User Sessions

### Creating a Session

1. Click **"Create Session"** on the home screen
2. Enter a session name (e.g., "Q1 Feature Prioritization")
3. Upload your Excel/CSV file with ideas
4. Map the columns (ID, Name, Description)
5. Choose a ranking strategy and configure settings
6. Click **"Create Session"**
7. Share the session name with participants

### Joining a Session

1. Click **"Join Session"** on the home screen
2. Select the session from the dropdown
3. Enter your name
4. Click **"Start Ranking"**
5. Complete pairwise comparisons
6. Your ranking is automatically saved when complete

### Viewing Session Results

1. From the home screen, click **"View"** next to any session
2. See participant status (who has completed)
3. View combined rankings with averages across all users
4. Download Excel file with:
   - **Combined Rankings** sheet (average rankings + individual ranks)
   - **Individual User** sheets (one per participant)

### How Averaging Works

For each item:
1. Each user's ranking is converted to a rank number (1st, 2nd, 3rd, etc.)
2. Average rank is calculated across all users
3. Items are sorted by average rank
4. Standard deviation shows agreement level (lower = more consensus)

**Example:**
- User A ranks Item X as #1
- User B ranks Item X as #3
- User C ranks Item X as #2
- **Average rank: 2.0** (consensus: 2nd place)

## Solo Mode

### Using Solo Mode

1. Click **"Solo Mode"** on the home screen
2. Upload your Excel/CSV file in the sidebar
3. Map columns (ID, Name, Description)
4. Choose ranking strategy
5. Click **"Start rating mode"**
6. Complete comparisons
7. Download Excel file with rankings

Solo mode provides the same ranking functionality without creating persistent sessions.

## File Format

### Required Columns

Your Excel or CSV file must contain at least three columns:

1. **ID Column**: Unique identifier for each item
2. **Name Column**: Short name/title of the item
3. **Description Column**: Detailed description for comparison

### Example Format

| ID | Name | Description |
|----|------|-------------|
| 1 | Mobile App | Develop native mobile application for iOS and Android |
| 2 | API v2 | Redesign REST API with GraphQL support |
| 3 | Dashboard | Create analytics dashboard for customer insights |
| 4 | Payment System | Integrate new payment gateway for subscriptions |
| 5 | Dark Mode | Add dark theme support across all platforms |

### Supported File Types

- **Excel**: `.xlsx` files
- **CSV**: `.csv` files (comma-separated)

### Best Practices

- Keep names concise (2-5 words)
- Make descriptions clear and comparable
- Use consistent formatting
- Include enough detail for informed comparisons
- Recommended: 5-50 items per session (too few = trivial, too many = time-consuming)

## Technical Details

### Architecture

- **Frontend**: Streamlit for interactive UI
- **Data Storage**: JSON files in `sessions/` directory
- **Data Processing**: Pandas for DataFrame operations
- **Export**: XlsxWriter for Excel generation

### Session Storage

Sessions are stored as JSON files in the `sessions/` directory:
```
sessions/
├── abc123de.json
├── xyz789fg.json
└── ...
```

Each session file contains:
- Session metadata (ID, name, strategy)
- Item data
- Column mappings
- User results and rankings
- Strategy-specific settings

### State Management

The application uses Streamlit's session state to manage:
- View navigation (home, create, join, rating, results, solo)
- Current session and user information
- Rating progress for each strategy
- Temporary data during ranking

### Ranking Algorithms

**Binary Insertion Sort:**
- Time complexity: O(n log n) comparisons
- Space complexity: O(n)
- Deterministic ordering

**Elo Rating:**
- K-factor: 32 (standard chess rating)
- Starting rating: 1500
- Formula: New Rating = Old Rating + K × (Actual - Expected)

**Swiss Rounds:**
- Pairing algorithm: Sort by points, pair adjacent items
- Tiebreaker: Item index (lower index wins ties)
- Bye points: 1 point for items without opponents

## Testing

The project includes comprehensive test suites:

### Running Tests

**Test all strategies:**
```bash
python tests/test_strategies.py
```

**Test session management:**
```bash
python tests/test_sessions.py
```

**Test main application flow:**
```bash
python tests/test_main_app.py
```

### Test Coverage

- **Strategy Tests**: Binary, Elo, Swiss ranking algorithms
- **Session Tests**: CRUD operations, user results, averaging, export
- **App Tests**: View navigation, button interactions, state management

All tests use mocked Streamlit components for fast, isolated execution.

## Project Structure

```
prroritizer/
├── app.py                      # Main application
├── sessions/                   # Session data storage (auto-created)
│   └── *.json                 # Session files
├── tests/
│   ├── test_strategies.py     # Strategy algorithm tests
│   ├── test_sessions.py       # Session management tests
│   └── test_main_app.py       # Main app flow tests
├── Testdata.xlsx              # Example data file
└── README.md                  # This file
```

## Configuration

### Application Settings

Edit these constants in `app.py` if needed:

```python
APP_TITLE = "Prioritizer"
APP_ICON = "⚖️"
DEBUG = False  # Enable for verbose logging
SESSIONS_DIR = Path(__file__).parent / "sessions"
```

### Strategy Labels

Customize strategy display names:
```python
STRATEGY_LABELS = {
    STRATEGY_BINARY: "Interactive sort (fewest comparisons)",
    STRATEGY_ELO: "Elo tournament (rating-based)",
    STRATEGY_SWISS: "Swiss rounds (batch-style)",
}
```

## Troubleshooting

### Common Issues

**Application won't start:**
- Verify Python version: `python --version` (must be 3.7+)
- Check Streamlit installation: `pip show streamlit`
- Try: `pip install --upgrade streamlit pandas xlsxwriter`

**File upload errors:**
- Ensure file has correct format (Excel .xlsx or CSV)
- Check that required columns exist
- Verify file isn't corrupted or password-protected

**Session not found:**
- Check that `sessions/` directory exists
- Verify session wasn't deleted
- Sessions are stored as JSON files - don't modify manually

**Streamlit compatibility errors:**
- Update Streamlit: `pip install --upgrade streamlit`
- Current app requires Streamlit 1.0+
- Some features may require Streamlit 1.29+

### Getting Help

- Check error messages in the browser and terminal
- Review test files for usage examples
- Verify your data file format matches requirements

## License

This project is open source. Feel free to use, modify, and distribute.

## Credits

Built with:
- [Streamlit](https://streamlit.io/) - Web framework
- [Pandas](https://pandas.pydata.org/) - Data manipulation
- [XlsxWriter](https://xlsxwriter.readthedocs.io/) - Excel generation

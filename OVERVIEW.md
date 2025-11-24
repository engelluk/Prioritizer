# Prioritizer - Quick Reference Guide

**Interactive Impact Ranking Tool for Solo and Collaborative Decision-Making**

---

## What is Prioritizer?

Prioritizer is a web-based tool that helps individuals and teams rank ideas, features, or options through simple pairwise comparisons ("which has more impact?"). Instead of manually ordering dozens of items, you compare just two at a time, and the algorithm builds a complete ranking.

---

## Three Ways to Use It

### 1. Solo Mode
Quick individual ranking without sessions
- Upload your data → Compare items → Download results
- No session management needed
- Perfect for personal decision-making

### 2. Create Session
Set up collaborative ranking for your team
- Create named session with your data
- Multiple users can join and rank independently
- System calculates average consensus ranking
- Export combined results with individual rankings

### 3. Join Session
Participate in an existing team session
- Select session by name
- Enter your name and start ranking
- Your results automatically saved to session
- View combined results after completion

---

## Three Ranking Strategies

### Interactive Sort (Binary Insertion Sort)
**⚡ Fastest - Fewest Comparisons**

- Places items one-by-one into sorted order using binary search
- **Best for:** Datasets with 5-50 items where you want quick results
- **Comparisons:** ~25-30 for 10 items (O(n log n))
- **Ideal when:** You need the absolute minimum comparisons

**How it feels:**
Compare each new item against already-ranked items until you find its exact position.

---

### Elo Tournament (Rating-Based)
**📊 Flexible - Statistical Ranking**

- Assigns ratings to items (like chess players)
- Ratings increase/decrease based on wins/losses
- Can stop early or continue for better accuracy
- **Best for:** Larger datasets (20-100+ items) or when you want statistical confidence
- **Comparisons:** Configurable (5-10 games per item recommended)
- **Ideal when:** You want to see relative "strength" scores and don't mind more comparisons

**Configuration:**
- **Games per idea:** How many times each item gets compared (default: 5)
  - More games = more accurate but longer session

**How it feels:**
Random matchups, watch ratings evolve, stop when you're satisfied with the rankings.

---

### Swiss Rounds (Tournament Format)
**🏆 Structured - Round-by-Round**

- Organizes ranking into discrete rounds
- Items with similar scores face each other
- Clear progression through tournament rounds
- **Best for:** Medium datasets (10-50 items) where you want a tournament structure
- **Comparisons:** ~15 for 10 items with 3 rounds (n/2 × rounds)
- **Ideal when:** You prefer structured rounds over continuous comparisons

**Configuration:**
- **Number of rounds:** How many rounds to play (default: 3)
  - More rounds = better separation of rankings

**How it feels:**
Complete round 1, winners face winners in round 2, rankings emerge round-by-round.

---

## Quick Comparison Matrix

| Strategy | Comparisons Needed | Best Dataset Size | Flexibility | Use Case |
|----------|-------------------|-------------------|-------------|----------|
| **Binary Sort** | Fewest (25-30 for n=10) | 5-50 items | Low - must complete all | Need quick, definitive ranking |
| **Elo Tournament** | Configurable (25-50+ for n=10) | 20-100+ items | High - can stop anytime | Want statistical confidence |
| **Swiss Rounds** | Moderate (15 for n=10, 3 rounds) | 10-50 items | Medium - complete by round | Prefer tournament structure |

---

## Typical Workflow

### Solo Mode (5 minutes)
1. Run: `streamlit run app.py`
2. Click **"Solo Mode"**
3. Upload Excel/CSV with your items (columns: ID, Name, Description)
4. Choose strategy (Binary for speed, Elo for accuracy, Swiss for structure)
5. Click **"Start rating mode"**
6. Compare items pairwise
7. Download ranked Excel file

### Multi-User Session (15 minutes setup + 5 minutes per user)
1. **Session Creator:**
   - Click **"Create Session"**
   - Enter session name: "Q1 Product Features"
   - Upload data file
   - Choose strategy
   - Share session name with team

2. **Team Members:**
   - Click **"Join Session"**
   - Select "Q1 Product Features"
   - Enter your name
   - Complete comparisons
   - Results auto-saved

3. **View Results:**
   - Click **"View"** next to session on home screen
   - See who completed rankings
   - View combined average rankings
   - Download Excel with all individual + average rankings

---

## When to Use Which Strategy?

### Use Binary Sort When:
- You have < 50 items
- You want the absolute fastest completion
- You need a definitive order with minimum effort
- You're ranking once and don't need statistical confidence

### Use Elo Tournament When:
- You have > 20 items
- You want to understand relative "strengths" of items
- You might want to stop early but keep ranking flexible
- You're okay with more comparisons for better statistical validity
- You want to see rating scores alongside rankings

### Use Swiss Rounds When:
- You prefer a tournament-style format
- You want clear round-by-round structure
- You have 10-50 items
- You like the idea of winners facing winners
- You want moderate comparison count with good differentiation

---

## File Format

**Required columns in Excel/CSV:**
- **ID**: Unique identifier (e.g., 1, 2, 3 or FEAT-001, FEAT-002)
- **Name**: Short title (e.g., "Mobile App", "Dark Mode")
- **Description**: Full description for comparison

**Example:**
| ID | Name | Description |
|----|------|-------------|
| 1 | Mobile App | Native iOS/Android application with offline support |
| 2 | Dashboard | Real-time analytics dashboard for customer insights |
| 3 | API v2 | GraphQL API with improved performance |

---

## Output

### Solo Mode:
**Excel file with:**
- All columns from input file
- **ranking** column (1, 2, 3, ...)
- Strategy-specific metrics (elo_rating or points)

### Multi-User Session:
**Excel file with multiple sheets:**
- **Combined Rankings**: Average ranking across all users + std deviation
- **User_[Name]**: Individual ranking for each participant

**Average ranking calculation:**
For each item, take the average of its rank across all users.
Example: User A ranks Item X as #1, User B as #3, User C as #2 → Average rank = 2.0

---

## Installation & Running

```bash
# Install dependencies
pip install streamlit pandas xlsxwriter

# Run application
streamlit run app.py

# Browser opens automatically to http://localhost:8501
```

---

## Tips for Best Results

1. **Dataset Size:**
   - Sweet spot: 10-30 items
   - Fewer than 5: too simple, just manually rank
   - More than 50: gets tedious, consider pre-filtering

2. **Write Good Descriptions:**
   - Include enough detail to make informed comparisons
   - Be consistent in format and depth
   - Focus on comparable attributes

3. **Strategy Selection:**
   - Not sure? Start with **Binary Sort** (fastest)
   - Need statistical confidence? Use **Elo** with 5-8 games per idea
   - Want structure? Use **Swiss** with 3-5 rounds

4. **Multi-User Sessions:**
   - Brief participants on comparison criteria first
   - Have everyone use the same strategy
   - 3-5 participants is ideal (too many = slow convergence)
   - Review average + std deviation (high std = disagreement)

---

## System Requirements

- Python 3.7+
- Modern web browser (Chrome, Firefox, Safari, Edge)
- ~10-50 MB disk space for sessions
- No database needed (uses local JSON files)

---

## Key Features at a Glance

✅ Three proven ranking algorithms
✅ Solo and collaborative modes
✅ Excel import/export
✅ Real-time progress tracking
✅ Average consensus rankings
✅ Session management (create, join, view, delete)
✅ Individual and combined results
✅ No database required
✅ Fully self-contained web app

---

**Ready to start?** Run `streamlit run app.py` and start prioritizing! 🎯

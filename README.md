# JoSAA Rankings Explorer

An interactive, premium web application designed to analyze, filter, and explore JoSAA (Joint Seat Allocation Authority) opening and closing ranks cutoffs, alongside active seat matrix distributions and newly introduced engineering courses.

## Features

- **Cutoff Rankings Explorer**: Browse multi-year (2022–2025) opening and closing ranks with detailed filter controls (Institute Type, Quota, Gender Pool, and custom CRL thresholds).
- **New Courses & Capacity Tracker**: Analyze newly introduced engineering courses (starting from 2023–2026), excluding baseline courses ($year \le 2022$). Inspect category seat breakdowns (OPEN, EWS, OBC-NCL, SC, ST) and female supernumerary capacities.
- **Interactive First-Time Setup**: Prompts users with a clean modal dialog to enter their JEE ranks and Home State on first startup. The profile displays dynamically in the sidebar with an option to edit/update via popup.
- **Performance Optimized Backend**:
  - Precomputes NIRF rankings for all 132 unique colleges at startup, replacing runtime fuzzy matching.
  - SQLite indexes on `(institute, program, year)` and `(seat_type, year, round)` for sub-millisecond query execution.
  - Automatically parses and splits master `ALL.json` files on database initialization to minimize storage footprint.
- **Data Sourcing Utilities**: Features standalone scraping tools to fetch historical cutoff ranks and seat matrices directly from the official JoSAA admissions portal.

---

## Tech Stack

- **Backend**: FastAPI (Python 3.10+), SQLite
- **Frontend**: HTML5, Vanilla CSS3 (Glassmorphism & tailored HSL accents), Vanilla Javascript (ES6+)
- **Libraries**: BeautifulSoup4, Requests, Uvicorn, Pandas

---

## Directory Structure

```
.
├── data/
│   ├── josaa_raw/              # Raw data backups (master ALL.json and seat matrix json)
│   └── nirf_rankings_2025.json # Static NIRF ranking dataset
├── data_sourcing/
│   ├── scraper.py              # On-demand individual rankings scraper
│   ├── seat_matrix_scraper.py  # Crawls the official JoSAA seat matrix
│   └── bulk_scraper.py         # Multi-threaded verified bulk rankings downloader
├── static/
│   ├── index.html              # Main frontend HTML markup
│   ├── style.css               # Styled visual layout and theme parameters
│   └── app.js                  # Frontend client application logic
├── db.py                       # SQLite DB initialization & category parser
├── main.py                     # FastAPI backend server
├── requirements.txt            # Python dependencies lists
└── run.sh                      # Shell launch launcher
```

---

## Installation & Setup

1. **Clone the Repository**:
   ```bash
   git clone <your-repository-url>
   cd josaa
   ```

2. **Setup Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Populate Database**:
   Run the database initialization script. It will scan `data/josaa_raw/`, import the master data, and configure the optimized indexes:
   ```bash
   python3 db.py
   ```

4. **Launch Server**:
   Execute the run script or start Uvicorn directly:
   ```bash
   ./run.sh
   ```
   The application will be live at `http://localhost:8000`.

---

## Sourcing New Data

To fetch fresh records from the admissions portal, run the scripts inside the `data_sourcing/` folder:
- **Fetch Seat Matrix**: `python3 data_sourcing/seat_matrix_scraper.py`
- **Bulk Fetch Ranks**: `python3 data_sourcing/bulk_scraper.py` (Automatically checks for cached rounds and crawls missing ones).

---

## Credits & Contributions

- **Concept & Inputs**: Repository Owner (Anupam Khurana)
- **Development & Coding**: Built in collaboration with **Antigravity** (Google DeepMind's advanced agentic coding AI assistant)


# 🎓 JoSAA Rankings Explorer & Seat Matrix Analyzer

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org)
[![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

An interactive, high-performance web analytics application designed to analyze, filter, and explore **JoSAA (Joint Seat Allocation Authority)** opening and closing rank cutoffs (2022–2025), NIRF rankings, and active seat matrix distributions across all **IITs, NITs, IIITs, and GFTIs**.

---

## ⚡ Highlights & Key Features

- 🔍 **Multi-Year Cutoff Rankings Explorer**: Query opening and closing ranks across admission cycles (2022–2025) with filters for Institute Type (IIT, NIT, IIIT, GFTI), Quota (Home State vs. Other State), Category (OPEN, EWS, OBC-NCL, SC, ST), Gender Pool (Female-only supernumerary), and custom CRL thresholds.
- 📈 **New Courses & Capacity Tracker**: Track newly launched branch additions and emergent engineering streams across IITs/NITs with detailed category seat splits.
- 🎯 **JEE Rank & State Profile Matching**: Personalized setup modal saves candidate JEE Advanced/Main ranks and home state to dynamically highlight eligible college branches and closing rank safety margins.
- ⚡ **Optimized Performance Architecture**:
  - Precomputes NIRF rankings across all 132 engineering colleges at boot to bypass fuzzy matching overhead.
  - Multi-column composite SQLite indexes on `(institute, program, year)` and `(seat_type, year, round)` for sub-millisecond query execution.
  - Efficient JSON streaming parsers that minimize database size and memory footprint.
- 🕷️ **Automated Data Sourcing Crawlers**: Includes standalone multi-threaded scraping tools to fetch official rounds, seat quotas, and closing ranks directly from JoSAA admissions portals.

---

## 🏗️ Architecture & Tech Stack

| Layer | Component | Description |
| :--- | :--- | :--- |
| **Backend API** | [FastAPI](https://fastapi.tiangolo.com/) | REST API with asynchronous request dispatch and CORS handling |
| **Data Storage** | [SQLite](https://www.sqlite.org/) | Relational database with composite indexing |
| **ETL & Data Sourcing** | BeautifulSoup4, Requests, Pandas | Automated scrapers for JoSAA portal datasets |
| **Frontend UI** | HTML5, Modern CSS Glassmorphism, Vanilla JS | Lightweight zero-dependency reactive interface |

---

## 📂 Directory Structure

```text
josaa/
├── data/
│   ├── josaa_raw/              # Raw JoSAA historical datasets & seat matrices
│   └── nirf_rankings_2025.json # Static NIRF ranking dataset for 132+ institutions
├── data_sourcing/
│   ├── scraper.py              # On-demand individual rankings scraper
│   ├── seat_matrix_scraper.py  # Crawls the official JoSAA seat matrix
│   └── bulk_scraper.py         # Multi-threaded verified bulk rankings downloader
├── static/
│   ├── index.html              # Main frontend dashboard
│   ├── style.css               # Glassmorphism styling and theme accents
│   └── app.js                  # Frontend client application logic & state
├── db.py                       # SQLite DB initialization & category parser
├── main.py                     # FastAPI backend server
├── requirements.txt            # Python dependencies
└── run.sh                      # Shell launch script
```

---

## 🚀 Quick Start Guide

### 1. Clone the Repository
```bash
git clone https://github.com/AnupamKhurana/josaa-rankings-explorer.git
cd josaa-rankings-explorer
```

### 2. Set Up Virtual Environment & Dependencies
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Populate Database
Initialize the SQLite database with historical JoSAA rounds and NIRF rankings:
```bash
python3 db.py
```

### 4. Launch Application
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
*(Or use `./run.sh`)*

Open your browser at: **`http://localhost:8000`**

---

## 🕷️ Sourcing New Admissions Data

To fetch fresh records from the official portal for new admission rounds:
- **Fetch Seat Matrix:** `python3 data_sourcing/seat_matrix_scraper.py`
- **Bulk Fetch Ranks:** `python3 data_sourcing/bulk_scraper.py` (Automatically checks cached rounds and downloads missing records).

---

## 📄 License

This project is licensed under the MIT License. See `LICENSE` for details.

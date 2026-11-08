import os
import json
import re
from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pandas as pd

from data_sourcing.scraper import get_cached_ranks, scrape_josaa_ranks
from db import init_db, import_existing_json_caches, get_db_connection, has_dataset

app = FastAPI(title="JoSAA Rankings Explorer")

# Get absolute path to the directory this file is in
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# NIRF rankings global data
nirf_map = {}
nirf_data = []
institute_nirf_cache = {}

# IIRF rankings global data
iirf_map = {}
iirf_data = []
institute_iirf_cache = {}

def init_nirf_data():
    global nirf_map, nirf_data
    nirf_path = os.path.join(BASE_DIR, "data", "nirf_rankings_2025.json")
    if os.path.exists(nirf_path):
        try:
            with open(nirf_path, "r", encoding="utf-8") as f:
                nirf_data = json.load(f)
            # Build normalized map
            def normalize(name):
                name = name.lower()
                name = re.sub(r'[^\w\s]', ' ', name)
                name = re.sub(r'\s+', ' ', name).strip()
                return name
            nirf_map = {normalize(item["name"]): item["rank"] for item in nirf_data}
            print(f"Loaded {len(nirf_data)} NIRF rankings.")
        except Exception as e:
            print(f"Error loading NIRF: {e}")

def init_iirf_data():
    global iirf_map, iirf_data
    iirf_path = os.path.join(BASE_DIR, "data", "iirf_rankings_2025.json")
    if os.path.exists(iirf_path):
        try:
            with open(iirf_path, "r", encoding="utf-8") as f:
                iirf_data = json.load(f)
            # Build normalized map
            def normalize(name):
                name = name.lower()
                name = re.sub(r'[^\w\s]', ' ', name)
                name = re.sub(r'\s+', ' ', name).strip()
                return name
            iirf_map = {normalize(item["name"]): item["rank"] for item in iirf_data}
            print(f"Loaded {len(iirf_data)} IIRF rankings.")
        except Exception as e:
            print(f"Error loading IIRF: {e}")

# Call init on startup
init_nirf_data()
init_iirf_data()

# Init SQLite DB and import any existing caches/data
init_db()
import_existing_json_caches()

STATE_PATTERNS = [
    ("Delhi", ["delhi"]),
    ("Maharashtra", ["bombay", "mumbai", "nagpur", "aurangabad", "pune", "vnit"]),
    ("Kerala", ["calicut", "kottayam"]),
    ("Tamil Nadu", ["trichy", "tiruchirappalli", "madras", "salem", "thanjavur", "kancheepuram"]),
    ("Karnataka", ["surathkal", "karnataka", "raichur", "dharwad"]),
    ("Andhra Pradesh", ["andhra", "kurnool", "tirupati", "vijayawada", "sri city", "chittoor"]),
    ("Uttar Pradesh", ["allahabad", "varanasi", "bhadohi", "gorakhpur", "amethi", "lucknow", "kanpur", "mmnit"]),
    ("Jharkhand", ["ranchi", "jamshedpur", "dhanbad", "jharkhand", "deoghar", "ism"]),
    ("Odisha", ["rourkela", "bhubaneswar", "odisha"]),
    ("Assam", ["silchar", "guwahati", "assam", "tezpur", "kokrajar"]),
    ("Bihar", ["patna", "bhagalpur", "bihar"]),
    ("Rajasthan", ["jaipur", "rajasthan", "ajmer", "kota", "jodhpur"]),
    ("Madhya Pradesh", ["bhopal", "gwalior", "indore", "jabalpur", "sagar", "manit"]),
    ("Gujarat", ["gandhinagar", "vadodara", "surat", "gujarat", "gujrat", "ahmedabad", "svnit"]),
    ("Uttarakhand", ["roorkee", "uttarakhand", "haridwar"]),
    ("Punjab", ["ropar", "punjab", "longowal", "jalandhar"]),
    ("Himachal Pradesh", ["hamirpur", "una", "mandi", "himachal"]),
    ("Jammu & Kashmir", ["katra", "jammu", "srinagar", "kashmir"]),
    ("Sikkim", ["sikkim"]),
    ("Goa", ["goa"]),
    ("Meghalaya", ["meghalaya", "shillong"]),
    ("Manipur", ["manipur"]),
    ("Mizoram", ["mizoram", "aizawl"]),
    ("Nagaland", ["nagaland"]),
    ("Arunachal Pradesh", ["arunachal", "nirjuli", "itanagar"]),
    ("Tripura", ["tripura", "agartala"]),
    ("Chhattisgarh", ["chhattisgarh", "bhilai", "raipur", "bilaspur"]),
    ("Haryana", ["haryana", "kundli", "sonepat", "kurukshetra"]),
    ("Puducherry", ["puducherry"]),
    ("Chandigarh", ["chandigarh"]),
    ("Ladakh", ["ladakh"]),
    ("Daman & Diu", ["diu"]),
    ("Telangana", ["hyderabad", "warangal"]),
    ("West Bengal", ["shibpur", "kalyani", "malda", "west bengal", "kharagpur"])
]

def get_institute_state(inst_name: str) -> str:
    name_lower = inst_name.lower()
    for state, patterns in STATE_PATTERNS:
        for p in patterns:
            if p in name_lower:
                return state
    return "Other"

def get_nirf_rank(institute_name):
    global nirf_map, nirf_data, institute_nirf_cache
    if not nirf_map:
        return None
    if institute_name in institute_nirf_cache:
        return institute_nirf_cache[institute_name]
        
    def normalize(name):
        name = name.lower()
        name = re.sub(r'[^\w\s]', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name
        
    def get_type(norm_name):
        if 'information technology' in norm_name or 'iiit' in norm_name:
            return 'iiit'
        if 'technology' in norm_name and ('indian institute' in norm_name or 'iit' in norm_name):
            if 'handloom' in norm_name or 'carpet' in norm_name:
                return 'other'
            return 'iit'
        if 'national institute' in norm_name and 'technology' in norm_name:
            return 'nit'
        return 'other'
        
    j_norm = normalize(institute_name)
    j_type = get_type(j_norm)
    best_match = None
    
    # Heuristic 1: Exact normalization match
    for n_item in nirf_data:
        n_norm = normalize(n_item['name'])
        if j_norm == n_norm:
            best_match = n_item
            break
            
    # Heuristic 2: For IIT/NIT/IIIT, match by city
    if not best_match and j_type in ['iit', 'nit', 'iiit']:
        j_words = set(j_norm.split())
        for n_item in nirf_data:
            n_norm = normalize(n_item['name'])
            n_type = get_type(n_norm)
            if j_type == n_type:
                n_words = set(n_norm.split())
                cities = {
                    'madras', 'chennai', 'delhi', 'bombay', 'mumbai', 'kanpur', 'kharagpur', 'roorkee', 
                    'hyderabad', 'guwahati', 'varanasi', 'bhu', 'dhanbad', 'ism', 'ropar', 'bhubaneswar', 
                    'gandhinagar', 'patna', 'indore', 'mandi', 'jodhpur', 'tirupati', 'palakkad', 'bhilai', 
                    'dharwad', 'jammu', 'goa', 'tiruchirappalli', 'trichy', 'surathkal', 'karnataka', 
                    'warangal', 'calicut', 'kozhikode', 'rourkela', 'kurukshetra', 'allahabad', 'mmnit', 
                    'nagpur', 'vnit', 'silchar', 'durgapur', 'hamirpur', 'jalandhar', 'meghalaya', 'raipur', 
                    'srinagar', 'jamshedpur', 'agartala', 'manipur', 'mizoram', 'nagaland', 'puducherry', 
                    'sikkim', 'uttarakhand', 'andhra', 'gwalior', 'jabalpur', 'kancheepuram', 'kurnool', 
                    'kota', 'sri', 'city', 'vadodara', 'pune', 'surat', 'bhopal', 'bhagalpur', 'kalyani', 
                    'una', 'sonepat', 'kottayam', 'ranchi'
                }
                shared = j_words.intersection(n_words).intersection(cities)
                if shared:
                    best_match = n_item
                    break
                    
    # Heuristic 3: Fuzzy match ONLY for 'other' types, with strict safeguards
    if not best_match and j_type == 'other':
        import difflib
        best_score = 0
        for n_item in nirf_data:
            n_norm = normalize(n_item['name'])
            n_type = get_type(n_norm)
            
            if n_type != 'other':
                continue
                
            score = difflib.SequenceMatcher(None, j_norm, n_norm).ratio()
            if score > best_score:
                best_score = score
                best_match = n_item
                
        # Only accept very high similarity
        if best_score < 0.85:
            best_match = None
        elif 'birla' in j_norm and 'mesra' not in j_norm:
            best_match = None
            
    if best_match:
        try:
            rank = int(best_match['rank'])
            institute_nirf_cache[institute_name] = rank
            return rank
        except:
            pass
            
    institute_nirf_cache[institute_name] = None
    return None

def precompute_nirf_ranks():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT institute FROM josaa_ranks")
    institutes = [r[0] for r in cursor.fetchall()]
    conn.close()
    for inst in institutes:
        get_nirf_rank(inst)
    print(f"Precomputed NIRF ranks for {len(institutes)} institutes.")

def get_iirf_rank(institute_name):
    global iirf_map, iirf_data, institute_iirf_cache
    if not iirf_map:
        return None
    if institute_name in institute_iirf_cache:
        return institute_iirf_cache[institute_name]
        
    def normalize(name):
        name = name.lower()
        name = re.sub(r'[^\w\s]', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name
        
    def get_type(norm_name):
        if 'information technology' in norm_name or 'iiit' in norm_name:
            return 'iiit'
        if 'technology' in norm_name and ('indian institute' in norm_name or 'iit' in norm_name):
            if 'handloom' in norm_name or 'carpet' in norm_name:
                return 'other'
            return 'iit'
        if 'national institute' in norm_name and 'technology' in norm_name:
            return 'nit'
        return 'other'
        
    j_norm = normalize(institute_name)
    j_type = get_type(j_norm)
    best_match = None
    
    # Heuristic 1: Exact normalization match
    for n_item in iirf_data:
        n_norm = normalize(n_item['name'])
        if j_norm == n_norm:
            best_match = n_item
            break
            
    # Heuristic 2: For IIT/NIT/IIIT, match by city
    if not best_match and j_type in ['iit', 'nit', 'iiit']:
        j_words = set(j_norm.split())
        for n_item in iirf_data:
            n_norm = normalize(n_item['name'])
            n_type = get_type(n_norm)
            if j_type == n_type:
                n_words = set(n_norm.split())
                cities = {
                    'madras', 'chennai', 'delhi', 'bombay', 'mumbai', 'kanpur', 'kharagpur', 'roorkee', 
                    'hyderabad', 'guwahati', 'varanasi', 'bhu', 'dhanbad', 'ism', 'ropar', 'bhubaneswar', 
                    'gandhinagar', 'patna', 'indore', 'mandi', 'jodhpur', 'tirupati', 'palakkad', 'bhilai', 
                    'dharwad', 'jammu', 'goa', 'tiruchirappalli', 'trichy', 'surathkal', 'karnataka', 
                    'warangal', 'calicut', 'kozhikode', 'rourkela', 'kurukshetra', 'allahabad', 'mmnit', 
                    'nagpur', 'vnit', 'silchar', 'durgapur', 'hamirpur', 'jalandhar', 'meghalaya', 'raipur', 
                    'srinagar', 'jamshedpur', 'agartala', 'manipur', 'mizoram', 'nagaland', 'puducherry', 
                    'sikkim', 'uttarakhand', 'andhra', 'gwalior', 'jabalpur', 'kancheepuram', 'kurnool', 
                    'kota', 'sri', 'city', 'vadodara', 'pune', 'surat', 'bhopal', 'bhagalpur', 'kalyani', 
                    'una', 'sonepat', 'kottayam', 'ranchi'
                }
                shared = j_words.intersection(n_words).intersection(cities)
                if shared:
                    best_match = n_item
                    break
                    
    # Heuristic 3: Fuzzy match ONLY for 'other' types, with strict safeguards
    if not best_match and j_type == 'other':
        import difflib
        best_score = 0
        for n_item in iirf_data:
            n_norm = normalize(n_item['name'])
            n_type = get_type(n_norm)
            
            if n_type != 'other':
                continue
                
            score = difflib.SequenceMatcher(None, j_norm, n_norm).ratio()
            if score > best_score:
                best_score = score
                best_match = n_item
                
        # Only accept very high similarity
        if best_score < 0.85:
            best_match = None
        elif 'birla' in j_norm and 'mesra' not in j_norm:
            best_match = None
            
    if best_match:
        try:
            rank = int(best_match['rank'])
            institute_iirf_cache[institute_name] = rank
            return rank
        except:
            pass
            
    institute_iirf_cache[institute_name] = None
    return None

def precompute_iirf_ranks():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT institute FROM josaa_ranks")
    institutes = [r[0] for r in cursor.fetchall()]
    conn.close()
    for inst in institutes:
        get_iirf_rank(inst)
    print(f"Precomputed IIRF ranks for {len(institutes)} institutes.")

precompute_nirf_ranks()
precompute_iirf_ranks()

class ScrapeRequest(BaseModel):
    year: str = "2025"
    round_no: str = "6"
    seat_type: str = "OPNO"

# In-memory dataframe cache to avoid loading JSON on every single request
df_cache = {}

def ensure_dataset(year: str, round_no: str, seat_type: str):
    if not has_dataset(year, round_no, seat_type):
        try:
            print(f"Dataset {year}_r{round_no}_{seat_type} not in DB. Triggering scrape...")
            scrape_josaa_ranks(year, round_no, seat_type)
        except Exception as e:
            print(f"Auto-scrape failed: {e}")

@app.get("/api/filters")
def get_filters(round_no: str = "6", seat_type: str = "OPNO"):
    r_2025 = str(min(int(round_no), 6))
    r_2024 = str(min(int(round_no), 5))
    r_2023 = str(min(int(round_no), 6))
    r_2022 = str(min(int(round_no), 6))
    
    ensure_dataset("2025", r_2025, seat_type)
    ensure_dataset("2024", r_2024, seat_type)
    ensure_dataset("2023", r_2023, seat_type)
    ensure_dataset("2022", r_2022, seat_type)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT institute FROM josaa_ranks 
        WHERE seat_type = ? AND (
            (year = '2025' AND round = ?) OR
            (year = '2024' AND round = ?) OR
            (year = '2023' AND round = ?) OR
            (year = '2022' AND round = ?)
        )
        ORDER BY institute
    """, (str(seat_type), r_2025, r_2024, r_2023, r_2022))
    institutes = [r[0] for r in cursor.fetchall()]
    
    cursor.execute("""
        SELECT DISTINCT program FROM josaa_ranks 
        WHERE seat_type = ? AND (
            (year = '2025' AND round = ?) OR
            (year = '2024' AND round = ?) OR
            (year = '2023' AND round = ?) OR
            (year = '2022' AND round = ?)
        )
        ORDER BY program
    """, (str(seat_type), r_2025, r_2024, r_2023, r_2022))
    programs = [r[0] for r in cursor.fetchall()]
    
    cursor.execute("""
        SELECT DISTINCT quota FROM josaa_ranks 
        WHERE seat_type = ? AND (
            (year = '2025' AND round = ?) OR
            (year = '2024' AND round = ?) OR
            (year = '2023' AND round = ?) OR
            (year = '2022' AND round = ?)
        )
        ORDER BY quota
    """, (str(seat_type), r_2025, r_2024, r_2023, r_2022))
    quotas = [r[0] for r in cursor.fetchall()]
    
    cursor.execute("""
        SELECT DISTINCT gender FROM josaa_ranks 
        WHERE seat_type = ? AND (
            (year = '2025' AND round = ?) OR
            (year = '2024' AND round = ?) OR
            (year = '2023' AND round = ?) OR
            (year = '2022' AND round = ?)
        )
        ORDER BY gender
    """, (str(seat_type), r_2025, r_2024, r_2023, r_2022))
    genders = [r[0] for r in cursor.fetchall()]
    
    cursor.execute("""
        SELECT MIN(opening_rank), MAX(opening_rank), MIN(closing_rank), MAX(closing_rank) 
        FROM josaa_ranks 
        WHERE seat_type = ? AND (
            (year = '2025' AND round = ?) OR
            (year = '2024' AND round = ?) OR
            (year = '2023' AND round = ?) OR
            (year = '2022' AND round = ?)
        ) AND opening_rank < 999999 AND closing_rank < 999999
    """, (str(seat_type), r_2025, r_2024, r_2023, r_2022))
    stats_row = cursor.fetchone()
    
    rank_stats = {
        "min_opening": stats_row[0] if stats_row and stats_row[0] is not None else 1,
        "max_opening": stats_row[1] if stats_row and stats_row[1] is not None else 100000,
        "min_closing": stats_row[2] if stats_row and stats_row[2] is not None else 1,
        "max_closing": stats_row[3] if stats_row and stats_row[3] is not None else 100000,
    }
    
    conn.close()
    
    return {
        "institutes": institutes,
        "programs": programs,
        "quotas": quotas,
        "genders": genders,
        "rank_stats": rank_stats
    }

@app.get("/api/ranks")
def get_ranks(
    round_no: str = "6",
    seat_type: str = "OPNO",
    search: str = None,
    institute: list[str] = Query(None),
    program: list[str] = Query(None),
    quota: list[str] = Query(None),
    gender: str = None,
    min_opening: int = None,
    max_opening: int = None,
    min_closing: int = None,
    max_closing: int = None,
    mains_min: int = None,
    adv_min: int = None,
    filter_mains: bool = False,
    filter_adv: bool = False,
    sort_by: str = "closing_rank",
    sort_desc: bool = False,
    home_state: str = None,
    user_mains_rank: int = None,
    user_adv_rank: int = None,
    page: int = 1,
    limit: int = 50
):
    r_2025 = str(min(int(round_no), 6))
    r_2024 = str(min(int(round_no), 5))
    r_2023 = str(min(int(round_no), 6))
    r_2022 = str(min(int(round_no), 6))

    ensure_dataset("2025", r_2025, seat_type)
    ensure_dataset("2024", r_2024, seat_type)
    ensure_dataset("2023", r_2023, seat_type)
    ensure_dataset("2022", r_2022, seat_type)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    base_query = """
        SELECT r.institute, r.program, r.quota, r.seat_type, r.gender, 
               MAX(CASE WHEN r.year = '2025' THEN r.opening_rank END) AS opening_2025,
               MAX(CASE WHEN r.year = '2025' THEN r.closing_rank END) AS closing_2025,
               MAX(CASE WHEN r.year = '2024' THEN r.closing_rank END) AS closing_2024,
               MAX(CASE WHEN r.year = '2023' THEN r.closing_rank END) AS closing_2023,
               MAX(CASE WHEN r.year = '2022' THEN r.closing_rank END) AS closing_2022,
               MAX(CASE WHEN r.year = '2025' THEN r.opening_rank_str END) AS opening_2025_str,
               MAX(CASE WHEN r.year = '2025' THEN r.closing_rank_str END) AS closing_2025_str,
               MAX(CASE WHEN r.year = '2024' THEN r.closing_rank_str END) AS closing_2024_str,
               MAX(CASE WHEN r.year = '2023' THEN r.closing_rank_str END) AS closing_2023_str,
               MAX(CASE WHEN r.year = '2022' THEN r.closing_rank_str END) AS closing_2022_str,
               i.state AS institute_state,
               i.exam_type
        FROM josaa_ranks r
        LEFT JOIN josaa_institutes i ON r.institute = i.institute
        WHERE r.seat_type = ? AND (
            (r.year = '2025' AND r.round = ?) OR
            (r.year = '2024' AND r.round = ?) OR
            (r.year = '2023' AND r.round = ?) OR
            (r.year = '2022' AND r.round = ?)
        )
        GROUP BY r.institute, r.program, r.quota, r.seat_type, r.gender, i.state, i.exam_type
    """
    
    user_mains_rank_val = user_mains_rank or 0
    user_adv_rank_val = user_adv_rank or 0

    query = f"""
        SELECT institute, program, quota, seat_type, gender,
               opening_2025, closing_2025, closing_2024, closing_2023, closing_2022,
               opening_2025_str, closing_2025_str, closing_2024_str, closing_2023_str, closing_2022_str,
               institute_state, exam_type,
               COALESCE(opening_2025, 999999) AS opening_rank,
               COALESCE(closing_2025, closing_2024, closing_2023, closing_2022, 999999) AS closing_rank,
               CASE 
                   WHEN exam_type = 'JEE-Advanced' THEN 
                       (CASE WHEN {user_adv_rank_val} > 0 AND COALESCE(closing_2025, closing_2024, closing_2023, closing_2022, 999999) < 999999 THEN CAST(COALESCE(closing_2025, closing_2024, closing_2023, closing_2022, 999999) AS REAL) / {user_adv_rank_val} ELSE NULL END)
                   ELSE 
                       (CASE WHEN {user_mains_rank_val} > 0 AND COALESCE(closing_2025, closing_2024, closing_2023, closing_2022, 999999) < 999999 THEN CAST(COALESCE(closing_2025, closing_2024, closing_2023, closing_2022, 999999) AS REAL) / {user_mains_rank_val} ELSE NULL END)
               END AS standardized_ratio
        FROM ({base_query})
        WHERE 1=1
    """
    params = [str(seat_type), r_2025, r_2024, r_2023, r_2022]
    
    if search:
        query += " AND (LOWER(institute) LIKE ? OR LOWER(program) LIKE ?)"
        params.extend([f"%{search.lower()}%", f"%{search.lower()}%"])
        
    if institute:
        placeholders = ",".join("?" for _ in institute)
        query += f" AND institute IN ({placeholders})"
        params.extend(institute)
        
    if program:
        placeholders = ",".join("?" for _ in program)
        query += f" AND program IN ({placeholders})"
        params.extend(program)
        
    if quota:
        placeholders = ",".join("?" for _ in quota)
        query += f" AND quota IN ({placeholders})"
        params.extend(quota)
        
    if gender and gender != "ALL":
        query += " AND gender = ?"
        params.append(gender)
        
    if min_opening is not None:
        query += " AND opening_rank >= ?"
        params.append(min_opening)
    if max_opening is not None:
        query += " AND opening_rank <= ?"
        params.append(max_opening)
        
    if home_state and home_state != "ALL":
        query += """ AND (
            (institute_state = ? AND quota != 'OS') OR 
            (institute_state != ? AND quota != 'HS') OR 
            (quota = 'AI')
        )"""
        params.extend([home_state, home_state])
        
        # Query special quotas dynamically from DB
        cursor.execute("SELECT quota, state FROM josaa_special_quotas")
        special_quotas = cursor.fetchall()
        for sq_quota, sq_state in special_quotas:
            query += f" AND NOT (quota = '{sq_quota}' AND ? != '{sq_state}')"
            params.append(home_state)
        
    if filter_mains and filter_adv:
        query += """ AND (
            (exam_type = 'JEE-Advanced' AND closing_rank >= ?) OR 
            (exam_type != 'JEE-Advanced' AND closing_rank >= ?)
        )"""
        params.extend([adv_min or 1, mains_min or 1])
    elif filter_mains:
        query += " AND exam_type != 'JEE-Advanced' AND closing_rank >= ?"
        params.extend([mains_min or 1])
    elif filter_adv:
        query += " AND exam_type = 'JEE-Advanced' AND closing_rank >= ?"
        params.extend([adv_min or 1])
    else:
        if min_closing is not None:
            query += " AND closing_rank >= ?"
            params.append(min_closing)
        if max_closing is not None:
            query += " AND closing_rank <= ?"
            params.append(max_closing)
            
    count_query = f"SELECT COUNT(*) FROM ({query})"
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]
    
    valid_sorts = {
        "opening_rank": "opening_rank",
        "closing_rank": "closing_rank",
        "institute": "institute",
        "program": "program",
        "quota": "quota",
        "gender": "gender",
        "standardized_ratio": "standardized_ratio"
    }
    sort_column = valid_sorts.get(sort_by, "closing_rank")
    direction = "DESC" if sort_desc else "ASC"
    
    if sort_column in ["opening_rank", "closing_rank"]:
        query += f" ORDER BY CASE WHEN {sort_column} >= 999999 THEN 1 ELSE 0 END, {sort_column} {direction}"
    elif sort_column == "standardized_ratio":
        query += f" ORDER BY CASE WHEN standardized_ratio IS NULL THEN 1 ELSE 0 END, standardized_ratio {direction}"
    else:
        query += f" ORDER BY {sort_column} {direction}"
        
    if limit > 0:
        query += " LIMIT ? OFFSET ?"
        offset = (page - 1) * limit
        params.extend([limit, offset])
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    ranks_list = [dict(row) for row in rows]
    
    for r in ranks_list:
        r["nirf_rank"] = get_nirf_rank(r["institute"])
        r["iirf_rank"] = get_iirf_rank(r["institute"])
        
    stats_query = f"""
        SELECT MIN(opening_rank), MAX(opening_rank), MIN(closing_rank), MAX(closing_rank)
        FROM ({query.split(" LIMIT ")[0]})
        WHERE opening_rank < 999999 AND closing_rank < 999999
    """
    stats_params = params[:-2] if limit > 0 else params
    cursor.execute(stats_query, stats_params)
    stats_row = cursor.fetchone()
    
    filtered_stats = {
        "min_opening": stats_row[0] if stats_row and stats_row[0] is not None else 0,
        "max_opening": stats_row[1] if stats_row and stats_row[1] is not None else 0,
        "min_closing": stats_row[2] if stats_row and stats_row[2] is not None else 0,
        "max_closing": stats_row[3] if stats_row and stats_row[3] is not None else 0,
    }
    
    conn.close()
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "rounds_used": {
            "2025": int(r_2025),
            "2024": int(r_2024),
            "2023": int(r_2023),
            "2022": int(r_2022)
        },
        "ranks": ranks_list,
        "filtered_stats": filtered_stats
    }

@app.post("/api/scrape")
def trigger_scrape(req: ScrapeRequest):
    try:
        data = scrape_josaa_ranks(req.year, req.round_no, req.seat_type)
        return {"status": "success", "count": len(data), "message": f"Successfully scraped {len(data)} items."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/new-courses")
def get_new_courses():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch all seat matrix courses (these are the active ones)
    cursor.execute("SELECT DISTINCT institute, program, quota, seat_pool, open, open_pwd, gen_ews, gen_ews_pwd, sc, sc_pwd, st, st_pwd, obc_ncl, obc_ncl_pwd, total, program_total, female_supernumerary, institute_state FROM josaa_seat_matrix WHERE year = (SELECT MAX(year) FROM josaa_seat_matrix)")
    seat_rows = cursor.fetchall()
    
    # Fetch all historic ranking courses with their first cutoff year
    cursor.execute("SELECT institute, program, MIN(year) as first_year FROM josaa_ranks GROUP BY institute, program")
    rank_rows = cursor.fetchall()
    conn.close()
    
    # Normalize comparison function to handle minor spelling changes like plurals, spacing, punctuation, and structural renames
    def normalize_name(name):
        # Convert to lowercase
        name = name.lower()
        
        # Preserve the program duration to prevent mixing different program types (e.g. 4-year and 5-year B.Techs)
        duration_match = re.search(r'\((\d+)\s*years', name)
        duration_prefix = f"({duration_match.group(1)}y) " if duration_match else ""
        
        # Remove parentheses content representing degree descriptors
        name = re.sub(r'\s*\([^)]*\)', '', name)
        
        # Replace hyphens, slashes, and periods with single spaces to reconcile punctuation/structural differences
        name = re.sub(r'[-/.]', ' ', name)
        
        # Remove common punctuation (commas, single quotes, double quotes, colons, semi-colons, ampersands)
        name = re.sub(r'[,\'":;&]', '', name)
        
        # Normalize double/multiple spaces and strip leading/trailing spaces
        name = re.sub(r'\s+', ' ', name.strip())
        
        # Replace plurals (e.g. "sciences" -> "science") at the end of words or strings to match minor rename nuances
        name = re.sub(r'\b(science)s\b', r'\1', name)
        name = re.sub(r'\b(engineering)s\b', r'\1', name)
        name = re.sub(r'\b(program)s\b', r'\1', name)
        name = re.sub(r'\b(resource)s\b', r'\1', name)
        name = re.sub(r'\b(technology)ies\b', r'technology', name)
        
        # Normalize structural variations in degrees
        name = name.replace("science-master of science", "science")
        name = name.replace("materials science and metallurgical", "metallurgical and materials")
        name = name.replace("materials and metallurgical", "metallurgical and materials")
        name = name.replace("metallurgy and materials", "metallurgical and materials")
        name = name.replace("integrated b tech and mba", "integrated b.tech and mba")
        name = name.replace("integrated b. tech. and mba", "integrated b.tech and mba")
        name = name.replace("b tech and mba dual degree", "integrated b.tech and mba")
        name = name.replace("b.tech and mba dual degree", "integrated b.tech and mba")
        name = name.replace("integrated master of technology", "dual degree")
        name = name.replace("integrated master of science", "master of science")
        name = name.replace("integrated bachelor of science master of science", "master of science")
        name = name.replace("bachelor and master of technology dual degree", "dual degree")
        
        # Final whitespace normalization pass
        name = re.sub(r'\s+', ' ', name.strip())
        return duration_prefix + name
        
    # Build a mapping of normalized (inst, prog) -> first_year
    historic_first_years = {}
    # We also keep a mapping of normalized (inst, prog) -> original (inst, prog) to help reconstruct fields for discontinued courses if needed
    original_names = {}
    
    for r in rank_rows:
        inst_norm = normalize_name(r['institute'])
        prog_norm = normalize_name(r['program'])
        key = (inst_norm, prog_norm)
        historic_first_years[key] = r['first_year']
        original_names[key] = (r['institute'], r['program'])
        
    new_courses = []
    active_keys = set()
    
    # Process active courses from the seat matrix
    for r in seat_rows:
        inst_norm = normalize_name(r['institute'])
        prog_norm = normalize_name(r['program'])
        key = (inst_norm, prog_norm)
        active_keys.add(key)
        
        # Determine the introduction year
        first_year = historic_first_years.get(key)
        if first_year is None:
            # Not in historic rankings at all -> starting in 2026 (offered in the current 2026 seat matrix)
            start_year = 2026
        else:
            # Start year is the year it first appeared in rankings
            start_year = int(first_year)
            
        new_courses.append({
            "institute": r['institute'],
            "program": r['program'],
            "quota": r['quota'],
            "seat_pool": r['seat_pool'],
            "seats": {
                "OPEN": r['open'],
                "OPEN_PWD": r['open_pwd'],
                "GEN_EWS": r['gen_ews'],
                "GEN_EWS_PWD": r['gen_ews_pwd'],
                "SC": r['sc'],
                "SC_PWD": r['sc_pwd'],
                "ST": r['st'],
                "ST_PWD": r['st_pwd'],
                "OBC_NCL": r['obc_ncl'],
                "OBC_NCL_PWD": r['obc_ncl_pwd']
            },
            "total": r['total'],
            "program_total": r['program_total'],
            "female_supernumerary": r['female_supernumerary'],
            "institute_state": r['institute_state'],
            "start_year": start_year,
            "is_active": True
        })
        
    # Process discontinued/historic courses that are not in the current seat matrix
    for key, first_year in historic_first_years.items():
        if key not in active_keys:
            inst_orig, prog_orig = original_names[key]
            start_year = int(first_year)
            
            # Since they are discontinued, they are not in the seat matrix and have no quota/seat pool records there.
            # We can classify them as inactive/discontinued and set seats to 0.
            new_courses.append({
                "institute": inst_orig,
                "program": prog_orig,
                "quota": "N/A",
                "seat_pool": "Gender-Neutral", # Default fallback
                "seats": {cat: 0 for cat in ["OPEN", "OPEN_PWD", "GEN_EWS", "GEN_EWS_PWD", "SC", "SC_PWD", "ST", "ST_PWD", "OBC_NCL", "OBC_NCL_PWD"]},
                "total": 0,
                "program_total": 0,
                "female_supernumerary": 0,
                "institute_state": get_institute_state(inst_orig),
                "start_year": start_year,
                "is_active": False
            })
            
    return {"new_courses": new_courses}

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    reload_mode = os.getenv("ENV", "production") == "development"
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=reload_mode)


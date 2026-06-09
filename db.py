import os
import sqlite3
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "josaa_rankings.db")
os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

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

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS josaa_ranks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year TEXT,
        round TEXT,
        seat_type TEXT,
        institute TEXT,
        program TEXT,
        quota TEXT,
        gender TEXT,
        opening_rank INTEGER,
        closing_rank INTEGER,
        opening_rank_str TEXT,
        closing_rank_str TEXT,
        institute_state TEXT
    )
    """)
    # Indices for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_query ON josaa_ranks (year, round, seat_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ranks ON josaa_ranks (closing_rank)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ranks_inst_prog_year ON josaa_ranks (institute, program, year)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ranks_seat_year_round ON josaa_ranks (seat_type, year, round)")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS josaa_seat_matrix (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        institute TEXT,
        program TEXT,
        quota TEXT,
        seat_pool TEXT,
        open INTEGER,
        open_pwd INTEGER,
        gen_ews INTEGER,
        gen_ews_pwd INTEGER,
        sc INTEGER,
        sc_pwd INTEGER,
        st INTEGER,
        st_pwd INTEGER,
        obc_ncl INTEGER,
        obc_ncl_pwd INTEGER,
        total INTEGER,
        program_total INTEGER,
        female_supernumerary INTEGER,
        institute_state TEXT
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_seat_matrix ON josaa_seat_matrix (institute, program)")
    
    conn.commit()
    conn.close()

def insert_seat_matrix(records: list[dict]):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clear existing seat matrix to avoid duplicates
    cursor.execute("DELETE FROM josaa_seat_matrix")
    
    data_to_insert = []
    for r in records:
        inst_name = r.get("institute", "")
        seats = r.get("seats", {})
        data_to_insert.append((
            inst_name,
            r.get("program", ""),
            r.get("quota", ""),
            r.get("seat_pool", ""),
            seats.get("OPEN", 0),
            seats.get("OPEN_PWD", 0),
            seats.get("GEN_EWS", 0),
            seats.get("GEN_EWS_PWD", 0),
            seats.get("SC", 0),
            seats.get("SC_PWD", 0),
            seats.get("ST", 0),
            seats.get("ST_PWD", 0),
            seats.get("OBC_NCL", 0),
            seats.get("OBC_NCL_PWD", 0),
            r.get("total", 0),
            r.get("program_total", 0),
            r.get("female_supernumerary", 0),
            get_institute_state(inst_name)
        ))
        
    cursor.executemany("""
    INSERT INTO josaa_seat_matrix (
        institute, program, quota, seat_pool, 
        open, open_pwd, gen_ews, gen_ews_pwd, 
        sc, sc_pwd, st, st_pwd, obc_ncl, obc_ncl_pwd, 
        total, program_total, female_supernumerary, institute_state
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data_to_insert)
    
    conn.commit()
    conn.close()
    print(f"Stored {len(records)} seat matrix records in DB")

def has_dataset(year: str, round_no: str, seat_type: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM josaa_ranks WHERE year = ? AND round = ? AND seat_type = ?",
        (year, round_no, seat_type)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def insert_ranks(year: str, round_no: str, seat_type: str, ranks: list[dict]):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Avoid duplicate data
    cursor.execute(
        "DELETE FROM josaa_ranks WHERE year = ? AND round = ? AND seat_type = ?",
        (year, round_no, seat_type)
    )
    
    data_to_insert = []
    for r in ranks:
        inst_name = r.get("institute", "")
        data_to_insert.append((
            str(year),
            str(round_no),
            str(seat_type),
            inst_name,
            r.get("program", ""),
            r.get("quota", ""),
            r.get("gender", ""),
            r.get("opening_rank", 999999),
            r.get("closing_rank", 999999),
            r.get("opening_rank_str", ""),
            r.get("closing_rank_str", ""),
            get_institute_state(inst_name)
        ))
        
    cursor.executemany("""
    INSERT INTO josaa_ranks (
        year, round, seat_type, institute, program, quota, gender, 
        opening_rank, closing_rank, opening_rank_str, closing_rank_str, institute_state
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data_to_insert)
    
    conn.commit()
    conn.close()
    print(f"Stored {len(ranks)} ranking records in DB for {year}_r{round_no}_{seat_type}")

def import_existing_json_caches():
    data_dir = os.path.join(BASE_DIR, "data", "josaa_raw")
    if not os.path.exists(data_dir):
        return
        
    import re
    # Match pattern like josaa_2025_r6_OPNO.json
    pattern = re.compile(r"^josaa_(\d{4})_r(\d+)_(.+)\.json$")
    
    for filename in os.listdir(data_dir):
        match = pattern.match(filename)
        if match:
            year, round_no, seat_type = match.groups()
            # Check if database already has this dataset
            if not has_dataset(year, round_no, seat_type):
                file_path = os.path.join(data_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        ranks = json.load(f)
                    insert_ranks(year, round_no, seat_type, ranks)
                    
                    # Split master 'ALL' data into separate database category caches
                    if seat_type == "ALL":
                        mapping = {
                            'OPEN': 'OPNO',
                            'OPEN (PwD)': 'OPPH',
                            'OBC-NCL': 'BCNO',
                            'OBC-NCL (PwD)': 'BCPH',
                            'SC': 'SCNO',
                            'SC (PwD)': 'SCPH',
                            'ST': 'STNO',
                            'ST (PwD)': 'STPH',
                            'EWS': 'EWNO',
                            'EWS (PwD)': 'EWPH'
                        }
                        grouped = {}
                        for r in ranks:
                            actual_st = r.get('seat_type')
                            db_key = mapping.get(actual_st)
                            if db_key:
                                grouped.setdefault(db_key, []).append(r)
                        for db_key, group_records in grouped.items():
                            insert_ranks(year, round_no, db_key, group_records)
                            
                    print(f"Imported cached file {filename} to SQLite.")
                except Exception as e:
                    print(f"Failed to import file {filename}: {e}")

def get_ranks_list(year: str, round_no: str, seat_type: str) -> list[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT institute, program, quota, seat_type, gender, opening_rank, closing_rank, 
               opening_rank_str, closing_rank_str, institute_state 
        FROM josaa_ranks 
        WHERE year = ? AND round = ? AND seat_type = ?
    """, (str(year), str(round_no), str(seat_type)))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

if __name__ == "__main__":
    init_db()
    import_existing_json_caches()

import sys
import os
# Add parent directory to sys.path so 'db' can be imported when running scraper directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests
from bs4 import BeautifulSoup
from db import insert_ranks, has_dataset, get_ranks_list

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "josaa_raw")
os.makedirs(DATA_DIR, exist_ok=True)

URL = "https://josaa.admissions.nic.in/applicant/seatmatrix/openingclosingrankarchieve.aspx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://josaa.admissions.nic.in",
    "Referer": URL,
    "Connection": "keep-alive"
}

def clean_rank(val: str) -> int:
    """Convert rank strings to integers. Returns a very large number or 0 if invalid."""
    val = val.strip()
    if not val:
        return 0
    # Strip any text if there is any, but typically ranks are integers.
    # Some ranks might end with 'P' (preparatory ranks).
    # We will try to extract just digits or return value if not numeric.
    try:
        # Check if it has prep suffix like '123P' or 'Prep'
        digits = "".join([c for c in val if c.isdigit()])
        if digits:
            return int(digits)
    except ValueError:
        pass
    return 999999  # Large fallback for sorting/filtering closing ranks

def get_available_years() -> list[str]:
    """Fetches the JoSAA landing page and returns available years from the select dropdown."""
    try:
        res = requests.get(URL, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            year_select = soup.find('select', {'name': 'ctl00$ContentPlaceHolder1$ddlYear'}) or soup.find('select', id=lambda x: x and 'ddlYear' in x)
            if year_select:
                return [opt.get('value') for opt in year_select.find_all('option') if opt.get('value') and opt.get('value') != "0"]
    except Exception as e:
        print(f"Error fetching available years: {e}")
    return ["2025", "2024", "2023", "2022"]  # Fallback

def get_available_rounds_for_year(year: str) -> list[str]:
    """Simulates selecting a year on the JoSAA page to get its available rounds list."""
    try:
        session = requests.Session()
        res = session.get(URL, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            h = {
                '__VIEWSTATE': soup.find('input', {'name': '__VIEWSTATE'}).get('value') if soup.find('input', {'name': '__VIEWSTATE'}) else "",
                '__VIEWSTATEGENERATOR': soup.find('input', {'name': '__VIEWSTATEGENERATOR'}).get('value') if soup.find('input', {'name': '__VIEWSTATEGENERATOR'}) else "",
                '__EVENTVALIDATION': soup.find('input', {'name': '__EVENTVALIDATION'}).get('value') if soup.find('input', {'name': '__EVENTVALIDATION'}) else "",
                'ctl00$hdnSecKey': soup.find('input', {'name': 'ctl00$hdnSecKey'}).get('value') if soup.find('input', {'name': 'ctl00$hdnSecKey'}) else "",
            }
            data = {
                **h,
                "__EVENTTARGET": 'ctl00$ContentPlaceHolder1$ddlYear',
                "__EVENTARGUMENT": "",
                'ctl00$ContentPlaceHolder1$ddlYear': year
            }
            res2 = session.post(URL, headers=HEADERS, data=data, timeout=10)
            if res2.status_code == 200:
                soup2 = BeautifulSoup(res2.text, 'html.parser')
                round_select = soup2.find('select', {'name': 'ctl00$ContentPlaceHolder1$ddlroundno'}) or soup2.find('select', id=lambda x: x and 'ddlroundno' in x)
                if round_select:
                    return [opt.get('value') for opt in round_select.find_all('option') if opt.get('value') and opt.get('value') != "0"]
    except Exception as e:
        print(f"Error fetching available rounds for year {year}: {e}")
    # Fallback
    return ["1", "2", "3", "4", "5"] if year == "2024" else ["1", "2", "3", "4", "5", "6"]

def scrape_josaa_ranks(year: str = "2025", round_no: str = "6", seat_type: str = "OPNO") -> list[dict]:
    """
    Simulates the sequence of POST requests (postbacks) on the JoSAA archive page
    to fetch the ranking table for the specified parameters.
    """
    session = requests.Session()
    
    print(f"Scraping JoSAA rankings for Year: {year}, Round: {round_no}, Seat Type: {seat_type}...")
    
    # Step 1: Initial GET
    res = session.get(URL, headers=HEADERS, timeout=20)
    if res.status_code != 200:
        raise Exception(f"Failed to load JoSAA archive page (Status Code: {res.status_code})")
        
    soup = BeautifulSoup(res.text, 'html.parser')
    
    def get_hidden_fields(s):
        return {
            '__VIEWSTATE': s.find('input', {'name': '__VIEWSTATE'}).get('value') if s.find('input', {'name': '__VIEWSTATE'}) else "",
            '__VIEWSTATEGENERATOR': s.find('input', {'name': '__VIEWSTATEGENERATOR'}).get('value') if s.find('input', {'name': '__VIEWSTATEGENERATOR'}) else "",
            '__EVENTVALIDATION': s.find('input', {'name': '__EVENTVALIDATION'}).get('value') if s.find('input', {'name': '__EVENTVALIDATION'}) else "",
            'ctl00$hdnSecKey': s.find('input', {'name': 'ctl00$hdnSecKey'}).get('value') if s.find('input', {'name': 'ctl00$hdnSecKey'}) else "",
        }
        
    def post_step(event_target, current_selections, extra_data=None):
        h = get_hidden_fields(soup)
        data = {
            **h,
            "__EVENTTARGET": event_target,
            "__EVENTARGUMENT": "",
            **current_selections
        }
        if extra_data:
            data.update(extra_data)
        r = session.post(URL, headers=HEADERS, data=data, timeout=20)
        if r.status_code != 200:
            raise Exception(f"Failed in postback step '{event_target}' (Status: {r.status_code})")
        return r, BeautifulSoup(r.text, 'html.parser')

    # Step 2: Select Year
    res, soup = post_step('ctl00$ContentPlaceHolder1$ddlYear', {
        'ctl00$ContentPlaceHolder1$ddlYear': year
    })
    
    # Step 3: Select Round No
    res, soup = post_step('ctl00$ContentPlaceHolder1$ddlroundno', {
        'ctl00$ContentPlaceHolder1$ddlYear': year,
        'ctl00$ContentPlaceHolder1$ddlroundno': round_no
    })
    
    # Step 4: Select Instype = ALL
    res, soup = post_step('ctl00$ContentPlaceHolder1$ddlInstype', {
        'ctl00$ContentPlaceHolder1$ddlYear': year,
        'ctl00$ContentPlaceHolder1$ddlroundno': round_no,
        'ctl00$ContentPlaceHolder1$ddlInstype': 'ALL'
    })
    
    # Step 5: Select Institute = ALL
    res, soup = post_step('ctl00$ContentPlaceHolder1$ddlInstitute', {
        'ctl00$ContentPlaceHolder1$ddlYear': year,
        'ctl00$ContentPlaceHolder1$ddlroundno': round_no,
        'ctl00$ContentPlaceHolder1$ddlInstype': 'ALL',
        'ctl00$ContentPlaceHolder1$ddlInstitute': 'ALL'
    })
    
    # Step 6: Select Branch = ALL
    res, soup = post_step('ctl00$ContentPlaceHolder1$ddlBranch', {
        'ctl00$ContentPlaceHolder1$ddlYear': year,
        'ctl00$ContentPlaceHolder1$ddlroundno': round_no,
        'ctl00$ContentPlaceHolder1$ddlInstype': 'ALL',
        'ctl00$ContentPlaceHolder1$ddlInstitute': 'ALL',
        'ctl00$ContentPlaceHolder1$ddlBranch': 'ALL'
    })
    
    # Step 7: Select Seat Type and Submit
    res, soup = post_step('', {
        'ctl00$ContentPlaceHolder1$ddlYear': year,
        'ctl00$ContentPlaceHolder1$ddlroundno': round_no,
        'ctl00$ContentPlaceHolder1$ddlInstype': 'ALL',
        'ctl00$ContentPlaceHolder1$ddlInstitute': 'ALL',
        'ctl00$ContentPlaceHolder1$ddlBranch': 'ALL',
        'ctl00$ContentPlaceHolder1$ddlSeatType': seat_type
    }, extra_data={'ctl00$ContentPlaceHolder1$btnSubmit': 'Submit'})
    
    table = soup.find('table')
    if not table:
        # Check if we got the standard error page
        if "Something Went Wrong" in res.text or soup.title and "Error Message" in soup.title.text:
            raise Exception("Official JoSAA website returned an internal server error. Please try again.")
        raise Exception("Ranks table not found in the final response.")
        
    rows = table.find_all('tr')
    if not rows:
        raise Exception("Ranks table is empty.")
        
    # Header check
    header_cols = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
    expected_headers = ['Institute', 'Academic Program Name', 'Quota', 'Seat Type', 'Gender', 'Opening Rank', 'Closing Rank']
    
    # In some tables headers might slightly differ, let's map them dynamically
    headers_map = {}
    for i, col in enumerate(header_cols):
        col_lower = col.lower()
        if 'institute' in col_lower:
            headers_map['institute'] = i
        elif 'program' in col_lower:
            headers_map['program'] = i
        elif 'quota' in col_lower:
            headers_map['quota'] = i
        elif 'seat' in col_lower:
            headers_map['seat_type'] = i
        elif 'gender' in col_lower:
            headers_map['gender'] = i
        elif 'opening' in col_lower:
            headers_map['opening_rank'] = i
        elif 'closing' in col_lower:
            headers_map['closing_rank'] = i
            
    # Default fallback mapping if headers don't match perfectly
    if len(headers_map) < 7:
        headers_map = {
            'institute': 0,
            'program': 1,
            'quota': 2,
            'seat_type': 3,
            'gender': 4,
            'opening_rank': 5,
            'closing_rank': 6
        }
        
    results = []
    for row in rows[1:]:
        cols = row.find_all(['td', 'th'])
        if len(cols) < max(headers_map.values()) + 1:
            continue
            
        inst = cols[headers_map['institute']].get_text(strip=True)
        # Skip empty lines, duplicate headers, or spacer rows
        if not inst or inst.lower() == 'institute' or inst.startswith('---'):
            continue
            
        prog = cols[headers_map['program']].get_text(strip=True)
        quota = cols[headers_map['quota']].get_text(strip=True)
        st = cols[headers_map['seat_type']].get_text(strip=True)
        gender = cols[headers_map['gender']].get_text(strip=True)
        
        open_rank_str = cols[headers_map['opening_rank']].get_text(strip=True)
        close_rank_str = cols[headers_map['closing_rank']].get_text(strip=True)
        
        results.append({
            "institute": inst,
            "program": prog,
            "quota": quota,
            "seat_type": st,
            "gender": gender,
            "opening_rank_str": open_rank_str,
            "closing_rank_str": close_rank_str,
            "opening_rank": clean_rank(open_rank_str),
            "closing_rank": clean_rank(close_rank_str)
        })
        
    # Cache the result to DB
    try:
        if seat_type == 'ALL':
            # Insert the 'ALL' dataset
            insert_ranks(year, round_no, 'ALL', results)
            
            # Map actual seat types to database keys
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
            
            # Group records
            grouped = {}
            for r in results:
                actual_st = r.get('seat_type')
                db_key = mapping.get(actual_st)
                if db_key:
                    grouped.setdefault(db_key, []).append(r)
            
            # Insert each group separately under its respective key
            for db_key, group_records in grouped.items():
                insert_ranks(year, round_no, db_key, group_records)
        else:
            insert_ranks(year, round_no, seat_type, results)
    except Exception as e:
        print(f"Failed to insert scraped ranks into DB: {e}")
        
    # Also write local JSON backup
    try:
        cache_file = os.path.join(DATA_DIR, f"josaa_{year}_r{round_no}_{seat_type}.json")
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
    except Exception as e:
        print(f"Failed to write local JSON backup: {e}")
        
    return results

def get_cached_ranks(year: str = "2025", round_no: str = "6", seat_type: str = "OPNO") -> list[dict]:
    """Loads ranks from local SQLite DB if exists, otherwise triggers scrape."""
    if has_dataset(year, round_no, seat_type):
        try:
            return get_ranks_list(year, round_no, seat_type)
        except Exception as e:
            print(f"Error reading ranks from DB: {e}")
            
    # Scrape if not cached
    return scrape_josaa_ranks(year, round_no, seat_type)

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests
from bs4 import BeautifulSoup
from db import init_db, insert_seat_matrix

URL = "https://josaa.admissions.nic.in/applicant/seatmatrix/seatmatrixinfo.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://josaa.admissions.nic.in",
    "Referer": URL,
    "Connection": "keep-alive"
}

def get_hidden_fields(s):
    return {
        '__VIEWSTATE': s.find('input', {'name': '__VIEWSTATE'}).get('value') if s.find('input', {'name': '__VIEWSTATE'}) else "",
        '__VIEWSTATEGENERATOR': s.find('input', {'name': '__VIEWSTATEGENERATOR'}).get('value') if s.find('input', {'name': '__VIEWSTATEGENERATOR'}) else "",
        '__EVENTVALIDATION': s.find('input', {'name': '__EVENTVALIDATION'}).get('value') if s.find('input', {'name': '__EVENTVALIDATION'}) else "",
        'ctl00$hdnSecKey': s.find('input', {'name': 'ctl00$hdnSecKey'}).get('value') if s.find('input', {'name': 'ctl00$hdnSecKey'}) else "",
    }

def scrape_seat_matrix():
    print("Initializing DB...")
    init_db()

    print("Requesting initial page...")
    session = requests.Session()
    r = session.get(URL, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        raise Exception(f"Failed to load JoSAA seat matrix page: {r.status_code}")
    soup = BeautifulSoup(r.text, 'html.parser')

    print("Selecting InstType: ALL...")
    h = get_hidden_fields(soup)
    data = {
        **h,
        "__EVENTTARGET": "ctl00$ContentPlaceHolder1$ddlInstType",
        "__EVENTARGUMENT": "",
        "ctl00$ContentPlaceHolder1$ddlInstType": "0"
    }
    r2 = session.post(URL, headers=HEADERS, data=data, timeout=20)
    if r2.status_code != 200:
        raise Exception("Failed in postback for selecting Institute Type")
    soup2 = BeautifulSoup(r2.text, 'html.parser')

    print("Selecting Institute: ALL...")
    h2 = get_hidden_fields(soup2)
    data2 = {
        **h2,
        "__EVENTTARGET": "ctl00$ContentPlaceHolder1$ddlInstitute",
        "__EVENTARGUMENT": "",
        "ctl00$ContentPlaceHolder1$ddlInstType": "0",
        "ctl00$ContentPlaceHolder1$ddlInstitute": "0"
    }
    r3 = session.post(URL, headers=HEADERS, data=data2, timeout=20)
    if r3.status_code != 200:
        raise Exception("Failed in postback for selecting Institute")
    soup3 = BeautifulSoup(r3.text, 'html.parser')

    print("Submitting request for seat matrix data...")
    h3 = get_hidden_fields(soup3)
    data3 = {
        **h3,
        "ctl00$ContentPlaceHolder1$ddlInstType": "0",
        "ctl00$ContentPlaceHolder1$ddlInstitute": "0",
        "ctl00$ContentPlaceHolder1$ddlBranch": "0",
        "ctl00$ContentPlaceHolder1$btnSubmit": "Submit"
    }
    r4 = session.post(URL, headers=HEADERS, data=data3, timeout=20)
    if r4.status_code != 200:
        raise Exception("Failed in submit postback")
    soup4 = BeautifulSoup(r4.text, 'html.parser')

    table = soup4.find('table')
    if not table:
        raise Exception("No seat matrix table found in final response")

    tbody = table.find('tbody')
    target = tbody if tbody else table
    outer_rows = target.find_all('tr', recursive=False)
    print(f"Found {len(outer_rows)} rows in table including headers.")

    records = []
    current_inst = ""
    current_prog = ""
    current_quota = ""

    categories = ['OPEN', 'OPEN_PWD', 'GEN_EWS', 'GEN_EWS_PWD', 'SC', 'SC_PWD', 'ST', 'ST_PWD', 'OBC_NCL', 'OBC_NCL_PWD']

    for tr in outer_rows[1:]:
        tds = tr.find_all('td', recursive=False)
        if not tds:
            continue
        
        # Gender-Neutral Row: length >= 15
        if len(tds) >= 15:
            current_inst = tds[0].text.strip().replace('\n', ' ')
            current_prog = tds[1].text.strip().replace('\n', ' ')
            current_quota = tds[2].text.strip().replace('\n', ' ')
            
            seat_pool = tds[3].text.strip()
            
            cat_seats = {}
            for c_idx, cat in enumerate(categories):
                cat_seats[cat] = int(tds[4 + c_idx].text.strip() or 0)
                
            total_seats = int(tds[14].text.strip() or 0)
            
            prog_total_span = tds[15].find('span', {'id': 'lblProgramTotal'})
            female_seats_span = tds[15].find('span', {'id': 'lblFemaleSeats'})
            
            program_total = int(prog_total_span.text.strip() if prog_total_span else 0)
            female_supernumerary = int(female_seats_span.text.strip() if female_seats_span else 0)
            
            records.append({
                "institute": current_inst,
                "program": current_prog,
                "quota": current_quota,
                "seat_pool": seat_pool,
                "seats": cat_seats,
                "total": total_seats,
                "program_total": program_total,
                "female_supernumerary": female_supernumerary
            })
            
        # Female-only Row: length >= 11
        elif len(tds) >= 11:
            seat_pool = tds[0].text.strip()
            
            cat_seats = {}
            for c_idx, cat in enumerate(categories):
                cat_seats[cat] = int(tds[1 + c_idx].text.strip() or 0)
                
            total_text = tds[11].text.strip()
            total_seats = int(total_text.split()[0] if total_text else 0)
            
            records.append({
                "institute": current_inst,
                "program": current_prog,
                "quota": current_quota,
                "seat_pool": seat_pool,
                "seats": cat_seats,
                "total": total_seats,
                "program_total": records[-1]["program_total"] if records else 0,
                "female_supernumerary": records[-1]["female_supernumerary"] if records else 0
            })

    print(f"Parsed {len(records)} seat matrix records successfully.")
    
    # Save JSON backup
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "josaa_raw")
    os.makedirs(data_dir, exist_ok=True)
    json_path = os.path.join(data_dir, "josaa_seat_matrix.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"Saved JSON backup to {json_path}")
    
    # Save to SQLite DB
    insert_seat_matrix(records)
    print("Scraping and download completed successfully!")

if __name__ == "__main__":
    scrape_seat_matrix()

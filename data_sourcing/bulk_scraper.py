import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import random
from db import init_db, has_dataset
from data_sourcing.scraper import scrape_josaa_ranks, get_available_years, get_available_rounds_for_year

# Parameters to scrape
SEAT_TYPES = ["ALL"]

def run_bulk_scrape():
    init_db()

    print("Fetching active years from JoSAA portal...")
    discovered_years = get_available_years()
    print(f"Discovered Years: {discovered_years}")

    print("Starting Bulk Scraper for past JoSAA Ranking Data...")
    print(f"Targeting discovered years and their respective available rounds.")

    success_count = 0
    skip_count = 0
    error_count = 0

    for year in discovered_years:
        rounds_for_year = get_available_rounds_for_year(year)
        print(f"Discovered Rounds for Year {year}: {rounds_for_year}")

        for round_no in rounds_for_year:

            for seat_type in SEAT_TYPES:
                # Check if database already has this combination
                if has_dataset(year, round_no, seat_type):
                    print(f"[SKIP] Data already exists for {year} Round {round_no} Category {seat_type}")
                    skip_count += 1
                    continue

                print(f"[FETCH] Scraping {year} Round {round_no} Category {seat_type}...")
                retries = 3
                for attempt in range(1, retries + 1):
                    try:
                        # Fetch and insert
                        ranks = scrape_josaa_ranks(year, round_no, seat_type)
                        print(f"[SUCCESS] Scraped {len(ranks)} records for {year} Round {round_no} Category {seat_type}")
                        success_count += 1

                        # Friendly sleep to avoid rate-limiting
                        sleep_time = random.uniform(3.0, 6.0)
                        print(f"Sleeping for {sleep_time:.2f}s...")
                        time.sleep(sleep_time)
                        break
                    except Exception as e:
                        print(f"[ERROR] Attempt {attempt}/{retries} failed for {year} Round {round_no} Category {seat_type}: {e}")
                        if attempt == retries:
                            error_count += 1
                        time.sleep(5)  # Wait longer on error

    print("\n==================================================")
    print("Bulk Scrape Complete Summary:")
    print(f"  Successfully Scraped: {success_count}")
    print(f"  Skipped (Already Cached): {skip_count}")
    print(f"  Errors: {error_count}")
    print("==================================================")

if __name__ == "__main__":
    run_bulk_scrape()

#!/usr/bin/env python3
"""
Premier Inn Hotel Parser
========================
Parses the saved hotels.html directory page.

Each hotel is in this structure:
    <li class="pi-hotel-directory__hotel ...">
        <a class="pi-hotel-directory__hotel-name ...">Hotel Name</a>
        <span class="pi-hotel-directory__hotel-address ...">Address, Town POSTCODE</span>
    </li>

Usage:
    python3 parse_premier_inn.py

Input:  PremierInnHotels.html  (in the same folder)
Output: premier_inn_hotels.csv
        premier_inn_hotels.json
"""

import json
import csv
from datetime import date

from services.models import Room, RoomType
from services.premier_inn_service import PremierInnService

OUTPUT_CSV  = "output/premier_inn_search.csv"
OUTPUT_JSON = "output/premier_inn_search.json"


def save_csv(hotels: list[dict], path: str):
    fields = ["hotel_id", "name", "county", "available", "price", "currency",
              "distance_mi", "rooms_left"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(hotels)
    print(f"✓ CSV  saved → {path}  ({len(hotels)} rows)")


def save_json(hotels: list[dict], path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(hotels, f, indent=2, ensure_ascii=False)
    print(f"✓ JSON saved → {path}  ({len(hotels)} records)")


def preview(hotels: list[dict], n: int = 20):
    print(f"\n{'─'*80}")
    print(f"{'NAME':<45} {'POSTCODE':<12} ADDRESS")
    print(f"{'─'*80}")
    for h in hotels[:n]:
        print(f"{h['name'][:44]:<45} {h['postcode']:<12} {h['address'][:35]}")
    if len(hotels) > n:
        print(f"  … and {len(hotels) - n} more")
    print(f"{'─'*80}")


if __name__ == "__main__":
    service = PremierInnService()
    print(f"Fetching hotels with their counties")
    countries = service.get_hotels()
    print(f"Found hotels in {len(countries)} hotels.\n")

    room = Room()
    room.adults = 2
    room.children = 2
    room.room_type = RoomType.FAMILY
    room.cot = 0

    start_date = date(2026, 5, 3)
    total_hotels = list()
    target_country = "England"

    for country in countries:
        if country.name == target_country:
            for county in country.counties:
                print(f"Fetching prices for hotels in {county.name} county")
                county_hotels = service.search(county.name, start_date, [ room ])
                for county_hotel in county_hotels:
                    county_hotel["county"] = county.name
                    total_hotels.append(county_hotel)

    print(f"Found {len(total_hotels)} total hotels")

    save_csv(total_hotels,  OUTPUT_CSV)
    save_json(total_hotels, OUTPUT_JSON)
    # preview(hotels)
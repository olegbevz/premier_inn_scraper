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

from services.premier_inn_service import PremierInnService, Room, RoomType

OUTPUT_CSV    = "premier_inn_hotels.csv"
OUTPUT_JSON   = "premier_inn_hotels.json"



def save_csv(hotels: list[dict], path: str):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "address", "postcode"])
        writer.writeheader()
        writer.writerows(hotels)
    print(f"✓ CSV  → {path}  ({len(hotels)} rows)")


def save_json(hotels: list[dict], path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(hotels, f, indent=2, ensure_ascii=False)
    print(f"✓ JSON → {path}  ({len(hotels)} records)")


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
    hotels = service.get_hotels()
    print(f"Found {len(hotels)} hotels.\n")

    location = hotels[0]["address"]
    room = Room()
    room.adults = 2
    room.children = 2
    room.room_type = RoomType.FAMILY
    room.cot = 0

    hotels = service.search(location, date(2026, 5, 3), [ room ])


    save_csv(hotels,  OUTPUT_CSV)
    save_json(hotels, OUTPUT_JSON)
    preview(hotels)
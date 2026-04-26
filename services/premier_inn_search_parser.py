import json
import csv
import re
import sys

class PremierInnSearchParser:
    # !/usr/bin/env python3
    """
    Premier Inn Search Results Parser
    ==================================
    Parses the Premier Inn search page HTML and extracts from the embedded
    __NEXT_DATA__ JSON:
      - Hotel name
      - Hotel ID  (e.g. "BEDPRI")
      - Lowest room price  (GBP)
      - Currency
      - Available  (True/False)
      - Distance from search (miles)

    Usage:
        python3 parse_premier_inn_search.py

    Input:   premier_inn_search.html   (same folder)
    Output:  premier_inn_search.csv
             premier_inn_search.json
    """



    def extract_next_data(self, html: str) -> dict:
        """Pull the JSON payload from the <script id="__NEXT_DATA__"> tag."""
        match = re.search(
            r'<script\s+id=["\']__NEXT_DATA__["\'][^>]*>\s*(\{.*?\})\s*</script>',
            html,
            re.DOTALL,
        )
        if not match:
            raise ValueError("Could not find __NEXT_DATA__ script tag in HTML")
        return json.loads(match.group(1))

    def parse_hotels(self, next_data: dict) -> list[dict]:
        """
        Navigate the dehydrated React-Query state to find hotelAvailabilitiesV2.
        Path:
          props.pageProps.dehydratedState.queries[]
            -> queryKey[0] == "hotelAvailabilitiesV2"
            -> state.data.hotelAvailabilitiesV2.multiHotelAvailabilities[]
        """
        queries = (
            next_data
            .get("props", {})
            .get("pageProps", {})
            .get("dehydratedState", {})
            .get("queries", [])
        )

        # Find the availability query
        availability_query = next(
            (q for q in queries
             if q.get("queryKey", [None])[0] == "hotelAvailabilitiesV2"),
            None,
        )

        if not availability_query:
            raise ValueError(
                "Could not find 'hotelAvailabilitiesV2' query in __NEXT_DATA__"
            )

        multi = (
            availability_query
            .get("state", {})
            .get("data", {})
            .get("hotelAvailabilitiesV2", {})
            .get("multiHotelAvailabilities", [])
        )

        hotels = []
        for entry in multi:
            avail = entry.get("hotelAvailability", {})
            rate = avail.get("lowestRoomRate") or {}

            price = rate.get("netTotal")  # None if sold out
            currency = rate.get("currencyCode", "GBP")

            hotels.append({
                "hotel_id": entry.get("hotelId", ""),
                "name": entry.get("name", ""),
                "available": avail.get("available", False),
                "price": price,
                "currency": currency,
                "distance_mi": avail.get("distance"),
                "rooms_left": avail.get("numberOfRoomsAvailable"),
            })

        # Sort: available first, then by price, then by distance
        hotels.sort(key=lambda h: (
            not h["available"],
            h["price"] if h["price"] is not None else float("inf"),
            h["distance_mi"] if h["distance_mi"] is not None else float("inf"),
        ))
        return hotels

    def save_csv(self, hotels: list[dict], path: str):
        fields = ["hotel_id", "name", "available", "price", "currency",
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
        print(f"\n{'─' * 75}")
        print(f"{'ID':<8} {'PRICE':>7}  {'AVAIL':<6} {'DIST':>6}  NAME")
        print(f"{'─' * 75}")
        for h in hotels[:n]:
            price = f"£{h['price']:.0f}" if h["price"] is not None else "N/A"
            avail = "✓" if h["available"] else "✗"
            dist = f"{h['distance_mi']:.1f}mi" if h["distance_mi"] is not None else "?"
            print(f"{h['hotel_id']:<8} {price:>7}  {avail:<6} {dist:>6}  {h['name']}")
        if len(hotels) > n:
            print(f"  … and {len(hotels) - n} more")
        print(f"{'─' * 75}")

        available = [h for h in hotels if h["available"]]
        if available:
            cheapest = available[0]
            print(f"\n🏆 Cheapest available: {cheapest['name']}  "
                  f"(£{cheapest['price']:.0f}, {cheapest['distance_mi']:.1f} miles, "
                  f"ID: {cheapest['hotel_id']})")

    def parse_search(self, html: str) -> list[dict]:
        next_data = self.extract_next_data(html)
        return self.parse_hotels(next_data)

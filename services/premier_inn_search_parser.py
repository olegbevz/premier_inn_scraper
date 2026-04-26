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

    def parse_search(self, html: str) -> list[dict]:
        next_data = self.extract_next_data(html)
        return self.parse_hotels(next_data)

import re
import urllib.error
import urllib.request
from enum import Enum
from datetime import date
from urllib.parse import urlencode, quote

from services.premier_inn_hotels_parser import PremierInnHotelsParser
from services.premier_inn_search_parser import PremierInnSearchParser

FETCH_HOTELS_URL = "https://www.premierinn.com/gb/en/hotels.html"
SEARCH_URL = "https://www.premierinn.com/gb/en/search.html"
BASE_URL = "https://www.premierinn.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}


class RoomType(str, Enum):
    FAMILY = "FAM"  # Family room (up to 2 adults + 2 children)
    DOUBLE = "DB"  # Double / kingsize
    TWIN = "TWIN"  # Twin
    SINGLE = "SB"  # Single
    ACCESSIBLE = "DIS"  # Accessible room


class SortOrder(int, Enum):
    RECOMMENDED = 1
    PRICE = 2
    DISTANCE = 3

class ViewMode(int, Enum):
    LIST = 1
    MAP = 2


class BookingChannel(str, Enum):
    WEB = "WEB"
    APP = "APP"

class Room:
    adults: int = 2
    children: int = 0
    room_type: RoomType = RoomType.FAMILY
    cot: int = 0  # 0 or 1

    def __post_init__(self):
        if self.adults < 1 or self.adults > 2:
            raise ValueError(f"adults must be 1 or 2, got {self.adults}")
        if self.children < 0 or self.children > 2:
            raise ValueError(f"children must be 0–2, got {self.children}")
        if self.cot not in (0, 1):
            raise ValueError(f"cot must be 0 or 1, got {self.cot}")

class PremierInnService:
    def get_hotels(self) -> list[dict]:
        print(f"Fetching hotel directory: {FETCH_HOTELS_URL}")
        html = self.fetch_html(FETCH_HOTELS_URL)
        if not html:
            print("Failed to fetch the directory page.")
            return []

        parser = PremierInnHotelsParser()
        parser.feed(html)
        return parser.hotels

    def search(self,
        location:  str,
        arrival:   date,
        rooms: list[Room],
        nights:    int      = 1,
        sort:      SortOrder = SortOrder.PRICE,
        view:      ViewMode  = ViewMode.LIST,
        channel:   BookingChannel = BookingChannel.WEB) -> list[dict]:

        params: dict[str, str | int] = {}
        params["searchModel.searchTerm"] = location
        # if place_id:
        #     params["PLACEID"] = place_id
        params["ARRmm"] = arrival.month
        params["ARRdd"] = arrival.day
        params["ARRyyyy"] = arrival.year
        params["NIGHTS"] = nights
        params["ROOMS"] = len(rooms)

        # ── Per-room occupancy ────────────────────────────────────────────────
        for i, room in enumerate(rooms, start=1):
            params[f"ADULT{i}"] = room.adults
            params[f"CHILD{i}"] = room.children
            params[f"COT{i}"] = room.cot
            params[f"INTTYP{i}"] = room.room_type.value

        # ── Display options ───────────────────────────────────────────────────
        params["BOOKINGCHANNEL"] = channel.value
        params["SORT"] = sort.value
        params["VIEW"] = view.value

        query_string = urlencode(params, quote_via=quote)
        query_string = f"{SEARCH_URL}?{query_string}"

        html = self.fetch_html(query_string)
        if not html:
            print("Failed to fetch the directory page.")
            return []

        parser = PremierInnSearchParser()
        return parser.parse_search(html)

    def build_search_url(self) -> str:
        """Construct the full Premier Inn search URL."""
        params: dict[str, str | int] = {}

        # ── Location ──────────────────────────────────────────────────────────
        # searchModel.searchTerm needs to stay un-encoded (Premier Inn uses +)
        # We'll handle it manually via urlencode's quote_via
        params["searchModel.searchTerm"] = self.location

        if self.place_id:
            params["PLACEID"] = self.place_id

        # ── Dates ─────────────────────────────────────────────────────────────
        params["ARRmm"] = self.arrival.month
        params["ARRdd"] = self.arrival.day
        params["ARRyyyy"] = self.arrival.year
        params["NIGHTS"] = self.nights
        params["ROOMS"] = len(self.rooms)

        # ── Per-room occupancy ────────────────────────────────────────────────
        for i, room in enumerate(self.rooms, start=1):
            params[f"ADULT{i}"] = room.adults
            params[f"CHILD{i}"] = room.children
            params[f"COT{i}"] = room.cot
            params[f"INTTYP{i}"] = room.resolved_room_type.value

        # ── Display options ───────────────────────────────────────────────────
        params["BOOKINGCHANNEL"] = self.channel.value
        params["SORT"] = self.sort.value
        params["VIEW"] = self.view.value

        query_string = urlencode(params, quote_via=quote)
        return f"{self.BASE_URL}?{query_string}"

    def fetch_html(self, url: str) -> str | None:
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                # Detect encoding from headers, default to utf-8
                content_type = resp.headers.get("Content-Type", "")
                enc_match = re.search(r'charset=([\w-]+)', content_type)
                encoding = enc_match.group(1) if enc_match else "utf-8"
                return raw.decode(encoding, errors="replace")
        except urllib.error.HTTPError as e:
            print(f"  ✗ HTTP {e.code}: {url}")
        except Exception as e:
            print(f"  ✗ Error fetching {url}: {e}")
        return None

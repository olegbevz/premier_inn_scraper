from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import date

@dataclass
class Hotel:
    name: str
    location: str  # full address without postcode
    postcode: str
    url: str = ""


@dataclass
class City:
    name: str
    hotels: list[Hotel] = field(default_factory=list)


@dataclass
class County:
    name: str
    cities: list[City] = field(default_factory=list)


@dataclass
class Country:
    name: str
    counties: list[County] = field(default_factory=list)

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

@dataclass
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
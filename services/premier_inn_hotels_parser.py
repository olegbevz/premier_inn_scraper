import re
from html.parser import HTMLParser
from bs4 import BeautifulSoup
from services.models import Country, County, City, Hotel

# Postcode patterns: UK, German (5-digit), Channel Islands
POSTCODE_RE = re.compile(
    r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}|\d{5})\s*$',
    re.IGNORECASE
)


class PremierInnHotelsParser(HTMLParser):

    def split_address(self, raw: str) -> tuple[str, str]:
        """Split 'Fletcher Road, Kempston, Bedford MK42 7FY' → (address, postcode)."""
        raw = re.sub(r'\s+', ' ', raw).strip()
        m = POSTCODE_RE.search(raw)
        if m:
            postcode = m.group(1).upper()
            # Normalise UK spacing: "MK429DJ" → "MK42 9DJ"
            postcode = re.sub(r'^([A-Z]{1,2}\d{1,2}[A-Z]?)\s*(\d[A-Z]{2})$',
                              r'\1 \2', postcode)
            location = raw[:m.start()].strip().rstrip(',').strip()
        else:
            postcode = ""
            location = raw
        return location, postcode

    def clean_name(self, text: str) -> str:
        """Collapse multiple spaces and extra whitespace from hotel names."""
        return re.sub(r'\s+', ' ', text).strip()

    def parse_city_name(self, text: str) -> str:
        """'Hotels In Bedford' → 'Bedford'"""
        return re.sub(r'^hotels\s+in\s+', '', text, flags=re.IGNORECASE).strip()

    def parse(self, html: str) -> list[Country]:
        bs = BeautifulSoup(html, "html.parser");

        countries: list[Country] = []


        # Each <aside class="pi-hotel-directory ..."> is one country block
        for aside in bs.find_all("aside", class_="pi-hotel-directory"):

            # ── Country ──────────────────────────────────────────────────────────
            country_tag = aside.find("a", class_="pi-hotel-directory__country")
            country_name = self.clean_name(country_tag.get_text()) if country_tag else "Unknown"
            country = Country(name=country_name)

            # ── County ───────────────────────────────────────────────────────────
            # Counties are grouped inside <div class="pi-hotel-directory__county">
            # but the h3 + h4 + ul siblings are flat within that div, so we walk
            # direct children to track the current county/city context.
            county_div = aside.find("div", class_="pi-hotel-directory__county")
            if not county_div:
                countries.append(country)
                continue

            current_county: County | None = None
            current_city: City | None = None

            for el in county_div.children:
                if not hasattr(el, 'name') or el.name is None:
                    continue  # skip NavigableString whitespace nodes

                # ── h3 = county heading ───────────────────────────────────────────
                if el.name == "h3":
                    county_tag = el.find("a", class_="pi-hotel-directory__county-title")
                    county_name = self.clean_name(county_tag.get_text()) if county_tag else self.clean_name(el.get_text())
                    county_name = county_name.title()  # "BEDFORDSHIRE" → "Bedfordshire"
                    current_county = County(name=county_name)
                    country.counties.append(current_county)
                    current_city = None

                # ── h4 = city/town heading ────────────────────────────────────────
                elif el.name == "h4" and "pi-hotel-directory__town" in el.get("class", []):
                    city_name = self.parse_city_name(self.clean_name(el.get_text()))
                    current_city = City(name=city_name)
                    if current_county is None:
                        current_county = County(name="Unknown")
                        country.counties.append(current_county)
                    current_county.cities.append(current_city)

                # ── ul = hotel list for the current city ──────────────────────────
                elif el.name == "ul" and "pi-hotel-directory__town-collection" in el.get("class", []):
                    if current_city is None:
                        continue
                    for li in el.find_all("li", class_="pi-hotel-directory__hotel"):
                        name_tag = li.find("a", class_="pi-hotel-directory__hotel-name")
                        addr_tag = li.find("span", class_="pi-hotel-directory__hotel-address")

                        name = self.clean_name(name_tag.get_text()) if name_tag else ""
                        raw_addr = self.clean_name(addr_tag.get_text()) if addr_tag else ""
                        location, postcode = self.split_address(raw_addr)
                        url = name_tag.get("href", "") if name_tag else ""

                        if name:
                            current_city.hotels.append(
                                Hotel(name=name, location=location,
                                      postcode=postcode, url=url)
                            )

            countries.append(country)

        return countries

    def __init__(self):
        super().__init__()
        self.hotels: list[dict] = []

        # State flags
        self._in_name    = False
        self._in_address = False
        self._cur_name   = ""
        self._cur_addr   = ""

    def handle_starttag(self, tag, attrs):
        classes = dict(attrs).get("class", "")

        if "pi-hotel-directory__hotel-name" in classes:
            self._in_name  = True
            self._cur_name = ""

        elif "pi-hotel-directory__hotel-address" in classes:
            self._in_address = True
            self._cur_addr   = ""

    def handle_data(self, data):
        if self._in_name:
            self._cur_name += data
        elif self._in_address:
            self._cur_addr += data

    def handle_endtag(self, tag):
        if self._in_name and tag == "a":
            self._in_name = False

        elif self._in_address and tag == "span":
            self._in_address = False
            self._flush()

    def _flush(self):
        name = re.sub(r'\s+', ' ', self._cur_name).strip()
        full = re.sub(r'\s+', ' ', self._cur_addr).strip()

        # Split postcode from the rest of the address
        pc_match = POSTCODE_RE.search(full)
        if pc_match:
            postcode = pc_match.group(1).upper()
            # Normalise UK postcode spacing: "RG121AA" → "RG12 1AA"
            postcode = re.sub(r'^([A-Z]{1,2}\d{1,2}[A-Z]?)\s*(\d[A-Z]{2})$',
                              r'\1 \2', postcode)
            address = full[:pc_match.start()].strip().rstrip(',').strip()
        else:
            postcode = ""
            address  = full

        if name:
            self.hotels.append({
                "name":     name,
                "address":  address,
                "postcode": postcode,
            })

        self._cur_name = ""
        self._cur_addr = ""

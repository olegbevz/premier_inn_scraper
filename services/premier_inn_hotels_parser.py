import re
from html.parser import HTMLParser

# Postcode patterns: UK, German (5-digit), Channel Islands
POSTCODE_RE = re.compile(
    r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}|\d{5})\s*$',
    re.IGNORECASE
)


class PremierInnHotelsParser(HTMLParser):

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

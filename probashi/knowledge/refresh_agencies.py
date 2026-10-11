"""Rebuild data/agencies.csv from the official BMET recruiting-agent register.

The register (RAIMS, "Recruiting Agents' Information System") publishes the whole
licence table in one HTML page. This script copies it into a CSV without changing
any value: nothing is guessed, and a page that does not look like the register is
rejected rather than half-imported.

    python -m probashi.knowledge.refresh_agencies              # fetch and rewrite the CSV
    python -m probashi.knowledge.refresh_agencies --html saved.html

Phone numbers are deliberately not copied: the engine does not need them.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import urllib.request
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path

REGISTER_URL = "https://raims.oep.gov.bd/agencies"
FIELDS = ["licence_no", "name", "status", "valid_until", "address", "source_url", "last_checked"]
LICENCE_RE = re.compile(r"^RL\d{3,5}$")
# A real register has thousands of rows; far fewer means the page layout changed.
MIN_ROWS = 1000


class _TableParser(HTMLParser):
    """Collects the text of every <td> in every <tr>."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag == "td" and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag == "td" and self._row is not None and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def parse_register(html: str, last_checked: date) -> list[dict[str, str]]:
    """Turn the register page into CSV rows. Raises ValueError if it looks wrong."""
    parser = _TableParser()
    parser.feed(html)
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for cells in parser.rows:
        # Columns: serial, licence no, name, address, phone, status, valid until
        if len(cells) != 7 or not LICENCE_RE.match(cells[1]):
            continue
        licence_no, name, address, status, valid_raw = cells[1], cells[2], cells[3], cells[5], cells[6]
        if licence_no in seen:
            raise ValueError(f"duplicate licence number in register: {licence_no}")
        seen.add(licence_no)
        try:
            valid_until = datetime.strptime(valid_raw, "%d/%b/%Y").date().isoformat()
        except ValueError:
            valid_until = ""  # unknown stays unknown; the engine treats it as not verified
        out.append(
            {
                "licence_no": licence_no,
                "name": name,
                "status": status,
                "valid_until": valid_until,
                "address": address,
                "source_url": REGISTER_URL,
                "last_checked": last_checked.isoformat(),
            }
        )
    if len(out) < MIN_ROWS:
        raise ValueError(f"only {len(out)} agency rows found; the register page layout may have changed")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--html", type=Path, help="parse a saved copy of the register page instead of fetching it")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[2] / "data" / "agencies.csv")
    ap.add_argument("--date", type=date.fromisoformat, default=date.today(),
                    help="date the register page was fetched (default: today)")
    args = ap.parse_args(argv)

    if args.html:
        html = args.html.read_text(encoding="utf-8", errors="replace")
    else:
        with urllib.request.urlopen(REGISTER_URL, timeout=60) as resp:  # noqa: S310 - fixed https URL
            html = resp.read().decode("utf-8", errors="replace")
    try:
        rows = parse_register(html, args.date)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    with args.out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} agencies to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

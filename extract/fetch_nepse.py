#!/usr/bin/env python3
"""Download free NEPSE OHLC CSVs and build Power BI–ready files."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SYMBOLS_FILE = ROOT / "symbols.txt"

CDN = "https://cdn.jsdelivr.net/gh/SamirWagle/Nepse-All-Scraper@main/data"
PRICES_URL = CDN + "/company-wise/{symbol}/prices.csv"

UA = "nepse-powerbi-extract/1.0 (personal educational use)"


def load_symbols() -> list[str]:
    if not SYMBOLS_FILE.exists():
        raise SystemExit(f"Missing {SYMBOLS_FILE}")
    symbols = []
    for line in SYMBOLS_FILE.read_text().splitlines():
        s = line.strip().upper()
        if s and not s.startswith("#"):
            symbols.append(s)
    if not symbols:
        raise SystemExit("symbols.txt is empty")
    return symbols


def fetch_text(url: str) -> str:
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def parse_prices(symbol: str, text: str) -> list[dict]:
    reader = csv.DictReader(text.splitlines())
    rows = []
    for row in reader:
        rows.append(
            {
                "symbol": symbol,
                "date": (row.get("date") or "").strip(),
                "open": (row.get("open") or "").strip(),
                "high": (row.get("high") or "").strip(),
                "low": (row.get("low") or "").strip(),
                "close": (row.get("ltp") or row.get("close") or "").strip(),
                "percent_change": (row.get("percent_change") or "").strip().replace("%", ""),
                "qty": (row.get("qty") or "").strip(),
                "turnover": (row.get("turnover") or "").strip(),
            }
        )
    return rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def latest_per_symbol(all_rows: list[dict]) -> list[dict]:
    latest: dict[str, dict] = {}
    for row in all_rows:
        sym = row["symbol"]
        prev = latest.get(sym)
        if prev is None or row["date"] > prev["date"]:
            latest[sym] = row
    return sorted(latest.values(), key=lambda r: r["symbol"])


def main() -> int:
    symbols = load_symbols()
    DATA.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict] = []
    failed: list[str] = []

    for symbol in symbols:
        url = PRICES_URL.format(symbol=symbol)
        print(f"Fetching {symbol} ...", flush=True)
        try:
            text = fetch_text(url)
            rows = parse_prices(symbol, text)
            if not rows:
                failed.append(symbol)
                print(f"  empty: {symbol}")
                continue
            all_rows.extend(rows)
            write_csv(
                DATA / "by_symbol" / f"{symbol}_prices.csv",
                [
                    "symbol",
                    "date",
                    "open",
                    "high",
                    "low",
                    "close",
                    "percent_change",
                    "qty",
                    "turnover",
                ],
                rows,
            )
            print(f"  {len(rows)} rows")
        except (HTTPError, URLError, TimeoutError) as e:
            failed.append(symbol)
            print(f"  failed: {symbol} ({e})")

    if not all_rows:
        print("No data downloaded.", file=sys.stderr)
        return 1

    fields = [
        "symbol",
        "date",
        "open",
        "high",
        "low",
        "close",
        "percent_change",
        "qty",
        "turnover",
    ]
    write_csv(DATA / "daily_prices.csv", fields, all_rows)
    write_csv(DATA / "watchlist_latest.csv", fields, latest_per_symbol(all_rows))
    write_csv(
        DATA / "symbols.csv",
        ["symbol"],
        [{"symbol": s} for s in symbols if s not in failed],
    )

    print()
    print(f"Wrote {DATA / 'daily_prices.csv'} ({len(all_rows)} rows)")
    print(f"Wrote {DATA / 'watchlist_latest.csv'}")
    print(f"Wrote {DATA / 'symbols.csv'}")
    if failed:
        print(f"Failed symbols: {', '.join(failed)}")
    print("Done. Import data/daily_prices.csv into Power BI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

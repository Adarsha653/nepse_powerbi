#!/usr/bin/env python3
"""Export watchlist/history OHLC into Google Drive for Power BI deep-dive later."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from nepse_common import load_settings, write_xlsx  # noqa: E402

CDN = "https://cdn.jsdelivr.net/gh/SamirWagle/Nepse-All-Scraper@main/data/company-wise/{symbol}/prices.csv"
UA = "nepse-powerbi-history/1.0"


def load_symbols() -> list[str]:
    # Prefer live suggestions if present; else symbols.txt
    settings = load_settings(ROOT / "config" / "settings.env")
    gdrive = Path(settings["GDRIVE_ROOT"])
    sug = gdrive / "live" / "suggestions.xlsx"
    symbols: list[str] = []

    # Always include symbols.txt as user seed defaults
    sym_file = ROOT / "symbols.txt"
    if sym_file.exists():
        for line in sym_file.read_text().splitlines():
            s = line.strip().upper()
            if s and not s.startswith("#"):
                symbols.append(s)

    # Merge suggested symbols from last live run (csv mirror)
    local_csv = ROOT / "live" / "suggestions.csv"
    if local_csv.exists():
        with local_csv.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                s = (row.get("symbol") or "").strip().upper()
                if s:
                    symbols.append(s)

    # unique preserve order
    seen = set()
    out = []
    for s in symbols:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def fetch_symbol(symbol: str) -> list[dict]:
    url = CDN.format(symbol=symbol)
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8")
    rows = []
    reader = csv.DictReader(text.splitlines())
    for row in reader:
        rows.append(
            {
                "symbol": symbol,
                "date": (row.get("date") or "").strip(),
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "close": row.get("ltp") or row.get("close"),
                "percent_change": (row.get("percent_change") or "").replace("%", ""),
                "qty": row.get("qty"),
                "turnover": row.get("turnover"),
            }
        )
    return rows


def main() -> int:
    settings = load_settings(ROOT / "config" / "settings.env")
    gdrive = Path(settings["GDRIVE_ROOT"])
    out_dir = gdrive / "history"
    out_dir.mkdir(parents=True, exist_ok=True)
    (ROOT / "history").mkdir(parents=True, exist_ok=True)

    symbols = load_symbols()
    all_rows: list[dict] = []
    failed = []
    for sym in symbols:
        print(f"History {sym} ...", flush=True)
        try:
            rows = fetch_symbol(sym)
            all_rows.extend(rows)
            print(f"  {len(rows)} rows")
        except Exception as e:
            failed.append(sym)
            print(f"  failed: {e}")

    if not all_rows:
        print("No history rows", file=sys.stderr)
        return 1

    write_xlsx(out_dir / "daily_prices.xlsx", "DailyPrices", all_rows)
    write_xlsx(ROOT / "history" / "daily_prices.xlsx", "DailyPrices", all_rows)
    print(f"Wrote {out_dir / 'daily_prices.xlsx'} ({len(all_rows)} rows)")
    if failed:
        print("Failed:", ", ".join(failed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

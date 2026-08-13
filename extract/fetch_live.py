#!/usr/bin/env python3
"""Pull near-live NEPSE data and write Power BI–ready Excel files to Google Drive."""

from __future__ import annotations

import asyncio
import csv
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from nepse_common import (  # noqa: E402
    load_settings,
    pct_change,
    safe_float,
    write_xlsx,
)


def score_attractiveness(row: dict[str, Any], max_turnover: float, max_trades: float) -> tuple[float, str]:
    """Heuristic score for 'likely interesting / liquid value candidates' — not financial advice."""
    turnover = safe_float(row.get("turnover")) or 0.0
    trades = safe_float(row.get("total_trades")) or 0.0
    pct = safe_float(row.get("percent_change")) or 0.0
    qty = safe_float(row.get("qty")) or 0.0
    ltp = safe_float(row.get("ltp")) or 0.0
    prev = safe_float(row.get("previous_close")) or 0.0
    high52 = safe_float(row.get("fifty_two_week_high")) or 0.0
    low52 = safe_float(row.get("fifty_two_week_low")) or 0.0

    reasons: list[str] = []
    score = 0.0

    # Liquidity (0–40)
    if max_turnover > 0:
        liq = 40.0 * (turnover / max_turnover)
        score += liq
        if liq >= 25:
            reasons.append("High turnover (liquid)")
        elif liq >= 12:
            reasons.append("Decent turnover")

    # Activity (0–20)
    if max_trades > 0:
        act = 20.0 * (trades / max_trades)
        score += act
        if act >= 12:
            reasons.append("Active trading")

    # Momentum quality (0–25): prefer steady gains over extreme spikes
    abs_pct = abs(pct)
    if 0.3 <= pct <= 4.0 and turnover > 0:
        score += 25.0
        reasons.append("Steady positive move")
    elif 0.0 < pct < 0.3:
        score += 8.0
    elif pct > 4.0 and pct <= 8.0 and turnover > 0:
        score += 12.0
        reasons.append("Strong gain (watch volatility)")
    elif pct < -2.0 and turnover > 0:
        score += 5.0
        reasons.append("Sold off on volume (contrarian watch)")

    # 52-week position (0–15): not at extreme frothy high, not dead low without volume
    if high52 > low52 and ltp > 0:
        pos = (ltp - low52) / (high52 - low52)
        if 0.25 <= pos <= 0.75:
            score += 15.0
            reasons.append("Mid 52-week range")
        elif pos < 0.25 and qty > 0:
            score += 8.0
            reasons.append("Near 52-week low (higher risk)")
        elif pos > 0.9:
            score += 2.0
            reasons.append("Near 52-week high")

    if not reasons:
        reasons.append("Mixed signals")

    # Tiny penalty for missing previous close math
    if prev <= 0 and ltp > 0:
        score *= 0.95

    return round(score, 2), "; ".join(reasons[:3])


def normalize_today_row(r: dict[str, Any]) -> dict[str, Any]:
    ltp = safe_float(r.get("lastUpdatedPrice"))
    if ltp is None:
        ltp = safe_float(r.get("closePrice"))
    prev = safe_float(r.get("previousDayClosePrice"))
    open_p = safe_float(r.get("openPrice"))
    high_p = safe_float(r.get("highPrice"))
    low_p = safe_float(r.get("lowPrice"))
    qty = safe_float(r.get("totalTradedQuantity"))
    turnover = safe_float(r.get("totalTradedValue"))
    trades = safe_float(r.get("totalTrades"))
    pct = pct_change(ltp, prev)

    return {
        "business_date": r.get("businessDate"),
        "symbol": (r.get("symbol") or "").strip().upper(),
        "security_name": r.get("securityName"),
        "ltp": ltp,
        "open": open_p,
        "high": high_p,
        "low": low_p,
        "previous_close": prev,
        "percent_change": pct,
        "qty": qty,
        "turnover": turnover,
        "total_trades": trades,
        "avg_traded_price": safe_float(r.get("averageTradedPrice")),
        "fifty_two_week_high": safe_float(r.get("fiftyTwoWeekHigh")),
        "fifty_two_week_low": safe_float(r.get("fiftyTwoWeekLow")),
        "last_updated_time": r.get("lastUpdatedTime"),
        "security_id": r.get("securityId"),
    }


def top_table(
    rows: list[dict[str, Any]],
    kind: str,
    market_by_symbol: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build movers rows. Gainers/losers APIs omit volume fields; enrich from market snapshot."""
    market_by_symbol = market_by_symbol or {}
    out = []
    for i, r in enumerate(rows, start=1):
        symbol = (r.get("symbol") or "").strip().upper()
        m = market_by_symbol.get(symbol, {})

        ltp = safe_float(r.get("ltp"))
        if ltp is None:
            ltp = safe_float(r.get("closingPrice"))
        if ltp is None:
            ltp = safe_float(m.get("ltp"))

        pct = safe_float(r.get("percentageChange"))
        if pct is None:
            pct = safe_float(m.get("percent_change"))

        point = safe_float(r.get("pointChange"))
        if point is None and ltp is not None and m.get("previous_close"):
            prev = safe_float(m.get("previous_close"))
            if prev is not None:
                point = round(ltp - prev, 4)

        turnover = safe_float(r.get("turnover") or r.get("totalTradedValue"))
        if turnover is None:
            turnover = safe_float(m.get("turnover"))

        qty = safe_float(r.get("quantity") or r.get("totalTradedQuantity"))
        if qty is None:
            qty = safe_float(m.get("qty"))

        trades = safe_float(r.get("totalTrades"))
        if trades is None:
            trades = safe_float(m.get("total_trades"))

        name = r.get("securityName") or m.get("security_name")

        out.append(
            {
                "rank": i,
                "list_type": kind,
                "symbol": symbol,
                "security_name": name,
                "ltp": ltp,
                "percent_change": pct,
                "point_change": point,
                "turnover": turnover,
                "qty": qty,
                "total_trades": trades,
            }
        )
    return out


async def fetch_all() -> dict[str, Any]:
    from nepseman_api import NepseClient

    async with NepseClient() as nepse:
        status = await nepse.market_status()
        today = await nepse.today_price()
        gainers = await nepse.top_gainers()
        losers = await nepse.top_losers()
        try:
            turnover = await nepse.top_turnover()
        except Exception:
            turnover = []
        try:
            summary = await nepse.market_summary()
        except Exception:
            summary = {}
        return {
            "status": status,
            "today": today or [],
            "gainers": gainers or [],
            "losers": losers or [],
            "turnover": turnover or [],
            "summary": summary or {},
        }


def build_suggestions(
    market: list[dict[str, Any]],
    min_turnover: float,
    max_abs_pct: float,
    count: int,
) -> list[dict[str, Any]]:
    eligible = []
    for row in market:
        sym = row.get("symbol") or ""
        # skip obvious debenture-like codes with long digit tails when low equity-like activity
        turnover = safe_float(row.get("turnover")) or 0.0
        pct = safe_float(row.get("percent_change"))
        if turnover < min_turnover:
            continue
        if pct is None:
            continue
        if abs(pct) > max_abs_pct:
            continue
        if not sym or sym.endswith(("D",)) and any(ch.isdigit() for ch in sym):
            # keep banks etc; only skip if looks like bond series e.g. BOKD86 — still allow if liquid
            pass
        eligible.append(row)

    max_turnover = max((safe_float(r.get("turnover")) or 0.0 for r in eligible), default=0.0)
    max_trades = max((safe_float(r.get("total_trades")) or 0.0 for r in eligible), default=0.0)

    scored = []
    for row in eligible:
        s, reason = score_attractiveness(row, max_turnover, max_trades)
        scored.append({**row, "attractiveness_score": s, "suggestion_reason": reason})

    scored.sort(key=lambda r: r["attractiveness_score"], reverse=True)
    out = []
    for i, row in enumerate(scored[:count], start=1):
        out.append(
            {
                "rank": i,
                "symbol": row["symbol"],
                "security_name": row.get("security_name"),
                "ltp": row.get("ltp"),
                "percent_change": row.get("percent_change"),
                "turnover": row.get("turnover"),
                "qty": row.get("qty"),
                "total_trades": row.get("total_trades"),
                "attractiveness_score": row["attractiveness_score"],
                "suggestion_reason": row["suggestion_reason"],
                "is_suggested": 1,
            }
        )
    return out


def append_run_log(path: Path, ok: bool, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().isoformat(timespec="seconds")
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{stamp}\tok={ok}\t{message}\n")


def resolve_output_dirs() -> tuple[list[Path], Path | None]:
    """Return write targets + optional log path.

    - CI/GitHub Actions: set OUTPUT_DIR=output/live (then upload_drive.py)
    - Mac local: also write to GDRIVE_ROOT/live from settings.env when present
    """
    settings_path = ROOT / "config" / "settings.env"
    settings = load_settings(settings_path) if settings_path.exists() else {}

    dirs: list[Path] = []
    log_path: Path | None = None

    output_dir = os.environ.get("OUTPUT_DIR", "").strip()
    if output_dir:
        dirs.append(Path(output_dir))

    gdrive_env = os.environ.get("GDRIVE_ROOT", "").strip()
    gdrive = Path(gdrive_env).expanduser() if gdrive_env else None
    if gdrive is None and settings.get("GDRIVE_ROOT"):
        gdrive = Path(settings["GDRIVE_ROOT"]).expanduser()

    if gdrive is not None:
        # Skip Mac Google Drive path on CI / machines where it doesn't exist
        if os.environ.get("CI", "").lower() in {"1", "true", "yes"}:
            gdrive = None
        elif not gdrive.parent.exists() and not gdrive.exists():
            # e.g. CloudStorage path missing on Linux runner
            print(f"Skipping GDRIVE_ROOT (path unavailable): {gdrive}")
            gdrive = None

    if gdrive is not None:
        live = gdrive / "live"
        dirs.append(live)
        (gdrive / "history").mkdir(parents=True, exist_ok=True)
        (gdrive / "config").mkdir(parents=True, exist_ok=True)
        log_path = gdrive / "config" / "extract_log.txt"

    # always keep a local mirror for debugging (skipped in CI if OUTPUT_DIR set only — still useful)
    local_live = ROOT / "live"
    if str(local_live.resolve()) not in {str(p.resolve()) for p in dirs}:
        dirs.append(local_live)

    if not dirs:
        dirs.append(ROOT / "output" / "live")

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    return dirs, log_path


async def async_main() -> int:
    settings_path = ROOT / "config" / "settings.env"
    settings = load_settings(settings_path) if settings_path.exists() else {}
    out_dirs, log_path = resolve_output_dirs()
    pulled_at = datetime.now().astimezone().isoformat(timespec="seconds")

    try:
        raw = await fetch_all()
    except Exception as e:
        if log_path is not None:
            append_run_log(log_path, False, f"fetch_failed: {type(e).__name__}: {e}")
        print(f"FETCH FAILED — keeping previous files. {e}", file=sys.stderr)
        return 1

    status = raw["status"] if isinstance(raw["status"], dict) else {"raw": raw["status"]}
    market = [normalize_today_row(r) for r in raw["today"] if r.get("symbol")]
    market = [r for r in market if r["symbol"]]

    suggestions = build_suggestions(
        market,
        min_turnover=float(settings.get("MIN_TURNOVER_NPR", 500000)),
        max_abs_pct=float(settings.get("MAX_ABS_PCT_FOR_SUGGESTION", 8.0)),
        count=int(settings.get("SUGGESTION_COUNT", 15)),
    )
    suggested_syms = {r["symbol"] for r in suggestions}

    # flag suggestions on full market for easy Power BI filtering
    for row in market:
        row["is_suggested"] = 1 if row["symbol"] in suggested_syms else 0

    movers = []
    market_by_symbol = {r["symbol"]: r for r in market if r.get("symbol")}
    movers += top_table(raw["gainers"][:15], "gainer", market_by_symbol)
    movers += top_table(raw["losers"][:15], "loser", market_by_symbol)
    # turnover list shape can vary
    t_rows = []
    for r in raw["turnover"][:15]:
        if isinstance(r, dict):
            t_rows.append(r)
    movers += top_table(t_rows, "turnover", market_by_symbol)

    is_open = str(status.get("isOpen", status.get("is_open", ""))).upper()
    meta = [
        {
            "pulled_at_local": pulled_at,
            "market_is_open": is_open,
            "market_as_of": status.get("asOf") or status.get("as_of"),
            "business_date": market[0]["business_date"] if market else None,
            "row_count_market": len(market),
            "suggestion_count": len(suggestions),
            "source": "nepseman-api / nepalstock (unofficial)",
            "disclaimer": "Educational use only. Suggestions are liquidity/momentum heuristics, not investment advice.",
        }
    ]

    # summary sheet-friendly single row extras
    summary = raw.get("summary")
    summary_rows = []
    if isinstance(summary, dict) and summary:
        summary_rows.append({k: summary.get(k) for k in summary})
    elif isinstance(summary, list):
        for item in summary:
            if isinstance(item, dict):
                summary_rows.append(item)

    files = {
        "market_snapshot.xlsx": ("Market", market),
        "suggestions.xlsx": ("Suggestions", suggestions),
        "movers.xlsx": ("Movers", movers),
        "meta.xlsx": ("Meta", meta),
    }
    if summary_rows:
        files["market_summary.xlsx"] = ("Summary", summary_rows)

    for name, (sheet, rows) in files.items():
        for d in out_dirs:
            write_xlsx(d / name, sheet, rows)

    # CSV copies on first output dir only (debug)
    debug_dir = out_dirs[0]
    for name, (_, rows) in files.items():
        if not rows:
            continue
        csv_path = debug_dir / name.replace(".xlsx", ".csv")
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    for d in out_dirs:
        (d / "last_success.json").write_text(
            json.dumps(meta[0], indent=2), encoding="utf-8"
        )

    if log_path is not None:
        append_run_log(
            log_path,
            True,
            f"rows={len(market)} suggested={len(suggestions)} open={is_open}",
        )
    print(f"OK — wrote {len(market)} market rows, {len(suggestions)} suggestions")
    print("Output dirs:", ", ".join(str(d) for d in out_dirs))
    print(f"Market open: {is_open} | pulled_at: {pulled_at}")
    if suggestions:
        print("Top suggestions:", ", ".join(r["symbol"] for r in suggestions[:8]))
    return 0


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())

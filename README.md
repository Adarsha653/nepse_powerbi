# NEPSE Pulse

Mac extracts near-live NEPSE data hourly → Google Drive → Windows Power BI Desktop.

**Look:** clean light finance  
**Watchlist:** user-selected in Power BI (slicer)  
**Suggestions:** ranked liquid/momentum heuristics (not investment advice)  
**Scope now:** Page 1 only

## Google Drive folder

Already created on Mac (Gmail Drive):

`My Drive / NEPSE_PowerBI / live /`

On Windows: sync the same Google account (`adarsha.aryal653@gmail.com`) and open that folder in Power BI Desktop.

## GitHub Actions (Mac can be off)

Hourly extract publishes to branch **`live-data`** (no Drive service-account upload — blocked on personal Gmail).

Setup: [`docs/GITHUB_ACTIONS_SETUP.md`](docs/GITHUB_ACTIONS_SETUP.md)

Power BI CSV URLs:

```text
https://raw.githubusercontent.com/Adarsha653/nepse_powerbi/live-data/live/market_snapshot.csv
```

## Mac setup (optional local fallback)

```bash
cd /Users/aryal/Documents/nepse_powerbi
python3 -m pip install -r requirements.txt

# one live pull (works now — market was OPEN in testing)
python3 extract/fetch_live.py

# optional history for later pages
python3 extract/fetch_history.py

# install hourly scheduler (skips outside market hours)
chmod +x scripts/*.sh
./scripts/install_scheduler.sh
```

Force a pull anytime:

```bash
./scripts/run_hourly.sh --force
```

## Outputs (`live/`)

| File | Purpose |
|------|---------|
| `market_snapshot.xlsx` | Full market — user builds watchlist via slicer |
| `suggestions.xlsx` | Top attractive candidates + reasons |
| `movers.xlsx` | Gainers / losers / turnover |
| `meta.xlsx` | Refresh time + market open/closed |

## Windows next step

Follow: [`docs/POWERBI_PAGE1.md`](docs/POWERBI_PAGE1.md)

## Disclaimer

Unofficial NEPSE data. Educational use only. Suggestions are not buy/sell recommendations.

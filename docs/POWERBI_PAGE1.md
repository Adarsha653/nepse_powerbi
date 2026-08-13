# NEPSE Pulse — Page 1 (Power BI Desktop on Windows)

Clean light finance look. User picks watchlist via slicers. Suggestions are ranked heuristics (not advice).

## 0. Data source (GitHub live-data branch)

After Actions runs, use **Get data → Web** with these CSVs:

```text
https://raw.githubusercontent.com/Adarsha653/nepse_powerbi/live-data/live/market_snapshot.csv
https://raw.githubusercontent.com/Adarsha653/nepse_powerbi/live-data/live/suggestions.csv
https://raw.githubusercontent.com/Adarsha653/nepse_powerbi/live-data/live/movers.csv
https://raw.githubusercontent.com/Adarsha653/nepse_powerbi/live-data/live/meta.csv
```

Or download the `.xlsx` files from the `live-data` branch and load them as Excel.

(Google Drive service-account auto-upload is blocked on personal Gmail; see `GITHUB_ACTIONS_SETUP.md`.)

## 1. Create the PBIX

1. Open **Power BI Desktop**
2. **Home → Get data → Web**
3. Paste:
   `https://raw.githubusercontent.com/Adarsha653/nepse_powerbi/live-data/live/market_snapshot.csv`
4. Load / Transform — set types:
   - `percent_change`, `ltp`, `turnover`, `qty`, … → Decimal
   - `is_suggested` → Whole number
5. Repeat **Get data → Web** for `suggestions.csv`, `movers.csv`, `meta.csv`
6. Rename tables to `Market`, `Suggestions`, `Movers`, `Meta` if you want

## 2. Page 1 layout — “NEPSE Pulse”

Theme: **light** background, dark text, green up / red down, one blue accent.

### A. Freshness banner
- Insert **Card** or **Multi-row card** from `Meta`
- Fields: `pulled_at_local`, `market_is_open`, `business_date`
- Title text box: **NEPSE Pulse**

### B. KPI row (4 cards)
Use `Market` with filters as noted:

| Card | Field / idea |
|------|----------------|
| Suggested avg % | Avg of `percent_change` where `is_suggested = 1` |
| Advancers | Count of rows with `percent_change > 0` |
| Decliners | Count of rows with `percent_change < 0` |
| Top turnover | Sum or Max `turnover` (or average of top names via Movers) |

Create measures if comfortable, e.g.:

```dax
Advancers = CALCULATE(COUNTROWS(Market), Market[percent_change] > 0)
Decliners = CALCULATE(COUNTROWS(Market), Market[percent_change] < 0)
Suggested Avg % = CALCULATE(AVERAGE(Market[percent_change]), Market[is_suggested] = 1)
```

### C. User watchlist control
- **Slicer** on `Market[symbol]` (search enabled)
- Optional second slicer: `is_suggested` (0/1) so users can focus suggestions first, then add more symbols

This is the user-based watchlist: whatever they select in the slicer.

### D. Suggestions panel
- Table from `Suggestions`:
  - `rank`, `symbol`, `security_name`, `ltp`, `percent_change`, `turnover`, `attractiveness_score`, `suggestion_reason`
- Sort by `rank`
- Conditional format `percent_change` green/red

### E. Watchlist live table
- Table from `Market` (respects symbol slicer):
  - `symbol`, `security_name`, `ltp`, `percent_change`, `qty`, `turnover`, `total_trades`
- Conditional format % column

### F. Movers strip
- Clustered bar from `Movers`
- Filter `list_type` = `gainer` (or use small multiples / two charts: gainers + losers)
- Values: `percent_change` by `symbol`

## 3. Interactivity checklist
- [ ] Symbol slicer drives watchlist table + KPIs as intended
- [ ] Suggestions table visible even when slicer empty (don’t filter Suggestions by Market slicer unless you want that — keep Suggestions **unfiltered** via Edit interactions)
- [ ] Meta banner always visible
- [ ] **Refresh** button updates after Mac hourly run

### Edit interactions (important)
1. Select the symbol slicer  
2. **Format → Edit interactions**  
3. Set **Suggestions** visual to **None** (so recommendations stay visible as guidance)  
4. Market watchlist table stays **Filter**

## 4. Refresh routine
1. Mac writes new Excel into Google Drive every hour in market hours  
2. Wait for Drive sync on Windows  
3. In Power BI Desktop: **Home → Refresh**

## 5. Look & feel (light finance)
- Theme: **Executive** or custom light theme
- Page background: white / very light gray
- Fonts: Segoe UI
- Greens for positive %, reds for negative
- Avoid dark mode, neon, purple gradients
- One clear title; no extra clutter cards

## Disclaimer
Suggestions use liquidity + momentum heuristics only. Not investment advice.

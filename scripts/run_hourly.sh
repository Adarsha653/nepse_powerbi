#!/usr/bin/env bash
# Run live NEPSE extract only during typical market hours (Sun–Thu, 11:00–15:30 NST).
# NST = UTC+05:45

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Compute current time in NST roughly via UTC+5:45
# macOS date
utc_hm=$(date -u +%H%M)
# NST = UTC + 5h45m → add 345 minutes
nst_minutes=$((10#${utc_hm:0:2} * 60 + 10#${utc_hm:2:2} + 345))
nst_minutes=$((nst_minutes % 1440))
nst_h=$((nst_minutes / 60))
nst_m=$((nst_minutes % 60))
nst_hm=$((nst_h * 100 + nst_m))

# Weekday in NST roughly same calendar day for AU/NP for our purposes; use local weekday
dow=$(date +%u) # 1=Mon .. 7=Sun

# NEPSE: Sun–Thu. Map: Sun=7, Mon=1, Tue=2, Wed=3, Thu=4
if [[ "$dow" -eq 5 || "$dow" -eq 6 ]]; then
  echo "Skip: weekend (Fri/Sat local). NEPSE typically closed."
  exit 0
fi

# Allow force
if [[ "${1:-}" == "--force" ]]; then
  exec python3 extract/fetch_live.py
fi

# Market window ~11:00–15:30 NST
if (( nst_hm < 1100 || nst_hm > 1530 )); then
  echo "Skip: outside market window (NST ~$(printf '%02d:%02d' "$nst_h" "$nst_m")). Use --force to run anyway."
  exit 0
fi

exec python3 extract/fetch_live.py

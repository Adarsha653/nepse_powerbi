# GitHub Actions setup (updated)

Hourly job runs on GitHub (Mac can be off) and publishes files to the **`live-data`** branch.

> **Why not Google Drive service account?**  
> Google no longer lets service accounts upload into a personal Gmail **My Drive** folder (`storageQuotaExceeded`). Shared Drives need Google Workspace. So we publish to GitHub instead.

## What you need
No Drive secrets required for the default setup.

## After each run, files appear at
Branch: `live-data` → folder `live/`

Raw CSV examples (for Power BI **Get data → Web**):

```text
https://raw.githubusercontent.com/Adarsha653/nepse_powerbi/live-data/live/market_snapshot.csv
https://raw.githubusercontent.com/Adarsha653/nepse_powerbi/live-data/live/suggestions.csv
https://raw.githubusercontent.com/Adarsha653/nepse_powerbi/live-data/live/movers.csv
https://raw.githubusercontent.com/Adarsha653/nepse_powerbi/live-data/live/meta.csv
```

Excel copies are in the same folder if you prefer downloading them.

## Run manually
Repo → **Actions** → **NEPSE hourly live extract** → **Run workflow**

## Optional: keep using your Drive folder
Your cloud folder is ready:

`https://drive.google.com/drive/folders/1P_6an-_gb-l56xqvYGyvBwybcpXtNjum`

You can **manually upload** the Excel files from Mac:

`/Users/aryal/Documents/nepse_powerbi/live/*.xlsx`

into that `live` folder for Power BI Desktop (Get data → Excel from Drive/local sync). Automated Drive upload would need **your** Google OAuth (not a service account).

# GitHub Actions → Google Drive setup

This runs the NEPSE extract on GitHub’s servers (Mac can be off) and uploads Excel files into your Drive `NEPSE_PowerBI/live` folder.

## 1. Create a Google Cloud service account

1. Open [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select a project (any name, e.g. `nepse-pulse`)
3. **APIs & Services → Enable APIs** → enable **Google Drive API**
4. **IAM & Admin → Service Accounts → Create**
   - Name: `nepse-pulse-uploader`
   - Skip optional permissions
5. Open the service account → **Keys → Add key → JSON** → download the JSON file
6. Copy the service account email (looks like `nepse-pulse-uploader@....iam.gserviceaccount.com`)

## 2. Share your Drive folder with that email

1. In Google Drive (account **`adarsha.aryal653@gmail.com`**) open **`NEPSE_PowerBI` → `live`**
2. **Share** → add the service account email → role **Editor**
3. Copy the **folder ID** from the browser URL:

```text
https://drive.google.com/drive/folders/THIS_IS_THE_FOLDER_ID
```

That `THIS_IS_THE_FOLDER_ID` value is `DRIVE_FOLDER_ID`.

## 3. Create the GitHub repo + secrets

After the code is pushed to GitHub:

1. Repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|-------------|--------|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Full contents of the downloaded JSON key file (paste entire JSON) |
| `DRIVE_FOLDER_ID` | The `live` folder ID from step 2 |

## 4. Run it

- Automatic: Sun–Thu about every hour during NEPSE hours (UTC cron)
- Manual: **Actions → NEPSE hourly live extract → Run workflow**

## 5. Power BI

Unchanged: Windows Power BI Desktop still reads from Google Drive  
`adarsha.aryal653@gmail.com` → `NEPSE_PowerBI/live/*.xlsx` → click **Refresh**.

## If the Action fails with 403 from NEPSE

Cloud IPs are sometimes blocked. Then use Mac extract as fallback, or a Nepal VPS later.

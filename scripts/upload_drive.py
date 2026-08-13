#!/usr/bin/env python3
"""Upload Excel files in a local folder to a Google Drive folder (service account)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]


def drive_service_from_env():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        raise SystemExit(
            "Missing env GOOGLE_SERVICE_ACCOUNT_JSON (service account JSON content)."
        )
    info = json.loads(raw)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def find_existing_file(service, folder_id: str, name: str) -> str | None:
    q = (
        f"name = '{name}' and '{folder_id}' in parents and trashed = false"
    )
    res = (
        service.files()
        .list(q=q, spaces="drive", fields="files(id, name)", pageSize=10)
        .execute()
    )
    files = res.get("files", [])
    return files[0]["id"] if files else None


def upload_or_update(service, folder_id: str, path: Path) -> str:
    existing = find_existing_file(service, folder_id, path.name)
    media = MediaFileUpload(
        str(path),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        resumable=True,
    )
    if existing:
        service.files().update(fileId=existing, media_body=media).execute()
        return existing
    meta = {"name": path.name, "parents": [folder_id]}
    created = service.files().create(body=meta, media_body=media, fields="id").execute()
    return created["id"]


def main() -> int:
    folder_id = os.environ.get("DRIVE_FOLDER_ID", "").strip()
    if not folder_id:
        raise SystemExit("Missing env DRIVE_FOLDER_ID (Google Drive folder id for live/).")

    src = Path(os.environ.get("UPLOAD_DIR", "output/live"))
    if not src.exists():
        raise SystemExit(f"Upload dir not found: {src}")

    files = sorted(src.glob("*.xlsx"))
    if not files:
        raise SystemExit(f"No .xlsx files in {src}")

    service = drive_service_from_env()
    for path in files:
        file_id = upload_or_update(service, folder_id, path)
        print(f"Uploaded {path.name} -> {file_id}")

    # also upload last_success.json if present
    js = src / "last_success.json"
    if js.exists():
        existing = find_existing_file(service, folder_id, js.name)
        media = MediaFileUpload(str(js), mimetype="application/json", resumable=True)
        if existing:
            service.files().update(fileId=existing, media_body=media).execute()
        else:
            service.files().create(
                body={"name": js.name, "parents": [folder_id]},
                media_body=media,
                fields="id",
            ).execute()
        print(f"Uploaded {js.name}")

    print("Drive upload complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

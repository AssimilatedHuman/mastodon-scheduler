# ------------------------------------------------------------
# mastodon-scheduler / scripts / post_mastodon.py
# ------------------------------------------------------------
# PURPOSE:
#   - Read content/mastodon.csv
#   - Check each row's timestamp
#   - If timestamp matches current UTC date within a ±3 hour window
#     AND not posted, then post it to Mastodon.
#   - Mark rows as posted instead of deleting them.
#
# WHY WE USE A 'posted' FLAG:
#   - Keeps rows intact for testing.
#   - Prevents double-posting.
#   - Lets you inspect what has been posted.
#   - Lets you reset a row by flipping posted=false.
#
# SCHEDULER:
#   - GitHub Actions runs this script once per hour.
#   - Cron: 0 * * * *
#
# TIME LOGIC:
#   - Current time = now (UTC)
#   - Match rows where:
#       row.timestamp.date() == now.date()
#       abs(row.timestamp.hour - now.hour) <= 3
#
# SECRETS:
#   - MASTODON_URL    (base URL of your Mastodon instance)
#   - MASTODON_TOKEN  (API token with write:statuses scope)
#
# CSV FORMAT:
#   timestamp,text,posted
#   2026-10-17T11:00,Hello world,false
#
# POSTING:
#   - Uses Mastodon API: POST /api/v1/statuses
#   - Sends "text" field as the status
# ------------------------------------------------------------

import csv
import os
from datetime import datetime
import requests

CSV_PATH = "content/mastodon.csv"

# ------------------------------------------------------------
# Load Mastodon credentials from environment variables
# ------------------------------------------------------------
MASTODON_URL = os.getenv("MASTODON_URL")
MASTODON_TOKEN = os.getenv("MASTODON_TOKEN")

if not MASTODON_URL or not MASTODON_TOKEN:
    print("Missing Mastodon credentials. Exiting.")
    exit(0)

# ------------------------------------------------------------
# Define current UTC date + hour
# ------------------------------------------------------------
now = datetime.utcnow()
current_date = now.date()
current_hour = now.hour

print(f"Current UTC time: {now}")
print(f"Matching rows scheduled for {current_date} within ±3 hours of {current_hour}")

# ------------------------------------------------------------
# Read CSV rows
# ------------------------------------------------------------
rows = []
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if "posted" not in row or row["posted"] == "":
            row["posted"] = "false"
        rows.append(row)

# ------------------------------------------------------------
# Process rows and decide which ones to post
# ------------------------------------------------------------
for row in rows:
    if row["posted"].lower() == "true":
        continue

    try:
        scheduled_time = datetime.fromisoformat(row["timestamp"])
    except Exception:
        print(f"Invalid timestamp format in row: {row}")
        continue

    # Match date + ±3 hour window
    if scheduled_time.date() == current_date and abs(scheduled_time.hour - current_hour) <= 3:
        print(f"POSTING: {row['text']} (scheduled for {scheduled_time})")

        try:
            response = requests.post(
                f"{MASTODON_URL}/api/v1/statuses",
                headers={"Authorization": f"Bearer {MASTODON_TOKEN}"},
                data={"status": row["text"]},
                timeout=10
            )

            if response.status_code == 200:
                print("Post successful.")
                row["posted"] = "true"
            else:
                print(f"Post failed: {response.status_code} {response.text}")
                continue

        except Exception as e:
            print(f"Error posting to Mastodon: {e}")
            continue

# ------------------------------------------------------------
# Rewrite CSV with updated posted flags
# ------------------------------------------------------------
with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["timestamp", "text", "posted"])
    writer.writeheader()
    writer.writerows(rows)

print("Done.")

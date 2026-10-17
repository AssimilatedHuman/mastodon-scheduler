# ------------------------------------------------------------
# mastodon-scheduler / scripts / post_mastodon.py
# ------------------------------------------------------------
# PURPOSE:
#   - Read content/mastodon.csv
#   - Check each row's timestamp
#   - If timestamp is within ±10 minutes of now AND not posted,
#     then post it to Mastodon.
#   - Mark rows as posted instead of deleting them.
#
# WHY WE USE A 'posted' FLAG:
#   - Keeps rows intact for testing.
#   - Prevents double-posting.
#   - Lets you inspect what has been posted.
#   - Lets you reset a row by flipping posted=false.
#
# SCHEDULER:
#   - GitHub Actions runs this script every 30 minutes.
#   - Cron: */30 * * * *
#
# TIME LOGIC:
#   - Current time = now (UTC)
#   - Valid window = now - 10 minutes  →  now + 10 minutes
#   - If row.timestamp is inside window → post it
#
# SECRETS:
#   - MASTODON_URL    (base URL of your Mastodon instance)
#   - MASTODON_TOKEN  (API token with write:statuses scope)
#
# CSV FORMAT:
#   timestamp,text,posted
#   2026-10-17T11:10,Hello world,false
#
# POSTING:
#   - Uses Mastodon API: POST /api/v1/statuses
#   - Sends "text" field as the status
# ------------------------------------------------------------

import csv
import os
from datetime import datetime, timedelta
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
# Define the ±10 minute posting window
# ------------------------------------------------------------
now = datetime.utcnow()
window_start = now - timedelta(minutes=10)
window_end = now + timedelta(minutes=10)

print(f"Current UTC time: {now}")
print(f"Posting window: {window_start} → {window_end}")

# ------------------------------------------------------------
# Read CSV rows
# ------------------------------------------------------------
rows = []
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Ensure 'posted' field exists
        if "posted" not in row or row["posted"] == "":
            row["posted"] = "false"
        rows.append(row)

# ------------------------------------------------------------
# Process rows and decide which ones to post
# ------------------------------------------------------------
for row in rows:
    # Skip rows already posted
    if row["posted"].lower() == "true":
        continue

    # Parse timestamp
    try:
        scheduled_time = datetime.fromisoformat(row["timestamp"])
    except Exception:
        print(f"Invalid timestamp format in row: {row}")
        continue

    # Check if scheduled_time is inside the ±10 minute window
    if window_start <= scheduled_time <= window_end:
        print(f"POSTING: {row['text']} (scheduled for {scheduled_time})")

        # ------------------------------------------------------------
        # Perform the Mastodon API POST
        # ------------------------------------------------------------
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
                # Leave posted=false so it retries next run
                continue

        except Exception as e:
            print(f"Error posting to Mastodon: {e}")
            # Leave posted=false so it retries next run
            continue

# ------------------------------------------------------------
# Rewrite CSV with updated posted flags
# ------------------------------------------------------------
with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["timestamp", "text", "posted"])
    writer.writeheader()
    writer.writerows(rows)

print("Done.")

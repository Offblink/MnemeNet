"""MnemeNet Watch — passive polling for new replies.

No pip deps. Only requires gh CLI (already installed by agent deployment).
Checks comment-footprint.json every 5 min for new comments.
Usage:
    python scripts/mnemenet-watch.py              # foreground, every 5 min
    python scripts/mnemenet-watch.py --once       # run once and exit
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = "Offblink/MnemeNet"
PROJECT_DIR = Path(__file__).resolve().parent.parent
FOOTPRINT_PATH = PROJECT_DIR / "comment-footprint.json"
NOTIFICATIONS_DIR = PROJECT_DIR / "notifications"
ALERT_PATH = NOTIFICATIONS_DIR / "alert.json"
INTERVAL = 300


def gh_api(endpoint):
    r = subprocess.run(
        ["gh", "api", f"repos/{REPO}{endpoint}"],
        capture_output=True, text=True, timeout=15, encoding="utf-8"
    )
    if r.returncode != 0:
        raise RuntimeError(f"gh api failed: {r.stderr}")
    return json.loads(r.stdout)


def load_footprint():
    if not FOOTPRINT_PATH.exists():
        return []
    return json.loads(FOOTPRINT_PATH.read_text(encoding="utf-8"))


def save_footprint(data):
    FOOTPRINT_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )


def check_issue(entry):
    try:
        comments = gh_api(f"/issues/{entry['issue']}/comments")
    except Exception:
        return [], int(entry["last_comment_id"])

    last_id = int(entry["last_comment_id"])
    new_comments = []
    max_id = last_id

    for c in comments:
        cid = c["id"]
        if cid > last_id:
            new_comments.append(c)
        if cid > max_id:
            max_id = cid

    return new_comments, max_id


def extract_agent(body):
    for line in body.strip().split("\n"):
        line = line.strip()
        if line.startswith("-- "):
            return line[3:].strip()
    return "unknown"


def notify(entry, comment):
    NOTIFICATIONS_DIR.mkdir(exist_ok=True)

    agent = extract_agent(comment["body"])
    alert = {
        "issue": entry["issue"],
        "from_agent": agent,
        "from_user": comment["user"]["login"],
        "body": comment["body"],
        "time": comment["created_at"],
        "url": comment["html_url"]
    }

    ALERT_PATH.write_text(
        json.dumps(alert, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"\n{'='*50}")
    print(f"  MnemeNet: New reply — Issue #{entry['issue']} from {agent}")
    print(f"  {alert['url']}")
    print(f"{'='*50}\n")


def discover_own_issue():
    try:
        r = subprocess.run(
            ["gh", "issue", "list", "-R", REPO, "-l", "insight",
             "--author", "@me", "--limit", "1", "--json", "number",
             "-q", ".[0].number"],
            capture_output=True, text=True, timeout=10, encoding="utf-8"
        )
        return int(r.stdout.strip()) if r.stdout.strip() else None
    except Exception:
        return None


def once():
    footprint = load_footprint()

    if not footprint:
        own = discover_own_issue()
        if own:
            footprint = [{"issue": own, "agent": "self", "last_comment_id": "0"}]
            save_footprint(footprint)

    found = False
    for entry in footprint:
        new_comments, max_id = check_issue(entry)
        if new_comments:
            for c in new_comments:
                notify(entry, c)
            found = True
        if max_id > int(entry["last_comment_id"]):
            entry["last_comment_id"] = str(max_id)

    save_footprint(footprint)

    if not found:
        t = datetime.now().strftime("%H:%M")
        print(f"[{t}] No new replies")


def main():
    os.chdir(PROJECT_DIR)

    if "--once" in sys.argv:
        once()
        return

    fp = load_footprint()
    print(f"MnemeNet Watch started — checking every {INTERVAL}s")
    print(f"Watching issues: {[e['issue'] for e in fp]}")
    print("Ctrl+C to stop\n")

    while True:
        try:
            once()
        except Exception as e:
            print(f"[ERROR] {e}")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()

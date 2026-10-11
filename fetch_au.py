"""Fetch this week's Coles / Woolworths / Aldi specials and save data/au/<date>.json.

Specials change every Wednesday, so this runs weekly. Same auth as fetch.py
(APIFY_TOKEN env, else the logged-in apify CLI).
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime

from fetch import DATA, KST


def api(method, path, body=None):
    token = os.environ.get("APIFY_TOKEN")
    if token:
        req = urllib.request.Request("https://api.apify.com" + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    cmd = ["apify", "api", method, path] + (["-d", json.dumps(body)] if body is not None else [])
    out = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, check=True)
    return json.loads(out.stdout)


def run_actor(act_id, inp):
    """Whole departments take longer than the 300 s sync limit, so start a run and poll."""
    run = api("POST", f"/v2/acts/{act_id}/runs?memory=256&maxTotalChargeUsd=30", inp)["data"]
    while run["status"] in ("READY", "RUNNING"):
        time.sleep(20)
        run = api("GET", f"/v2/actor-runs/{run['id']}")["data"]
    print("run", run["id"], run["status"], run.get("statusMessage"))
    items, offset = [], 0
    while True:
        page = api("GET", f"/v2/datasets/{run['defaultDatasetId']}/items?clean=1&limit=1000&offset={offset}")
        if not page:
            return items
        items += page
        offset += len(page)

ACTOR = "yLZu97UZ2P1SnNUeO"  # magenta_courser/australia-supermarket-prices
DEPARTMENTS = ["dairy-eggs-fridge", "pantry", "fruit-vegetables", "meat-seafood", "frozen", "drinks"]
INPUT = {"stores": ["coles", "woolworths", "aldi"], "categories": DEPARTMENTS,
         "maxItems": 0, "onlyOnSpecial": True}
KEEP = ["store", "productId", "name", "brand", "size", "price", "wasPrice", "unitPrice", "unitOfMeasure",
        "specialType", "specialText", "discountPct", "category", "subcategory", "requestedCategory", "url"]


def main():
    # One run per store and half of the departments: each run is capped by the account's
    # remaining budget (about 3,500 rows), and Coles alone has ~3,100 specials.
    rows = []
    halves = [DEPARTMENTS[:3], DEPARTMENTS[3:]]
    for store in INPUT["stores"]:
        for depts in halves:
            rows += run_actor(ACTOR, {**INPUT, "stores": [store], "categories": depts})
    rows = [{k: r.get(k) for k in KEEP} for r in rows if r.get("store") and r.get("name") and r.get("price")]
    stores = {r["store"] for r in rows}
    if len(rows) < 200 or len(stores) < 2:
        raise SystemExit(f"au: only {len(rows)} rows from {sorted(stores)}, not saving")
    today = datetime.now(KST).strftime("%Y-%m-%d")
    os.makedirs(os.path.join(DATA, "au"), exist_ok=True)
    with open(os.path.join(DATA, "au", f"{today}.json"), "w", encoding="utf-8") as f:
        json.dump({"date": today, "fetchedAt": datetime.now(KST).isoformat(timespec="minutes"), "items": rows},
                  f, ensure_ascii=False, indent=0)
    print("au", len(rows), sorted(stores))


if __name__ == "__main__":
    sys.exit(main())

"""Run the Daiso and Olive Young actors once and save today's snapshots to data/.

Auth: APIFY_TOKEN env var (GitHub Actions) or, if unset, the logged-in `apify` CLI (local).
Snapshots keep only public ranking facts (rank, name, brand, price, ratings, link).
"""
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

RUNS = {
    "daiso": ("o6n89EPvYwG4oxJFd", {
        "mode": "bestsellers", "period": "daily", "categories": ["all"],
        "maxItems": 100, "historyStoreName": "ranking-site-daiso"}),
    "oliveyoung": ("kbE4pFxEbMvdCQnYT", {
        "market": "both", "categories": ["all"], "maxItems": 100,
        "koreaPeriod": "day", "historyStoreName": "ranking-site-oliveyoung"}),
}
QS = "memory=256&timeout=280&clean=1"


def run_actor(act_id, inp):
    path = f"/v2/acts/{act_id}/run-sync-get-dataset-items?{QS}"
    token = os.environ.get("APIFY_TOKEN")
    if token:
        req = urllib.request.Request(
            "https://api.apify.com" + path, data=json.dumps(inp).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=320) as r:
            return json.load(r)
    out = subprocess.run(["apify", "api", "POST", path, "-d", json.dumps(inp, ensure_ascii=False)],
                         capture_output=True, text=True, stdin=subprocess.DEVNULL, check=True)
    return json.loads(out.stdout)


def slim_daiso(x):
    return {"rank": x["rank"], "id": x["productId"], "name": x["name"], "brand": x.get("brand"),
            "price": x.get("price"), "currency": "KRW", "rating": x.get("rating"),
            "reviews": x.get("reviewCount"), "sold": x.get("totalSold"),
            "category": x.get("category"), "soldOut": x.get("isSoldOut"), "url": x["url"]}


def slim_oy(x):
    ko = x["source"] == "korea"
    return {"rank": x["rank"], "id": x["productId"],
            "name": x.get("nameKo") if ko else (x.get("name") or x.get("nameKo")),
            "brand": x.get("brandKo") if ko else (x.get("brand") or x.get("brandKo")),
            "price": x.get("salePrice"), "originalPrice": x.get("originalPrice"),
            "discount": x.get("discountRate"), "currency": x.get("currency"),
            "rating": x.get("rating") if ko else x.get("globalRating"),
            "reviews": x.get("reviewCount") if ko else x.get("globalReviewCount"),
            "category": x.get("productCategory"), "soldOut": x.get("isSoldOut"), "url": x["url"]}


def save(key, rows, today):
    rows = [r for r in rows if r.get("name") and r.get("url")]
    if len(rows) < 50:
        raise SystemExit(f"{key}: only {len(rows)} rows, not saving")
    rows.sort(key=lambda r: r["rank"])
    os.makedirs(os.path.join(DATA, key), exist_ok=True)
    with open(os.path.join(DATA, key, f"{today}.json"), "w", encoding="utf-8") as f:
        json.dump({"date": today, "fetchedAt": datetime.now(KST).isoformat(timespec="minutes"),
                   "items": rows}, f, ensure_ascii=False, indent=0)
    print(key, len(rows))


def main():
    today = datetime.now(KST).strftime("%Y-%m-%d")
    items = run_actor(*RUNS["daiso"])
    save("daiso", [slim_daiso(x) for x in items if x.get("source") == "daiso"], today)
    items = run_actor(*RUNS["oliveyoung"])
    save("oliveyoung-kr", [slim_oy(x) for x in items if x.get("source") == "korea"], today)
    save("oliveyoung-global", [slim_oy(x) for x in items if x.get("source") == "global"], today)


if __name__ == "__main__":
    sys.exit(main())

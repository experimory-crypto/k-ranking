"""Build docs/au/index.html: this week's Coles / Woolworths / Aldi specials, side by side."""
import glob
import html
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "au")
OUT = os.path.join(HERE, "docs", "au")
ACTOR_URL = "https://apify.com/magenta_courser/australia-supermarket-prices"
STORES = {"coles": "Coles", "woolworths": "Woolworths", "aldi": "Aldi"}
DEPTS = {"dairy-eggs-fridge": "Dairy, Eggs & Fridge", "pantry": "Pantry", "fruit-vegetables": "Fruit & Vegetables",
         "meat-seafood": "Meat & Seafood", "frozen": "Frozen", "drinks": "Drinks"}
PER_STORE = 15  # rows per store per department, so Aldi (no was-prices) still shows up
e = html.escape

TITLE = "Supermarket Specials This Week: Coles vs Woolworths vs Aldi"
DESC = ("This week's Coles, Woolworths and Aldi specials side by side: half-price deals, biggest discounts and "
        "unit prices by department, updated every Wednesday.")


def latest():
    files = sorted(glob.glob(os.path.join(DATA, "*.json")))
    return json.load(open(files[-1], encoding="utf-8")) if files else None


def money(v):
    return "–" if v is None else f"${v:,.2f}"


def disc(r):
    if r.get("discountPct"):
        return r["discountPct"]
    if r.get("wasPrice") and r.get("price") and r["wasPrice"] > r["price"]:
        return round(100 * (1 - r["price"] / r["wasPrice"]))
    return 0


def row(r):
    unit = f'{money(r["unitPrice"])}/{e(r["unitOfMeasure"])}' if r.get("unitPrice") and r.get("unitOfMeasure") else "–"
    was = f'<s>{money(r["wasPrice"])}</s>' if r.get("wasPrice") else ""
    d = disc(r)
    label = r.get("specialText") or (f"{d}% off" if d else (r.get("specialType") or "").replace("_", " ").title())
    name = e(r["name"] + (f' {r["size"]}' if r.get("size") and r["size"] not in r["name"] else ""))
    return (f'<tr data-s="{r["store"]}" data-q="{e(((r.get("brand") or "") + " " + r["name"]).lower())}">'
            f'<td><span class="st st-{r["store"]}">{STORES[r["store"]]}</span></td>'
            f'<td class="it"><a href="{e(r["url"])}" rel="nofollow noopener" target="_blank">{name}</a></td>'
            f'<td class="num">{money(r["price"])} {was}</td>'
            f'<td class="num"><span class="disc">{e(label)}</span></td>'
            f'<td class="num hide-s">{unit}</td></tr>')


def table(rows):
    return ('<div class="tbl"><table><thead><tr><th>Store</th><th>Product</th><th class="num">Price</th>'
            '<th class="num">Deal</th><th class="num hide-s">Unit price</th></tr></thead><tbody>'
            + "".join(row(r) for r in rows) + "</tbody></table></div>")


def build(head_extra=""):
    snap = latest()
    if not snap:
        return False
    items = snap["items"]
    by_store = defaultdict(list)
    for r in items:
        by_store[r["store"]].append(r)
    cards = []
    for s, name in STORES.items():
        rs = by_store.get(s, [])
        half = sum(1 for r in rs if r.get("specialType") == "HALF_PRICE" or disc(r) >= 50)
        ds = [disc(r) for r in rs if disc(r)]
        avg = f"{round(sum(ds) / len(ds))}%" if ds else "–"
        detail = (f'<b>{half:,}</b> half price or better · avg discount {avg}' if ds
                  else 'Super Savers &amp; Lower Prices (no was-prices shown)')
        cards.append(f'<div class="card stat"><span class="st st-{s}">{name}</span>'
                     f'<b>{len(rs):,}</b> specials · {detail}</div>')
    top = sorted([r for r in items if disc(r)], key=lambda r: (-disc(r), -(r.get("wasPrice") or 0)))[:30]
    sections = []
    for key, label in DEPTS.items():
        rs = []
        for s in STORES:
            pool = [r for r in items if r.get("requestedCategory") == key and r["store"] == s]
            rs += sorted(pool, key=lambda r: (-disc(r), -(r.get("wasPrice") or 0), r["price"]))[:PER_STORE]
        if rs:
            sections.append(f'<section id="{key}"><h2>{label}</h2>{table(rs)}</section>')
    nav = " · ".join(f'<a href="#{k}">{v}</a>' for k, v in DEPTS.items())
    filters = "".join(f'<button data-f="{s}">{n}</button>' for s, n in STORES.items())
    jsonld = json.dumps({"@context": "https://schema.org", "@type": "ItemList", "name": TITLE,
                         "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": r["name"], "url": r["url"]}
                                             for i, r in enumerate(top[:10])]})
    page = f"""<!doctype html>
<html lang="en-AU"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(TITLE)}</title><meta name="description" content="{e(DESC)}">
<meta property="og:title" content="{e(TITLE)}"><meta property="og:description" content="{e(DESC)}">
<link rel="stylesheet" href="../style.css">{head_extra}
<script type="application/ld+json">{jsonld}</script>
<style>.st{{display:inline-block;font-size:11px;font-weight:700;padding:2px 7px;border-radius:999px;color:#fff;white-space:nowrap}}
.st-coles{{background:#e01a22}}.st-woolworths{{background:#178841}}.st-aldi{{background:#00005f}}
.stat b{{font-size:18px}}.stat .st{{margin-right:8px}}s{{color:var(--mut);font-size:12px}}
.filters button{{border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:999px;padding:6px 12px;margin:0 6px 8px 0;cursor:pointer}}
.filters button.on{{background:var(--acc);color:#fff;border-color:var(--acc)}}</style>
</head><body>
<header class="top"><a class="logo" href="index.html">AU Supermarket Specials</a><nav><a href="#top-deals">Top deals</a><a href="{ACTOR_URL}" target="_blank" rel="noopener">Get the data</a></nav></header>
<main>
<h1>{e(TITLE)}</h1><p class="lead">{e(DESC)}</p>
<p class="meta">Updated {e(snap["fetchedAt"].replace("T", " ")[:16])} (KST) · {len(items):,} specials across six departments · Prices from each store's public website; check the store before you shop.</p>
<div class="grid">{"".join(cards)}</div>
<section class="cta"><div><strong>Need every product and price, not just specials?</strong><p>Get the full Coles, Woolworths and Aldi catalogue with prices, was-prices, unit prices and stock as CSV, JSON or API, on any schedule.</p></div><a class="btn" href="{ACTOR_URL}" target="_blank" rel="noopener">Get the data on Apify →</a></section>
<p class="meta">Jump to: {nav}</p>
<div class="filters">{filters}</div>
<input id="q" type="search" placeholder="Search product or brand" aria-label="Search product or brand">
<section id="top-deals"><h2>Biggest discounts this week</h2>{table(top)}</section>
{"".join(sections)}
</main><footer><p>Unofficial comparison of publicly listed prices. Coles, Woolworths and Aldi are trademarks of their owners; this page is not affiliated with them. Prices, specials and availability change; confirm on the store's website.</p></footer>
<script>
let on=new Set();const q=document.getElementById('q');
function apply(){{const v=q.value.trim().toLowerCase();document.querySelectorAll('tbody tr').forEach(r=>{{
r.style.display=(!v||r.dataset.q.includes(v))&&(!on.size||on.has(r.dataset.s))?'':'none'}})}}
q.addEventListener('input',apply);
document.querySelectorAll('.filters button').forEach(b=>b.addEventListener('click',()=>{{
const s=b.dataset.f;on.has(s)?on.delete(s):on.add(s);b.classList.toggle('on');apply()}}));
</script></body></html>"""
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(page)
    return True


if __name__ == "__main__":
    print("built au" if build() else "no au data")

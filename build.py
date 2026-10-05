"""Build the static ranking site into docs/ from the snapshots in data/.

Rank change = yesterday's (latest earlier snapshot) rank minus today's rank.
"""
import glob
import html
import json
import os
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "docs")
SITE_URL = os.environ.get("SITE_URL", "https://experimory-crypto.github.io/k-ranking/").rstrip("/") + "/"
APIFY = "https://apify.com/magenta_courser/"

PAGES = {
    "daiso": dict(
        path="daiso.html", lang="ko",
        title="다이소 인기상품 순위 TOP 100 | 오늘의 다이소 베스트",
        h1="다이소 인기상품 순위 TOP 100",
        desc="다이소몰 일간 베스트 TOP 100을 매일 정리합니다. 순위 변동, 가격, 누적 판매량, 리뷰 수를 한눈에 보고 어제보다 오른 상품을 확인하세요.",
        source=("다이소몰 일간 베스트", "https://www.daisomall.co.kr/ds/rank/C105"),
        actor="daiso-ranking-scraper", actor_name="Daiso Korea Ranking Scraper"),
    "oliveyoung-kr": dict(
        path="oliveyoung.html", lang="ko",
        title="올리브영 랭킹 TOP 100 | 오늘의 올리브영 베스트",
        h1="올리브영 랭킹 TOP 100",
        desc="올리브영 온라인몰 오늘의 베스트 TOP 100을 매일 정리합니다. 순위 변동, 판매가, 할인율, 리뷰 수와 어제보다 오른 상품을 확인하세요.",
        source=("올리브영 온라인몰 랭킹", "https://www.oliveyoung.co.kr/store/main/getBestList.do"),
        actor="oliveyoung-ranking-scraper", actor_name="Olive Young Ranking Scraper"),
    "oliveyoung-global": dict(
        path="en/k-beauty-best-sellers.html", lang="en",
        title="Olive Young Global Best Sellers Top 100 | K-Beauty Ranking Today",
        h1="Olive Young Global Best Sellers Top 100",
        desc="Today's Olive Young Global best-seller Top 100 for K-beauty, updated daily: rank change, price in USD, discount, rating and review count.",
        source=("Olive Young Global best sellers", "https://global.oliveyoung.com/display/page/best-seller"),
        actor="oliveyoung-ranking-scraper", actor_name="Olive Young Ranking Scraper"),
}

T = {
    "ko": dict(rank="순위", change="변동", item="상품", price="가격", sold="누적 판매", reviews="리뷰",
               new="NEW", updated="업데이트", vs="어제 대비", risers="어제보다 많이 오른 상품",
               nochange="순위 변동은 다음 업데이트부터 표시됩니다.", search="상품명·브랜드 검색",
               cta_h="이 순위를 매일 데이터로 받기",
               cta_p="CSV·JSON·API로 매일 자동 수집하려면 Apify에서 같은 데이터를 받아보세요. 순위 변동·가격·재고까지 포함됩니다.",
               cta_btn="Apify에서 보기", source="출처",
               note="이 페이지는 공개된 랭킹 정보를 정리한 비공식 페이지입니다. 상품명과 상표는 각 권리자에게 있으며, 가격과 재고는 원본 페이지에서 확인하세요.",
               home="홈", sold_unit="개"),
    "en": dict(rank="Rank", change="Change", item="Product", price="Price", sold="Sold", reviews="Reviews",
               new="NEW", updated="Updated", vs="vs. previous day", risers="Biggest risers since yesterday",
               nochange="Rank changes appear from the next update.", search="Search product or brand",
               cta_h="Get this ranking as data, every day",
               cta_p="Need it as CSV, JSON or API on a schedule? The same data, with rank changes, prices and stock, is available on Apify.",
               cta_btn="View on Apify", source="Source",
               note="Unofficial page summarizing a publicly visible ranking. Product names and trademarks belong to their owners. Check prices and stock on the original page.",
               home="Home", sold_unit=""),
}

e = html.escape


def snapshots(key):
    files = sorted(glob.glob(os.path.join(DATA, key, "*.json")))
    load = lambda f: json.load(open(f, encoding="utf-8"))
    cur = load(files[-1])
    prev = load(files[-2]) if len(files) > 1 else None
    return cur, prev


def with_change(cur, prev):
    prank = {x["id"]: x["rank"] for x in prev["items"]} if prev else None
    for x in cur["items"]:
        if prank is None:
            x["chg"] = None
        elif x["id"] not in prank:
            x["chg"] = "new"
        else:
            x["chg"] = prank[x["id"]] - x["rank"]
    return cur["items"]


def money(v, cur):
    if v is None:
        return "–"
    if cur == "KRW":
        return f"{int(round(v)):,}원"
    return f"${v:,.2f}"


def chg_html(c, t):
    if c is None:
        return '<span class="chg">–</span>'
    if c == "new":
        return f'<span class="chg new">{t["new"]}</span>'
    if c > 0:
        return f'<span class="chg up">▲{c}</span>'
    if c < 0:
        return f'<span class="chg down">▼{-c}</span>'
    return '<span class="chg">–</span>'


def row(x, key, t):
    name = e(x["name"])
    brand = f'<span class="brand">{e(x["brand"])}</span>' if x.get("brand") else ""
    price = money(x.get("price"), x.get("currency"))
    if x.get("discount") and x["discount"] >= 1:
        price += f' <span class="disc">{round(x["discount"])}%</span>'
    if key == "daiso":
        extra = f'{x["sold"]:,}{t["sold_unit"]}' if x.get("sold") else "–"
    else:
        extra = None
    rev = f'{x["reviews"]:,}' if x.get("reviews") else "–"
    if x.get("rating"):
        rev = f'★{x["rating"]} · {rev}'
    cells = [f'<td class="rk">{x["rank"]}</td>', f'<td>{chg_html(x["chg"], t)}</td>',
             f'<td class="it">{brand}<a href="{e(x["url"])}" rel="nofollow noopener" target="_blank">{name}</a></td>',
             f'<td class="num">{price}</td>']
    if extra is not None:
        cells.append(f'<td class="num hide-s">{extra}</td>')
    cells.append(f'<td class="num hide-s">{rev}</td>')
    return f'<tr data-q="{e((x.get("brand") or "") + " " + x["name"]).lower()}">' + "".join(cells) + "</tr>"


def head(title, desc, lang, path, prefix, jsonld=""):
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{SITE_URL}{path}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website"><meta property="og:url" content="{SITE_URL}{path}">
<link rel="stylesheet" href="{prefix}style.css">{jsonld}</head><body>
<header class="top"><a class="logo" href="{prefix}index.html">오늘의 K랭킹</a>
<nav><a href="{prefix}daiso.html">다이소</a><a href="{prefix}oliveyoung.html">올리브영</a><a href="{prefix}en/k-beauty-best-sellers.html">K-Beauty (EN)</a></nav></header>
<main>"""


def foot(t, prefix):
    return f"""</main><footer><p>{e(t["note"])}</p></footer>
<script>
const q=document.getElementById('q');if(q){{q.addEventListener('input',()=>{{const v=q.value.trim().toLowerCase();
document.querySelectorAll('tbody tr').forEach(r=>{{r.style.display=!v||r.dataset.q.includes(v)?'':'none'}})}})}}
</script></body></html>"""


def build_page(key, cfg):
    t = T[cfg["lang"]]
    cur, prev = snapshots(key)
    items = with_change(cur, prev)
    prefix = "../" if "/" in cfg["path"] else ""
    top = items[:10]
    jsonld = '<script type="application/ld+json">' + json.dumps({
        "@context": "https://schema.org", "@type": "ItemList", "name": cfg["h1"],
        "itemListElement": [{"@type": "ListItem", "position": x["rank"], "name": x["name"], "url": x["url"]} for x in top]},
        ensure_ascii=False) + "</script>"
    out = [head(cfg["title"], cfg["desc"], cfg["lang"], cfg["path"], prefix, jsonld)]
    out.append(f'<h1>{e(cfg["h1"])}</h1><p class="lead">{e(cfg["desc"])}</p>')
    out.append(f'<p class="meta">{t["updated"]} {e(cur["fetchedAt"].replace("T", " ")[:16])} KST · '
               f'{t["source"]}: <a href="{e(cfg["source"][1])}" rel="nofollow noopener" target="_blank">{e(cfg["source"][0])}</a></p>')
    risers = sorted([x for x in items if isinstance(x["chg"], int) and x["chg"] > 0], key=lambda x: -x["chg"])[:5]
    if risers:
        out.append(f'<section class="card"><h2>{t["risers"]}</h2><ol class="risers">' + "".join(
            f'<li><span class="chg up">▲{x["chg"]}</span> {x["rank"]}. <a href="{e(x["url"])}" rel="nofollow noopener" target="_blank">{e(x["name"])}</a></li>'
            for x in risers) + "</ol></section>")
    elif prev is None:
        out.append(f'<p class="meta">{t["nochange"]}</p>')
    cta = (f'<section class="cta"><div><strong>{t["cta_h"]}</strong><p>{t["cta_p"]}</p></div>'
           f'<a class="btn" href="{APIFY}{cfg["actor"]}" target="_blank" rel="noopener">{t["cta_btn"]} →</a></section>')
    out.append(cta)
    cols = [t["rank"], t["change"], t["item"], t["price"]] + ([t["sold"]] if key == "daiso" else []) + [t["reviews"]]
    ths = "".join(f'<th class="{"num hide-s" if i >= 4 else ("num" if i == 3 else "")}">{c}</th>' for i, c in enumerate(cols))
    out.append(f'<input id="q" type="search" placeholder="{t["search"]}" aria-label="{t["search"]}">')
    out.append(f'<div class="tbl"><table><thead><tr>{ths}</tr></thead><tbody>' +
               "".join(row(x, key, t) for x in items) + "</tbody></table></div>")
    out.append(foot(t, prefix))
    path = os.path.join(OUT, cfg["path"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write("\n".join(out))
    return cur, items


def build_index(results):
    t = T["ko"]
    desc = "다이소·올리브영 인기 순위를 매일 정리합니다. 오늘의 TOP 100과 어제보다 오른 상품을 한 곳에서 확인하세요."
    out = [head("오늘의 K랭킹 | 다이소·올리브영 인기 순위 매일 업데이트", desc, "ko", "", "")]
    out.append(f'<h1>오늘의 K랭킹</h1><p class="lead">{e(desc)}</p><div class="grid">')
    for key in ("daiso", "oliveyoung-kr", "oliveyoung-global"):
        cfg = PAGES[key]
        cur, items = results[key]
        lis = "".join(f'<li>{chg_html(x["chg"], T[cfg["lang"]]) + " " if x["chg"] not in (None, 0) else ""}{e(x["name"])}</li>'
                      for x in items[:5])
        out.append(f'<section class="card"><h2><a href="{cfg["path"]}">{e(cfg["h1"])}</a></h2>'
                   f'<p class="meta">{t["updated"]} {e(cur["fetchedAt"].replace("T", " ")[:16])}</p><ol>{lis}</ol>'
                   f'<a href="{cfg["path"]}">TOP 100 →</a></section>')
    out.append("</div>")
    out.append(foot(t, ""))
    open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write("\n".join(out))


def build_meta():
    today = datetime.now().strftime("%Y-%m-%d")
    urls = [""] + [c["path"] for c in PAGES.values()]
    open(os.path.join(OUT, "sitemap.xml"), "w").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        "".join(f"<url><loc>{SITE_URL}{u}</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq></url>\n" for u in urls) +
        "</urlset>\n")
    open(os.path.join(OUT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n")


def main():
    os.makedirs(OUT, exist_ok=True)
    results = {k: build_page(k, c) for k, c in PAGES.items()}
    build_index(results)
    build_meta()
    css = os.path.join(HERE, "style.css")
    open(os.path.join(OUT, "style.css"), "w").write(open(css).read())
    print("built", len(results) + 1, "pages")


if __name__ == "__main__":
    main()

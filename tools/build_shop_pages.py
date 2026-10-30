"""샵별 가격 페이지 만들기: shops.json → s/<구분>/<이름>/index.html, s/index.html, sitemap.xml
원칙(소비자원 자료 조건, 2026-10-08): 원문 그대로, 공개일·원문 링크, 구성 다르면 같은 줄 비교 안 함, 최신 정보는 참가격 안내.
대행사끼리 계산한 차이·순위·"가장 싼 곳"은 만들지 않는다.
    python tools/build_shop_pages.py
"""
import datetime, html, json, pathlib, re, shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
D = json.loads((ROOT / "shops.json").read_text(encoding="utf-8"))
A = {a["n"]: a for a in D["a"]}
TODAY = datetime.date.today()
CAT = {"studio": "스튜디오", "dress": "드레스", "makeup": "메이크업"}
SITE = "https://sdmcheck.kr"
e = html.escape


def slug(n):
    return re.sub(r"[^0-9A-Za-z가-힣]+", "-", n).strip("-").lower()


def url(x):
    return f"/s/{x['c']}/{slug(x['n'])}/"


def old(p):
    try:
        return (TODAY - datetime.date.fromisoformat(p)).days > 180
    except ValueError:
        return False


CSS = """:root{--bg:#FAF4F7;--paper:#FFFFFF;--ink:#1E2032;--muted:#5E5C72;--line:#F0DCE6;--accent:#8C2B50;--accent-soft:#FADCE8;--accent-ink:#FFFFFF;--warn:#9A5E06;--warn-soft:#FBF0DD;--band:#F5E3EC;--r:20px}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#17141A;--paper:#211C24;--ink:#F1ECF2;--muted:#B3A9B8;--line:#3A3040;--accent:#E68DB1;--accent-soft:#3A2431;--accent-ink:#1A0F15;--warn:#E9B556;--warn-soft:#352915;--band:#2C2430;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:"Noto Sans KR","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;font-size:15.5px;line-height:1.6;letter-spacing:-.01em;word-break:keep-all;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}
a{color:var(--accent)}.wrap{max-width:760px;margin:0 auto;padding:20px 16px 64px;display:grid;gap:20px}
.top{display:flex;justify-content:space-between;align-items:center}.logo{font-weight:800;font-size:20px;color:var(--accent);text-decoration:none}
.pill{background:var(--accent-soft);color:var(--ink);border-radius:999px;padding:8px 14px;font-weight:700;font-size:14px;text-decoration:none}
.crumb{font-size:13px;color:var(--muted)}.crumb a{color:var(--muted)}
.band{background:var(--band);border-radius:28px;padding:24px 20px;display:grid;gap:10px}
.eyebrow{font-size:13px;font-weight:700;color:var(--muted)}h1{margin:0;font-size:clamp(26px,6vw,36px);line-height:1.25;font-weight:800;letter-spacing:-.03em}
h2{margin:0;font-size:19px;font-weight:800}.lead{margin:0;color:var(--ink)}
.card{background:var(--paper);border-radius:var(--r);padding:8px 20px}
.row{padding:16px 0;border-bottom:1px solid var(--line);display:grid;gap:4px}.row:last-child{border-bottom:0}
.rt{display:flex;justify-content:space-between;gap:12px;align-items:baseline}.rt b{font-size:15.5px}.rt span{font-size:13px;color:var(--muted);white-space:nowrap}
.pr{font-weight:700;white-space:pre-line}.alias{font-size:13px;color:var(--muted)}.src{font-size:13px}
.old{font-size:12px;font-weight:700;color:var(--warn);background:var(--warn-soft);border-radius:999px;padding:1px 8px;margin-left:6px}
.note{background:var(--warn-soft);color:var(--warn);border-radius:16px;padding:12px 16px;font-size:14px}
.cta{display:grid;gap:10px}.btn{display:block;text-align:center;background:var(--accent);color:var(--accent-ink);border-radius:999px;padding:14px 18px;font-weight:800;text-decoration:none}
.btn.sub{background:var(--accent-soft);color:var(--ink)}
ul.q{margin:0;padding-left:20px;display:grid;gap:6px}
.rel{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px}.rel a{background:var(--paper);border-radius:16px;padding:12px 14px;text-decoration:none;color:var(--ink);display:grid}.rel small{color:var(--muted)}
footer{font-size:12.5px;color:var(--muted);display:grid;gap:6px}"""

HEAD = """<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><meta name="description" content="{desc}"><link rel="canonical" href="{canon}">
<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}"><meta property="og:url" content="{canon}"><meta property="og:image" content="https://sdmcheck.kr/og-v2.png"><meta property="og:type" content="website"><meta property="og:locale" content="ko_KR">
<link rel="icon" href="/icon.png"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;800&display=swap">
<style>{css}</style>{ld}
<script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{{"token": "{cf}"}}'></script>
</head><body><div class="wrap">
<div class="top"><a class="logo" href="/">스드메체크</a><a class="pill" href="/s/">샵별 가격</a></div>"""

FOOT = """<footer><p>출처: 한국소비자원 참가격 '결혼서비스 중요정보 공개'에 각 결혼준비대행 업체가 낸 자료예요. 가격은 원문을 고치지 않고 옮겼고, 업체가 자료를 고치면 달라질 수 있어요. 성수기·요일·시간대·구성에 따라 실제 계약 금액은 다를 수 있으니 최신 정보는 <a href="https://www.price.go.kr/" rel="noopener">참가격</a>에서 확인하세요.</p>
<p>스드메체크는 특정 웨딩 업체나 대행사와 관계가 없고, 이 페이지는 광고가 아니에요. 자료 기준일 {today}.</p></footer></div></body></html>"""


def cf_token():
    m = re.search(r'data-cf-beacon=\'\{"token": "([^"]+)"', (ROOT / "index.html").read_text(encoding="utf-8"))
    return m.group(1) if m else ""


CF = cf_token()


def page(x, rel):
    c = CAT[x["c"]]
    n = x["n"]
    k = len(x["e"])
    canon = SITE + url(x)
    title = f"{n} 가격 | {c} 대행사별 공개 가격 {k}곳 (2026 참가격)"
    desc = f"{n}({c}) 가격을 서울 결혼준비대행 {k}곳이 한국소비자원 참가격에 공개한 원문 그대로 모았어요. 대행사별 공개일, 원문 링크, 상담 때 물어볼 것."
    rows = []
    any_old = False
    for en in sorted(x["e"], key=lambda en: A.get(en["a"], {}).get("p", ""), reverse=True):
        a = A.get(en["a"], {})
        p = a.get("p", "")
        o = old(p)
        any_old |= o
        names = sorted(set(en.get("n", [])) - {n})
        rows.append(
            f'<div class="row"><div class="rt"><b>{e(en["a"])}</b><span>공개일 {e(p)}{"<span class=old>6개월 넘음</span>" if o else ""}</span></div>'
            f'<div class="pr">{e(chr(10).join(en["l"]))}</div>'
            + (f'<div class="alias">대행사 자료 표기: {e(", ".join(names))}</div>' if names else "")
            + (f'<a class="src" href="{e(a["u"])}" rel="noopener nofollow" target="_blank">참가격 원문 표 ↗</a>' if a.get("u") else "")
            + "</div>")
    ld = json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "스드메체크", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": "샵별 가격", "item": SITE + "/s/"},
        {"@type": "ListItem", "position": 3, "name": f"{n} 가격", "item": canon}]}, ensure_ascii=False)
    relh = "".join(f'<a href="{url(r)}"><b>{e(r["n"])}</b><small>대행사 {len(r["e"])}곳</small></a>' for r in rel)
    body = f"""
<nav class="crumb"><a href="/">스드메체크</a> › <a href="/s/">샵별 가격</a> › {c}</nav>
<section class="band"><div class="eyebrow">{c} · 대행사 {k}곳 공개 · 원문 그대로</div><h1>{e(n)} 가격</h1>
<p class="lead">서울 결혼준비대행 {k}곳이 한국소비자원 참가격에 공개한 {e(n)} 가격이에요. 최근 공개된 순서로 놓았어요.</p></section>
<section class="card" aria-label="대행사별 공개 가격">{''.join(rows)}</section>
{'<p class="note">공개일이 6개월 넘은 자료가 있어요. 지금 상담 가격과 다를 수 있으니 최근 공개된 줄을 기준으로 물어보세요.</p>' if any_old else ''}
<p class="note">대행사마다 구성(포함 항목, 횟수, 직급, 시간대)이 달라요. 가격을 나란히 비교하기 전에 원문 표에서 구성이 같은지 먼저 보세요.</p>
<section class="card" style="padding:18px 20px;display:grid;gap:10px"><h2>상담 때 물어볼 것</h2><ul class="q">
<li>이 가격에 무엇이 들어 있나요? (촬영 시간·앨범·원본, 드레스 벌수, 메이크업 직급·횟수)</li>
<li>최근 공개된 가격 기준으로는 얼마인가요?</li>
<li>원본·헬퍼비·피팅비·얼리스타트가 포함인지 계약서에 적어 주실 수 있나요?</li></ul></section>
<section class="cta"><a class="btn" href="/#checker">이 샵 견적 받았어요 · 총액 넣고 무료 검토</a><a class="btn sub" href="/">다른 샵 이름으로 찾기</a></section>
<section style="display:grid;gap:10px"><h2>같이 많이 보는 {c}</h2><div class="rel">{relh}</div></section>"""
    out = ROOT / url(x).strip("/")
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(
        HEAD.format(title=e(title), desc=e(desc), canon=canon, css=CSS, cf=CF,
                    ld=f'<script type="application/ld+json">{ld}</script>') + body + FOOT.format(today=TODAY.isoformat()),
        encoding="utf-8")


def main():
    shutil.rmtree(ROOT / "s", ignore_errors=True)
    V = D["v"]
    by = {c: sorted([x for x in V if x["c"] == c], key=lambda x: (-len(x["e"]), x["n"])) for c in CAT}
    for c, xs in by.items():
        for i, x in enumerate(xs):
            rel = [r for r in xs if r is not x][:6] if i >= 6 else [r for r in xs[:7] if r is not x][:6]
            page(x, rel)
    # 목록 페이지
    secs = []
    for c, xs in by.items():
        li = "".join(f'<a href="{url(x)}"><b>{e(x["n"])}</b><small>대행사 {len(x["e"])}곳</small></a>' for x in xs)
        secs.append(f'<section style="display:grid;gap:10px"><h2 id="{c}">{CAT[c]} {len(xs)}곳</h2><div class="rel">{li}</div></section>')
    canon = SITE + "/s/"
    title = "샵별 스드메 가격 | 스튜디오·드레스·메이크업 대행사별 공개 가격 (2026 참가격)"
    desc = f"서울 결혼준비대행 업체들이 한국소비자원 참가격에 공개한 스튜디오·드레스·메이크업 {len(V)}곳의 가격을 샵별로 모았어요. 원문 그대로, 공개일과 원문 링크 포함."
    body = f"""<nav class="crumb"><a href="/">스드메체크</a> › 샵별 가격</nav>
<section class="band"><div class="eyebrow">대행사 2곳 이상에 올라온 서울 업체 {len(V)}곳</div><h1>샵별 스드메 가격</h1>
<p class="lead">샵 이름을 누르면 대행사마다 한국소비자원에 공개한 가격을 원문 그대로 볼 수 있어요. <a href="#studio">스튜디오</a> · <a href="#dress">드레스</a> · <a href="#makeup">메이크업</a></p></section>
{''.join(secs)}"""
    (ROOT / "s").mkdir(exist_ok=True)
    (ROOT / "s" / "index.html").write_text(
        HEAD.format(title=e(title), desc=e(desc), canon=canon, css=CSS, cf=CF, ld="") + body + FOOT.format(today=TODAY.isoformat()),
        encoding="utf-8")
    # 사이트맵
    t = TODAY.isoformat()
    urls = [SITE + "/", SITE + "/compare.html", SITE + "/s/"] + [SITE + url(x) for x in V]
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc><lastmod>{t}</lastmod></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
    print("샵 페이지", len(V), "개 + 목록 + sitemap", len(urls))


if __name__ == "__main__":
    main()

import json, re, sys, time, html, urllib.request
from concurrent.futures import ThreadPoolExecutor
URLS, OUT = sys.argv[1], sys.argv[2]
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
def get(url):
    for i in range(3):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40).read().decode("utf-8", "ignore")
        except Exception: time.sleep(3)
def clean(s): return html.unescape(re.sub(r"<[^>]+>", " ", s)).strip()
def work(u):
    h = get(u) or ""
    spec = {}
    parts = re.split(r'<div class="tech-specs_accord[ "]', h)
    for p in parts[1:]:
        m = re.search(r'aria-label="([^"]+)"', p)
        rows = re.findall(r'<div class="tech-specs_accord__row"><span>(.*?)</span><span>(.*?)</span>', p, re.S)
        if m and rows: spec[html.unescape(m.group(1))] = {clean(a): clean(b) for a, b in rows}
    title = re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S)
    img = re.search(r'<meta property="og:image" content="([^"]+)"', h)
    desc = re.search(r'<meta name="description" content="([^"]*)"', h)
    return dict(url=u, title=clean(title.group(1)) if title else None, image=img.group(1) if img else None, desc=html.unescape(desc.group(1)) if desc else None, spec=spec)
urls = open(URLS).read().split()
urls = [u for u in urls if not u.endswith("/compare")]
with ThreadPoolExecutor(4) as ex: res = list(ex.map(work, urls))
print("with spec", sum(1 for r in res if r["spec"]), "of", len(res), file=sys.stderr)
json.dump(res, open(OUT, "w"))

import json, re, sys, time, html, urllib.request
from concurrent.futures import ThreadPoolExecutor
SL, OUT = sys.argv[1], sys.argv[2]
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
def get(url):
    for i in range(3):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40).read().decode("utf-8", "ignore")
        except Exception: time.sleep(3)
dec = json.JSONDecoder()
def work(s):
    h = get("https://www.hisense-usa.com/product-page/" + s) or ""
    out = dict(slug=s)
    i = h.find('"slug":"%s"' % s)
    j = h.rfind('"description":"', 0, i) if i > 0 else -1
    if j > 0:
        try: out["description"] = html.unescape(re.sub(r"<[^>]+>", " ", dec.raw_decode(h, j + 14)[0]))
        except Exception: pass
    for k, pat in [("name", r'"name":"((?:[^"\\]|\\.)*)","sku":"([A-Z0-9-]+)"')]:
        m = re.search(pat, h[max(0, j - 200000):i + 50000] if j > 0 else h)
    t = re.search(r'<meta property="og:title" content="([^"]+)"', h); out["title"] = html.unescape(t.group(1)) if t else None
    im = re.search(r'<meta property="og:image" content="([^"]+)"', h); out["image"] = im.group(1) if im else None
    md = re.search(r'<meta name="description" content="([^"]*)"', h); out["meta"] = html.unescape(md.group(1)) if md else None
    rt = re.search(r'"richTextContent".*?"text":"((?:[^"\\]|\\.){80,})"', h); out["rich"] = json.loads('"' + rt.group(1) + '"') if rt else None
    return out
slugs = json.load(open(SL))
with ThreadPoolExecutor(4) as ex: res = list(ex.map(work, slugs))
print(sum(1 for r in res if r.get("description")), len(res), file=sys.stderr)
json.dump(res, open(OUT, "w"))

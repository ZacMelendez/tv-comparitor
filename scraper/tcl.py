import json, re, sys, time, html, urllib.request, glob
from concurrent.futures import ThreadPoolExecutor
RAW, OUT = sys.argv[1], sys.argv[2]
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
def get(url):
    for i in range(3):
        try: return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40).read().decode("utf-8", "ignore")
        except Exception: time.sleep(3)
prods = {}
for c in ["smart-tv", "tv-home-theater", "tv-for-sale", "televisions", "all-tvs", "tvs", "mini-led-tvs", "qled-tvs"]:
    t = get(f"https://us.tcl.com/collections/{c}/products.json?limit=250")
    try: ps = json.loads(t)["products"]
    except Exception: continue
    for p in ps: prods[p["handle"]] = p
tvs = {h: p for h, p in prods.items() if ("Televisions" in p["tags"] or "TV" in p["product_type"].upper() or " TV" in p["title"]) and not re.search(r"monitor|soundbar|sound bar|mount|remote|projector|cable", p["title"], re.I)}
print("products", len(prods), "tvs", len(tvs), file=sys.stderr)
def clean(s): return html.unescape(re.sub(r"<[^>]+>", " ", s)).strip()
def work(item):
    h, p = item
    page = get(f"https://us.tcl.com/products/{h}") or ""
    panels = {}
    def parse(body):
        spec = {}
        for box in re.finditer(r'specifications_one">\s*<div class="h3">(.*?)</div>.*?specifications_two">(.*?)</div>\s*</div>\s*(?=<div class="specifications_box|</div>|$)', body, re.S):
            cells = [clean(x) for x in re.findall(r'<div class="specifications_time">(.*?)</div>', box.group(2) + "</div>", re.S)]
            spec[clean(box.group(1))] = dict(zip(cells[0::2], cells[1::2]))
        return spec
    for m in re.finditer(r'variant-specs-panel"\s+data-variant-id="(\d+)"[^>]*>(.*?)(?=<div class="variant-specs-panel"|</section|<script|$)', page, re.S):
        vid, body = m.group(1), m.group(2)
        spec = {}
        for box in re.finditer(r'specifications_one">\s*<div class="h3">(.*?)</div>.*?specifications_two">(.*?)</div>\s*</div>\s*(?=<div class="specifications_box|</div>|$)', body, re.S):
            cells = [clean(x) for x in re.findall(r'<div class="specifications_time">(.*?)</div>', box.group(2) + "</div>", re.S)]
            grp = clean(box.group(1))
            spec[grp] = dict(zip(cells[0::2], cells[1::2]))
        panels[vid] = spec
    if not panels and p["variants"]:
        sp = parse(page)
        if sp: panels[str(p["variants"][0]["id"])] = sp
    return dict(handle=h, title=p["title"], tags=p["tags"], variants=[dict(id=str(v["id"]), title=v["title"], sku=v["sku"], price=v["price"], compare=v.get("compare_at_price")) for v in p["variants"]], image=(p.get("images") or [{}])[0].get("src"), panels=panels)
with ThreadPoolExecutor(5) as ex: res = list(ex.map(work, tvs.items()))
print("with panels", sum(1 for r in res if r["panels"]), file=sys.stderr)
json.dump(res, open(OUT, "w"))

import json, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
LIST, OUT = sys.argv[1], sys.argv[2]
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
def get(url):
    for i in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40).read().decode("utf-8", "ignore")
        except Exception: time.sleep(3)
def specs_from(h):
    h = h.replace('\\"', '"')
    out = {}
    for g in re.finditer(r'"specGroupOrder":\d+,"subtitle":"([^"]*)","tableData":\[(.*?)\]\}', h):
        grp = g.group(1)
        for t in re.finditer(r'\{"attributeOrder":\d+,"description":"((?:[^"\\]|\\.)*)","term":"((?:[^"\\]|\\.)*)"\}', g.group(2)):
            out.setdefault(grp, {})[t.group(2)] = t.group(1)
    return out
rows = [r["raw"] for r in json.load(open(LIST))["results"]]
def work(r):
    h = get("https://www.lg.com" + r["ec_uri_link"])
    s = specs_from(h or "")
    return dict(r, specs=s)
with ThreadPoolExecutor(6) as ex:
    res = list(ex.map(work, rows))
print("with specs", sum(1 for r in res if r["specs"]), "of", len(res), file=sys.stderr)
json.dump(res, open(OUT, "w"))

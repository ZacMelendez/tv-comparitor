import json, sys, time
from concurrent.futures import ThreadPoolExecutor
sys.argv = [sys.argv[0], "x", "/dev/null"] + sys.argv[1:]
src = open(sys.argv[0].replace("lg_fill.py", "lg.py")).read().split("rows =")[0]
exec(src)
P = sys.argv[3]
d = json.load(open(P))
def fix(r):
    if r["specs"]: return r
    for i in range(2):
        h = get("https://www.lg.com" + r["ec_uri_link"])
        s = specs_from(h or "")
        if s: r["specs"] = s; return r
        time.sleep(2)
    return r
with ThreadPoolExecutor(3) as ex: d = list(ex.map(fix, d))
print("with specs", sum(1 for r in d if r["specs"]), "of", len(d), file=sys.stderr)
json.dump(d, open(P, "w"))

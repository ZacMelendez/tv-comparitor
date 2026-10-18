import json, sys, os, subprocess
D, OUTDIR = sys.argv[1], sys.argv[2]
rows = json.load(open(os.path.join(D, "tvs.json")))
import re
raw = {r["id"]: r.pop("raw") for r in rows}
for r in rows:
    txt = json.dumps(raw[r["id"]]) + " " + (r.get("name") or "")
    r["antiGlare"] = bool(re.search(r"anti[- ]?(reflect|glare)|glare[- ]?free|matte display|low reflection|x-anti reflection|obsidian", txt, re.I))
for r in rows:
    for k in list(r):
        if r[k] is None or r[k] is False or r[k] == "": del r[k]
meta = {"scraped": "Oct 17, 2026", "sources": {
    "Samsung": {"how": "samsung.com/us product finder + per-SKU spec API"},
    "LG": {"how": "lg.com/us catalog index + spec table on each product page"},
    "Sony": {"how": "sony.co.uk BRAVIA spec pages (US store blocks automated access)"},
    "TCL": {"how": "us.tcl.com store catalog + per-size spec panels"},
    "Hisense": {"how": "hisense-usa.com product pages; spec tables where published, otherwise product descriptions"},
    "Vizio": {"how": "vizio.com product sitemap + tech-spec tables"}}}
os.makedirs(OUTDIR, exist_ok=True)
json.dump({"meta": meta, "rows": rows}, open(os.path.join(OUTDIR, "tvs.json"), "w"), separators=(",", ":"))
json.dump(raw, open(os.path.join(OUTDIR, "raw.json"), "w"), separators=(",", ":"))
print(len(rows), os.path.getsize(os.path.join(OUTDIR, "tvs.json")) // 1024, "KB", os.path.getsize(os.path.join(OUTDIR, "raw.json")) // 1024, "KB")

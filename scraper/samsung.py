import json, re, sys, time, urllib.request, urllib.parse, os
OUT = sys.argv[1]
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
def get(url, data=None, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Origin": "https://www.samsung.com", "Referer": "https://www.samsung.com/us/tvs/all-tvs/"})
            return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
        except Exception as e:
            time.sleep(2)
    return None
fams = {}
for sort in ["newest", "priceasc", "pricedesc", "mostclicked", "ratings", "recommended", ""]:
    for s in range(0, 45):
        body = urllib.parse.urlencode(dict(clientCode="b2c", clientName="scom_pf", firstSearchYN="true", countryCode="us", storeID="us", startIndex=s, requestCount=10, category_code="04010000", filters="[]", sort=sort)).encode()
        t = get("https://sribsrch.ecom.samsung.com/estoresearch-api/v1/scom/us/pf_search", body)
        if not t: continue
        d = json.loads(t)
        rs = d.get("searchResults", [])
        if not rs: break
        for r in rs:
            fams.setdefault(r.get("group_id") or r["modelCode"], r)
    print(sort, len(fams), file=sys.stderr)
    if len(fams) >= 43: break
print("families", len(fams), file=sys.stderr)
out = []
for gid, r in fams.items():
    url = "https://www.samsung.com" + r["pdpURL"].rstrip("/") + "/"
    h = get(url)
    m = re.search(r'"groupId":"(\d+)"', h or "")
    if not m:
        print("no groupId", url, file=sys.stderr); continue
    sp = get(f"https://www.samsung.com/us/gapi/v1/bridge/cacheable/bridge-data?data_type=Specs&store_type=B2C&group_id={m.group(1)}&version=v2")
    try:
        specs = json.loads(sp)
        specs = specs["Specs"] if isinstance(specs, dict) else specs
    except Exception: print("no specs", url, file=sys.stderr); continue
    prices = {}
    for g in r.get("groupedProductList", []) or []:
        prices[g["modelCode"]] = dict(msrp=g.get("msrp_price"), sale=g.get("sale_price"), url=g.get("pdpURL"), title=g.get("productShortTitle"), rating=g.get("reviewRating"), reviews=g.get("numberOfReviews"))
    out.append(dict(family=r, specs=specs, prices=prices, pdp=url))
    print(len(out), r["familyMktName"][:60], len(specs), file=sys.stderr)
    time.sleep(0.5)
json.dump(out, open(OUT, "w"))

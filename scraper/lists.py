"""Build the product lists the per-brand scrapers start from.

Usage: python3 lists.py <data_dir>
Writes: lg_list.json, vizio_urls.txt, hisense_slugs.json
"""
import json, os, re, sys, time, urllib.request

D = sys.argv[1]
os.makedirs(D, exist_ok=True)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"

def get(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})})
    return urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore")

# LG: lg.com/us uses a Coveo index; the site hands out a short-lived public search token.
tok = json.loads(get("https://www.lg.com/us/plp/api/coveo/v1/getAccessToken"))["token"]
q = {"aq": '@source=="PDS Product Catalog" @ec_category=="TVs" @ec_model_status_code==ACTIVE', "numberOfResults": 1000,
     "fieldsToInclude": ["ec_model_id", "ec_user_friendly_name", "ec_uri_link", "ec_size", "ec_msrp", "ec_final_price", "ec_category",
                         "ec_group_id", "ec_s_rating", "ec_participant_count", "ec_medium_image_addr", "ec_model_display_name", "ec_model_type", "ec_creation_date"]}
lg = get("https://platform.cloud.coveo.com/rest/search/v2?organizationId=lgelectronicsusaproductionh9cyypz4",
         json.dumps(q).encode(), {"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
open(os.path.join(D, "lg_list.json"), "w").write(lg)
print("LG", len(json.loads(lg)["results"]), file=sys.stderr)

# Vizio: every TV page is in the products sitemap.
sm = get("https://www.vizio.com/products-sitemap.xml")
urls = sorted(set(re.findall(r"https://www\.vizio\.com/en/tv/[^<]+", sm)))
open(os.path.join(D, "vizio_urls.txt"), "w").write("\n".join(urls))
print("Vizio", len(urls), file=sys.stderr)

# Hisense: product links from the paginated TV category.
slugs = set()
for p in range(1, 11):
    h = get(f"https://www.hisense-usa.com/category/televisions?page={p}")
    found = set(re.findall(r"product-page/([a-z0-9-]+)", h))
    if not found - slugs and p > 1: break
    slugs |= found
    time.sleep(1)
skip = r"air-products|dehumid|soundbar|sound-bar|projector|laser|refriger|washer|dryer|range|dishwasher|microwave|freezer|subwoofer|speaker|roamview"
slugs = sorted(s for s in slugs if not re.search(skip, s))
json.dump(slugs, open(os.path.join(D, "hisense_slugs.json"), "w"))
print("Hisense", len(slugs), file=sys.stderr)

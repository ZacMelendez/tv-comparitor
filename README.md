# TV Spec Comparator

A single-page tool for choosing a TV, built on spec data collected from six manufacturers' own websites (842 models as of Oct 17, 2026).

- **Compare**: filter the full catalog by brand, panel type, size, refresh rate, HDR formats, gaming features, platform and price. Sizes of the same model are grouped into one row. Pick up to four TVs to see their specs side by side, with the best value in each row highlighted.
- **Find my TV**: set how much you care about bright-room viewing, dark-room movies, gaming, sports, sound, smart features, price per inch, size for your seating distance and model year. Every TV gets a 0–100 score with a per-criterion breakdown.
- **Size on your wall**: drag TVs and furniture (sofa, console, door, a 5′9″ person…) on a scale drawing of your wall to see what a 65″ vs 85″ actually looks like.

The app is plain HTML/CSS/JS with no build step. It loads `tvs.json` (normalized fields) and lazily loads `raw.json` (each manufacturer's full spec sheet) for the detail and compare views.

```bash
python3 -m http.server 8000   # then open http://localhost:8000
```

## Data pipeline

Everything in `scraper/` uses only the Python standard library.

| Brand   | Source | How |
|---------|--------|-----|
| Samsung | samsung.com/us | Product-finder search API for the lineup, then the per-SKU spec endpoint the product pages use |
| LG      | lg.com/us | Public Coveo catalog index for the model list, spec table embedded in each product page |
| TCL     | us.tcl.com | Shopify `products.json` collections, per-size spec panels on each product page |
| Vizio   | vizio.com | Product sitemap, server-rendered tech-spec tables |
| Hisense | hisense-usa.com | Category pages for the list; spec tables are rendered client-side, so they're read in a browser (`scraper/browser/hisense.js`) |
| Sony    | sony.co.uk | Sony's US store refuses scripted requests, so specs come from Sony UK's BRAVIA spec pages (`scraper/browser/sony.js`) |

```bash
cd scraper
python3 lists.py ../data                                   # LG catalog, Vizio sitemap, Hisense product list
python3 samsung.py ../data/samsung_raw.json
python3 lg.py ../data/lg_list.json ../data/lg_raw.json
python3 lg_fill.py ../data/lg_raw.json                     # retry pages that were rate-limited
python3 tcl.py - ../data/tcl_raw.json
python3 vizio.py ../data/vizio_urls.txt ../data/vizio_raw.json
python3 hisense_desc.py ../data/hisense_slugs.json ../data/hisense_desc.json
# Sony and Hisense spec tables: run scraper/browser/*.js in the browser console and save the output
# as data/sony_raw.json and data/hisense_specs.json
python3 normalize.py ../data ../data/tvs.json              # map every brand onto one schema
python3 build.py ../data ..                                # write tvs.json + raw.json for the app
```

`normalize.py` maps each brand's spec vocabulary onto ~35 common fields (panel type, native/max refresh, HDR formats, HDMI 2.1 ports, audio power, etc.), keeping the original spec sheet alongside. Hisense publishes a spec table on only some sizes of a series, so those specs are shared with sibling sizes (excluding size-specific fields like weight and dimensions).

## Caveats

- Prices are what each brand's own store listed on the scrape date. Sony, Hisense and Vizio mostly sell through retailers, so their rows have no price.
- Brightness, dimming zones and speaker wattage are manufacturer claims, not measurements.
- Spec coverage varies by brand; the scoring tab leaves out any criterion a TV has no data for and deducts a few points for the uncertainty.
- Scrapers were written against the sites as they were in October 2026 and will need updating when the sites change. They make requests at low concurrency; please keep it that way if you rerun them.

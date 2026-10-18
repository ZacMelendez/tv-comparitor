# TV Spec Comparator

A TV buyer's guide built on spec data collected from six manufacturers' own websites (842 models as of Oct 17, 2026). The page runs in the order a TV actually gets bought:

1. **Measure the room**: set your seating distance and wall size. A to-scale drawing shows the comfortable size range next to furniture you can drag around. Or switch to **Your photo**: upload a picture of the wall, drag four dots onto the corners of a rectangle on it (the wall itself works best), enter its width, and TVs are drawn at true size in the photo's perspective. The photo never leaves the browser.
2. **Say what matters**: weight nine questions (bright room, films in the dark, gaming, sport, speakers, casting, price, size fit, model year) and set hard limits.
3. **Read the shortlist**: every TV scored 0–100 against your weights, with the criteria it beats the field on and where it trails.
4. **Compare head to head**: two to four picks side by side, normalised specs first, then each maker's own spec sheet.

Behind the stages sits **the catalogue**: every set, filterable, with sizes of the same model grouped into one row.

Design: a dark app shell in the spirit of Linear: a side rail of steps with live counts, one view at a time, keyboard shortcuts (`1`–`4`, `C`, `/`), a floating compare bar and a peek panel for spec sheets. Geist and Geist Mono on cool near-black. Tokens live in `tokens.css`, mirrored inline at the top of `index.html`.

**How the photo placer works.** The four marked corners and the known width define a homography between the wall plane (in inches) and the photo; TVs are placed in wall-plane coordinates and projected back into the image. The rectangle's height is estimated from the perspective (after Zhang & He's whiteboard-scanning method), assuming a typical phone main lens; in synthetic tests that's within about 7% for wall-sized rectangles even with sloppy clicks. A measured height can be typed in for exact scale.

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

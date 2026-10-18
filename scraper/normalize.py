"""Merge each brand's raw scrape into one normalized dataset.

Output: list of rows (one per model/size) with common fields + `raw` (grouped original specs).
"""
import json, re, sys, os, html

D = sys.argv[1]  # data dir
OUT = sys.argv[2]

def load(name):
    p = os.path.join(D, name)
    return json.load(open(p)) if os.path.exists(p) else None

def num(s):
    m = re.search(r"(\d+(?:\.\d+)?)", s or "")
    return float(m.group(1)) if m else None

def flat(grouped):
    out = {}
    for g, o in (grouped or {}).items():
        for k, v in (o or {}).items():
            if k and v not in (None, ""):
                out[f"{g} > {k}"] = str(v)
    return out

def pick(f, *pats, exclude=None):
    """First value whose label matches any regex (in order of patterns)."""
    for p in pats:
        r = re.compile(p, re.I)
        for k, v in f.items():
            lab = k.split(" > ", 1)[-1]
            if r.search(lab) and not (exclude and re.search(exclude, lab, re.I)):
                if v.strip() not in ("-", "", "N/A"):
                    return v
    return None

YES = re.compile(r"^\s*(yes|y|supported|built[- ]?in|included)\b", re.I)
NO = re.compile(r"^\s*(no|n|none|not supported|-)\s*$", re.I)

def yn(v):
    if v is None: return None
    if NO.match(v): return False
    return True

def has(text, pat):
    return bool(re.search(pat, text, re.I))

def tech_of(text, title):
    t = (title or "") + " | " + text
    if re.search(r"micro ?led(?! ?rgb)|microled|\bMICRO LED\b", t, re.I) and not re.search(r"micro ?rgb", t, re.I):
        if re.search(r"micro ?led", title or "", re.I) or re.search(r"\bMNA\d|\b\d+MX\b|136MX|MS1", t):
            return "MicroLED"
    if re.search(r"micro ?rgb|rgb[- ]?mini ?led|rgb led|true rgb|rgb miniled|rgb-mini|RGB MiniLED", t, re.I):
        return "RGB Mini-LED"
    if re.search(r"\boled\b", title or "", re.I) or re.search(r"(display type|product type|panel)[^|]*oled", t, re.I) or re.search(r"self[- ]illuminating", t, re.I):
        return "OLED"
    if re.search(r"mini[- ]?led|miniled|neo ?qled|qd-mini|sqd-mini|qned evo mini|quantum mini", t, re.I):
        return "Mini-LED"
    if re.search(r"\bqled\b|quantum dot|\bqned\b|quantum color|hi-qled|nanocell|\bULED\b", t, re.I):
        return "QLED / QNED"
    return "LED"

def res_of(text, title):
    t = (title or "") + " | " + text
    if re.search(r"\b8K\b|7680", t): return "8K"
    if re.search(r"\b4K\b|3840|UHD|2160", t, re.I): return "4K"
    if re.search(r"1080|full ?hd|\bFHD\b", t, re.I): return "1080p"
    if re.search(r"720|\bHD\b", t, re.I): return "720p"
    return None

def os_of(text, brand):
    for pat, name in [(r"google tv|android tv", "Google TV"), (r"roku", "Roku TV"), (r"fire ?tv", "Fire TV"), (r"vidaa", "VIDAA"),
                      (r"webos", "webOS"), (r"tizen", "Tizen"), (r"vizio ?os|smartcast", "VIZIO OS")]:
        if re.search(pat, text, re.I): return name
    return {"Samsung": "Tizen", "LG": "webOS", "Vizio": "VIZIO OS"}.get(brand)

def hz_list(s):
    return [int(x) for x in re.findall(r"(\d{2,3})\s*-?\s*hz", s or "", re.I) if 24 <= int(x) <= 500]

def year_of(title, f, model):
    for src in [pick(f, r"^model year$"), title]:
        m = re.search(r"\b(20[12]\d)\b", src or "")
        if m: return int(m.group(1))
    return None

def lbs(s):
    if not s: return None
    v = num(s)
    if v is None: return None
    if re.search(r"kg", s, re.I) and not re.search(r"lb", s, re.I): v = v * 2.20462
    return round(v, 1)

def dims_in(s):
    if not s: return None
    m = re.findall(r"(\d+(?:\.\d+)?)", s)
    if len(m) < 3: return None
    a = [float(x) for x in m[:3]]
    if re.search(r"\bcm\b", s, re.I) and not re.search(r'inch|"|\bin\b', s, re.I): a = [x / 2.54 for x in a]
    elif re.search(r"\bmm\b", s, re.I) and not re.search(r'inch|"|\bin\b', s, re.I): a = [x / 25.4 for x in a]
    return " × ".join(f"{x:.1f}" for x in a) + " in"

def common(row, f, text):
    """Derive the shared fields from a flattened spec dict + blob text."""
    title = row.get("name") or ""
    t = text
    row["tech"] = tech_of(t, title)
    row["resolution"] = res_of(pick(f, r"resolution") or "", title) or res_of(t, title)
    rr = pick(f, r"^(panel )?refresh rate$|panel refresh|native refresh|^refresh", exclude=r"variable|vrr")
    hzs = hz_list(rr)
    vrr_s = pick(f, r"variable refresh|\bvrr\b")
    allhz = hzs + hz_list(vrr_s) + hz_list(pick(f, r"hdmi maximum input rate"))
    if hzs:
        row["refresh"] = min(hzs) if re.search(r"up to|vrr", rr or "", re.I) and len(hzs) > 1 else hzs[0]
    else:
        m = re.search(r"(\d{2,3})\s*hz (native|refresh)", t + " " + title, re.I)
        row["refresh"] = int(m.group(1)) if m else None
    mx = max(allhz) if allhz else None
    if not mx:
        m = re.findall(r"(?:up to|vrr|game mode ultra|variable refresh rate of[^.]*?to)\s*(\d{2,3})\s*hz", t, re.I)
        mx = max(int(x) for x in m) if m else None
    row["refreshMax"] = max(filter(None, [mx, row["refresh"]]), default=None)
    hdr = " ".join(filter(None, [pick(f, r"^hdr|high dynamic range|hdr.*compat|hdr format"), pick(f, r"dolby vision"), pick(f, r"hdr ?10\+")]))
    blob = hdr + " | " + t
    dv = pick(f, r"^dolby vision$")
    row["dolbyVision"] = (yn(dv) if dv is not None else has(blob, r"dolby\W*vis?i?on")) and row["brand"] != "Samsung"
    row["hdr10plus"] = has(blob, r"hdr ?10 ?\+|hdr10 ?plus|hdr 10 plus")
    row["hlg"] = has(blob, r"\bhlg\b|hybrid log")
    row["imax"] = has(t, r"imax enhanced")
    row["filmmaker"] = has(t, r"filmmaker")
    hd = pick(f, r"^hdmi( inputs?( total)?)?$|^hdmi ports?$|^ports$|hdmi input", exclude=r"arc|cec|rate|sync|signal|format|pc")
    n = None
    if hd:
        m = re.match(r"\s*(\d)\b", hd) or re.search(r"(\d)\s*(?:x\s*)?(?:hdmi|ea|\()", hd, re.I)
        n = int(m.group(1)) if m else None
    if n is None:
        m = re.search(r"(\d)\s*(?:x\s*)?HDMI", t)
        n = int(m.group(1)) if m else None
    row["hdmi"] = n
    # HDMI 2.1 / 4K@120 capable ports
    h21 = None
    for v in filter(None, [pick(f, r"hdmi maximum input rate"), pick(f, r"hdmi input"), pick(f, r"^hdmi$"), pick(f, r"hdmi.*2\.1"), pick(f, r"^type$"), pick(f, r"variable refresh"), hd]):
        m = re.search(r"for HDMI\s*([\d/ ,]+)", v, re.I) or re.search(r"\(([\d/]+)\)", v)
        if m and re.search(r"1[2-9]\d|2\d\d|2\.1|vrr", v, re.I):
            h21 = len(re.findall(r"\d", m.group(1))); break
        m = re.search(r"(\d)\s*(?:x\s*)?(?:hdmi )?2\.1|\((\d) port\)|(\d) ?x ?HDMI 2\.1|v2\.1", v, re.I)
        if m:
            g = next((x for x in m.groups() if x), None)
            if g: h21 = int(g); break
            if re.search(r"x(\d)\)?\(v2\.1", v): h21 = int(re.search(r"x(\d)\)?\(v2\.1", v).group(1)); break
    if h21 is None and (row.get("refreshMax") or 0) >= 100 and has(t, r"hdmi ?2\.1|4k ?120|4k@120"):
        h21 = None  # capable but count unknown
    row["hdmi21"] = h21
    row["earc"] = has(t, r"\bearc\b")
    row["vrr"] = bool(vrr_s and yn(vrr_s)) or has(t, r"\bvrr\b|variable refresh")
    row["allm"] = has(t, r"\ballm\b|auto low latency|auto game mode")
    row["freesync"] = has(t, r"freesync")
    row["gsync"] = has(t, r"g-?sync")
    row["os"] = os_of(" ".join(filter(None, [pick(f, r"operating system|smart platform|smart tv|type of tv|^os\b"), title, t])), row["brand"])
    aw = pick(f, r"^sound output", r"^audio power output", r"audio output power", r"audio power", r"^audio output$", r"output power", r"^speakers$", exclude=r"simultaneous|headphone")
    w = None
    if aw:
        ws = re.findall(r"(\d+(?:\.\d+)?)\s*w", aw, re.I)
        xs = re.findall(r"(\d+)\s*w\s*x\s*(\d)", aw, re.I)
        if xs: w = sum(float(a) * int(b) for a, b in xs)
        elif ws and "+" in aw: w = sum(float(x) for x in ws)
        elif ws: w = max(float(x) for x in ws)
    row["audioW"] = w
    ch = " ".join(filter(None, [pick(f, r"speaker (type|system)"), pick(f, r"channel"), pick(f, r"surround sound")]))
    m = re.search(r"(\d\.\d(?:\.\d)?)\s*(?:ch|channel)?", ch, re.I) or re.search(r"(\d)\s*ch\b", ch, re.I) or re.search(r"(\d\.\d\.\d)\s*(?:ch|channel|multi)", t, re.I)
    row["channels"] = m.group(1) if m else None
    row["atmos"] = has(t, r"dolby\W*atmos")
    row["dtsx"] = has(t, r"dts:? ?x|dts virtual")
    wifi = pick(f, r"wi-?fi|wireless") or ""
    m = re.search(r"wi-?fi ?(7|6e|6|5)\b|802\.11 ?(be|ax|ac)", wifi + " " + t, re.I)
    row["wifi"] = ("Wi-Fi " + {"be": "7", "ax": "6", "ac": "5"}.get((m.group(2) or "").lower(), (m.group(1) or "").upper())) if m else None
    bt = pick(f, r"bluetooth")
    row["bluetooth"] = yn(bt) if bt else has(t, r"bluetooth")
    row["atsc3"] = has(t, r"atsc ?3\.0|nextgen tv")
    row["airplay"] = has(t, r"airplay")
    row["chromecast"] = has(t, r"chromecast|google cast")
    row["alexa"] = has(t, r"alexa")
    proc = pick(f, r"processor|picture engine|display processor|^engine$")
    row["processor"] = proc
    dz = pick(f, r"dimming zones|local dimming zones|precise dimming")
    zn = None
    if dz:
        m = re.search(r"x\s*(\d{2,5})|(\d{2,5})\s*zones|LD\s*(\d{3,5})", dz, re.I)
        zn = int(next(g for g in m.groups() if g)) if m else None
    ld = pick(f, r"local dimming|dimming tech|dimming type|micro dimming|backlight dimming")
    row["localDimming"] = (row["tech"] in ("OLED", "MicroLED")) and "Per-pixel" or (ld if ld and not NO.match(ld) else ("Yes" if zn else None))
    row["zones"] = zn
    pb = pick(f, r"peak brightness|display brightness|brightness \(nits\)")
    m = re.search(r"(\d[\d,]{2,5})\s*nits|HDR\s*(\d{3,5})|^(\d{3,5})$", pb or "", re.I)
    row["nits"] = int((next(g for g in m.groups() if g)).replace(",", "")) if m else None
    if not row["nits"]:
        m = re.search(r"up to ([\d,]{3,6})[- ]nits?|([\d,]{3,6})[- ]nits? peak", t, re.I)
        row["nits"] = int(next(g for g in m.groups() if g).replace(",", "")) if m else None
    row["weightLb"] = lbs(pick(f, r"weight.*without stand|set weight without|weight of tv without|tv weight without|product weight without|weight \(without stand\)"))
    row["dimsIn"] = dims_in(pick(f, r"(size|dimension).*without stand|without stand.*\(w", exclude=r"package|carton"))
    row["vesa"] = pick(f, r"vesa(?! compliance)|wall mount.*pattern|^pattern$|hole pitch")
    pw = pick(f, r"power consumption \(typical\)", r"^power consumption( \(watts\))?$", r"typical power", r"on mode power", r"power consumption", exclude=r"standby|stand-by|max|annual|networked")
    row["powerW"] = num(pw) if pw and re.search(r"w", pw, re.I) else None
    row["usb"] = (lambda v: int(num(v)) if v and num(v) and num(v) < 6 else None)(pick(f, r"^usb( ports| input)?$|usb ports"))
    return row

def blob_of(f, extra=""):
    return " | ".join(f"{k.split(' > ',1)[-1]}: {v}" for k, v in f.items()) + " | " + extra

rows = []

# ---------------- Samsung ----------------
sam = load("samsung_raw.json") or []
seen = set()
for fam in sam:
    r = fam["family"]
    for m in fam["specs"]:
        mc = m["modelCode"]
        if mc in seen: continue
        seen.add(mc)
        g = {x["groupName"]: {s["name"]: s["value"] for s in x["specList"]} for x in m.get("fullSpecs", [])}
        f = flat(g)
        pr = fam["prices"].get(mc, {})
        size = num(f.get("Display > Screen Size")) or num(pr.get("title"))
        fname = (r.get("familyMktName") or r.get("name") or "").replace("{size}", str(int(size)) if size else "").replace("{Size}", str(int(size)) if size else "")
        name = fname if re.search(r"\d+\s*(\"|inch|in\b|”)", fname, re.I) else f'{int(size) if size else ""}" {fname}'
        name = re.sub(r"\s+", " ", name).strip()
        ser = next((m for m in re.findall(r"\b([A-Z]{1,3}\d{1,4}[A-Z0-9]{0,3})\b", fname) if not re.fullmatch(r"[48]K|20\d\d", m)), None)
        if ser: ser = type("M", (), {"group": lambda self, i, v=ser: v})()
        if ser and re.search(r"the frame", fname, re.I): ser = type("M", (), {"group": lambda self, i, v="The Frame " + ser.group(1): v})()
        url = pr.get("url") or r.get("pdpURL")
        row = dict(brand="Samsung", model=mc, name=name, series=(ser.group(1) if ser else fname.split(" ")[0]), size=size,
                   url=("https://www.samsung.com" + url) if url and url.startswith("/") else url,
                   image=(r.get("images") or {}).get("smImage"), price=pr.get("sale") or r.get("sale_price"),
                   msrp=pr.get("msrp") or r.get("msrp_price"), currency="USD", region="US",
                   rating=pr.get("rating"), reviews=pr.get("reviews"), category=r.get("sub_genre") or r.get("sub_category"))
        row["year"] = year_of(name, f, mc)
        if size and not row["price"] and fam["prices"]:
            pass
        common(row, f, blob_of(f, name))
        row["raw"] = g
        rows.append(row)

# ---------------- LG ----------------
for r in load("lg_raw.json") or []:
    g = r.get("specs") or {}
    f = flat(g)
    name = r.get("ec_user_friendly_name") or r.get("ec_model_display_name")
    mc = r.get("ec_model_display_name") or r.get("ec_model_id")
    m = re.search(r"\b(OLED\d{2,3}([A-Z]\d[A-Z]?)|(\d{2,3})(QNED\w+?|NANO\w+|UA\w+?|UT\w+?|NU\w+?|UR\w+?|UQ\w+?)(?:[A-Z]{3})$)", mc or "")
    series = None
    if mc:
        mm = re.match(r"(?:OLED)?(\d{2,3})([A-Z]+\d+[A-Z]?\d?)", mc.replace("OLED", "OLED", 1))
        mo = re.match(r"OLED\d{2,3}([A-Z]\d+[A-Z]?)", mc)
        mq = re.match(r"\d{2,3}([A-Z]+\d+[A-Z]?)", mc)
        series = ("OLED " + mo.group(1)) if mo else (mq.group(1) if mq else mc)
    cats = r.get("ec_category") or []
    if not isinstance(cats, list): cats = [cats]
    row = dict(brand="LG", model=mc, name=name, series=series, size=r.get("ec_size"),
               url="https://www.lg.com" + r["ec_uri_link"], image=r.get("ec_medium_image_addr"),
               price=r.get("ec_final_price"), msrp=r.get("ec_msrp"), currency="USD", region="US",
               rating=(r.get("ec_s_rating") or 0) / 20 if isinstance(r.get("ec_s_rating"), (int, float)) and r.get("ec_s_rating") > 5 else r.get("ec_s_rating"),
               reviews=r.get("ec_participant_count"), category=", ".join(c for c in cats if c != "TVs"))
    if isinstance(row["image"], list): row["image"] = row["image"][0]
    row["year"] = year_of(name, f, mc)
    common(row, f, blob_of(f, name))
    row["raw"] = g
    if "lifestyle-products" in row["url"] and not g:
        continue
    rows.append(row)

# ---------------- Sony (UK site; specs global) ----------------
sony = load("sony_raw.json")
if sony:
    for pid, p in sony["specs"].items():
        for mc, sp in p["models"].items():
            clean = {}
            for k, v in sp.items():
                lab = k.split("::")[0].strip()
                lab = lab[:1] + lab[1:].lower() if lab.isupper() else lab
                clean[lab] = v
            meta = sony["meta"].get(mc) or sony["meta"].get(mc.replace(" EU", "")) or {}
            g = {"Specifications": clean}
            f = flat(g)
            pname = (meta.get("name") or pid.replace("-", " ").upper()).split("|")[0].strip()
            size = num(clean.get('Screen size (inch, measured diagonally)') or "") or num(re.sub(r"K-", "", mc))
            row = dict(brand="Sony", model=mc, name=f'{int(size) if size else ""}" {pname} ({mc})', series=pname, size=size,
                       url=p["url"].replace("/spec", ""), image=("https:" + meta["img"]) if meta.get("img", "").startswith("//") else meta.get("img"),
                       price=None, msrp=None, currency=None, region="UK/EU (model specs global)", category=None)
            row["year"] = year_of("", f, mc)
            common(row, f, blob_of(f, pname + " " + (meta.get("name") or "")))
            row["raw"] = g
            rows.append(row)

# ---------------- TCL ----------------
for p in load("tcl_raw.json") or []:
    panels = p["panels"]
    only = list(panels.values())[0] if len(panels) == 1 else None
    for v in p["variants"]:
        g = panels.get(v["id"]) or only
        if not g: continue
        g = {k: o for k, o in g.items()}
        f = flat(g)
        mc = v.get("sku") or (pick(f, r"^model$") or "")
        size = num(v["title"]) if num(v["title"]) else num(pick(f, r"screen size|class size") or "")
        ser = re.search(r"\b(QM\d[A-Z]|RM\d[A-Z]|X1\d[A-Z]|Q\d[A-Z]|QM\d{3}[A-Z]?|S\d[A-Z]?|A\d{3}[A-Z]?|F\d[A-Z]|[QS] Class|QD\w+)\b", p["title"])
        title = re.sub(r"\s*[–-]\s*\w+ Series$", "", p["title"]).strip()
        row = dict(brand="TCL", model=mc, name=f'{int(size) if size else ""}" {title}'.strip(), series=ser.group(1) if ser else title.split(" ")[0],
                   size=size, url=f"https://us.tcl.com/products/{p['handle']}?variant={v['id']}", image=("https:" + p["image"]) if (p.get("image") or "").startswith("//") else p.get("image"),
                   price=float(v["price"]) if v.get("price") else None, msrp=float(v["compare"]) if v.get("compare") else None, currency="USD", region="US", category=None)
        if row["msrp"] and row["price"] and row["msrp"] < row["price"]: row["msrp"] = None
        row["year"] = year_of(p["title"], f, mc)
        common(row, f, blob_of(f, p["title"] + " " + " ".join(p.get("tags", []))))
        row["raw"] = g
        rows.append(row)

# ---------------- Vizio ----------------
for r in load("vizio_raw.json") or []:
    g = r["spec"]
    if not g: continue
    f = flat(g)
    mc = r["url"].rstrip("/").split("/")[-1]
    cat = r["url"].split("/")[-2]
    size = num(pick(f, r"class size") or "")
    catname = {"4k": "4K UHD", "d-series": "D-Series", "fhd": "Full HD", "hd": "HD", "m-series": "M-Series Quantum", "mini-led": "Quantum Mini-LED", "oled": "OLED", "p-series": "P-Series Quantum", "quantum": "Quantum", "quantum-pro": "Quantum Pro", "v-series": "V-Series"}.get(cat, cat)
    row = dict(brand="Vizio", model=mc, name=f'{int(size) if size else ""}" VIZIO {catname} ({mc})', series=catname, size=size, url=r["url"], image=r.get("image"),
               price=None, msrp=None, currency=None, region="US", category=catname)
    row["year"] = None
    common(row, f, blob_of(f, catname + " " + (r.get("desc") or "")))
    row["raw"] = g
    rows.append(row)

# ---------------- Hisense ----------------
hspec = load("hisense_specs.json") or {}
hdesc = {x["slug"]: x for x in (load("hisense_desc.json") or [])}
for slug, x in hdesc.items():
    sp = (hspec.get(slug) or {})
    g = sp.get("spec") if sp and not sp.get("err") else None
    title = (sp.get("title") if sp else None) or (x.get("title") or "").replace(" | Hisense-USA", "").replace(" | Hisense", "")
    if not title or title == "404": continue
    m = re.search(r"-([0-9]{2,3}[a-z0-9]+(?:-pro)?)$", slug)
    mc = (m.group(1).upper() if m else slug.split("-")[-1].upper())
    size = num(re.search(r'(\d{2,3})"', title).group(1)) if re.search(r'(\d{2,3})"', title) else None
    ser = re.search(r"Class\s+(\w+)\s+Series|\b(U\d\w*|UR\d|UX|E\d|QD\d\w*|A\d|S\d|H\d\w*|R\d|M\d|MX)\s+Series", title)
    desc = " ".join(filter(None, [x.get("description"), x.get("rich"), x.get("meta")]))
    derived = not g
    if derived:
        g = {"From product description (no spec table published)": {"Description": re.sub(r"\s+", " ", desc).strip()[:1500]}}
    f = flat(g) if not derived else {}
    row = dict(brand="Hisense", model=mc, name=title, series=(next((s for s in ser.groups() if s), None) if ser else None), size=size,
               url="https://www.hisense-usa.com/product-page/" + slug, image=x.get("image"), price=None, msrp=None, currency=None, region="US",
               category=None, derived=derived)
    row["year"] = year_of(title, f, mc)
    common(row, f, blob_of(f, title + " " + desc))
    row["raw"] = g
    rows.append(row)

# Hisense publishes a spec table on only some sizes of a series: share series-level specs with siblings
SIZE_FIELDS = {"size", "weightLb", "dimsIn", "vesa", "powerW"}
SHARE = ["tech", "resolution", "refresh", "refreshMax", "dolbyVision", "hdr10plus", "hlg", "imax", "filmmaker", "hdmi", "hdmi21", "earc", "vrr", "allm",
         "freesync", "gsync", "os", "audioW", "channels", "atmos", "dtsx", "wifi", "bluetooth", "atsc3", "airplay", "chromecast", "alexa", "processor",
         "localDimming", "zones", "nits", "usb"]
def fam(mc): return re.sub(r"^\d{2,3}", "", mc or "")
donors = {}
for r in rows:
    if r["brand"] == "Hisense" and not r.get("derived"):
        donors.setdefault(fam(r["model"]), r)
for r in rows:
    if r["brand"] == "Hisense" and r.get("derived"):
        d = donors.get(fam(r["model"]))
        if not d: continue
        for k in SHARE:
            if d.get(k) not in (None, False, ""): r[k] = d[k]
        r["derived"] = False
        r["sharedFrom"] = d["model"]
        g = {f"Series specs (published on {d['model']})": {k: v for grp in d["raw"].values() for k, v in grp.items()
             if not re.search(r"dimension|weight|size|power|upc|vesa|wall mount|package", k, re.I)}}
        g.update(r["raw"])
        r["raw"] = g
        if not r.get("year"): r["year"] = d.get("year")

# year fallbacks from model codes
SAM_Y = {"D": 2024, "F": 2025, "H": 2026, "C": 2023, "B": 2022, "A": 2021}
for r in rows:
    if r.get("year"): continue
    mc = r.get("model") or ""
    if r["brand"] == "Samsung":
        m = re.match(r"(?:QN|UN|MRN|MN)\d{2,3}([A-Z]+?\d{2,3}|LS0\d|LST\d)([A-H])", mc)
        if m: r["year"] = SAM_Y.get(m.group(2))
    elif r["brand"] == "LG":
        m = re.match(r"OLED\d{2,3}[A-Z](\d)", mc) or re.match(r"\d{2,3}[A-Z]+\d{2}([A-Z])", mc)
        if m:
            k = m.group(1)
            r["year"] = {"1": 2021, "2": 2022, "3": 2023, "4": 2024, "5": 2025, "6": 2026, "Q": 2022, "R": 2023, "T": 2024, "A": 2025, "B": 2026}.get(k)
    elif r["brand"] == "Sony":
        r["year"] = 2025 if "M2" in mc else 2024
    elif r["brand"] == "TCL":
        m = re.search(r"\d([A-Z])(?:-|$)", mc)
        r["year"] = {"K": 2025, "L": 2026, "J": 2024, "D": 2024, "S": None}.get(m.group(1)) if m else None
    elif r["brand"] == "Hisense":
        m = re.search(r"\d([A-Z]+)$", mc)
        s = m.group(1) if m else ""
        r["year"] = 2026 if s.endswith(("SG", "SF", "SV", "SV-PRO")) or "S" == s[:1] else 2025 if s.endswith(("QG", "QF", "QR")) else 2024 if s.endswith(("N", "NF", "NR")) else None
    elif r["brand"] == "Vizio":
        m = re.search(r"-([A-Z]?\d)(\d)", mc)

for r in rows:
    for k in ("price", "msrp"):
        if r.get(k) in (0, 0.0): r[k] = None
    if r.get("size"): r["size"] = round(float(r["size"]))
    r["id"] = f'{r["brand"]}:{r["model"]}'

# dedupe ids
uniq = {}
for r in rows:
    if r["id"] in uniq:
        if len(json.dumps(r["raw"])) <= len(json.dumps(uniq[r["id"]]["raw"])): continue
    uniq[r["id"]] = r
rows = list(uniq.values())
json.dump(rows, open(OUT, "w"))
import collections
print(len(rows), collections.Counter(r["brand"] for r in rows), file=sys.stderr)

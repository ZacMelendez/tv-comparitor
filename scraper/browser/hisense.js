// Hisense spec-table scraper — paste into the DevTools console on any https://www.hisense-usa.com page,
// after setting SLUGS to the contents of data/hisense_slugs.json (made by lists.py).
// The spec table is filled in client-side by a Wix widget, so each product page is loaded in a
// same-origin iframe and read once the widget renders. Many sizes have no table at all; normalize.py
// then shares the series' specs from a sibling size. Progress is kept in localStorage, so it can resume.
// When finished, copy the logged JSON into data/hisense_specs.json.
const SLUGS = []; // paste slugs here
(async () => {
  const done = JSON.parse(localStorage.getItem("__his") || "{}");
  const save = () => localStorage.setItem("__his", JSON.stringify(done));
  const one = slug => new Promise(resolve => {
    const f = document.createElement("iframe");
    f.style.cssText = "position:fixed;left:0;top:0;width:1200px;height:900px;opacity:0.01;pointer-events:none;z-index:-1";
    f.src = "/product-page/" + slug;
    const t0 = Date.now(); let k = 0;
    const finish = v => { clearInterval(iv); done[slug] = v; save(); f.src = "about:blank"; f.remove(); resolve(); };
    const iv = setInterval(() => {
      try {
        const d = f.contentDocument, w = f.contentWindow;
        if (d && d.body) {
          k++; w.scrollTo(0, (k % 10) * d.body.scrollHeight / 10);          // the widget lazy-loads on scroll
          const b = [...d.querySelectorAll("button")].find(b => /full specs/i.test(b.textContent));
          if (b && k % 4 === 0) b.click();
        }
        const el = d && d.querySelector(".wixui-productSpecification");
        if (el && el.querySelectorAll("dd").length > 3) {
          const spec = {};
          el.querySelectorAll(":scope > div").forEach(g => {
            const o = {};
            g.querySelectorAll("dl > div").forEach(r => { o[r.querySelector("dt")?.textContent.trim()] = r.querySelector("dd")?.textContent.trim(); });
            spec[g.querySelector("h5")?.textContent.trim() || ""] = o;
          });
          finish({ title: d.querySelector("h1")?.textContent.trim(), spec });
        } else if (Date.now() - t0 > 18000) finish({ err: "empty" });
      } catch (e) { finish({ err: String(e) }); }
    }, 700);
    document.body.appendChild(f);
  });
  const todo = SLUGS.filter(s => !(s in done));
  for (let i = 0; i < todo.length; i += 3) await Promise.all(todo.slice(i, i + 3).map(one)); // keep concurrency low
  console.log(JSON.stringify(Object.fromEntries(Object.entries(done).filter(([, v]) => v.spec))));
})();

// Sony BRAVIA spec scraper — paste into the DevTools console on https://www.sony.co.uk/bravia
// Sony's US store rejects scripted requests, so specs come from Sony UK (panels, processors
// and HDMI features are the same globally). Copy the logged JSON into data/sony_raw.json.
(async () => {
  const parents = "bravia-9-ii,bravia-8-ii,bravia-7-ii,bravia-6-ii,bravia-5-ii,bravia-3-ii,bravia-2-ii,bravia-9,bravia-8,bravia-7,bravia-6,bravia-5,bravia-3,bravia-2";
  // 1) Model list (SKUs, sizes, marketing names) from Sony's own product API
  const products = [];
  for (let start = 0; start < 100; start += 10) {
    const j = await (await fetch(`/api/open/products?parentIds=${parents}&group=default&locale=en_GB&start=${start}`)).json();
    const p = j.searchResponse.products;
    if (!p.length) break;
    products.push(...p);
  }
  const meta = {};
  for (const p of products) for (const s of p.skus)
    meta[s.modelName] = meta[s.modelName] || { sku: s.id, size: s.differentiators?.[0]?.valueDisplayName, parent: p.id, name: p.marketingProductName, img: p.images?.[0]?.desktop };

  // 2) Spec tables: one page per series, one column per size. Cells spanning several
  //    sizes use colspan, so expand them across the column order.
  const txt = el => el.textContent.trim().replace(/\s*\n\s*/g, " / ").replace(/\s+/g, " ");
  const specs = {};
  for (const p of products) {
    const slug = new URL(p.learnMoreURL, location.origin).pathname.replace(/^\/permalink\/product\//, "/bravia/products/");
    const res = await fetch(slug.replace(/\/$/, "") + "/spec");
    if (!res.ok) continue;
    const doc = new DOMParser().parseFromString(await res.text(), "text/html");
    const rows = [...doc.querySelectorAll("tr.SpecificationsTable__TableRow")];
    let order = [];
    for (const tr of rows) {
      const ids = [...new Set([...tr.querySelectorAll("td[data-product-id]")].map(t => t.dataset.productId))];
      if (ids.length > order.length) order = ids;
    }
    const models = {};
    for (const tr of rows) {
      const th = tr.querySelector("th"); if (!th) continue;
      const label = txt(th), tds = [...tr.querySelectorAll("td")], per = {};
      for (const t of tds.filter(t => t.classList.contains("-onlySmallScreen"))) if (t.dataset.productId && !(t.dataset.productId in per)) per[t.dataset.productId] = txt(t);
      let i = 0;
      for (const t of tds.filter(t => !t.classList.contains("-onlySmallScreen"))) {
        const c = +t.getAttribute("colspan") || 1;
        for (let k = 0; k < c; k++) { const m = order[i + k]; if (m && !(m in per)) per[m] = txt(t); }
        i += c;
      }
      for (const [m, v] of Object.entries(per)) (models[m] = models[m] || {})[label] = v;
    }
    specs[p.id] = { url: location.origin + slug + "/spec", order, models };
  }
  console.log(JSON.stringify({ specs, meta }));
})();

"use strict";
const $ = id => document.getElementById(id);
const NOSERVER = "Cannot reach the server. Start it with `python backend/app.py` and open http://127.0.0.1:5000 " +
  "in your browser (do not open index.html directly).";
let items = [];          // [{name, known}]
let status = {};

const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined && text !== null) e.textContent = text;
  return e;
};
const setMsg = (t, err = false) => { $("msg").textContent = t; $("msg").className = "msg" + (err ? " err" : ""); };

async function api(url, opts) {
  try {
    const r = await fetch(url, opts);
    let d = {};
    try { d = await r.json(); } catch (_) { d = { error: "The server sent an unreadable answer." }; }
    return { ok: r.ok, d };
  } catch (e) {
    return { ok: false, d: { error: NOSERVER } };
  }
}

/* ---------- ingredient list ---------- */
function renderChips() {
  $("chips").replaceChildren(...items.map(it => {
    const c = el("button", "chip" + (it.known ? "" : " unknown"));
    c.type = "button";
    c.title = it.known ? "Click to remove" : "Not in the recipe collection - click to remove";
    c.append(it.name, el("span", "x", "✕"));
    c.onclick = () => { items = items.filter(x => x.name !== it.name); renderChips(); };
    return c;
  }));
  const bad = items.filter(i => !i.known).map(i => i.name);
  $("note").hidden = !bad.length;
  $("note").textContent = bad.length ? `Not found in any recipe: ${bad.join(", ")}. It stays in your list but cannot match recipes.` : "";
}

async function addText(text) {
  const lines = String(text).split(/[,;\n]+/).map(s => s.trim()).filter(Boolean);
  if (!lines.length) return;
  const { ok, d } = await api("/api/normalize", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ingredients: lines }) });
  if (!ok) { setMsg(d.error || "Could not read that ingredient.", true); return; }
  const fixed = [];
  d.items.forEach(x => {
    if (!items.some(i => i.name === x.name)) items.push({ name: x.name, known: x.known });
    if (x.known && x.input.trim().toLowerCase() !== x.name) fixed.push(`"${x.input.trim()}" → ${x.name}`);
  });
  renderChips();
  setMsg(fixed.length ? "Understood: " + fixed.join(", ") : "");
}

$("addform").onsubmit = async e => { e.preventDefault(); const v = $("ing").value; $("ing").value = ""; await addText(v); $("ing").focus(); };
$("demo").onclick = () => addText("tomato, egg, onion, cheese");
$("clear").onclick = () => { items = []; renderChips(); $("results").replaceChildren(); setMsg(""); $("detected").replaceChildren(); $("previews").replaceChildren(); };
$("time").oninput = () => { const v = +$("time").value; $("tv").textContent = v >= 180 ? "any" : v + " min"; };
$("miss").oninput = () => { const v = +$("miss").value; $("mv").textContent = v >= 6 ? "any" : v; };
$("time").oninput(); $("miss").oninput();

/* ---------- startup ---------- */
(async function init() {
  const [st, vocab] = await Promise.all([api("/api/status"), api("/api/ingredients")]);
  if (!st.ok) { setMsg(st.d.error, true); return; }
  status = st.d;
  const b = $("badges");
  const badge = (t, ok) => { const s = el("span", "badge " + (ok ? "ok" : "off"), t); b.append(s); };
  badge(`${status.recipes} recipes`, true);
  badge(`${status.ingredients} ingredients`, true);
  badge(status.image_model ? "photo recognition ready" : "photo recognition: not trained", !!status.image_model);
  badge(status.word2vec ? "Word2Vec substitutions on" : "Word2Vec off (rules only)", status.word2vec);
  if (vocab.ok) $("vocab").replaceChildren(...vocab.d.map(x => { const o = el("option"); o.value = x; return o; }));
  $("popular").replaceChildren(...(status.popular || []).filter(x => !status.staples.includes(x)).slice(0, 18).map(x => {
    const c = el("button", "chip", x); c.type = "button"; c.onclick = () => addText(x); return c;
  }));
  if (!status.image_model) {
    $("drop").classList.add("disabled");
    $("photohint").textContent = status.image_hint || "Photo recognition is not available.";
  }
})();

/* ---------- photo recognition ---------- */
async function handleFiles(files) {
  files = [...files].filter(f => f.type.startsWith("image/"));
  if (!files.length) return;
  $("detected").replaceChildren();
  for (const f of files) {
    const img = el("img"); img.alt = "uploaded ingredient photo"; img.src = URL.createObjectURL(f);
    $("previews").append(img);
    setMsg("Analysing photo…");
    const fd = new FormData(); fd.append("image", f);
    const { ok, d } = await api("/api/detect", { method: "POST", body: fd });
    if (!ok) { setMsg(d.error || "Photo recognition failed.", true); continue; }
    d.predictions.forEach(p => {
      const c = el("button", "chip sug", `${p.label} (${Math.round(p.confidence * 100)}%)`);
      c.type = "button"; c.title = "Click to add";
      c.onclick = () => { addText(p.label); c.remove(); };
      $("detected").append(c);
    });
    setMsg("Tap the correct guess to add it. You can still edit the list before searching.");
  }
}
$("photo").onchange = async e => { await handleFiles(e.target.files); e.target.value = ""; };
const drop = $("drop");
["dragenter", "dragover"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("drag"); }));
["dragleave", "drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("drag"); }));
drop.addEventListener("drop", e => handleFiles(e.dataTransfer.files));

/* ---------- results ---------- */
function recipeCard(x, i) {
  const c = el("article", "recipe");
  c.style.animationDelay = (i * 60) + "ms";
  const head = el("div", "rhead");
  const ring = el("div", "ring", Math.round(x.coverage * 100) + "%");
  ring.style.setProperty("--p", Math.round(x.coverage * 100)); ring.title = "Share of the recipe's ingredients you already have";
  head.append(el("div", "rank", i + 1), el("h4", "", x.name), ring);
  c.append(head);
  const meta = el("div", "meta");
  meta.append(el("span", "", "⏱ " + x.minutes + " min"), el("span", "", `🛒 ${x.missing.length} missing`), el("span", "", "score " + x.score));
  c.append(meta);

  const chipRow = (title, list, cls) => {
    if (!list.length) return;
    c.append(el("div", "sec", title));
    const row = el("div", "chips");
    list.forEach(t => row.append(el("span", "chip static " + cls, t)));
    c.append(row);
  };
  chipRow("You have", x.have, "have");
  chipRow("Missing", x.missing, "miss");
  chipRow("Assumed pantry staples", x.staples, "staple");

  if (x.substitutions.length) {
    c.append(el("div", "sec", "Substitutions"));
    x.substitutions.forEach(s => {
      const p = el("p", "subline");
      p.append(el("b", "", `${s.for} → ${s.use}`), " — " + s.reason);
      p.append(el("span", "tag" + (s.source === "embedding" ? " ai" : ""), s.source === "embedding" ? "Word2Vec" : "rule"));
      c.append(p);
    });
  } else if (x.missing.length) {
    c.append(el("p", "subline", "No suitable replacement among the ingredients you have."));
  }
  if (x.breakdown) {
    const d = el("details"); d.append(el("summary", "", "Why this score?"));
    const b = el("div", "bars");
    b.append(el("div", "", `Coverage +${x.breakdown.coverage}`), el("div", "", `Missing-ingredient penalty −${x.breakdown.missing_penalty}`),
      el("div", "", `Cooking-time penalty −${x.breakdown.time_penalty}`), el("div", "", `Utility = ${x.score}`));
    d.append(b); c.append(d);
  }
  if (x.steps.length) {
    const d = el("details"); d.append(el("summary", "", "Steps"));
    const o = el("ol"); x.steps.forEach(t => o.append(el("li", "", t))); d.append(o); c.append(d);
  }
  return c;
}

function column(title, list) {
  const col = el("div", "col");
  if (title) col.append(el("h3", "", title));
  if (!list.length) col.append(el("div", "empty card", "No recipes match these limits."));
  list.forEach((x, i) => col.append(recipeCard(x, i)));
  return col;
}

$("go").onclick = async () => {
  if (!items.length) { setMsg("Add at least one ingredient first.", true); return; }
  const btn = $("go"); btn.disabled = true; setMsg("Cooking up ideas…");
  const t = +$("time").value, m = +$("miss").value;
  const { ok, d } = await api("/api/recommend", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ingredients: items.map(i => i.name), max_time: t >= 180 ? null : t,
      max_missing: m >= 6 ? null : m, method: $("method").value }) });
  btn.disabled = false;
  const box = $("results"); box.replaceChildren();
  if (!ok) { setMsg(d.error || "Something went wrong.", true); return; }
  if (!d.results.length) {
    setMsg(d.have.length ? "No recipes match. Try a longer cooking time or allow more missing ingredients." : "None of those ingredients could be understood.", true);
    return;
  }
  setMsg("");
  const sum = el("p", "summary", `Found in ${d.elapsed_ms} ms using ${d.have.length} ingredient${d.have.length === 1 ? "" : "s"}.`);
  const wrap = el("div", "cols" + (d.method === "compare" ? " two" : ""));
  if (d.method === "compare") wrap.append(column("Utility ranking (proposed)", d.results), column("Overlap baseline", d.baseline_results));
  else wrap.append(column("", d.results));
  box.append(sum, wrap);
  box.scrollIntoView({ behavior: "smooth", block: "start" });
};

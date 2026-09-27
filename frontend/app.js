/*
  app.js - the behaviour of the Airline Operations Console.

  If you have never written JavaScript, here is the mental model:
    * The browser loads index.html, which contains empty boxes (<div id="...">).
    * This file asks the Python server for data (fetch(...)), builds HTML text
      from that data, and puts it inside those boxes (element.innerHTML = ...).
    * When the user clicks something, a function here runs and repeats that.

  Nothing here contains business logic.  Every rule lives in the Python
  package `airline/`; this file only displays results and sends requests.

  Reading guide (top to bottom):
    1. tiny helpers            - shortcuts for finding elements, escaping text
    2. talking to the server   - api()
    3. global data             - META (classes/operations), STATE (records)
    4. one render function per section
    5. wiring                  - which button calls which function
*/

// ---------------------------------------------------------------- 1. helpers
const $ = (selector) => document.querySelector(selector);          // find one element
const $$ = (selector) => document.querySelectorAll(selector);      // find many elements

// Make text safe to insert into HTML (so a name like "<b>" is shown, not interpreted)
function esc(value) {
  if (value === null || value === undefined) return "";
  return String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Pick a colour for a status word
function pill(status) {
  const s = String(status || "");
  let cls = "";
  if (/(active|in_service|confirmed|assigned|arrived|planned|closed|rectified|delivered|valid|agreed|resolved|chosen|loaded|checked_in|boarded|flown|accepted)/.test(s)) cls = "s-ok";
  if (/(delayed|deferred|held|seat_pending|needs_aircraft|amended|open|offloaded|proposed|departed|diverted|standby)/.test(s)) cls = "s-warn";
  if (/(cancelled|aog|retired|refused|invalid|rejected|offloaded|irregular|revoked)/.test(s)) cls = "s-bad";
  if (/(superseded|ended|released|replaced|rebooked|archived|removed|lifted|landed)/.test(s)) cls = "s-hist";
  return `<span class="pill ${cls}">${esc(s)}</span>`;
}

// Show a small message in the corner for a few seconds
let toastTimer = null;
function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 3500);
}

// Build an HTML table from a list of objects and a list of columns.
// columns = [{ key: "status", label: "Status", render: (row) => "..." }, ...]
function table(rows, columns, rowAttrs = () => "") {
  if (!rows.length) return `<p class="muted">Nothing here yet.</p>`;
  const head = columns.map((c) => `<th>${esc(c.label)}</th>`).join("");
  const body = rows.map((row) => {
    const cells = columns.map((c) => `<td>${c.render ? c.render(row) : esc(row[c.key])}</td>`).join("");
    return `<tr ${rowAttrs(row)}>${cells}</tr>`;
  }).join("");
  return `<div class="table-wrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

// ---------------------------------------------------------------- 2. talking to the server
// api("GET", "/api/state")  or  api("POST", "/api/op/assign_seat", {segment: "SEG-001", seat_number: "5A"})
async function api(method, path, body) {
  const options = { method, headers: { "Content-Type": "application/json" } };
  if (body !== undefined) options.body = JSON.stringify(body);
  const response = await fetch(path, options);
  return response.json();
}

// ---------------------------------------------------------------- 3. global data
let META = null;     // classes, inheritance tree, operations, demo names  (loaded once)
let STATE = null;    // all records + journal                              (reloaded after every change)
let DEMO_RESULTS = [];
let selectedRecordId = null;
const MAX_ROWS = 60;      // longest table we draw at once (tables never scroll on their own)

// Fetch the latest records from Python and redraw every section that shows them.
async function refresh() {
  STATE = await api("GET", "/api/state");
  $("#clock").textContent = STATE.clock.slice(11, 16);
  fillIdList();
  renderOverview();
  renderRecords();
  renderJournal();
}

// Every record id + label goes into the <datalist>, so operation forms can autocomplete.
function fillIdList() {
  const options = [];
  for (const [cls, rows] of Object.entries(STATE.records)) {
    for (const r of rows) options.push(`<option value="${esc(r.id)}">${esc(cls)}: ${esc(r.label)}</option>`);
  }
  $("#all-ids").innerHTML = options.join("");
}

// Small helper: find a record's label by id (used when a field holds another record's id)
function labelOf(id) {
  if (!STATE || typeof id !== "string") return id;
  for (const rows of Object.values(STATE.records)) {
    const hit = rows.find((r) => r.id === id);
    if (hit) return hit.label;
  }
  return id;
}

// ---------------------------------------------------------------- 4a. OVERVIEW
function renderOverview() {
  const records = Object.values(STATE.records).reduce((n, rows) => n + rows.length, 0) + STATE.seat_count;
  const classCount = META.classes.length;
  const opCount = Object.values(META.operations).reduce((n, list) => n + list.length, 0);
  const refused = STATE.journal.filter((e) => e.action === "refused").length;
  const disruptions = ["Delay", "Cancellation", "Diversion", "AircraftSubstitution"].reduce((n, c) => n + (STATE.records[c] || []).length, 0);
  $("#stats").innerHTML = [
    [classCount, "classes in model"], [opCount, "operations"], [records, "records"],
    [STATE.journal.length, "history events"], [disruptions, "disruptions today"], [refused, "rules refused an action"],
  ].map(([n, l]) => `<div class="stat"><div class="n">${n}</div><div class="l">${l}</div></div>`).join("");

  const flights = (STATE.records.Flight || []).slice().sort((a, b) => a.std.localeCompare(b.std));
  $("#flight-board").innerHTML = table(flights, [
    { key: "label", label: "Flight" }, { key: "route", label: "Route" }, { key: "service_kind", label: "Kind" },
    { key: "std_time", label: "STD" }, { key: "etd_time", label: "ETD" },
    { label: "Delay", render: (f) => f.delay_min ? `<span class="pill s-warn">+${f.delay_min}</span>` : "" },
    { label: "Aircraft", render: (f) => f.aircraft ? esc(f.aircraft) : `<span class="pill s-bad">none</span>` },
    { key: "passengers", label: "Pax" }, { key: "crew", label: "Crew" },
    { label: "Status", render: (f) => pill(f.status) },
  ], (f) => `class="clickable" data-open="${f.id}"`);

  const fleet = STATE.records.Aircraft || [];
  const cfgs = STATE.records.CabinConfiguration || [];
  $("#fleet-board").innerHTML = table(fleet, [
    { key: "registration", label: "Reg" }, { label: "Type", render: (a) => esc(labelOf(a.aircraft_type)) },
    { label: "Current cabin", render: (a) => { const c = cfgs.find((x) => x.aircraft === a.id && x.valid_to === null); return c ? `${esc(c.name)} (${c.seats} seats)` : "-"; } },
    { key: "cargo_capacity_kg", label: "Cargo kg" }, { label: "At", render: (a) => esc(labelOf(a.location)) },
    { label: "Status", render: (a) => pill(a.status) },
  ], (a) => `class="clickable" data-open="${a.id}"`);
}

// ---------------------------------------------------------------- 4b. RECORDS
function renderRecords() {
  const select = $("#record-class");
  const classes = Object.keys(STATE.records).sort();
  const current = select.value || "Flight";
  select.innerHTML = classes.map((c) => `<option value="${c}" ${c === current ? "selected" : ""}>${c} (${STATE.records[c].length})</option>`).join("");
  drawRecordTable();
}

function drawRecordTable() {
  const cls = $("#record-class").value;
  const filter = $("#record-filter").value.toLowerCase();
  let rows = STATE.records[cls] || [];
  if (filter) rows = rows.filter((r) => JSON.stringify(r).toLowerCase().includes(filter));
  const total = rows.length;
  rows = rows.slice(0, MAX_ROWS);               // keep the page a sensible length; the filter narrows it
  $("#record-count").textContent = total > MAX_ROWS ? `showing ${MAX_ROWS} of ${total} - use the filter to narrow` : `${total} record(s)`;

  // Columns: id, label, status, then up to 5 other simple fields
  const skip = new Set(["id", "label", "status", "type", "created_at", "event_count", "events"]);
  const extra = rows.length ? Object.keys(rows[0]).filter((k) => !skip.has(k) && typeof rows[0][k] !== "object").slice(0, 5) : [];
  const columns = [
    { key: "id", label: "Id" }, { key: "label", label: "Label" },
    { label: "Status", render: (r) => pill(r.status) },
    ...extra.map((k) => ({ label: k, render: (r) => esc(typeof r[k] === "string" && /^[A-Z]{3}-\d{3}$/.test(r[k]) ? labelOf(r[k]) : r[k]) })),
    { label: "Events", render: (r) => r.event_count },
  ];
  $("#record-table").innerHTML = table(rows, columns, (r) => `class="clickable ${r.id === selectedRecordId ? "selected" : ""}" data-open="${r.id}"`);
}

// Show one record and its full history in the panel above the table
async function openRecord(id) {
  selectedRecordId = id;
  const data = await api("GET", "/api/record/" + id);
  if (data.error) return toast(data.error);
  const r = data.record;
  const fields = Object.entries(r).filter(([k]) => !["type", "label", "id", "event_count"].includes(k)).map(([k, v]) => {
    let shown = v;
    if (typeof v === "string" && /^[A-Z]{3}-\d{3}$/.test(v)) shown = `${v} (${labelOf(v)})`;
    else if (typeof v === "object" && v !== null) shown = JSON.stringify(v);
    return `<dt>${esc(k)}</dt><dd>${esc(shown)}</dd>`;
  }).join("");
  const events = data.events.map((e) => `<div class="event ${e.action === "refused" ? "refused" : ""}"><span class="t">${esc(e.time)}</span><span class="a">${esc(e.action)}</span>${esc(e.detail)} <span class="muted">(${esc(e.actor)})</span></div>`).join("");
  $("#record-detail").classList.remove("empty");
  $("#record-detail").innerHTML = `<h3>${esc(r.type)} &middot; ${esc(r.label)} <span class="mono muted">${esc(r.id)}</span></h3>
    <dl>${fields}</dl><div class="events"><strong>History (${data.events.length})</strong>${events || '<p class="muted">no events</p>'}</div>`;
  // scroll to the Records section so the panel is visible, and highlight the row
  showTab("records", true);
  drawRecordTable();
}

// ---------------------------------------------------------------- 4c. OPERATIONS
// The section shows a handful of FEATURED operations (the ones the scenarios use most).
// Any of the others can be added from the drop-down menu.
const FEATURED_OPS = ["substitute_aircraft", "swap_crew", "declare_delay", "cancel_flight",
                      "check_in_passenger", "offload_passenger", "declare_handling", "defer_defect"];
let pickedOps = [];          // operations the user added from the menu (shown first)

function allOps() {
  const out = [];
  for (const [area, list] of Object.entries(META.operations)) for (const op of list) out.push({ ...op, area });
  return out;
}

function opCard(op) {
  const inputs = op.params.map((p) => {
    const hint = p.required ? "required" : `default ${p.default}`;
    const useList = /(aircraft|flight|segment|crew|employee|engineer|passenger|booking|bag|consignment|load|defect|work_order|component|restriction|assignment|option|disruption|document|qualification|customer|shipper|agent|airport|origin|destination|holder|service|corporate|pir|inspection|replacement|new_flight|new_aircraft|accepted_by|handler|base|new_airport|connecting_from|agreement)$/.test(p.name);
    return `<label>${esc(p.name)} <span class="muted">(${hint})</span>
      <input name="${esc(p.name)}" ${useList ? 'list="all-ids"' : ""} placeholder="${useList ? "record id, e.g. FLT-001" : ""}"></label>`;
  }).join("");
  return `<div class="op-card" id="op-${esc(op.name)}"><h3>${esc(op.name)}<span class="area">${esc(op.area)}</span></h3>
    <div class="doc">${esc(op.doc.replace(/\s+/g, " "))}</div>
    <form class="op-form" data-op="${esc(op.name)}">${inputs}<div><button class="btn btn-primary btn-small" type="submit">Run</button></div></form>
    <div class="op-result"></div></div>`;
}

function renderOperations() {
  const ops = allOps();
  // the menu: every operation grouped by area
  const picker = $("#op-picker");
  picker.innerHTML = `<option value="">Add another operation…</option>` +
    Object.entries(META.operations).map(([area, list]) =>
      `<optgroup label="${esc(area)}">${list.map((o) => `<option value="${esc(o.name)}">${esc(o.name)}</option>`).join("")}</optgroup>`).join("");
  // the cards: picked ones first, then the featured set
  const names = [...pickedOps, ...FEATURED_OPS.filter((n) => !pickedOps.includes(n))];
  $("#op-list").innerHTML = names.map((n) => ops.find((o) => o.name === n)).filter(Boolean).map(opCard).join("");
}

// Called when a form's Run button is pressed
async function runOperation(form) {
  const args = {};
  for (const input of form.querySelectorAll("input")) if (input.value.trim() !== "") args[input.name] = input.value;
  const box = form.parentElement.querySelector(".op-result");
  const data = await api("POST", "/api/op/" + form.dataset.op, args);
  const events = (data.events || []).map((e) => `<div>${esc(e.time)} <b>${esc(e.subject_label)}</b> ${esc(e.action)}: ${esc(e.detail)}</div>`).join("");
  if (data.ok) {
    box.className = "op-result ok";
    box.innerHTML = `<b>Done.</b> Result: ${esc(JSON.stringify(data.result))}${events}`;
  } else if (data.refused) {
    box.className = "op-result refused";
    box.innerHTML = `<b>Refused by a business rule:</b> ${esc(data.refused)}${events}`;
  } else {
    box.className = "op-result error";
    box.innerHTML = `<b>Could not run:</b> ${esc(data.error)} <span class="muted">(check the argument names/ids)</span>`;
  }
  await refresh();
}

// ---------------------------------------------------------------- 4d. SCENARIOS
function renderDemos() {
  $("#demo-list").innerHTML = META.demos.map((d, i) => {
    const result = DEMO_RESULTS.find((r) => r.name === d.name);
    return `<div class="demo" id="demo-${d.name}"><div class="demo-head"><div>
        <h3>${i + 1}. ${esc(d.name.replace(/^demo_/, "").replace(/_/g, " "))}</h3><div class="demo-title">${esc(d.title)}</div></div>
        <button class="btn btn-small" data-demo="${d.name}">Run this scenario</button></div>
        <div class="story">${result ? storyHtml(result.story) : ""}</div></div>`;
  }).join("");
}

function storyHtml(story) {
  return story.map((l) => `<div class="line ${l.kind}"><span class="t">${esc(l.time)}</span>${l.kind === "refused" ? '<span class="k-refused">refused </span>' : ""}${l.kind === "check" ? '<span class="k-check">check </span>' : ""}${esc(l.text)}</div>`).join("");
}

async function runDemo(name) {
  const data = await api("POST", "/api/demo/" + name);
  if (!data.ok) return toast("Scenario failed: " + data.error);
  DEMO_RESULTS.push(data.result);
  renderDemos();
  await refresh();
  toast(`Scenario finished: ${data.result.story.length} steps recorded`);
}

async function runAll() {
  toast("Resetting the day and running every scenario...");
  const data = await api("POST", "/api/demo-all");
  DEMO_RESULTS = data.results;
  renderDemos();
  await refresh();
  await renderReport();
  showTab("scenarios");
  toast("Full day complete. Scroll on for the journal and the end-of-day report.");
}

// ---------------------------------------------------------------- 4e. JOURNAL
function renderJournal() {
  const filter = $("#journal-filter").value.toLowerCase();
  const refusedOnly = $("#journal-refused-only").checked;
  let rows = STATE.journal.slice().reverse();          // newest first
  if (refusedOnly) rows = rows.filter((e) => e.action === "refused");
  if (filter) rows = rows.filter((e) => `${e.subject_label} ${e.subject_type} ${e.action} ${e.detail} ${e.actor}`.toLowerCase().includes(filter));
  const total = rows.length;
  rows = rows.slice(0, MAX_ROWS);
  $("#journal-count").textContent = total > MAX_ROWS ? `latest ${MAX_ROWS} of ${total} events - use the filter for older ones` : `${total} event(s)`;
  $("#journal-table").innerHTML = table(rows, [
    { key: "time", label: "Time" }, { key: "subject_type", label: "Record type" },
    { key: "subject_label", label: "Record" },
    { label: "Action", render: (e) => e.action === "refused" ? `<span class="pill s-bad">refused</span>` : esc(e.action) },
    { key: "detail", label: "Detail" }, { key: "actor", label: "By" },
  ], (e) => `class="clickable" data-open="${e.subject_id}"`);
}

// ---------------------------------------------------------------- 4f. REPORT
async function renderReport() {
  const r = await api("GET", "/api/report");
  const flights = table(r.flights, [
    { key: "flight", label: "Flight" }, { key: "route", label: "Route" }, { label: "Status", render: (f) => pill(f.status) },
    { key: "std", label: "STD" }, { key: "etd", label: "ETD" }, { label: "Aircraft chain", render: (f) => esc(f.aircraft_chain.join(" -> ") || "-") },
    { label: "Passengers", render: (f) => esc(JSON.stringify(f.passengers_by_status)) },
    { key: "bags", label: "Bags" }, { label: "Cargo", render: (f) => esc(f.cargo_loads.join(", ")) },
    { label: "Movement", render: (f) => esc(f.movement || "-") },
    { label: "Crew", render: (f) => f.crew.map((c) => esc(c)).join("<br>") },
  ]);
  const disruptions = r.disruptions.map((d) => `<li><b>${esc(d.declared)} ${esc(d.type)}</b> ${esc(d.flight)} [${esc(d.reason)}] ${esc(d.description)}<br>
      <span class="muted">Resolution: ${esc(d.resolution || "-")}. Affected: ${esc(d.affected.join(", ") || "-")}</span>
      ${d.options.length ? `<br><span class="muted">Options: ${esc(d.options.join(" | "))}</span>` : ""}</li>`).join("");
  const refused = r.refused_attempts.map((e) => `<li>${esc(e.time)} <b>${esc(e.subject_label)}</b>: ${esc(e.detail)}</li>`).join("");
  const ended = r.periods_ended_today.map((p) => `<li>${esc(p.type)} ${esc(p.label)} ${esc(p.from)}-${esc(p.to)} ${pill(p.status)}</li>`).join("");
  const defects = r.defects.map((d) => `<li>${esc(d.id)} ${esc(d.aircraft)}: ${esc(d.description)} ${pill(d.status)} ${d.grounding ? '<span class="pill s-bad">grounding</span>' : ""} ${d.mel ? esc(d.mel) : ""}</li>`).join("");
  const open = r.open_items.map((o) => `<li>${esc(o)}</li>`).join("");
  $("#report").innerHTML = `
    <div class="report-block"><h2>What changed, who was affected, and why</h2>
      <p class="muted">${r.totals.records} records, ${r.totals.events} history events, ${r.totals.classes_in_use} classes in use. Nothing was deleted.</p>${flights}</div>
    <div class="two-col">
      <div class="report-block"><h3>Disruptions (${r.disruptions.length})</h3><ul>${disruptions || "<li>none</li>"}</ul></div>
      <div class="report-block"><h3>Attempts refused by business rules (${r.refused_attempts.length})</h3><ul>${refused || "<li>none</li>"}</ul></div>
      <div class="report-block"><h3>Engineering</h3><ul>${defects || "<li>none</li>"}</ul></div>
      <div class="report-block"><h3>Open items at close of day</h3><ul>${open || "<li>none</li>"}</ul></div>
    </div>
    <div class="report-block"><h3>Periods that ended today (still on file for historical queries)</h3><ul>${ended || "<li>none</li>"}</ul></div>`;
}

// ---------------------------------------------------------------- 4g. DESIGN
function renderDesign() {
  const byModule = {};
  for (const c of META.classes) (byModule[c.module] = byModule[c.module] || []).push(c);
  const list = Object.entries(byModule).map(([m, classes]) => `<h3>${esc(m)}.py</h3>` + table(classes, [
    { label: "Class", render: (c) => `<span class="mono">${"&nbsp;&nbsp;".repeat(c.depth - 1)}${esc(c.name)}</span>` },
    { label: "Inherits from", render: (c) => `<span class="mono">${esc(c.base)}</span>` },
    { key: "prefix", label: "Id prefix" }, { key: "doc", label: "What it is" },
  ])).join("");
  const treeHtml = (node, level = 0) => `<li><span class="cls lvl${level}">${esc(node.name)}</span>${node.children.length ? `<ul>${node.children.map((k) => treeHtml(k, level + 1)).join("")}</ul>` : ""}</li>`;
  const opCount = Object.values(META.operations).reduce((n, l) => n + l.length, 0);
  const ops = Object.entries(META.operations).map(([area, list]) => `<h3>${esc(area)} (${list.length})</h3><ul>${list.map((o) => `<li><span class="mono">${esc(o.name)}(${o.params.map((p) => p.name).join(", ")})</span></li>`).join("")}</ul>`).join("");
  $("#design").innerHTML = `
    <div class="two-col">
      <div class="report-block"><h2>Inheritance tree (${META.classes.length} classes)</h2>
        <p class="muted">Deeper colour = deeper level. Record &rarr; Person &rarr; Employee &rarr; CrewMember &rarr; FlightDeckCrew is the multi-level chain.</p>
        <div class="tree"><ul>${treeHtml(META.tree)}</ul></div></div>
      <div class="report-block"><h2>Operations (${opCount})</h2>${ops}</div>
    </div>
    <div class="report-block"><h2>Classes by module</h2>${list}</div>`;
}

// ---------------------------------------------------------------- 5. wiring
// The site is one long page.  "showTab" just scrolls to that section
// (to its content block when asked, otherwise to its hero).
function showTab(name, scrollToContent = false) {
  const page = $("#tab-" + name);
  if (name === "report") renderReport();
  const target = scrollToContent ? page.querySelector(".content") : page;
  target.scrollIntoView({ behavior: "smooth", block: "start" });
}

// Only play the hero videos that are on screen (saves CPU with several videos on one page)
function watchVideos() {
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) { if (e.isIntersecting) e.target.play().catch(() => {}); else e.target.pause(); }
  }, { threshold: 0.2 });
  $$("video.hero-media").forEach((v) => io.observe(v));
}

document.addEventListener("click", async (event) => {
  const el = event.target;
  if (el.matches("button[data-demo]")) return runDemo(el.dataset.demo);
  const row = el.closest("tr[data-open]");
  if (row) return openRecord(row.dataset.open);
});

document.addEventListener("submit", (event) => {
  if (event.target.matches("form.op-form")) { event.preventDefault(); runOperation(event.target); }
});

$("#op-picker").addEventListener("change", (e) => {
  const name = e.target.value;
  if (name && !pickedOps.includes(name)) pickedOps.unshift(name);
  renderOperations();
  const card = document.getElementById("op-" + name);
  if (card) card.scrollIntoView({ behavior: "smooth", block: "center" });
});
$("#record-class").addEventListener("change", drawRecordTable);
$("#record-filter").addEventListener("input", drawRecordTable);
$("#journal-filter").addEventListener("input", renderJournal);
$("#journal-refused-only").addEventListener("change", renderJournal);
$("#btn-run-all").addEventListener("click", runAll);
$("#btn-reset").addEventListener("click", async () => { await api("POST", "/api/reset"); DEMO_RESULTS = []; renderDemos(); await refresh(); toast("Day reset to 04:00 seed state"); });

// Start: load the catalogue once, then the data
(async function start() {
  META = await api("GET", "/api/meta");
  DEMO_RESULTS = await api("GET", "/api/demo-results");
  $("#op-count").textContent = Object.values(META.operations).reduce((n, l) => n + l.length, 0);
  $("#class-count").textContent = META.classes.length;
  renderOperations();
  renderDemos();
  renderDesign();
  await refresh();
  await renderReport();
  watchVideos();
})();
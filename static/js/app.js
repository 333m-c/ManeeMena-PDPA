"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  const data = $("app-data");
  const rules = JSON.parse(data.dataset.rules);
  const samples = JSON.parse(data.dataset.samples);
  const machines = JSON.parse(data.dataset.machines || "{}");
  const ruleMap = Object.fromEntries(rules.map((rule) => [rule.key, rule]));
  const limit = Number(data.dataset.limit);
  const playground = document.body.dataset.page === "playground";
  const input = $("input-log");
  if (!input) return;

  let selectedRule = rules[0].key;
  let result = null;
  let scannedText = "";
  let inputView = "edit";
  let compare = false;
  let controller = null;
  let revision = 0;
  let toastTimer;
  let activeDetection = null;
  let revealed = false;
  let machine = null;
  let machineReady = false;
  let traceStep = -1;
  let playTimer = null;

  const characters = (text) => Array.from(text);
  const formatNumber = (number) => number.toLocaleString("en-US");
  const setText = (id, text) => { if ($(id)) $(id).textContent = text; };
  const enabledRules = () => playground
    ? Object.fromEntries(rules.map((rule) => [rule.key, rule.key === selectedRule]))
    : Object.fromEntries(Array.from(document.querySelectorAll(".rule-checkbox"), (box) => [box.value, box.checked]));

  function toast(message) {
    clearTimeout(toastTimer);
    $("toast").textContent = message;
    $("toast").hidden = false;
    toastTimer = setTimeout(() => { $("toast").hidden = true; }, 3500);
  }

  function updateCounters() {
    const text = input.value;
    const count = characters(text).length;
    const lines = text ? text.split(/\r\n|\r|\n/).length : 0;
    setText("input-count", `${formatNumber(count)} characters · ${formatNumber(lines)} lines`);
    const active = Object.values(enabledRules()).filter(Boolean).length;
    setText("stat-rules", String(active).padStart(2, "0"));
    setText("toggle-all", active === rules.length ? "Disable all" : "Enable all");
    setText("input-help", count > limit ? "50,000 character limit exceeded" : "Plain text only");
  }

  function busy(value) {
    $("scan").disabled = value;
    $("scan").closest(".workspace").setAttribute("aria-busy", String(value));
    setText("scan-label", value ? "Scanning…" : playground ? "Test pattern" : "Scan & Mask");
    if (playground) updateMachineControls();
  }

  function invalidate(message = "Input or rules changed. Scan again.") {
    revision += 1;
    if (controller) controller.abort();
    controller = null;
    result = null;
    scannedText = "";
    activeDetection = null;
    if ($("detection-dialog").open) $("detection-dialog").close();
    $("dialog-preview").textContent = "";
    inputView = "edit";
    compare = false;
    busy(false);
    ["copy", "download", "detected-view", "compare-view"].forEach((id) => { $(id).disabled = true; });
    $("output-log").textContent = "";
    $("source-preview").textContent = "";
    $("output-log").hidden = true;
    $("output-empty").hidden = false;
    $("scan-error").hidden = true;
    $("inspector-list").replaceChildren();
    $("inspector-list").hidden = true;
    $("inspector-empty").hidden = false;
    $("inspector-empty").querySelector("strong").textContent = "No detections yet";
    $("inspector-empty").querySelector("p").textContent = "Run a scan to explore the matches.";
    setText("inspector-count", "0");
    setText("stat-detected", "—");
    setText("stat-masked", "—");
    setText("stat-risk", "Not scanned");
    document.querySelectorAll(".risk-meter i").forEach((item) => item.classList.remove("filled"));
    const riskCard = document.querySelector(".risk-card");
    if (riskCard) delete riskCard.dataset.level;
    setText("stat-detected-caption", "Across your enabled rules");
    setText("output-count", "Waiting for a scan");
    setText("scan-status", message);
    const enabled = enabledRules();
    rules.forEach((rule) => setText(`count-${rule.key}`, enabled[rule.key] ? "Ready to detect" : "Disabled"));
    updateCounters();
    renderViews();
    if (playground && machine) resetMachineInput();
  }

  // Python offsets count Unicode code points, while JS string offsets count
  // UTF-16 code units. Slice arrays of code points so emoji never shift marks.
  function renderHighlights(target, text, spans) {
    const points = characters(text);
    const fragment = document.createDocumentFragment();
    let cursor = 0;
    for (const span of spans) {
      fragment.append(document.createTextNode(points.slice(cursor, span.start).join("")));
      const mark = document.createElement("mark");
      mark.className = span.className;
      mark.textContent = points.slice(span.start, span.end).join("");
      mark.dataset.detection = span.detection.id;
      mark.title = `${ruleMap[span.detection.rule].label} · Click to explain`;
      mark.tabIndex = 0;
      mark.setAttribute("role", "button");
      mark.setAttribute("aria-label", `Explain ${ruleMap[span.detection.rule].label} on line ${span.detection.line}`);
      fragment.append(mark);
      cursor = span.end;
    }
    fragment.append(document.createTextNode(points.slice(cursor).join("")));
    target.replaceChildren(fragment);
  }

  function renderViews() {
    input.hidden = inputView !== "edit";
    $("source-preview").hidden = inputView === "edit";
    $("edit-view").setAttribute("aria-pressed", String(inputView === "edit"));
    $("detected-view").setAttribute("aria-pressed", String(inputView === "detections"));
    $("compare-view").setAttribute("aria-pressed", String(compare));
    $("masked-view").setAttribute("aria-pressed", String(!compare));
    if (!result) return;
    const sourceSpans = [];
    const outputSpans = [];
    for (const detection of result.detections) {
      if (compare) {
        for (const change of detection.changes) {
          sourceSpans.push({ start: change.start, end: change.end, className: "changed-source", detection });
          outputSpans.push({ start: change.output_start, end: change.output_end, className: "changed-output", detection });
        }
      } else {
        sourceSpans.push({ start: detection.start, end: detection.end, className: `rule-${detection.rule}`, detection });
        outputSpans.push({ start: detection.output_start, end: detection.output_end, className: `rule-${detection.rule}`, detection });
      }
    }
    renderHighlights($("source-preview"), scannedText, sourceSpans);
    renderHighlights($("output-log"), result.masked_text, outputSpans);
  }

  function renderInspector() {
    const fragment = document.createDocumentFragment();
    result.detections.forEach((detection) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `detection-row rule-${detection.rule}`;
      button.dataset.detection = detection.id;
      button.setAttribute("aria-label", `Explain ${ruleMap[detection.rule].label} on line ${detection.line}`);
      for (const [className, text] of [
        ["type-badge", ruleMap[detection.rule].label],
        ["detection-preview", detection.masked_preview],
        ["detection-line", `Line ${detection.line}`],
        ["detection-arrow", "↗"],
      ]) {
        const span = document.createElement("span");
        span.className = className;
        span.textContent = text;
        button.append(span);
      }
      fragment.append(button);
    });
    $("inspector-list").replaceChildren(fragment);
    $("inspector-list").hidden = result.detections.length === 0;
    $("inspector-empty").hidden = result.detections.length > 0;
    if (!result.detections.length) {
      $("inspector-empty").querySelector("strong").textContent = "No matches in this scan";
      $("inspector-empty").querySelector("p").textContent = "Only the enabled patterns were checked.";
    }
    setText("inspector-count", formatNumber(result.total_detected));
  }

  function updateResultStats() {
    setText("stat-detected", String(result.total_detected).padStart(2, "0"));
    setText("stat-masked", String(result.masked_characters).padStart(2, "0"));
    const settings = enabledRules();
    const active = Object.values(settings).filter(Boolean).length;
    setText("stat-detected-caption", `Across ${active} enabled ${active === 1 ? "rule" : "rules"}`);
    rules.forEach((rule) => {
      const count = result.counts[rule.key];
      setText(`count-${rule.key}`, settings[rule.key] ? `${count} ${count === 1 ? "match" : "matches"} found` : "Disabled");
    });
    const count = result.total_detected;
    const level = count === 0 ? 0 : count <= 2 ? 1 : count <= 5 ? 2 : count <= 10 ? 3 : 4;
    const label = ["Safe", "Low", "Medium", "High", "Critical"][level];
    setText("stat-risk", label);
    const card = document.querySelector(".risk-card");
    if (card) {
      card.dataset.level = label;
      card.querySelectorAll(".risk-meter i").forEach((bar, index) => bar.classList.toggle("filled", index <= level));
    }
    setText("output-count", `${formatNumber(result.total_detected)} detected · ${formatNumber(result.masked_characters)} characters masked`);
  }

  async function scan() {
    invalidate("Scanning your text…");
    const text = input.value;
    if ((!playground && !text.trim()) || characters(text).length > limit) {
      setText("scan-error", !playground && !text.trim() ? "Enter some text to scan." : "Keep your input within 50,000 characters.");
      $("scan-error").hidden = false;
      setText("scan-status", "Your text has not been sent.");
      input.focus();
      return false;
    }
    const scanRevision = revision;
    controller = new AbortController();
    const requestController = controller;
    let timedOut = false;
    const timeout = setTimeout(() => { timedOut = true; requestController.abort(); }, 15000);
    busy(true);
    try {
      const response = await fetch("/api/mask", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, rules: enabledRules(), ...(playground ? { trace_rule: selectedRule } : {}) }), signal: requestController.signal,
        cache: "no-store",
      });
      const payload = await response.json();
      if (scanRevision !== revision) return false;
      if (!response.ok || !payload.success) throw new Error(payload.error || "The scan could not be completed.");
      result = payload;
      scannedText = text;
      ["copy", "download", "detected-view", "compare-view"].forEach((id) => { $(id).disabled = false; });
      $("output-empty").hidden = true;
      $("output-log").hidden = false;
      updateResultStats();
      renderInspector();
      renderViews();
      if (playground) {
        machine = payload.machine;
        machineReady = true;
        traceStep = -1;
        renderTape(machine);
        showTrace();
      }
      const unchanged = payload.detections.filter((detection) => !detection.changes.length).length;
      const allDisabled = Object.values(enabledRules()).every((enabled) => !enabled);
      setText("scan-status", allDisabled
        ? "All rules are disabled, so nothing was checked."
        : `Scan complete · ${payload.total_detected} ${payload.total_detected === 1 ? "match" : "matches"}.${unchanged ? ` ${unchanged} short email ${unchanged === 1 ? "username stays" : "usernames stay"} visible.` : ""}`);
      return true;
    } catch (error) {
      if (scanRevision !== revision) return false;
      setText("scan-error", timedOut ? "The scan timed out. Try a smaller log." : error instanceof TypeError || error instanceof SyntaxError ? "Unable to reach the masking service." : error.message);
      $("scan-error").hidden = false;
      setText("scan-status", "Scan unsuccessful. Your input is still here.");
      if (playground) setText("machine-caption", "Unable to test this input. Try again.");
      return false;
    } finally {
      clearTimeout(timeout);
      if (scanRevision === revision) { controller = null; busy(false); }
    }
  }

  function renderTokens(target, rule) {
    target.replaceChildren();
    rule.tokens.forEach(({ syntax, meaning }) => {
      const row = document.createElement("div");
      row.className = "token-row";
      const code = document.createElement("code");
      code.textContent = syntax;
      const explanation = document.createElement("p");
      explanation.textContent = meaning;
      row.append(code, explanation);
      target.append(row);
    });
  }

  function explain(id) {
    if (!result) return;
    activeDetection = result.detections[id];
    const rule = ruleMap[activeDetection.rule];
    revealed = false;
    setText("dialog-title", `Why was this detected? · ${rule.label}`);
    setText("dialog-description", rule.description);
    setText("dialog-pattern", rule.pattern);
    setText("dialog-preview", activeDetection.masked_preview);
    setText("preview-label", `Masked preview · Line ${activeDetection.line}`);
    setText("reveal-match", "Reveal matched text");
    renderTokens($("dialog-tokens"), rule);
    $("detection-dialog").showModal();
  }

  document.addEventListener("click", (event) => {
    const target = event.target.closest("[data-detection]");
    if (target) explain(Number(target.dataset.detection));
  });
  document.addEventListener("keydown", (event) => {
    if ((event.key === "Enter" || event.key === " ") && event.target.matches("mark[data-detection]")) {
      event.preventDefault();
      explain(Number(event.target.dataset.detection));
    }
  });
  $("close-dialog").addEventListener("click", () => $("detection-dialog").close());
  $("detection-dialog").addEventListener("close", () => {
    setText("dialog-preview", "");
    activeDetection = null;
    revealed = false;
  });
  $("reveal-match").addEventListener("click", () => {
    if (!activeDetection) return;
    revealed = !revealed;
    setText("dialog-preview", revealed
      ? characters(scannedText).slice(activeDetection.start, activeDetection.end).join("")
      : activeDetection.masked_preview);
    setText("preview-label", `${revealed ? "Matched text" : "Masked preview"} · Line ${activeDetection.line}`);
    setText("reveal-match", revealed ? "Hide matched text" : "Reveal matched text");
  });
  $("scan").addEventListener("click", scan);
  input.addEventListener("input", () => invalidate());
  input.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") { event.preventDefault(); scan(); }
  });
  document.querySelectorAll(".rule-checkbox").forEach((box) => box.addEventListener("change", () => invalidate()));
  if ($("toggle-all")) $("toggle-all").addEventListener("click", () => {
    const allEnabled = Object.values(enabledRules()).every(Boolean);
    document.querySelectorAll(".rule-checkbox").forEach((box) => { box.checked = !allEnabled; });
    invalidate();
  });
  $("edit-view").addEventListener("click", () => { inputView = "edit"; compare = false; renderViews(); });
  $("detected-view").addEventListener("click", () => { inputView = "detections"; compare = false; renderViews(); });
  $("compare-view").addEventListener("click", () => { inputView = "compare"; compare = true; renderViews(); });
  $("masked-view").addEventListener("click", () => { compare = false; if (inputView === "compare") inputView = "detections"; renderViews(); });

  function loadSample() {
    input.value = playground ? ruleMap[selectedRule].sample : samples[0].text;
    invalidate("Sample loaded. Ready to scan.");
  }
  $("load-sample").addEventListener("click", loadSample);

  function accept(text, origin) {
    if (/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(text)) {
      toast("That looks like a binary file, not text.");
      return;
    }
    if (characters(text).length > limit) {
      toast(`Too long: keep it within ${formatNumber(limit)} characters.`);
      return;
    }
    input.value = text;
    inputView = "edit";
    invalidate(`${origin} Ready to scan.`);
    input.focus();
  }

  $("upload").addEventListener("click", () => $("file-input").click());
  $("file-input").addEventListener("change", async (event) => {
    const [file] = event.target.files;
    event.target.value = "";
    if (!file) return;
    try {
      accept(await file.text(), `Loaded ${file.name}.`);
    } catch {
      toast("That file could not be read as UTF-8 text.");
    }
  });
  $("paste").addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (!text) {
        toast("Your clipboard is empty.");
        return;
      }
      accept(text, "Pasted from the clipboard.");
    } catch {
      toast("The browser blocked clipboard access. Press Ctrl+V in the box instead.");
      inputView = "edit";
      renderViews();
      input.focus();
    }
  });
  const dropZone = $("drop-zone");
  ["dragenter", "dragover"].forEach((name) => dropZone.addEventListener(name, (event) => {
    if (![...event.dataTransfer.types].includes("Files")) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    dropZone.classList.add("dropping");
  }));
  ["dragleave", "dragend"].forEach((name) => dropZone.addEventListener(name, (event) => {
    if (event.target === dropZone || name !== "dragleave") dropZone.classList.remove("dropping");
  }));
  dropZone.addEventListener("drop", async (event) => {
    const [file] = event.dataTransfer.files;
    if (!file) return;
    event.preventDefault();
    dropZone.classList.remove("dropping");
    try {
      accept(await file.text(), `Loaded ${file.name}.`);
    } catch {
      toast("That file could not be read as UTF-8 text.");
    }
  });

  $("clear").addEventListener("click", () => {
    input.value = "";
    invalidate("Workspace cleared.");
    $("toast").hidden = true;
    input.focus();
  });
  $("copy").addEventListener("click", async () => {
    if (!result) return;
    const text = result.masked_text;
    try {
      await navigator.clipboard.writeText(text);
      toast("Masked text copied to clipboard.");
    } catch {
      const field = document.createElement("textarea");
      field.className = "clipboard-fallback";
      field.value = text;
      document.body.append(field);
      field.select();
      const copied = document.execCommand("copy");
      field.remove();
      toast(copied ? "Masked text copied to clipboard." : "Copy was blocked. Select and copy the masked output manually.");
    }
  });
  $("download").addEventListener("click", () => {
    if (!result) return;
    const url = URL.createObjectURL(new Blob([result.masked_text], { type: "text/plain;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "masked_log.txt";
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast("Masked log downloaded.");
  });

  // ---- Automaton drawing -------------------------------------------------
  // Python supplies the states, transitions and a replay of the current input.
  const SVG = "http://www.w3.org/2000/svg";
  const RADIUS = 20, COLUMN = 118, BASE_ROW = 88, LOOP_ROOM = 48, SKIP_ROOM = 54, MARGIN = 46, EDGE_PAD = 34;
  const PROBE = Array.from("0123456789AZaz_.-+%@/: \t");

  const shape = (name, attributes, text) => {
    const node = document.createElementNS(SVG, name);
    for (const key in attributes) node.setAttribute(key, attributes[key]);
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const reads = (symbol) => new RegExp(`^(?:${symbol})$`);
  // Classes are shown as written; a single literal gets quotes so a hyphen or
  // a dot reads as a symbol rather than a stray mark.
  const symbolText = (edge) => {
    if (edge.kind === "skip") return "ε";
    if (edge.symbol.startsWith("[")) return edge.symbol;
    return `'${edge.symbol.replace(/^\\/, "")}'`;
  };

  function classify(current) {
    const branching = current.states.some((state, index) => {
      const out = current.edges.filter((edge) => edge.from === index);
      if (out.some((edge) => edge.kind === "skip") && out.length > 1) return true;
      const tests = out.filter((edge) => edge.kind !== "skip").map((edge) => reads(edge.symbol));
      return PROBE.some((character) => tests.filter((test) => test.test(character)).length > 1);
    });
    return `${branching ? "NFA" : "DFA"} · ${current.states.length} states · ${current.edges.length} transitions`;
  }

  function drawMachine(current) {
    const rows = [];
    current.states.forEach((state, index) => (rows[state.row] = rows[state.row] || []).push(index));
    const hasLoop = rows.map((row) => current.edges.some((edge) => edge.kind === "loop" && row.includes(edge.from)));
    const hasSkip = rows.map((row) => current.edges.some((edge) => edge.kind === "skip" && row.includes(edge.from)));
    const tops = rows.map(() => 0);
    rows.forEach((row, index) => {
      tops[index] = index === 0
        ? EDGE_PAD + RADIUS + (hasLoop[0] ? LOOP_ROOM : 0)
        : tops[index - 1] + BASE_ROW + (hasSkip[index - 1] ? SKIP_ROOM : 0) + (hasLoop[index] ? LOOP_ROOM : 0);
    });
    // Widen the columns for long character classes so a label never runs past
    // the two states it belongs to.
    const column = Math.max(COLUMN, Math.max(...current.edges.map((edge) => symbolText(edge).length)) * 8 + 30);
    const at = [];
    rows.forEach((row, rowIndex) => row.forEach((state, index) => {
      at[state] = { x: MARGIN + RADIUS + index * column, y: tops[rowIndex] };
    }));
    const width = MARGIN * 2 + RADIUS * 2 + (Math.max(...rows.map((row) => row.length)) - 1) * column;
    const height = tops[tops.length - 1] + RADIUS + EDGE_PAD + (hasSkip[hasSkip.length - 1] ? SKIP_ROOM : 0);
    const root = shape("svg", { viewBox: `0 0 ${width} ${height}`, width, height, class: "machine-svg" });

    const defs = shape("defs");
    for (const variant of ["read", "mask", "skip", "live"]) {
      const marker = shape("marker", { id: `head-${variant}`, viewBox: "0 0 10 10", refX: "8.5", refY: "5",
        markerWidth: "9", markerHeight: "9", markerUnits: "userSpaceOnUse", orient: "auto" });
      marker.append(shape("path", { d: "M0 0 10 5 0 10Z", class: `head head-${variant}` }));
      defs.append(marker);
    }
    root.append(defs);

    const first = at[0];
    root.append(shape("path", { class: "edge-line", "marker-end": "url(#head-read)",
      d: `M ${first.x - RADIUS - 28} ${first.y} L ${first.x - RADIUS - 5} ${first.y}` }));
    root.append(shape("text", { class: "machine-hint", x: first.x - RADIUS - 17, y: first.y - 14, "text-anchor": "middle" }, "start"));

    current.edges.forEach((edge, index) => {
      const from = at[edge.from];
      const to = at[edge.to];
      let path;
      let label;
      if (edge.kind === "loop") {
        path = `M ${from.x - 11} ${from.y - RADIUS + 3} C ${from.x - 38} ${from.y - RADIUS - 36} ${from.x + 38} ${from.y - RADIUS - 36} ${from.x + 11} ${from.y - RADIUS + 3}`;
        label = { x: from.x, y: from.y - RADIUS - 32 };
      } else if (edge.kind === "skip") {
        path = `M ${from.x} ${from.y + RADIUS + 2} C ${from.x + 26} ${from.y + RADIUS + 40} ${to.x - 26} ${to.y + RADIUS + 40} ${to.x} ${to.y + RADIUS + 4}`;
        label = { x: (from.x + to.x) / 2, y: (from.y + to.y) / 2 + RADIUS + 54 };
      } else if (from.y === to.y) {
        path = `M ${from.x + RADIUS + 3} ${from.y} L ${to.x - RADIUS - 5} ${to.y}`;
        label = { x: (from.x + to.x) / 2, y: from.y - 13 };
      } else {
        const right = width - 16;
        const left = 16;
        const lane = from.y + RADIUS + (hasSkip[current.states[edge.from].row] ? SKIP_ROOM : 0) + 22;
        const bend = 12;
        path = `M ${from.x + RADIUS + 3} ${from.y} H ${right - bend} Q ${right} ${from.y} ${right} ${from.y + bend}`
          + ` V ${lane - bend} Q ${right} ${lane} ${right - bend} ${lane} H ${left + bend}`
          + ` Q ${left} ${lane} ${left} ${lane + bend} V ${to.y - bend} Q ${left} ${to.y} ${left + bend} ${to.y} H ${to.x - RADIUS - 5}`;
        label = { x: (left + right) / 2, y: lane - 10 };
      }
      const group = shape("g", { class: `edge edge-${edge.kind}${edge.masked ? " masked" : ""}`, "data-edge": index });
      group.append(shape("title", {}, `${symbolText(edge)} — ${edge.meaning}`));
      group.append(shape("path", { class: "edge-hit", d: path }));
      group.append(shape("path", { class: "edge-line", d: path,
        "marker-end": `url(#head-${edge.masked ? "mask" : edge.kind === "skip" ? "skip" : "read"})` }));
      group.append(shape("text", { class: "edge-label", x: label.x, y: label.y, "text-anchor": "middle" }, symbolText(edge)));
      root.append(group);
    });

    current.states.forEach((state, index) => {
      const spot = at[index];
      const group = shape("g", { class: `state state-${state.kind}${state.guards.length ? " guarded" : ""}`, "data-state": index });
      const detail = state.guards.map((guard) => `${guard.symbol} — ${guard.meaning}`).join("\n");
      group.append(shape("title", {}, detail || `State ${state.id}`));
      if (state.guards.length) group.append(shape("circle", { class: "state-guard", cx: spot.x, cy: spot.y, r: RADIUS + 6 }));
      group.append(shape("circle", { class: "state-ring", cx: spot.x, cy: spot.y, r: RADIUS }));
      if (state.kind === "accept") group.append(shape("circle", { class: "state-inner", cx: spot.x, cy: spot.y, r: RADIUS - 4.5 }));
      group.append(shape("text", { class: "state-label", x: spot.x, y: spot.y + 4, "text-anchor": "middle" }, state.id));
      root.append(group);
    });

    $("machine-canvas").replaceChildren(root);
  }

  function renderTape(current) {
    const points = characters(current.input);
    const last = current.failure ? Math.min(points.length, current.failure.position + 1)
      : current.trace.length ? current.trace[current.trace.length - 1].end : current.offset;
    const fragment = document.createDocumentFragment();
    const plain = (text) => {
      if (!text) return;
      const span = document.createElement("span");
      span.className = "tape-outside";
      span.textContent = text;
      fragment.append(span);
    };
    plain(points.slice(0, current.offset).join(""));
    for (let index = current.offset; index < last; index += 1) {
      const cell = document.createElement("span");
      cell.className = "tape-cell";
      cell.dataset.index = index;
      cell.textContent = ({ " ": "␣", "\t": "⇥", "\n": "↵", "\r": "␍" })[points[index]] || points[index];
      fragment.append(cell);
    }
    if (current.failure?.position === points.length) {
      const end = document.createElement("span");
      end.className = "tape-cell tape-end";
      end.dataset.index = points.length;
      end.textContent = "EOF";
      end.title = "End of input";
      fragment.append(end);
    }
    plain(points.slice(last).join(""));
    $("machine-tape").replaceChildren(fragment);
  }

  function showTrace() {
    const rejected = machineReady && !!machine.failure && traceStep === machine.trace.length;
    const move = traceStep >= 0 ? machine.trace[Math.min(traceStep, machine.trace.length - 1)] : null;
    const state = rejected ? machine.failure.state : move ? move.to : 0;
    const head = rejected ? machine.failure.position : move ? move.end : machine.offset;
    const canvas = $("machine-canvas");
    canvas.querySelectorAll(".state").forEach((node) => {
      node.classList.toggle("current", Number(node.dataset.state) === state);
      node.classList.toggle("rejected", rejected && Number(node.dataset.state) === state);
    });
    canvas.querySelectorAll(".edge").forEach((node) => node.classList.toggle("active", !rejected && !!move && Number(node.dataset.edge) === move.edge));
    $("machine-tape").querySelectorAll(".tape-cell").forEach((cell) => {
      const index = Number(cell.dataset.index);
      cell.classList.toggle("read", index < head);
      cell.classList.toggle("head", index === head);
      cell.classList.toggle("rejected", rejected && index === head);
    });
    const done = machineReady && traceStep >= machineStepCount() - 1;
    const accepted = done && machine.matched && machine.states[state].kind === "accept";
    $("machine-result").hidden = !accepted && !rejected;
    $("machine-result").dataset.outcome = accepted ? "accepted" : rejected ? "rejected" : "";
    setText("machine-result", accepted ? "Accepted" : rejected ? "Rejected" : "");
    updateMachineControls();
    if (!machineReady) {
      setText("machine-caption", !input.value
        ? "Run input or Step to test the empty input, or enter text above."
        : characters(input.value).length > limit
          ? "Keep your input within 50,000 characters."
          : "Input changed. Run input, Step or Test pattern to update the machine.");
      return;
    }
    if (rejected) {
      const failure = machine.failure;
      const found = failure.character === null ? "end of input"
        : ({ " ": "a space", "\t": "a tab", "\n": "a line break", "\r": "a carriage return" })[failure.character]
          || `“${failure.character}”`;
      const location = failure.character === null ? `at the end of input (after ${head} characters)`
        : `before ${found} at character ${head + 1}`;
      const reason = failure.reason === "guard"
        ? `Boundary check failed: ${failure.guards.map((guard) => `${guard.symbol} · ${guard.meaning}`).join(" ")}`
        : `Expected ${failure.expected.join(" or ") || "the end of the pattern"}.`;
      setText("machine-caption", `Rejected · ${machine.states[state].id} stopped ${location}. ${reason}`);
      return;
    }
    if (!move) {
      setText("machine-caption", machine.matched
        ? `${machine.states[0].id} is the start state. Step through the first match in your input.`
        : "No match was found. Run input or Step to follow an attempt from the first character and see why it rejects.");
      return;
    }
    const edge = machine.edges[move.edge];
    const destination = `${move.to === edge.from ? "stays in" : "moves to"} ${machine.states[move.to].id}`;
    const action = edge.kind === "skip"
      ? `takes the ε bypass to ${machine.states[move.to].id}`
      : `reads “${move.text}” and ${destination}`;
    setText("machine-caption", `${machine.states[edge.from].id} ${action} · ${edge.meaning}${accepted ? " · accepted" : ""}`);
  }

  function machineStepCount() {
    return machine ? machine.trace.length + (machine.failure ? 1 : 0) : 0;
  }

  function updateMachineControls() {
    const unavailable = $("scan").disabled || characters(input.value).length > limit
      || (machineReady && !machineStepCount());
    $("machine-play").disabled = unavailable;
    $("machine-step").disabled = unavailable || (machineReady && traceStep >= machineStepCount() - 1);
    $("machine-reset").disabled = $("scan").disabled || !machineReady || !machineStepCount();
  }

  function stopPlaying() {
    clearInterval(playTimer);
    playTimer = null;
    setText("machine-play-label", "Run input");
    $("machine-play").classList.remove("playing");
  }

  function renderMachine(key) {
    drawMachine(machines[key]);
    setText("machine-badge", classify(machines[key]));
    resetMachineInput();
  }

  function resetMachineInput() {
    stopPlaying();
    traceStep = -1;
    const sample = machines[selectedRule];
    machineReady = input.value === sample.input;
    machine = machineReady ? sample : { ...sample, input: input.value, offset: 0, trace: [], matched: null, failure: null };
    renderTape(machine);
    showTrace();
  }

  async function prepareMachine() {
    if (!machineReady && !await scan()) return false;
    return machineReady && machineStepCount() > 0;
  }

  function stepMachine() {
    if (!machine || traceStep >= machineStepCount() - 1) return false;
    traceStep += 1;
    showTrace();
    return traceStep < machineStepCount() - 1;
  }

  if (playground) {
    $("machine-step").addEventListener("click", async () => {
      stopPlaying();
      if (await prepareMachine()) stepMachine();
    });
    $("machine-reset").addEventListener("click", () => {
      stopPlaying();
      traceStep = -1;
      showTrace();
    });
    $("machine-play").addEventListener("click", async () => {
      if (playTimer) {
        stopPlaying();
        return;
      }
      if (!await prepareMachine()) return;
      if (traceStep >= machineStepCount() - 1) traceStep = -1;
      setText("machine-play-label", "Pause");
      $("machine-play").classList.add("playing");
      showTrace();
      playTimer = setInterval(() => {
        if (!stepMachine()) stopPlaying();
      }, 620);
    });
    $("machine-canvas").addEventListener("click", (event) => {
      const edge = event.target.closest(".edge");
      if (edge) {
        const detail = machine.edges[Number(edge.dataset.edge)];
        setText("machine-caption", `${symbolText(detail)} · ${detail.meaning}`);
        return;
      }
      const state = event.target.closest(".state");
      if (!state) return;
      const guards = machine.states[Number(state.dataset.state)].guards;
      setText("machine-caption", guards.length
        ? guards.map((guard) => `${guard.symbol} · ${guard.meaning}`).join("  ")
        : `${machine.states[Number(state.dataset.state)].id} reads the next character and moves on.`);
    });
  }

  function selectPattern(key) {
    const useSample = !machine || input.value === ruleMap[selectedRule].sample;
    selectedRule = key;
    const rule = ruleMap[key];
    document.querySelectorAll(".pattern-choice").forEach((button) => {
      const selected = button.dataset.rule === key;
      button.setAttribute("aria-pressed", String(selected));
      button.querySelector(".pattern-status").textContent = selected ? "Selected" : "Select pattern";
    });
    setText("pattern-label", rule.label.toUpperCase());
    setText("pattern-code", rule.pattern);
    setText("pattern-description", rule.description);
    renderTokens($("pattern-tokens"), rule);
    renderMachine(key);
    if (useSample) loadSample();
    else invalidate("Pattern changed. Ready to test your text.");
  }
  if (playground) {
    document.querySelectorAll(".pattern-choice").forEach((button) => button.addEventListener("click", () => selectPattern(button.dataset.rule)));
    selectPattern(selectedRule);
  } else {
    const requestedSample = new URLSearchParams(location.search).get("sample");
    input.value = (samples.find((sample) => sample.id === requestedSample) || samples[0]).text;
    updateCounters();
  }
  // Do not restore entered logs from a browser back/forward cache.
  window.addEventListener("pagehide", () => {
    input.value = "";
    invalidate("Workspace cleared after navigation.");
  });
})();

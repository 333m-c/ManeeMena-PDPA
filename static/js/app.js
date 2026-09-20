"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  const data = $("app-data");
  const rules = JSON.parse(data.dataset.rules);
  const samples = JSON.parse(data.dataset.samples);
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
  }

  function invalidate(message = "Input or rules changed. Scan again to update your results.") {
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
    $("inspector-empty").querySelector("p").textContent = "Run a scan to explore matched patterns, locations and masking rules.";
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
      $("inspector-empty").querySelector("p").textContent = "Only enabled patterns are checked. Review your log before sharing it.";
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
    if (!text.trim() || characters(text).length > limit) {
      setText("scan-error", !text.trim() ? "Enter some text to scan." : "Keep your input within 50,000 characters.");
      $("scan-error").hidden = false;
      setText("scan-status", "Your text has not been sent.");
      input.focus();
      return;
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
        body: JSON.stringify({ text, rules: enabledRules() }), signal: requestController.signal,
        cache: "no-store",
      });
      const payload = await response.json();
      if (scanRevision !== revision) return;
      if (!response.ok || !payload.success) throw new Error(payload.error || "The scan could not be completed.");
      result = payload;
      scannedText = text;
      ["copy", "download", "detected-view", "compare-view"].forEach((id) => { $(id).disabled = false; });
      $("output-empty").hidden = true;
      $("output-log").hidden = false;
      updateResultStats();
      renderInspector();
      renderViews();
      const unchanged = payload.detections.filter((detection) => !detection.changes.length).length;
      const allDisabled = Object.values(enabledRules()).every((enabled) => !enabled);
      setText("scan-status", allDisabled
        ? "All rules are disabled. Output is unchanged; no patterns were checked."
        : `Scan complete. ${payload.total_detected} ${payload.total_detected === 1 ? "match" : "matches"} found.${unchanged ? ` ${unchanged} short email ${unchanged === 1 ? "username remains" : "usernames remain"} visible under the assignment policy.` : " Review the result before sharing."}`);
    } catch (error) {
      if (scanRevision !== revision) return;
      setText("scan-error", timedOut ? "The scan timed out. Try a smaller log or scan again." : error instanceof TypeError || error instanceof SyntaxError ? "Unable to reach the masking service. Check the server and try again." : error.message);
      $("scan-error").hidden = false;
      setText("scan-status", "Scan unsuccessful. Your input is still available.");
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
    invalidate("Fictional sample loaded. Ready to scan.");
  }
  $("load-sample").addEventListener("click", loadSample);
  $("clear").addEventListener("click", () => {
    input.value = "";
    invalidate("Workspace cleared. Paste a log or load a sample to begin.");
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

  function selectPattern(key) {
    selectedRule = key;
    const rule = ruleMap[key];
    document.querySelectorAll(".pattern-choice").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.rule === key)));
    setText("pattern-label", rule.label.toUpperCase());
    setText("pattern-code", rule.pattern);
    setText("pattern-description", rule.description);
    renderTokens($("pattern-tokens"), rule);
    loadSample();
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

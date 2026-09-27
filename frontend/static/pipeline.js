/* ==========================================================================
   DevForge Control Center — frontend logic (vanilla JS, no build step)
   ========================================================================== */

let projectId = null;
let pollingTimer = null;
let elapsedTimer = null;
let lastStagesSignature = null;
let lastEventsCount = -1;
let lastSecuritySignature = null;
let insightsOpen = true;
let currentStages = [];
let currentEvents = [];
let runStartMs = null;

const API_BASE = "";

const STAGE_ORDER = ["plan", "build", "test", "debug", "security", "fix", "approval", "release"];

const STAGE_ICONS = {
    plan: "🧭", build: "🔨", test: "🧪", debug: "🐛",
    security: "🛡️", fix: "🔧", approval: "🖐️", release: "🚀",
};

const AGENT_META = {
    plan:     { real: true,  purpose: "Turns a one-line idea into user stories and architecture decisions (ADRs)." },
    build:    { real: false, purpose: "Generates the milestone's code from the approved plan. Stub in this build." },
    test:     { real: true,  purpose: "Actually executes the project's test suite and reports real pass/fail counts." },
    security: { real: true,  purpose: "Scans generated code for vulnerabilities and classifies severity." },
    debug:    { real: true,  purpose: "Identifies the actual failing code, patches it, and reruns the tests." },
    fix:      { real: true,  purpose: "When security blocks, patches the flagged vulnerability and re-scans." },
};

/* ---------- DOM refs ---------- */

const startBtn = document.getElementById("start-btn");
const startBtnLabel = startBtn.querySelector(".btn-label");
const startBtnSpinner = startBtn.querySelector(".btn-spinner");
const heroLaunchBtn = document.getElementById("hero-launch-btn");
const resetBtn = document.getElementById("reset-btn");
const approveBtn = document.getElementById("approve-btn");
const changesBtn = document.getElementById("changes-btn");
const ideaInput = document.getElementById("idea-input");
const copyIdBtn = document.getElementById("copy-id-btn");

const projectInfo = document.getElementById("project-info");
const projectIdElement = document.getElementById("project-id");
const pipelineStatus = document.getElementById("pipeline-status");
const runningDot = document.getElementById("running-dot");
const elapsedTimeEl = document.getElementById("elapsed-time");
const asciiProgressEl = document.getElementById("ascii-progress");

const stagesContainer = document.getElementById("stages-container");
const eventsFallback = document.getElementById("events-container"); // may be absent
const railFill = document.getElementById("rail-fill");
const orchestrationGraph = document.getElementById("orchestration-graph");

const attentionBanner = document.getElementById("attention-banner");
const attentionIcon = document.getElementById("attention-icon");
const attentionTitle = document.getElementById("attention-title");
const attentionMessage = document.getElementById("attention-message");
const downloadBtn = document.getElementById("download-btn");

const approvalPanel = document.getElementById("approval-panel");
const approvalGate = document.getElementById("approval-gate");
const gateResults = document.getElementById("gate-results");

const hcArchValue = document.getElementById("hc-arch-value");
const hcReleaseValue = document.getElementById("hc-release-value");

const loopPanel = document.getElementById("loop-panel");
const securitySpotlight = document.getElementById("security-spotlight");

const agentsGrid = document.getElementById("agents-grid");

const insightsRefresh = document.getElementById("insights-refresh");
const impactText = document.getElementById("impact-text");
const metricsGrid = document.getElementById("metrics-grid");
const testsTable = document.getElementById("tests-table");
const securityTable = document.getElementById("security-table");
const testsChart = document.getElementById("tests-chart");
const securityChart = document.getElementById("security-chart");

const auditTimeline = document.getElementById("audit-timeline");

const judgeModeBtn = document.getElementById("judge-mode-btn");
const judgeView = document.getElementById("judge-view");
const judgeExitBtn = document.getElementById("judge-exit-btn");
const judgePipeline = document.getElementById("judge-pipeline");

const paletteHint = document.getElementById("palette-hint");
const commandPalette = document.getElementById("command-palette");
const paletteInput = document.getElementById("palette-input");
const paletteResults = document.getElementById("palette-results");


/* =========================
   INIT — orchestration graph + agent registry (static shell first)
========================= */

function renderOrchestrationGraph(stages) {
    const byName = {};
    (stages || []).forEach(s => { byName[s.name] = s; });

    orchestrationGraph.innerHTML = STAGE_ORDER.map((name, i) => {
        const s = byName[name];
        const stateClass = s ? `og-${getStateClass(s.state).replace("state-", "")}` : "";
        const node = `
            <div class="og-node ${stateClass}">
                <div class="og-icon">${STAGE_ICONS[name]}</div>
                <div class="og-label">${name}</div>
            </div>`;
        if (i === STAGE_ORDER.length - 1) return node;
        const connectorActive = s && s.state === "done" ? "og-connector-active" : "";
        return node + `<div class="og-connector ${connectorActive}"></div>`;
    }).join("");
}

function renderAgentsGrid() {
    const byName = {};
    currentStages.forEach(s => { byName[s.name] = s; });

    agentsGrid.innerHTML = Object.keys(AGENT_META).map(name => {
        const meta = AGENT_META[name];
        const live = byName[name];
        const execCount = currentEvents.filter(e => e.event === "AGENT_DONE" && e.stage === name).length;
        const badge = meta.real
            ? `<span class="real-label">REAL</span>`
            : `<span class="stub-label">STUB</span>`;
        const latest = live && live.state !== "pending"
            ? `${escapeHtml(live.state)}${live.verdict ? " · " + escapeHtml(live.verdict) : ""}`
            : "Not run yet";
        return `
            <article class="agent-card">
                <div class="agent-card-top">
                    <h3><span class="stage-icon">${STAGE_ICONS[name] || "•"}</span>${capitalize(name)} agent</h3>
                    ${badge}
                </div>
                <p class="agent-purpose">${escapeHtml(meta.purpose)}</p>
                <div class="agent-meta">
                    <span>Latest result: <b>${escapeHtml(latest)}</b></span>
                    <span>Executions this run: <b>${execCount}</b></span>
                </div>
            </article>
        `;
    }).join("");
}

renderOrchestrationGraph([]);
renderAgentsGrid();


/* =========================
   PROJECT CREATION
========================= */

async function startProject() {
    setStarting(true);
    const idea = (ideaInput.value || "").trim() || "task management SaaS";

    try {
        const response = await fetch(`${API_BASE}/projects`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ idea }),
        });
        if (!response.ok) throw new Error(`Create project failed: ${response.status}`);

        const data = await response.json();
        projectId = data.project_id;
        lastStagesSignature = null;
        lastEventsCount = -1;
        lastSecuritySignature = null;
        runStartMs = Date.now();
        startElapsedTimer();

        await startPipeline();
    } catch (error) {
        console.error(error);
        alert(`Unable to start project: ${error.message}`);
        setStarting(false);
    }
}

function setStarting(isStarting) {
    startBtn.disabled = isStarting;
    ideaInput.disabled = isStarting;
    startBtnLabel.classList.toggle("hidden", isStarting);
    startBtnSpinner.classList.toggle("hidden", !isStarting);
}

async function startPipeline() {
    if (!projectId) return;
    try {
        const response = await fetch(`${API_BASE}/projects/${projectId}/start`, { method: "POST" });
        if (!response.ok) throw new Error(`Start pipeline failed: ${response.status}`);
        startPolling();
    } catch (error) {
        console.error(error);
        alert(`Unable to start pipeline: ${error.message}`);
        setStarting(false);
    }
}


/* =========================
   POLLING
========================= */

function startPolling() {
    stopPolling();
    fetchStatus();
    pollingTimer = setInterval(fetchStatus, 2000);
}

function stopPolling() {
    if (pollingTimer !== null) { clearInterval(pollingTimer); pollingTimer = null; }
}

function startElapsedTimer() {
    stopElapsedTimer();
    elapsedTimer = setInterval(updateElapsed, 1000);
    updateElapsed();
}
function stopElapsedTimer() {
    if (elapsedTimer !== null) { clearInterval(elapsedTimer); elapsedTimer = null; }
}
function updateElapsed() {
    if (!runStartMs) { elapsedTimeEl.textContent = "00:00"; return; }
    const secs = Math.max(0, Math.floor((Date.now() - runStartMs) / 1000));
    const m = String(Math.floor(secs / 60)).padStart(2, "0");
    const s = String(secs % 60).padStart(2, "0");
    elapsedTimeEl.textContent = `${m}:${s}`;
}

async function fetchStatus() {
    if (!projectId) return;
    try {
        const response = await fetch(`${API_BASE}/projects/${projectId}/status`);
        if (!response.ok) throw new Error(`Status request failed: ${response.status}`);
        const data = await response.json();
        renderDashboard(data);
    } catch (error) {
        console.error("Status polling error:", error);
    }
}


/* =========================
   DASHBOARD RENDERING
========================= */

function renderDashboard(data) {
    projectId = data.project_id;
    currentStages = data.stages || [];
    currentEvents = data.events || [];

    if (runStartMs === null && currentEvents.length) {
        const firstTs = Date.parse(currentEvents[0].ts);
        if (!Number.isNaN(firstTs)) { runStartMs = firstTs; startElapsedTimer(); }
    }

    projectInfo.textContent = data.idea || "Project";
    projectIdElement.textContent = data.project_id || "—";
    pipelineStatus.textContent = data.status || "UNKNOWN";

    runningDot.classList.remove("dot-running", "dot-done", "dot-failed");
    if (data.running) runningDot.classList.add("dot-running");
    else if (data.status === "RELEASED") runningDot.classList.add("dot-done");
    else if (data.status === "FAILED") runningDot.classList.add("dot-failed");

    renderStages(currentStages, data.retries || {});
    renderOrchestrationGraph(currentStages);
    renderAgentsGrid();
    renderAuditTrail(currentEvents);
    renderAttention(data.status);
    renderApproval(data.awaiting_approval);
    renderHumanControl(currentEvents, data.awaiting_approval);
    renderLoopPanel(currentEvents, data.retries || {});
    fetchSecuritySpotlight();

    if (insightsOpen) fetchInsights();

    if (!data.running) {
        setStarting(false);
        if (data.status === "RELEASED" || data.status === "FAILED") {
            stopPolling();
            stopElapsedTimer();
        }
    }
}


/* =========================
   STAGES
========================= */

function renderStages(stages, retries) {
    if (!stages.length) {
        stagesContainer.innerHTML = '<p class="empty-state">No stages available.</p>';
        railFill.style.width = "0%";
        asciiProgressEl.textContent = "[░░░░░░░░░░░░]";
        return;
    }

    const doneCount = stages.filter(s => s.state === "done").length;
    const pct = doneCount / stages.length;
    railFill.style.width = `${Math.round(pct * 100)}%`;

    const filled = Math.round(pct * 12);
    asciiProgressEl.textContent = `[${"█".repeat(filled)}${"░".repeat(12 - filled)}]`;

    const signature = JSON.stringify(stages) + JSON.stringify(retries);
    if (signature === lastStagesSignature) return;
    lastStagesSignature = signature;

    stagesContainer.innerHTML = stages.map(stage => {
        const retryCount = retries[stage.name] ?? 0;
        const stateClass = getStateClass(stage.state);
        const icon = STAGE_ICONS[stage.name] || "•";

        const verdict = stage.verdict
            ? `<span class="verdict ${getVerdictClass(stage.verdict)}">${escapeHtml(stage.verdict)}</span>`
            : `<span class="verdict neutral">—</span>`;

        const realLabel = stage.real === false ? `<span class="stub-label">stub</span>` : `<span class="real-label">real</span>`;
        const retryLabel = `<span class="retry-badge">retries: ${retryCount}</span>`;
        const duration = Number(stage.duration_seconds || 0).toFixed(1);

        let gateBox = "";
        if (stage.verdict) {
            const passed = stage.verdict === "PASS";
            gateBox = `
                <div class="gate-box ${passed ? "gate-pass" : "gate-fail"}">
                    GATE &nbsp; ${passed ? "✓ PASSED" : "✕ " + escapeHtml(stage.verdict)}
                    ${!passed ? `<div><button class="why-toggle" onclick="scrollToEvidence('${stage.name}')">Why? ↓</button></div>` : ""}
                </div>`;
        }

        return `
            <article class="stage-card ${stateClass}">
                <div class="stage-top">
                    <div>
                        <h3><span class="stage-icon">${icon}</span>${escapeHtml(stage.name)}</h3>
                        <div class="stage-labels">${realLabel}${retryLabel}</div>
                    </div>
                    <span class="state-badge ${stateClass}">${escapeHtml(stage.state)}</span>
                </div>
                <div class="stage-verdict">${verdict}</div>
                <p class="stage-summary">${escapeHtml(stage.summary || "Waiting…")}</p>
                <div class="stage-duration">⏱ ${duration}s</div>
                ${gateBox}
            </article>
        `;
    }).join("");
}

function scrollToEvidence(stageName) {
    const target = (stageName === "security") ? securitySpotlight : loopPanel;
    if (target && !target.classList.contains("hidden")) {
        target.scrollIntoView({ behavior: "smooth", block: "center" });
    } else {
        document.getElementById("audit-section").scrollIntoView({ behavior: "smooth" });
    }
}
window.scrollToEvidence = scrollToEvidence;


/* =========================
   HUMAN CONTROL
========================= */

function renderHumanControl(events, awaitingApproval) {
    setHcChip(hcArchValue, deriveGateStatus(events, awaitingApproval, "architecture"));
    setHcChip(hcReleaseValue, deriveGateStatus(events, awaitingApproval, "release"));
}

function deriveGateStatus(events, awaitingApproval, gateName) {
    for (let i = events.length - 1; i >= 0; i--) {
        const e = events[i];
        if (e.event === "HUMAN_APPROVAL" && e.gate === gateName) {
            return e.approved ? "approved" : "rejected";
        }
    }
    if (awaitingApproval && awaitingApproval.gate === gateName) return "waiting";
    return "pending";
}

function setHcChip(el, status) {
    el.classList.remove("hc-approved", "hc-waiting", "hc-rejected");
    if (status === "approved") { el.textContent = "✓ Approved"; el.classList.add("hc-approved"); }
    else if (status === "waiting") { el.textContent = "⏳ Awaiting approval"; el.classList.add("hc-waiting"); }
    else if (status === "rejected") { el.textContent = "✕ Rejected"; el.classList.add("hc-rejected"); }
    else { el.textContent = "Not reached"; }
}


/* =========================
   DEBUG / FIX LOOP PANEL
========================= */

function renderLoopPanel(events, retries) {
    const debugEvents = events.filter(e => e.event === "AGENT_DONE" && e.stage === "debug");
    const fixEvents = events.filter(e => e.event === "AGENT_DONE" && e.stage === "fix");
    const testFails = events.filter(e => e.event === "GATE" && e.gate === "tests" && e.verdict !== "PASS");
    const secFails = events.filter(e => e.event === "GATE" && e.gate === "security" && e.verdict === "BLOCKED");

    if (!debugEvents.length && !fixEvents.length) {
        loopPanel.classList.add("hidden");
        loopPanel.innerHTML = "";
        return;
    }

    loopPanel.classList.remove("hidden");
    let html = `<h3>🔁 Automated feedback loop</h3>`;

    if (debugEvents.length) {
        const lastDebug = debugEvents[debugEvents.length - 1];
        const lastFail = testFails.length ? testFails[testFails.length - 1] : null;
        html += `
            <div class="loop-flow">
                <span class="lf-fail">TEST ✕ FAILED</span> → DEBUG AGENT → PATCH → TEST AGAIN → <span class="lf-pass">✓ PASSED</span>
            </div>
            <p class="loop-detail">
                Retry <b>${retries.test ?? 0}</b>.
                ${lastFail ? `Failure: <b>${escapeHtml(lastFail.reason || lastFail.msg || "")}</b>. ` : ""}
                Debug agent: <b>${escapeHtml(lastDebug.summary || lastDebug.msg || "patch applied")}</b>.
            </p>`;
    }

    if (fixEvents.length) {
        const lastFix = fixEvents[fixEvents.length - 1];
        const lastSecFail = secFails.length ? secFails[secFails.length - 1] : null;
        html += `
            <div class="loop-flow">
                <span class="lf-fail">SECURITY ✕ BLOCKED</span> → FIX AGENT → PATCH → RE-SCAN → <span class="lf-pass">✓ PASSED</span>
            </div>
            <p class="loop-detail">
                Retry <b>${retries.security ?? 0}</b>.
                ${lastSecFail ? `Blocked: <b>${escapeHtml(lastSecFail.reason || lastSecFail.msg || "")}</b>. ` : ""}
                Fix agent: <b>${escapeHtml(lastFix.summary || lastFix.msg || "patch applied")}</b>.
            </p>`;
    }

    loopPanel.innerHTML = html;
}


/* =========================
   SECURITY SPOTLIGHT
========================= */

async function fetchSecuritySpotlight() {
    if (!projectId) return;
    try {
        const res = await fetch(`${API_BASE}/projects/${projectId}/security`);
        if (!res.ok) return;
        const runs = await res.json();
        renderSecuritySpotlight(runs);
    } catch (error) {
        console.error("Security spotlight fetch error:", error);
    }
}

function renderSecuritySpotlight(runs) {
    if (!runs || !runs.length) {
        securitySpotlight.classList.add("hidden");
        return;
    }

    const signature = JSON.stringify(runs);
    if (signature === lastSecuritySignature) return;
    lastSecuritySignature = signature;

    const last = runs[runs.length - 1];
    const blocked = runs.find(r => r.verdict === "BLOCKED");

    if (!blocked) {
        securitySpotlight.classList.add("hidden");
        return;
    }

    securitySpotlight.classList.remove("hidden");
    const findings = blocked.findings || [];
    const first = findings[0] || {};
    const sevClass = `sev-${(first.severity || "medium").toLowerCase()}`;

    let html = `<h3>🛡 Security finding</h3>`;
    html += `
        <div class="finding-row">
            <div class="finding-field"><div class="ff-label">Severity</div><div class="ff-value ${sevClass}">${escapeHtml((first.severity || "?").toUpperCase())}</div></div>
            <div class="finding-field"><div class="ff-label">Type</div><div class="ff-value">${escapeHtml(first.type || "Unknown")}</div></div>
            <div class="finding-field"><div class="ff-label">Location</div><div class="ff-value">${escapeHtml(first.location || "—")}</div></div>
            <div class="finding-field"><div class="ff-label">Detected by</div><div class="ff-value">Security agent</div></div>
        </div>
        <div class="finding-status">${findings.length > 1 ? findings.length + " findings — " : ""}BLOCKING RELEASE (attempt ${escapeHtml(String(blocked.attempt ?? "?"))})</div>
    `;

    if (last.verdict === "PASS" && last !== blocked) {
        html += `<div class="fix-flow">FIX AGENT → patch applied → RE-SCAN → <span class="fx-pass">✓ SECURITY GATE PASSED</span> (attempt ${escapeHtml(String(last.attempt ?? "?"))})</div>`;
    }

    securitySpotlight.innerHTML = html;
}


/* =========================
   ATTENTION / SUCCESS BANNER
========================= */

function renderAttention(status) {
    if (status === "FAILED") {
        attentionBanner.classList.remove("hidden", "success");
        attentionIcon.textContent = "⚠";
        attentionTitle.textContent = "Needs human attention";
        attentionMessage.textContent = "The pipeline failed and requires human intervention.";
        downloadBtn.classList.add("hidden");
    } else if (status === "RELEASED") {
        attentionBanner.classList.remove("hidden");
        attentionBanner.classList.add("success");
        attentionIcon.textContent = "🚀";
        attentionTitle.textContent = "Released";
        attentionMessage.textContent = "All gates passed and a human approved the release.";
        if (projectId) {
            downloadBtn.href = `/projects/${projectId}/download`;
            downloadBtn.classList.remove("hidden");
        }
    } else {
        attentionBanner.classList.add("hidden");
        downloadBtn.classList.add("hidden");
    }
}


/* =========================
   APPROVAL
========================= */

function renderApproval(awaitingApproval) {
    if (!awaitingApproval) { approvalPanel.classList.add("hidden"); return; }

    approvalPanel.classList.remove("hidden");
    approvalGate.textContent = `Gate awaiting approval: ${awaitingApproval.gate}`;

    const results = awaitingApproval.gate_results || [];
    if (!results.length) {
        gateResults.innerHTML = '<p class="empty-state small">No gate results available.</p>';
        return;
    }

    gateResults.innerHTML = results.map(result => `
        <div class="gate-result">
            <div class="gate-result-top">
                <strong>${escapeHtml(result.gate)}</strong>
                <span class="verdict ${getVerdictClass(result.verdict)}">${escapeHtml(result.verdict)}</span>
            </div>
            <p>${escapeHtml(result.reason || "")}</p>
        </div>
    `).join("");
}

async function sendApproval(approved) {
    if (!projectId) return;
    const gate = approvalGate.textContent.replace("Gate awaiting approval: ", "").trim();
    if (!gate) return;

    approveBtn.disabled = true;
    changesBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/projects/${projectId}/approve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ gate, approved }),
        });
        if (!response.ok) throw new Error(`Approval failed: ${response.status}`);
        await fetchStatus();
    } catch (error) {
        console.error(error);
        alert(`Approval failed: ${error.message}`);
    } finally {
        approveBtn.disabled = false;
        changesBtn.disabled = false;
    }
}


/* =========================
   RESET
========================= */

async function resetProject() {
    if (!projectId) { alert("No project to reset."); return; }
    resetBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/projects/${projectId}/reset`, { method: "POST" });
        if (!response.ok) throw new Error(`Reset failed: ${response.status}`);

        stopPolling();
        stopElapsedTimer();
        projectId = null;
        lastStagesSignature = null;
        lastEventsCount = -1;
        lastSecuritySignature = null;
        currentStages = [];
        currentEvents = [];
        runStartMs = null;

        projectInfo.textContent = "No project started";
        projectIdElement.textContent = "—";
        pipelineStatus.textContent = "IDLE";
        elapsedTimeEl.textContent = "00:00";
        asciiProgressEl.textContent = "[░░░░░░░░░░░░]";
        runningDot.classList.remove("dot-running", "dot-done", "dot-failed");

        stagesContainer.innerHTML = '<p class="empty-state">Start a project above to watch the pipeline run.</p>';
        auditTimeline.innerHTML = '<p class="empty-state">No events yet.</p>';
        railFill.style.width = "0%";

        approvalPanel.classList.add("hidden");
        attentionBanner.classList.add("hidden");
        loopPanel.classList.add("hidden");
        securitySpotlight.classList.add("hidden");

        renderOrchestrationGraph([]);
        renderAgentsGrid();
        renderHumanControl([], null);

        impactText.textContent = "Start a project to see insights.";
        metricsGrid.innerHTML = "";
        testsTable.innerHTML = '<p class="empty-state small">No test runs yet.</p>';
        securityTable.innerHTML = '<p class="empty-state small">No security runs yet.</p>';
        testsChart.innerHTML = "";
        securityChart.innerHTML = "";

        setStarting(false);
    } catch (error) {
        console.error(error);
        alert(`Reset failed: ${error.message}`);
    } finally {
        resetBtn.disabled = false;
    }
}


/* =========================
   AUDIT TRAIL
========================= */

function renderAuditTrail(events) {
    if (!events.length) {
        auditTimeline.innerHTML = '<p class="empty-state">No events yet.</p>';
        lastEventsCount = 0;
        return;
    }
    if (events.length === lastEventsCount) return;
    lastEventsCount = events.length;

    auditTimeline.innerHTML = [...events].reverse().map(event => {
        const timestamp = event.ts ? formatTimestamp(event.ts) : "";
        const actor = actorFor(event);
        const dotClass = dotClassFor(event);
        const msg = event.msg || event.reason || event.summary || "";
        return `
            <div class="audit-item">
                <span class="audit-dot ${dotClass}"></span>
                <div class="audit-time">${escapeHtml(timestamp)}</div>
                <div class="audit-actor">${escapeHtml(actor)}</div>
                <div class="audit-msg">${escapeHtml(msg)}${event.verdict ? " — " + escapeHtml(event.verdict) : ""}</div>
            </div>
        `;
    }).join("");
}

function actorFor(event) {
    if (event.event === "HUMAN_APPROVAL") return "HUMAN";
    if (event.stage) return `${event.stage.toUpperCase()} AGENT`;
    if (event.gate) return `${event.gate.toUpperCase()} GATE`;
    return event.event || "DEVFORGE";
}

function dotClassFor(event) {
    if (event.event === "HUMAN_APPROVAL") return "ad-human";
    if (event.verdict === "PASS" || event.status === "PASS") return "ad-pass";
    if (event.verdict === "FAIL" || event.verdict === "BLOCKED" || event.status === "FAIL") return "ad-fail";
    return "";
}


/* =========================
   INSIGHTS
========================= */

async function fetchInsights() {
    if (!projectId) return;
    try {
        const [metricsRes, testsRes, securityRes] = await Promise.all([
            fetch(`${API_BASE}/projects/${projectId}/metrics`),
            fetch(`${API_BASE}/projects/${projectId}/tests`),
            fetch(`${API_BASE}/projects/${projectId}/security`),
        ]);
        if (metricsRes.ok) renderMetrics(await metricsRes.json());
        if (testsRes.ok) { const t = await testsRes.json(); renderTests(t); renderTestsChart(t); }
        if (securityRes.ok) { const s = await securityRes.json(); renderSecurity(s); renderSecurityChart(s); }
    } catch (error) {
        console.error("Insights fetch error:", error);
    }
}

function renderMetrics(data) {
    const summary = data.summary || {};
    impactText.textContent = data.impact_text || "No activity measured for this project yet.";
    const tiles = [
        { value: summary.retry_count ?? 0, label: "Retries" },
        { value: summary.security_findings_count ?? 0, label: "Security findings" },
        { value: summary.human_interventions ?? 0, label: "Human approvals" },
        { value: `${Number(summary.debugging_time_seconds ?? 0).toFixed(1)}s`, label: "Debug time" },
    ];
    metricsGrid.innerHTML = tiles.map(tile => `
        <div class="metric-tile">
            <div class="metric-value">${escapeHtml(String(tile.value))}</div>
            <div class="metric-label">${escapeHtml(tile.label)}</div>
        </div>
    `).join("");
}

function renderTests(runs) {
    if (!runs || !runs.length) { testsTable.innerHTML = '<p class="empty-state small">No test runs yet.</p>'; return; }
    testsTable.innerHTML = runs.map(run => {
        const passed = run.passed ?? 0, total = run.total ?? 0;
        const ok = passed === total && total > 0;
        return `
            <div class="mini-row">
                <span class="mini-main">Attempt ${escapeHtml(String(run.attempt ?? "?"))}</span>
                <span class="${ok ? "verdict pass" : "verdict fail"}">${passed}/${total} passed</span>
            </div>`;
    }).join("");
}

function renderTestsChart(runs) {
    if (!runs || !runs.length) { testsChart.innerHTML = ""; return; }
    const last = runs[runs.length - 1];
    const passed = last.passed ?? 0, total = last.total ?? 0, failed = Math.max(0, total - passed);
    const passPct = total ? Math.round((passed / total) * 100) : 0;
    const failPct = total ? 100 - passPct : 0;
    testsChart.innerHTML = `
        <div class="chart-bar-row"><span class="chart-bar-label">Passed</span><div class="chart-bar-track"><div class="chart-bar-fill cb-pass" style="width:${passPct}%"></div></div><span class="chart-bar-count">${passed}</span></div>
        <div class="chart-bar-row"><span class="chart-bar-label">Failed</span><div class="chart-bar-track"><div class="chart-bar-fill cb-fail" style="width:${failPct}%"></div></div><span class="chart-bar-count">${failed}</span></div>
    `;
}

function renderSecurity(runs) {
    if (!runs || !runs.length) { securityTable.innerHTML = '<p class="empty-state small">No security runs yet.</p>'; return; }
    securityTable.innerHTML = runs.map(run => {
        const findings = run.findings || [];
        const verdictClass = run.verdict === "PASS" ? "pass" : "fail";
        const findingsText = findings.length ? findings.map(f => `${f.severity || "?"} ${f.type || ""}`).join(", ") : "No blocking findings";
        return `
            <div class="mini-row">
                <span class="mini-main">Attempt ${escapeHtml(String(run.attempt ?? "?"))} <span class="verdict ${verdictClass}">${escapeHtml(run.verdict || "?")}</span></span>
                <span class="mini-sub">${escapeHtml(findingsText)}</span>
            </div>`;
    }).join("");
}

function renderSecurityChart(runs) {
    const counts = { critical: 0, high: 0, medium: 0, low: 0 };
    (runs || []).forEach(run => (run.findings || []).forEach(f => {
        const sev = (f.severity || "").toLowerCase();
        if (sev in counts) counts[sev] += 1;
    }));
    const max = Math.max(1, ...Object.values(counts));
    securityChart.innerHTML = Object.keys(counts).map(sev => {
        const pct = Math.round((counts[sev] / max) * 100);
        return `<div class="chart-bar-row"><span class="chart-bar-label">${capitalize(sev)}</span><div class="chart-bar-track"><div class="chart-bar-fill cb-${sev}" style="width:${pct}%"></div></div><span class="chart-bar-count">${counts[sev]}</span></div>`;
    }).join("");
}


/* =========================
   JUDGE MODE
========================= */

function openJudgeMode() {
    judgeView.classList.remove("hidden");
    judgePipeline.innerHTML = STAGE_ORDER.map(name => {
        const s = currentStages.find(st => st.name === name);
        const cls = s ? (s.state === "done" ? "jc-done" : s.state === "running" ? "jc-running" : "") : "";
        return `<span class="judge-chip ${cls}">${STAGE_ICONS[name]} ${capitalize(name)}</span>`;
    }).join("");
}
function closeJudgeMode() { judgeView.classList.add("hidden"); }
function toggleJudgeMode() { judgeView.classList.contains("hidden") ? openJudgeMode() : closeJudgeMode(); }


/* =========================
   COMMAND PALETTE
========================= */

function paletteActions() {
    const actions = [
        { label: "▶ Start pipeline", run: () => { closePalette(); startProject(); } },
        { label: "↺ Reset project", run: () => { closePalette(); resetProject(); } },
        { label: "🎓 Toggle Judge Mode", run: () => { closePalette(); toggleJudgeMode(); } },
        { label: "🧭 Scroll to Pipeline", run: () => { closePalette(); scrollTo("pipeline-section"); } },
        { label: "🧩 Scroll to Agents", run: () => { closePalette(); scrollTo("agents-section"); } },
        { label: "📊 Scroll to Insights", run: () => { closePalette(); scrollTo("insights-section"); } },
        { label: "📜 Scroll to Audit Trail", run: () => { closePalette(); scrollTo("audit-section"); } },
    ];
    if (!approvalPanel.classList.contains("hidden")) {
        actions.unshift({ label: "✓ Approve pending gate", run: () => { closePalette(); sendApproval(true); } });
        actions.unshift({ label: "✕ Reject pending gate", run: () => { closePalette(); sendApproval(false); } });
    }
    return actions;
}

function scrollTo(id) { document.getElementById(id)?.scrollIntoView({ behavior: "smooth" }); }

let paletteFiltered = [];
let paletteIndex = 0;

function openPalette() {
    commandPalette.classList.remove("hidden");
    paletteInput.value = "";
    renderPaletteResults("");
    setTimeout(() => paletteInput.focus(), 10);
}
function closePalette() { commandPalette.classList.add("hidden"); }

function renderPaletteResults(query) {
    const all = paletteActions();
    paletteFiltered = all.filter(a => a.label.toLowerCase().includes(query.toLowerCase()));
    paletteIndex = 0;
    paletteResults.innerHTML = paletteFiltered.map((a, i) =>
        `<div class="palette-item ${i === 0 ? "palette-active" : ""}" data-index="${i}">${a.label}</div>`
    ).join("") || '<div class="palette-item">No matching command</div>';
}

paletteInput?.addEventListener("input", () => renderPaletteResults(paletteInput.value));

paletteResults?.addEventListener("click", (e) => {
    const item = e.target.closest(".palette-item");
    if (!item) return;
    const idx = Number(item.dataset.index);
    if (paletteFiltered[idx]) paletteFiltered[idx].run();
});

document.addEventListener("keydown", (e) => {
    const isMeta = e.metaKey || e.ctrlKey;
    if (isMeta && e.key.toLowerCase() === "k") { e.preventDefault(); openPalette(); return; }
    if (isMeta && e.key.toLowerCase() === "j") { e.preventDefault(); toggleJudgeMode(); return; }

    if (!commandPalette.classList.contains("hidden")) {
        if (e.key === "Escape") { closePalette(); return; }
        if (e.key === "ArrowDown") { e.preventDefault(); movePalette(1); return; }
        if (e.key === "ArrowUp") { e.preventDefault(); movePalette(-1); return; }
        if (e.key === "Enter") { e.preventDefault(); if (paletteFiltered[paletteIndex]) paletteFiltered[paletteIndex].run(); return; }
    }

    if (!judgeView.classList.contains("hidden") && e.key === "Escape") closeJudgeMode();
});

function movePalette(delta) {
    if (!paletteFiltered.length) return;
    paletteIndex = (paletteIndex + delta + paletteFiltered.length) % paletteFiltered.length;
    [...paletteResults.children].forEach((el, i) => el.classList.toggle("palette-active", i === paletteIndex));
}


/* =========================
   HELPERS
========================= */

function getStateClass(state) {
    switch (state) {
        case "done": return "state-done";
        case "running": return "state-running";
        case "failed": return "state-failed";
        case "pending": default: return "state-pending";
    }
}
function getVerdictClass(verdict) {
    if (verdict === "PASS") return "pass";
    if (verdict === "FAIL" || verdict === "BLOCKED") return "fail";
    return "neutral";
}
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return timestamp;
    return date.toLocaleTimeString();
}
function capitalize(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }
function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}


/* =========================
   WIRE UP
========================= */

startBtn.addEventListener("click", startProject);
heroLaunchBtn?.addEventListener("click", () => { ideaInput.focus(); ideaInput.scrollIntoView({ behavior: "smooth", block: "center" }); });
resetBtn.addEventListener("click", resetProject);
approveBtn.addEventListener("click", () => sendApproval(true));
changesBtn.addEventListener("click", () => sendApproval(false));
insightsRefresh?.addEventListener("click", fetchInsights);
judgeModeBtn?.addEventListener("click", toggleJudgeMode);
judgeExitBtn?.addEventListener("click", closeJudgeMode);
paletteHint?.addEventListener("click", openPalette);
commandPalette?.addEventListener("click", (e) => { if (e.target === commandPalette) closePalette(); });

ideaInput.addEventListener("keydown", (e) => { if (e.key === "Enter" && !startBtn.disabled) startProject(); });

copyIdBtn.addEventListener("click", () => {
    if (!projectId) return;
    navigator.clipboard?.writeText(projectId).then(() => {
        copyIdBtn.textContent = "✓";
        setTimeout(() => { copyIdBtn.textContent = "⧉"; }, 1200);
    });
});

/* initial empty insights labels */
impactText.textContent = "Start a project to see insights.";

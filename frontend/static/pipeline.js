let projectId = null;
let pollingTimer = null;

const startBtn = document.getElementById("start-btn");
const resetBtn = document.getElementById("reset-btn");
const approveBtn = document.getElementById("approve-btn");
const changesBtn = document.getElementById("changes-btn");

const projectInfo = document.getElementById("project-info");
const projectIdElement = document.getElementById("project-id");
const pipelineStatus = document.getElementById("pipeline-status");
const runningStatus = document.getElementById("running-status");

const stagesContainer = document.getElementById("stages-container");
const eventsContainer = document.getElementById("events-container");

const attentionBanner = document.getElementById("attention-banner");
const attentionMessage = document.getElementById("attention-message");

const approvalPanel = document.getElementById("approval-panel");
const approvalGate = document.getElementById("approval-gate");
const gateResults = document.getElementById("gate-results");

const API_BASE = "";


/* =========================
   PROJECT CREATION
========================= */

async function startProject() {
    startBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/projects`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                idea: "task management SaaS"
            })
        });

        if (!response.ok) {
            throw new Error(`Create project failed: ${response.status}`);
        }

        const data = await response.json();

        projectId = data.project_id;

        await startPipeline();

    } catch (error) {
        console.error(error);
        alert(`Unable to start project: ${error.message}`);
        startBtn.disabled = false;
    }
}


/* =========================
   START PIPELINE
========================= */

async function startPipeline() {
    if (!projectId) {
        return;
    }

    try {
        const response = await fetch(
            `${API_BASE}/projects/${projectId}/start`,
            {
                method: "POST"
            }
        );

        if (!response.ok) {
            throw new Error(`Start pipeline failed: ${response.status}`);
        }

        startPolling();

    } catch (error) {
        console.error(error);
        alert(`Unable to start pipeline: ${error.message}`);
        startBtn.disabled = false;
    }
}


/* =========================
   POLLING
========================= */

function startPolling() {
    stopPolling();

    fetchStatus();

    pollingTimer = setInterval(() => {
        fetchStatus();
    }, 2000);
}


function stopPolling() {
    if (pollingTimer !== null) {
        clearInterval(pollingTimer);
        pollingTimer = null;
    }
}


async function fetchStatus() {
    if (!projectId) {
        return;
    }

    try {
        const response = await fetch(
            `${API_BASE}/projects/${projectId}/status`
        );

        if (!response.ok) {
            throw new Error(`Status request failed: ${response.status}`);
        }

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

    projectInfo.textContent = data.idea || "Project";
    projectIdElement.textContent = data.project_id || "—";
    pipelineStatus.textContent = data.status || "UNKNOWN";
    runningStatus.textContent = data.running ? "Yes" : "No";

    renderStages(data.stages || [], data.retries || {});
    renderEvents(data.events || []);
    renderAttention(data.status);
    renderApproval(data.awaiting_approval);

    if (!data.running) {
        if (
            data.status === "RELEASED" ||
            data.status === "FAILED"
        ) {
            stopPolling();
        }
    }
}


/* =========================
   STAGES
========================= */

function renderStages(stages, retries) {
    if (!stages.length) {
        stagesContainer.innerHTML =
            '<p class="empty-state">No stages available.</p>';
        return;
    }

    stagesContainer.innerHTML = stages.map(stage => {

        const retryCount = retries[stage.name] ?? 0;

        const stateClass = getStateClass(stage.state);

        const verdict = stage.verdict
            ? `<span class="verdict ${getVerdictClass(stage.verdict)}">
                    ${escapeHtml(stage.verdict)}
               </span>`
            : `<span class="verdict neutral">—</span>`;

        const realLabel = stage.real === false
            ? `<span class="stub-label">stub</span>`
            : "";

        const retryLabel = retryCount > 0
            ? `<span class="retry-badge">
                    retries: ${retryCount}
               </span>`
            : `<span class="retry-badge">
                    retries: 0
               </span>`;

        const duration = Number(stage.duration_seconds || 0).toFixed(1);

        return `
            <article class="stage-card ${stateClass}">

                <div class="stage-top">
                    <div>
                        <h3>${escapeHtml(stage.name)}</h3>

                        <div class="stage-labels">
                            ${realLabel}
                            ${retryLabel}
                        </div>
                    </div>

                    <span class="state-badge ${stateClass}">
                        ${escapeHtml(stage.state)}
                    </span>
                </div>

                <div class="stage-verdict">
                    ${verdict}
                </div>

                <p class="stage-summary">
                    ${escapeHtml(stage.summary || "No summary available.")}
                </p>

                <div class="stage-duration">
                    Duration: ${duration}s
                </div>

            </article>
        `;
    }).join("");
}


/* =========================
   EVENTS
========================= */

function renderEvents(events) {
    if (!events.length) {
        eventsContainer.innerHTML =
            '<p class="empty-state">No events yet.</p>';
        return;
    }

    eventsContainer.innerHTML = [...events]
        .reverse()
        .map(event => {

            const timestamp = event.ts
                ? formatTimestamp(event.ts)
                : "";

            return `
                <div class="event-item">

                    <div class="event-time">
                        ${escapeHtml(timestamp)}
                    </div>

                    <div class="event-content">
                        <strong>
                            ${escapeHtml(event.event || "EVENT")}
                        </strong>

                        <span>
                            ${escapeHtml(event.stage || "")}
                        </span>

                        <p>
                            ${escapeHtml(event.msg || "")}
                        </p>
                    </div>

                </div>
            `;
        })
        .join("");
}


/* =========================
   ATTENTION BANNER
========================= */

function renderAttention(status) {
    if (status === "FAILED") {
        attentionBanner.classList.remove("hidden");

        attentionMessage.textContent =
            "The pipeline failed and requires human intervention.";

    } else {
        attentionBanner.classList.add("hidden");
    }
}


/* =========================
   APPROVAL
========================= */

function renderApproval(awaitingApproval) {
    if (!awaitingApproval) {
        approvalPanel.classList.add("hidden");
        return;
    }

    approvalPanel.classList.remove("hidden");

    approvalGate.textContent =
        `Gate awaiting approval: ${awaitingApproval.gate}`;

    const results = awaitingApproval.gate_results || [];

    if (!results.length) {
        gateResults.innerHTML =
            '<p class="empty-state">No gate results available.</p>';
        return;
    }

    gateResults.innerHTML = results.map(result => `
        <div class="gate-result">

            <strong>
                ${escapeHtml(result.gate)}
            </strong>

            <span class="${getVerdictClass(result.verdict)}">
                ${escapeHtml(result.verdict)}
            </span>

            <p>
                ${escapeHtml(result.reason || "")}
            </p>

        </div>
    `).join("");
}


/* =========================
   APPROVAL ACTION
========================= */

async function sendApproval(approved) {
    if (!projectId) {
        return;
    }

    const gate = approvalGate.textContent
        .replace("Gate awaiting approval: ", "")
        .trim();

    if (!gate) {
        return;
    }

    approveBtn.disabled = true;
    changesBtn.disabled = true;

    try {
        const response = await fetch(
            `${API_BASE}/projects/${projectId}/approve`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    gate: gate,
                    approved: approved
                })
            }
        );

        if (!response.ok) {
            throw new Error(`Approval failed: ${response.status}`);
        }

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
    if (!projectId) {
        alert("No project to reset.");
        return;
    }

    resetBtn.disabled = true;

    try {
        const response = await fetch(
            `${API_BASE}/projects/${projectId}/reset`,
            {
                method: "POST"
            }
        );

        if (!response.ok) {
            throw new Error(`Reset failed: ${response.status}`);
        }

        stopPolling();

        projectId = null;

        projectInfo.textContent = "No project started";
        projectIdElement.textContent = "—";
        pipelineStatus.textContent = "IDLE";
        runningStatus.textContent = "No";

        stagesContainer.innerHTML =
            '<p class="empty-state">Start a project to see the pipeline.</p>';

        eventsContainer.innerHTML =
            '<p class="empty-state">No events yet.</p>';

        approvalPanel.classList.add("hidden");
        attentionBanner.classList.add("hidden");

        startBtn.disabled = false;

    } catch (error) {
        console.error(error);
        alert(`Reset failed: ${error.message}`);

    } finally {
        resetBtn.disabled = false;
    }
}


/* =========================
   HELPERS
========================= */

function getStateClass(state) {
    switch (state) {
        case "done":
            return "state-done";

        case "running":
            return "state-running";

        case "failed":
            return "state-failed";

        case "pending":
        default:
            return "state-pending";
    }
}


function getVerdictClass(verdict) {
    if (verdict === "PASS") {
        return "pass";
    }

    if (verdict === "FAIL") {
        return "fail";
    }

    return "neutral";
}


function formatTimestamp(timestamp) {
    const date = new Date(timestamp);

    if (Number.isNaN(date.getTime())) {
        return timestamp;
    }

    return date.toLocaleTimeString();
}


function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


/* =========================
   EVENTS
========================= */

startBtn.addEventListener("click", startProject);

resetBtn.addEventListener("click", resetProject);

approveBtn.addEventListener("click", () => {
    sendApproval(true);
});

changesBtn.addEventListener("click", () => {
    sendApproval(false);
});
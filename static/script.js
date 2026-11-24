// Client-side Application State
let currentWaterLevel = 0;
let previousWaterLevel = 0;
let tankCapacity = 200;
let currentPercentage = 0;
let isFull = false;
let depthLimit = 5;
let modalShown = false;
let pollingInterval = null;
let operatingMode = "SIMULATION";
let lastLoggedHash = "";
let currentSearchRequestId = 0;
let globalSearchNodes = [];

// Tank Simulation Playback State Machine
let isSimulationRunning = false;
let isSimulationPaused = false;
let simulationTimeoutTimer = null;
let latestDlsData = null;

// Initialize when the DOM is fully loaded
document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

function initApp() {
    // Setup event handlers
    setupEventListeners();
    
    // Initialize playback states
    updatePlaybackStateLabel("READY");
    updateSimulationControls();
    
    // Perform initial fetch to load current backend status
    fetchStatus();
    
    // Start polling loop
    startPolling();
}

function setupEventListeners() {
    // Mode selectors
    document.getElementById("btn-mode-sim").addEventListener("click", () => {
        switchOperatingMode("SIMULATION");
    });
    document.getElementById("btn-mode-sensor").addEventListener("click", () => {
        switchOperatingMode("SENSOR");
    });

    // IoT Telemetry Simulator
    const iotSlider = document.getElementById("iot-distance-slider");
    const iotVal = document.getElementById("iot-distance-val");
    iotSlider.addEventListener("input", (e) => {
        iotVal.textContent = `${parseFloat(e.target.value).toFixed(1)} cm`;
    });
    
    document.getElementById("btn-send-iot").addEventListener("click", () => {
        const distance = parseFloat(iotSlider.value);
        sendIoTTelemetry(distance);
    });

    // Capacity nodes (futuristic cards)
    const capacityNodes = document.querySelectorAll(".cap-node");
    capacityNodes.forEach(node => {
        node.addEventListener("click", () => {
            if (operatingMode === "SENSOR") return; // Disabled in sensor mode
            capacityNodes.forEach(n => n.classList.remove("active"));
            node.classList.add("active");
            
            const selectedCapacity = parseInt(node.getAttribute("data-capacity"), 10);
            changeCapacity(selectedCapacity);
        });
    });

    // Depth Limit Slider
    const slider = document.getElementById("depth-limit-slider");
    const sliderVal = document.getElementById("depth-limit-val");
    slider.addEventListener("input", (e) => {
        depthLimit = parseInt(e.target.value, 10);
        sliderVal.textContent = depthLimit;
        
        // Re-run search immediately with the new depth limit
        if (isSimulationRunning || isSimulationPaused) {
            stopSimulation();
        }
        triggerSearch();
    });

    // Simulation Playback Controls
    document.getElementById("btn-algo-start").addEventListener("click", () => {
        startSimulation();
    });
    document.getElementById("btn-algo-pause").addEventListener("click", () => {
        pauseSimulation();
    });
    document.getElementById("btn-algo-resume").addEventListener("click", () => {
        resumeSimulation();
    });
    document.getElementById("btn-algo-stop").addEventListener("click", () => {
        stopSimulation();
    });
    document.getElementById("btn-algo-reset").addEventListener("click", () => {
        resetSimulation();
    });

    // Action buttons
    document.getElementById("btn-fill").addEventListener("click", () => {
        triggerManualFill(100);
    });
    
    document.getElementById("btn-reset").addEventListener("click", () => {
        resetTank();
    });

    // Close Modal Button (Reset tank on close)
    document.getElementById("btn-close-modal").addEventListener("click", () => {
        resetTank();
        closeFullModal();
    });
    
    // Close modal if user clicks outside of the modal content
    const modalOverlay = document.getElementById("full-modal");
    modalOverlay.addEventListener("click", (e) => {
        if (e.target === modalOverlay) {
            resetTank();
            closeFullModal();
        }
    });
}

function startPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
    // Poll status only in SENSOR mode to keep telemetry synchronized
    pollingInterval = setInterval(() => {
        if (operatingMode === "SENSOR") {
            fetchStatus();
        }
    }, 2000);
}

// REST Response Helper (Step 8)
async function handleResponse(response, endpoint) {
    if (!response.ok) {
        let errorCode = "HTTP_ERROR";
        let message = `HTTP error ${response.status}`;
        try {
            const errData = await response.json();
            if (errData.error) {
                errorCode = errData.error.code || errorCode;
                message = errData.error.message || message;
            }
        } catch (e) {
            // Not a JSON response
        }
        const error = new Error(message);
        error.status = response.status;
        error.code = errorCode;
        error.endpoint = endpoint;
        throw error;
    }
    return response.json();
}

// REST API calls

async function switchOperatingMode(mode) {
    try {
        const response = await fetch('/api/mode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode })
        });
        
        const data = await handleResponse(response, '/api/mode');
        
        operatingMode = mode;
        
        // Update button visual state
        const btnSim = document.getElementById("btn-mode-sim");
        const btnSensor = document.getElementById("btn-mode-sensor");
        const iotSec = document.getElementById("iot-simulator-section");
        const opsSec = document.getElementById("ops-btn-sec");
        const capSec = document.getElementById("capacity-sec");
        
        if (mode === "SIMULATION") {
            btnSim.classList.add("active");
            btnSensor.classList.remove("active");
            iotSec.style.display = "none";
            opsSec.style.opacity = "1";
            opsSec.style.pointerEvents = "auto";
            capSec.style.opacity = "1";
            capSec.style.pointerEvents = "auto";
            addTerminalLog("System switched to Simulation Mode. Manual filling active.", "cyan");
        } else {
            btnSim.classList.remove("active");
            btnSensor.classList.add("active");
            iotSec.style.display = "block";
            opsSec.style.opacity = "0.5";
            opsSec.style.pointerEvents = "none";
            capSec.style.opacity = "0.5";
            capSec.style.pointerEvents = "none";
            addTerminalLog("System switched to SENSOR Mode. Listening for IoT Node packet broadcasts...", "orange");
        }
        
        modalShown = false;
        if (mode === "SENSOR") {
            stopSimulation();
        }
        renderTankStatus(data.data.tank);
        updateSimulationControls();
    } catch (error) {
        handleApiError(error, '/api/mode');
    }
}

async function sendIoTTelemetry(distanceCm) {
    try {
        addTerminalLog(`Sending IoT sensor packet: distance_cm = ${distanceCm}`, "orange");
        const response = await fetch('/api/sensor-reading', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ distance_cm: distanceCm })
        });
        
        const data = await handleResponse(response, '/api/sensor-reading');
        const tel = data.data.sensor;
        addTerminalLog(`IoT Packet processed. Raw: ${tel.raw_value}cm -> Filtered: ${tel.filtered_value}cm -> Est. Level: ${tel.estimated_level}L. Status: ${tel.sensor_status}`, "green");
        
        await fetchStatus();
    } catch (error) {
        handleApiError(error, '/api/sensor-reading');
    }
}

async function fetchStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await handleResponse(response, '/api/status');
        renderTankStatus(data.data.tank);
        renderSensorData(data.data.sensor, data.data.sensor_hardware);
    } catch (error) {
        handleApiError(error, '/api/status');
    }
}

async function autoFillStep() {
    try {
        const response = await fetch('/api/fill', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount: 100, source: "SYSTEM" })
        });
        
        const data = await handleResponse(response, '/api/fill');
        renderTankStatus(data.data.tank);
    } catch (error) {
        handleApiError(error, '/api/fill');
    }
}

async function triggerManualFill(amount) {
    try {
        addTerminalLog(`Requesting manual fill of +${amount} L...`, "cyan");
        const response = await fetch('/api/fill', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount, source: "USER" })
        });
        
        const data = await handleResponse(response, '/api/fill');
        renderTankStatus(data.data.tank);
    } catch (error) {
        handleApiError(error, '/api/fill');
    }
}

async function changeCapacity(capacity) {
    try {
        addTerminalLog(`Requesting capacity adjustment to ${capacity} L...`, "orange");
        const response = await fetch('/api/capacity', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ capacity })
        });
        
        modalShown = false;
        previousWaterLevel = 0;
        
        const data = await handleResponse(response, '/api/capacity');
        renderTankStatus(data.data.tank);
    } catch (error) {
        handleApiError(error, '/api/capacity');
    }
}

async function resetTank() {
    try {
        addTerminalLog("Sending system reset instruction...", "red");
        const response = await fetch('/api/reset', {
            method: 'POST'
        });
        
        modalShown = false;
        previousWaterLevel = 0;
        
        const data = await handleResponse(response, '/api/reset');
        renderTankStatus(data.data.tank);
    } catch (error) {
        handleApiError(error, '/api/reset');
    }
}

async function triggerSearch() {
    currentSearchRequestId++;
    const requestId = currentSearchRequestId;
    
    // Clear old visualization display placeholder (Step 9)
    const container = document.getElementById("dls-tree-container");
    container.innerHTML = `<span class="field-desc">Executing search request #${requestId}...</span>`;
    
    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                initial_state: currentWaterLevel, 
                target_state: tankCapacity, 
                depth_limit: depthLimit 
            })
        });
        
        const data = await handleResponse(response, '/api/search');
        
        // Prevent stale overlapping request responses updating UI
        if (requestId !== currentSearchRequestId) {
            console.log(`Ignoring stale search response for request #${requestId}`);
            return;
        }
        
        latestDlsData = data.data.dls;
        renderDlsResult(latestDlsData);
    } catch (error) {
        if (requestId === currentSearchRequestId) {
            handleApiError(error, '/api/search');
        }
    }
}

async function fetchIntelligence() {
    try {
        const response = await fetch('/api/intelligence');
        const data = await handleResponse(response, '/api/intelligence');
        renderIntelligence(data.data.intelligence);
    } catch (error) {
        console.error("Intelligence request error: ", error);
    }
}

// UI Dedicated Rendering Functions (Explicit Response Mapping)

function renderTankStatus(tank) {
    if (!tank) return;
    
    previousWaterLevel = currentWaterLevel;
    currentWaterLevel = tank.water;
    tankCapacity = tank.capacity;
    currentPercentage = tank.percentage;
    isFull = tank.is_full;
    operatingMode = tank.operating_mode;
    
    if (isFull && operatingMode === "SIMULATION") {
        isSimulationRunning = false;
        isSimulationPaused = false;
        if (simulationTimeoutTimer) {
            clearTimeout(simulationTimeoutTimer);
            simulationTimeoutTimer = null;
        }
        updatePlaybackStateLabel("COMPLETE");
    }
    
    // 1. Update operating mode badge & header status
    const modeBadge = document.getElementById("operating-mode-badge");
    const headerStatus = document.getElementById("header-status-text");
    if (modeBadge) modeBadge.textContent = operatingMode === "SIMULATION" ? "SIMULATED STATE" : "IOT STREAM ACTIVE";
    if (headerStatus) headerStatus.textContent = operatingMode === "SIMULATION" ? "SYSTEM ONLINE (SIM)" : "SYSTEM ONLINE (IoT)";
    
    // 1b. Update active flow status badge inside digital twin header
    const flowBadge = document.getElementById("flow-status-badge");
    if (flowBadge) {
        const diff = currentWaterLevel - previousWaterLevel;
        flowBadge.className = "flow-status-badge"; // reset classes
        if (isFull) {
            flowBadge.classList.add("flow-critical");
            flowBadge.textContent = "▲ LOCKDOWN (FULL)";
        } else if (diff > 0 && previousWaterLevel !== 0) {
            flowBadge.classList.add("flow-filling");
            flowBadge.textContent = `▶ FILLING (+${diff}L)`;
        } else if (diff < 0) {
            flowBadge.classList.add("flow-draining");
            flowBadge.textContent = `◀ DRAINING (${diff}L)`;
        } else {
            flowBadge.classList.add("flow-stable");
            flowBadge.textContent = "● SYSTEM STABLE";
        }
    }
    
    // 2. Update Tank visuals
    updateTank(currentPercentage, isFull);
    
    // 3. Update Timeline progress bar
    updateTimeline(currentWaterLevel, tankCapacity, currentPercentage);
    
    // 4. Update stats cards text contents
    const lvlVal = document.getElementById("bottom-lvl-val");
    if (lvlVal) lvlVal.textContent = `${currentWaterLevel} L`;
    
    const diffLabel = document.getElementById("bottom-lvl-diff");
    if (diffLabel) {
        const diff = currentWaterLevel - previousWaterLevel;
        if (currentWaterLevel === 0) {
            diffLabel.textContent = "▼ RESET";
            diffLabel.className = "gsc-sub-val text-red";
        } else if (diff > 0) {
            diffLabel.textContent = `▲ +${diff} L`;
            diffLabel.className = "gsc-sub-val text-cyan";
        } else if (diff < 0) {
            diffLabel.textContent = `▼ ${diff} L`;
            diffLabel.className = "gsc-sub-val text-red";
        } else {
            diffLabel.textContent = "● STABLE";
            diffLabel.className = "gsc-sub-val text-dark";
        }
    }
    
    const capVal = document.getElementById("bottom-cap-val");
    if (capVal) capVal.textContent = `${tankCapacity} L`;
    
    const capPct = document.getElementById("bottom-cap-pct");
    if (capPct) capPct.textContent = `${currentPercentage}% FULL`;
    
    // 5. Trigger DLS search & intelligence updates separately (Step 11 requirement 5)
    triggerSearch();
    fetchIntelligence();
    
    // 6. Handle alert warning modal
    if (isFull) {
        if (!modalShown) {
            showFullModal(currentWaterLevel, tankCapacity);
        }
    }
    updateSimulationControls();
}

function renderSensorData(sensor, sensor_hardware) {
    // Initial empty/disconnected sensor states fallback (Safe null handling)
    const s = sensor || {
        raw_value: null,
        filtered_value: null,
        sensor_status: "DISCONNECTED",
        data_quality: "UNAVAILABLE",
        warning_message: "No sensor reading available"
    };
    
    const hw = sensor_hardware || {
        sensor_id: "IOT_NODE_UNKNOWN",
        provider_type: "IOT_HARDWARE",
        sensor_status: "DISCONNECTED",
        data_quality: "UNAVAILABLE",
        warning_message: "No hardware details"
    };

    const telemetryStatus = document.getElementById("sensor-telemetry-status");
    if (telemetryStatus) {
        telemetryStatus.textContent = 
            s.raw_value !== null ? `Raw: ${s.raw_value}cm | Filtered: ${s.filtered_value}cm` : `Sensor reading: N/A`;
    }
        
    const hardwareStatus = document.getElementById("sensor-hardware-status");
    if (hardwareStatus) {
        hardwareStatus.textContent = 
            `ID: ${hw.sensor_id} | Status: ${hw.sensor_status} (${hw.data_quality})`;
    }
        
    const capCard = document.getElementById("stat-card-capacity");
    if (capCard) {
        if (hw.sensor_status === "STALE" || hw.sensor_status === "DISCONNECTED") {
            capCard.classList.add("alert-state");
        } else {
            capCard.classList.remove("alert-state");
        }
    }
}

function renderDlsResult(dls) {
    if (!dls) return;
    
    const countLbl = document.getElementById("dls-lbl-nodes-count");
    if (countLbl) countLbl.textContent = `${dls.explored_nodes} / ${dls.generated_nodes}`;
    
    const prunedLbl = document.getElementById("dls-lbl-pruned");
    if (prunedLbl) prunedLbl.textContent = dls.pruned_nodes;
    
    // Render the tree structure
    const container = document.getElementById("dls-tree-container");
    if (container) {
        container.innerHTML = "";
        
        if (!dls.nodes || dls.nodes.length === 0) {
            container.innerHTML = `<span class="field-desc">No search tree state space.</span>`;
            return;
        }
        
        // Build nested tree structure
        const nodes = dls.nodes;
        globalSearchNodes = nodes; 
        const nodeMap = {};
        let root = null;
        
        nodes.forEach(n => {
            nodeMap[n.node_id] = { ...n, children: [] };
        });
        
        nodes.forEach(n => {
            if (n.parent_id === null) {
                root = nodeMap[n.node_id];
            } else {
                if (nodeMap[n.parent_id]) {
                    nodeMap[n.parent_id].children.push(nodeMap[n.node_id]);
                }
            }
        });
        
        if (root) {
            renderTreeNode(root, container);
        }
    }
    
    // Print search engine updates to scrolling log terminal
    logDlsRound(dls);
}

function renderIntelligence(intelligence) {
    if (!intelligence) return;
    
    const p = intelligence.predictions;
    const a = intelligence.anomalies;
    if (!p || !a) return;
    
    // Update Smart Status panel variables
    const trendVal = document.getElementById("intel-trend");
    if (trendVal) {
        trendVal.textContent = p.trend;
        if (p.trend === "RISING") {
            trendVal.className = "intel-val text-cyan";
            document.getElementById("intel-time").textContent = `Full: ${p.estimated_time_until_full}`;
        } else if (p.trend === "FALLING") {
            trendVal.className = "intel-val text-orange";
            document.getElementById("intel-time").textContent = `Empty: ${p.estimated_time_until_empty}`;
        } else {
            trendVal.className = "intel-val text-dark";
            document.getElementById("intel-time").textContent = "N/A (Stable)";
        }
    }
    
    const riskVal = document.getElementById("intel-risk");
    if (riskVal) {
        riskVal.textContent = `${p.overflow_risk.level} (${p.overflow_risk.score.toFixed(2)})`;
        if (p.overflow_risk.level === "CRITICAL" || p.overflow_risk.level === "HIGH") {
            riskVal.className = "intel-val text-red";
        } else if (p.overflow_risk.level === "MEDIUM") {
            riskVal.className = "intel-val text-orange";
        } else {
            riskVal.className = "intel-val text-green";
        }
    }
    
    renderAnomaly(a);
    
    const recVal = document.getElementById("intel-rec");
    if (recVal) recVal.textContent = `Recommendation: ${p.recommendation}`;
}

function renderAnomaly(anomaly) {
    if (!anomaly) return;
    
    const anomalyVal = document.getElementById("intel-anomaly");
    const currentCard = document.getElementById("stat-card-current");
    
    if (anomaly.anomaly_detected) {
        if (anomalyVal) {
            anomalyVal.textContent = `${anomaly.anomaly_type} (${anomaly.severity})`;
            anomalyVal.className = "intel-val text-red";
        }
        if (currentCard) currentCard.classList.add("alert-state");
        addTerminalLog(`🚨 ANOMALY ALERT: ${anomaly.explanation}`, "red");
    } else {
        if (anomalyVal) {
            anomalyVal.textContent = anomaly.explanation.includes("Baseline") ? "AWAITING HIST" : "NONE";
            anomalyVal.className = "intel-val text-green";
        }
        if (currentCard) currentCard.classList.remove("alert-state");
    }
}

function updateTank(percentage, isFull) {
    const tankElement = document.getElementById("cylinder-tank");
    const fillElement = document.getElementById("cylinder-water");
    const volDisplay = document.getElementById("tank-vol-val");
    const pctDisplay = document.getElementById("tank-pct-val");
    
    fillElement.style.height = `${percentage}%`;
    volDisplay.textContent = `${currentWaterLevel} L`;
    
    if (isFull) {
        tankElement.classList.add("full-state");
        pctDisplay.textContent = "FULL";
    } else {
        tankElement.classList.remove("full-state");
        pctDisplay.textContent = `${percentage}%`;
    }

    // Dynamic Scale Marks Highlighting
    const scaleMarks = document.querySelectorAll(".scale-mark");
    scaleMarks.forEach(mark => {
        const span = mark.querySelector("span");
        if (span) {
            const val = parseInt(span.textContent, 10);
            if (val === currentWaterLevel) {
                mark.classList.add("active");
            } else {
                mark.classList.remove("active");
            }
        }
    });
}

function updateTimeline(water, capacity, percentage) {
    const trackFill = document.getElementById("timeline-track-fill");
    trackFill.style.width = `${percentage}%`;
    
    const nodes = document.querySelectorAll(".timeline-node");
    nodes.forEach(node => {
        const val = parseInt(node.getAttribute("data-value"), 10);
        node.className = "timeline-node";
        
        if (val < water) {
            node.classList.add("visited");
        } else if (val === water) {
            node.classList.add("current");
        }
        
        if (val === capacity) {
            node.classList.add("target");
        }
    });
}

function renderTreeNode(node, container) {
    const wrapper = document.createElement("div");
    wrapper.className = "dls-tree-node-wrapper";
    wrapper.style.paddingLeft = `${node.depth * 15}px`;
    
    const nodeBox = document.createElement("div");
    nodeBox.className = `dls-tree-node ${node.status.toLowerCase()}`;
    
    let actionLabel = "";
    if (node.action && node.action !== "START") {
        const parts = node.action.split("_");
        actionLabel = parts[0] === "FILL" ? `+${parts[1]}` : `-${parts[1]}`;
    }
    
    let parentStateStr = "";
    if (node.parent_id !== null) {
        const parentNode = globalSearchNodes.find(n => n.node_id === node.parent_id);
        if (parentNode) {
            parentStateStr = `<span class="tree-node-parent-ref">from ${parentNode.state}L</span>`;
        }
    }
    
    // Draw stylized ASCII branch connectors for sibling trees
    let connector = "";
    if (node.depth > 0) {
        const siblings = globalSearchNodes.filter(n => n.parent_id === node.parent_id);
        const isLast = siblings.indexOf(node) === siblings.length - 1;
        connector = `<span class="tree-branch-connector">${isLast ? "└─" : "├─"}</span>`;
    }
    
    nodeBox.innerHTML = `
        ${connector}
        <span class="tree-node-state">${node.state}L</span>
        ${actionLabel ? `<span class="tree-node-action">${actionLabel}</span>` : ""}
        ${parentStateStr}
        <span class="tree-node-depth">d:${node.depth}</span>
        ${node.status === "PRUNED" ? `<span class="tree-node-pruned-badge">✖</span>` : ""}
        ${node.status === "TARGET" ? `<span class="tree-node-target-badge">★</span>` : ""}
    `;
    
    wrapper.appendChild(nodeBox);
    container.appendChild(wrapper);
    
    // Recursively draw children
    node.children.forEach(child => {
        renderTreeNode(child, container);
    });
}

function logDlsRound(searchResult) {
    const init = searchResult.initial_state;
    const tgt = searchResult.target_state;
    const limit = searchResult.depth_limit;
    
    const logHash = `${init}-${tgt}-${limit}-${searchResult.visited_states.join(",")}-${searchResult.target_found}-${searchResult.termination_reason}`;
    if (logHash === lastLoggedHash) return;
    lastLoggedHash = logHash;
    
    const logsContainer = document.getElementById("terminal-logs");
    if (logsContainer.children.length > 25) {
        logsContainer.innerHTML = '<div class="term-line text-dark">> Log buffer truncated...</div>';
    }

    addTerminalLog("------------------------------------");
    addTerminalLog(`DLS Traversal cycle initialized.`);
    addTerminalLog(`Initial State: ${init}L`);
    addTerminalLog(`Target State: ${tgt}L`);
    addTerminalLog(`Depth Limit: ${limit}`);
    addTerminalLog(`Root initialized at depth 0.`);
    
    const childrenCount = searchResult.generated_nodes > 1 ? searchResult.generated_nodes - 1 : 0;
    addTerminalLog(`Generated ${childrenCount} valid child states.`);
    addTerminalLog(`Pruned invalid or cyclic states.`);
    
    if (searchResult.target_found) {
        addTerminalLog(`✓ Target resolved at depth ${searchResult.target_depth}.`, "green");
    } else {
        addTerminalLog(`✘ DLS Aborted: Reason = ${searchResult.termination_reason}`, "orange");
    }
    
    // Add final search summary (Step 5)
    addTerminalLog(`Search Result: ${searchResult.target_found ? "TARGET_FOUND" : searchResult.termination_reason}`);
    addTerminalLog(`Initial State: ${init}L`);
    addTerminalLog(`Target State: ${tgt}L`);
    addTerminalLog(`Depth Limit: ${limit}`);
    addTerminalLog(`Target Depth: ${searchResult.target_depth}`);
    addTerminalLog(`Explored Nodes: ${searchResult.explored_nodes}`);
    addTerminalLog(`Generated Nodes: ${searchResult.generated_nodes}`);
    addTerminalLog(`Pruned Nodes: ${searchResult.pruned_nodes}`);
    if (searchResult.target_found) {
        addTerminalLog(`Solution Path: ${searchResult.path.map(s => s + 'L').join(" -> ")}`, "green");
    }
}

function addTerminalLog(message, type = "") {
    const logsContainer = document.getElementById("terminal-logs");
    if (!logsContainer) return;
    
    const line = document.createElement("div");
    line.className = `term-line ${type}`;
    line.textContent = `> ${message}`;
    logsContainer.appendChild(line);
    
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

function showFullModal(water, capacity) {
    const modal = document.getElementById("full-modal");
    document.getElementById("modal-water-digits").textContent = water;
    document.getElementById("modal-cap-digits").textContent = capacity;
    
    modal.classList.add("active");
    modalShown = true;
    
    addTerminalLog("🚨 SYSTEM LOCKDOWN: Target capacity matched. Full alarm active.", "red");
}

function closeFullModal() {
    const modal = document.getElementById("full-modal");
    modal.classList.remove("active");
    startPolling(); // Resume simulation polling
}

function handleApiError(error, contextEndpoint = "unknown") {
    console.error("Error occurred in context:", contextEndpoint, error);
    
    let type = "NETWORK_ERROR";
    let endpoint = error.endpoint || contextEndpoint;
    let status = error.status || "N/A";
    let code = error.code || "CONNECTION_FAILURE";
    let message = error.message || "Failed to communicate with Flask server.";
    
    // Classify error type (Step 8 classification rules)
    if (error.name === "TypeError" || error.name === "ReferenceError") {
        type = "FRONTEND_RENDER_ERROR";
        code = error.name;
        message = error.stack ? error.stack.split('\n')[0] : error.message;
    } else if (error.status) {
        type = error.code && error.code !== "HTTP_ERROR" ? "BACKEND_ERROR" : "HTTP_ERROR";
    } else if (error.message && error.message.includes("Schema")) {
        type = "RESPONSE_SCHEMA_ERROR";
    }
    
    addTerminalLog(`Request Error`, "red");
    addTerminalLog(`Type: ${type}`, "red");
    addTerminalLog(`Endpoint: ${endpoint}`, "red");
    addTerminalLog(`HTTP Status: ${status}`, "red");
    addTerminalLog(`Error Code: ${code}`, "red");
    addTerminalLog(`Message: ${message}`, "red");
    
    const diffLabel = document.getElementById("bottom-lvl-diff");
    if (diffLabel && type === "NETWORK_ERROR") {
        diffLabel.textContent = "OFFLINE";
        diffLabel.className = "gsc-sub-val text-red";
    }
}

// Tank Simulation Controls (Start, Pause, Resume, Stop, Reset)

function startSimulation() {
    if (operatingMode === "SENSOR" || isFull) {
        return;
    }
    
    // Clear any duplicate timers first (Requirement 5)
    if (simulationTimeoutTimer) {
        clearTimeout(simulationTimeoutTimer);
        simulationTimeoutTimer = null;
    }

    isSimulationRunning = true;
    isSimulationPaused = false;

    updatePlaybackStateLabel("RUNNING");
    updateSimulationControls();

    addTerminalLog("Water Simulation started.", "cyan");

    // Execute first step immediately (Requirement 1)
    autoFillStep();
    
    // Schedule loop steps recursively using setTimeout (Requirement 4)
    scheduleNextSimulationStep();
}

function pauseSimulation() {
    isSimulationPaused = true;

    if (simulationTimeoutTimer) {
        clearTimeout(simulationTimeoutTimer);
        simulationTimeoutTimer = null;
    }

    updatePlaybackStateLabel("PAUSED");
    updateSimulationControls();

    addTerminalLog("Water Simulation paused.", "orange");
}

function resumeSimulation() {
    if (operatingMode === "SENSOR" || isFull) {
        return;
    }

    // Clear duplicate timers (Requirement 5)
    if (simulationTimeoutTimer) {
        clearTimeout(simulationTimeoutTimer);
        simulationTimeoutTimer = null;
    }

    isSimulationRunning = true;
    isSimulationPaused = false;

    updatePlaybackStateLabel("RUNNING");
    updateSimulationControls();

    addTerminalLog("Water Simulation resumed.", "cyan");

    // Execute immediately on resume
    autoFillStep();
    
    scheduleNextSimulationStep();
}

function stopSimulation() {
    isSimulationRunning = false;
    isSimulationPaused = false;

    if (simulationTimeoutTimer) {
        clearTimeout(simulationTimeoutTimer);
        simulationTimeoutTimer = null;
    }

    updatePlaybackStateLabel("STOPPED");
    updateSimulationControls();

    addTerminalLog("Water Simulation stopped.", "red");
}

async function resetSimulation() {
    // 1. Stop every active simulation timer before calling the reset API (Requirement 10)
    isSimulationRunning = false;
    isSimulationPaused = false;

    if (simulationTimeoutTimer) {
        clearTimeout(simulationTimeoutTimer);
        simulationTimeoutTimer = null;
    }

    addTerminalLog("Resetting water simulation...", "red");

    // 2. Call the reset API
    await resetTank();

    // 3. Reset playback state label to READY
    updatePlaybackStateLabel("READY");
    updateSimulationControls();
}

function scheduleNextSimulationStep() {
    if (simulationTimeoutTimer) {
        clearTimeout(simulationTimeoutTimer);
    }
    simulationTimeoutTimer = setTimeout(() => {
        if (isSimulationRunning && !isSimulationPaused && !isFull) {
            autoFillStep();
            scheduleNextSimulationStep();
        }
    }, 2000);
}

function updatePlaybackStateLabel(state) {
    const label = document.getElementById("playback-state-label");
    if (!label) return;
    
    label.className = "playback-state-label"; // Reset classes
    
    if (state === "READY") {
        label.classList.add("playback-ready");
        label.textContent = "STATE: READY";
    } else if (state === "RUNNING") {
        label.classList.add("playback-running");
        label.textContent = "STATE: RUNNING";
    } else if (state === "PAUSED") {
        label.classList.add("playback-paused");
        label.textContent = "STATE: PAUSED";
    } else if (state === "STOPPED") {
        label.classList.add("playback-stopped");
        label.textContent = "STATE: STOPPED";
    } else if (state === "COMPLETE") {
        label.classList.add("playback-complete");
        label.textContent = "STATE: COMPLETE";
    }
}

function updateSimulationControls() {
    const btnStart = document.getElementById("btn-algo-start");
    const btnPause = document.getElementById("btn-algo-pause");
    const btnResume = document.getElementById("btn-algo-resume");
    const btnStop = document.getElementById("btn-algo-stop");
    const btnReset = document.getElementById("btn-algo-reset");

    if (!btnStart || !btnPause || !btnResume || !btnStop || !btnReset) {
        return;
    }

    if (operatingMode === "SENSOR") {
        btnStart.disabled = true;
        btnPause.disabled = true;
        btnResume.disabled = true;
        btnStop.disabled = true;
        btnReset.disabled = true;
        return;
    }

    if (isFull) {
        // Tank is full!
        btnStart.disabled = true;
        btnPause.disabled = true;
        btnResume.disabled = true;
        btnStop.disabled = true;
        btnReset.disabled = false; // Reset must remain enabled (Requirement 12)
        return;
    }

    if (!isSimulationRunning && !isSimulationPaused) {
        // stopped/idle
        btnStart.disabled = false;
        btnPause.disabled = true;
        btnResume.disabled = true;
        btnStop.disabled = true;
        btnReset.disabled = (currentWaterLevel === 0);
    } else if (isSimulationRunning && !isSimulationPaused) {
        // running
        btnStart.disabled = true;
        btnPause.disabled = false;
        btnResume.disabled = true;
        btnStop.disabled = false;
        btnReset.disabled = false;
    } else if (isSimulationPaused) {
        // paused
        btnStart.disabled = true;
        btnPause.disabled = true;
        btnResume.disabled = false;
        btnStop.disabled = false;
        btnReset.disabled = false;
    }
}

// Solr AI Doctor — Interactive Dashboard Client

let allEvents = [];
let allIncidents = [];
let activeFilter = 'ALL';

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    loadScenario('mixed_incident');
});

function initEventListeners() {
    // Scenario buttons
    document.querySelectorAll('.btn-scenario').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.btn-scenario').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadScenario(btn.dataset.scenario);
        });
    });

    // Refresh button
    document.getElementById('btn-refresh').addEventListener('click', fetchDashboardData);

    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            activeFilter = btn.dataset.filter;
            renderTimeline();
        });
    });

    // Modal Close
    document.getElementById('modal-close').addEventListener('click', () => {
        document.getElementById('rca-modal').classList.add('hidden');
    });

    // Custom Ingest Modal
    document.getElementById('btn-custom-ingest').addEventListener('click', () => {
        document.getElementById('ingest-modal').classList.remove('hidden');
    });

    document.getElementById('ingest-close').addEventListener('click', () => {
        document.getElementById('ingest-modal').classList.add('hidden');
    });

    document.getElementById('btn-submit-ingest').addEventListener('click', submitCustomLogs);
}

async function loadScenario(scenarioName) {
    try {
        const res = await fetch(`/api/pipeline/scenario/${scenarioName}`, { method: 'POST' });
        if (!res.ok) throw new Error(`Failed to load scenario: ${res.statusText}`);
        await fetchDashboardData();
    } catch (err) {
        console.error('Error loading scenario:', err);
    }
}

async function fetchDashboardData() {
    try {
        const [healthRes, incidentsRes, anomaliesRes, eventsRes] = await Promise.all([
            fetch('/api/cluster/health'),
            fetch('/api/incidents'),
            fetch('/api/anomalies'),
            fetch('/api/events?limit=200')
        ]);

        const health = await healthRes.json();
        const incidents = await incidentsRes.json();
        const anomalies = await anomaliesRes.json();
        const events = await eventsRes.json();

        allEvents = events;
        allIncidents = incidents;

        renderClusterHealth(health);
        renderNodesGrid(health.node_summaries);
        renderIncidents(incidents);
        renderTimeline();
        document.getElementById('count-anomalies').textContent = anomalies.length;

    } catch (err) {
        console.error('Error fetching dashboard data:', err);
    }
}

function renderClusterHealth(health) {
    const scoreElem = document.getElementById('cluster-score');
    const badgeElem = document.getElementById('cluster-badge');
    const concernElem = document.getElementById('cluster-concern');

    scoreElem.textContent = `${health.overall_health_score}%`;
    badgeElem.textContent = health.state;
    badgeElem.className = `badge badge-${health.state.toLowerCase()}`;
    concernElem.textContent = health.primary_concern;

    document.getElementById('count-total').textContent = health.total_nodes;
    document.getElementById('count-healthy').textContent = health.healthy_nodes_count;
    document.getElementById('count-warning').textContent = health.warning_nodes_count;
    document.getElementById('count-critical').textContent = health.critical_nodes_count;
    document.getElementById('count-incidents').textContent = health.active_incidents_count;
}

function renderNodesGrid(nodeSummaries) {
    const grid = document.getElementById('nodes-grid');
    grid.innerHTML = '';

    Object.values(nodeSummaries || {}).forEach(node => {
        const card = document.createElement('div');
        card.className = `node-card glass-card ${node.state}`;

        const issuesHtml = (node.primary_issues || []).map(iss => `<li>${iss}</li>`).join('');

        card.innerHTML = `
            <div class="node-card-top">
                <span class="node-name">${node.node_id}</span>
                <span class="badge badge-${node.state.toLowerCase()}">${node.state} (${node.health_score}%)</span>
            </div>
            <div class="node-metrics-bar">
                <div>
                    <div class="n-met-label">Avg QTime</div>
                    <div class="n-met-val">${node.avg_qtime_ms}ms</div>
                </div>
                <div>
                    <div class="n-met-label">Max GC Pause</div>
                    <div class="n-met-val">${node.max_gc_pause_ms}ms</div>
                </div>
                <div>
                    <div class="n-met-label">Errors / Anom</div>
                    <div class="n-met-val">${node.error_count} / ${node.active_anomalies_count}</div>
                </div>
            </div>
            <div class="node-issues-box">
                <strong>Observed Conditions:</strong>
                <ul>${issuesHtml}</ul>
            </div>
        `;
        grid.appendChild(card);
    });
}

function renderIncidents(incidents) {
    const container = document.getElementById('incidents-container');
    container.innerHTML = '';

    if (!incidents || incidents.length === 0) {
        container.innerHTML = `<div class="glass-card text-muted">No active incidents detected. Cluster is operating within normal baseline.</div>`;
        return;
    }

    incidents.forEach(inc => {
        const card = document.createElement('div');
        card.className = 'incident-card';
        card.addEventListener('click', () => openRCAModal(inc.incident_id));

        const rcaSummary = inc.rca_result 
            ? inc.rca_result.root_cause_summary 
            : (inc.deterministic_candidates[0]?.primary_hypothesis || "Correlating incident telemetry...");

        card.innerHTML = `
            <div class="incident-card-top">
                <span class="badge badge-${inc.severity.toLowerCase()}">${inc.severity}</span>
                <span class="t-time">${new Date(inc.start_time).toLocaleTimeString()} - ${new Date(inc.end_time).toLocaleTimeString()}</span>
            </div>
            <div class="incident-title">${inc.title}</div>
            <div class="incident-meta-row">
                <span>Affected Nodes: ${inc.affected_nodes.join(', ')}</span>
                <span>Anomalies: ${inc.anomaly_ids.length}</span>
                <span>Events: ${inc.event_ids.length}</span>
            </div>
            <div class="incident-rca-preview">
                <strong>RCA Hypothesis:</strong> ${rcaSummary}
            </div>
        `;
        container.appendChild(card);
    });
}

function renderTimeline() {
    const stream = document.getElementById('timeline-stream');
    stream.innerHTML = '';

    let filtered = allEvents;
    if (activeFilter === 'SOLR') {
        filtered = allEvents.filter(e => e.source === 'SOLR');
    } else if (activeFilter === 'JVM_GC') {
        filtered = allEvents.filter(e => e.source === 'JVM_GC');
    } else if (activeFilter === 'ANOMALY') {
        filtered = allEvents.filter(e => e.severity === 'ERROR' || e.severity === 'WARN');
    }

    filtered.slice(0, 80).forEach(e => {
        const row = document.createElement('div');
        row.className = 'timeline-row';
        row.innerHTML = `
            <span class="t-time">${new Date(e.timestamp).toISOString().substring(11, 23)}</span>
            <span class="t-node">${e.node_id}</span>
            <span class="t-source ${e.source}">${e.source}</span>
            <span class="t-msg" title="${e.message}">${e.message}</span>
        `;
        stream.appendChild(row);
    });
}

async function openRCAModal(incidentId) {
    const modal = document.getElementById('rca-modal');
    modal.classList.remove('hidden');

    try {
        const res = await fetch(`/api/incidents/${incidentId}`);
        const inc = await res.json();
        const rca = inc.rca_result;

        document.getElementById('modal-title').textContent = inc.title;
        document.getElementById('modal-severity').textContent = inc.severity;
        document.getElementById('modal-severity').className = `badge badge-${inc.severity.toLowerCase()}`;

        if (rca) {
            document.getElementById('modal-root-cause').textContent = rca.root_cause_summary;
            document.getElementById('modal-causality').textContent = rca.causality_assessment;
            document.getElementById('modal-confidence').textContent = `Confidence: ${(rca.confidence * 100).toFixed(0)}%`;
            document.getElementById('modal-conf-reason').textContent = rca.confidence_reason;

            // Facts
            document.getElementById('modal-facts').innerHTML = (rca.observed_facts || []).map(f => `<li>${f}</li>`).join('');
            // Mechanisms
            document.getElementById('modal-mechanisms').innerHTML = (rca.inferred_mechanisms || []).map(m => `<li>${m}</li>`).join('');
            // Uncertainties
            document.getElementById('modal-uncertainties').innerHTML = (rca.uncertainties || []).map(u => `<li>${u}</li>`).join('');

            // Impact
            document.getElementById('modal-op-impact').textContent = rca.operational_impact;
            document.getElementById('modal-biz-impact').textContent = rca.business_impact;

            // Remediations
            document.getElementById('modal-immediate-rem').innerHTML = (rca.immediate_remediation || []).map(r => `
                <div class="rem-item ${r.priority}">
                    <div class="rem-action">${r.action}</div>
                    <div class="rem-rationale">${r.rationale}</div>
                </div>
            `).join('');

            document.getElementById('modal-preventative-rem').innerHTML = (rca.preventative_remediation || []).map(r => `
                <div class="rem-item ${r.priority}">
                    <div class="rem-action">${r.action}</div>
                    <div class="rem-rationale">${r.rationale}</div>
                </div>
            `).join('');

            // LLM Meta
            document.getElementById('modal-llm-model').textContent = rca.llm_status.model_name;
            document.getElementById('modal-llm-mode').textContent = rca.llm_status.mode;
            document.getElementById('modal-llm-latency').textContent = `${rca.llm_status.latency_ms} ms`;
        }
    } catch (err) {
        console.error('Error opening RCA modal:', err);
    }
}

async function submitCustomLogs() {
    const nodeId = document.getElementById('custom-node-id').value;
    const solrLogs = document.getElementById('custom-solr-logs').value;
    const gcLogs = document.getElementById('custom-gc-logs').value;

    try {
        const res = await fetch('/api/pipeline/ingest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ node_id: nodeId, solr_logs: solrLogs, gc_logs: gcLogs, run_llm: true })
        });
        if (!res.ok) throw new Error(`Ingest failed: ${res.statusText}`);
        
        document.getElementById('ingest-modal').classList.add('hidden');
        await fetchDashboardData();
    } catch (err) {
        alert('Failed to ingest custom logs: ' + err.message);
    }
}

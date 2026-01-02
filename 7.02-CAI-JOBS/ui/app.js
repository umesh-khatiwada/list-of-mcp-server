// Get API_BASE from injected global variable, fallback to .env via server-side template, else use window location
const API_BASE = window.API_BASE || document.body.getAttribute('data-api-base') || `${window.location.origin}`;
console.log('API_BASE:', API_BASE);

// Tab Management
function showTab(tabName, el) {
    console.log('showTab called with:', tabName);
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    const tabElement = document.getElementById(`${tabName}-tab`);
    console.log('tabElement:', tabElement);
    if (tabElement) {
        tabElement.classList.add('active');
        console.log('Added active class to tab element');
    }
    if (el) el.classList.add('active');

    if (tabName === 'sessions') loadSessions();
    if (tabName === 'advanced') loadAdvancedSessions();
    if (tabName === 'manifestworks') {
        console.log('Calling loadManifestWorks');
        loadManifestWorks();
    }
    if (tabName === 'jobs') {
        console.log('Calling loadJobs');
        loadJobs();
    }
    if (tabName === 'agents') loadAgents();
}

// Load Sessions
async function loadSessions() {
    const container = document.getElementById('sessions-list');
    container.innerHTML = '<div class="loading">Loading sessions...</div>';

    try {
        const response = await fetch(`${API_BASE}/api/sessions`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const sessions = await response.json();

        const container = document.getElementById('sessions-list');
        if (sessions.length === 0) {
            container.innerHTML = '<div class="empty-state"><h3>No sessions yet</h3><p>Create your first session to get started</p></div>';
            return;
        }

        container.innerHTML = sessions.map(session => `
            <div class="session-card">
                <div class="session-header">
                    <div class="session-name">${session.name}</div>
                    <span class="status-badge status-${session.status.toLowerCase()}">${session.status}</span>
                </div>
                <div class="session-info">
                    <div class="info-row">
                        <span class="info-label">ID:</span>
                        <span class="info-value">${session.id.substring(0, 8)}...</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Created:</span>
                        <span class="info-value">${new Date(session.created).toLocaleString()}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Job:</span>
                        <span class="info-value">${session.jobName}</span>
                    </div>
                </div>
                <div class="session-actions">
                    <button class="btn btn-primary btn-small" onclick="viewDetails('${session.id}', 'basic')">Details</button>
                    <button class="btn btn-secondary btn-small" onclick="viewLogs('${session.id}')">Logs</button>
                    <button class="btn btn-secondary btn-small" onclick="viewResults('${session.id}')">Result</button>
                    <button class="btn btn-danger btn-small" onclick="deleteSession('${session.id}', 'basic')">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading sessions:', error);
        showError('Failed to load sessions');
    }
}

// Load Advanced Sessions
async function loadAdvancedSessions() {
    const container = document.getElementById('advanced-sessions-list');
    container.innerHTML = '<div class="loading">Loading advanced sessions...</div>';

    try {
        const response = await fetch(`${API_BASE}/api/v2/sessions`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const sessions = await response.json();

        const container = document.getElementById('advanced-sessions-list');
        if (sessions.length === 0) {
            container.innerHTML = '<div class="empty-state"><h3>No advanced sessions yet</h3><p>Create an advanced session with parallel execution</p></div>';
            return;
        }

        container.innerHTML = sessions.map(session => {
            const progress = session.total_steps ?
                Math.round((session.completed_steps / session.total_steps) * 100) : 0;

            return `
                <div class="session-card">
                    <div class="session-header">
                        <div class="session-name">${session.name}</div>
                        <span class="status-badge status-${session.status.toLowerCase()}">${session.status}</span>
                    </div>
                    <div class="session-info">
                        <div class="info-row">
                            <span class="info-label">Mode:</span>
                            <span class="info-value">${session.mode}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Jobs:</span>
                            <span class="info-value">${session.job_names.length}</span>
                        </div>
                        ${session.total_steps ? `
                        <div class="info-row">
                            <span class="info-label">Progress:</span>
                            <span class="info-value">${session.completed_steps}/${session.total_steps}</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${progress}%"></div>
                        </div>
                        ` : ''}
                        ${session.progress_details && session.progress_details.manifest_details ? `
                        <div class="info-row">
                            <span class="info-label">Manifests:</span>
                            <span class="info-value">${session.progress_details.manifest_details.map(m => `${m.kind}: ${m.available ? 'Available' : 'Pending'}`).join(', ')}</span>
                        </div>
                        ` : ''}
                    </div>
                    <div class="session-actions">
                        <button class="btn btn-primary btn-small" onclick="viewDetails('${session.id}', 'advanced')">Details</button>
                        <button class="btn btn-secondary btn-small" onclick="viewLogsEnhanced('${session.id}', true)">Logs</button>
                        <button class="btn btn-secondary btn-small" onclick="viewResults('${session.id}')">Results</button>
                        <button class="btn btn-danger btn-small" onclick="deleteSession('${session.id}', 'advanced')">Delete</button>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading advanced sessions:', error);
        showError('Failed to load advanced sessions');
    }
}

// Load ManifestWorks
async function loadManifestWorks() {
    console.log('loadManifestWorks called');
    try {
        console.log('Fetching:', `${API_BASE}/api/v2/sessions/manifestworks`);
        const response = await fetch(`${API_BASE}/api/v2/sessions/manifestworks`);
        console.log('Response status:', response.status);
        const manifestworks = await response.json();
        console.log('ManifestWorks response:', manifestworks);

        const container = document.getElementById('manifestworks-list');
        if (manifestworks.length === 0) {
            container.innerHTML = '<div class="empty-state"><h3>No ManifestWorks found</h3><p>ManifestWorks will appear here when advanced sessions are created</p></div>';
            return;
        }

        container.innerHTML = manifestworks.map(mw => {
            const status = mw.status?.conditions?.find(c => c.type === 'Available')?.status === 'True' ? 'Available' : 'Pending';
            const created = mw.metadata?.creationTimestamp ? new Date(mw.metadata.creationTimestamp).toLocaleString() : 'Unknown';

            return `
                <div class="session-card">
                    <div class="session-header">
                        <div class="session-name">${mw.metadata?.name || 'Unknown'}</div>
                        <span class="status-badge status-${status.toLowerCase()}">${status}</span>
                    </div>
                    <div class="session-info">
                        <div class="info-row">
                            <span class="info-label">Namespace:</span>
                            <span class="info-value">${mw.metadata?.namespace || 'Unknown'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Created:</span>
                            <span class="info-value">${created}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Cluster:</span>
                            <span class="info-value">${mw.spec?.placement?.clusters?.[0]?.name || 'Unknown'}</span>
                        </div>
                        ${mw.status?.resourceStatus?.manifests ? `
                        <div class="info-row">
                            <span class="info-label">Resources:</span>
                            <span class="info-value">${mw.status.resourceStatus.manifests.length} manifests</span>
                        </div>
                        ` : ''}
                    </div>
                    <div class="session-actions">
                        <button class="btn btn-primary btn-small" onclick="viewManifestWorkDetails('${mw.metadata?.name}')">View Details</button>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading ManifestWorks:', error);
        showError('Failed to load ManifestWorks');
    }
}

// Load Jobs
async function loadJobs() {
    const container = document.getElementById('jobs-list');
    container.innerHTML = '<div class="loading">Loading jobs...</div>';

    try {
        let response = await fetch(`${API_BASE}/api/v2/sessions/jobs`);
        // Fallback to legacy endpoint if advanced API not available
        if (!response.ok) {
            response = await fetch(`${API_BASE}/api/sessions/jobs`);
        }
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const jobs = await response.json();
        console.log('Jobs response:', jobs);

        const container = document.getElementById('jobs-list');
        if (jobs.length === 0) {
            container.innerHTML = '<div class="empty-state"><h3>No jobs found</h3><p>Kubernetes jobs will appear here when sessions are created</p></div>';
            return;
        }

        container.innerHTML = jobs.map(job => {
            const created = job.created ? new Date(job.created).toLocaleString() : 'Unknown';
            const statusClass = job.status ? job.status.toLowerCase() : 'unknown';

            return `
                <div class="session-card">
                    <div class="session-header">
                        <div class="session-name">${job.name}</div>
                        <span class="status-badge status-${statusClass}">${job.status || 'Unknown'}</span>
                    </div>
                    <div class="session-info">
                        <div class="info-row">
                            <span class="info-label">Namespace:</span>
                            <span class="info-value">${job.namespace}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Created:</span>
                            <span class="info-value">${created}</span>
                        </div>
                        ${job.labels && Object.keys(job.labels).length > 0 ? `
                        <div class="info-row">
                            <span class="info-label">Labels:</span>
                            <span class="info-value">${Object.entries(job.labels).map(([k, v]) => `${k}=${v}`).join(', ')}</span>
                        </div>
                        ` : ''}
                    </div>
                    <div class="session-actions">
                        <button class="btn btn-primary btn-small" onclick="viewJobDetails('${job.name}')">View Details</button>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading jobs:', error);
        showError('Failed to load jobs');
    }
}

// Load Agents
async function loadAgents() {
    try {
        const response = await fetch(`${API_BASE}/api/mcp/agents`);
        const agents = await response.json();

        const container = document.getElementById('agents-list');
        if (agents.length === 0) {
            container.innerHTML = '<div class="empty-state"><h3>No agents configured</h3></div>';
            return;
        }

        container.innerHTML = agents.map(agent => `
            <div class="agent-card">
                <h3>${agent.replace('_', ' ').toUpperCase()}</h3>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading agents:', error);
    }
}

// UI Toggle Functions
function toggleMCPFields() {
    const transport = document.getElementById('mcp-transport')?.value;
    const isSSE = transport === 'sse';
    const urlGroup = document.getElementById('url-group');
    const cmdGroup = document.getElementById('command-group');
    if (urlGroup) urlGroup.style.display = isSSE ? 'block' : 'none';
    if (cmdGroup) cmdGroup.style.display = isSSE ? 'none' : 'block';
}

function toggleAdvancedMCPFields() {
    const transport = document.getElementById('adv-mcp-transport')?.value;
    const isSSE = transport === 'sse';
    const urlGroup = document.getElementById('adv-url-group');
    const cmdGroup = document.getElementById('adv-command-group');
    if (urlGroup) urlGroup.style.display = isSSE ? 'block' : 'none';
    if (cmdGroup) cmdGroup.style.display = isSSE ? 'none' : 'block';
}

function toggleVolcanoFields() {
    const volcanoEnabled = document.getElementById('adv-volcano-enabled')?.checked;
    const volcanoFields = document.getElementById('volcano-fields');
    if (volcanoFields) volcanoFields.style.display = volcanoEnabled ? 'block' : 'none';
}

// Event Listeners
document.getElementById('mcp-transport')?.addEventListener('change', toggleMCPFields);
document.getElementById('adv-mcp-transport')?.addEventListener('change', toggleAdvancedMCPFields);
document.getElementById('adv-volcano-enabled')?.addEventListener('change', toggleVolcanoFields);

// Test MCP Connection
async function testMCPConnection() {
    const transport = document.getElementById('mcp-transport').value;
    const mcpConfig = {
        timeout: 5,
        servers: [{
            name: document.getElementById('mcp-name').value,
            transport: transport,
            allow_insecure: document.getElementById('mcp-insecure').checked
        }]
    };

    if (transport === 'sse') {
        mcpConfig.servers[0].url = document.getElementById('mcp-url').value;
    } else {
        mcpConfig.servers[0].command = document.getElementById('mcp-command').value;
    }

    try {
        const response = await fetch(`${API_BASE}/api/mcp/test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(mcpConfig)
        });

        const results = await response.json();
        displayMCPResults(results);
    } catch (error) {
        console.error('Error testing MCP:', error);
        showError('Failed to test MCP connection');
    }
}

function displayMCPResults(results) {
    const container = document.getElementById('mcp-results');
    container.innerHTML = results.map(result => `
        <div class="mcp-result-card">
            <div class="mcp-result-header">
                <strong>${result.name}</strong>
                <span class="${result.reachable ? 'mcp-status-ok' : 'mcp-status-error'}">
                    ${result.reachable ? '✓ Reachable' : '✗ Failed'}
                </span>
            </div>
            <div><strong>Transport:</strong> ${result.transport}</div>
            <div><strong>Target:</strong> ${result.target}</div>
            <div><strong>Status:</strong> ${result.status}</div>
            ${result.latency_ms ? `<div><strong>Latency:</strong> ${result.latency_ms}ms</div>` : ''}
            ${result.detail ? `<div><strong>Detail:</strong> ${result.detail}</div>` : ''}
        </div>
    `).join('');
}

// Create Session Modal
function showCreateSession() {
    document.getElementById('create-modal').style.display = 'block';
}

function closeModal() {
    document.getElementById('create-modal').style.display = 'none';
}

function showAdvancedSessionModal() {
    document.getElementById('advanced-modal').style.display = 'block';
}

function closeAdvancedModal() {
    document.getElementById('advanced-modal').style.display = 'none';
}

document.getElementById('create-session-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const sessionData = {
        name: document.getElementById('session-name').value,
        prompt: document.getElementById('session-prompt').value
    };

    try {
        const response = await fetch(`${API_BASE}/api/sessions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(sessionData)
        });

        if (response.ok) {
            const session = await response.json();
            closeModal();
            showSuccess(`Session "${session.name}" created successfully!`);
            loadSessions();
            e.target.reset();
        } else {
            const error = await response.json().catch(() => ({ detail: 'Failed to create session' }));
            showError(error.detail || 'Failed to create session');
        }
    } catch (error) {
        console.error('Error creating session:', error);
        showError('Failed to create session');
    }
});

// Advanced session form
// (Transport toggling is now handled by toggleAdvancedMCPFields via direct event listener)

document.getElementById('advanced-session-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const agentType = document.getElementById('adv-agent')?.value || 'redteam_agent';
    const transport = document.getElementById('adv-mcp-transport')?.value || 'sse';

    const payload = {
        name: document.getElementById('adv-name')?.value || '',
        prompt: document.getElementById('adv-prompt')?.value || '',
        agent_type: agentType,
        model: document.getElementById('adv-model')?.value || 'deepseek/deepseek-chat',
    };

    const mcpName = document.getElementById('adv-mcp-name')?.value.trim() || '';
    const allowInsecure = document.getElementById('adv-mcp-insecure')?.checked || false;
    const mcpServer = {
        name: mcpName || agentType,
        transport,
        allow_insecure: allowInsecure,
    };

    if (transport === 'sse') {
        const urlInput = document.getElementById('adv-mcp-url');
        mcpServer.url = urlInput ? urlInput.value.trim() : '';
    } else {
        const cmdInput = document.getElementById('adv-mcp-command');
        mcpServer.command = cmdInput ? cmdInput.value.trim() : '';
    }

    // Volcano configuration
    const volcanoEnabled = document.getElementById('adv-volcano-enabled')?.checked;
    if (volcanoEnabled) {
        payload.volcano_config = {
            enabled: true,
            queue: document.getElementById('adv-volcano-queue')?.value || 'default',
            min_available: parseInt(document.getElementById('adv-volcano-min')?.value) || 1,
            replicas: parseInt(document.getElementById('adv-volcano-replicas')?.value) || 1
        };
    }

    // Only include overrides if a target was provided
    if ((transport === 'sse' && mcpServer.url) || (transport === 'stdio' && mcpServer.command)) {
        payload.mcp_agent_overrides = [
            {
                agent_type: agentType,
                mcp_servers: [mcpServer],
            },
        ];
    }

    try {
        const response = await fetch(`${API_BASE}/api/v2/sessions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (response.ok) {
            const session = await response.json();
            closeAdvancedModal();
            showSuccess(`Advanced session "${session.name || session.id}" created successfully!`);
            loadAdvancedSessions();
            e.target.reset();
        } else {
            const error = await response.json().catch(() => ({ detail: 'Failed to create advanced session' }));
            showError(error.detail || 'Failed to create advanced session');
        }
    } catch (error) {
        console.error('Error creating advanced session:', error);
        showError('Failed to create advanced session');
    }
});

// View Session Details
async function viewDetails(sessionId, type) {
    const endpoint = type === 'advanced' ? `/api/v2/sessions/${sessionId}` : `/api/sessions/${sessionId}`;

    try {
        const response = await fetch(`${API_BASE}${endpoint}`);
        const session = await response.json();

        document.getElementById('details-title').textContent = `Session: ${session.name}`;
        document.getElementById('details-content').innerHTML = `
            <div class="session-info">
                <div class="info-row"><span class="info-label">ID:</span><span class="info-value">${session.id}</span></div>
                <div class="info-row"><span class="info-label">Status:</span><span class="info-value">${session.status}</span></div>
                <div class="info-row"><span class="info-label">Created:</span><span class="info-value">${new Date(session.created).toLocaleString()}</span></div>
                ${session.mode ? `<div class="info-row"><span class="info-label">Mode:</span><span class="info-value">${session.mode}</span></div>` : ''}
                ${JSON.stringify(session, null, 2)}
            </div>
        `;

        document.getElementById('details-modal').style.display = 'block';
    } catch (error) {
        console.error('Error loading details:', error);
        showError('Failed to load session details');
    }
}

// View ManifestWork Details
async function viewManifestWorkDetails(name) {
    try {
        // For now, we'll show a simple details view since we don't have a detailed API endpoint
        document.getElementById('details-title').textContent = `ManifestWork: ${name}`;
        document.getElementById('details-content').innerHTML = `
            <div class="session-info">
                <div class="info-row"><span class="info-label">Name:</span><span class="info-value">${name}</span></div>
                <div class="info-row"><span class="info-label">Type:</span><span class="info-value">ManifestWork</span></div>
                <p>This ManifestWork manages the deployment of CAI jobs to managed clusters.</p>
                <p>For detailed status information, check the Kubernetes cluster directly.</p>
            </div>
        `;

        document.getElementById('details-modal').style.display = 'block';
    } catch (error) {
        console.error('Error showing ManifestWork details:', error);
        showError('Failed to show ManifestWork details');
    }
}

// View Job Details
async function viewJobDetails(name) {
    try {
        // For now, we'll show a simple details view since we don't have a detailed API endpoint
        document.getElementById('details-title').textContent = `Job: ${name}`;
        document.getElementById('details-content').innerHTML = `
            <div class="session-info">
                <div class="info-row"><span class="info-label">Name:</span><span class="info-value">${name}</span></div>
                <div class="info-row"><span class="info-label">Type:</span><span class="info-value">Kubernetes Job</span></div>
                <p>This job executes CAI tasks in the cluster.</p>
                <p>For detailed logs and status, check the job in the Kubernetes dashboard.</p>
            </div>
        `;

        document.getElementById('details-modal').style.display = 'block';
    } catch (error) {
        console.error('Error showing job details:', error);
        showError('Failed to show job details');
    }
}

// View Logs Enhanced with real-time updates
async function viewLogsEnhanced(sessionId, isAdvanced = false) {
    const endpoint = isAdvanced ? `/api/v2/sessions/${sessionId}/logs` : `/api/sessions/${sessionId}/logs`;

    document.getElementById('details-title').textContent = 'Session Logs (Live)';
    document.getElementById('details-content').innerHTML = `
        <div class="logs-container" id="live-logs">
            <div class="loading">Loading logs...</div>
        </div>
        <div style="margin-top: 10px;">
            <button class="btn btn-secondary btn-small" onclick="refreshLogs('${sessionId}', ${isAdvanced})">Refresh</button>
            <button class="btn btn-secondary btn-small" id="auto-refresh-btn" onclick="toggleAutoRefresh('${sessionId}', ${isAdvanced}, this)">Auto-refresh: OFF</button>
        </div>
    `;
    document.getElementById('details-modal').style.display = 'block';

    await refreshLogs(sessionId, isAdvanced);
}

// View Logs
async function viewLogs(sessionId) {
    await viewLogsEnhanced(sessionId, false);
}

// Refresh logs function
async function refreshLogs(sessionId, isAdvanced) {
    try {
        const endpoint = isAdvanced ? `/api/v2/sessions/${sessionId}/logs` : `/api/sessions/${sessionId}/logs`;
        const response = await fetch(`${API_BASE}${endpoint}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        const logsContainer = document.getElementById('live-logs');
        if (data.logs) {
            logsContainer.innerHTML = `<pre>${escapeHtml(data.logs)}</pre>`;
            logsContainer.scrollTop = logsContainer.scrollHeight;
        } else {
            logsContainer.innerHTML = '<div class="empty-state">No logs available yet</div>';
        }
    } catch (error) {
        const logsContainer = document.getElementById('live-logs');
        if (logsContainer) {
            logsContainer.innerHTML = `<div class="error">Error loading logs: ${escapeHtml(error.message)}</div>`;
        }
    }
}

// Toggle auto-refresh for logs
let logRefreshIntervals = {};

function toggleAutoRefresh(sessionId, isAdvanced, btnElement) {
    const key = `${sessionId}-${isAdvanced}`;
    if (logRefreshIntervals[key]) {
        clearInterval(logRefreshIntervals[key]);
        delete logRefreshIntervals[key];
        btnElement.textContent = 'Auto-refresh: OFF';
    } else {
        logRefreshIntervals[key] = setInterval(() => {
            refreshLogs(sessionId, isAdvanced);
        }, 3000);
        btnElement.textContent = 'Auto-refresh: ON';
    }
}

// View Result for basic sessions
async function viewResult(sessionId, type) {
    try {
        const endpoint = type === 'advanced' ? `/api/v2/sessions/${sessionId}/results` : `/api/sessions/${sessionId}/result`;
        const response = await fetch(`${API_BASE}${endpoint}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();

        document.getElementById('details-title').textContent = 'Session Result';
        document.getElementById('details-content').innerHTML = `
            <div class="result-section">
                <div class="result-summary">
                    <div><strong>Status:</strong> ${escapeHtml(result.status || 'Unknown')}</div>
                    ${result.log_path ? `<div><strong>Log Path:</strong> ${escapeHtml(result.log_path)}</div>` : ''}
                    ${result.file_size ? `<div><strong>File Size:</strong> ${result.file_size} bytes</div>` : ''}
                </div>
                ${result.pod_logs ? `
                    <div class="collapsible">
                        <div class="collapsible-header" onclick="toggleCollapsible('pod-logs')">
                            <span>Pod Logs</span>
                            <span class="toggle-icon">▼</span>
                        </div>
                        <div id="pod-logs" class="collapsible-body">
                            <pre class="logs-container">${escapeHtml(result.pod_logs)}</pre>
                        </div>
                    </div>
                ` : ''}
                ${result.file_content ? `
                    <div class="collapsible">
                        <div class="collapsible-header" onclick="toggleCollapsible('file-content')">
                            <span>File Content</span>
                            <span class="toggle-icon">▼</span>
                        </div>
                        <div id="file-content" class="collapsible-body">
                            <pre class="logs-container">${escapeHtml(result.file_content)}</pre>
                        </div>
                    </div>
                ` : ''}
            </div>
        `;

        document.getElementById('details-modal').style.display = 'block';
    } catch (error) {
        console.error('Error loading result:', error);
        showError(`Failed to load result: ${error.message}`);
    }
}

// View Results
async function viewResults(sessionId) {
    try {
        // Try v2 endpoint first, fallback to webhook result endpoint if 404
        // let response = await fetch(`${API_BASE}/api/v2/sessions/${sessionId}/results`);
        // Use standard webhook result endpoint which now handles JSONL parsing
        let response = await fetch(`${API_BASE}/api/webhooks/result/${sessionId}`);
        let results;
        let isWebhook = false;

        if (response.ok) {
            results = await response.json();
            isWebhook = true;
        } else {
            // Fallback to legacy
            response = await fetch(`${API_BASE}/api/sessions/${sessionId}/result`);
            if (response.ok) {
                results = await response.json();
                isWebhook = false;
            } else {
                throw new Error('Failed to fetch results from any endpoint');
            }
        }

        window.lastResults = results;
        document.getElementById('details-title').textContent = 'Session Results';
        let html = renderResults(results);
        // If this is a webhook result, add a button to show raw JSON
        if (isWebhook) {
            html += `<div style="margin-top:1em;"><button class="btn btn-secondary btn-small" onclick="viewWebhookRawResult('${sessionId}')">Show Raw Webhook JSON</button></div>`;
        }
        document.getElementById('details-content').innerHTML = html;
        document.getElementById('details-modal').style.display = 'block';
    } catch (error) {
        console.error('Error loading results:', error);
        showError('Failed to load results');
    }
}

// Show raw scan_report JSON in a modal
function showRawScanReport() {
    try {
        const detailsModal = document.getElementById('details-modal');
        const detailsTitle = document.getElementById('details-title');
        const detailsContent = document.getElementById('details-content');
        let scanReport = null;
        if (window.lastResults && window.lastResults.scan_report) {
            scanReport = window.lastResults.scan_report;
        }
        if (!scanReport) {
            showError('No scan report found');
            return;
        }
        detailsTitle.textContent = 'Raw Scan Report JSON';
        detailsContent.innerHTML = `
        <div style="margin-bottom:1em;"><button class="btn btn-secondary btn-small" onclick="closeDetailsModal()">Close</button></div>
        <pre style="background:#222;color:#fff;padding:1em;border-radius:6px;max-height:60vh;overflow:auto;">${escapeHtml(JSON.stringify(scanReport, null, 2))}</pre>
    `;
        detailsModal.style.display = 'block';
    } catch (e) {
        showError('Failed to show raw scan report');
    }
}

// Show raw webhook result JSON in a modal
async function viewWebhookRawResult(sessionId) {
    try {
        const response = await fetch(`${API_BASE}/api/webhooks/result/${sessionId}?raw_file=true`);
        const data = await response.json();
        document.getElementById('details-title').textContent = 'Raw Webhook Result JSON';
        document.getElementById('details-content').innerHTML = `
        <div style="margin-bottom:1em;"><button class="btn btn-secondary btn-small" onclick="closeDetailsModal()">Close</button></div>
        <pre style="background:#222;color:#fff;padding:1em;border-radius:6px;max-height:60vh;overflow:auto;">${escapeHtml(JSON.stringify(data, null, 2))}</pre>
    `;
        document.getElementById('details-modal').style.display = 'block';
    } catch (error) {
        console.error('Error loading raw webhook result:', error);
        showError('Failed to load raw webhook result');
    }
}

// Render results with sections and collapsible outputs
function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function renderResults(results) {
    const status = results.status || 'Completed';
    const flags = results.flags_found || [];
    const vulns = results.vulnerabilities || [];
    const outputs = results.outputs || {};

    // Webhook scan fields
    const repository = results.repository;
    const scan_summary = results.scan_summary;
    const files = results.files;
    const security_analysis = results.security_analysis;
    const recommendations = results.recommendations;

    let html = `<div class="result-section"><div class="result-summary">
        <div><strong>Status:</strong> ${escapeHtml(status)}</div>
        <div><strong>Flags:</strong> ${flags.length}</div>
        <div><strong>Vulnerabilities:</strong> ${vulns.length}</div>
        ${results.progress ? `<div><strong>Jobs:</strong> ${results.progress.completed_jobs}/${results.progress.total_jobs}</div>` : ''}
    </div></div>`;


    // If scan_report is present, render a parsed summary and a button for raw JSON
    if (results.scan_report) {
        const sr = results.scan_report;
        html += `<div class="result-section"><h3>Scan Report</h3>`;
        html += `<div><strong>Image:</strong> ${escapeHtml(sr.image || '')}</div>`;
        html += `<div><strong>Scan Date:</strong> ${escapeHtml(sr.scan_date || '')}</div>`;
        html += `<div><strong>Risk Level:</strong> ${escapeHtml(sr.risk_level || '')}</div>`;
        html += `<div><strong>Summary:</strong> ${escapeHtml(sr.summary || '')}</div>`;
        if (sr.repository_info) {
            html += `<div><strong>Repository:</strong> ${escapeHtml(sr.repository_info.owner || '')}/${escapeHtml(sr.repository_info.name || '')}</div>`;
            html += `<div><strong>Status:</strong> ${escapeHtml(sr.repository_info.status || '')}</div>`;
            html += `<div><strong>Pull Count:</strong> ${escapeHtml(String(sr.repository_info.pull_count || ''))}</div>`;
            html += `<div><strong>Last Updated:</strong> ${escapeHtml(sr.repository_info.last_updated || '')}</div>`;
            html += `<div><strong>Storage Size:</strong> ${escapeHtml(sr.repository_info.storage_size_human || '')}</div>`;
        }
        if (Array.isArray(sr.available_tags) && sr.available_tags.length) {
            html += `<div><strong>Available Tags:</strong><ul class="result-list">`;
            sr.available_tags.forEach(tag => {
                html += `<li><strong>${escapeHtml(tag.name)}</strong> (${escapeHtml(tag.size_human || '')}, ${escapeHtml(tag.digest || '')})${tag.is_latest ? ' <span class="status-badge status-success">latest</span>' : ''}</li>`;
            });
            html += `</ul></div>`;
        }
        if (Array.isArray(sr.security_findings) && sr.security_findings.length) {
            html += `<div><strong>Security Findings:</strong><ul class="result-list">`;
            sr.security_findings.forEach(f => {
                html += `<li><strong>[${escapeHtml(f.severity)}]</strong> ${escapeHtml(f.title)}<br><em>${escapeHtml(f.description)}</em><br><small>Impact: ${escapeHtml(f.impact)}</small></li>`;
            });
            html += `</ul></div>`;
        }
        if (sr.user_context) {
            html += `<div><strong>User Context:</strong> ${escapeHtml(sr.user_context.username || '')}, Total Repos: ${escapeHtml(String(sr.user_context.total_repositories || ''))}, Repos w/o Descriptions: ${escapeHtml(sr.user_context.repositories_without_descriptions || '')}</div>`;
        }
        if (sr.limitations) {
            html += `<div><strong>Limitations:</strong> ${escapeHtml(JSON.stringify(sr.limitations, null, 2))}</div>`;
        }
        if (Array.isArray(sr.recommendations) && sr.recommendations.length) {
            html += `<div><strong>Recommendations:</strong><ul class="result-list">`;
            sr.recommendations.forEach(r => {
                html += `<li>${escapeHtml(r)}</li>`;
            });
            html += `</ul></div>`;
        }
        if (Array.isArray(sr.next_steps) && sr.next_steps.length) {
            html += `<div><strong>Next Steps:</strong><ul class="result-list">`;
            sr.next_steps.forEach(n => {
                html += `<li>${escapeHtml(n)}</li>`;
            });
            html += `</ul></div>`;
        }
        if (Array.isArray(sr.scan_methodology) && sr.scan_methodology.length) {
            html += `<div><strong>Scan Methodology:</strong><ul class="result-list">`;
            sr.scan_methodology.forEach(m => {
                html += `<li>${escapeHtml(m)}</li>`;
            });
            html += `</ul></div>`;
        }
        html += `</div>`;
        // Add a button to show raw JSON for scan_report
        html += `<div style=\"margin-top:1em;\"><button class=\"btn btn-secondary btn-small\" onclick=\"showRawScanReport()\">Show Raw Scan Report JSON</button></div>`;
    }

    // Show scan fields if present (legacy fields)
    if (repository) {
        html += `<div class=\"result-section\"><strong>Repository:</strong> <a href=\"${escapeHtml(repository)}\" target=\"_blank\">${escapeHtml(repository)}</a></div>`;
    }
    if (scan_summary) {
        html += `<div class=\"result-section\"><h3>Scan Summary</h3><pre>${escapeHtml(JSON.stringify(scan_summary, null, 2))}</pre></div>`;
    }
    if (Array.isArray(files) && files.length) {
        html += `<div class=\"result-section\"><h3>Files</h3><ul class=\"result-list\">`;
        files.forEach(f => {
            html += `<li><strong>${escapeHtml(f.path || '')}</strong> (${f.size || '?'} bytes, ${f.lines || '?'} lines)
                ${f.content_preview ? `<details><summary>Preview</summary><pre>${escapeHtml(f.content_preview)}</pre></details>` : ''}
            </li>`;
        });
        html += `</ul></div>`;
    }
    if (security_analysis) {
        html += `<div class=\"result-section\"><h3>Security Analysis</h3><pre>${escapeHtml(JSON.stringify(security_analysis, null, 2))}</pre></div>`;
    }
    if (Array.isArray(recommendations) && recommendations.length) {
        html += `<div class=\"result-section\"><h3>Recommendations</h3><ul class=\"result-list\">`;
        recommendations.forEach(r => {
            html += `<li>${escapeHtml(r)}</li>`;
        });
        html += `</ul></div>`;
    }

    if (flags.length) {
        // Extract clean flag tokens like flag{...}
        const tokenRegex = /(flag\{[^}]*\}|FLAG\{[^}]*\}|ctf\{[^}]*\}|CTF\{[^}]*\})/g;
        const displayFlags = flags.map(f => {
            const matches = String(f).match(tokenRegex);
            return matches && matches.length ? matches[0] : String(f).slice(0, 200);
        });

        html += `
        <div class="result-section">
            <h3>Flags Found</h3>
            <div class="flag-list">
                ${displayFlags.map(f => `
                    <span class="flag-chip">${escapeHtml(f)}
                        <button class="chip-copy" onclick="copyToClipboard('${escapeHtml(f)}')">Copy</button>
                    </span>
                `).join('')}
            </div>
            <div class="collapsible">
                <div class="collapsible-header" onclick="toggleCollapsible('raw-flags')">
                    <span>Show raw flag lines</span>
                    <span class="toggle-icon">▼</span>
                </div>
                <div id="raw-flags" class="collapsible-body">
                    <pre class="logs-container">${escapeHtml(flags.join('\n\n'))}</pre>
                </div>
            </div>
        </div>`;
    }

    if (vulns.length) {
        html += `
        <div class="result-section">
            <h3>Vulnerabilities</h3>
            <ul class="result-list">
                ${vulns.map(v => {
            if (typeof v === 'object' && v !== null) {
                const title = v.title || v.name || 'Unknown Vulnerability';
                const severity = v.severity || 'Unknown';
                const desc = v.description || JSON.stringify(v);
                return `<li><strong>[${escapeHtml(severity)}] ${escapeHtml(title)}</strong><br>${escapeHtml(desc)}</li>`;
            }
            return `<li>${escapeHtml(v)}</li>`;
        }).join('')}
            </ul>
        </div>`;
    }

    const agentKeys = Object.keys(outputs);
    if (agentKeys.length) {
        html += `<div class="result-section"><h3>Agent Outputs</h3>`;
        agentKeys.forEach(agent => {
            const rawOutput = outputs[agent] || '';
            const safeAgentName = agent ? agent.replace(/_/g, ' ') : 'unknown';
            const escapedOutput = escapeHtml(rawOutput);
            const bodyId = `out-${(agent || 'unknown').replace(/[^a-zA-Z0-9_-]/g, '-')}`;
            html += `
            <div class="collapsible">
                <div class="collapsible-header" onclick="toggleCollapsible('${bodyId}')">
                    <span class="agent-name">${escapeHtml(safeAgentName)}</span>
                    <span class="toggle-icon">▼</span>
                </div>
                <div id="${bodyId}" class="collapsible-body">
                    <div class="collapsible-actions">
                        <button class="btn btn-secondary btn-small" onclick="copyToClipboard(${JSON.stringify(rawOutput)})">Copy Output</button>
                    </div>
                    <pre class="logs-container">${escapedOutput}</pre>
                </div>
            </div>`;
        });
        html += `</div>`;
    }

    if (!flags.length && !vulns.length && agentKeys.length === 0 && !results.scan_report && !scan_summary) {
        html += `<div class="empty-state"><h3>No results yet</h3><p>Try again when jobs complete.</p></div>`;
    }

    return html;
}

function toggleCollapsible(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.style.display = (el.style.display === 'none' || !el.style.display) ? 'block' : 'none';
}

function copyToClipboard(text) {
    try {
        navigator.clipboard.writeText(text);
        alert('Copied to clipboard');
    } catch (e) {
        console.error('Copy failed', e);
    }
}

// Delete Session (basic or advanced)
async function deleteSession(sessionId, type) {
    if (!confirm('Delete this session?')) return;

    const endpoint = type === 'advanced' ? `/api/v2/sessions/${sessionId}` : `/api/sessions/${sessionId}`;

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, { method: 'DELETE' });
        if (response.ok) {
            showSuccess('Session deleted successfully');
            refreshAll();
        } else {
            const error = await response.json().catch(() => ({ detail: 'Failed to delete session' }));
            showError(error.detail || 'Failed to delete session');
        }
    } catch (error) {
        console.error('Error deleting session:', error);
        showError('Failed to delete session');
    }
}

function closeDetailsModal() {
    document.getElementById('details-modal').style.display = 'none';
}

// Utility Functions
function showError(message) {
    showToast(message, 'error');
}

function showSuccess(message) {
    showToast(message, 'success');
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function refreshAll() {
    const activeTab = document.querySelector('.tab-btn.active');
    if (activeTab.textContent.includes('Sessions') && !activeTab.textContent.includes('Advanced')) {
        loadSessions();
    } else if (activeTab.textContent.includes('Advanced')) {
        loadAdvancedSessions();
    } else if (activeTab.textContent.includes('ManifestWorks')) {
        loadManifestWorks();
    } else if (activeTab.textContent.includes('Jobs')) {
        loadJobs();
    } else if (activeTab.textContent.includes('Agents')) {
        loadAgents();
    }
}

// Auto-refresh: only when window has focus and relevant tab is active.
// Reduced frequency to 60s to avoid frequent /api/sessions calls.
setInterval(() => {
    if (!document.hasFocus()) return; // don't poll when user is not looking
    const activeTab = document.querySelector('.tab-btn.active');
    if (!activeTab) return;
    if (activeTab.textContent.includes('Sessions')) {
        loadSessions();
    } else if (activeTab.textContent.includes('Advanced')) {
        loadAdvancedSessions();
    }
}, 600000);

// Initial Load
loadSessions();
console.log('CAI Job Manager UI loaded successfully');

// Get API_BASE from injected global variable, fallback to .env via server-side template, else use window location
const API_BASE = window.API_BASE || document.body.getAttribute('data-api-base') || `${window.location.origin}`;

// Tab Management
function showTab(tabName, el) {
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    document.getElementById(`${tabName}-tab`).classList.add('active');
    if (el) el.classList.add('active');

    if (tabName === 'sessions') loadSessions();
    if (tabName === 'advanced') loadAdvancedSessions();
    if (tabName === 'agents') loadAgents();
}

// Load Sessions
async function loadSessions() {
    try {
        const response = await fetch(`${API_BASE}/api/sessions`);
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
                    <button class="btn btn-primary btn-small" onclick="viewDetails('${session.id}', 'basic')">View Details</button>
                    <button class="btn btn-secondary btn-small" onclick="viewLogs('${session.id}')">Logs</button>
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
    try {
        const response = await fetch(`${API_BASE}/api/v2/sessions`);
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
                    </div>
                    <div class="session-actions">
                        <button class="btn btn-primary btn-small" onclick="viewDetails('${session.id}', 'advanced')">View Details</button>
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

// MCP Transport Toggle
document.getElementById('mcp-transport')?.addEventListener('change', (e) => {
    const isSSE = e.target.value === 'sse';
    document.getElementById('url-group').style.display = isSSE ? 'block' : 'none';
    document.getElementById('command-group').style.display = isSSE ? 'none' : 'block';
});

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
            closeModal();
            loadSessions();
            e.target.reset();
        } else {
            showError('Failed to create session');
        }
    } catch (error) {
        console.error('Error creating session:', error);
        showError('Failed to create session');
    }
});

// Advanced session form
document.getElementById('adv-mcp-transport')?.addEventListener('change', (e) => {
    const isSSE = e.target.value === 'sse';
    document.getElementById('adv-url-group').style.display = isSSE ? 'block' : 'none';
    document.getElementById('adv-command-group').style.display = isSSE ? 'none' : 'block';
});

document.getElementById('advanced-session-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const agentType = document.getElementById('adv-agent').value;
    const transport = document.getElementById('adv-mcp-transport').value;

    const payload = {
        name: document.getElementById('adv-name').value,
        prompt: document.getElementById('adv-prompt').value,
        agent_type: agentType,
        model: document.getElementById('adv-model').value,
    };

    const mcpName = document.getElementById('adv-mcp-name').value.trim();
    const allowInsecure = document.getElementById('adv-mcp-insecure').checked;
    const mcpServer = {
        name: mcpName || agentType,
        transport,
        allow_insecure: allowInsecure,
    };

    if (transport === 'sse') {
        mcpServer.url = document.getElementById('adv-mcp-url').value.trim();
    } else {
        mcpServer.command = document.getElementById('adv-mcp-command').value.trim();
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
            closeAdvancedModal();
            loadAdvancedSessions();
            e.target.reset();
        } else {
            showError('Failed to create advanced session');
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

// View Logs
async function viewLogs(sessionId) {
    try {
        const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/logs`);
        const data = await response.json();

        document.getElementById('details-title').textContent = 'Session Logs';
        document.getElementById('details-content').innerHTML = `
            <div class="logs-container">${data.logs || 'No logs available'}</div>
        `;

        document.getElementById('details-modal').style.display = 'block';
    } catch (error) {
        console.error('Error loading logs:', error);
        showError('Failed to load logs');
    }
}

// View Results
async function viewResults(sessionId) {
    try {
        // Try v2 endpoint first, fallback to webhook result endpoint if 404
        let response = await fetch(`${API_BASE}/api/v2/sessions/${sessionId}/results`);
        let results;
        if (response.status === 404) {
            response = await fetch(`${API_BASE}/api/webhooks/result/${sessionId}`);
        }
        results = await response.json();

        document.getElementById('details-title').textContent = 'Session Results';
        document.getElementById('details-content').innerHTML = renderResults(results);

        document.getElementById('details-modal').style.display = 'block';
    } catch (error) {
        console.error('Error loading results:', error);
        showError('Failed to load results');
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

    // Show scan fields if present
    if (repository) {
        html += `<div class="result-section"><strong>Repository:</strong> <a href="${escapeHtml(repository)}" target="_blank">${escapeHtml(repository)}</a></div>`;
    }
    if (scan_summary) {
        html += `<div class="result-section"><h3>Scan Summary</h3><pre>${escapeHtml(JSON.stringify(scan_summary, null, 2))}</pre></div>`;
    }
    if (Array.isArray(files) && files.length) {
        html += `<div class="result-section"><h3>Files</h3><ul class="result-list">`;
        files.forEach(f => {
            html += `<li><strong>${escapeHtml(f.path || '')}</strong> (${f.size || '?'} bytes, ${f.lines || '?'} lines)
                ${f.content_preview ? `<details><summary>Preview</summary><pre>${escapeHtml(f.content_preview)}</pre></details>` : ''}
            </li>`;
        });
        html += `</ul></div>`;
    }
    if (security_analysis) {
        html += `<div class="result-section"><h3>Security Analysis</h3><pre>${escapeHtml(JSON.stringify(security_analysis, null, 2))}</pre></div>`;
    }
    if (Array.isArray(recommendations) && recommendations.length) {
        html += `<div class="result-section"><h3>Recommendations</h3><ul class="result-list">`;
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
                ${vulns.map(v => `<li>${escapeHtml(v)}</li>`).join('')}
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

    if (!flags.length && !vulns.length && agentKeys.length === 0) {
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
            refreshAll();
        } else {
            showError('Failed to delete session');
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
    alert(message); // Simple for now, can be improved with toast notifications
}

function refreshAll() {
    const activeTab = document.querySelector('.tab-btn.active');
    if (activeTab.textContent.includes('Sessions')) {
        loadSessions();
    } else if (activeTab.textContent.includes('Advanced')) {
        loadAdvancedSessions();
    } else if (activeTab.textContent.includes('Agents')) {
        loadAgents();
    }
}

// Auto-refresh every 10 seconds
setInterval(() => {
    const activeTab = document.querySelector('.tab-btn.active');
    if (activeTab.textContent.includes('Sessions')) {
        loadSessions();
    } else if (activeTab.textContent.includes('Advanced')) {
        loadAdvancedSessions();
    }
}, 10000);

// Initial Load
loadSessions();

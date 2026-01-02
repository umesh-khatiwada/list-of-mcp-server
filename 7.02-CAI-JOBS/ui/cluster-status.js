
// Cluster Status
async function loadClusterStatus() {
    const container = document.getElementById('cluster-grid');
    if (!container) return; // Guard clause if element doesn't exist

    try {
        const response = await fetch(`${API_BASE}/api/monitoring/clusters`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        const clusters = data.clusters || {};
        const serverTime = new Date(data.server_time || new Date());
        const clusterNames = Object.keys(clusters);

        if (clusterNames.length === 0) {
            container.innerHTML = `
                <div class="cluster-card" style="grid-column: 1/-1; text-align: center;">
                    <div class="cluster-name">No Clusters Monitored</div>
                    <p style="color: var(--text-secondary);">Deploy the monitoring agent to spoke clusters to see them here.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = clusterNames.map(name => {
            const metrics = clusters[name];
            const lastUpdated = new Date(metrics.last_updated);
            const diffSeconds = (serverTime - lastUpdated) / 1000;
            const isOnline = diffSeconds < 600; // Consider online if updated in last 10 minutes

            const cpu = metrics.cpu_usage || 0;
            const mem = metrics.memory_usage || 0;

            let timeAgoText = '';
            if (diffSeconds < 60) {
                timeAgoText = 'Just now';
            } else if (diffSeconds < 3600) {
                timeAgoText = `${Math.floor(diffSeconds / 60)}m ago`;
            } else {
                timeAgoText = `${Math.floor(diffSeconds / 3600)}h ago`;
            }

            return `
                <div class="cluster-card" style="border-left: 4px solid ${isOnline ? 'var(--success-color)' : 'var(--danger-color)'}">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div class="cluster-name">${name}</div>
                        <span class="status-badge ${isOnline ? 'status-completed' : 'status-failed'}">
                            ${isOnline ? 'ONLINE' : 'OFFLINE'}
                        </span>
                    </div>
                    
                    <div class="metric-row" style="margin-top: 1rem;">
                        <span>CPU Usage</span>
                        <span class="metric-value">${cpu.toFixed(1)}%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill ${cpu > 80 ? 'high' : ''}" style="width: ${Math.min(cpu, 100)}%"></div>
                    </div>

                    <div class="metric-row" style="margin-top: 0.75rem;">
                        <span>Memory Usage</span>
                        <span class="metric-value">${mem.toFixed(1)}%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill ${mem > 80 ? 'high' : ''}" style="width: ${Math.min(mem, 100)}%"></div>
                    </div>
                    
                    <div style="margin-top: 1rem; font-size: 0.8rem; color: var(--text-secondary); text-align: right;">
                        Last updated: ${timeAgoText} (${lastUpdated.toLocaleTimeString()})
                    </div>
                </div>
            `;
        }).join('');

    } catch (error) {
        console.error('Error loading cluster status:', error);
        container.innerHTML = `<div class="error">Failed to load cluster status: ${error.message}</div>`;
    }
}

// Add refresh button listener
document.getElementById('refresh-btn')?.addEventListener('click', () => {
    loadClusterStatus();
    loadSessions();
    // Refresh other tabs as well if needed
});

// Auto-refresh cluster status every 30 seconds
setInterval(loadClusterStatus, 30000);

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    loadClusterStatus();
});

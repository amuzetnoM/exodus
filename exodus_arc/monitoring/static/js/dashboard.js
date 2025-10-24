// EXODUS Service Monitoring Dashboard JavaScript

class ServiceDashboard {
    constructor() {
        this.updateInterval = 30000; // 30 seconds
        this.charts = {};
        this.init();
    }

    init() {
        this.bindEvents();
        this.startUpdates();
        this.loadInitialData();
    }

    bindEvents() {
        // Refresh buttons
        document.querySelectorAll('.btn-refresh').forEach(btn => {
            btn.addEventListener('click', () => this.refreshData());
        });

        // Debug tool buttons
        document.getElementById('run-health-check')?.addEventListener('click', () => this.runHealthCheck());
        document.getElementById('clear-alerts')?.addEventListener('click', () => this.clearAlerts());
        document.getElementById('export-logs')?.addEventListener('click', () => this.exportLogs());
    }

    async loadInitialData() {
        await Promise.all([
            this.updateHealthStatus(),
            this.updateMetrics(),
            this.updateAlerts(),
            this.updateActivity(),
            this.updateSystemStats()
        ]);
    }

    startUpdates() {
        setInterval(() => {
            this.updateHealthStatus();
            this.updateMetrics();
            this.updateAlerts();
            this.updateSystemStats();
        }, this.updateInterval);
    }

    async updateHealthStatus() {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();

            // Update component statuses
            const componentsContainer = document.getElementById('component-status');
            componentsContainer.innerHTML = '';

            Object.entries(data.components).forEach(([component, status]) => {
                const statusClass = status.healthy ? 'status-healthy' : 'status-error';
                const statusText = status.healthy ? 'Healthy' : 'Error';

                const componentItem = document.createElement('div');
                componentItem.className = 'component-status-item';
                componentItem.innerHTML = `
                    <div>
                        <span class="status-indicator ${statusClass}"></span>
                        ${component}
                    </div>
                    <div>
                        <small class="text-muted">${statusText}</small>
                    </div>
                `;
                componentsContainer.appendChild(componentItem);
            });

            // Update overall health
            const overallHealth = document.getElementById('overall-health');
            const isHealthy = Object.values(data.components).every(c => c.healthy);
            overallHealth.className = `metric-card ${isHealthy ? 'bg-success' : 'bg-danger'}`;
            overallHealth.querySelector('h3').textContent = isHealthy ? 'Healthy' : 'Issues';

        } catch (error) {
            console.error('Failed to update health status:', error);
        }
    }

    async updateMetrics() {
        try {
            const response = await fetch('/api/metrics');
            const data = await response.json();

            // Update key metrics
            document.getElementById('total-orders').textContent = data.total_orders || 0;
            document.getElementById('active-positions').textContent = data.active_positions || 0;
            document.getElementById('total-pnl').textContent = `$${data.total_pnl?.toFixed(2) || '0.00'}`;
            document.getElementById('success-rate').textContent = `${data.success_rate?.toFixed(1) || '0.0'}%`;

            // Update strategy metrics
            const strategyMetrics = document.getElementById('strategy-metrics');
            strategyMetrics.innerHTML = '';

            if (data.strategy_metrics) {
                Object.entries(data.strategy_metrics).forEach(([strategy, metrics]) => {
                    const metricDiv = document.createElement('div');
                    metricDiv.className = 'strategy-metric';
                    metricDiv.innerHTML = `
                        <h3>${strategy}</h3>
                        <p>Win Rate: ${metrics.win_rate?.toFixed(1) || 0}%</p>
                        <small>Avg P&L: $${metrics.avg_pnl?.toFixed(2) || '0.00'}</small>
                    `;
                    strategyMetrics.appendChild(metricDiv);
                });
            }

        } catch (error) {
            console.error('Failed to update metrics:', error);
        }
    }

    async updateAlerts() {
        try {
            const response = await fetch('/api/alerts');
            const alerts = await response.json();

            const alertsContainer = document.getElementById('alerts-list');
            alertsContainer.innerHTML = '';

            if (alerts.length === 0) {
                alertsContainer.innerHTML = '<p class="text-muted">No active alerts</p>';
                return;
            }

            alerts.forEach(alert => {
                const alertDiv = document.createElement('div');
                alertDiv.className = `alert-item alert-${alert.level.toLowerCase()}`;
                alertDiv.innerHTML = `
                    <strong>${alert.title}</strong>
                    <p class="mb-1">${alert.message}</p>
                    <small class="text-muted">${new Date(alert.timestamp).toLocaleString()}</small>
                `;
                alertsContainer.appendChild(alertDiv);
            });

        } catch (error) {
            console.error('Failed to update alerts:', error);
        }
    }

    async updateActivity() {
        try {
            const response = await fetch('/api/activity?limit=10');
            const activities = await response.json();

            const activityContainer = document.getElementById('recent-activity');
            activityContainer.innerHTML = '';

            activities.forEach(activity => {
                const activityDiv = document.createElement('div');
                activityDiv.className = 'activity-item';
                activityDiv.innerHTML = `
                    <div>${activity.description}</div>
                    <div class="activity-timestamp">${new Date(activity.timestamp).toLocaleString()}</div>
                `;
                activityContainer.appendChild(activityDiv);
            });

        } catch (error) {
            console.error('Failed to update activity:', error);
        }
    }

    async updateSystemStats() {
        try {
            const response = await fetch('/api/system/stats');
            const stats = await response.json();

            // Update CPU usage
            const cpuProgress = document.getElementById('cpu-usage');
            cpuProgress.style.width = `${stats.cpu_percent || 0}%`;
            cpuProgress.setAttribute('aria-valuenow', stats.cpu_percent || 0);

            // Update memory usage
            const memoryProgress = document.getElementById('memory-usage');
            memoryProgress.style.width = `${stats.memory_percent || 0}%`;
            memoryProgress.setAttribute('aria-valuenow', stats.memory_percent || 0);

            // Update disk usage
            const diskProgress = document.getElementById('disk-usage');
            diskProgress.style.width = `${stats.disk_percent || 0}%`;
            diskProgress.setAttribute('aria-valuenow', stats.disk_percent || 0);

            // Update uptime
            document.getElementById('system-uptime').textContent = this.formatUptime(stats.uptime || 0);

        } catch (error) {
            console.error('Failed to update system stats:', error);
        }
    }

    async runHealthCheck() {
        try {
            const response = await fetch('/api/health/check', { method: 'POST' });
            const result = await response.json();

            alert(`Health check completed. Status: ${result.status}`);
            this.updateHealthStatus();

        } catch (error) {
            console.error('Health check failed:', error);
            alert('Health check failed');
        }
    }

    async clearAlerts() {
        if (!confirm('Are you sure you want to clear all alerts?')) return;

        try {
            await fetch('/api/alerts', { method: 'DELETE' });
            this.updateAlerts();
            alert('Alerts cleared successfully');

        } catch (error) {
            console.error('Failed to clear alerts:', error);
            alert('Failed to clear alerts');
        }
    }

    async exportLogs() {
        try {
            const response = await fetch('/api/logs/export');
            const blob = await response.blob();

            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `exodus_logs_${new Date().toISOString().split('T')[0]}.zip`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

        } catch (error) {
            console.error('Failed to export logs:', error);
            alert('Failed to export logs');
        }
    }

    async refreshData() {
        await this.loadInitialData();
    }

    formatUptime(seconds) {
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);

        if (days > 0) {
            return `${days}d ${hours}h ${minutes}m`;
        } else if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else {
            return `${minutes}m`;
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ServiceDashboard();
});

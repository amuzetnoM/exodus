// EXODUS Trading Dashboard JavaScript

class TradingDashboard {
    constructor() {
        this.updateInterval = 10000; // 10 seconds for trading data
        this.charts = {};
        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeCharts();
        this.startUpdates();
        this.loadInitialData();
    }

    bindEvents() {
        // Refresh buttons
        document.querySelectorAll('.btn-refresh').forEach(btn => {
            btn.addEventListener('click', () => this.refreshData());
        });

        // Position action buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('btn-close-position')) {
                this.closePosition(e.target.dataset.positionId);
            }
        });

        // Strategy control buttons
        document.getElementById('pause-strategy')?.addEventListener('click', () => this.pauseStrategy());
        document.getElementById('resume-strategy')?.addEventListener('click', () => this.resumeStrategy());
    }

    initializeCharts() {
        // P&L Chart
        const pnlCtx = document.getElementById('pnl-chart');
        if (pnlCtx) {
            this.charts.pnl = new Chart(pnlCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Portfolio P&L',
                        data: [],
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: false,
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toFixed(2);
                                }
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }

        // Performance Chart
        const perfCtx = document.getElementById('performance-chart');
        if (perfCtx) {
            this.charts.performance = new Chart(perfCtx, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Daily P&L',
                        data: [],
                        backgroundColor: function(context) {
                            const value = context.parsed.y;
                            return value >= 0 ? '#28a745' : '#dc3545';
                        }
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toFixed(2);
                                }
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }

        // Risk Chart
        const riskCtx = document.getElementById('risk-chart');
        if (riskCtx) {
            this.charts.risk = new Chart(riskCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Used Margin', 'Available Margin'],
                    datasets: [{
                        data: [0, 100],
                        backgroundColor: ['#dc3545', '#28a745'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }
    }

    async loadInitialData() {
        await Promise.all([
            this.updatePortfolioMetrics(),
            this.updatePositions(),
            this.updatePerformance(),
            this.updateRiskMetrics(),
            this.updateStrategyStatus()
        ]);
    }

    startUpdates() {
        setInterval(() => {
            this.updatePortfolioMetrics();
            this.updatePositions();
            this.updatePerformance();
            this.updateRiskMetrics();
        }, this.updateInterval);
    }

    async updatePortfolioMetrics() {
        try {
            const response = await fetch('/api/trading/portfolio');
            const data = await response.json();

            // Update main metrics
            document.getElementById('total-balance').textContent = `$${data.balance?.toFixed(2) || '0.00'}`;
            document.getElementById('total-equity').textContent = `$${data.equity?.toFixed(2) || '0.00'}`;
            document.getElementById('used-margin').textContent = `$${data.margin_used?.toFixed(2) || '0.00'}`;
            document.getElementById('free-margin').textContent = `$${data.margin_free?.toFixed(2) || '0.00'}`;

            // Update P&L display
            const pnlElement = document.getElementById('total-pnl');
            const pnlValue = data.total_pnl || 0;
            pnlElement.textContent = `$${pnlValue.toFixed(2)}`;
            pnlElement.className = pnlValue >= 0 ? 'pnl-positive' : 'pnl-negative';

            // Update P&L chart
            if (this.charts.pnl && data.pnl_history) {
                this.charts.pnl.data.labels = data.pnl_history.map(d => d.timestamp);
                this.charts.pnl.data.datasets[0].data = data.pnl_history.map(d => d.value);
                this.charts.pnl.update();
            }

        } catch (error) {
            console.error('Failed to update portfolio metrics:', error);
        }
    }

    async updatePositions() {
        try {
            const response = await fetch('/api/trading/positions');
            const positions = await response.json();

            const positionsContainer = document.getElementById('positions-list');
            positionsContainer.innerHTML = '';

            if (positions.length === 0) {
                positionsContainer.innerHTML = '<p class="text-muted text-center">No open positions</p>';
                return;
            }

            positions.forEach(position => {
                const positionDiv = document.createElement('div');
                positionDiv.className = `position-card position-${position.type.toLowerCase()}`;

                const pnlClass = position.pnl >= 0 ? 'pnl-positive' : 'pnl-negative';

                positionDiv.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${position.symbol}</strong>
                            <span class="badge badge-${position.type.toLowerCase() === 'buy' ? 'success' : 'danger'} ml-2">${position.type}</span>
                        </div>
                        <div class="text-right">
                            <div class="${pnlClass}">$${position.pnl.toFixed(2)}</div>
                            <small class="text-muted">${position.size} lots</small>
                        </div>
                    </div>
                    <div class="d-flex justify-content-between align-items-center mt-2">
                        <small class="text-muted">
                            Entry: ${position.entry_price.toFixed(5)} |
                            Current: ${position.current_price.toFixed(5)}
                        </small>
                        <button class="btn btn-sm btn-outline-danger btn-close-position"
                                data-position-id="${position.id}">
                            Close
                        </button>
                    </div>
                `;

                positionsContainer.appendChild(positionDiv);
            });

        } catch (error) {
            console.error('Failed to update positions:', error);
        }
    }

    async updatePerformance() {
        try {
            const response = await fetch('/api/trading/performance');
            const data = await response.json();

            // Update performance metrics
            document.getElementById('win-rate').textContent = `${data.win_rate?.toFixed(1) || 0}%`;
            document.getElementById('avg-win').textContent = `$${data.avg_win?.toFixed(2) || '0.00'}`;
            document.getElementById('avg-loss').textContent = `$${data.avg_loss?.toFixed(2) || '0.00'}`;
            document.getElementById('profit-factor').textContent = data.profit_factor?.toFixed(2) || '0.00';

            // Update performance chart
            if (this.charts.performance && data.daily_pnl) {
                this.charts.performance.data.labels = data.daily_pnl.map(d => d.date);
                this.charts.performance.data.datasets[0].data = data.daily_pnl.map(d => d.pnl);
                this.charts.performance.update();
            }

        } catch (error) {
            console.error('Failed to update performance:', error);
        }
    }

    async updateRiskMetrics() {
        try {
            const response = await fetch('/api/trading/risk');
            const data = await response.json();

            // Update risk metrics
            document.getElementById('max-drawdown').textContent = `${data.max_drawdown?.toFixed(2) || '0.00'}%`;
            document.getElementById('current-drawdown').textContent = `${data.current_drawdown?.toFixed(2) || '0.00'}%`;
            document.getElementById('sharpe-ratio').textContent = data.sharpe_ratio?.toFixed(2) || '0.00';
            document.getElementById('var-95').textContent = `$${data.var_95?.toFixed(2) || '0.00'}`;

            // Update risk chart
            if (this.charts.risk) {
                const usedPercent = data.margin_utilization || 0;
                this.charts.risk.data.datasets[0].data = [usedPercent, 100 - usedPercent];
                this.charts.risk.update();
            }

        } catch (error) {
            console.error('Failed to update risk metrics:', error);
        }
    }

    async updateStrategyStatus() {
        try {
            const response = await fetch('/api/trading/strategy/status');
            const data = await response.json();

            const statusElement = document.getElementById('strategy-status');
            const controlBtn = document.getElementById('strategy-control-btn');

            if (data.is_active) {
                statusElement.innerHTML = '<span class="badge badge-success">Active</span>';
                controlBtn.innerHTML = '<i class="fas fa-pause"></i> Pause Strategy';
                controlBtn.className = 'btn btn-warning';
            } else {
                statusElement.innerHTML = '<span class="badge badge-secondary">Paused</span>';
                controlBtn.innerHTML = '<i class="fas fa-play"></i> Resume Strategy';
                controlBtn.className = 'btn btn-success';
            }

            // Update strategy performance
            const strategiesContainer = document.getElementById('strategy-performance');
            strategiesContainer.innerHTML = '';

            if (data.strategies) {
                Object.entries(data.strategies).forEach(([strategy, perf]) => {
                    const strategyDiv = document.createElement('div');
                    strategyDiv.className = 'strategy-performance';
                    strategyDiv.innerHTML = `
                        <h5>${strategy}</h5>
                        <div class="progress">
                            <div class="progress-bar bg-success" style="width: ${perf.win_rate || 0}%"></div>
                        </div>
                        <small class="text-muted">
                            Win Rate: ${perf.win_rate?.toFixed(1) || 0}% |
                            Total Trades: ${perf.total_trades || 0}
                        </small>
                    `;
                    strategiesContainer.appendChild(strategyDiv);
                });
            }

        } catch (error) {
            console.error('Failed to update strategy status:', error);
        }
    }

    async closePosition(positionId) {
        if (!confirm('Are you sure you want to close this position?')) return;

        try {
            const response = await fetch(`/api/trading/positions/${positionId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                alert('Position closed successfully');
                this.updatePositions();
                this.updatePortfolioMetrics();
            } else {
                alert('Failed to close position');
            }

        } catch (error) {
            console.error('Failed to close position:', error);
            alert('Failed to close position');
        }
    }

    async pauseStrategy() {
        try {
            await fetch('/api/trading/strategy/pause', { method: 'POST' });
            this.updateStrategyStatus();
        } catch (error) {
            console.error('Failed to pause strategy:', error);
        }
    }

    async resumeStrategy() {
        try {
            await fetch('/api/trading/strategy/resume', { method: 'POST' });
            this.updateStrategyStatus();
        } catch (error) {
            console.error('Failed to resume strategy:', error);
        }
    }

    async refreshData() {
        await this.loadInitialData();
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TradingDashboard();
});

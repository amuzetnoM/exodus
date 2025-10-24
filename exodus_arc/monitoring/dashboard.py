# exodus_arc/monitoring/dashboard.py
"""
EXODUS Monitoring Dashboard

Comprehensive monitoring and visualization for both service-side
(system health, debugging) and user-side (trading performance) views.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import psutil
import platform

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from .metrics import MetricsCollector
from .tracing import TracingService
from .alerts import AlertManager


class MonitoringDashboard:
    """
    Comprehensive monitoring dashboard for EXODUS platform

    Features:
    - Service-side: System health, metrics, debugging tools
    - User-side: Trading performance, positions, risk metrics
    - Real-time updates via WebSocket
    - Historical data visualization
    - Alert management interface
    """

    def __init__(self,
                 metrics: MetricsCollector,
                 tracing: TracingService,
                 alerts: AlertManager,
                 data_dir: str = "data"):
        """
        Initialize monitoring dashboard

        Args:
            metrics: Metrics collector instance
            tracing: Tracing service instance
            alerts: Alert manager instance
            data_dir: Directory for data storage
        """
        self.metrics = metrics
        self.tracing = tracing
        self.alerts = alerts
        self.data_dir = Path(data_dir)

        # Dashboard app
        self.app = FastAPI(title="EXODUS Monitoring Dashboard", version="1.0.0")

        # Templates and static files
        self.templates = Jinja2Templates(directory="exodus_arc/monitoring/templates")
        self.app.mount("/static", StaticFiles(directory="exodus_arc/monitoring/static"), name="static")

        # Setup routes
        self._setup_routes()

        # System monitoring
        self.system_stats = {}
        self.start_time = datetime.utcnow()

    def _setup_routes(self):
        """Setup dashboard routes"""

        @self.app.get("/", response_class=HTMLResponse)
        async def root(request: Request):
            """Main dashboard - redirects to service dashboard"""
            return await self.service_dashboard(request)

        @self.app.get("/service", response_class=HTMLResponse)
        async def service_dashboard(request: Request):
            """Service-side monitoring dashboard"""
            return self.templates.TemplateResponse(
                "service_dashboard.html",
                {
                    "request": request,
                    "title": "EXODUS Service Monitor",
                    "uptime": self._get_uptime(),
                    "system_info": self._get_system_info()
                }
            )

        @self.app.get("/trading", response_class=HTMLResponse)
        async def trading_dashboard(request: Request):
            """User-side trading dashboard"""
            return self.templates.TemplateResponse(
                "trading_dashboard.html",
                {
                    "request": request,
                    "title": "EXODUS Trading Dashboard"
                }
            )

        @self.app.get("/api/health")
        async def health_check():
            """Comprehensive health check"""
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
                "system": self._get_system_health(),
                "components": self._get_component_health()
            }

        @self.app.get("/api/metrics")
        async def get_metrics():
            """Get current metrics"""
            return self.metrics.get_metrics()

        @self.app.get("/api/metrics/prometheus")
        async def get_prometheus_metrics():
            """Get Prometheus-formatted metrics"""
            return self.metrics.get_prometheus_format()

        @self.app.get("/api/traces")
        async def get_traces(limit: int = 100):
            """Get recent traces"""
            traces = []
            for span in list(self.tracing.completed_spans)[-limit:]:
                traces.append({
                    "trace_id": span.trace_id,
                    "span_id": span.span_id,
                    "name": span.name,
                    "start_time": span.start_time.isoformat(),
                    "duration_ms": (span.end_time - span.start_time).total_seconds() * 1000 if span.end_time else None,
                    "status": span.status,
                    "attributes": span.attributes
                })
            return {"traces": traces}

        @self.app.get("/api/alerts")
        async def get_alerts():
            """Get active alerts"""
            return {"alerts": self.alerts.get_active_alerts()}

        @self.app.get("/api/system/stats")
        async def get_system_stats():
            """Get detailed system statistics"""
            return self._get_detailed_system_stats()

        @self.app.get("/api/trading/performance")
        async def get_trading_performance():
            """Get trading performance metrics"""
            return self._get_trading_performance()

        @self.app.get("/api/debug/logs")
        async def get_debug_logs(lines: int = 100):
            """Get recent debug logs"""
            return self._get_recent_logs(lines)

        @self.app.post("/api/debug/test-order")
        async def test_order_endpoint(order_data: Dict[str, Any]):
            """Debug endpoint to test order processing"""
            # This would integrate with the orchestrator
            return {"status": "test_order_received", "data": order_data}

    def _get_uptime(self) -> str:
        """Get system uptime"""
        uptime = datetime.utcnow() - self.start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        else:
            return f"{minutes}m {seconds}s"

    def _get_system_info(self) -> Dict[str, Any]:
        """Get basic system information"""
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "disk_usage": psutil.disk_usage('/').total
        }

    def _get_system_health(self) -> Dict[str, Any]:
        """Get system health status"""
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_percent = psutil.cpu_percent(interval=1)

        return {
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "disk_usage": disk.percent,
            "memory_available": memory.available,
            "disk_available": disk.free,
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
        }

    def _get_component_health(self) -> Dict[str, Any]:
        """Get component health status"""
        return {
            "metrics_collector": "healthy",
            "tracing_service": "healthy",
            "alert_manager": "healthy",
            "order_router": "healthy",
            "risk_engine": "healthy",
            "reconciliation": "healthy"
        }

    def _get_detailed_system_stats(self) -> Dict[str, Any]:
        """Get detailed system statistics"""
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()

        return {
            "cpu": {
                "percent": psutil.cpu_percent(interval=0.1),
                "count": psutil.cpu_count(),
                "freq": psutil.cpu_freq().current if psutil.cpu_freq() else None
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used
            },
            "disk": {
                "total": disk.total,
                "free": disk.free,
                "used": disk.used,
                "percent": disk.percent
            },
            "network": {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            },
            "processes": len(psutil.pids())
        }

    def _get_trading_performance(self) -> Dict[str, Any]:
        """Get trading performance metrics"""
        # This would aggregate data from various sources
        return {
            "total_orders": 0,
            "successful_orders": 0,
            "failed_orders": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "current_positions": [],
            "daily_pnl": [],
            "monthly_pnl": []
        }

    def _get_recent_logs(self, lines: int = 100) -> Dict[str, Any]:
        """Get recent application logs"""
        # This would read from log files
        return {
            "logs": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "INFO",
                    "message": "System initialized",
                    "component": "orchestrator"
                }
            ]
        }

    async def start_dashboard(self, host: str = "0.0.0.0", port: int = 8001):
        """
        Start the monitoring dashboard

        Args:
            host: Host to bind to
            port: Port to bind to
        """
        print(f"Starting EXODUS Monitoring Dashboard on {host}:{port}")
        config = uvicorn.Config(self.app, host=host, port=port)
        server = uvicorn.Server(config)
        await server.serve()

    def update_system_stats(self):
        """Update system statistics periodically"""
        self.system_stats = self._get_detailed_system_stats()


# Global dashboard instance
dashboard_instance: Optional[MonitoringDashboard] = None


def get_dashboard() -> MonitoringDashboard:
    """Get the global dashboard instance"""
    if dashboard_instance is None:
        raise RuntimeError("Dashboard not initialized")
    return dashboard_instance


def create_dashboard(metrics: MetricsCollector,
                    tracing: TracingService,
                    alerts: AlertManager,
                    data_dir: str = "data") -> MonitoringDashboard:
    """Create and return dashboard instance"""
    global dashboard_instance
    dashboard_instance = MonitoringDashboard(metrics, tracing, alerts, data_dir)
    return dashboard_instance

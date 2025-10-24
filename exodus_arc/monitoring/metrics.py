# exodus_arc/monitoring/metrics.py
"""
Prometheus metrics collection for EXODUS Platform

Provides comprehensive metrics for monitoring system health,
performance, and trading activity.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import time
from collections import defaultdict


@dataclass
class MetricValue:
    """Metric value with timestamp"""
    value: float
    timestamp: datetime
    labels: Dict[str, str]


class MetricsCollector:
    """
    Prometheus-style metrics collector

    Collects and exposes metrics for:
    - Order processing performance
    - Risk engine activity
    - Broker connectivity
    - Reconciliation status
    - System health
    """

    def __init__(self):
        # Core metrics storage
        self.counters: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.gauges: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.histograms: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))

        # Metric definitions
        self._setup_metrics()

    def _setup_metrics(self):
        """Setup metric definitions"""
        # Order metrics
        self.define_counter("orders_total", "Total number of orders processed")
        self.define_counter("orders_failed", "Total number of failed orders")
        self.define_gauge("orders_pending", "Number of pending orders")
        self.define_histogram("order_processing_time", "Order processing duration")

        # Risk metrics
        self.define_counter("risk_checks_total", "Total risk checks performed")
        self.define_counter("risk_violations_total", "Total risk violations")
        self.define_gauge("circuit_breaker_active", "Circuit breaker status")

        # Broker metrics
        self.define_counter("broker_requests_total", "Total broker API requests")
        self.define_counter("broker_errors_total", "Total broker API errors")
        self.define_gauge("broker_connected", "Broker connection status")
        self.define_histogram("broker_request_duration", "Broker request duration")

        # Reconciliation metrics
        self.define_counter("reconciliation_records_total", "Total reconciliation records")
        self.define_gauge("unmatched_orders", "Number of unmatched orders")
        self.define_gauge("reconciliation_discrepancy_rate", "Discrepancy rate")

        # System metrics
        self.define_gauge("system_memory_usage", "Memory usage percentage")
        self.define_gauge("system_cpu_usage", "CPU usage percentage")
        self.define_counter("system_errors_total", "Total system errors")

    def define_counter(self, name: str, description: str):
        """Define a counter metric"""
        self.counters[name] = {"value": 0.0, "description": description}

    def define_gauge(self, name: str, description: str):
        """Define a gauge metric"""
        self.gauges[name] = {"value": 0.0, "description": description}

    def define_histogram(self, name: str, description: str, buckets: list = None):
        """Define a histogram metric"""
        if buckets is None:
            buckets = [0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
        self.histograms[name] = {
            "description": description,
            "buckets": buckets,
            "counts": [0] * len(buckets),
            "sum": 0.0,
            "count": 0
        }

    def increment_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment a counter"""
        if name in self.counters:
            self.counters[name]["value"] += value
            if labels:
                self.counters[name]["labels"] = labels

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge value"""
        if name in self.gauges:
            self.gauges[name]["value"] = value
            if labels:
                self.gauges[name]["labels"] = labels

    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Observe a histogram value"""
        if name in self.histograms:
            hist = self.histograms[name]
            hist["sum"] += value
            hist["count"] += 1

            # Update buckets
            for i, bucket in enumerate(hist["buckets"]):
                if value <= bucket:
                    hist["counts"][i] += 1

            if labels:
                hist["labels"] = labels

    def record_order_processed(self, order_type: str, success: bool, duration: float):
        """Record order processing metrics"""
        self.increment_counter("orders_total", labels={"type": order_type})
        if not success:
            self.increment_counter("orders_failed", labels={"type": order_type})
        self.observe_histogram("order_processing_time", duration, {"type": order_type})

    def record_risk_check(self, check_type: str, violation: bool):
        """Record risk check metrics"""
        self.increment_counter("risk_checks_total", labels={"type": check_type})
        if violation:
            self.increment_counter("risk_violations_total", labels={"type": check_type})

    def record_broker_request(self, broker: str, method: str, success: bool, duration: float):
        """Record broker API request metrics"""
        self.increment_counter("broker_requests_total",
                             labels={"broker": broker, "method": method})
        if not success:
            self.increment_counter("broker_errors_total",
                                 labels={"broker": broker, "method": method})
        self.observe_histogram("broker_request_duration", duration,
                             {"broker": broker, "method": method})

    def update_system_metrics(self, memory_usage: float, cpu_usage: float):
        """Update system resource metrics"""
        self.set_gauge("system_memory_usage", memory_usage)
        self.set_gauge("system_cpu_usage", cpu_usage)

    def get_metrics(self) -> Dict[str, Any]:
        """Get all current metrics"""
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": dict(self.histograms),
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_prometheus_format(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []

        # Counters
        for name, data in self.counters.items():
            lines.append(f"# HELP {name} {data['description']}")
            lines.append(f"# TYPE {name} counter")
            labels = data.get("labels", {})
            if labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
                lines.append(f"{name}{{{label_str}}} {data['value']}")
            else:
                lines.append(f"{name} {data['value']}")

        # Gauges
        for name, data in self.gauges.items():
            lines.append(f"# HELP {name} {data['description']}")
            lines.append(f"# TYPE {name} gauge")
            labels = data.get("labels", {})
            if labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
                lines.append(f"{name}{{{label_str}}} {data['value']}")
            else:
                lines.append(f"{name} {data['value']}")

        # Histograms
        for name, data in self.histograms.items():
            lines.append(f"# HELP {name} {data['description']}")
            lines.append(f"# TYPE {name} histogram")

            # Sum
            lines.append(f"{name}_sum {data['sum']}")

            # Count
            lines.append(f"{name}_count {data['count']}")

            # Buckets
            for i, bucket in enumerate(data['buckets']):
                lines.append(f"{name}_bucket{{le=\"{bucket}\"}} {data['counts'][i]}")

            # +Inf bucket
            lines.append(f"{name}_bucket{{le=\"+Inf\"}} {data['count']}")

        return "\n".join(lines)

    def reset(self):
        """Reset all metrics"""
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()
        self._setup_metrics()

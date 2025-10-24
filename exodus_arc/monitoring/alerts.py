# exodus_arc/monitoring/alerts.py
"""
Alert management for EXODUS Platform

Provides alerting for critical events, performance issues,
and system anomalies.
"""

from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class Alert:
    """Alert definition"""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    status: AlertStatus
    source: str
    labels: Dict[str, str]
    annotations: Dict[str, str]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]


class AlertRule:
    """Alert rule definition"""
    def __init__(self,
                 name: str,
                 condition: Callable[[Dict[str, Any]], bool],
                 severity: AlertSeverity,
                 title: str,
                 description: str,
                 labels: Dict[str, str] = None):
        self.name = name
        self.condition = condition
        self.severity = severity
        self.title = title
        self.description = description
        self.labels = labels or {}

    def evaluate(self, metrics: Dict[str, Any]) -> Optional[Alert]:
        """
        Evaluate the alert rule

        Args:
            metrics: Current metrics

        Returns:
            Alert if condition is met, None otherwise
        """
        if self.condition(metrics):
            return Alert(
                id=f"{self.name}_{int(datetime.utcnow().timestamp())}",
                title=self.title,
                description=self.description,
                severity=self.severity,
                status=AlertStatus.ACTIVE,
                source="alert_rule",
                labels=self.labels,
                annotations={},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                resolved_at=None
            )
        return None


class AlertManager:
    """
    Alert management system

    Manages alert rules, active alerts, and alert notifications.
    """

    def __init__(self):
        self.alert_rules: List[AlertRule] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_callbacks: List[Callable[[Alert], Awaitable[None]]] = []

        self._setup_default_rules()

    def _setup_default_rules(self):
        """Setup default alert rules"""

        # High error rate alert
        self.add_rule(AlertRule(
            name="high_error_rate",
            condition=lambda m: (
                m.get("counters", {}).get("orders_failed", {}).get("value", 0) /
                max(m.get("counters", {}).get("orders_total", {}).get("value", 0), 1)
            ) > 0.1,  # 10% error rate
            severity=AlertSeverity.ERROR,
            title="High Order Failure Rate",
            description="Order failure rate exceeds 10%",
            labels={"component": "orders"}
        ))

        # Circuit breaker active
        self.add_rule(AlertRule(
            name="circuit_breaker_active",
            condition=lambda m: m.get("gauges", {}).get("circuit_breaker_active", {}).get("value", 0) > 0,
            severity=AlertSeverity.CRITICAL,
            title="Circuit Breaker Activated",
            description="Trading circuit breaker is active",
            labels={"component": "risk"}
        ))

        # Broker disconnection
        self.add_rule(AlertRule(
            name="broker_disconnected",
            condition=lambda m: m.get("gauges", {}).get("broker_connected", {}).get("value", 0) == 0,
            severity=AlertSeverity.CRITICAL,
            title="Broker Disconnected",
            description="Broker connection is down",
            labels={"component": "broker"}
        ))

        # High reconciliation discrepancy
        self.add_rule(AlertRule(
            name="high_reconciliation_discrepancy",
            condition=lambda m: m.get("gauges", {}).get("reconciliation_discrepancy_rate", {}).get("value", 0) > 0.05,
            severity=AlertSeverity.WARNING,
            title="High Reconciliation Discrepancy",
            description="Reconciliation discrepancy rate exceeds 5%",
            labels={"component": "reconciliation"}
        ))

        # System resource alert
        self.add_rule(AlertRule(
            name="high_memory_usage",
            condition=lambda m: m.get("gauges", {}).get("system_memory_usage", {}).get("value", 0) > 0.9,
            severity=AlertSeverity.WARNING,
            title="High Memory Usage",
            description="System memory usage exceeds 90%",
            labels={"component": "system"}
        ))

    def add_rule(self, rule: AlertRule):
        """
        Add an alert rule

        Args:
            rule: Alert rule to add
        """
        self.alert_rules.append(rule)

    def evaluate_rules(self, metrics: Dict[str, Any]):
        """
        Evaluate all alert rules against current metrics

        Args:
            metrics: Current metrics
        """
        for rule in self.alert_rules:
            alert = rule.evaluate(metrics)
            if alert:
                self.fire_alert(alert)

    def fire_alert(self, alert: Alert):
        """
        Fire an alert

        Args:
            alert: Alert to fire
        """
        # Check if alert is already active
        if alert.id in self.active_alerts:
            return

        self.active_alerts[alert.id] = alert
        self.alert_history.append(alert)

        # Notify subscribers
        for callback in self.notification_callbacks:
            try:
                # In real implementation, this would be async
                # For now, we'll assume synchronous callbacks
                pass
            except Exception as e:
                print(f"Alert notification error: {e}")

    def resolve_alert(self, alert_id: str):
        """
        Resolve an alert

        Args:
            alert_id: Alert ID to resolve
        """
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            alert.updated_at = datetime.utcnow()

            del self.active_alerts[alert_id]

    def acknowledge_alert(self, alert_id: str):
        """
        Acknowledge an alert

        Args:
            alert_id: Alert ID to acknowledge
        """
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].status = AlertStatus.ACKNOWLEDGED
            self.active_alerts[alert_id].updated_at = datetime.utcnow()

    def add_notification_callback(self, callback: Callable[[Alert], Awaitable[None]]):
        """
        Add notification callback

        Args:
            callback: Callback function for alert notifications
        """
        self.notification_callbacks.append(callback)

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """
        Get active alerts

        Returns:
            List of active alerts as dictionaries
        """
        return [self._alert_to_dict(alert) for alert in self.active_alerts.values()]

    def get_alert_history(self,
                         limit: int = 100,
                         severity: Optional[AlertSeverity] = None) -> List[Dict[str, Any]]:
        """
        Get alert history

        Args:
            limit: Maximum number of alerts to return
            severity: Filter by severity

        Returns:
            List of alerts as dictionaries
        """
        alerts = self.alert_history
        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        # Sort by creation time, most recent first
        alerts.sort(key=lambda a: a.created_at, reverse=True)

        return [self._alert_to_dict(alert) for alert in alerts[:limit]]

    def _alert_to_dict(self, alert: Alert) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            "id": alert.id,
            "title": alert.title,
            "description": alert.description,
            "severity": alert.severity.value,
            "status": alert.status.value,
            "source": alert.source,
            "labels": alert.labels,
            "annotations": alert.annotations,
            "created_at": alert.created_at.isoformat(),
            "updated_at": alert.updated_at.isoformat(),
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None
        }

    def get_alert_summary(self) -> Dict[str, Any]:
        """
        Get alert summary statistics

        Returns:
            Alert summary
        """
        total_alerts = len(self.alert_history)
        active_alerts = len(self.active_alerts)

        severity_counts = {}
        for severity in AlertSeverity:
            severity_counts[severity.value] = len([
                a for a in self.active_alerts.values()
                if a.severity == severity
            ])

        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "severity_breakdown": severity_counts,
            "most_recent_alert": self._alert_to_dict(self.alert_history[-1]) if self.alert_history else None
        }

    def export_alerts(self, format: str = "json") -> str:
        """
        Export alerts in specified format

        Args:
            format: Export format

        Returns:
            Exported alert data
        """
        alerts = [self._alert_to_dict(alert) for alert in self.alert_history]

        if format == "json":
            return json.dumps({
                "alerts": alerts,
                "export_time": datetime.utcnow().isoformat()
            }, indent=2)
        else:
            return json.dumps(alerts)

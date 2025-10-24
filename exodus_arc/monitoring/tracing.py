# exodus_arc/monitoring/tracing.py
"""
OpenTelemetry tracing for EXODUS Platform

Provides distributed tracing for request flows, performance monitoring,
and debugging capabilities.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import uuid
import json


@dataclass
class TraceSpan:
    """Trace span representation"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    start_time: datetime
    end_time: Optional[datetime]
    attributes: Dict[str, Any]
    events: List[Dict[str, Any]]
    status: str


class TracingService:
    """
    OpenTelemetry-style tracing service

    Provides tracing for:
    - Order lifecycle
    - Risk checks
    - Broker interactions
    - Reconciliation processes
    """

    def __init__(self):
        self.active_spans: Dict[str, TraceSpan] = {}
        self.completed_spans: List[TraceSpan] = []
        self.service_name = "exodus-trading-platform"

    def start_span(self,
                   name: str,
                   parent_span_id: Optional[str] = None,
                   attributes: Dict[str, Any] = None) -> str:
        """
        Start a new trace span

        Args:
            name: Span name
            parent_span_id: Parent span ID
            attributes: Span attributes

        Returns:
            Span ID
        """
        span_id = str(uuid.uuid4())
        trace_id = self._get_trace_id(parent_span_id)

        span = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            name=name,
            start_time=datetime.utcnow(),
            end_time=None,
            attributes=attributes or {},
            events=[],
            status="started"
        )

        self.active_spans[span_id] = span
        return span_id

    def _get_trace_id(self, parent_span_id: Optional[str]) -> str:
        """Get or create trace ID"""
        if parent_span_id and parent_span_id in self.active_spans:
            return self.active_spans[parent_span_id].trace_id
        return str(uuid.uuid4())

    def add_span_event(self, span_id: str, name: str, attributes: Dict[str, Any] = None):
        """
        Add an event to a span

        Args:
            span_id: Span ID
            name: Event name
            attributes: Event attributes
        """
        if span_id in self.active_spans:
            event = {
                "name": name,
                "timestamp": datetime.utcnow().isoformat(),
                "attributes": attributes or {}
            }
            self.active_spans[span_id].events.append(event)

    def set_span_attribute(self, span_id: str, key: str, value: Any):
        """
        Set a span attribute

        Args:
            span_id: Span ID
            key: Attribute key
            value: Attribute value
        """
        if span_id in self.active_spans:
            self.active_spans[span_id].attributes[key] = value

    def end_span(self, span_id: str, status: str = "ok"):
        """
        End a trace span

        Args:
            span_id: Span ID
            status: Span status
        """
        if span_id in self.active_spans:
            span = self.active_spans[span_id]
            span.end_time = datetime.utcnow()
            span.status = status

            # Move to completed spans
            self.completed_spans.append(span)
            del self.active_spans[span_id]

    def trace_order_lifecycle(self, order_id: str, order_data: Dict[str, Any]) -> str:
        """
        Start tracing an order lifecycle

        Args:
            order_id: Order ID
            order_data: Order data

        Returns:
            Root span ID
        """
        span_id = self.start_span(
            f"order_lifecycle_{order_id}",
            attributes={
                "order.id": order_id,
                "order.symbol": order_data.get("symbol"),
                "order.side": order_data.get("side"),
                "order.quantity": order_data.get("qty"),
                "service.name": self.service_name
            }
        )

        self.add_span_event(span_id, "order_received", {"order": order_data})
        return span_id

    def trace_risk_check(self, order_id: str, check_type: str) -> str:
        """
        Trace a risk check operation

        Args:
            order_id: Order ID
            check_type: Risk check type

        Returns:
            Span ID
        """
        span_id = self.start_span(
            f"risk_check_{check_type}",
            attributes={
                "order.id": order_id,
                "risk.check_type": check_type,
                "service.name": self.service_name
            }
        )

        return span_id

    def trace_broker_interaction(self, broker: str, method: str, order_id: Optional[str] = None) -> str:
        """
        Trace a broker API interaction

        Args:
            broker: Broker name
            method: API method
            order_id: Associated order ID

        Returns:
            Span ID
        """
        span_id = self.start_span(
            f"broker_{broker}_{method}",
            attributes={
                "broker.name": broker,
                "broker.method": method,
                "order.id": order_id,
                "service.name": self.service_name
            }
        )

        return span_id

    def trace_reconciliation(self, order_id: str, reconciliation_type: str) -> str:
        """
        Trace a reconciliation operation

        Args:
            order_id: Order ID
            reconciliation_type: Type of reconciliation

        Returns:
            Span ID
        """
        span_id = self.start_span(
            f"reconciliation_{reconciliation_type}",
            attributes={
                "order.id": order_id,
                "reconciliation.type": reconciliation_type,
                "service.name": self.service_name
            }
        )

        return span_id

    def get_active_spans(self) -> List[Dict[str, Any]]:
        """
        Get active spans

        Returns:
            List of active span dictionaries
        """
        return [self._span_to_dict(span) for span in self.active_spans.values()]

    def get_completed_spans(self,
                           limit: int = 100,
                           start_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get completed spans

        Args:
            limit: Maximum number of spans to return
            start_time: Start time filter

        Returns:
            List of completed span dictionaries
        """
        spans = self.completed_spans
        if start_time:
            spans = [s for s in spans if s.start_time >= start_time]

        # Sort by start time, most recent first
        spans.sort(key=lambda s: s.start_time, reverse=True)

        return [self._span_to_dict(span) for span in spans[:limit]]

    def get_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        """
        Get all spans for a trace

        Args:
            trace_id: Trace ID

        Returns:
            List of spans in the trace
        """
        spans = [
            span for span in self.completed_spans + list(self.active_spans.values())
            if span.trace_id == trace_id
        ]

        return [self._span_to_dict(span) for span in spans]

    def _span_to_dict(self, span: TraceSpan) -> Dict[str, Any]:
        """Convert span to dictionary"""
        duration = None
        if span.end_time:
            duration = (span.end_time - span.start_time).total_seconds()

        return {
            "trace_id": span.trace_id,
            "span_id": span.span_id,
            "parent_span_id": span.parent_span_id,
            "name": span.name,
            "start_time": span.start_time.isoformat(),
            "end_time": span.end_time.isoformat() if span.end_time else None,
            "duration": duration,
            "attributes": span.attributes,
            "events": span.events,
            "status": span.status
        }

    def export_traces(self, format: str = "json") -> str:
        """
        Export traces in specified format

        Args:
            format: Export format ("json" or "otlp")

        Returns:
            Exported trace data
        """
        spans = [self._span_to_dict(span) for span in self.completed_spans]

        if format == "json":
            return json.dumps({
                "spans": spans,
                "export_time": datetime.utcnow().isoformat()
            }, indent=2)
        else:
            # OTLP format would require additional implementation
            return json.dumps(spans)

    def cleanup_old_spans(self, max_age_hours: int = 24):
        """
        Clean up old completed spans

        Args:
            max_age_hours: Maximum age in hours
        """
        cutoff_time = datetime.utcnow().replace(hour=datetime.utcnow().hour - max_age_hours)

        self.completed_spans = [
            span for span in self.completed_spans
            if span.start_time > cutoff_time
        ]

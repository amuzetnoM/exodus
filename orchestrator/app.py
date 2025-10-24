"""EXODUS Orchestrator - Production Trading Platform

Endpoints:
- POST /api/v1/orders -> accept order, validate, route, persist events
- GET /health -> health check
- GET /metrics -> prometheus metrics
- GET /status -> system status

Integrates with Exodus ARC strategy, risk management, and broker adapters.
"""
from fastapi import FastAPI, Request, Header, HTTPException
from pydantic import BaseModel
import uvicorn
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any
import asyncio

# Import Exodus ARC components
from exodus_arc import (
    ExodusArcStrategy,
    XMMT5Adapter,
    RiskEngine,
    ReconciliationService,
    MetricsCollector,
    TracingService,
    AlertManager,
    OrderRouter,
    RoutingStrategy,
    BrokerStatus
)

app = FastAPI(title="EXODUS Orchestrator", version="1.0.0")

os.makedirs('data', exist_ok=True)

EVENTS_FILE = 'data/events.jsonl'

class OrderRequest(BaseModel):
    clientOrderId: Optional[str]
    clientId: Optional[str]
    symbol: str
    qty: int
    price: float
    side: str
    type: str = "market"  # market, limit, stop
    timeInForce: str = "day"  # day, gtc, ioc, fok


# Initialize core components
strategy = ExodusArcStrategy()
risk_engine = RiskEngine()
reconciliation = ReconciliationService()
metrics = MetricsCollector()
tracing = TracingService()
alerts = AlertManager()
order_router = OrderRouter()

# Register XM MT5 broker (only if credentials are available)
xm_adapter = None
if os.getenv('XM_API_KEY') and os.getenv('XM_API_SECRET'):
    xm_adapter = XMMT5Adapter(
        broker_url=os.getenv('XM_BROKER_URL', 'https://mt5.xmtrading.com'),
        api_key=os.getenv('XM_API_KEY'),
        api_secret=os.getenv('XM_API_SECRET'),
        account_id=os.getenv('XM_ACCOUNT_ID', 'demo-account')
    )

    order_router.register_broker(
        name="xm_mt5",
        adapter=xm_adapter,
        priority=1,
        max_concurrent=50,
        capabilities=["forex", "equities", "limit_orders", "stop_orders"]
    )
else:
    # Register mock adapter for testing
    from exodus_arc.adapters.base_adapter import BaseBrokerAdapter
    class MockAdapter(BaseBrokerAdapter):
        async def submit_order(self, order):
            return type('MockResponse', (), {'status': 'accepted', 'broker_order_id': f'mock-{order["id"]}'})()
        async def cancel_order(self, order_id):
            return True

    mock_adapter = MockAdapter("mock://test", "mock", "mock")
    order_router.register_broker(
        name="mock_broker",
        adapter=mock_adapter,
        priority=1,
        max_concurrent=100,
        capabilities=["forex", "equities", "limit_orders", "stop_orders"]
    )


def persist_event(event: dict):
    """Persist event to JSONL file"""
    with open(EVENTS_FILE, 'a') as f:
        f.write(json.dumps(event) + '\n')


async def process_order(order_data: dict) -> dict:
    """
    Process order through complete pipeline

    Args:
        order_data: Order dictionary

    Returns:
        Processing result
    """
    order_id = order_data["id"]

    # Start tracing span
    with tracing.start_span("process_order") as span:
        span.set_attribute("order.id", order_id)
        span.set_attribute("order.symbol", order_data["symbol"])

        try:
            # 1. Risk check
            risk_result = await risk_engine.check_order(order_data)
            if not risk_result["approved"]:
                metrics.record_order_rejected(order_id, "risk_check")
                alerts.trigger_alert("risk_violation", {
                    "order_id": order_id,
                    "reason": risk_result["reason"]
                })
                return {
                    "status": "rejected",
                    "reason": risk_result["reason"]
                }

            # 2. Route to broker
            selected_broker = await order_router.route_order(order_data)
            if not selected_broker:
                metrics.record_order_rejected(order_id, "no_broker_available")
                alerts.trigger_alert("routing_failure", {
                    "order_id": order_id,
                    "reason": "No broker available"
                })
                return {
                    "status": "rejected",
                    "reason": "No broker available"
                }

            # 3. Submit to broker
            broker_adapter = order_router.brokers[selected_broker].adapter
            submission_result = await broker_adapter.submit_order(order_data)

            if submission_result["status"] == "accepted":
                # Record successful submission
                metrics.record_order_processed(order_id, selected_broker)
                reconciliation.record_order(order_id, order_data, selected_broker)

                # Persist event
                event = {
                    'type': 'OrderSubmitted',
                    'internalOrderId': order_id,
                    'broker': selected_broker,
                    'brokerOrderId': submission_result.get("broker_order_id"),
                    'idempotency': order_data.get("idempotency"),
                    'clientOrderId': order_data.get("clientOrderId"),
                    'clientId': order_data.get("clientId"),
                    'symbol': order_data["symbol"],
                    'qty': order_data["qty"],
                    'price': order_data["price"],
                    'side': order_data["side"],
                    'orderType': order_data["type"],
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
                persist_event(event)

                return {
                    "status": "accepted",
                    "internalOrderId": order_id,
                    "broker": selected_broker,
                    "brokerOrderId": submission_result.get("broker_order_id")
                }
            else:
                # Handle submission failure
                await order_router.handle_routing_failure(order_id, selected_broker)
                metrics.record_order_failed(order_id, selected_broker, submission_result.get("error", "unknown"))
                alerts.trigger_alert("order_submission_failure", {
                    "order_id": order_id,
                    "broker": selected_broker,
                    "error": submission_result.get("error")
                })
                return {
                    "status": "failed",
                    "reason": submission_result.get("error", "Submission failed")
                }

        except Exception as e:
            # Handle unexpected errors
            metrics.record_order_error(order_id, str(e))
            alerts.trigger_alert("system_error", {
                "order_id": order_id,
                "error": str(e)
            })
            span.record_exception(e)
            return {
                "status": "error",
                "reason": str(e)
            }


@app.post('/api/v1/orders')
async def create_order(req: OrderRequest, x_idempotency_key: Optional[str] = Header(None)):
    """
    Create and process a new order

    Args:
        req: Order request
        x_idempotency_key: Idempotency key header

    Returns:
        Order processing result
    """
    idempotency = x_idempotency_key or req.clientOrderId
    if not idempotency:
        raise HTTPException(status_code=400, detail='clientOrderId or X-Idempotency-Key required')

    # Check for duplicate orders
    if os.path.exists(EVENTS_FILE):
        with open(EVENTS_FILE, 'r') as f:
            for line in f:
                ev = json.loads(line)
                if (ev.get('type') == 'OrderSubmitted' and
                    ev.get('idempotency') == idempotency):
                    return {
                        'status': 'duplicate',
                        'internalOrderId': ev.get('internalOrderId')
                    }

    # Create order data structure
    order_data = {
        "id": f"int-{int(datetime.utcnow().timestamp()*1000)}",
        "idempotency": idempotency,
        "clientOrderId": req.clientOrderId,
        "clientId": req.clientId,
        "symbol": req.symbol,
        "qty": req.qty,
        "price": req.price,
        "side": req.side,
        "type": req.type,
        "timeInForce": req.timeInForce,
        "timestamp": datetime.utcnow().isoformat() + 'Z'
    }

    # Process order through pipeline
    result = await process_order(order_data)

    return result


@app.get('/health')
async def health():
    """Health check endpoint"""
    return {
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }


@app.get('/metrics')
async def get_metrics():
    """Prometheus-style metrics endpoint"""
    return metrics.get_prometheus_metrics()


@app.get('/status')
async def get_status():
    """System status endpoint"""
    return {
        'brokers': order_router.get_broker_status(),
        'routing_stats': order_router.get_routing_stats(),
        'risk_engine': risk_engine.get_status(),
        'reconciliation': reconciliation.get_status(),
        'alerts': alerts.get_active_alerts(),
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }


@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    # Start health monitoring
    await order_router.start_health_monitoring()

    # Initialize monitoring
    await metrics.initialize()
    await tracing.initialize()
    await alerts.initialize()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    # Stop health monitoring
    await order_router.stop_health_monitoring()

    # Cleanup monitoring
    await tracing.shutdown()
    await alerts.shutdown()


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8000)

"""Minimal orchestrator scaffold for POC testing.

Endpoints:
- POST /api/v1/orders -> accept order, dedupe, persist OrderSubmitted event
- GET /health -> simple ok
- GET /metrics -> placeholder

Persists events to data/events.jsonl as JSON lines.
"""
from fastapi import FastAPI, Request, Header, HTTPException
from pydantic import BaseModel
import uvicorn
import os
import json
from datetime import datetime
from typing import Optional

app = FastAPI()

os.makedirs('data', exist_ok=True)

EVENTS_FILE = 'data/events.jsonl'

class OrderRequest(BaseModel):
    clientOrderId: Optional[str]
    clientId: Optional[str]
    symbol: str
    qty: int
    price: float
    side: str


def persist_event(event: dict):
    with open(EVENTS_FILE, 'a') as f:
        f.write(json.dumps(event) + '\n')


@app.post('/api/v1/orders')
async def create_order(req: OrderRequest, x_idempotency_key: Optional[str] = Header(None)):
    idempotency = x_idempotency_key or req.clientOrderId
    if not idempotency:
        raise HTTPException(status_code=400, detail='clientOrderId or X-Idempotency-Key required')

    # naive dedupe: check existing events for same idempotency
    if os.path.exists(EVENTS_FILE):
        with open(EVENTS_FILE, 'r') as f:
            for line in f:
                ev = json.loads(line)
                if ev.get('type') == 'OrderSubmitted' and ev.get('idempotency') == idempotency:
                    return {'status': 'duplicate', 'internalOrderId': ev.get('internalOrderId')}

    internal_id = f"int-{int(datetime.utcnow().timestamp()*1000)}"
    event = {
        'type': 'OrderSubmitted',
        'internalOrderId': internal_id,
        'idempotency': idempotency,
        'clientOrderId': req.clientOrderId,
        'clientId': req.clientId,
        'symbol': req.symbol,
        'qty': req.qty,
        'price': req.price,
        'side': req.side,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    persist_event(event)
    return {'status': 'accepted', 'internalOrderId': internal_id}


@app.get('/health')
async def health():
    return {'status': 'ok'}


@app.get('/metrics')
async def metrics():
    return {'uptime_seconds': 0}


if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8000)

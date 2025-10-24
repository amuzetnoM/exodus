#!/usr/bin/env python3
"""Mock orchestrator for XM MT5 EA testing.

Provides a deterministic REST endpoint that simulates broker ACKs
and execution reports. Intended for local E2E and CI tests.
"""

import asyncio
import json
import uuid
from aiohttp import web

routes = web.RouteTableDef()


@routes.post('/api/v1/ea_callback')
async def ea_callback(request):
    body = await request.json()
    client_order_id = body.get('clientOrderId')
    symbol = body.get('symbol')
    qty = int(body.get('qty', 0))

    # immediate ACK response
    broker_order_id = str(uuid.uuid4())
    ack = {
        'status': 'ACKED',
        'brokerOrderId': broker_order_id,
        'internalOrderId': str(uuid.uuid4()),
        'filledQty': 0,
        'remainingQty': qty,
    }

    print('RECEIVED ORDER:', client_order_id, symbol, qty)

    # schedule a simulated fill for CI or manual testing
    asyncio.create_task(simulate_fill(broker_order_id, symbol, qty,
                                      client_order_id))

    return web.json_response(ack)


async def simulate_fill(broker_order_id, symbol, qty, client_order_id):
    await asyncio.sleep(1.0)
    filled = qty
    fill_event = {
        'event': 'EXECUTION_REPORT',
        'brokerOrderId': broker_order_id,
        'clientOrderId': client_order_id,
        'status': 'FILLED',
        'filledQty': filled,
        'price': 1.2345,
        'tradeId': str(uuid.uuid4()),
    }
    # In CI tests this line can be captured or sent to a websocket
    print('SIMULATED FILL:', json.dumps(fill_event))


async def init_app():
    app = web.Application()
    app.add_routes(routes)
    return app


def main():
    app = asyncio.run(init_app())
    web.run_app(app, host='127.0.0.1', port=8080)


if __name__ == '__main__':
    main()

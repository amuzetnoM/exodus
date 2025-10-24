# exodus_arc/adapters/xm_adapter.py
"""
XM Trading MT5 Adapter

Adapter for connecting to XM Trading's MT5 platform via REST API
and MetaTrader 5 Expert Advisor WebRequest calls.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import httpx
from .base_adapter import BaseBrokerAdapter, OrderStatus, ExecutionReport


class XMMT5Adapter(BaseBrokerAdapter):
    """
    XM Trading MT5 Adapter

    Connects to XM Trading's MT5 platform for order execution.
    Supports both direct API calls and MT5 EA WebRequest integration.
    """

    def __init__(self, broker_url: str, api_key: str, api_secret: str,
                 account_id: str = None, mt5_server: str = "XMGlobal-MT5"):
        """
        Initialize XM MT5 adapter

        Args:
            broker_url: XM API endpoint (e.g., https://api.xm.com/v1)
            api_key: XM API key
            api_secret: XM API secret
            account_id: XM account ID
            mt5_server: MT5 server name
        """
        super().__init__(broker_url, api_key, api_secret)
        self.account_id = account_id
        self.mt5_server = mt5_server
        self.client: Optional[httpx.AsyncClient] = None
        self.connected = False

    async def connect(self) -> bool:
        """
        Establish connection to XM MT5

        Returns:
            True if connection successful
        """
    async def connect(self) -> bool:
        """
        Establish connection to XM MT5

        Returns:
            True if connection successful
        """
        try:
            # For testing purposes, simulate connection to MT5
            # In production, this would validate MT5 terminal connectivity
            print(f"✓ Connecting to XM MT5 server: {self.mt5_server}")
            print(f"✓ Account: {self.account_id}")

            # Mock successful connection
            self.connected = True
            print("✓ XM MT5 connection established (mock)")
            return True

        except Exception as e:
            print(f"XM connection error: {e}")
            return False

    async def disconnect(self) -> None:
        """
        Close connection to XM MT5
        """
        if self.client:
            await self.client.aclose()
            self.client = None
        self.connected = False

    async def submit_order(self, order: Dict[str, Any]) -> ExecutionReport:
        """
        Submit order to XM MT5

        Args:
            order: Order in EXODUS format

        Returns:
            ExecutionReport with order status
        """
        if not self.client or not self.connected:
            raise ConnectionError("Not connected to XM MT5")

        # Transform order to XM format
        xm_order = self.transform_order_to_xm(order)

    async def submit_order(self, order: Dict[str, Any]) -> ExecutionReport:
        """
        Submit order to XM MT5

        Args:
            order: Order in EXODUS format

        Returns:
            ExecutionReport with order status
        """
        if not self.client or not self.connected:
            raise ConnectionError("Not connected to XM MT5")

        # For testing purposes, return a mock successful execution
        # In production, this would use WebRequest to communicate with MT5 EA
        import time
        broker_order_id = f"xm-{int(time.time()*1000)}"

        print(f"✓ MOCK: Order submitted to XM MT5 - {order['symbol']} {order['side']} {order['qty']} @ {order.get('price', 'market')}")
        print(f"✓ MOCK: Broker Order ID: {broker_order_id}")

        return ExecutionReport(
            broker_order_id=broker_order_id,
            client_order_id=order.get("clientOrderId"),
            symbol=order["symbol"],
            side=order["side"],
            quantity=order["qty"],
            price=order.get("price", 0.0),
            status=OrderStatus.FILLED,
            timestamp=datetime.now(timezone.utc),
            fills=[{
                "price": order.get("price", 1.0875),  # Mock fill price
                "quantity": order["qty"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]
        )

    async def cancel_order(self, broker_order_id: str) -> bool:
        """
        Cancel order in XM MT5

        Args:
            broker_order_id: XM order ID

        Returns:
            True if cancellation successful
        """
        if not self.client or not self.connected:
            return False

        try:
            response = await self.client.delete(f"/orders/{broker_order_id}")
            return response.status_code == 200
        except Exception:
            return False

    async def get_order_status(self, broker_order_id: str) -> Optional[ExecutionReport]:
        """
        Get order status from XM MT5

        Args:
            broker_order_id: XM order ID

        Returns:
            ExecutionReport if found, None otherwise
        """
        if not self.client or not self.connected:
            return None

        try:
            response = await self.client.get(f"/orders/{broker_order_id}")
            if response.status_code == 200:
                xm_response = response.json()
                return self.transform_xm_response(xm_response)
            return None
        except Exception:
            return None

    async def get_account_balance(self) -> Dict[str, Any]:
        """
        Get account balance from XM MT5

        Returns:
            Dictionary with balance information
        """
        if not self.client or not self.connected:
            return {}

        try:
            response = await self.client.get("/account/balance")
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception:
            return {}

    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get current positions from XM MT5

        Returns:
            List of position dictionaries
        """
        if not self.client or not self.connected:
            return []

        try:
            response = await self.client.get("/positions")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception:
            return []

    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get market data for symbol from XM MT5

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with market data
        """
        if not self.client or not self.connected:
            return {}

        try:
            response = await self.client.get(f"/market/{symbol}")
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception:
            return {}

    def transform_order_to_xm(self, exodus_order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform EXODUS order to XM MT5 format

        Args:
            exodus_order: Order in EXODUS format

        Returns:
            Order in XM format
        """
        # XM MT5 order structure
        xm_order = {
            "account": self.account_id,
            "symbol": exodus_order["symbol"],
            "side": exodus_order["side"].upper(),
            "quantity": exodus_order["qty"],
            "type": "market" if not exodus_order.get("price") else "limit",
            "clientOrderId": exodus_order.get("clientOrderId", ""),
            "server": self.mt5_server
        }

        # Add price for limit orders
        if exodus_order.get("price"):
            xm_order["price"] = exodus_order["price"]

        # Add strategy metadata
        if "strategy" in exodus_order:
            xm_order["metadata"] = {
                "strategy": exodus_order["strategy"],
                "signal_type": exodus_order.get("signal_type", "")
            }

        return xm_order

    def transform_xm_response(self, xm_response: Dict[str, Any]) -> ExecutionReport:
        """
        Transform XM response to ExecutionReport

        Args:
            xm_response: XM API response

        Returns:
            Standardized ExecutionReport
        """
        # Map XM status to OrderStatus
        status_mapping = {
            "pending": OrderStatus.PENDING,
            "accepted": OrderStatus.ACCEPTED,
            "partial": OrderStatus.PARTIAL_FILL,
            "filled": OrderStatus.FILLED,
            "cancelled": OrderStatus.CANCELLED,
            "rejected": OrderStatus.REJECTED,
            "expired": OrderStatus.EXPIRED
        }

        status_str = xm_response.get("status", "").lower()
        status = status_mapping.get(status_str, OrderStatus.PENDING)

        # Parse timestamp
        timestamp_str = xm_response.get("timestamp")
        if timestamp_str:
            # Assume ISO format
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            timestamp = datetime.now(timezone.utc)

        return ExecutionReport(
            broker_order_id=xm_response.get("orderId", ""),
            client_order_id=xm_response.get("clientOrderId"),
            symbol=xm_response.get("symbol", ""),
            side=xm_response.get("side", "").lower(),
            quantity=xm_response.get("quantity", 0.0),
            price=xm_response.get("price", 0.0),
            status=status,
            timestamp=timestamp,
            fills=xm_response.get("fills", [])
        )

    async def get_mt5_webrequest_status(self) -> Dict[str, Any]:
        """
        Get status for MT5 WebRequest integration

        Returns:
            Dictionary with WebRequest status information
        """
        return {
            "connected": self.connected,
            "mt5_server": self.mt5_server,
            "account_id": self.account_id,
            "webrequest_enabled": True,  # Would check MT5 config
            "last_heartbeat": datetime.now(timezone.utc).isoformat()
        }

    async def simulate_mt5_webrequest(self, order_payload: str) -> Dict[str, Any]:
        """
        Simulate MT5 WebRequest call for testing

        Args:
            order_payload: JSON payload from MT5 EA

        Returns:
            Simulated response
        """
        try:
            # Parse the order from MT5
            mt5_order = json.loads(order_payload)

            # Convert to EXODUS format and submit
            exodus_order = {
                "clientOrderId": mt5_order.get("clientOrderId"),
                "symbol": mt5_order.get("symbol"),
                "qty": mt5_order.get("qty"),
                "price": mt5_order.get("price"),
                "side": mt5_order.get("side"),
                "source": "mt5_ea"
            }

            # Submit the order
            result = await self.submit_order(exodus_order)

            # Return response that MT5 EA expects
            return {
                "status": "success" if result.status == OrderStatus.ACCEPTED else "error",
                "internalOrderId": result.broker_order_id,
                "clientOrderId": result.client_order_id,
                "timestamp": result.timestamp.isoformat()
            }

        except json.JSONDecodeError:
            return {"status": "error", "message": "Invalid JSON payload"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

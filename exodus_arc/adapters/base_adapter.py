# exodus_arc/adapters/base_adapter.py
"""
Base broker adapter interface for EXODUS platform
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class ExecutionReport:
    """Execution report data structure"""
    broker_order_id: str
    client_order_id: Optional[str]
    symbol: str
    side: str
    quantity: float
    price: float
    status: OrderStatus
    timestamp: datetime
    fills: list = None

    def __post_init__(self):
        if self.fills is None:
            self.fills = []


class BaseBrokerAdapter(ABC):
    """
    Abstract base class for broker adapters

    All broker adapters must implement this interface to ensure
    consistent behavior across different brokers.
    """

    def __init__(self, broker_url: str, api_key: str, api_secret: str):
        """
        Initialize broker adapter

        Args:
            broker_url: Broker API endpoint URL
            api_key: API key for authentication
            api_secret: API secret for authentication
        """
        self.broker_url = broker_url
        self.api_key = api_key
        self.api_secret = api_secret

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to broker

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close connection to broker
        """
        pass

    @abstractmethod
    async def submit_order(self, order: Dict[str, Any]) -> ExecutionReport:
        """
        Submit order to broker

        Args:
            order: Order dictionary with standard fields

        Returns:
            ExecutionReport with order status and details
        """
        pass

    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> bool:
        """
        Cancel pending order

        Args:
            broker_order_id: Broker's order identifier

        Returns:
            True if cancellation successful, False otherwise
        """
        pass

    @abstractmethod
    async def get_order_status(self, broker_order_id: str) -> Optional[ExecutionReport]:
        """
        Get current status of an order

        Args:
            broker_order_id: Broker's order identifier

        Returns:
            ExecutionReport if order found, None otherwise
        """
        pass

    @abstractmethod
    async def get_account_balance(self) -> Dict[str, Any]:
        """
        Get account balance and margin information

        Returns:
            Dictionary with balance details
        """
        pass

    @abstractmethod
    async def get_positions(self) -> list:
        """
        Get current positions

        Returns:
            List of position dictionaries
        """
        pass

    @abstractmethod
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get current market data for symbol

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with market data (bid, ask, spread, etc.)
        """
        pass

    def transform_order(self, exodus_order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform EXODUS order format to broker-specific format

        This is a common transformation that can be overridden by subclasses
        for broker-specific requirements.

        Args:
            exodus_order: Order in EXODUS format

        Returns:
            Order in broker-specific format
        """
        # Default transformation - most brokers use similar structure
        return {
            "symbol": exodus_order["symbol"],
            "side": exodus_order["side"].upper(),
            "quantity": exodus_order["qty"],
            "price": exodus_order.get("price"),  # None for market orders
            "orderType": "MARKET" if not exodus_order.get("price") else "LIMIT",
            "clientOrderId": exodus_order.get("clientOrderId")
        }

    def transform_execution_report(self, broker_response: Dict[str, Any]) -> ExecutionReport:
        """
        Transform broker execution report to standard ExecutionReport

        Args:
            broker_response: Broker-specific execution report

        Returns:
            Standardized ExecutionReport
        """
        # Map broker status to OrderStatus enum
        status_mapping = {
            "pending": OrderStatus.PENDING,
            "accepted": OrderStatus.ACCEPTED,
            "partial": OrderStatus.PARTIAL_FILL,
            "filled": OrderStatus.FILLED,
            "cancelled": OrderStatus.CANCELLED,
            "rejected": OrderStatus.REJECTED,
            "expired": OrderStatus.EXPIRED
        }

        status = status_mapping.get(
            broker_response.get("status", "").lower(),
            OrderStatus.PENDING
        )

        return ExecutionReport(
            broker_order_id=broker_response.get("orderId", ""),
            client_order_id=broker_response.get("clientOrderId"),
            symbol=broker_response.get("symbol", ""),
            side=broker_response.get("side", "").lower(),
            quantity=broker_response.get("quantity", 0.0),
            price=broker_response.get("price", 0.0),
            status=status,
            timestamp=datetime.utcnow(),  # Would parse from broker response
            fills=broker_response.get("fills", [])
        )

    async def health_check(self) -> bool:
        """
        Perform health check on broker connection

        Returns:
            True if broker is accessible, False otherwise
        """
        try:
            # Simple connectivity check
            balance = await self.get_account_balance()
            return balance is not None
        except Exception:
            return False

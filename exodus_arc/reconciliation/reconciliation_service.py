# exodus_arc/reconciliation/reconciliation_service.py
"""
Reconciliation Service for EXODUS Platform

Handles real-time order-to-fill matching, end-of-day reconciliation,
unmatched trade detection, and automated alerts.
"""

from typing import Dict, Any, List, Optional, Set, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict


class ReconciliationStatus(Enum):
    """Reconciliation status"""
    MATCHED = "matched"
    UNMATCHED = "unmatched"
    PARTIAL = "partial"
    PENDING = "pending"
    FAILED = "failed"


class ReconciliationType(Enum):
    """Types of reconciliation"""
    REAL_TIME = "real_time"
    END_OF_DAY = "end_of_day"
    INTRA_DAY = "intra_day"


@dataclass
class OrderFill:
    """Order fill record"""
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    timestamp: datetime
    broker_order_id: Optional[str] = None
    execution_id: Optional[str] = None


@dataclass
class ReconciliationRecord:
    """Reconciliation record"""
    order_id: str
    broker_order_id: Optional[str]
    expected_quantity: float
    filled_quantity: float
    expected_price: Optional[float]
    average_fill_price: Optional[float]
    status: ReconciliationStatus
    reconciliation_type: ReconciliationType
    timestamp: datetime
    discrepancies: List[str]
    fills: List[OrderFill]


class ReconciliationService:
    """
    Handles order-to-fill reconciliation and trade matching

    Features:
    - Real-time order-to-fill matching
    - End-of-day reconciliation
    - Unmatched trade detection
    - Automated discrepancy alerts
    - Broker statement comparison
    """

    def __init__(self):
        # Reconciliation data
        self.pending_orders: Dict[str, Dict[str, Any]] = {}
        self.fills_by_order: Dict[str, List[OrderFill]] = defaultdict(list)
        self.reconciliation_records: List[ReconciliationRecord] = []

        # Reconciliation settings
        self.tolerance_price = 0.001  # 0.1% price tolerance
        self.tolerance_quantity = 0.01  # 1% quantity tolerance
        self.max_reconciliation_age = timedelta(hours=24)

        # Alert callbacks
        self.alert_callbacks: List[
            Callable[[Dict[str, Any]], Awaitable[None]]
        ] = []

    async def submit_order(self, order: Dict[str, Any]):
        """
        Submit order for reconciliation tracking

        Args:
            order: Order dictionary
        """
        order_id = order["id"]
        self.pending_orders[order_id] = {
            "order": order,
            "submitted_at": datetime.utcnow(),
            "fills": [],
            "status": ReconciliationStatus.PENDING
        }

    async def record_fill(self, fill: OrderFill):
        """
        Record a fill against an order

        Args:
            fill: Fill record
        """
        order_id = fill.order_id

        if order_id not in self.pending_orders:
            # Fill for unknown order - create pending record
            self.pending_orders[order_id] = {
                "order": None,  # Will be populated when order arrives
                "submitted_at": datetime.utcnow(),
                "fills": [],
                "status": ReconciliationStatus.PENDING
            }

        self.pending_orders[order_id]["fills"].append(fill)
        self.fills_by_order[order_id].append(fill)

        # Attempt real-time reconciliation
        await self._reconcile_order_real_time(order_id)

    async def _reconcile_order_real_time(self, order_id: str):
        """
        Perform real-time reconciliation for an order

        Args:
            order_id: Order ID to reconcile
        """
        if order_id not in self.pending_orders:
            return

        order_record = self.pending_orders[order_id]
        order = order_record["order"]
        fills = order_record["fills"]

        if not order:
            return  # Wait for order to arrive

        expected_quantity = order["qty"]
        filled_quantity = sum(fill.quantity for fill in fills)

        # Check if order is fully filled
        if abs(filled_quantity - expected_quantity) < self.tolerance_quantity:
            order_record["status"] = ReconciliationStatus.MATCHED
            await self._create_reconciliation_record(
                order_id, order, fills, ReconciliationType.REAL_TIME
            )
        elif filled_quantity > 0:
            order_record["status"] = ReconciliationStatus.PARTIAL

    async def _create_reconciliation_record(
        self,
        order_id: str,
        order: Dict[str, Any],
        fills: List[OrderFill],
        reconciliation_type: ReconciliationType
    ):
        """
        Create a reconciliation record

        Args:
            order_id: Order ID
            order: Order details
            fills: List of fills
            reconciliation_type: Type of reconciliation
        """
        expected_quantity = order["qty"]
        filled_quantity = sum(fill.quantity for fill in fills)
        expected_price = order.get("price")

        if fills:
            total_value = sum(fill.quantity * fill.price for fill in fills)
            average_fill_price = total_value / filled_quantity
        else:
            average_fill_price = None

        # Check for discrepancies
        discrepancies = []

        if abs(filled_quantity - expected_quantity) > self.tolerance_quantity:
            discrepancies.append(
                f"Quantity mismatch: expected {expected_quantity}, "
                f"filled {filled_quantity}"
            )

        if expected_price and average_fill_price:
            price_diff = abs(average_fill_price - expected_price) / expected_price
            if price_diff > self.tolerance_price:
                discrepancies.append(
                    f"Price mismatch: expected {expected_price}, "
                    f"average fill {average_fill_price:.4f}"
                )

        # Determine status
        if not discrepancies:
            status = ReconciliationStatus.MATCHED
        elif filled_quantity == 0:
            status = ReconciliationStatus.UNMATCHED
        else:
            status = ReconciliationStatus.PARTIAL

        record = ReconciliationRecord(
            order_id=order_id,
            broker_order_id=order.get("broker_order_id"),
            expected_quantity=expected_quantity,
            filled_quantity=filled_quantity,
            expected_price=expected_price,
            average_fill_price=average_fill_price,
            status=status,
            reconciliation_type=reconciliation_type,
            timestamp=datetime.utcnow(),
            discrepancies=discrepancies,
            fills=fills
        )

        self.reconciliation_records.append(record)

        # Alert on discrepancies
        if discrepancies:
            await self._alert_discrepancy(record)

    async def reconcile_end_of_day(
        self, broker_statement: List[Dict[str, Any]]
    ):
        """
        Perform end-of-day reconciliation against broker statement

        Args:
            broker_statement: Broker's statement of trades
        """
        # Group broker trades by order ID
        broker_trades_by_order: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for trade in broker_statement:
            order_id = trade.get("client_order_id") or trade.get("order_id")
            if order_id:
                broker_trades_by_order[order_id].append(trade)

        # Reconcile each pending order
        for order_id, order_record in self.pending_orders.items():
            if order_record["status"] == ReconciliationStatus.MATCHED:
                continue

            broker_trades = broker_trades_by_order.get(order_id, [])
            await self._reconcile_with_broker_statement(order_id, broker_trades)

        # Check for broker trades without matching orders
        all_order_ids = set(self.pending_orders.keys())
        for order_id, broker_trades in broker_trades_by_order.items():
            if order_id not in all_order_ids:
                await self._handle_unmatched_broker_trade(order_id, broker_trades)

    async def _reconcile_with_broker_statement(
        self,
        order_id: str,
        broker_trades: List[Dict[str, Any]]
    ):
        """
        Reconcile order with broker statement

        Args:
            order_id: Order ID
            broker_trades: Broker trades for this order
        """
        order_record = self.pending_orders[order_id]
        order = order_record["order"]

        if not order:
            return

        # Convert broker trades to fills
        broker_fills = []
        for trade in broker_trades:
            fill = OrderFill(
                order_id=order_id,
                symbol=trade["symbol"],
                side=trade["side"],
                quantity=trade["quantity"],
                price=trade["price"],
                timestamp=datetime.fromisoformat(trade["timestamp"]),
                broker_order_id=trade.get("broker_order_id"),
                execution_id=trade.get("execution_id")
            )
            broker_fills.append(fill)

        # Combine with existing fills
        all_fills = order_record["fills"] + broker_fills

        # Remove duplicates based on execution_id
        unique_fills = self._deduplicate_fills(all_fills)

        order_record["fills"] = unique_fills

        # Create EOD reconciliation record
        await self._create_reconciliation_record(
            order_id, order, unique_fills, ReconciliationType.END_OF_DAY
        )

    def _deduplicate_fills(self, fills: List[OrderFill]) -> List[OrderFill]:
        """
        Remove duplicate fills based on execution ID

        Args:
            fills: List of fills

        Returns:
            Deduplicated list of fills
        """
        seen_executions: Set[str] = set()
        unique_fills = []

        for fill in fills:
            execution_key = (
                fill.execution_id or
                f"{fill.order_id}_{fill.timestamp.isoformat()}_{fill.quantity}_{fill.price}"
            )

            if execution_key not in seen_executions:
                seen_executions.add(execution_key)
                unique_fills.append(fill)

        return unique_fills

    async def _handle_unmatched_broker_trade(
        self,
        order_id: str,
        broker_trades: List[Dict[str, Any]]
    ):
        """
        Handle broker trades without matching orders

        Args:
            order_id: Order ID from broker
            broker_trades: Broker trades
        """
        # Create reconciliation record for unmatched broker trade
        total_quantity = sum(trade["quantity"] for trade in broker_trades)

        record = ReconciliationRecord(
            order_id=order_id,
            broker_order_id=broker_trades[0].get("broker_order_id"),
            expected_quantity=0,  # No expected order
            filled_quantity=total_quantity,
            expected_price=None,
            average_fill_price=None,
            status=ReconciliationStatus.UNMATCHED,
            reconciliation_type=ReconciliationType.END_OF_DAY,
            timestamp=datetime.utcnow(),
            discrepancies=["No matching order found"],
            fills=[]  # Could populate with broker fills if needed
        )

        self.reconciliation_records.append(record)
        await self._alert_discrepancy(record)

    async def _alert_discrepancy(self, record: ReconciliationRecord):
        """
        Alert on reconciliation discrepancies

        Args:
            record: Reconciliation record with discrepancies
        """
        alert_message = {
            "type": "reconciliation_discrepancy",
            "order_id": record.order_id,
            "status": record.status.value,
            "discrepancies": record.discrepancies,
            "expected_quantity": record.expected_quantity,
            "filled_quantity": record.filled_quantity,
            "timestamp": record.timestamp.isoformat()
        }

        for callback in self.alert_callbacks:
            try:
                await callback(alert_message)
            except Exception as e:
                print(f"Alert callback error: {e}")

    def add_alert_callback(self, callback: callable):
        """
        Add alert callback function

        Args:
            callback: Async function to call on alerts
        """
        self.alert_callbacks.append(callback)

    def get_reconciliation_status(self, order_id: str) -> Optional[ReconciliationStatus]:
        """
        Get reconciliation status for an order

        Args:
            order_id: Order ID

        Returns:
            Reconciliation status or None if not found
        """
        if order_id in self.pending_orders:
            return self.pending_orders[order_id]["status"]
        return None

    def get_unmatched_orders(self) -> List[str]:
        """
        Get list of unmatched order IDs

        Returns:
            List of unmatched order IDs
        """
        return [
            order_id for order_id, record in self.pending_orders.items()
            if record["status"] in [ReconciliationStatus.UNMATCHED, ReconciliationStatus.FAILED]
        ]

    def get_reconciliation_report(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate reconciliation report

        Args:
            start_time: Start time for report
            end_time: End time for report

        Returns:
            List of reconciliation records as dictionaries
        """
        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=1)
        if not end_time:
            end_time = datetime.utcnow()

        report_records = [
            record for record in self.reconciliation_records
            if start_time <= record.timestamp <= end_time
        ]

        return [
            {
                "order_id": record.order_id,
                "broker_order_id": record.broker_order_id,
                "expected_quantity": record.expected_quantity,
                "filled_quantity": record.filled_quantity,
                "expected_price": record.expected_price,
                "average_fill_price": record.average_fill_price,
                "status": record.status.value,
                "reconciliation_type": record.reconciliation_type.value,
                "timestamp": record.timestamp.isoformat(),
                "discrepancies": record.discrepancies,
                "fill_count": len(record.fills)
            }
            for record in report_records
        ]

    def cleanup_old_records(self, max_age: timedelta = None):
        """
        Clean up old reconciliation records

        Args:
            max_age: Maximum age to keep records
        """
        if not max_age:
            max_age = self.max_reconciliation_age

        cutoff_time = datetime.utcnow() - max_age

        # Remove old reconciliation records
        self.reconciliation_records = [
            record for record in self.reconciliation_records
            if record.timestamp > cutoff_time
        ]

        # Remove old pending orders (completed ones)
        to_remove = []
        for order_id, order_record in self.pending_orders.items():
            if (order_record["status"] == ReconciliationStatus.MATCHED and
                order_record["submitted_at"] < cutoff_time):
                to_remove.append(order_id)

        for order_id in to_remove:
            del self.pending_orders[order_id]

    def get_reconciliation_metrics(self) -> Dict[str, Any]:
        """
        Get reconciliation metrics

        Returns:
            Dictionary with reconciliation metrics
        """
        total_records = len(self.reconciliation_records)
        if total_records == 0:
            return {"total_records": 0}

        status_counts = defaultdict(int)
        for record in self.reconciliation_records:
            status_counts[record.status] += 1

        discrepancy_count = sum(
            1 for record in self.reconciliation_records
            if record.discrepancies
        )

        return {
            "total_records": total_records,
            "matched": status_counts[ReconciliationStatus.MATCHED],
            "unmatched": status_counts[ReconciliationStatus.UNMATCHED],
            "partial": status_counts[ReconciliationStatus.PARTIAL],
            "pending": status_counts[ReconciliationStatus.PENDING],
            "failed": status_counts[ReconciliationStatus.FAILED],
            "with_discrepancies": discrepancy_count,
            "discrepancy_rate": discrepancy_count / total_records
        }

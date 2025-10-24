# exodus_arc/order_router.py
"""
Order Router for EXODUS Platform

Routes orders from orchestrator to appropriate broker adapters
with load balancing and failover capabilities.
"""

from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio
from collections import defaultdict
import random


class RoutingStrategy(Enum):
    """Order routing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    PRIORITY_BASED = "priority_based"
    FAILOVER = "failover"


class BrokerStatus(Enum):
    """Broker connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"


@dataclass
class BrokerEndpoint:
    """Broker endpoint configuration"""
    name: str
    adapter: Any  # Broker adapter instance
    status: BrokerStatus
    priority: int
    max_concurrent_orders: int
    current_load: int
    last_heartbeat: datetime
    capabilities: List[str]


@dataclass
class RoutingDecision:
    """Order routing decision"""
    order_id: str
    selected_broker: str
    routing_strategy: RoutingStrategy
    failover_attempts: int
    route_timestamp: datetime
    reason: str


class OrderRouter:
    """
    Intelligent order routing system

    Features:
    - Multiple routing strategies
    - Load balancing across brokers
    - Automatic failover
    - Health monitoring
    - Priority-based routing
    """

    def __init__(self):
        self.brokers: Dict[str, BrokerEndpoint] = {}
        self.routing_history: List[RoutingDecision] = []
        self.routing_strategy = RoutingStrategy.LEAST_LOADED

        # Routing state
        self.round_robin_index = 0
        self.failover_cache: Dict[str, List[str]] = defaultdict(list)

        # Health monitoring
        self.health_check_interval = 30  # seconds
        self.health_check_task: Optional[asyncio.Task] = None

    def register_broker(self,
                       name: str,
                       adapter: Any,
                       priority: int = 1,
                       max_concurrent: int = 100,
                       capabilities: List[str] = None):
        """
        Register a broker endpoint

        Args:
            name: Broker name
            adapter: Broker adapter instance
            priority: Routing priority (higher = preferred)
            max_concurrent: Max concurrent orders
            capabilities: Broker capabilities
        """
        endpoint = BrokerEndpoint(
            name=name,
            adapter=adapter,
            status=BrokerStatus.CONNECTED,
            priority=priority,
            max_concurrent_orders=max_concurrent,
            current_load=0,
            last_heartbeat=datetime.utcnow(),
            capabilities=capabilities or []
        )

        self.brokers[name] = endpoint

    def unregister_broker(self, name: str):
        """
        Unregister a broker endpoint

        Args:
            name: Broker name
        """
        if name in self.brokers:
            del self.brokers[name]

    async def route_order(self, order: Dict[str, Any]) -> Optional[str]:
        """
        Route an order to appropriate broker

        Args:
            order: Order dictionary

        Returns:
            Broker name if routed successfully, None otherwise
        """
        order_id = order["id"]
        symbol = order["symbol"]

        # Find available brokers for this order
        available_brokers = self._get_available_brokers(order)

        if not available_brokers:
            return None

        # Select broker based on strategy
        selected_broker = self._select_broker(available_brokers, order)

        if selected_broker:
            # Record routing decision
            decision = RoutingDecision(
                order_id=order_id,
                selected_broker=selected_broker,
                routing_strategy=self.routing_strategy,
                failover_attempts=0,
                route_timestamp=datetime.utcnow(),
                reason=f"Selected via {self.routing_strategy.value} strategy"
            )
            self.routing_history.append(decision)

            # Update broker load
            self.brokers[selected_broker].current_load += 1

            return selected_broker

        return None

    def _get_available_brokers(self, order: Dict[str, Any]) -> List[str]:
        """
        Get brokers available for order routing

        Args:
            order: Order to route

        Returns:
            List of available broker names
        """
        available = []

        for name, broker in self.brokers.items():
            if (broker.status == BrokerStatus.CONNECTED and
                broker.current_load < broker.max_concurrent_orders):

                # Check capabilities match
                if self._broker_supports_order(broker, order):
                    available.append(name)

        return available

    def _broker_supports_order(self, broker: BrokerEndpoint, order: Dict[str, Any]) -> bool:
        """
        Check if broker supports the order

        Args:
            broker: Broker endpoint
            order: Order to check

        Returns:
            True if broker supports the order
        """
        # Basic capability checks
        required_capabilities = []

        # Check order type
        order_type = order.get("type", "market")
        if order_type == "limit":
            required_capabilities.append("limit_orders")
        elif order_type == "stop":
            required_capabilities.append("stop_orders")

        # Check symbol/asset class
        symbol = order["symbol"]
        if symbol.startswith("EUR") or symbol.startswith("GBP"):
            required_capabilities.append("forex")
        elif symbol.endswith("USD") or "USD" in symbol:
            required_capabilities.append("forex")
        else:
            required_capabilities.append("equities")

        # Check if broker has required capabilities
        return all(cap in broker.capabilities for cap in required_capabilities)

    def _select_broker(self, available_brokers: List[str], order: Dict[str, Any]) -> Optional[str]:
        """
        Select broker using current routing strategy

        Args:
            available_brokers: List of available broker names
            order: Order being routed

        Returns:
            Selected broker name
        """
        if not available_brokers:
            return None

        if self.routing_strategy == RoutingStrategy.ROUND_ROBIN:
            return self._round_robin_select(available_brokers)

        elif self.routing_strategy == RoutingStrategy.LEAST_LOADED:
            return self._least_loaded_select(available_brokers)

        elif self.routing_strategy == RoutingStrategy.PRIORITY_BASED:
            return self._priority_based_select(available_brokers)

        elif self.routing_strategy == RoutingStrategy.FAILOVER:
            return self._failover_select(available_brokers, order)

        # Default to least loaded
        return self._least_loaded_select(available_brokers)

    def _round_robin_select(self, brokers: List[str]) -> str:
        """Round-robin broker selection"""
        if self.round_robin_index >= len(brokers):
            self.round_robin_index = 0

        selected = brokers[self.round_robin_index]
        self.round_robin_index += 1
        return selected

    def _least_loaded_select(self, brokers: List[str]) -> str:
        """Select least loaded broker"""
        broker_loads = [
            (name, self.brokers[name].current_load)
            for name in brokers
        ]
        broker_loads.sort(key=lambda x: x[1])  # Sort by load ascending
        return broker_loads[0][0]

    def _priority_based_select(self, brokers: List[str]) -> str:
        """Select highest priority broker"""
        broker_priorities = [
            (name, self.brokers[name].priority)
            for name in brokers
        ]
        broker_priorities.sort(key=lambda x: x[1], reverse=True)  # Sort by priority descending
        return broker_priorities[0][0]

    def _failover_select(self, brokers: List[str], order: Dict[str, Any]) -> Optional[str]:
        """Failover-based selection using cached preferences"""
        order_id = order["id"]

        # Check if we have a cached failover sequence
        if order_id in self.failover_cache and self.failover_cache[order_id]:
            cached_broker = self.failover_cache[order_id][0]
            if cached_broker in brokers:
                return cached_broker

        # No cache or cached broker unavailable, use primary selection
        return self._least_loaded_select(brokers)

    async def handle_routing_failure(self, order_id: str, failed_broker: str):
        """
        Handle routing failure and attempt failover

        Args:
            order_id: Order ID
            failed_broker: Broker that failed
        """
        # Find routing decision
        decision = None
        for d in reversed(self.routing_history):
            if d.order_id == order_id:
                decision = d
                break

        if not decision:
            return

        # Mark broker as failed (temporarily)
        if failed_broker in self.brokers:
            self.brokers[failed_broker].status = BrokerStatus.DEGRADED

        # Attempt failover
        available_brokers = [
            name for name in self.brokers.keys()
            if name != failed_broker and self.brokers[name].status == BrokerStatus.CONNECTED
        ]

        if available_brokers:
            new_broker = self._select_broker(available_brokers, {"id": order_id})

            if new_broker:
                # Update routing decision
                decision.selected_broker = new_broker
                decision.failover_attempts += 1
                decision.reason = f"Failover from {failed_broker} to {new_broker}"

                # Update failover cache
                self.failover_cache[order_id].append(new_broker)

                # Update broker loads
                self.brokers[failed_broker].current_load = max(0, self.brokers[failed_broker].current_load - 1)
                self.brokers[new_broker].current_load += 1

    def complete_order(self, order_id: str, broker_name: str):
        """
        Mark order as completed and update broker load

        Args:
            order_id: Order ID
            broker_name: Broker that handled the order
        """
        if broker_name in self.brokers:
            self.brokers[broker_name].current_load = max(0, self.brokers[broker_name].current_load - 1)

        # Clean up failover cache
        if order_id in self.failover_cache:
            del self.failover_cache[order_id]

    def set_routing_strategy(self, strategy: RoutingStrategy):
        """
        Set routing strategy

        Args:
            strategy: New routing strategy
        """
        self.routing_strategy = strategy

    def get_routing_stats(self) -> Dict[str, Any]:
        """
        Get routing statistics

        Returns:
            Routing statistics
        """
        total_routes = len(self.routing_history)
        if total_routes == 0:
            return {"total_routes": 0}

        broker_usage = defaultdict(int)
        strategy_usage = defaultdict(int)
        failover_count = 0

        for decision in self.routing_history:
            broker_usage[decision.selected_broker] += 1
            strategy_usage[decision.routing_strategy.value] += 1
            if decision.failover_attempts > 0:
                failover_count += 1

        return {
            "total_routes": total_routes,
            "broker_usage": dict(broker_usage),
            "strategy_usage": dict(strategy_usage),
            "failover_count": failover_count,
            "failover_rate": failover_count / total_routes
        }

    def get_broker_status(self) -> Dict[str, Any]:
        """
        Get status of all registered brokers

        Returns:
            Broker status information
        """
        return {
            name: {
                "status": broker.status.value,
                "current_load": broker.current_load,
                "max_concurrent": broker.max_concurrent_orders,
                "load_percentage": broker.current_load / broker.max_concurrent_orders,
                "last_heartbeat": broker.last_heartbeat.isoformat(),
                "capabilities": broker.capabilities
            }
            for name, broker in self.brokers.items()
        }

    async def start_health_monitoring(self):
        """
        Start broker health monitoring
        """
        if self.health_check_task:
            self.health_check_task.cancel()

        self.health_check_task = asyncio.create_task(self._health_check_loop())

    async def stop_health_monitoring(self):
        """
        Stop broker health monitoring
        """
        if self.health_check_task:
            self.health_check_task.cancel()
            self.health_check_task = None

    async def _health_check_loop(self):
        """
        Health check loop
        """
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Health check error: {e}")
                await asyncio.sleep(self.health_check_interval)

    async def _perform_health_checks(self):
        """
        Perform health checks on all brokers
        """
        for name, broker in self.brokers.items():
            try:
                # Simple health check - in real implementation,
                # this would test actual connectivity
                health_ok = await self._check_broker_health(broker)

                if health_ok:
                    if broker.status != BrokerStatus.CONNECTED:
                        broker.status = BrokerStatus.CONNECTED
                else:
                    if broker.status == BrokerStatus.CONNECTED:
                        broker.status = BrokerStatus.DEGRADED

                broker.last_heartbeat = datetime.utcnow()

            except Exception as e:
                print(f"Health check failed for {name}: {e}")
                broker.status = BrokerStatus.DISCONNECTED

    async def _check_broker_health(self, broker: BrokerEndpoint) -> bool:
        """
        Check broker health

        Args:
            broker: Broker endpoint to check

        Returns:
            True if healthy, False otherwise
        """
        # Placeholder health check - in real implementation,
        # this would ping the broker API or check connection
        try:
            # Simulate health check
            await asyncio.sleep(0.1)  # Simulate network call
            return True
        except Exception:
            return False

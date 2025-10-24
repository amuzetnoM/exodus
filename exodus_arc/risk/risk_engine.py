# exodus_arc/risk/risk_engine.py
"""
Risk Engine for EXODUS Platform

Implements pre-trade risk controls including position limits, margin checks,
velocity controls, and circuit breakers.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict


class RiskCheck(Enum):
    """Types of risk checks"""
    BUYING_POWER = "buying_power"
    POSITION_LIMIT = "position_limit"
    MARGIN_CHECK = "margin_check"
    VELOCITY_LIMIT = "velocity_limit"
    PRICE_SANITY = "price_sanity"
    CIRCUIT_BREAKER = "circuit_breaker"
    NOTIONAL_LIMIT = "notional_limit"


class RiskResult(Enum):
    """Risk check results"""
    PASS = "pass"
    WARNING = "warning"
    REJECT = "reject"


@dataclass
class RiskViolation:
    """Risk violation details"""
    check: RiskCheck
    result: RiskResult
    message: str
    details: Dict[str, Any]
    timestamp: datetime


class RiskEngine:
    """
    Pre-trade risk management engine

    Performs layered risk checks before order execution:
    1. Buying power / margin checks
    2. Position limits
    3. Velocity controls
    4. Price sanity checks
    5. Circuit breakers
    """

    def __init__(self):
        # Risk limits configuration
        self.limits = {
            RiskCheck.BUYING_POWER: {
                "max_utilization": 0.8,  # 80% of buying power
                "margin_call_threshold": 0.9
            },
            RiskCheck.POSITION_LIMIT: {
                "max_position_size": 100000,  # Max lots per symbol
                "max_total_exposure": 1000000  # Max total notional
            },
            RiskCheck.VELOCITY_LIMIT: {
                "orders_per_minute": 10,
                "orders_per_hour": 100,
                "notional_per_hour": 500000
            },
            RiskCheck.PRICE_SANITY: {
                "max_price_deviation": 0.05,  # 5% from mid price
                "max_spread_multiple": 5.0
            },
            RiskCheck.CIRCUIT_BREAKER: {
                "max_rejections_per_minute": 5,
                "circuit_open_duration": 300  # 5 minutes
            }
        }

        # State tracking
        self.order_history: List[Dict[str, Any]] = []
        self.position_sizes: Dict[str, float] = defaultdict(float)
        self.account_balance = 10000.0  # Default starting balance
        self.margin_used = 0.0
        self.circuit_breaker_active = False
        self.circuit_breaker_until: Optional[datetime] = None

        # Custom risk check functions
        self.custom_checks: List[Callable] = []

    async def check_order(self,
                          order: Dict[str, Any],
                          market_data: Dict[str, Any]) -> List[RiskViolation]:
        """
        Perform comprehensive risk check on order

        Args:
            order: Order dictionary
            market_data: Current market data for symbol

        Returns:
            List of risk violations (empty if all checks pass)
        """
        violations = []

        # Check circuit breaker first
        if self.circuit_breaker_active:
            if datetime.utcnow() < self.circuit_breaker_until:
                violations.append(RiskViolation(
                    check=RiskCheck.CIRCUIT_BREAKER,
                    result=RiskResult.REJECT,
                    message="Circuit breaker active - trading suspended",
                    details={"until": self.circuit_breaker_until.isoformat()},
                    timestamp=datetime.utcnow()
                ))
                return violations
            else:
                # Reset circuit breaker
                self.circuit_breaker_active = False
                self.circuit_breaker_until = None

        # Perform all risk checks
        checks = [
            self._check_buying_power,
            self._check_position_limits,
            self._check_velocity_limits,
            self._check_price_sanity,
            self._check_notional_limits
        ]

        for check_func in checks:
            violation = await check_func(order, market_data)
            if violation:
                violations.append(violation)

                # If any check rejects, stop further checks
                if violation.result == RiskResult.REJECT:
                    break

        # Run custom checks
        for custom_check in self.custom_checks:
            try:
                violation = await custom_check(order, market_data)
                if violation:
                    violations.append(violation)
            except Exception as e:
                # Log custom check errors but don't fail the order
                print(f"Custom risk check error: {e}")

        # Update circuit breaker state based on violations
        self._update_circuit_breaker(violations)

        return violations

    async def _check_buying_power(self,
                                  order: Dict[str, Any],
                                  market_data: Dict[str, Any]) -> Optional[RiskViolation]:
        """
        Check buying power and margin requirements

        Args:
            order: Order to check
            market_data: Market data

        Returns:
            RiskViolation if check fails, None otherwise
        """
        quantity = order["qty"]
        price = order.get("price", market_data.get("mid", 0))

        if price <= 0:
            return RiskViolation(
                check=RiskCheck.BUYING_POWER,
                result=RiskResult.REJECT,
                message="Invalid price for margin calculation",
                details={"price": price},
                timestamp=datetime.utcnow()
            )

        # Calculate required margin (simplified - broker-specific formula)
        notional_value = quantity * price
        required_margin = notional_value * 0.02  # 2% margin requirement

        available_buying_power = self.account_balance - self.margin_used
        utilization_after = ((self.margin_used + required_margin) /
                             self.account_balance)

        limits = self.limits[RiskCheck.BUYING_POWER]

        if utilization_after > limits["max_utilization"]:
            return RiskViolation(
                check=RiskCheck.BUYING_POWER,
                result=RiskResult.REJECT,
                message="Insufficient buying power. "
                        f"Required: ${required_margin:.2f}, "
                        f"Available: ${available_buying_power:.2f}",
                details={
                    "required_margin": required_margin,
                    "available_buying_power": available_buying_power,
                    "utilization_after": utilization_after
                    },
                timestamp=datetime.utcnow()
            )

        if utilization_after > limits["margin_call_threshold"]:
            return RiskViolation(
                check=RiskCheck.BUYING_POWER,
                result=RiskResult.WARNING,
                message=f"High margin utilization: {utilization_after:.1%}",
                details={"utilization": utilization_after},
                timestamp=datetime.utcnow()
            )

        return None

    async def _check_position_limits(self,
                                     order: Dict[str, Any],
                                     market_data: Dict[str, Any]) -> Optional[RiskViolation]:
        """
        Check position size limits

        Args:
            order: Order to check
            market_data: Market data

        Returns:
            RiskViolation if check fails, None otherwise
        """
        symbol = order["symbol"]
        quantity = order["qty"]
        side = order["side"]

        limits = self.limits[RiskCheck.POSITION_LIMIT]

        # Calculate new position size
        current_position = self.position_sizes[symbol]
        if side.lower() == "buy":
            new_position = current_position + quantity
        else:
            new_position = current_position - quantity

        # Check symbol-specific limit
        if abs(new_position) > limits["max_position_size"]:
            return RiskViolation(
                check=RiskCheck.POSITION_LIMIT,
                result=RiskResult.REJECT,
                message="Position limit exceeded for "
                        f"{symbol}. Max: {limits['max_position_size']}, "
                        f"New: {new_position}",
                details={
                    "symbol": symbol,
                    "current_position": current_position,
                    "new_position": new_position,
                    "limit": limits["max_position_size"]
                    },
                timestamp=datetime.utcnow()
            )

        # Check total exposure
        total_exposure = sum(abs(pos) for pos in self.position_sizes.values())
        price = order.get("price", market_data.get("mid", 0))

        if side.lower() == "buy":
            new_total_exposure = total_exposure - (current_position * price) + (new_position * price)
        else:
            new_total_exposure = total_exposure - (abs(current_position) * price) + (abs(new_position) * price)

        if new_total_exposure > limits["max_total_exposure"]:
            return RiskViolation(
                check=RiskCheck.POSITION_LIMIT,
                result=RiskResult.REJECT,
                message="Total exposure limit exceeded. "
                        f"Max: ${limits['max_total_exposure']}, "
                        f"New: ${new_total_exposure}",
                details={
                    "current_exposure": total_exposure,
                    "new_exposure": new_total_exposure,
                    "limit": limits["max_total_exposure"]
                    },
                timestamp=datetime.utcnow()
            )

        return None

    async def _check_velocity_limits(self,
                                     order: Dict[str, Any],
                                     market_data: Dict[str, Any]) -> Optional[RiskViolation]:
        """
        Check order velocity limits

        Args:
            order: Order to check
            market_data: Market data

        Returns:
            RiskViolation if check fails, None otherwise
        """
        now = datetime.utcnow()
        limits = self.limits[RiskCheck.VELOCITY_LIMIT]

        # Count orders in time windows
        one_minute_ago = now - timedelta(minutes=1)
        one_hour_ago = now - timedelta(hours=1)

        recent_orders_minute = [
            o for o in self.order_history
            if o["timestamp"] > one_minute_ago
        ]

        recent_orders_hour = [
            o for o in self.order_history
            if o["timestamp"] > one_hour_ago
        ]

        # Check orders per minute
        if len(recent_orders_minute) >= limits["orders_per_minute"]:
            return RiskViolation(
                check=RiskCheck.VELOCITY_LIMIT,
                result=RiskResult.REJECT,
                message="Order velocity limit exceeded: "
                        f"{len(recent_orders_minute)} orders in last minute",
                details={
                    "orders_last_minute": len(recent_orders_minute),
                    "limit": limits["orders_per_minute"]
                    },
                timestamp=now
            )

        # Check orders per hour
        if len(recent_orders_hour) >= limits["orders_per_hour"]:
            return RiskViolation(
                check=RiskCheck.VELOCITY_LIMIT,
                result=RiskResult.WARNING,
                message="High order frequency: "
                        f"{len(recent_orders_hour)} orders in last hour",
                details={
                    "orders_last_hour": len(recent_orders_hour),
                    "limit": limits["orders_per_hour"]
                },
                timestamp=now
            )

        # Check notional per hour
        notional_last_hour = sum(
            o.get("qty", 0) * o.get("price", 0)
            for o in recent_orders_hour
        )

        if notional_last_hour >= limits["notional_per_hour"]:
            return RiskViolation(
                check=RiskCheck.VELOCITY_LIMIT,
                result=RiskResult.WARNING,
                message="Notional limit approached: "
                        f"${notional_last_hour:.2f} in last hour",
                details={
                    "notional_last_hour": notional_last_hour,
                    "limit": limits["notional_per_hour"]
                    },
                timestamp=now
            )

        return None

    async def _check_price_sanity(self,
                                  order: Dict[str, Any],
                                  market_data: Dict[str, Any]) -> Optional[RiskViolation]:
        """
        Check price sanity and deviation from market

        Args:
            order: Order to check
            market_data: Market data

        Returns:
            RiskViolation if check fails, None otherwise
        """
        price = order.get("price")
        if not price:
            return None  # Market orders skip price sanity check

        limits = self.limits[RiskCheck.PRICE_SANITY]

        mid_price = market_data.get("mid")
        if not mid_price:
            return RiskViolation(
                check=RiskCheck.PRICE_SANITY,
                result=RiskResult.WARNING,
                message="Unable to verify price sanity - no market data available",
                details={"order_price": price},
                timestamp=datetime.utcnow()
            )

        # Check price deviation from mid
        deviation = abs(price - mid_price) / mid_price
        if deviation > limits["max_price_deviation"]:
            return RiskViolation(
                check=RiskCheck.PRICE_SANITY,
                result=RiskResult.REJECT,
                message="Price deviates too far from market: "
                        f"{deviation:.1%} > {limits['max_price_deviation']:.1%}",
                details={
                    "order_price": price,
                    "mid_price": mid_price,
                    "deviation": deviation,
                    "max_deviation": limits["max_price_deviation"]
                },
                timestamp=datetime.utcnow()
            )

        # Check spread
        spread = market_data.get("spread", 0)
        if spread > 0:
            spread_multiple = abs(price - mid_price) / spread
            if spread_multiple > limits["max_spread_multiple"]:
                return RiskViolation(
                    check=RiskCheck.PRICE_SANITY,
                    result=RiskResult.WARNING,
                    message="Price far from mid relative to spread: "
                            f"{spread_multiple:.1f}x spread",
                    details={
                        "spread_multiple": spread_multiple,
                        "max_multiple": limits["max_spread_multiple"]
                        },
                    timestamp=datetime.utcnow()
                )

        return None

    async def _check_notional_limits(self,
                                     order: Dict[str, Any],
                                     market_data: Dict[str, Any]) -> Optional[RiskViolation]:
        """
        Check notional value limits

        Args:
            order: Order to check
            market_data: Market data

        Returns:
            RiskViolation if check fails, None otherwise
        """
        quantity = order["qty"]
        price = order.get("price", market_data.get("mid", 0))

        notional_value = quantity * price
        limits = self.limits[RiskCheck.POSITION_LIMIT]

        if notional_value > limits["max_total_exposure"] * 0.1:  # 10% of total exposure limit
            return RiskViolation(
                check=RiskCheck.NOTIONAL_LIMIT,
                result=RiskResult.WARNING,
                message=f"Large order notional: ${notional_value:,.2f}",
                details={"notional_value": notional_value},
                timestamp=datetime.utcnow()
            )

        return None

    def _update_circuit_breaker(self, violations: List[RiskViolation]):
        """
        Update circuit breaker state based on violations

        Args:
            violations: List of risk violations
        """
        now = datetime.utcnow()
        limits = self.limits[RiskCheck.CIRCUIT_BREAKER]

        # Count rejections in last minute
        one_minute_ago = now - timedelta(minutes=1)
        recent_rejections = [
            v for v in violations
            if v.result == RiskResult.REJECT and v.timestamp > one_minute_ago
        ]

        if len(recent_rejections) >= limits["max_rejections_per_minute"]:
            self.circuit_breaker_active = True
            self.circuit_breaker_until = now + timedelta(seconds=limits["circuit_open_duration"])
            print(f"Circuit breaker activated until {self.circuit_breaker_until}")

    def update_order_history(self, order: Dict[str, Any]):
        """
        Update order history for velocity tracking

        Args:
            order: Completed order
        """
        order_record = {
            "timestamp": datetime.utcnow(),
            "symbol": order["symbol"],
            "qty": order["qty"],
            "price": order.get("price", 0),
            "side": order["side"]
        }
        self.order_history.append(order_record)

        # Keep only last 1000 orders
        if len(self.order_history) > 1000:
            self.order_history = self.order_history[-1000:]

    def update_positions(self, symbol: str, quantity: float, side: str):
        """
        Update position sizes

        Args:
            symbol: Trading symbol
            quantity: Order quantity
            side: Order side
        """
        if side.lower() == "buy":
            self.position_sizes[symbol] += quantity
        else:
            self.position_sizes[symbol] -= quantity

    def update_account_balance(self, balance: float, margin_used: float):
        """
        Update account balance and margin

        Args:
            balance: Account balance
            margin_used: Margin currently used
        """
        self.account_balance = balance
        self.margin_used = margin_used

    def add_custom_check(self, check_func: Callable):
        """
        Add custom risk check function

        Args:
            check_func: Async function that takes (order, market_data) and returns RiskViolation or None
        """
        self.custom_checks.append(check_func)

    def get_risk_metrics(self) -> Dict[str, Any]:
        """
        Get current risk metrics

        Returns:
            Dictionary with risk metrics
        """
        total_exposure = sum(abs(pos) for pos in self.position_sizes.values())
        margin_utilization = self.margin_used / self.account_balance if self.account_balance > 0 else 0

        return {
            "account_balance": self.account_balance,
            "margin_used": self.margin_used,
            "margin_utilization": margin_utilization,
            "total_exposure": total_exposure,
            "position_count": len(self.position_sizes),
            "circuit_breaker_active": self.circuit_breaker_active,
            "orders_last_hour": len([
                o for o in self.order_history
                if o["timestamp"] > datetime.utcnow() - timedelta(hours=1)
            ])
        }

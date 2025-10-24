# exodus_arc/strategy/exodus_arc_strategy.py
"""
Exodus ARC Strategy Implementation

Turtle Trading-inspired strategy with Donchian breakouts, ATR-based position sizing,
and pyramiding logic as specified in the Exodus ARC blueprint.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import statistics
import math


class EntrySignal(Enum):
    """Entry signal types"""
    NONE = "none"
    LONG_SYSTEM1 = "long_system1"
    SHORT_SYSTEM1 = "short_system1"
    LONG_SYSTEM2 = "long_system2"
    SHORT_SYSTEM2 = "short_system2"


class ExitSignal(Enum):
    """Exit signal types"""
    NONE = "none"
    SYSTEM1_EXIT = "system1_exit"
    SYSTEM2_EXIT = "system2_exit"
    STOP_LOSS = "stop_loss"


@dataclass
class DonchianChannel:
    """Donchian channel data structure"""
    high: float
    low: float
    mid: float


@dataclass
class PositionSize:
    """Position sizing calculation result"""
    units: int
    quantity: float
    risk_amount: float
    stop_distance: float


@dataclass
class TradingSignal:
    """Trading signal data structure"""
    signal_type: EntrySignal
    symbol: str
    price: float
    timestamp: datetime
    channel_period: int  # 20 or 55 for system identification


@dataclass
class PositionUnit:
    """Individual position unit tracking"""
    unit_number: int
    entry_price: float
    quantity: float
    entry_time: datetime
    stop_loss: float
    system: int  # 1 or 2


class ExodusArcStrategy:
    """
    Exodus ARC Strategy Implementation

    Based on Turtle Trading principles:
    - System 1: 20-period Donchian channel breakouts
    - System 2: 55-period Donchian channel breakouts
    - Position sizing: 1-2% risk per unit based on ATR
    - Pyramiding: Add units every 0.5 ATR favorable move
    - Stops: 2 ATR initial stop, trailing stops
    - Exits: 10/20-period Donchian channels
    """

    def __init__(self,
                 risk_percent: float = 1.0,
                 max_units: int = 5,
                 system1_period: int = 20,
                 system2_period: int = 55,
                 exit1_period: int = 10,
                 exit2_period: int = 20,
                 atr_period: int = 20,
                 pyramid_threshold: float = 0.5,
                 stop_atr_multiplier: float = 2.0):
        """
        Initialize Exodus ARC strategy

        Args:
            risk_percent: Risk per unit as percentage of account balance
            max_units: Maximum number of units to pyramid
            system1_period: Donchian period for System 1 entries
            system2_period: Donchian period for System 2 entries
            exit1_period: Donchian period for System 1 exits
            exit2_period: Donchian period for System 2 exits
            atr_period: Period for ATR calculation
            pyramid_threshold: ATR multiplier for pyramiding (0.5 = every 0.5 ATR)
            stop_atr_multiplier: ATR multiplier for stop loss (2.0 = 2 ATR stop)
        """
        self.risk_percent = risk_percent
        self.max_units = max_units
        self.system1_period = system1_period
        self.system2_period = system2_period
        self.exit1_period = exit1_period
        self.exit2_period = exit2_period
        self.atr_period = atr_period
        self.pyramid_threshold = pyramid_threshold
        self.stop_atr_multiplier = stop_atr_multiplier

        # Position tracking: symbol -> list of PositionUnit
        self.positions: Dict[str, List[PositionUnit]] = {}

    def calculate_donchian(self, prices: List[float], period: int) -> DonchianChannel:
        """
        Calculate Donchian channel for given period

        Args:
            prices: List of price values (typically closes)
            period: Lookback period

        Returns:
            DonchianChannel with high, low, and mid values
        """
        if len(prices) < period:
            raise ValueError(f"Need at least {period} prices for Donchian calculation, got {len(prices)}")

        # Get the highest high and lowest low over the period
        channel_high = max(prices[-period:])
        channel_low = min(prices[-period:])
        channel_mid = (channel_high + channel_low) / 2

        return DonchianChannel(high=channel_high, low=channel_low, mid=channel_mid)

    def calculate_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int) -> float:
        """
        Calculate Average True Range

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices
            period: ATR period

        Returns:
            ATR value
        """
        if len(highs) < period + 1 or len(lows) < period + 1 or len(closes) < period + 1:
            raise ValueError(f"Need at least {period + 1} periods for ATR calculation")

        tr_values = []

        # Calculate True Range for each period
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],                                    # Current high - current low
                abs(highs[i] - closes[i-1]),                         # Current high - previous close
                abs(lows[i] - closes[i-1])                           # Current low - previous close
            )
            tr_values.append(tr)

        # Return average of last 'period' TR values
        return statistics.mean(tr_values[-period:])

    def calculate_position_size(self, atr: float, account_balance: float, symbol: str) -> PositionSize:
        """
        Calculate position size based on ATR and risk parameters

        Args:
            atr: Current ATR value
            account_balance: Account balance
            symbol: Trading symbol (for pip value calculation)

        Returns:
            PositionSize with calculated values
        """
        # Risk amount per unit
        risk_amount = account_balance * (self.risk_percent / 100.0)

        # Stop distance in price terms (2 ATR)
        stop_distance = atr * self.stop_atr_multiplier

        # Calculate pip value (simplified - would need symbol-specific logic)
        pip_value = self._get_pip_value(symbol)

        # Position size = Risk Amount / (Stop Distance * Pip Value)
        # For forex: quantity in lots
        quantity = risk_amount / (stop_distance * pip_value)

        # Round to standard lot sizes (0.01 lots minimum for forex)
        quantity = max(round(quantity / 0.01) * 0.01, 0.01)

        return PositionSize(
            units=1,
            quantity=quantity,
            risk_amount=risk_amount,
            stop_distance=stop_distance
        )

    def _get_pip_value(self, symbol: str) -> float:
        """
        Get pip value for symbol (simplified implementation)

        In production, this would query broker API or use symbol specifications
        """
        # Simplified pip values for common forex pairs
        pip_values = {
            'EURUSD': 10.0,  # $10 per pip per 10k lot
            'GBPUSD': 10.0,
            'USDJPY': 9.0,   # ¥900 per pip per 10k lot ≈ $9
            'USDCHF': 10.0,
            'AUDUSD': 10.0,
            'USDCAD': 10.0,
        }

        return pip_values.get(symbol, 10.0)  # Default to 10

    def check_entry_signals(self, symbol: str, current_price: float,
                          prices: List[float]) -> Optional[TradingSignal]:
        """
        Check for entry signals using Donchian breakouts

        Args:
            symbol: Trading symbol
            current_price: Current market price
            prices: Historical price data for Donchian calculation

        Returns:
            TradingSignal if entry signal detected, None otherwise
        """
        # Check System 1 (20-period)
        if len(prices) >= self.system1_period:
            dc20 = self.calculate_donchian(prices, self.system1_period)

            if current_price > dc20.high:
                return TradingSignal(
                    signal_type=EntrySignal.LONG_SYSTEM1,
                    symbol=symbol,
                    price=current_price,
                    timestamp=datetime.utcnow(),
                    channel_period=self.system1_period
                )
            elif current_price < dc20.low:
                return TradingSignal(
                    signal_type=EntrySignal.SHORT_SYSTEM1,
                    symbol=symbol,
                    price=current_price,
                    timestamp=datetime.utcnow(),
                    channel_period=self.system1_period
                )

        # Check System 2 (55-period)
        if len(prices) >= self.system2_period:
            dc55 = self.calculate_donchian(prices, self.system2_period)

            if current_price > dc55.high:
                return TradingSignal(
                    signal_type=EntrySignal.LONG_SYSTEM2,
                    symbol=symbol,
                    price=current_price,
                    timestamp=datetime.utcnow(),
                    channel_period=self.system2_period
                )
            elif current_price < dc55.low:
                return TradingSignal(
                    signal_type=EntrySignal.SHORT_SYSTEM2,
                    symbol=symbol,
                    price=current_price,
                    timestamp=datetime.utcnow(),
                    channel_period=self.system2_period
                )

        return None

    def check_exit_signals(self, symbol: str, current_price: float,
                         prices: List[float]) -> ExitSignal:
        """
        Check for exit signals

        Args:
            symbol: Trading symbol
            current_price: Current market price
            prices: Historical price data

        Returns:
            ExitSignal type
        """
        if symbol not in self.positions or not self.positions[symbol]:
            return ExitSignal.NONE

        # Determine position direction from first unit
        first_unit = self.positions[symbol][0]
        is_long = first_unit.entry_price < current_price

        # Check System 1 exit (10-period Donchian)
        if len(prices) >= self.exit1_period:
            dc10 = self.calculate_donchian(prices, self.exit1_period)

            if is_long and current_price <= dc10.low:
                return ExitSignal.SYSTEM1_EXIT
            elif not is_long and current_price >= dc10.high:
                return ExitSignal.SYSTEM1_EXIT

        # Check System 2 exit (20-period Donchian)
        if len(prices) >= self.exit2_period:
            dc20 = self.calculate_donchian(prices, self.exit2_period)

            if is_long and current_price <= dc20.low:
                return ExitSignal.SYSTEM2_EXIT
            elif not is_long and current_price >= dc20.high:
                return ExitSignal.SYSTEM2_EXIT

        # Check stop loss
        for unit in self.positions[symbol]:
            if (is_long and current_price <= unit.stop_loss) or \
               (not is_long and current_price >= unit.stop_loss):
                return ExitSignal.STOP_LOSS

        return ExitSignal.NONE

    def should_add_unit(self, symbol: str, current_price: float, atr: float) -> bool:
        """
        Check if should add another pyramiding unit

        Args:
            symbol: Trading symbol
            current_price: Current market price
            atr: Current ATR value

        Returns:
            True if should add unit
        """
        if symbol not in self.positions or not self.positions[symbol]:
            return False

        if len(self.positions[symbol]) >= self.max_units:
            return False

        # Get most recent unit
        last_unit = self.positions[symbol][-1]
        is_long = last_unit.entry_price < current_price

        # Calculate price distance from first unit entry
        first_unit = self.positions[symbol][0]
        distance = abs(current_price - first_unit.entry_price)

        # Check if distance exceeds pyramid threshold
        threshold = atr * self.pyramid_threshold

        return distance >= threshold

    def calculate_pyramid_size(self, atr: float, account_balance: float, symbol: str) -> PositionSize:
        """
        Calculate size for pyramiding unit

        Uses same logic as initial position sizing
        """
        return self.calculate_position_size(atr, account_balance, symbol)

    def generate_entry_order(self, signal: TradingSignal, position_size: PositionSize) -> Dict:
        """
        Generate order dictionary from trading signal

        Args:
            signal: Trading signal
            position_size: Calculated position size

        Returns:
            Order dictionary for submission to orchestrator
        """
        # Determine side from signal type
        side = "buy" if "long" in signal.signal_type.value else "sell"

        # Generate unique client order ID
        client_order_id = f"exodus_arc_{signal.signal_type.value}_{signal.symbol}_{signal.timestamp.strftime('%Y%m%d_%H%M%S')}"

        return {
            "clientOrderId": client_order_id,
            "clientId": "exodus_arc_strategy",
            "symbol": signal.symbol,
            "qty": position_size.quantity,
            "price": signal.price,
            "side": side,
            "strategy": "exodus_arc",
            "signal_type": signal.signal_type.value,
            "channel_period": signal.channel_period
        }

    def generate_exit_order(self, symbol: str, exit_signal: ExitSignal) -> Dict:
        """
        Generate exit order for position

        Args:
            symbol: Trading symbol
            exit_signal: Type of exit signal

        Returns:
            Order dictionary for position closure
        """
        if symbol not in self.positions or not self.positions[symbol]:
            raise ValueError(f"No position found for symbol {symbol}")

        # Calculate total position size
        total_quantity = sum(unit.quantity for unit in self.positions[symbol])

        # Determine side (opposite of position direction)
        first_unit = self.positions[symbol][0]
        # Assume we can get current price from market data
        # In production, this would be passed as parameter
        side = "sell" if first_unit.entry_price < 0 else "buy"  # Placeholder logic

        client_order_id = f"exodus_arc_exit_{exit_signal.value}_{symbol}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        return {
            "clientOrderId": client_order_id,
            "clientId": "exodus_arc_strategy",
            "symbol": symbol,
            "qty": total_quantity,
            "price": 0,  # Market order
            "side": side,
            "strategy": "exodus_arc",
            "exit_type": exit_signal.value
        }

    def update_position_tracking(self, symbol: str, order: Dict, execution_result: Dict):
        """
        Update position tracking after order execution

        Args:
            symbol: Trading symbol
            order: Original order dictionary
            execution_result: Execution result from broker
        """
        if symbol not in self.positions:
            self.positions[symbol] = []

        # Determine system from signal type
        system = 1 if "system1" in order.get("signal_type", "").lower() else 2

        # Calculate stop loss
        entry_price = execution_result.get("price", order["price"])
        # In production, ATR would be calculated and passed
        atr = 0.005  # Placeholder
        stop_distance = atr * self.stop_atr_multiplier

        is_long = order["side"] == "buy"
        stop_loss = entry_price - stop_distance if is_long else entry_price + stop_distance

        unit = PositionUnit(
            unit_number=len(self.positions[symbol]) + 1,
            entry_price=entry_price,
            quantity=order["qty"],
            entry_time=datetime.utcnow(),
            stop_loss=stop_loss,
            system=system
        )

        self.positions[symbol].append(unit)

    def close_position(self, symbol: str):
        """
        Close all units for a symbol

        Args:
            symbol: Trading symbol
        """
        if symbol in self.positions:
            self.positions[symbol].clear()

    def get_position_summary(self, symbol: str) -> Dict:
        """
        Get summary of current position for symbol

        Args:
            symbol: Trading symbol

        Returns:
            Position summary dictionary
        """
        if symbol not in self.positions or not self.positions[symbol]:
            return {
                "units": 0,
                "total_quantity": 0.0,
                "avg_entry_price": 0.0,
                "unrealized_pnl": 0.0,
                "direction": None
            }

        units = self.positions[symbol]
        total_quantity = sum(unit.quantity for unit in units)
        total_value = sum(unit.entry_price * unit.quantity for unit in units)
        avg_entry_price = total_value / total_quantity

        # Determine direction from first unit
        first_unit = units[0]
        direction = "long" if first_unit.entry_price > 0 else "short"  # Placeholder logic

        return {
            "units": len(units),
            "total_quantity": total_quantity,
            "avg_entry_price": avg_entry_price,
            "unrealized_pnl": 0.0,  # Would calculate from current price
            "direction": direction
        }

    def get_strategy_metrics(self) -> Dict:
        """
        Get strategy performance metrics

        Returns:
            Dictionary with strategy metrics
        """
        total_positions = sum(len(units) for units in self.positions.values())
        active_symbols = len([s for s, units in self.positions.items() if units])

        return {
            "total_positions": total_positions,
            "active_symbols": active_symbols,
            "max_units_per_symbol": self.max_units,
            "risk_percent": self.risk_percent,
            "system1_period": self.system1_period,
            "system2_period": self.system2_period
        }

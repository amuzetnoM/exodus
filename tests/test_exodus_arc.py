# tests/test_exodus_arc.py
"""
Comprehensive test suite for EXODUS ARC platform components
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

# Import components to test
from exodus_arc import (
    ExodusArcStrategy,
    XMMT5Adapter,
    RiskEngine,
    ReconciliationService,
    MetricsCollector,
    AlertManager,
    OrderRouter,
    RoutingStrategy
)


class TestExodusArcStrategy:
    """Test Exodus ARC strategy implementation"""

    def setup_method(self):
        self.strategy = ExodusArcStrategy()

    def test_calculate_donchian(self):
        """Test Donchian channel calculation"""
        # Sample price data
        prices = [100.0, 102.0, 98.0, 105.0, 103.0, 107.0, 99.0, 101.0,
                 106.0, 104.0, 108.0, 102.0, 109.0, 107.0, 111.0, 105.0,
                 110.0, 108.0, 112.0, 106.0]

        donchian = self.strategy.calculate_donchian(prices, period=20)

        assert donchian.high == max(prices)
        assert donchian.low == min(prices)
        assert donchian.mid == (max(prices) + min(prices)) / 2

    def test_calculate_atr(self):
        """Test ATR calculation"""
        # Sample OHLC data
        highs = [102.0, 105.0, 107.0, 106.0, 109.0, 111.0,
                 110.0, 113.0, 112.0, 115.0]
        lows = [98.0, 99.0, 101.0, 102.0, 103.0, 105.0,
                106.0, 107.0, 108.0, 109.0]
        closes = [100.0, 103.0, 105.0, 104.0, 107.0, 109.0,
                  108.0, 111.0, 110.0, 113.0]

        atr = self.strategy.calculate_atr(highs, lows, closes, period=10)

        assert atr > 0
        assert isinstance(atr, float)

    def test_check_entry_signals(self):
        """Test entry signal generation"""
        # Sample price data
        prices = [1.0950, 1.0960, 1.0940, 1.0970, 1.0955, 1.0980,
                  1.0930, 1.0960, 1.0975, 1.0945, 1.0985, 1.0940,
                  1.0990, 1.0970, 1.1000, 1.0950, 1.0995, 1.0975,
                  1.1010, 1.0960, 1.1020]  # 21 prices for 20-period

        # Test with price above 20-period high
        signal = self.strategy.check_entry_signals('EURUSD', 1.1025, prices)
        assert signal is not None
        assert signal.symbol == 'EURUSD'

    def test_generate_entry_order(self):
        """Test order generation"""
        from exodus_arc.strategy.exodus_arc_strategy import (
            TradingSignal, PositionSize, EntrySignal
        )
        from datetime import timezone

        signal = TradingSignal(
            signal_type=EntrySignal.LONG_SYSTEM1,
            symbol='EURUSD',
            price=1.1000,
            timestamp=datetime.now(timezone.utc),
            channel_period=20
        )

        position_size = PositionSize(
            units=1,
            quantity=0.1,
            risk_amount=100.0,
            stop_distance=0.0020
        )

        order = self.strategy.generate_entry_order(signal, position_size)

        assert order['symbol'] == 'EURUSD'
        assert order['side'] == 'buy'
        assert order['quantity'] == 0.1
        assert 'stop_loss' in order
        assert 'take_profit' in order


class TestXMMT5Adapter:
    """Test XM MT5 adapter"""

    def setup_method(self):
        self.adapter = XMMT5Adapter(
            broker_url="https://test.xmtrading.com",
            api_key="test-key",
            api_secret="test-secret",
            account_id="test-account"
        )

    @pytest.mark.asyncio
    async def test_submit_order(self):
        """Test order submission"""
        order = {
            'id': 'test-123',
            'symbol': 'EURUSD',
            'qty': 1000,
            'price': 1.1000,
            'side': 'buy',
            'type': 'market'
        }

        # Mock successful response
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'status': 'accepted',
                'broker_order_id': 'XM-12345'
            }
            mock_post.return_value = mock_response

            result = await self.adapter.submit_order(order)

            assert result.status == 'accepted'
            assert result.broker_order_id == 'XM-12345'

    @pytest.mark.asyncio
    async def test_cancel_order(self):
        """Test order cancellation"""
        order_id = 'test-123'

        with patch('httpx.AsyncClient.delete') as mock_delete:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'cancelled'}
            mock_delete.return_value = mock_response

            result = await self.adapter.cancel_order(order_id)

            assert result is True


class TestRiskEngine:
    """Test risk management engine"""

    def setup_method(self):
        self.risk_engine = RiskEngine()

    @pytest.mark.asyncio
    async def test_check_order_approved(self):
        """Test order approval"""
        order = {
            'id': 'test-123',
            'symbol': 'EURUSD',
            'qty': 1000,
            'price': 1.1000,
            'side': 'buy'
        }

        result = await self.risk_engine.check_order(order)

        assert 'approved' in result
        assert 'reason' in result

    @pytest.mark.asyncio
    async def test_buying_power_check(self):
        """Test buying power validation"""
        # This would test the buying power calculation
        # Implementation depends on account balance tracking
        pass

    @pytest.mark.asyncio
    async def test_position_limits(self):
        """Test position size limits"""
        # Test position limit enforcement
        pass


class TestReconciliationService:
    """Test reconciliation service"""

    def setup_method(self):
        self.reconciliation = ReconciliationService()

    def test_record_order(self):
        """Test order recording"""
        order_id = 'test-123'
        order_data = {'symbol': 'EURUSD', 'qty': 1000}
        broker = 'xm_mt5'

        self.reconciliation.record_order(order_id, order_data, broker)

        # Check that order was recorded
        assert order_id in self.reconciliation.pending_orders

    def test_record_fill(self):
        """Test fill recording and matching"""
        order_id = 'test-123'
        fill_data = {
            'order_id': order_id,
            'qty': 1000,
            'price': 1.1000,
            'timestamp': datetime.utcnow()
        }

        self.reconciliation.record_fill(order_id, fill_data)

        # Check reconciliation
        assert order_id in self.reconciliation.reconciled_orders


class TestMetricsCollector:
    """Test metrics collection"""

    def setup_method(self):
        self.metrics = MetricsCollector()

    def test_record_order_processed(self):
        """Test order processing metrics"""
        order_id = 'test-123'
        broker = 'xm_mt5'

        self.metrics.record_order_processed(order_id, broker)

        # Check metrics were recorded
        prometheus_output = self.metrics.get_prometheus_metrics()
        assert 'order_processed_total' in prometheus_output

    def test_record_order_failed(self):
        """Test order failure metrics"""
        order_id = 'test-123'
        broker = 'xm_mt5'
        error = 'connection_failed'

        self.metrics.record_order_failed(order_id, broker, error)

        prometheus_output = self.metrics.get_prometheus_metrics()
        assert 'order_failed_total' in prometheus_output


class TestOrderRouter:
    """Test order routing system"""

    def setup_method(self):
        self.router = OrderRouter()

        # Register test brokers
        mock_adapter1 = Mock()
        mock_adapter2 = Mock()

        self.router.register_broker(
            name='broker1',
            adapter=mock_adapter1,
            priority=1,
            max_concurrent=10,
            capabilities=['forex', 'limit_orders']
        )

        self.router.register_broker(
            name='broker2',
            adapter=mock_adapter2,
            priority=2,
            max_concurrent=10,
            capabilities=['forex', 'equities']
        )

    @pytest.mark.asyncio
    async def test_route_order(self):
        """Test order routing"""
        order = {
            'id': 'test-123',
            'symbol': 'EURUSD',
            'qty': 1000,
            'price': 1.1000,
            'side': 'buy',
            'type': 'market'
        }

        broker = await self.router.route_order(order)

        assert broker in ['broker1', 'broker2']

    def test_least_loaded_routing(self):
        """Test least loaded routing strategy"""
        self.router.set_routing_strategy(RoutingStrategy.LEAST_LOADED)

        # Both brokers should have 0 load initially
        available = ['broker1', 'broker2']
        selected = self.router._select_broker(available, {})

        # Should select first broker (arbitrary but deterministic)
        assert selected in available

    def test_round_robin_routing(self):
        """Test round-robin routing strategy"""
        self.router.set_routing_strategy(RoutingStrategy.ROUND_ROBIN)

        available = ['broker1', 'broker2']

        # First selection
        selected1 = self.router._select_broker(available, {})
        # Second selection
        selected2 = self.router._select_broker(available, {})

        assert selected1 != selected2
        assert selected1 in available
        assert selected2 in available

    def test_routing_stats(self):
        """Test routing statistics"""
        stats = self.router.get_routing_stats()

        assert 'total_routes' in stats
        assert 'broker_usage' in stats
        assert 'strategy_usage' in stats

    def test_broker_status(self):
        """Test broker status reporting"""
        status = self.router.get_broker_status()

        assert 'broker1' in status
        assert 'broker2' in status

        broker1_status = status['broker1']
        assert 'status' in broker1_status
        assert 'current_load' in broker1_status
        assert 'load_percentage' in broker1_status


class TestAlertManager:
    """Test alert management system"""

    def setup_method(self):
        self.alerts = AlertManager()

    def test_trigger_alert(self):
        """Test alert triggering"""
        alert_type = 'test_alert'
        data = {'message': 'Test alert'}

        self.alerts.trigger_alert(alert_type, data)

        active_alerts = self.alerts.get_active_alerts()
        assert len(active_alerts) > 0

    def test_alert_rules(self):
        """Test alert rule evaluation"""
        # Test default rules are loaded
        assert len(self.alerts.alert_rules) > 0

    def test_resolve_alert(self):
        """Test alert resolution"""
        alert_id = 'test-alert-123'

        # Mock an active alert
        self.alerts.active_alerts[alert_id] = {
            'id': alert_id,
            'type': 'test',
            'timestamp': datetime.utcnow(),
            'data': {}
        }

        self.alerts.resolve_alert(alert_id)

        assert alert_id not in self.alerts.active_alerts


# Integration Tests
class TestIntegration:
    """Integration tests for component interaction"""

    @pytest.mark.asyncio
    async def test_full_order_flow(self):
        """Test complete order processing flow"""
        # This would test the full pipeline from order submission
        # through strategy, risk, routing, and execution
        pass

    @pytest.mark.asyncio
    async def test_strategy_with_adapter(self):
        """Test strategy integration with broker adapter"""
        # Test strategy signals driving actual order submission
        pass


if __name__ == '__main__':
    pytest.main([__file__])

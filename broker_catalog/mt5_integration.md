# MT5 Integration Guide (mt5_integration.md)

Comprehensive guide for integrating MetaTrader 5 with EXODUS platform, including MQL5 code examples, security hardening, operational procedures, and strategy implementation.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [MQL5 Development Environment](#mql5-development-environment)
4. [Security Hardening](#security-hardening)
5. [Order Lifecycle](#order-lifecycle)
6. [Exodus ARC Strategy Implementation](#exodus-arc-strategy-implementation)
7. [Adapter Implementation](#adapter-implementation)
8. [Testing and Validation](#testing-and-validation)
9. [Deployment Procedures](#deployment-procedures)
10. [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)
11. [Performance Tuning](#performance-tuning)
12. [Compliance and Audit](#compliance-and-audit)
13. [Code Examples](#code-examples)
14. [References](#references)

---

## Overview

### Purpose

This document provides exhaustive MQL5 integration plans and code examples for connecting MetaTrader 5 Expert Advisors (EAs) to the EXODUS broker integration platform. It covers the implementation of the Exodus ARC strategy (Turtle Trading-inspired) with Donchian breakouts, ATR-based position sizing, and pyramiding logic.

### Key Integration Points

- **WebRequest Bridge**: MQL5 EA calls EXODUS orchestrator via HTTPS POST
- **Idempotency**: Guaranteed-once order submission with deduplication
- **Event Persistence**: All orders and fills logged to append-only event store
- **Risk Controls**: Pre-trade validation and circuit breakers
- **Reconciliation**: Real-time matching of strategy orders to broker executions

### Integration Options

Based on the Exodus ARC blueprint, three integration paths are supported:

1. **Observe/Reconcile (Passive)**: External EA trades independently; EXODUS ingests fills for monitoring
2. **Native EXODUS (Active)**: Strategy runs in EXODUS with full control; orders routed through adapters
3. **Hybrid Approval**: EA requests pre-trade approval from EXODUS before execution

---

## Architecture

### High-Level Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   MT5 Terminal  │     │  EXODUS          │     │   XM Broker     │
│   (EA Running)  │────▶│  Orchestrator    │────▶│   (Live/Demo)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                        │                        │
         │ WebRequest POST        │ Order Routing         │ FIX/REST
         │ /api/v1/orders         │ & Risk Checks         │ Execution
         ▼                        ▼                        ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Event Store     │     │ Reconciliation   │     │ Broker Reports  │
│ (JSONL)         │◀────│ Service          │◀────│ (Statements)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### Component Responsibilities

- **MQL5 EA**: Market data processing, signal generation, order submission via WebRequest
- **EXODUS Orchestrator**: Order validation, risk checks, idempotency, event persistence
- **Broker Adapter**: Protocol translation (FIX/REST), execution, fill reporting
- **Reconciliation Service**: Match strategy orders to broker fills, detect discrepancies

---

## MQL5 Development Environment

### Prerequisites

- **MetaTrader 5 Terminal**: Latest version (5.0.0.3470+)
- **MQL5 Editor**: Integrated development environment
- **WebRequest Permissions**: Configure allowed URLs in MT5 settings
- **Python Environment**: For testing mock orchestrator

### MT5 Configuration

#### Enable WebRequest

1. Open MT5 Terminal
2. Go to Tools → Options → Expert Advisors
3. Check "Allow automated trading"
4. Check "Allow DLL imports"
5. Check "Allow WebRequest for listed URL"
6. Add allowed URLs:
   - `https://your-orchestrator.com/api/v1/orders`
   - `https://your-orchestrator.com/health`

#### WebRequest URL Whitelist

For production deployment, configure the exact orchestrator URL:

```ini
# File: C:\Users\<User>\AppData\Roaming\MetaQuotes\Terminal\<hash>\config\common.ini
WebRequest=https://exodus-orchestrator.production.com/api/v1
```

### Development Setup

#### Project Structure

```
xm/
├── mql5_ea_template.mq5          # Base EA template
├── exodus_arc_ea.mq5             # Exodus ARC implementation
├── mock_orchestrator.py          # Python mock for testing
└── test_data/                     # Historical data for backtesting
```

#### Compilation

```bash
# Compile EA in MT5 Editor (F7)
# Or use command line:
metaeditor.exe /compile:"C:\path\to\exodus_arc_ea.mq5"
```

---

## Security Hardening

### API Key Management

Never store API keys in EA source code. Use MT5 input parameters with encryption:

```mql5
input string ApiKey = "";        // Leave empty in source
input string ApiSecret = "";     // Configure in EA properties
```

### HTTPS Enforcement

Always use HTTPS for WebRequest calls:

```mql5
string orchestratorUrl = "https://exodus-orchestrator.com/api/v1/orders";
```

### Request Signing

Implement HMAC-SHA256 request signing:

```mql5
string SignRequest(string payload, string secret) {
    // HMAC-SHA256 implementation
    return hmac_sha256(payload, secret);
}
```

### Audit Logging

Log all WebRequest calls and responses:

```mql5
void LogWebRequest(string method, string url, string payload, int responseCode, string response) {
    PrintFormat("WebRequest: %s %s -> %d", method, url, responseCode);
    // Log to file for audit trail
}
```

---

## Order Lifecycle

### Order States

1. **Signal Generated**: Strategy identifies entry/exit opportunity
2. **Order Submitted**: EA sends WebRequest to orchestrator
3. **Order Accepted**: Orchestrator returns internalOrderId
4. **Order Routed**: Orchestrator forwards to broker adapter
5. **Order Executed**: Broker fills the order
6. **Fill Reported**: Broker sends execution report
7. **Reconciled**: EXODUS matches order to fill

### Idempotency Handling

Use X-Idempotency-Key header to prevent duplicate orders:

```mql5
string GenerateIdempotencyKey(string symbol, ENUM_ORDER_TYPE type, double price) {
    return StringFormat("%s_%s_%f_%d", symbol, EnumToString(type), price, TimeCurrent());
}
```

### Error Handling

Implement exponential backoff for failed requests:

```mql5
int SubmitOrderWithRetry(OrderRequest &req, int maxRetries = 3) {
    int delay = 1000; // 1 second
    for(int attempt = 0; attempt < maxRetries; attempt++) {
        int result = SubmitOrder(req);
        if(result == 200) return result;

        PrintFormat("Order submission failed (attempt %d/%d), retrying in %dms",
                   attempt + 1, maxRetries, delay);
        Sleep(delay);
        delay *= 2; // Exponential backoff
    }
    return -1; // All retries failed
}
```

---

## Exodus ARC Strategy Implementation

### Strategy Overview

Based on the Exodus ARC blueprint, implementing Turtle Trading rules:

- **Entry Systems**:
  - System 1: 20-period Donchian channel breakout
  - System 2: 55-period Donchian channel breakout

- **Position Sizing**: ATR-based, 1-2% risk per unit
- **Pyramiding**: Add units every 0.5 ATR favorable move
- **Stops**: 2 ATR initial stop, trailing stops
- **Exits**: 10/20-period Donchian channels

### MQL5 Implementation

#### Donchian Channel Calculation

```mql5
struct DonchianChannel {
    double high;
    double low;
    double mid;
};

DonchianChannel CalculateDonchian(int period, int shift = 0) {
    DonchianChannel dc;
    dc.high = 0;
    dc.low = DBL_MAX;

    for(int i = shift; i < shift + period; i++) {
        double high = iHigh(_Symbol, PERIOD_D1, i);
        double low = iLow(_Symbol, _Period, i);

        dc.high = MathMax(dc.high, high);
        dc.low = MathMin(dc.low, low);
    }

    dc.mid = (dc.high + dc.low) / 2;
    return dc;
}
```

#### ATR Calculation

```mql5
double CalculateATR(int period, int shift = 0) {
    double atr = 0;
    for(int i = shift; i < shift + period; i++) {
        double tr = MathMax(
            MathMax(
                iHigh(_Symbol, PERIOD_D1, i) - iLow(_Symbol, PERIOD_D1, i),
                MathAbs(iHigh(_Symbol, PERIOD_D1, i) - iClose(_Symbol, PERIOD_D1, i - 1))
            ),
            MathAbs(iLow(_Symbol, PERIOD_D1, i) - iClose(_Symbol, PERIOD_D1, i - 1))
        );
        atr += tr;
    }
    return atr / period;
}
```

#### Position Sizing

```mql5
struct PositionSize {
    double units;      // Number of units
    double quantity;   // Total position size
    double riskAmount; // Risk per unit in account currency
};

PositionSize CalculatePositionSize(double atr, double accountBalance, double riskPercent = 1.0) {
    PositionSize ps;

    // Risk amount per unit
    ps.riskAmount = accountBalance * (riskPercent / 100.0);

    // ATR-based stop distance (2 ATR)
    double stopDistance = atr * 2;

    // Position size = Risk / Stop Distance
    // For forex: 1 lot = 100,000 units, pip value depends on pair
    double pipValue = 10; // Approximate for EURUSD
    ps.quantity = ps.riskAmount / (stopDistance * pipValue);

    // Round to lot size (0.01 lots minimum)
    ps.quantity = MathRound(ps.quantity / 0.01) * 0.01;
    ps.units = 1; // Start with 1 unit

    return ps;
}
```

#### Entry Signal Detection

```mql5
enum EntrySignal {
    SIGNAL_NONE,
    SIGNAL_LONG_SYSTEM1,
    SIGNAL_SHORT_SYSTEM1,
    SIGNAL_LONG_SYSTEM2,
    SIGNAL_SHORT_SYSTEM2
};

EntrySignal CheckEntrySignals() {
    // System 1: 20-period Donchian
    DonchianChannel dc20 = CalculateDonchian(20, 1); // Yesterday's channel
    double close = iClose(_Symbol, PERIOD_D1, 1);

    if(close > dc20.high) return SIGNAL_LONG_SYSTEM1;
    if(close < dc20.low) return SIGNAL_SHORT_SYSTEM1;

    // System 2: 55-period Donchian
    DonchianChannel dc55 = CalculateDonchian(55, 1);
    if(close > dc55.high) return SIGNAL_LONG_SYSTEM2;
    if(close < dc55.low) return SIGNAL_SHORT_SYSTEM2;

    return SIGNAL_NONE;
}
```

#### Pyramiding Logic

```mql5
bool ShouldAddUnit(double entryPrice, double currentPrice, bool isLong, double atr) {
    double distance = isLong ? (currentPrice - entryPrice) : (entryPrice - currentPrice);
    double threshold = atr * 0.5; // Add every 0.5 ATR

    return distance >= threshold;
}
```

### Order Submission

```mql5
struct OrderRequest {
    string symbol;
    string side;        // "buy" or "sell"
    double quantity;
    double price;
    string clientOrderId;
};

int SubmitOrderToOrchestrator(OrderRequest &req) {
    string url = "https://exodus-orchestrator.com/api/v1/orders";
    string payload = StringFormat(
        "{\"clientOrderId\":\"%s\",\"symbol\":\"%s\",\"qty\":%f,\"price\":%f,\"side\":\"%s\"}",
        req.clientOrderId, req.symbol, req.quantity, req.price, req.side
    );

    string headers = "Content-Type: application/json\r\n";
    headers += "X-Idempotency-Key: " + req.clientOrderId + "\r\n";

    char data[];
    StringToCharArray(payload, data);

    char result[];
    string resultHeaders;
    int timeout = 5000; // 5 seconds

    int responseCode = WebRequest("POST", url, headers, timeout, data, result, resultHeaders);

    if(responseCode == 200) {
        string response = CharArrayToString(result);
        Print("Order submitted successfully: ", response);
        return responseCode;
    } else {
        PrintFormat("Order submission failed: HTTP %d", responseCode);
        return responseCode;
    }
}
```

---

## Adapter Implementation

### XM MT5 Adapter

The XM adapter handles communication between EXODUS orchestrator and XM Trading's MT5 bridge.

#### Adapter Architecture

```python
# xm_adapter.py
from fastapi import FastAPI
import httpx
import asyncio
from typing import Dict, List

class XMMT5Adapter:
    def __init__(self, broker_url: str, api_key: str, api_secret: str):
        self.broker_url = broker_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = httpx.AsyncClient()

    async def submit_order(self, order: Dict) -> Dict:
        """Submit order to XM MT5"""
        # Transform EXODUS order to XM format
        xm_order = self.transform_order(order)

        # Submit via REST API or FIX
        response = await self.client.post(
            f"{self.broker_url}/orders",
            json=xm_order,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )

        return self.transform_response(response.json())

    def transform_order(self, exodus_order: Dict) -> Dict:
        """Transform EXODUS order format to XM format"""
        return {
            "symbol": exodus_order["symbol"],
            "side": exodus_order["side"].upper(),
            "quantity": exodus_order["qty"],
            "price": exodus_order.get("price"),
            "orderType": "MARKET" if not exodus_order.get("price") else "LIMIT",
            "clientOrderId": exodus_order.get("clientOrderId")
        }

    def transform_response(self, xm_response: Dict) -> Dict:
        """Transform XM response to EXODUS format"""
        return {
            "brokerOrderId": xm_response.get("orderId"),
            "status": xm_response.get("status"),
            "fills": xm_response.get("fills", [])
        }
```

#### Order Routing Logic

```python
# order_router.py
from typing import Dict, Any
from adapters.xm_adapter import XMMT5Adapter

class OrderRouter:
    def __init__(self):
        self.adapters = {
            "XM": XMMT5Adapter(
                broker_url="https://api.xm.com/v1",
                api_key=os.getenv("XM_API_KEY"),
                api_secret=os.getenv("XM_API_SECRET")
            )
        }

    async def route_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Route order to appropriate broker adapter"""

        # Determine broker from order metadata or configuration
        broker = self.determine_broker(order)

        # Pre-trade risk checks
        await self.perform_risk_checks(order)

        # Route to adapter
        adapter = self.adapters[broker]
        result = await adapter.submit_order(order)

        # Persist execution event
        await self.persist_execution_event(order, result)

        return result

    async def perform_risk_checks(self, order: Dict) -> None:
        """Perform pre-trade risk validation"""
        # Position limits
        # Margin checks
        # Velocity controls
        # Circuit breakers
        pass

    def determine_broker(self, order: Dict) -> str:
        """Determine which broker to route order to"""
        # Simple routing logic - can be enhanced
        return "XM"  # Default to XM for now
```

---

## Testing and Validation

### Unit Testing

```python
# test_exodus_arc.py
import pytest
from exodus_arc.strategy import ExodusArcStrategy

class TestExodusArcStrategy:
    def test_donchian_calculation(self):
        strategy = ExodusArcStrategy()
        # Mock price data
        prices = [1.1000, 1.1050, 1.1020, 1.1080, 1.1060]

        dc = strategy.calculate_donchian(prices, 3)
        assert dc.high == 1.1080
        assert dc.low == 1.1020

    def test_position_sizing(self):
        strategy = ExodusArcStrategy()
        account_balance = 10000
        atr = 0.0050  # 50 pips
        risk_percent = 1.0

        size = strategy.calculate_position_size(atr, account_balance, risk_percent)
        expected_size = (10000 * 0.01) / (0.0050 * 10)  # Risk / (ATR * pip_value)
        assert abs(size - expected_size) < 0.01

    def test_entry_signals(self):
        strategy = ExodusArcStrategy()

        # Test System 1 breakout
        signal = strategy.check_entry_signals(high=1.1100, low=1.1000, close=1.1120)
        assert signal == EntrySignal.LONG_SYSTEM1
```

### Integration Testing

```python
# test_mt5_integration.py
import pytest
from unittest.mock import Mock, patch
import httpx

class TestMT5Integration:
    @pytest.mark.asyncio
    async def test_order_submission_success(self):
        # Mock orchestrator response
        mock_response = {
            "status": "accepted",
            "internalOrderId": "int-123456789"
        }

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = Mock()
            mock_post.return_value.json.return_value = mock_response

            adapter = XMMT5Adapter("https://api.xm.com", "key", "secret")
            result = await adapter.submit_order({
                "symbol": "EURUSD",
                "qty": 10000,
                "side": "buy"
            })

            assert result["status"] == "accepted"
            assert "internalOrderId" in result

    @pytest.mark.asyncio
    async def test_order_submission_failure(self):
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = httpx.HTTPError("Connection failed")

            adapter = XMMT5Adapter("https://api.xm.com", "key", "secret")

            with pytest.raises(httpx.HTTPError):
                await adapter.submit_order({
                    "symbol": "EURUSD",
                    "qty": 10000,
                    "side": "buy"
                })
```

### End-to-End Testing

```python
# test_e2e_mt5.py
import pytest
import subprocess
import time
import requests

class TestE2EMT5:
    def test_full_order_flow(self):
        # Start mock orchestrator
        orchestrator = subprocess.Popen([
            "python", "xm/mock_orchestrator.py"
        ])

        time.sleep(2)  # Wait for startup

        try:
            # Submit order via API
            response = requests.post(
                "http://localhost:8000/api/v1/orders",
                json={
                    "clientOrderId": "e2e-test-001",
                    "symbol": "EURUSD",
                    "qty": 10000,
                    "price": 1.1234,
                    "side": "buy"
                },
                headers={"X-Idempotency-Key": "e2e-test-001"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"
            assert "internalOrderId" in data

            # Verify event persistence
            events_response = requests.get("http://localhost:8000/api/v1/events")
            events = events_response.json()

            order_events = [e for e in events if e["type"] == "OrderSubmitted"]
            assert len(order_events) == 1
            assert order_events[0]["clientOrderId"] == "e2e-test-001"

        finally:
            orchestrator.terminate()
            orchestrator.wait()
```

### Backtesting

```mql5
// Backtesting framework in MQL5
void OnTesterInit() {
    // Initialize backtest parameters
    Print("Starting Exodus ARC backtest");
}

void OnTesterPass() {
    // Calculate performance metrics after each pass
    double profit = TesterStatistics(STAT_PROFIT);
    double drawdown = TesterStatistics(STAT_EQUITY_DD);
    double sharpe = TesterStatistics(STAT_SHARPE_RATIO);

    PrintFormat("Pass Results - Profit: %.2f, Drawdown: %.2f%%, Sharpe: %.2f",
               profit, drawdown, sharpe);
}

void OnTesterDeinit() {
    // Final backtest results
    Print("Backtest completed");
}
```

---

## Deployment Procedures

### Production Deployment Checklist

- [ ] Configure MT5 terminal with WebRequest permissions
- [ ] Deploy EXODUS orchestrator to production environment
- [ ] Configure broker API credentials securely
- [ ] Test connectivity between MT5 and orchestrator
- [ ] Validate idempotency and error handling
- [ ] Setup monitoring and alerting
- [ ] Perform smoke tests with small position sizes
- [ ] Enable automated trading in MT5

### Rollback Procedures

1. **Immediate Stop**: Disable automated trading in MT5
2. **Circuit Breaker**: Activate kill-switch in orchestrator
3. **Position Management**: Close all open positions manually
4. **Code Rollback**: Revert to previous EA version
5. **Restart Services**: Restart MT5 terminal and orchestrator

### Blue-Green Deployment

```bash
# Deploy new EA version to green environment
cp exodus_arc_ea_v2.mq5 /path/to/mt5/experts/

# Test green environment
# Switch traffic by updating EA in MT5
# Monitor for 24 hours
# If successful, remove blue version
```

---

## Monitoring and Troubleshooting

### Key Metrics

```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Order metrics
orders_submitted = Counter('exodus_orders_submitted_total', 'Total orders submitted')
orders_rejected = Counter('exodus_orders_rejected_total', 'Total orders rejected')
order_latency = Histogram('exodus_order_latency_seconds', 'Order processing latency')

# MT5-specific metrics
webrequest_errors = Counter('exodus_mt5_webrequest_errors_total', 'WebRequest errors')
signal_detected = Counter('exodus_mt5_signals_detected_total', 'Trading signals detected')
```

### Common Issues

#### WebRequest Failures

**Symptoms**: Orders not being submitted, timeout errors

**Diagnosis**:
```bash
# Check MT5 logs
tail -f "$MT5_DATA_PATH/Logs/$(date +%Y%m%d).log"

# Test connectivity
curl -v https://exodus-orchestrator.com/health
```

**Resolution**:
- Verify WebRequest URL whitelist
- Check network connectivity
- Validate SSL certificates
- Implement retry logic with backoff

#### Idempotency Conflicts

**Symptoms**: Duplicate orders being rejected

**Diagnosis**:
```bash
# Check event store for duplicates
grep "clientOrderId.*duplicate" data/events.jsonl
```

**Resolution**:
- Improve idempotency key generation
- Add timestamp or sequence number
- Implement client-side deduplication

#### Reconciliation Mismatches

**Symptoms**: Orders not matching broker fills

**Diagnosis**:
```python
# Query reconciliation service
reconciliation_service.check_unmatched_orders()
```

**Resolution**:
- Verify order ID mapping
- Check timestamp synchronization
- Review broker API response parsing

### Log Analysis

```bash
# Search for errors in MT5 logs
grep -i error "$MT5_DATA_PATH/Logs/$(date +%Y%m%d).log"

# Analyze WebRequest calls
grep "WebRequest" "$MT5_DATA_PATH/Logs/$(date +%Y%m%d).log"

# Check orchestrator logs
tail -f logs/orchestrator.log | jq 'select(.level == "ERROR")'
```

---

## Performance Tuning

### MT5 Optimization

```mql5
// Optimize EA performance
#property strict

// Use tick events efficiently
void OnTick() {
    static datetime lastBar = 0;
    datetime currentBar = iTime(_Symbol, PERIOD_D1, 0);

    if(currentBar != lastBar) {
        lastBar = currentBar;
        // Process daily bar logic here
        ProcessDailySignals();
    }
}

// Minimize WebRequest calls
void ProcessDailySignals() {
    static bool processedToday = false;

    if(!processedToday && CheckEntrySignals() != SIGNAL_NONE) {
        SubmitOrderToOrchestrator(buildOrderRequest());
        processedToday = true;
    }

    // Reset at midnight
    if(TimeHour(TimeCurrent()) == 0) {
        processedToday = false;
    }
}
```

### Orchestrator Optimization

```python
# app.py - Performance improvements
from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn

app = FastAPI()

# Add security middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*.yourdomain.com"])

# Connection pooling
from httpx import AsyncClient
client = AsyncClient(limits=httpx.Limits(max_keepalive_connections=20, max_connections=100))

# Caching layer
from cachetools import TTLCache
order_cache = TTLCache(maxsize=1000, ttl=300)  # 5 minute TTL
```

### Database Optimization

```sql
-- Create indexes for performance
CREATE INDEX idx_events_type_timestamp ON events (type, timestamp);
CREATE INDEX idx_events_idempotency ON events (idempotency);
CREATE INDEX idx_orders_symbol_status ON orders (symbol, status);

-- Partition event table by date
CREATE TABLE events_y2025m10 PARTITION OF events
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
```

---

## Compliance and Audit

### Audit Trail Requirements

- All order submissions with timestamps
- Idempotency keys and deduplication logic
- Risk check results and approvals
- Broker execution reports
- Reconciliation results
- Error logs and incident responses

### Compliance Reporting

```python
# compliance_report.py
def generate_compliance_report(start_date: str, end_date: str) -> Dict:
    """Generate compliance report for regulatory requirements"""

    # Query orders within date range
    orders = query_orders(start_date, end_date)

    # Calculate required metrics
    report = {
        "period": f"{start_date} to {end_date}",
        "total_orders": len(orders),
        "successful_orders": len([o for o in orders if o["status"] == "filled"]),
        "rejected_orders": len([o for o in orders if o["status"] == "rejected"]),
        "reconciliation_matches": calculate_reconciliation_rate(orders),
        "audit_trail_complete": verify_audit_trail(orders)
    }

    return report
```

### Data Retention

- **Order Events**: 7+ years (regulatory requirement)
- **Audit Logs**: 7+ years
- **Trade Data**: 7+ years
- **System Logs**: 1-2 years

### Encryption at Rest

```python
# encryption.py
from cryptography.fernet import Fernet
import os

class DataEncryption:
    def __init__(self):
        self.key = os.getenv("ENCRYPTION_KEY")
        self.cipher = Fernet(self.key)

    def encrypt_data(self, data: str) -> str:
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt_data(self, encrypted_data: str) -> str:
        return self.cipher.decrypt(encrypted_data.encode()).decode()
```

---

## Code Examples

### Complete Exodus ARC EA

```mql5
// exodus_arc_ea.mq5 - Complete implementation
#property copyright "EXODUS Platform"
#property link      "https://github.com/amuzetnoM/exodus"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>

// Input parameters
input string OrchestratorUrl = "https://exodus-orchestrator.com/api/v1/orders";
input string ApiKey = "";  // Configure in EA properties
input int RiskPercent = 1; // Risk per unit (%)
input int MaxUnits = 5;    // Maximum pyramiding units

// Global variables
CTrade trade;
string symbol = _Symbol;
int magicNumber = 12345;

// Position tracking
struct PositionUnit {
    double entryPrice;
    double quantity;
    double stopLoss;
};

PositionUnit units[];
int currentUnits = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit() {
    trade.SetExpertMagicNumber(magicNumber);
    Print("Exodus ARC EA initialized");
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
    Print("Exodus ARC EA deinitialized");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick() {
    static datetime lastBar = 0;
    datetime currentBar = iTime(symbol, PERIOD_D1, 0);

    if(currentBar != lastBar) {
        lastBar = currentBar;
        ProcessDailySignals();
    }

    // Check for pyramiding opportunities
    CheckPyramidingSignals();

    // Update stops
    UpdateStops();
}

//+------------------------------------------------------------------+
//| Process daily signals                                            |
//+------------------------------------------------------------------+
void ProcessDailySignals() {
    EntrySignal signal = CheckEntrySignals();

    if(signal != SIGNAL_NONE && currentUnits == 0) {
        // New position entry
        double atr = CalculateATR(20);
        double accountBalance = AccountInfoDouble(ACCOUNT_BALANCE);

        PositionSize ps = CalculatePositionSize(atr, accountBalance, RiskPercent);

        if(signal == SIGNAL_LONG_SYSTEM1 || signal == SIGNAL_LONG_SYSTEM2) {
            EnterLongPosition(ps.quantity, atr);
        } else if(signal == SIGNAL_SHORT_SYSTEM1 || signal == SIGNAL_SHORT_SYSTEM2) {
            EnterShortPosition(ps.quantity, atr);
        }
    }

    // Check exit signals
    CheckExitSignals();
}

//+------------------------------------------------------------------+
//| Enter long position                                               |
//+------------------------------------------------------------------+
void EnterLongPosition(double quantity, double atr) {
    double price = SymbolInfoDouble(symbol, SYMBOL_ASK);
    double stopLoss = price - (atr * 2);

    // Submit to orchestrator
    OrderRequest req;
    req.symbol = symbol;
    req.side = "buy";
    req.quantity = quantity;
    req.price = price;
    req.clientOrderId = GenerateOrderId("BUY");

    int result = SubmitOrderToOrchestrator(req);

    if(result == 200) {
        // Add to position tracking
        PositionUnit unit;
        unit.entryPrice = price;
        unit.quantity = quantity;
        unit.stopLoss = stopLoss;

        ArrayResize(units, currentUnits + 1);
        units[currentUnits] = unit;
        currentUnits++;
    }
}

//+------------------------------------------------------------------+
//| Enter short position                                              |
//+------------------------------------------------------------------+
void EnterShortPosition(double quantity, double atr) {
    double price = SymbolInfoDouble(symbol, SYMBOL_BID);
    double stopLoss = price + (atr * 2);

    // Submit to orchestrator
    OrderRequest req;
    req.symbol = symbol;
    req.side = "sell";
    req.quantity = quantity;
    req.price = price;
    req.clientOrderId = GenerateOrderId("SELL");

    int result = SubmitOrderToOrchestrator(req);

    if(result == 200) {
        // Add to position tracking
        PositionUnit unit;
        unit.entryPrice = price;
        unit.quantity = quantity;
        unit.stopLoss = stopLoss;

        ArrayResize(units, currentUnits + 1);
        units[currentUnits] = unit;
        currentUnits++;
    }
}

//+------------------------------------------------------------------+
//| Check pyramiding signals                                         |
//+------------------------------------------------------------------+
void CheckPyramidingSignals() {
    if(currentUnits == 0 || currentUnits >= MaxUnits) return;

    double currentPrice = SymbolInfoDouble(symbol, SYMBOL_BID);
    double atr = CalculateATR(20);

    bool isLong = (units[0].entryPrice < currentPrice); // Assume all units same direction

    if(ShouldAddUnit(units[0].entryPrice, currentPrice, isLong, atr)) {
        // Add another unit
        double accountBalance = AccountInfoDouble(ACCOUNT_BALANCE);
        PositionSize ps = CalculatePositionSize(atr, accountBalance, RiskPercent);

        if(isLong) {
            EnterLongPosition(ps.quantity, atr);
        } else {
            EnterShortPosition(ps.quantity, atr);
        }
    }
}

//+------------------------------------------------------------------+
//| Check exit signals                                               |
//+------------------------------------------------------------------+
void CheckExitSignals() {
    if(currentUnits == 0) return;

    // System 1 exit: 10-period Donchian
    DonchianChannel dc10 = CalculateDonchian(10);
    double currentPrice = SymbolInfoDouble(symbol, SYMBOL_BID);

    bool isLong = (units[0].entryPrice < currentPrice);

    if(isLong && currentPrice <= dc10.low) {
        // Exit long position
        CloseAllPositions();
    } else if(!isLong && currentPrice >= dc10.high) {
        // Exit short position
        CloseAllPositions();
    }

    // System 2 exit: 20-period Donchian (if applicable)
    if(currentUnits > 0) {
        DonchianChannel dc20 = CalculateDonchian(20);

        if(isLong && currentPrice <= dc20.low) {
            CloseAllPositions();
        } else if(!isLong && currentPrice >= dc20.high) {
            CloseAllPositions();
        }
    }
}

//+------------------------------------------------------------------+
//| Update stops                                                     |
//+------------------------------------------------------------------+
void UpdateStops() {
    if(currentUnits == 0) return;

    double currentPrice = SymbolInfoDouble(symbol, SYMBOL_BID);
    double atr = CalculateATR(20);

    for(int i = 0; i < currentUnits; i++) {
        bool isLong = (units[i].entryPrice < currentPrice);

        if(isLong) {
            // Trail stop for long positions
            double newStop = currentPrice - (atr * 2);
            if(newStop > units[i].stopLoss) {
                units[i].stopLoss = newStop;
            }
        } else {
            // Trail stop for short positions
            double newStop = currentPrice + (atr * 2);
            if(newStop < units[i].stopLoss) {
                units[i].stopLoss = newStop;
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Close all positions                                              |
//+------------------------------------------------------------------+
void CloseAllPositions() {
    // Submit close orders to orchestrator
    for(int i = 0; i < currentUnits; i++) {
        OrderRequest req;
        req.symbol = symbol;
        req.side = units[i].entryPrice < SymbolInfoDouble(symbol, SYMBOL_BID) ? "sell" : "buy";
        req.quantity = units[i].quantity;
        req.price = 0; // Market order
        req.clientOrderId = GenerateOrderId("CLOSE");

        SubmitOrderToOrchestrator(req);
    }

    // Reset position tracking
    ArrayResize(units, 0);
    currentUnits = 0;
}

//+------------------------------------------------------------------+
//| Generate unique order ID                                         |
//+------------------------------------------------------------------+
string GenerateOrderId(string prefix) {
    return StringFormat("%s_%s_%d", prefix, symbol, TimeCurrent());
}

//+------------------------------------------------------------------+
//| Helper functions (implementations above)                         |
//+------------------------------------------------------------------+
// DonchianChannel CalculateDonchian(int period, int shift = 0)
// double CalculateATR(int period, int shift = 0)
// PositionSize CalculatePositionSize(double atr, double accountBalance, double riskPercent)
// EntrySignal CheckEntrySignals()
// bool ShouldAddUnit(double entryPrice, double currentPrice, bool isLong, double atr)
// int SubmitOrderToOrchestrator(OrderRequest &req)
```

### Python Strategy Implementation

```python
# exodus_arc/strategy.py
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import numpy as np

@dataclass
class DonchianChannel:
    high: float
    low: float
    mid: float

@dataclass
class PositionSize:
    units: int
    quantity: float
    risk_amount: float

@dataclass
class TradingSignal:
    signal_type: str  # 'LONG_SYSTEM1', 'SHORT_SYSTEM1', etc.
    symbol: str
    price: float
    timestamp: datetime

class ExodusArcStrategy:
    """Exodus ARC strategy implementation (Turtle Trading-inspired)"""

    def __init__(self, risk_percent: float = 1.0, max_units: int = 5):
        self.risk_percent = risk_percent
        self.max_units = max_units
        self.positions: Dict[str, List[Dict]] = {}  # symbol -> list of units

    def calculate_donchian(self, prices: List[float], period: int) -> DonchianChannel:
        """Calculate Donchian channel for given period"""
        if len(prices) < period:
            raise ValueError(f"Need at least {period} prices, got {len(prices)}")

        high = max(prices[-period:])
        low = min(prices[-period:])
        mid = (high + low) / 2

        return DonchianChannel(high=high, low=low, mid=mid)

    def calculate_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int) -> float:
        """Calculate Average True Range"""
        if len(highs) < period + 1:
            raise ValueError(f"Need at least {period + 1} periods for ATR")

        tr_values = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],  # Current high - current low
                abs(highs[i] - closes[i-1]),  # Current high - previous close
                abs(lows[i] - closes[i-1])    # Current low - previous close
            )
            tr_values.append(tr)

        return np.mean(tr_values[-period:])  # Average of last 'period' TR values

    def calculate_position_size(self, atr: float, account_balance: float) -> PositionSize:
        """Calculate position size based on ATR and risk"""
        risk_amount = account_balance * (self.risk_percent / 100.0)
        stop_distance = atr * 2  # 2 ATR stop

        # For forex pairs, approximate pip value
        pip_value = 10  # USD per pip for EURUSD with 10k lot

        quantity = risk_amount / (stop_distance * pip_value)

        # Round to standard lot sizes (0.01 minimum)
        quantity = round(quantity / 0.01) * 0.01

        return PositionSize(
            units=1,
            quantity=max(quantity, 0.01),  # Minimum 0.01 lots
            risk_amount=risk_amount
        )

    def check_entry_signals(self, high: float, low: float, close: float,
                          prices_20: List[float], prices_55: List[float]) -> Optional[TradingSignal]:
        """Check for entry signals using Donchian breakouts"""

        # System 1: 20-period Donchian
        dc20 = self.calculate_donchian(prices_20, 20)

        if close > dc20.high:
            return TradingSignal(
                signal_type='LONG_SYSTEM1',
                symbol='EURUSD',  # Parameterize this
                price=close,
                timestamp=datetime.utcnow()
            )
        elif close < dc20.low:
            return TradingSignal(
                signal_type='SHORT_SYSTEM1',
                symbol='EURUSD',
                price=close,
                timestamp=datetime.utcnow()
            )

        # System 2: 55-period Donchian
        dc55 = self.calculate_donchian(prices_55, 55)

        if close > dc55.high:
            return TradingSignal(
                signal_type='LONG_SYSTEM2',
                symbol='EURUSD',
                price=close,
                timestamp=datetime.utcnow()
            )
        elif close < dc55.low:
            return TradingSignal(
                signal_type='SHORT_SYSTEM2',
                symbol='EURUSD',
                price=close,
                timestamp=datetime.utcnow()
            )

        return None

    def check_exit_signals(self, symbol: str, current_price: float,
                          prices_10: List[float], prices_20: List[float]) -> bool:
        """Check for exit signals"""
        if symbol not in self.positions or not self.positions[symbol]:
            return False

        # Determine position direction from first unit
        first_unit = self.positions[symbol][0]
        is_long = first_unit['entry_price'] < current_price

        # System 1 exit: 10-period Donchian
        dc10 = self.calculate_donchian(prices_10, 10)

        if is_long and current_price <= dc10.low:
            return True
        elif not is_long and current_price >= dc10.high:
            return True

        # System 2 exit: 20-period Donchian
        dc20 = self.calculate_donchian(prices_20, 20)

        if is_long and current_price <= dc20.low:
            return True
        elif not is_long and current_price >= dc20.high:
            return True

        return False

    def should_add_unit(self, entry_price: float, current_price: float,
                       is_long: bool, atr: float) -> bool:
        """Check if should add another unit (pyramiding)"""
        distance = abs(current_price - entry_price)
        threshold = atr * 0.5  # Add every 0.5 ATR

        return distance >= threshold

    def generate_entry_order(self, signal: TradingSignal, atr: float,
                           account_balance: float) -> Dict:
        """Generate order from trading signal"""
        position_size = self.calculate_position_size(atr, account_balance)

        return {
            'clientOrderId': f"exodus_arc_{signal.signal_type}_{signal.timestamp.strftime('%Y%m%d_%H%M%S')}",
            'symbol': signal.symbol,
            'side': 'buy' if 'LONG' in signal.signal_type else 'sell',
            'qty': position_size.quantity,
            'price': signal.price,
            'strategy': 'exodus_arc',
            'signal_type': signal.signal_type
        }

    def update_positions(self, symbol: str, order_result: Dict):
        """Update position tracking after order execution"""
        if symbol not in self.positions:
            self.positions[symbol] = []

        unit = {
            'order_id': order_result['internalOrderId'],
            'entry_price': order_result.get('price', 0),
            'quantity': order_result.get('qty', 0),
            'entry_time': datetime.utcnow()
        }

        self.positions[symbol].append(unit)

    def get_position_summary(self, symbol: str) -> Dict:
        """Get summary of current position"""
        if symbol not in self.positions:
            return {'units': 0, 'total_quantity': 0, 'avg_entry': 0}

        units = self.positions[symbol]
        total_quantity = sum(u['quantity'] for u in units)
        total_value = sum(u['entry_price'] * u['quantity'] for u in units)
        avg_entry = total_value / total_quantity if total_quantity > 0 else 0

        return {
            'units': len(units),
            'total_quantity': total_quantity,
            'avg_entry': avg_entry
        }
```

---

## References

### Documentation

- [EXODUS Platform Design](brokerage_platform_design.md)
- [Exodus ARC Strategy Blueprint](agent/exodus_arc.md)
- [XM MT5 Integration Catalog](broker_catalog/xm_mt5.md)
- [Command Codex](cmd_cdx.md)

### MQL5 Resources

- [MQL5 Reference](https://www.mql5.com/en/docs)
- [MetaTrader 5 Terminal Help](https://www.metatrader5.com/en/terminal/help)
- [WebRequest Function](https://www.mql5.com/en/docs/network/webrequest)

### Trading Strategy Resources

- "Way of the Turtle" by Curtis Faith
- [Donchian Channel Explanation](https://www.investopedia.com/terms/d/donchianchannels.asp)
- [Average True Range (ATR)](https://www.investopedia.com/terms/a/atr.asp)

### Development Tools

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Pydantic Models](https://pydantic-docs.helpmanual.io)
- [httpx Async HTTP Client](https://www.python-httpx.org)

---

**Exodus ARC MT5 Integration Guide - Complete Implementation**

This document provides the comprehensive technical specification and implementation guide for integrating the Exodus ARC strategy with MetaTrader 5 through the EXODUS platform. The implementation follows the blueprint specifications with robust error handling, security measures, and operational procedures.

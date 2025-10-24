# Exodus ARC Integration Research & Blueprint

**Status**: Strategy Integration Analysis  
**Last Updated**: 2025-10-24  
**Product**: Exodus ARC  
**Vendor**: EXODUS (internal)  
**Platform**: EXODUS Strategy Service / optional MT5 bridge

---

## 1. Executive Summary

Exodus ARC is an EXODUS-native strategy service that implements a classic trend-following
workflow using the Donchian Channel breakouts, ATR-based sizing,
and pyramiding. Exodus ARC is designed to run inside EXODUS but can also interoperate with
external execution platforms (MT5) for hybrid deployments.

Key Insight for EXODUS Integration:
Exodus ARC is a strategy implementation intended to run inside EXODUS. Integration options are:

1. Path A: Run an external EA (third-party) and have EXODUS observe/reconcile trades
2. Path B: Run Exodus ARC natively in EXODUS and route orders through your adapters (recommended)
3. Path C: Hybrid — run Exodus ARC logic in EXODUS but allow modified EA to request pre-trade approvals

---

## 2. Product Details (Exodus ARC)

### Official Information
- **Product Name**: Exodus ARC  
- **Product ID**: exodus_arc (internal)  
- **Version**: check EXODUS release tags  
- **Author**: EXODUS Strategy Team  
- **Activation**: Internal deployment and service registration  
- **Platform**: EXODUS Strategy Service (preferred); optional MT5 adapter for external execution

### Strategy Overview (Turtle-inspired Rules)
Exodus ARC automates trend-following using Donchian breakout signals, ATR sizing, and pyramiding:

1. Entry Signals:
    - System 1 (S1): 20-period Donchian breakout
    - System 2 (S2): 55-period Donchian breakout
    - Buy on N-period high breakout; sell on N-period low breakout

2. Position Sizing:
    - Risk 1-2% of account equity per unit
    - Unit size = (Equity × Risk%) / (ATR × Point Value)
    - ATR-based volatility adjustment

3. Pyramiding:
    - Add units at 0.5 ATR intervals
    - Max 4-5 units per trend (configurable)

4. Stop Loss:
    - Initial stop = 2 ATR from entry
    - Trailing stop management as position profits accrue

5. Exit Signals:
    - System 1: 10-period Donchian exit
    - System 2: 20-period Donchian exit

Supported Instruments
- Forex pairs, indices CFDs, commodities, (crypto CFDs if available)
- Primary timeframe: D1; optional H4/W1

---

## 3. Technical Specifications (Exodus ARC)

### Exodus ARC Inputs (typical configurable parameters)
```mql5
// Example parameters (for parity with common implementations)
input int System1_Entry = 20;
input int System2_Entry = 55;
input int System1_Exit = 10;
input int System2_Exit = 20;
input double RiskPercent = 1.0;
input int MaxUnits = 4;
input int ATR_Period = 20;
input double ATR_Multiplier = 2.0;
input bool UseSystem1 = true;
input bool UseSystem2 = true;
input string StrategyId = "exodus_arc";
```

### Order Management
- Order Type: Market orders (configurable)
- Position Mode: Hedging or netting depending on adapter
- StrategyId / metadata used to tag orders and trades for reconciliation

### Risk Management (Built-in)
- Margin validation before entry
- Configurable drawdown and daily loss limits
- Circuit breakers and velocity controls

---

## 4. Integration Options with EXODUS

### Option A: Observe & Reconcile (Passive Integration)
Use Case: Run external EA; EXODUS monitors and records trades for compliance and reporting.

Architecture:
MT5 Terminal (third-party EA)
            ↓
     Broker
            ↓
EXODUS Reconciliation Service (polls broker/MT5 history)
            ↓
EXODUS Trade Tape (read-only records)

Implementation:
1. Run EA on external platform (if used)
2. Build EXODUS history poller to ingest deals/orders; tag with source=external
3. Reconcile trades to EXODUS trade tape and risk reports

Pros:
- No change to external EA
- Centralized reporting in EXODUS

Cons:
- No pre-trade control from EXODUS
- Dependent on EA/vendor support

When to Use:
- Quick auditability for third-party strategies
- Testing vendor EA performance before migration

---

### Option B: Native Exodus ARC (Active Integration) — recommended
Use Case: Implement Turtle-inspired rules natively in EXODUS; route orders through adapters.

Architecture:
EXODUS Strategy Service (Exodus ARC)
            ↓
EXODUS Orchestrator (risk checks, routing)
            ↓
Broker Adapter (FIX/REST/MT5 bridge)
            ↓
Broker

Implementation:
1. Strategy service that evaluates Donchian breakouts and ATR on bar close
2. Market data pipeline (daily bars) publishing to strategy
3. Orchestrator applies pre-trade checks and routes approved orders
4. Position manager maintains unit state, pyramiding, and stops

Python example (simplified) — metadata uses "exodus_arc":
```python
class ExodusArcStrategy:
     def generate_entry_order(self, atr, direction):
          account_equity = get_account_equity()
          risk_amount = account_equity * self.risk_pct
          position_size = risk_amount / (atr * 2.0)  # 2 ATR stop
          return {
                'symbol': self.symbol,
                'side': 'buy' if direction == 'long' else 'sell',
                'quantity': position_size,
                'type': 'market',
                'stop_loss': calculate_stop(direction, atr),
                'metadata': {'strategy': 'exodus_arc', 'system': self.system, 'unit': 1}
          }
```

Pros:
- Full control, pre-trade risk enforcement
- No third-party dependency
- Easier backtesting and observability

Cons:
- Development effort to implement and validate

When to Use:
- Full integration with EXODUS risk and routing required
- Need to customize rules and enforce compliance

---

### Option C: Hybrid Approach (EXODUS Oversight)
Use Case: External EA requests EXODUS pre-trade approval before executing.

Architecture:
MT5 Terminal (modified EA)
            ↓
     WebRequest() to EXODUS API
            ↓
EXODUS Pre-Trade Risk Check
            ↓ (approved)
Return approval to EA
            ↓
EA executes order at broker

Implementation:
1. Modify EA to call EXODUS API for approvals before sending orders
2. EXODUS risk service validates and returns approval/rejection

Pros:
- Keep vendor EA logic while enforcing centralized risk
- Audit trail of approvals

Cons:
- Requires EA source access or vendor cooperation
- Adds latency and complexity

---

## 5. Deployment & Setup (Exodus ARC)

### Deployment Process
1. Pull Exodus ARC release from internal registry
2. Deploy the strategy service to EXODUS cluster
3. Register service in orchestrator and configure adapters
4. Provision market data subscriptions (daily bars)

### Recommended Server Setup for EXODUS Components
- OS: Linux (containerized) or Windows for MT5 bridge
- Specs: 2 vCPU, 4GB RAM for strategy container; scale as needed
- Monitoring: Heartbeat and alerting (Prometheus/Grafana)

---

## 6. Strategy Backtesting & Validation

Before live trading, validate Exodus ARC performance:

MT5 Strategy Tester (if using MT5 bridge) or EXODUS backtest:
1. Select symbol and timeframe (D1 recommended)
2. Use 10+ years of historical bars
3. Run walk-forward/backtest and evaluate metrics:
    - Total return, Sharpe, max drawdown, profit factor

Validation Checklist:
- [ ] Backtest on multi-year data for target symbols
- [ ] Forward test on demo for 3+ months
- [ ] Verify position sizing and ATR calculations
- [ ] Validate stop-loss and pyramiding behavior

---

## 7. Risk Considerations

Strategy Risks:
- False breakouts in ranging markets
- Potential 20–40% drawdowns in adverse regimes
- Correlation risk across pairs

Operational Risks:
- Data feed gaps, adapter failures, VPS downtime for MT5 bridge
- Execution slippage and broker limitations

EXODUS Mitigations:
- Position limits, daily loss caps, velocity controls, kill-switch

---

## 8. Monitoring & Reconciliation

Key Metrics:
- Open positions, average entry, unrealized P&L
- Daily trade list, slippage, fill quality
- Strategy performance and risk metrics

Integration Points:
1. Trade ingestion: tag trades with metadata.strategy = 'exodus_arc'
2. Reconciliation: map strategy orders to broker fills; alert on mismatches
3. Dashboards: Grafana panels for P&L, drawdown, open positions

---

## 9. Compliance & Audit Trail

Required Records:
- Strategy configuration and version
- Trade justification (link to Donchian event)
- Risk approvals and rejections
- P&L attribution with strategy tag = 'exodus_arc'

Audit Queries (example):
```sql
SELECT * FROM trades
WHERE strategy = 'exodus_arc'
  AND trade_date >= '2025-10-01'
  AND trade_date < '2025-11-01';
```

---

## 10. Cost-Benefit Analysis

Costs:
- Development and integration hours (estimate 40–80 hrs)
- Hosting and adapter maintenance
- Execution costs (broker spreads/commissions)

Benefits:
- Centralized risk and observability
- Native integration and easier regulatory/audit compliance
- Faster iteration and backtesting

---

## 11. Alternatives & Migration Paths

Option 1: Observe external vendor EAs and ingest trades into EXODUS (low-effort)  
Option 2: Implement Exodus ARC natively in EXODUS (recommended for control)  
Option 3: Hybrid: external EA requests EXODUS pre-trade approvals

---

## 12. Next Steps

Immediate Actions (Week 1)
1. [ ] Confirm decision: Observe, Native, or Hybrid
2. [ ] Provision test environment in EXODUS
3. [ ] Load historical bars for target instruments

Integration Planning (Week 2-3)
1. [ ] Design strategy service and state management
2. [ ] Define risk parameters and limit values
3. [ ] Build adapters (MT5 / FIX) as required

Testing (Week 4-6)
1. [ ] Backtest and forward test
2. [ ] Validate reconciliation and kill-switch behavior
3. [ ] Perform chaos tests (adapter failures, data gaps)

Production Rollout (Week 7+)
1. [ ] Start with 1 symbol at reduced risk (0.5% per unit)
2. [ ] Monitor daily for 2+ weeks, then scale

---

## 13. References

- "Way of the Turtle" by Curtis Faith — background on Turtle Trading (conceptual)
- Donchian Channel & ATR references (Investopedia links)
- EXODUS internal docs: strategy-service, orchestrator, adapter guides

---

## 14. Appendix: Rules Summary (Exodus ARC)

Entry
- System 1: 20-period Donchian high/low breakout
- System 2: 55-period Donchian high/low breakout

Position Sizing
- Risk ~1% per unit
- Unit = (Equity × Risk%) / (ATR × Dollar per point)

Pyramiding
- Add unit every 0.5 ATR favorable move
- Stop for all units at 2 ATR from most recent entry

Stops & Exits
- Initial stop = 2 ATR
- System 1 exit = 10-period Donchian
- System 2 exit = 20-period Donchian

Markets
- Liquidity and ATR thresholds required


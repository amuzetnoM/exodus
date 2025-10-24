# XM/MT5 E2E Test Scenarios

Purpose: deterministic acceptance tests for the XM/MT5 EA -> Orchestrator flow.

Environment prerequisites
- Local mock orchestrator running at `http://127.0.0.1:8080` (see `xm/mock_orchestrator.py`).
- MetaTrader 5 terminal with EA installed (`xm/mql5_ea_template.mq5`) or an EA simulator that emits WebRequest payloads.

Test scenarios

1) Basic ACK + Full Fill
- Steps:
  - EA sends order POST with `clientOrderId`, `symbol`, `qty`, `price`.
  - Mock orchestrator returns ACK with `brokerOrderId` and `internalOrderId`.
  - Mock orchestrator prints simulated EXECUTION_REPORT (FILLED).
- Acceptance:
  - Orchestrator stored the OrderSubmitted event with matching `clientOrderId`.
  - ExecutionReport persisted with filledQty == qty.

2) Partial Fill then Fill
- Steps:
  - EA sends order.
  - Mock orchestrator returns ACK and then sends partial fill after short delay.
  - Later, mock orchestrator sends remaining fill.
- Acceptance:
  - Orchestrator records multiple ExecutionReport events linked to same order; final remainingQty == 0.

3) Out-of-order Execution Reports
- Steps:
  - Simulate delayed ACK or fill by introducing delay in mock.
  - Ensure orchestrator uses sequence numbers / timestamps to reorder.
- Acceptance:
  - Final order state reconciles correctly and does not double-count fills.

4) Idempotency test
- Steps:
  - EA resends identical order payload (same `clientOrderId`) multiple times due to retry.
- Acceptance:
  - Orchestrator deduplicates and returns same `internalOrderId` and does not create duplicate orders.

5) Network partition & replay
- Steps:
  - Mock simulate network drop; EA replays requests after reconnect.
- Acceptance:
  - No duplicate fills; dedupe via idempotency; reconciliation identifies any mismatches.

6) Latency & throughput smoke
- Steps:
  - Generate 100 concurrent EA order requests against mock.
- Acceptance:
  - Orchestrator handles with bounded latency; no uncaught exceptions; metrics emitted.

Canary promotion gates
- Reconciliation success rate >= 99.9% over 24h in sandbox.
- No critical alerts (sequence gaps, missing fills) during staged pilot.

Automation notes
- Tests should be runnable in CI using the mock orchestrator and a small test runner (pytest + httpx or requests).


Last updated: 2025-10-24

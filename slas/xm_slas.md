# XM Adapter SLAs and Monitoring Thresholds

SLA targets for the XM/MT5 adapter (recommendations for POC -> production).

## Availability
- Core order routing availability: 99.95% (monthly uptime).
- Adapter process liveness: 99.99% (auto-restart + session resume required).

## Latency
- Median (p50) order RTT from API ingress to broker ACK: < 150ms (POC target)
- P99 RTT: define per broker during onboarding; aim for < 500ms for retail.

## Reconciliation
- Daily reconciliation success rate: >= 99.9% (matched volumes vs broker reports).
- Orphan fills threshold for alerting: > 0.1% unmatched volume or > 10 unmatched trades.

## Error budgets and canary gates
- Canary promotion requirement: zero unreconciled fills and no critical alerts for 24h in sandbox.
- Max rejection rate during canary: < 1% for valid orders.

## Monitoring & Alerts
- Alert on sequence gaps, missed FIX heartbeats, WebRequest error spikes, reconciliation deltas exceeding thresholds, and credential rotation failures.


Last updated: 2025-10-24

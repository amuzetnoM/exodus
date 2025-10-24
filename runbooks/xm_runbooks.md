# XM / MT5 Operator Runbooks

Purpose: concise runbooks for common operational incidents affecting the XM/MT5 adapter and orchestrator.

1) FIX/Adapter session lost (if FIX used)
- Detect: missing heartbeats, session marked 'DISCONNECTED' in dashboard.
- Immediate: escalate to on-call; do not restart adapter without checking seq numbers.
- Steps:
  - Check persisted session sequence numbers in DB.
  - If adapter crashed, restart with session store attached and monitor for ResendRequest handling.
  - If gaps observed, request manual resend from broker or replay events from trade-tape.

2) EA WebRequest failures (EA cannot reach orchestrator)
- Detect: spikes in WebRequest errors from EA logs or missing ACKs.
- Immediate: toggle global EA kill-switch to prevent accidental duplicate orders.
- Steps:
  - Verify orchestrator health endpoint; ensure DNS and TLS certs valid.
  - If orchestrator healthy but persistent errors, check firewall/VPN and broker-side connectivity (e.g., MT5 VPS outbound rules).
  - Re-enable EA traffic once resolved and confirm idempotency prevents duplicates.

3) Reconciliation drift (orphan fills)
- Detect: reconciliation delta > threshold (e.g., unmatched volume > 0.1% or > X units)
- Immediate: pause new live orders for affected accounts and notify risk/compliance.
- Steps:
  - Start targeted replay of event store for affected instrument/account.
  - Compare broker-provided reports against internal trade tape.
  - Create remediation tickets and flag customer accounts if necessary.

4) Broker outage (XM sandbox/prod)
- Detect: broker rejects or prolonged connectivity losses, or broker status page reports outage.
- Immediate: move to failover plan (alternate broker) if business-critical.
- Steps:
  - Switch new orders to alternate broker or enter safe-mode where orders are queued.
  - Notify clients and SRE. Run post-incident RCA.

5) Credential compromise
- Detect: unexpected credential use, large number of order failures, or alerts from secret manager.
- Immediate: revoke compromised credentials and rotate secrets.
- Steps:
  - Revoke API keys / disable affected accounts.
  - Roll new credentials and update EAs / adapters with new values via secure rotation.
  - Investigate scope and notify compliance/legal if needed.

6) Emergency kill-switch
- Use case: runaway algo, severe slippage, systemic bug.
- Immediate: flip global order-accepting flag to OFF; notify clients.
- Steps:
  - Run reconciliation on recent trades; assess exposure.
  - Re-enable incrementally after verifying systems.

---

Keep runbooks concise; attach exact commands, monitoring dashboard links, and contact lists in your internal SRE portal.

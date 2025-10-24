# EXODUS

Version: 1.1  
Purpose: Consolidated design and implementation blueprint for a platform that connects to one or more live brokerages. Covers architecture, connectivity, auth/security, order lifecycle, pre-trade risk, testing/rollout, monitoring/reconciliation, compliance/logging, deployment, and operational playbooks. This document merges the original notes with expanded, buildable artifacts and removes duplication.

## Executive summary
EXODUS is a production-grade broker integration and order-routing platform designed for safe, auditable, and low-latency trading across retail and institutional broker connectivity. It centralizes risk control, provides durable order state and reconciliation, and exposes a normalized API for clients. Design priorities: correctness, recoverability, observability, and operational simplicity.

## Glossary
- ClientOrderId: client-supplied idempotency key.
- InternalOrderId: system-generated unique id.
- Adapter: broker-specific connector (FIX/REST/etc).
- Event store / trade tape: append-only canonical list of events and fills.
- Correlation ID: request-scoped identifier used for tracing.
- WORM: write-once-read-many immutable storage.

## 1. Scope and Goals
- Provide a reliable, auditable, and low-latency bridge between client systems and multiple brokerages.
- Support core order types (market, limit, stop, IOC, FOK, pegged, conditional).
- Enforce safety via layered pre-trade risk controls and operator kill-switches.
- Guarantee traceability for compliance and reconciliation.
- Provide deterministic testing: mock broker, sandbox, and replayable event-store.

## 2. Stakeholders
- Trading desk / clients
- Broker/integration team
- Risk & compliance
- SRE / Ops
- QA / Testing
- Legal / Audit

## 3. Non-functional requirements (must-have)
- Availability: 99.95% for core order routing; degraded mode available for non-critical services.
- Latency: target median order RTT < 150ms (retail); specific SLOs defined per adapter/market; P99 budgets defined.
- Throughput: specify N orders/sec per account pool (business-driven).
- Durability: guaranteed event persistence for replay and reconciliation.
- Security: secrets in Vault/KMS, TLS/mTLS, role-based access control.
- Retention: 7+ years default (adjust per jurisdiction).
- Observability: metrics, traces, structured logs for every user action and adapter interaction.

## 4. High-Level Architecture (expanded)
Components:
- Client-facing API / Gateway (REST/WS) — normalizes client requests, enforces auth, quotas, rate limits.
- Order Router / Orchestrator — validation, transformation, routing, correlation, and state transitions.
- Broker Adapters / Connectors — protocol-specific logic (QuickFIX, REST adapter, binary codecs).
- Risk Engine (pre-trade & runtime) — synchronous pre-trade checks and async monitoring.
- Order State Store / Event Store — append-only ledger (event-sourcing) and read models for fast queries.
- Market Data Ingress — consolidated ticks, L1/L2, symbol normalization, reference data.
- Messaging Layer — Kafka for durable streaming between services; Redis for ephemeral counters and throttles.
- Persistence & Reconciliation DB — Postgres read models, audit exports, snapshots.
- Monitoring / Alerting / Telemetry — Prometheus, Grafana, OpenTelemetry/Jaeger.
## 25. XM Trading (MetaTrader 5) — integration notes

This section captures XM + MetaTrader 5 integration guidance and links to
the dedicated broker catalog entry at `broker_catalog/xm_mt5.md` which
contains verification checkpoints and POC artifacts.

Summary:
- Primary POC path: use MetaTrader 5 Expert Advisors (EAs) that call out
  to an external orchestrator via HTTPS WebRequest. This is the fastest
  path to get a reliable integration for retail XM accounts.
- Institutional/FIX access: may be available for institutional clients;
  confirm availability, FIX version and access details with XM support.

Action items:
- Validate the `broker_catalog/xm_mt5.md` [VERIFY] placeholders with XM
  support (endpoints, rate limits, FIX availability, sandbox URLs).
- Use the provided `xm/mql5_ea_template.mq5` as the EA starting point and
  run it on a MetaTrader VPS for 24/7 operation during POC.
- Use `xm/mock_orchestrator.py` locally for deterministic E2E and chaos
  tests before connecting to live/sandbox XM accounts.

References and verification:
- See `broker_catalog/xm_mt5.md` for details and explicit fields to
  confirm with XM during onboarding. Replace any remaining [VERIFY]
  placeholders with the broker-provided values.
- Admin Console / Operator UI — manual controls, kill-switches, config management, incident tooling.
- Audit / Compliance Store — immutable, encrypted archives (S3 WORM or equivalent).

Design considerations:
- Adapters are thin; business and risk logic centralized.
- Use correlation IDs and idempotency everywhere.
- Event-sourcing enables deterministic replay, reconciliation, and debugging.
- Multi-tenant partitioning: separate topics/partitions per client or account group for isolation.

## 5. Connectivity Types & Protocols (detailed)
- FIX (v4.2–5.0): institutional standard; use QuickFIX/QuickFIX/J or high-performance engines.
- REST/HTTP(s): common for retail brokers; HMAC/OAuth signing as required.
- WebSocket/Streaming: for market data and real-time order updates.
- Binary / proprietary / DMA: custom adapters for low-latency needs.
- File transfer (SFTP): batch fills and end-of-day reports ingestion.

FIX specifics:
- Persist inbound/outbound seq nums and session state for resume after restarts.
- Implement ResendRequest and gap-fill handling.
- Heartbeats and test-request flows; alert on missed heartbeats.
- Message-level persistence for retransmit ability.

## 6. Authentication & Security (expanded)
- Transport: TLS 1.2+ and mTLS for broker sessions where supported.
- Client auth: OAuth2/JWT for human/API clients; API keys for programmatic access.
- Secret management: HashiCorp Vault or AWS Secrets Manager with rotation policies and audit trails.
- HSM: optionally required for signing high-assurance orders.
- Network: firewall rules, private connectivity (Direct Connect/PrivateLink), VPNs for broker tunnels.
- Least privilege: IAM roles scoped to required resources only.
- Incident response: automated credential revocation workflows and forced rotation.

## 7. Order Lifecycle and Reliability (expanded)
Canonical state machine:
- RECEIVED -> VALIDATED -> RISK_CHECK_PASSED / RISK_BLOCKED -> ROUTED -> SENT -> ACKED_BY_BROKER / REJECTED -> PARTIAL_FILL / FILL -> SETTLED / FAILED -> CANCELLED / EXPIRED

Persistence:
- Record each state transition with internalOrderId, clientOrderId, timestamps, adapterId, sessionId, correlationId, and full payloads.
- Snapshot periodic order state for efficient read models.

Idempotency & dedup:
- Require clientOrderId (or generate on receipt); store mapping of idempotency key -> internalOrderId.
- Use a TTL for idempotency keys and persist them to durable storage to survive restarts.

Reliability patterns:
- Local write-ahead queue before outbound sends; mark SENT only after successful transmission record.
- Retries with exponential backoff + jitter; circuit-breakers per adapter/broker.
- Delivery semantics: best-effort guaranteed-once via dedupe + reconciliation; accept eventual consistency but ensure eventual correctness via trade-tape reconciliation.

Partial fills & child orders:
- Track remaining quantity; optionally submit child orders or re-route automatically based on a policy.
- Persist filled legs as separate trade events linked to parent order.

Edge cases:
- Network partitions: persist requests locally, alert ops, and attempt resumptions with replay.
- Out-of-order execution reports: reorder using sequence numbers, reconciliation, and replay.

## 8. Pre-Trade Risk Controls (detailed)
Checks (synchronous, pre-trade):
- Buying power / margin checks.
- Position & exposure limits (per instrument, sector, account group).
- Notional and quantity caps.
- Price sanity: check against mid/mark/last with configurable tolerances.
- Velocity controls: orders/sec by client, symbol, and global.
- Blacklist/whitelist checks for instruments and clients.
- Circuit breakers: global, per-instrument, per-client automatic/manual.

Enforcement:
- Centralized risk service performing synchronous checks with fast in-memory caches and authoritative reconciliation background jobs.
- Policy store for configurable rules and change approvals (with audit trails).

## 9. Testing & Safe Rollout (detailed)
Environments:
- Local dev with mock broker emulator (deterministic).
- CI: unit tests + static analysis.
- Integration/staging: simulated broker endpoints and recorded market data.
- Sandbox: broker-provided paper accounts.
- Canary/production: limited traffic, progressive ramp-up.

Test types:
- Unit tests: business logic and risk rules.
- Integration tests: adapters vs mock/sandbox brokers.
- E2E tests: full order lifecycle validation.
- Load/perf testing: latency/throughput under representative loads.
- Chaos/fault-injection: disconnects, seq gaps, delayed acks.
- Security tests: secret access, token rotation, pen tests.

Rollout strategy:
- Feature flags, canary releases, metric-based promotion criteria (e.g., reconciliation success rate, latency bounds).
- Start with paper accounts and small client cohort.
- Operator runbooks for rollbacks and emergency kills.

## 10. Monitoring, Observability & Reconciliation (detailed)
Metrics:
- Latency P50/P90/P99 for API ingress, adapter outbound, and broker ack.
- Throughput: orders/sec, cancels/sec, fills/sec.
- Health: FIX session states, websocket counts, queue lag.
- Risk metrics: blocked orders, limit hits.

Logging & tracing:
- Structured JSON logs with correlationId, internalOrderId, clientOrderId, adapter/session IDs.
- OpenTelemetry traces for distributed call graphs; sample critical flows.
- Store raw adapter messages (encrypted) for forensic debugging.

Reconciliation algorithm:
- Reconcile by replaying event-store: match outgoing OrderSubmitted / OrderRouted events to ExecutionReport events from brokers.
- Use brokerOrderId mapping where available; fallback to fuzzy matching by symbol / qty / timestamps for older integrations.
- Record reconciliation deltas and escalate based on thresholds (unmatched volume, orphan fills).

Alerts & runbooks:
- Pre-built alerts for sequence gaps, reconciliation drift, SLA breaches, and risk triggers.
- Operator playbooks attached to alerts with exact remediation steps.

## 11. Compliance & Logging (expanded)
- Immutable audit trail: store all client requests, internal transforms, broker messages, risk decisions, and operator actions.
- WORM/immutable archives for regulatory retention.
- Encryption in transit and at rest; KMS for key management and rotation.
- Access control and audit logs for all access/modifications.
- Data residency and retention policies mapped to jurisdictional requirements.
- Exportable regulator-ready reports and redaction guidelines.

## 12. Practical Implementation Notes (expanded)
Persistence & snapshots:
- Event store: Kafka compacted topics or append-only DB as the primary stream.
- Read models: Postgres materialized views for fast queries; snapshot order-state periodically.
- Session state persistence externalized for adapter restarts (seq nums, heartbeats).

Tech stack suggestions:
- Adapters: Go or Java for low-latency (QuickFIX/J for FIX); Python for orchestration and analytics.
- Messaging: Kafka for durable streaming; Redis for counters and rate-limiting.
- Storage: Postgres for ledgers; S3 for archives.
- Observability: Prometheus, Grafana, ELK/Opensearch, Jaeger.

Operational patterns:
- Heartbeats and health endpoints; broker session health dashboards.
- Broker session state must be durable to enable stateless adapter restarts.
- Backpressure: API gateway enforces soft limits and clear error codes for clients.

Time handling:
- Prefer UTC internally; store broker timestamps and timestamp provenance.
- Monitor NTP and clock drift.

## 13. Data Models & Event Schemas (canonical)
Include schema_version in every event.

Examples:
- OrderSubmitted { schema_version, internalOrderId, clientOrderId, clientId, symbol, side, qty, price, type, tif, timestamp }
- OrderRouted { schema_version, internalOrderId, adapterId, sessionId, sequenceNumber, timestamp }
- ExecutionReport { schema_version, internalOrderId, brokerOrderId, status, filledQty, remainingQty, price, tradeId, timestamp }
- PositionUpdate { schema_version, accountId, symbol, position, pnl, timestamp }

Version & evolve schemas using semantic versioning and provide transformers for backward compatibility.

## 14. API Surface (minimal viable)
- POST /v1/orders -> submit order (returns internalOrderId, status)
- GET /v1/orders/{internalOrderId} -> order status and history
- POST /v1/orders/{internalOrderId}/cancel -> cancel order
- GET /v1/positions -> current positions
- GET /v1/health -> readiness & liveness
- Headers: X-Idempotency-Key accepted and persisted for TTL; rate-limit headers returned.

API contract: JSON schemas, explicit HTTP error codes, and standard rate limit responses.

## 15. FIX Adapter: config & behaviors
- Persist session store (seq nums, timestamps) externally.
- Resend flows: request resend on session re-establishment if seq numbers mismatch.
- Heartbeat policy: configurable thresholds and alerts for missed heartbeats.
- Outgoing message persistence to support retransmits.

## 16. CI/CD & Deployment
- Pipelines: build -> unit tests -> integration tests (mock broker) -> canary deployment -> staged rollout.
- IaC: Terraform for infra; Helm charts for Kubernetes.
- Deploy strategies: canary or blue/green for adapters and orchestrator.
- Smoke tests: automated post-deploy validation hitting sandbox endpoints.

## 17. Incident Response & Disaster Recovery
- Incident steps: detect -> alert -> runbook -> mitigate -> escalate -> resolve.
- Broker outage handling: failover to alternate brokers or buffer orders based on business rules.
- DR: backups of DBs, Kafka topics, and object stores; quarterly restore tests.
- RCA: timeline, impact, remediation, and preventive actions documented.

## 18. Broker Onboarding Checklist
- Obtain sandbox/production credentials and endpoints.
- Acquire FIX spec or REST API docs; confirm supported types and TIFs.
- Symbol mapping and timezone normalization.
- Test logon/heartbeat and sequence handling in sandbox.
- Configure throttles, SLAs, and monitoring expectations.
- Run integration tests, reconciliation checks, and runbook rehearsals.

## 19. Testing Matrix (summary)
- Unit: business/risk logic and schema validation.
- Integration: adapter <-> mock/sandbox broker flows.
- Performance: latency and throughput under target load.
- Fault tolerance: redo/resend, partial fills, disconnects.
- Security: secret rotations, token revocation, pen tests.

## 20. Cost & Resourcing (high level)
- Budget for Kafka, Postgres, K8s compute, observability, and HSMs where necessary.
- Staff: SRE/on-call, integration engineers, compliance analysts, QA.

## 21. Versioning & Governance
- Service API versioning policy and event schema versioning.
- Change governance for risk rules: staging windows, approvals, and audit logs.
- Config change audit trails and rollback policies.

## 22. Appendix — Example Message Flow (expanded)
1. Client POST /orders -> Gateway validates schema, auth, assigns internalOrderId and returns 202.
2. Orchestrator performs synchronous pre-trade risk checks.
3. If passed, OrderSubmitted event persisted and published to outgoing topic.
4. Adapter reads event, translates to broker protocol, persists outgoing message, and sends.
5. Broker ACK/REJECT received by adapter -> ExecutionReport persisted and published; orchestrator updates state and notifies client.
6. Fills append to trade tape; reconciliation compares broker fills and internal events, generating exceptions for mismatches.

## 23. Next Steps / Action Items
- Define exact SLAs and throughput targets.
- Choose first broker(s) and obtain sandbox credentials.
- Implement mock broker emulator and build automated integration test harness.
- Scaffold minimal API, orchestrator, basic risk rules, and a simple FIX/REST adapter in repo.
- Draft operator runbooks and test reconciliation flows end-to-end.

## 24. Execution plan to raise production confidence (from ~60% → target >85%)
Objective: remove major operational unknowns by specifying SLAs, infra sizing heuristics, broker-specific integration rules, SRE runbooks, staffing, and an automated chaos and acceptance test plan.

24.1 SLA & acceptance criteria
- Service-level objectives:
  - Core order routing availability: 99.95% (monthly).
  - API median RTT target: <150ms; P99 budget per adapter (start: 1s retail; 3s institutional/FIX) while optimizing.
  - Reconciliation lag: near-real-time (<5min) for active trading hours; daily full reconciliation complete within 2 hours.
  - Reconciliation mismatch threshold for promotion: <0.01% unmatched volume in canary period.
- Acceptance gates (must pass before moving to next stage):
  - Unit + integration tests 100% pass; end-to-end tests with mock broker pass deterministic scenarios.
  - Load test: system sustains 2x expected peak orders/sec for 30 minutes within latency budgets.
  - Chaos tests: simulated disconnects and seq-gaps without irrecoverable state in 95% of runs.

24.2 Infra sizing & architecture heuristics
- Baseline throughput assumption: estimate orders/sec (O) per client cohort; design for O_peak = 3x projected business peak.
- Kafka: provision partitions = ceil(total_producers*2) and retention for trade tape; enable replication factor >=3.
- Adapters: autoscaled stateless worker pools; keep session state external (Redis/Postgres) to allow horizontal restart.
- Execution path latency budget: API gateway (10-30ms) → Orchestrator (20-50ms) → Adapter enqueue (5-20ms) → Broker RTT (variable).
- Instance sizing examples (starting point):
  - Orchestrator: 4-8 vCPU, 16-32GB RAM, autoscale based on CPU & msg lag.
  - Adapter (per broker heavy): 2-4 vCPU, 8-16GB RAM; pin to low-latency AZ with private connectivity.
  - Kafka cluster: 3+ brokers, SSD-backed, 64GB+, JVM tuned; monitor ISR & under-replicated partitions.
- Observability: 99th percentile metrics retention and alerting windows; budget for Prometheus HA and long-term metrics store.

24.3 Broker-specific integration catalog
- For each broker record:
  - Protocol (FIX/REST/Websocket), supported order types, TIFs, max order size, rate limits, credential model, session quirks (e.g., per-connection seq reset), and expected message RTT.
  - Template: BrokerName { protocol, endpoints(sandbox/prod), rateLimits, seqResetBehavior, idempotencySupport, caveats }
- Operational rule: do not promote integration to production until sandbox shows stable seq handling, resend/gap-fill success rate >99.9% over 24h.

24.4 SRE runbooks & operator playbooks (minimum required)
- Runbook templates (one per alert category):
  - FIX session loss / repeated heartbeat misses: check session store, attempt controlled reconnect, request ResendRequest, escalate if gap > configured threshold.
  - Reconciliation drift > threshold: run targeted replay of event-store; mark suspect orders and pause new order routing to affected broker if required.
  - High rejection/slippage rate: enable kill-switch for the client cohort, notify trading desk, throttle or divert flows.
  - Credential compromise suspected: rotate broker keys, revoke sessions, fail open/closed per policy, escalate security team.
- Emergency procedures: global kill-switch, per-broker pause, warm failover to alternate brokers, and controlled replay instructions.

24.5 Staffing & roles (recommended minimal roster for production)
- Core team for initial production (24/7 coverage via on-call rotation):
  - 1 Product/Trading owner (domain decisions & priority)
  - 2 Integration engineers (adapter + broker onboarding)
  - 2 SREs (runbooks, HA infra, incident triage)
  - 1 Risk engineer (policy & rule book)
  - 1 QA/automation engineer (test harness and CI pipeline)
- Expand as throughput and clients grow; include compliance/ops as needed.

24.6 Chaos, resilience, and testing plan
- Automated chaos scenarios (run in staging and periodically in production canary):
  - Broker disconnects and delayed ACKs.
  - FIX seq gaps and duplicate messages.
  - High rejection rates and partial fill storms.
  - Background load with sudden spikes (traffic surges).
- For each scenario define expected system behavior and acceptance (e.g., orders buffered and replayed within X minutes; no lost fills; alerts trigged).
- Continuous integration includes deterministic replay tests using recorded market data and injected faults.

24.7 Monitoring, dashboards, and SLO burn-down
- Dashboards:
  - Order P99 latency heatmap by adapter.
  - FIX session health panel (seq nums, resend counts, heartbeat misses).
  - Reconciliation panel: unmatched volume, orphan fills, reconciliation lag histogram.
  - Risk panel: blocked orders, limit breaches, velocity events.
- Alerts with severity levels tied to runbooks and SLO burn rate calculations (auto-escalate if burn rate exceeds X).

24.8 Canary & progressive rollout criteria
- Canary window requirements:
  - Start with paper mode (no real funds) for functional validation.
  - Move to small dollar live trades (e.g., 1–5% of typical size) for limited clients.
  - Evaluate metrics for N hours/days: latency, reconciliation mismatches (< threshold), reject/slippage rates.
  - Only promote when all gates pass; otherwise rollback and iterate.

24.9 Concrete next tasks (actionable)
- Populate broker integration catalog for the first target broker (fields in 24.3).
- Define expected orders/sec and simulated traffic profile for load tests.
- Implement mock broker scenarios for the chaos tests list.
- Draft SRE runbooks for top 5 alert categories and test them in staging.
- Schedule a discovery session to finalize SLAs and staffing commitments.

## 25. XM Trading (MetaTrader 5) — integration notes
Note: I cannot browse the web. The notes below reflect common XM/MetaTrader 5 integration patterns and best practices known up to 2024-06. You must verify broker-specific endpoints, APIs, and commercial terms directly with XM (support/documentation).

Overview:
- XM is a retail broker that provides MetaTrader 4 and MetaTrader 5 platforms to clients. Retail connectivity is typically via the MT5 Client (desktop/web/mobile) rather than an open REST API. Some brokers offer institutional FIX or custom APIs on request.

Connectivity options (practical choices):
1) Broker-provided FIX/API (preferred if available)
   - If XM offers an institutional FIX gateway or REST API for execution, request credentials and specification.
   - Pros: lower-latency, standard protocol, session semantics (seq nums), and generally more controllable.
   - Cons: may require business onboarding, minimum volumes, or additional fees.

2) MetaTrader 5 Expert Advisor (EA) bridge (most common for retail)
   - Deploy an MQL5 EA on an MT5 instance (demo or live) that listens for orders via secure WebRequest/HTTP(S) or a lightweight socket bridge, and submits orders locally to MT5.
   - EA posts execution reports back to the orchestration layer (ACKs/fills) via the same secure channel.
   - Pros: no broker-side changes required, works with retail accounts, full access to MT5 order primitives.
   - Cons: EA runs in user-terminal context (requires a running MT5 instance), potential latency, reliance on terminal uptime, security considerations for credentials and network access.

3) Third-party gateway / meta-api providers
   - Use MetaApi, FXCM bridges, or vendor MT5-to-REST bridges that expose a managed API and run the terminal in the cloud.
   - Pros: faster to integrate, managed uptime, optional historical/tick replay features.
   - Cons: third-party dependency, cost, and extra risk surface.

Recommended approach (pragmatic):
- Start with an EA bridge for POC and sandbox testing against XM demo accounts.
- Concurrently evaluate whether XM will grant FIX/institutional access for production. If yes, plan migration to FIX for higher SLAs.

Key integration caveats & mapping
- Account types & execution model: confirm whether XM account uses Market Execution or Instant Execution. Market Execution means the broker executes at market price and may re-quote; Instant expects price match.
- Order types: map internal canonical types to MT5 order primitives (ORDER_TYPE_BUY, SELL, BUY_LIMIT, SELL_LIMIT, STOP, STOP_LIMIT, MARKET, etc.) and handle MT5-specific fields (deviation/slippage, expiration, comments).
- Partial fills: MT5 reports partial fills via trade/result events; handle partial fills and remaining qty logic in orchestration and trade tape.
- Hedging vs netting: verify account mode (hedging allows multiple offsetting positions; netting consolidates). This affects how positions and cancels are represented.
- Symbol conventions and contract specifications: fetch symbol info (tick_size, lot_size, contract_size, margin_currency) from MT5 MarketInfo and normalize to internal symbol registry.
- Time zones & DST: MT5 server time is broker-dependent; record both broker timestamps and local UTC, and include timestamp provenance in events.
- Tick & historical data: MT5 provides tick/history via terminal APIs; if you need continuous market data for risk checks, use consolidated market-data ingress and subscribe to broker feed or third-party tick providers.
- Rate limits & throttles: demo and retail environments often throttle connection rates; design EA/adapter to respect limits and implement retries/backoff.

Security & operational points
- EA credentials and access: never hardcode secrets; use encrypted config and rotate keys. Limit allowed callback URLs (MT5 WebRequest requires explicit domain whitelisting).
- Secure channel: use HTTPS with strong TLS and mutual auth where possible. Sign/verify messages using HMAC if EA supports header signing.
- Terminal availability: EA approach requires a running MT5 terminal; plan for process monitoring, auto-restart, and heartbeats. Consider hosted terminals on dedicated VMs with private networking.
- Forensic logging: persist raw MT5 messages and EA logs (encrypted) to trade tape for reconciliation and audit.

Testing & sandbox checklist for XM/MT5
- Obtain XM demo credentials and server endpoints.
- Validate symbol list, contract specs, and time zone.
- Deploy EA in demo terminal and test: logon, order placement, cancels, partial fills, rejection scenarios, and reconnects.
- Run deterministic scenarios: seq-gaps, network disconnects, delayed fills, and partial-fill storms.
- Validate reconciliation by comparing EA-reported ExecutionReports with MT5 terminal history and broker reports.

Actionable next steps (for repo)
- I will create broker_catalog/xm_mt5.md capturing the above details, a recommended EA bridge architecture diagram, and an integration-checklist.
- I can scaffold an MQL5 EA template (skeleton with secure WebRequest calls and message handlers) plus a small Python mock-orchestrator that accepts EA callbacks and simulates order-state transitions.

Confirmation and data needed from you
- Confirm you want XM as first broker (you already did) and whether we should pursue EA bridge POC or request institutional FIX from XM.
- If you have XM demo credentials or an XM account rep contact, provide them (do NOT paste secrets into chat; use secure channel). Otherwise I will proceed with a generic POC.

End of document.
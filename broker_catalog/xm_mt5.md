# XM Trading - MetaTrader 5 Integration Catalog

IMPORTANT: This document consolidates public facts about XM + MetaTrader 5 integration and includes explicit verification checkpoints. I cannot access private sandbox credentials or live broker support channels; please verify the fields marked "[VERIFY]" with XM support or your account manager.

## Summary
Target broker: XM (MetaTrader 5)
Primary connectivity model: MetaTrader 5 terminal running Expert Advisors (EAs) that communicate outbound via HTTP(S) WebRequest or WebSocket to our orchestrator. XM does not publicly expose a standard FIX endpoint for retail MT5 accounts in most regions; confirm with XM for institutional/FIX access.

## Key facts (publicly verifiable)
- MetaTrader 5 supports EAs written in MQL5 which can perform trading operations and HTTP(S) outbound calls using `WebRequest`.
- MetaTrader platform supports multiple execution modes: Instant, Request, Market, and Exchange execution.
- EAs can be run on a client terminal or via MetaTrader Virtual Hosting (VPS) for 24/7 operation.
- MQL5 reference and WebRequest docs: https://www.mql5.com/en/docs and https://www.metatrader5.com/en/terminal/help

## Connectivity options
1. EA WebRequest -> Orchestrator (recommended for initial POC)
   - Pros: quick to implement, no FIX gateway required, uses standard MT5 functionality (WebRequest), low friction for retail XM accounts.
   - Cons: depends on MT5 terminal availability (VPS recommended), limited control over low-latency guarantees, must secure WebRequest endpoints and manage client credentials in EA.

2. FIX / Broker Gateway (verify with XM)
   - Pros: standardized institutional protocol, session-level sequencing, lower-latency options available for institutional clients.
   - Cons: likely requires institutional onboarding; confirm availability, costs, and FIX version with XM. [VERIFY]

3. Bridge solutions (MT5 bridge, third-party gateway)
   - Pros: existing connectors for FIX <-> MT5 or broker-provided bridges.
   - Cons: added complexity and potential licensing.

## EA (MQL5) constraints and best practices
- WebRequest: EAs may use `WebRequest()` to send/receive HTTP(S) requests. The platform requires listing allowed URLs in the terminal options for security.
- Required permissions: when using WebRequest, users must add authorized URLs in `Tools -> Options -> Expert Advisors -> Allow WebRequest for listed URLs`.
- Execution & slippage: MT5 may apply slippage rules per account; always design the orchestrator to handle partial fills and rejections.
- Threading: MQL5 runs in the EA thread model; avoid long blocking calls in tick handlers — use timers or async patterns inside EA logic.

## Order model & mapping
- MT5 supports market, limit, stop, and various pending orders; use canonical order fields: side, qty, price, type, time-in-force where supported.
- BrokerOrderId: MT5 will return ticket IDs for orders executed via terminal; ensure mapping from EA-submitted requests to returned ticket ids in your event-store.

## Security considerations
- Use HTTPS endpoints with TLS 1.2+ and mTLS if EA supports client certificates (MQL5 WebRequest supports standard HTTP headers; client certs may not be available — verify). [VERIFY]
- Do not store raw API keys in EA source or repository; use EA input parameters and platform-provided protected storage if possible.
- Audit: log all requests, responses, and EA actions to the event-store. Encrypt any archived raw messages.

## Sandbox & testing
- XM provides demo accounts — use a demo/dedicated account for integration testing. [VERIFY exact sandbox URLs and account provisioning with XM]
- Use MetaTrader Virtual Hosting (VPS) to run EAs 24/7 for integration testing.

## Implementation checklist (POC)
- [ ] Confirm if XM offers a FIX/REST API for institutional use; else proceed with EA WebRequest model. [VERIFY]
- [ ] Create a demo XM account and test EA WebRequest outbound to a local test endpoint.
- [ ] Draft MQL5 EA skeleton and ensure WebRequest allowed URL is set in terminal options.
- [ ] Implement orchestrator endpoint with idempotency, auth, and TLS; validate against MT5 WebRequest responses.
- [ ] Build mock orchestrator for deterministic scenario testing (ACKs, partial fills, rejects, sequence gaps).

## Onboarding fields to verify with XM
- Sandbox/prod endpoints
- Demo account provisioning process
- FIX gateway availability and details (host, port, FIX version, credentials) [VERIFY]
- Rate limits and usage policies [VERIFY]
- Maximum order size, allowed instruments, and available TIFs for retail/demo vs institutional [VERIFY]

## References
- MQL5 docs: https://www.mql5.com/en/docs
- MetaTrader 5 Help: https://www.metatrader5.com/en/terminal/help
- XM trading platforms page: https://www.xm.com/trading-platforms/metatrader-5 (verify availability)


---

Last updated: 2025-10-24
Notes: This catalog entry should be validated against XM support during onboarding. Replace [VERIFY] placeholders with confirmed values and add sample requests/responses from XM when available.

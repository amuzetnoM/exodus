# EXODUS

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.120.0-009688.svg)](https://fastapi.tiangolo.com)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Linting: flake8](https://img.shields.io/badge/linting-flake8-informational)](https://flake8.pycqa.org/)
[![Type checking: mypy](https://img.shields.io/badge/type_checking-mypy-blue)](http://mypy-lang.org/)

**EXODUS** is a broker integration and order-routing platform designed for safe, auditable, and low-latency trading across retail and institutional broker connectivity. The platform centralizes risk control, provides durable order state and reconciliation, and exposes a normalized API for clients and trading strategies.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [Technology Stack](#technology-stack)
5. [Project Structure](#project-structure)
6. [Prerequisites](#prerequisites)
7. [Installation](#installation)
8. [Configuration](#configuration)
9. [Usage](#usage)
10. [API Reference](#api-reference)
11. [Testing](#testing)
12. [Deployment](#deployment)
13. [Monitoring and Observability](#monitoring-and-observability)
14. [Security](#security)
15. [Compliance and Audit](#compliance-and-audit)
16. [Troubleshooting](#troubleshooting)
17. [Contributing](#contributing)
18. [License](#license)
19. [References](#references)

---

## Overview

### Purpose

EXODUS provides a reliable, auditable, and low-latency bridge between client trading systems and multiple brokerages. It supports core order types (market, limit, stop, IOC, FOK, pegged, conditional), enforces safety via layered pre-trade risk controls and operator kill-switches, and guarantees traceability for compliance and reconciliation.

### Design Priorities

- **Correctness**: Event-sourced order lifecycle ensures deterministic replay and audit.
- **Recoverability**: Durable event persistence and idempotency enable safe restarts and failover.
- **Observability**: Comprehensive logging, metrics, and distributed tracing.
- **Operational Simplicity**: Containerized microservices with clear separation of concerns.

### Key Capabilities

- Multi-broker connectivity (FIX, REST, WebSocket, MetaTrader 5 bridge)
- Centralized pre-trade risk management (position limits, margin checks, velocity controls)
- Event-sourced order state with append-only trade tape
- Idempotency and deduplication for guaranteed-once semantics
- Real-time reconciliation and end-of-day position checks
- Operator UI for manual interventions, kill-switches, and configuration management
- Compliance-ready audit trails and immutable logs

---

## Architecture

### High-Level Components

```
┌─────────────────┐
│ Client Systems  │
│ / Strategies    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│         Client-Facing API / Gateway (REST/WS)           │
│  (Auth, Quotas, Schema Validation, Rate Limiting)       │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│      Order Router / Orchestrator                        │
│  (Validation, Risk Checks, Routing, Correlation)        │
└────────┬────────────────────────────────────────────────┘
         │
         ├──────────┬──────────┬──────────────────┐
         ▼          ▼          ▼                  ▼
    ┌────────┐ ┌────────┐ ┌────────┐      ┌────────────┐
    │FIX     │ │REST    │ │MT5     │ ...  │Risk Engine │
    │Adapter │ │Adapter │ │Bridge  │      │(Pre-Trade) │
    └────┬───┘ └────┬───┘ └────┬───┘      └────────────┘
         │          │          │
         ▼          ▼          ▼
    ┌──────────────────────────────┐
    │       Broker Network         │
    └──────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Event Store / Trade Tape (Kafka / Append-Only DB)      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Persistence & Reconciliation (Postgres, Ledgers)       │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Monitoring / Alerting (Prometheus, Grafana, OTel)      │
└─────────────────────────────────────────────────────────┘
```

### Connectivity Models

- **FIX Protocol** (v4.2–5.0): Institutional/low-latency using QuickFIX/QuickFIX/J
- **REST/HTTP(s)**: Retail broker APIs with HMAC/OAuth signing
- **WebSocket**: Real-time market data and order updates
- **MetaTrader 5 Bridge**: Expert Advisors (EAs) via WebRequest callbacks to orchestrator
- **File Transfer (SFTP)**: Batch fills and end-of-day reports

---

## Features

### Order Management

- Support for market, limit, stop, IOC, FOK, pegged, and conditional orders
- Idempotency via `clientOrderId` or `X-Idempotency-Key` header
- Event-sourced order lifecycle with canonical state transitions
- Partial fill handling and child order routing

### Risk Management

- Pre-trade checks: buying power, margin, position limits, notional caps, price sanity
- Velocity controls: orders/sec throttling per client, symbol, and global
- Circuit breakers: automatic and manual kill-switches
- Configurable policy store with audit trails for rule changes

### Reconciliation

- Real-time matching of outbound order events to broker execution reports
- End-of-day reconciliation with broker statements
- Automated alerts for unmatched fills, orphan orders, and reconciliation drift

### Monitoring and Observability

- Metrics: latency (P50/P90/P99), throughput, rejection rates, health indicators
- Structured JSON logs with correlation IDs, order IDs, and session IDs
- Distributed tracing via OpenTelemetry
- Grafana dashboards and Prometheus alerts

### Compliance and Audit

- Immutable audit trail: all requests, transforms, broker messages, risk decisions, operator actions
- WORM storage for regulatory retention (7+ years default)
- Encryption at rest and in transit; KMS-managed keys
- Access control and audit logs for data access

---

## Technology Stack

### Core Runtime

- **Python 3.12**: Primary application runtime
- **FastAPI**: High-performance async web framework
- **Uvicorn**: ASGI server with uvloop for low-latency event loop
- **Pydantic**: Data validation and settings management

### Data and Messaging

- **Kafka**: Durable event streaming and message bus
- **PostgreSQL**: Ledgers, positions, compliance exports, snapshots
- **Redis**: Rate limiting counters and ephemeral state

### Observability

- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards
- **OpenTelemetry**: Distributed tracing and instrumentation
- **ELK / Opensearch**: Log aggregation and search

### Development and Quality

- **pytest**: Unit and integration testing
- **mypy**: Static type checking
- **flake8**: Code linting
- **bandit**: Security vulnerability scanning
- **pip-audit**: Dependency vulnerability auditing

### Deployment

- **Docker**: Containerization
- **Kubernetes / Helm**: Orchestration and deployment
- **Terraform**: Infrastructure as Code (IaC)
- **GitHub Actions**: CI/CD pipelines

---

## Project Structure

```
exodus/
├── agent/                        # Agent blueprints and integration specs
│   └── exodus_arc.md             # Exodus ARC strategy integration design
├── broker_catalog/               # Broker integration catalogs
│   └── xm_mt5.md                 # XM Trading + MT5 integration guide
├── data/                         # Runtime data (events, logs) - gitignored
├── orchestrator/                 # Core orchestrator service
│   └── app.py                    # FastAPI orchestrator app
├── runbooks/                     # Operational runbooks
│   └── xm_runbooks.md            # XM/MT5 SRE runbooks
├── slas/                         # Service-level agreements
│   └── xm_slas.md                # XM adapter SLA definitions
├── tests/                        # Test suite
│   └── e2e_xm.md                 # End-to-end test scenarios for XM
├── xm/                           # XM-specific artifacts
│   ├── mql5_ea_template.mq5      # MQL5 EA skeleton for MT5 bridge
│   └── mock_orchestrator.py      # Mock orchestrator for E2E testing
├── .gitignore                    # Git ignore rules
├── brokerage_platform_design.md  # Comprehensive platform design document
├── cmd_cdx.md                    # Command codex (all platform commands)
├── README.md                     # This file
└── requirements.txt              # Python dependencies
```

---

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+, RHEL 8+), macOS 11+, or Windows 10+ with WSL2
- **Python**: 3.12 or later
- **Memory**: Minimum 4 GB RAM (8 GB+ recommended for production)
- **Disk**: 20 GB+ for logs, event storage, and dependencies
- **Network**: Stable internet connection with low latency to broker endpoints

### External Dependencies

- **Broker Accounts**: Live or sandbox accounts with API access (e.g., XM Trading, Interactive Brokers, OANDA)
- **MetaTrader 5** (optional): For MT5 bridge integrations
- **Kafka**: Event streaming (can be self-hosted or use managed service)
- **PostgreSQL**: Relational database for ledgers and snapshots
- **Redis** (optional): For rate limiting and caching

### Development Tools

- **Git**: Version control
- **Docker**: For containerization (optional but recommended)
- **kubectl**: Kubernetes CLI (for production deployments)
- **Terraform**: Infrastructure provisioning (optional)

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/amuzetnoM/exodus.git
cd exodus
```

### 2. Create and Activate Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Upgrade pip and Install Dependencies

```bash
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 4. Verify Installation

```bash
python -m pip check
python -m pip_audit  # Check for known vulnerabilities
```

### 5. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Orchestrator Configuration
ORCHESTRATOR_HOST=127.0.0.1
ORCHESTRATOR_PORT=8000

# Broker Configuration (example for XM)
XM_BROKER_URL=https://api.xm.com/v1
XM_API_KEY=your_api_key_here
XM_API_SECRET=your_api_secret_here

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/exodus

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Redis Configuration (optional)
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Security
SECRET_KEY=your_secret_key_for_jwt_signing
```

### 6. Initialize Database (if using PostgreSQL)

```bash
# Create database
createdb exodus

# Run migrations (if applicable)
# python -m alembic upgrade head
```

---

## Configuration

### Orchestrator Settings

The orchestrator configuration is managed via environment variables and `.env` file. Key settings:

- **ORCHESTRATOR_HOST**: Bind address (default: `127.0.0.1`)
- **ORCHESTRATOR_PORT**: Bind port (default: `8000`)
- **LOG_LEVEL**: Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
- **EVENT_STORE_PATH**: Path to event persistence file (default: `data/events.jsonl`)

### Broker Adapter Configuration

Each broker adapter requires specific credentials and endpoints. Refer to `broker_catalog/xm_mt5.md` for XM configuration and `brokerage_platform_design.md` for general adapter setup.

#### XM Trading MT5 Configuration

EXODUS supports XM Trading via MetaTrader 5 bridge. Configure your XM credentials in the `.env` file:

```bash
# XM Trading MT5 Credentials
XM_ACCOUNT_ID=your_account_number
XM_SERVER=XMGlobal-MT5 6
XM_PASSWORD=your_mt5_password

# XM API Configuration
XM_BROKER_URL=https://mt5.xmtrading.com
XM_API_KEY=${XM_ACCOUNT_ID}
XM_API_SECRET=${XM_PASSWORD}
```

**Setup Steps:**

1. **Create `.env` file** in the project root with your XM credentials
2. **Ensure `.env` is gitignored** (already configured in `.gitignore`)
3. **Start the orchestrator** - it will automatically detect and validate XM credentials
4. **Check connectivity** via `/status` endpoint or startup logs

**Security Notes:**
- Never commit `.env` files to version control
- Use strong, unique passwords for MT5 accounts
- Enable 2FA on your XM trading account when available
- Regularly rotate API credentials

**Connectivity Verification:**
The orchestrator performs connectivity checks on startup:
- Validates credential presence and format
- Confirms MT5 server configuration
- Registers XM adapter if checks pass
- Logs detailed status information

Example startup output:
```
Checking XM MT5 connectivity for account 301073553 on server XMGlobal-MT5 6
✓ XM MT5 credentials configured for account 301073553
✓ MT5 Server: XMGlobal-MT5 6
✓ Connectivity check passed (credentials validated)
✓ XM MT5 broker registered successfully for account 301073553
```

### Risk Engine Configuration

Risk rules are configurable via a policy store (to be implemented). Example rules:

- Max position size per symbol: 100,000 units
- Max notional exposure: $1,000,000
- Velocity limit: 10 orders/sec per client
- Circuit breaker: Auto-disable on 5 consecutive rejections

---

## Usage

### Starting the Orchestrator

```bash
# Activate virtual environment
source .venv/bin/activate

# Start the orchestrator
python orchestrator/app.py
```

The orchestrator will start on `http://127.0.0.1:8000`.

### API Endpoints

#### Submit Order

```bash
POST /api/v1/orders
Content-Type: application/json
X-Idempotency-Key: unique-key-123

{
  "clientOrderId": "client-order-001",
  "clientId": "client-alpha",
  "symbol": "EURUSD",
  "qty": 10000,
  "price": 1.1234,
  "side": "buy"
}
```

**Response:**

```json
{
  "status": "accepted",
  "internalOrderId": "int-1729800000000"
}
```

#### Get Order Status

```bash
GET /api/v1/orders/{internalOrderId}
```

#### Health Check

```bash
GET /health
```

**Response:**

```json
{
  "status": "ok"
}
```

#### Metrics (Placeholder)

```bash
GET /metrics
```

---

## API Reference

### POST /api/v1/orders

Submit a new order.

**Request Body:**

| Field           | Type   | Required | Description                          |
|-----------------|--------|----------|--------------------------------------|
| clientOrderId   | string | No       | Client-supplied order ID             |
| clientId        | string | No       | Client identifier                    |
| symbol          | string | Yes      | Trading symbol (e.g., EURUSD)        |
| qty             | int    | Yes      | Order quantity                       |
| price           | float  | Yes      | Order price                          |
| side            | string | Yes      | Order side: `buy` or `sell`          |

**Headers:**

- `X-Idempotency-Key` (optional): Idempotency key for deduplication

**Response:**

- `200 OK`: Order accepted
- `400 Bad Request`: Validation error
- `409 Conflict`: Duplicate order (idempotency key matched)

### GET /api/v1/orders/{internalOrderId}

Retrieve order status and history.

**Response:**

- `200 OK`: Order details
- `404 Not Found`: Order not found

### POST /api/v1/orders/{internalOrderId}/cancel

Cancel an order.

**Response:**

- `200 OK`: Cancel request accepted
- `404 Not Found`: Order not found

### GET /health

Health check endpoint.

**Response:**

```json
{
  "status": "ok"
}
```

### GET /metrics

Metrics endpoint (placeholder).

**Response:**

```json
{
  "uptime_seconds": 0
}
```

---

## Testing

### Unit Tests

Run unit tests using `pytest`:

```bash
pytest tests/
```

### Integration Tests

Integration tests validate adapter behavior against mock or sandbox broker endpoints.

```bash
# Start mock orchestrator
python xm/mock_orchestrator.py &

# Run integration tests
pytest tests/e2e_xm.md
```

### End-to-End Tests

Refer to `tests/e2e_xm.md` for detailed E2E test scenarios and acceptance criteria.

### Security Scanning

```bash
# Run bandit security scanner
bandit -r orchestrator/ xm/

# Audit dependencies for vulnerabilities
pip-audit
```

### Linting and Type Checking

```bash
# Run flake8 linter
flake8 orchestrator/ xm/

# Run mypy type checker
mypy orchestrator/ xm/
```

---

## Deployment

### Docker

#### Build Docker Image

```bash
docker build -t exodus-orchestrator:latest .
```

#### Run Container

```bash
docker run -d \
  -p 8000:8000 \
  --env-file .env \
  --name exodus-orchestrator \
  exodus-orchestrator:latest
```

### Kubernetes

#### Deploy Using Helm

```bash
helm install exodus ./charts/exodus \
  --namespace exodus \
  --create-namespace \
  --values values.yaml
```

### Infrastructure as Code (Terraform)

Provision cloud resources using Terraform:

```bash
cd terraform/
terraform init
terraform plan
terraform apply
```

---

## Monitoring and Observability

### Metrics

EXODUS exposes Prometheus-compatible metrics at `/metrics`:

- **exodus_orders_total**: Total orders submitted
- **exodus_orders_rejected_total**: Total orders rejected
- **exodus_order_latency_seconds**: Order processing latency (histogram)
- **exodus_reconciliation_drift_total**: Reconciliation mismatches

### Dashboards

Import the provided Grafana dashboard JSON from `monitoring/grafana_dashboard.json` (to be added).

### Alerts

Configure Prometheus alerts in `monitoring/alerts.yml` (to be added):

- High order rejection rate
- Reconciliation drift exceeds threshold
- Adapter connection failures

### Distributed Tracing

EXODUS integrates with OpenTelemetry for distributed tracing. Configure trace export to Jaeger or Zipkin via environment variables.

---

## Security

### Secrets Management

- Store API keys and secrets in **HashiCorp Vault** or **AWS Secrets Manager**
- Use environment variables for non-sensitive configuration
- Rotate secrets periodically and audit access

### Transport Security

- Use **TLS 1.2+** for all broker connections
- Enable **mTLS** where supported
- Validate SSL certificates

### Access Control

- Implement **role-based access control (RBAC)** for API endpoints
- Use **JWT** for authentication and authorization
- Audit all access and modifications

### Vulnerability Management

- Run `pip-audit` regularly to detect dependency vulnerabilities
- Apply security patches promptly
- Monitor CVE databases for affected packages

---

## Compliance and Audit

### Immutable Audit Trail

All events are persisted to an append-only event store (`data/events.jsonl`) and Kafka topics. Events include:

- Client requests
- Order state transitions
- Broker messages (sent/received)
- Risk decisions
- Operator actions

### Retention Policies

- Default retention: **7 years**
- Adjust per jurisdiction requirements
- Archive to WORM storage (e.g., AWS S3 Object Lock)

### Regulatory Reporting

Generate compliance reports from the event store:

```bash
# Example: Export orders for a date range
python scripts/export_orders.py --start-date 2025-01-01 --end-date 2025-01-31 --output report.csv
```

---

## Troubleshooting

### Common Issues

#### 1. Orchestrator Fails to Start

**Symptoms**: Orchestrator exits immediately or logs connection errors.

**Resolution**:
- Check `.env` file for correct configuration
- Verify database and Kafka connectivity
- Review logs in `logs/` directory

#### 2. Orders Not Being Accepted

**Symptoms**: Orders return `400 Bad Request` or `409 Conflict`.

**Resolution**:
- Validate request payload against API schema
- Ensure `clientOrderId` or `X-Idempotency-Key` is unique
- Check orchestrator logs for validation errors

#### 3. Reconciliation Drift

**Symptoms**: Alerts for unmatched fills or orphan orders.

**Resolution**:
- Review reconciliation logs
- Verify broker API responses
- Check for clock drift or network latency issues

### Logs

- **Orchestrator logs**: `logs/orchestrator.log`
- **Event store**: `data/events.jsonl`
- **Adapter logs**: `logs/adapter_{adapter_name}.log`

### Support

For further assistance:
- Review documentation in `brokerage_platform_design.md`
- Check runbooks in `runbooks/`
- Open an issue on GitHub

---

## Contributing

We welcome contributions to EXODUS. Please follow these guidelines:

1. **Fork the repository** and create a feature branch
2. **Write tests** for new features or bug fixes
3. **Ensure code passes linting and type checks**:
   ```bash
   flake8 .
   mypy .
   ```
4. **Run security scans**:
   ```bash
   bandit -r .
   pip-audit
   ```
5. **Submit a pull request** with a clear description

### Code Style

- Follow **PEP 8** conventions
- Use **type hints** for all functions
- Write **docstrings** for public APIs

### Commit Messages

Use conventional commit format:
```
feat: add support for limit orders
fix: resolve idempotency key collision
docs: update API reference
```

---

## License

EXODUS is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## References

### Documentation

- [Brokerage Platform Design](brokerage_platform_design.md)
- [XM MT5 Integration Catalog](broker_catalog/xm_mt5.md)
- [Exodus ARC Strategy Blueprint](agent/exodus_arc.md)
- [Command Codex](cmd_cdx.md)

### External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [MetaTrader 5 Terminal Help](https://www.metatrader5.com/en/terminal/help)
- [MQL5 Reference](https://www.mql5.com/en/docs)
- [QuickFIX Documentation](http://www.quickfixengine.org)
- [OpenTelemetry](https://opentelemetry.io)
- [Prometheus](https://prometheus.io)
- [Grafana](https://grafana.com)

### Community

- **GitHub Repository**: [https://github.com/amuzetnoM/exodus](https://github.com/amuzetnoM/exodus)
- **Issues**: Report bugs and request features on GitHub Issues
- **Discussions**: Join discussions on GitHub Discussions

---

**Built with precision. Deployed with confidence. Monitored with clarity.**

---

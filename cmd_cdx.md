# Command Codex (cmd_cdx.md)

Complete reference of all commands used in the EXODUS platform for development, testing, deployment, monitoring, and operations.

---

## Table of Contents

1. [Python Environment Management](#python-environment-management)
2. [Dependency Management](#dependency-management)
3. [Git Operations](#git-operations)
4. [Development](#development)
5. [Testing](#testing)
6. [Security and Auditing](#security-and-auditing)
7. [Code Quality](#code-quality)
8. [Running the Orchestrator](#running-the-orchestrator)
9. [API Testing](#api-testing)
10. [MetaTrader 5 Operations](#metatrader-5-operations)
11. [Database Operations](#database-operations)
12. [Kafka Operations](#kafka-operations)
13. [Docker Operations](#docker-operations)
14. [Kubernetes Operations](#kubernetes-operations)
15. [Monitoring and Observability](#monitoring-and-observability)
16. [Backup and Recovery](#backup-and-recovery)
17. [Deployment](#deployment)
18. [Troubleshooting](#troubleshooting)

---

## Python Environment Management

### Create Virtual Environment

```bash
# Create venv in .venv directory
python3 -m venv .venv

# Create venv with specific Python version
python3.12 -m venv .venv
```

### Activate Virtual Environment

```bash
# Linux/macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (cmd.exe)
.venv\Scripts\activate.bat
```

### Deactivate Virtual Environment

```bash
deactivate
```

### Verify Python Version

```bash
python --version
python -c 'import sys; print(sys.executable)'
```

### Check Active Environment

```bash
which python  # Linux/macOS
where python  # Windows
```

---

## Dependency Management

### Install Dependencies from requirements.txt

```bash
# Standard install
pip install -r requirements.txt

# Upgrade pip first (recommended)
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Install Individual Packages

```bash
# Install latest version
pip install fastapi

# Install specific version
pip install fastapi==0.120.0

# Install with extras
pip install uvicorn[standard]
```

### Upgrade Packages

```bash
# Upgrade single package
pip install --upgrade fastapi

# Upgrade multiple packages
pip install --upgrade fastapi uvicorn requests

# Upgrade all packages (use with caution)
pip list --outdated
pip install --upgrade $(pip freeze | cut -d '=' -f 1)
```

### List Installed Packages

```bash
# List all packages
pip list

# List outdated packages
pip list --outdated

# Show package details
pip show fastapi

# List packages with tree view
pip install pipdeptree
pipdeptree
```

### Check Dependencies

```bash
# Verify no broken dependencies
pip check

# Show dependency tree
pipdeptree --reverse
```

### Freeze Requirements

```bash
# Generate requirements.txt from current environment
pip freeze > requirements.txt

# Generate with only top-level packages (using pip-tools)
pip install pip-tools
pip-compile requirements.in
```

### Uninstall Packages

```bash
# Uninstall single package
pip uninstall fastapi

# Uninstall all packages in requirements.txt
pip uninstall -r requirements.txt -y
```

---

## Git Operations

### Clone Repository

```bash
# Clone via HTTPS
git clone https://github.com/amuzetnoM/exodus.git

# Clone via SSH
git clone git@github.com:amuzetnoM/exodus.git

# Clone specific branch
git clone -b main https://github.com/amuzetnoM/exodus.git
```

### Branch Management

```bash
# List branches
git branch                # Local branches
git branch -r             # Remote branches
git branch -a             # All branches

# Create new branch
git checkout -b feature/new-adapter

# Switch branches
git checkout main
git switch main           # Modern alternative

# Delete branch
git branch -d feature/old-branch      # Local
git push origin --delete feature/old-branch  # Remote

# Rename branch
git branch -m old-name new-name
```

### Merge Operations

```bash
# Merge branch into current branch
git merge feature/new-adapter

# Abort merge
git merge --abort

# Merge with squash
git merge --squash feature/new-adapter
git commit -m "Merge feature"
```

### Commit Operations

```bash
# Stage changes
git add .
git add file.py

# Commit changes
git commit -m "feat: add new adapter"

# Amend last commit
git commit --amend
git commit --amend --no-edit

# Commit with detailed message
git commit -m "feat: add limit order support" -m "Detailed description here"
```

### Push and Pull

```bash
# Push to remote
git push origin main

# Force push (use with caution)
git push --force-with-lease

# Pull from remote
git pull origin main

# Pull with rebase
git pull --rebase origin main
```

### Status and Diff

```bash
# Check status
git status

# View changes
git diff                  # Unstaged changes
git diff --staged         # Staged changes
git diff HEAD             # All changes

# View commit history
git log
git log --oneline
git log --graph --oneline --all
```

### Stash Operations

```bash
# Stash changes
git stash
git stash save "Work in progress on feature"

# List stashes
git stash list

# Apply stash
git stash apply
git stash apply stash@{0}

# Pop stash (apply and remove)
git stash pop

# Drop stash
git stash drop stash@{0}
```

### Reset and Revert

```bash
# Unstage file
git reset HEAD file.py

# Soft reset (keep changes)
git reset --soft HEAD~1

# Hard reset (discard changes)
git reset --hard HEAD~1

# Revert commit
git revert <commit-hash>
```

### Tags

```bash
# Create tag
git tag v1.0.0
git tag -a v1.0.0 -m "Release version 1.0.0"

# List tags
git tag
git tag -l "v1.*"

# Push tags
git push origin v1.0.0
git push origin --tags

# Delete tag
git tag -d v1.0.0
git push origin --delete v1.0.0
```

---

## Development

### Project Setup

```bash
# Complete setup from scratch
git clone https://github.com/amuzetnoM/exodus.git
cd exodus
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Run Development Server

```bash
# Start orchestrator with auto-reload
uvicorn orchestrator.app:app --reload --host 127.0.0.1 --port 8000

# Start with custom log level
uvicorn orchestrator.app:app --reload --log-level debug

# Start on all interfaces
uvicorn orchestrator.app:app --host 0.0.0.0 --port 8000
```

### Run Mock Orchestrator

```bash
# Start mock orchestrator for testing
python xm/mock_orchestrator.py

# Run in background
python xm/mock_orchestrator.py &

# Stop background process
pkill -f mock_orchestrator.py
```

---

## Testing

### Run Unit Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_orchestrator.py

# Run specific test
pytest tests/test_orchestrator.py::test_order_submission

# Run with coverage
pytest --cov=orchestrator --cov-report=html
pytest --cov=orchestrator --cov-report=term-missing
```

### Run Integration Tests

```bash
# Run integration tests
pytest tests/integration/

# Run with markers
pytest -m integration

# Run excluding certain tests
pytest -m "not slow"
```

### Run End-to-End Tests

```bash
# Run E2E tests against staging
pytest tests/e2e/ --env=staging

# Run with retries for flaky tests
pytest tests/e2e/ --reruns 3
```

### Test Options

```bash
# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf

# Show local variables on failure
pytest -l

# Parallel execution
pytest -n auto  # Requires pytest-xdist
```

---

## Security and Auditing

### Vulnerability Scanning

```bash
# Audit dependencies for known vulnerabilities
pip-audit

# Audit with output to file
pip-audit --output audit-report.json --format json

# Audit specific requirements file
pip-audit -r requirements.txt

# Skip certain vulnerabilities
pip-audit --ignore-vuln GHSA-xxxx-yyyy-zzzz
```

### Security Scanning with Bandit

```bash
# Scan entire project
bandit -r .

# Scan specific directory
bandit -r orchestrator/

# Scan with specific tests
bandit -r . -t B201,B301

# Output to file
bandit -r . -f json -o bandit-report.json

# Scan with severity filter
bandit -r . -ll  # Only low level and above
bandit -r . -lll # Only high severity
```

### Check for Secrets

```bash
# Install and run gitleaks (if available)
gitleaks detect --source . --verbose

# Install and run truffleHog
trufflehog filesystem . --json
```

---

## Code Quality

### Linting with flake8

```bash
# Lint entire project
flake8 .

# Lint specific directory
flake8 orchestrator/

# Lint with custom config
flake8 --config=.flake8

# Lint with specific rules
flake8 --select=E,W,F

# Show statistics
flake8 --statistics --count

# Output to file
flake8 --output-file=flake8-report.txt
```

### Type Checking with mypy

```bash
# Type check entire project
mypy .

# Type check specific module
mypy orchestrator/

# Type check with strict mode
mypy --strict orchestrator/

# Type check with specific config
mypy --config-file=mypy.ini

# Generate type coverage report
mypy --html-report=mypy-report/
```

### Code Formatting with Black

```bash
# Format entire project
black .

# Check formatting without changes
black --check .

# Format specific file
black orchestrator/app.py

# Show diff
black --diff orchestrator/app.py
```

### Import Sorting with isort

```bash
# Sort imports
isort .

# Check import sorting
isort --check-only .

# Show diff
isort --diff .
```

---

## Running the Orchestrator

### Start Orchestrator

```bash
# Activate environment and start
source .venv/bin/activate
python orchestrator/app.py

# Or using uvicorn directly
uvicorn orchestrator.app:app --host 127.0.0.1 --port 8000

# Start with custom workers (production)
uvicorn orchestrator.app:app --host 0.0.0.0 --port 8000 --workers 4

# Start with SSL
uvicorn orchestrator.app:app --ssl-keyfile=key.pem --ssl-certfile=cert.pem
```

### Environment-Specific Startup

```bash
# Development
export ENV=development
uvicorn orchestrator.app:app --reload

# Staging
export ENV=staging
uvicorn orchestrator.app:app --host 0.0.0.0 --port 8000

# Production
export ENV=production
uvicorn orchestrator.app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Background Execution

```bash
# Run in background
nohup uvicorn orchestrator.app:app --host 0.0.0.0 --port 8000 > orchestrator.log 2>&1 &

# Using screen
screen -S orchestrator
uvicorn orchestrator.app:app --host 0.0.0.0 --port 8000
# Ctrl+A, D to detach
# screen -r orchestrator to reattach

# Using systemd (create service file)
sudo systemctl start exodus-orchestrator
sudo systemctl enable exodus-orchestrator
```

---

## API Testing

### Health Check

```bash
# Check health endpoint
curl http://localhost:8000/health

# With JSON formatting
curl http://localhost:8000/health | jq
```

### Submit Order

```bash
# Submit market order
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: $(uuidgen)" \
  -d '{
    "clientOrderId": "test-001",
    "clientId": "client-alpha",
    "symbol": "EURUSD",
    "qty": 10000,
    "price": 1.1234,
    "side": "buy"
  }'

# Submit with authentication
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Idempotency-Key: test-key-001" \
  -d @order_payload.json
```

### Get Order Status

```bash
# Get specific order
curl http://localhost:8000/api/v1/orders/int-1729800000000

# Get all orders
curl http://localhost:8000/api/v1/orders

# Get with query parameters
curl "http://localhost:8000/api/v1/orders?clientId=client-alpha&status=filled"
```

### Cancel Order

```bash
# Cancel order
curl -X POST http://localhost:8000/api/v1/orders/int-1729800000000/cancel \
  -H "Content-Type: application/json"
```

### Metrics

```bash
# Get Prometheus metrics
curl http://localhost:8000/metrics

# Query specific metric
curl http://localhost:8000/metrics | grep exodus_orders_total
```

### Load Testing

```bash
# Using Apache Bench
ab -n 1000 -c 10 http://localhost:8000/health

# Using wrk
wrk -t4 -c100 -d30s http://localhost:8000/health

# Using hey
hey -n 1000 -c 10 http://localhost:8000/health
```

---

## MetaTrader 5 Operations

### MQL5 Compilation

```bash
# Compile EA (on Windows with MetaEditor CLI)
metaeditor.exe /compile:"C:\path\to\ea.mq5"

# Compile all EAs in directory
metaeditor.exe /compile:"C:\path\to\experts" /recursive
```

### EA Deployment

```bash
# Copy EA to MT5 experts directory
cp xm/mql5_ea_template.mq5 "$MT5_DATA_PATH/MQL5/Experts/exodus_ea.mq5"

# Restart MT5 terminal (Windows)
taskkill /F /IM terminal64.exe
start "" "C:\Program Files\MetaTrader 5\terminal64.exe"
```

### MT5 Logs

```bash
# View MT5 logs (Windows)
tail -f "$MT5_DATA_PATH/Logs/$(date +%Y%m%d).log"

# View EA logs
tail -f "$MT5_DATA_PATH/MQL5/Logs/$(date +%Y%m%d).log"

# Search for errors
grep -i error "$MT5_DATA_PATH/Logs/$(date +%Y%m%d).log"
```

### WebRequest Whitelist Configuration

```bash
# Add allowed URL to MT5 config (manually edit config file)
# File: C:\Users\<User>\AppData\Roaming\MetaQuotes\Terminal\<hash>\config\common.ini
# Add line:
# WebRequest=https://your-orchestrator.com/api/v1
```

---

## Database Operations

### PostgreSQL

```bash
# Create database
createdb exodus

# Drop database
dropdb exodus

# Connect to database
psql -U postgres -d exodus

# Run SQL script
psql -U postgres -d exodus -f scripts/schema.sql

# Backup database
pg_dump -U postgres exodus > exodus_backup.sql

# Restore database
psql -U postgres exodus < exodus_backup.sql

# Export to CSV
psql -U postgres -d exodus -c "COPY (SELECT * FROM orders) TO STDOUT CSV HEADER" > orders.csv
```

### Database Migrations (Alembic)

```bash
# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Add orders table"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Show migration history
alembic history

# Show current version
alembic current
```

---

## Kafka Operations

### Start Kafka (Docker Compose)

```bash
# Start Kafka and Zookeeper
docker-compose up -d kafka zookeeper

# Stop Kafka
docker-compose down
```

### Kafka Topics

```bash
# Create topic
kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic exodus.orders \
  --partitions 3 \
  --replication-factor 1

# List topics
kafka-topics.sh --list --bootstrap-server localhost:9092

# Describe topic
kafka-topics.sh --describe \
  --bootstrap-server localhost:9092 \
  --topic exodus.orders

# Delete topic
kafka-topics.sh --delete \
  --bootstrap-server localhost:9092 \
  --topic exodus.orders
```

### Kafka Console Consumer/Producer

```bash
# Consume messages
kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic exodus.orders \
  --from-beginning

# Produce messages
kafka-console-producer.sh \
  --bootstrap-server localhost:9092 \
  --topic exodus.orders

# Consume with key
kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic exodus.orders \
  --property print.key=true \
  --from-beginning
```

### Kafka Consumer Groups

```bash
# List consumer groups
kafka-consumer-groups.sh --list --bootstrap-server localhost:9092

# Describe consumer group
kafka-consumer-groups.sh --describe \
  --bootstrap-server localhost:9092 \
  --group exodus-reconciliation

# Reset offsets
kafka-consumer-groups.sh --reset-offsets \
  --bootstrap-server localhost:9092 \
  --group exodus-reconciliation \
  --topic exodus.orders \
  --to-earliest \
  --execute
```

---

## Docker Operations

### Build Docker Image

```bash
# Build orchestrator image
docker build -t exodus-orchestrator:latest .

# Build with specific Dockerfile
docker build -f Dockerfile.orchestrator -t exodus-orchestrator:latest .

# Build with build args
docker build --build-arg PYTHON_VERSION=3.12 -t exodus-orchestrator:latest .

# Build without cache
docker build --no-cache -t exodus-orchestrator:latest .
```

### Run Docker Container

```bash
# Run orchestrator container
docker run -d \
  --name exodus-orchestrator \
  -p 8000:8000 \
  --env-file .env \
  exodus-orchestrator:latest

# Run with volume mount
docker run -d \
  --name exodus-orchestrator \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  exodus-orchestrator:latest

# Run interactive
docker run -it --rm exodus-orchestrator:latest /bin/bash
```

### Docker Container Management

```bash
# List running containers
docker ps

# List all containers
docker ps -a

# Stop container
docker stop exodus-orchestrator

# Start container
docker start exodus-orchestrator

# Restart container
docker restart exodus-orchestrator

# Remove container
docker rm exodus-orchestrator

# Remove container forcefully
docker rm -f exodus-orchestrator
```

### Docker Logs

```bash
# View logs
docker logs exodus-orchestrator

# Follow logs
docker logs -f exodus-orchestrator

# View last 100 lines
docker logs --tail 100 exodus-orchestrator

# View logs with timestamps
docker logs -t exodus-orchestrator
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d orchestrator

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# View logs
docker-compose logs -f orchestrator

# Rebuild and restart
docker-compose up -d --build
```

### Docker Cleanup

```bash
# Remove unused containers
docker container prune

# Remove unused images
docker image prune

# Remove unused volumes
docker volume prune

# Remove all unused data
docker system prune -a
```

---

## Kubernetes Operations

### Deploy to Kubernetes

```bash
# Apply deployment
kubectl apply -f k8s/orchestrator-deployment.yaml

# Apply all manifests in directory
kubectl apply -f k8s/

# Delete deployment
kubectl delete -f k8s/orchestrator-deployment.yaml
```

### Pods

```bash
# List pods
kubectl get pods

# List pods with more details
kubectl get pods -o wide

# Describe pod
kubectl describe pod exodus-orchestrator-xxxxx

# Get pod logs
kubectl logs exodus-orchestrator-xxxxx

# Follow logs
kubectl logs -f exodus-orchestrator-xxxxx

# Get logs from previous instance
kubectl logs --previous exodus-orchestrator-xxxxx

# Execute command in pod
kubectl exec -it exodus-orchestrator-xxxxx -- /bin/bash

# Copy file to pod
kubectl cp local-file.txt exodus-orchestrator-xxxxx:/app/file.txt
```

### Services

```bash
# List services
kubectl get services

# Describe service
kubectl describe service exodus-orchestrator

# Port forward
kubectl port-forward service/exodus-orchestrator 8000:8000
```

### Deployments

```bash
# List deployments
kubectl get deployments

# Scale deployment
kubectl scale deployment exodus-orchestrator --replicas=3

# Update image
kubectl set image deployment/exodus-orchestrator \
  orchestrator=exodus-orchestrator:v2.0.0

# Rollout status
kubectl rollout status deployment/exodus-orchestrator

# Rollback
kubectl rollout undo deployment/exodus-orchestrator

# Restart deployment
kubectl rollout restart deployment/exodus-orchestrator
```

### ConfigMaps and Secrets

```bash
# Create configmap from file
kubectl create configmap exodus-config --from-file=config.yaml

# Create secret from literal
kubectl create secret generic exodus-secrets \
  --from-literal=api-key=your-api-key

# List configmaps
kubectl get configmaps

# List secrets
kubectl get secrets

# Describe configmap
kubectl describe configmap exodus-config

# Edit configmap
kubectl edit configmap exodus-config
```

### Helm

```bash
# Install chart
helm install exodus ./charts/exodus

# Install with values file
helm install exodus ./charts/exodus -f values.yaml

# Upgrade release
helm upgrade exodus ./charts/exodus

# Rollback release
helm rollback exodus 1

# List releases
helm list

# Uninstall release
helm uninstall exodus

# Show values
helm show values ./charts/exodus
```

### Namespace Operations

```bash
# Create namespace
kubectl create namespace exodus

# List namespaces
kubectl get namespaces

# Set default namespace
kubectl config set-context --current --namespace=exodus

# Delete namespace
kubectl delete namespace exodus
```

---

## Monitoring and Observability

### Prometheus Queries

```bash
# Query Prometheus API
curl 'http://localhost:9090/api/v1/query?query=exodus_orders_total'

# Query range
curl 'http://localhost:9090/api/v1/query_range?query=exodus_orders_total&start=2025-01-01T00:00:00Z&end=2025-01-01T23:59:59Z&step=15s'

# Query using promtool
promtool query instant http://localhost:9090 'exodus_orders_total'
```

### Grafana

```bash
# Import dashboard
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GRAFANA_API_KEY" \
  -d @dashboard.json

# Export dashboard
curl http://localhost:3000/api/dashboards/uid/exodus-overview \
  -H "Authorization: Bearer $GRAFANA_API_KEY" > dashboard.json
```

### OpenTelemetry

```bash
# Start OpenTelemetry Collector
otelcol --config=otel-collector-config.yaml

# Export traces to Jaeger
export OTEL_EXPORTER_JAEGER_ENDPOINT=http://localhost:14268/api/traces
```

### Log Aggregation

```bash
# Tail orchestrator logs
tail -f logs/orchestrator.log

# Search logs
grep -i error logs/orchestrator.log

# View logs in JSON format
cat logs/orchestrator.log | jq .

# Stream logs with jq filter
tail -f logs/orchestrator.log | jq 'select(.level == "ERROR")'
```

### Event Store Inspection

```bash
# View all events
cat data/events.jsonl | jq .

# Filter by event type
cat data/events.jsonl | jq 'select(.eventType == "OrderSubmitted")'

# Count events by type
cat data/events.jsonl | jq -r '.eventType' | sort | uniq -c

# View latest events
tail -f data/events.jsonl | jq .
```

---

## Backup and Recovery

### Backup Event Store

```bash
# Backup events.jsonl
cp data/events.jsonl data/events_backup_$(date +%Y%m%d_%H%M%S).jsonl

# Compress backup
gzip data/events_backup_$(date +%Y%m%d_%H%M%S).jsonl

# Backup to remote
rsync -avz data/events.jsonl user@backup-server:/backups/exodus/
```

### Backup Database

```bash
# Backup PostgreSQL
pg_dump -U postgres exodus > exodus_backup_$(date +%Y%m%d).sql

# Compressed backup
pg_dump -U postgres exodus | gzip > exodus_backup_$(date +%Y%m%d).sql.gz

# Backup to remote
pg_dump -U postgres exodus | ssh user@backup-server "cat > /backups/exodus_$(date +%Y%m%d).sql"
```

### Restore Event Store

```bash
# Restore from backup
cp data/events_backup_20250101_120000.jsonl data/events.jsonl

# Restore from compressed backup
gunzip -c data/events_backup_20250101_120000.jsonl.gz > data/events.jsonl
```

### Restore Database

```bash
# Restore PostgreSQL
psql -U postgres exodus < exodus_backup_20250101.sql

# Restore from compressed backup
gunzip -c exodus_backup_20250101.sql.gz | psql -U postgres exodus
```

---

## Deployment

### Production Deployment Checklist

```bash
# 1. Update version
git tag v1.0.0
git push origin v1.0.0

# 2. Build production image
docker build -t exodus-orchestrator:v1.0.0 .

# 3. Push to registry
docker tag exodus-orchestrator:v1.0.0 your-registry.com/exodus-orchestrator:v1.0.0
docker push your-registry.com/exodus-orchestrator:v1.0.0

# 4. Update Kubernetes manifests
kubectl set image deployment/exodus-orchestrator \
  orchestrator=your-registry.com/exodus-orchestrator:v1.0.0

# 5. Monitor rollout
kubectl rollout status deployment/exodus-orchestrator

# 6. Verify deployment
curl https://orchestrator.production.com/health

# 7. Run smoke tests
pytest tests/smoke/
```

### Blue-Green Deployment

```bash
# Deploy green environment
kubectl apply -f k8s/orchestrator-green.yaml

# Verify green environment
kubectl port-forward service/exodus-orchestrator-green 8001:8000
curl http://localhost:8001/health

# Switch traffic to green
kubectl patch service exodus-orchestrator -p '{"spec":{"selector":{"version":"green"}}}'

# Delete blue environment
kubectl delete -f k8s/orchestrator-blue.yaml
```

### Canary Deployment

```bash
# Deploy canary (10% traffic)
kubectl apply -f k8s/orchestrator-canary.yaml

# Monitor metrics
watch -n 5 'curl -s http://localhost:9090/api/v1/query?query=exodus_orders_total | jq'

# Promote canary
kubectl scale deployment exodus-orchestrator-canary --replicas=10
kubectl scale deployment exodus-orchestrator-stable --replicas=0

# Rollback canary
kubectl delete deployment exodus-orchestrator-canary
```

---

## Troubleshooting

### Check System Resources

```bash
# CPU and memory usage
top
htop

# Disk usage
df -h
du -sh data/

# Network connections
netstat -tuln
ss -tuln

# Process tree
pstree -p

# Check specific process
ps aux | grep orchestrator
```

### Debug Python Application

```bash
# Run with debugger
python -m pdb orchestrator/app.py

# Run with profiler
python -m cProfile -o profile.stats orchestrator/app.py
python -m pstats profile.stats

# Memory profiling
python -m memory_profiler orchestrator/app.py
```

### Network Debugging

```bash
# Test connectivity
ping orchestrator.example.com

# Test port
telnet orchestrator.example.com 8000
nc -zv orchestrator.example.com 8000

# Trace route
traceroute orchestrator.example.com

# DNS lookup
nslookup orchestrator.example.com
dig orchestrator.example.com

# Check SSL certificate
openssl s_client -connect orchestrator.example.com:443 -showcerts
```

### Application Debugging

```bash
# Check application logs
tail -f logs/orchestrator.log

# Check error logs
grep ERROR logs/orchestrator.log | tail -20

# Check recent orders
tail data/events.jsonl | jq 'select(.eventType == "OrderSubmitted")'

# Test API endpoint
curl -v http://localhost:8000/health

# Check listening ports
lsof -i :8000
```

### Performance Profiling

```bash
# Run load test
wrk -t4 -c100 -d30s --latency http://localhost:8000/api/v1/orders

# Monitor in real-time
watch -n 1 'curl -s http://localhost:8000/metrics | grep exodus_order_latency'

# Profile with py-spy
py-spy record -o profile.svg -- python orchestrator/app.py
```

### Container Debugging

```bash
# Enter running container
docker exec -it exodus-orchestrator /bin/bash

# Check container logs
docker logs --tail 100 exodus-orchestrator

# Check container stats
docker stats exodus-orchestrator

# Inspect container
docker inspect exodus-orchestrator

# Check container network
docker network inspect bridge
```

---

## Additional Utility Commands

### Generate Idempotency Keys

```bash
# Generate UUID
uuidgen

# Generate UUID v4 (Python)
python -c "import uuid; print(uuid.uuid4())"

# Generate timestamp-based key
echo "order-$(date +%s%N)"
```

### JSON Processing

```bash
# Pretty print JSON
cat data/events.jsonl | jq .

# Extract specific field
cat data/events.jsonl | jq -r '.internalOrderId'

# Filter by condition
cat data/events.jsonl | jq 'select(.symbol == "EURUSD")'

# Count entries
cat data/events.jsonl | jq -s 'length'
```

### File Operations

```bash
# Count lines in file
wc -l data/events.jsonl

# Check file size
du -h data/events.jsonl

# Find large files
find . -type f -size +100M

# Remove old log files
find logs/ -name "*.log" -mtime +30 -delete
```

### Environment Variables

```bash
# Load .env file
export $(cat .env | xargs)

# Show environment variables
printenv | grep EXODUS

# Set environment variable
export ORCHESTRATOR_PORT=8000
```

---

**End of Command Codex**

For additional commands and detailed usage, refer to the official documentation and tool manuals.

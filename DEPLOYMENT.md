# AEGIS AI — Deployment & Operations Guide

**Version:** 1.0  
**Last Updated:** April 2026  
**Status:** Production-Ready (20/20 Requirements Complete)

---

## Table of Contents

1. [Deployment Checklist](#deployment-checklist)
2. [Environment Setup](#environment-setup)
3. [Secret Management](#secret-management)
4. [Monitoring & Alerts](#monitoring--alerts)
5. [Scaling & Performance](#scaling--performance)
6. [Troubleshooting](#troubleshooting)
7. [Operations Runbook](#operations-runbook)

---

## Deployment Checklist

### Pre-Deployment Verification

- [ ] All 20 requirements completed
- [ ] Unit tests passing (pytest suite)
- [ ] Integration tests passing
- [ ] Code security scan (Bandit, Safety)
- [ ] Docker image builds successfully
- [ ] Docker image vulnerability scan (Trivy) passed
- [ ] Documentation updated
- [ ] Secrets rotated and stored securely
- [ ] CORS configuration finalized
- [ ] Rate limiting configured

### Infrastructure Setup

- [ ] Azure subscription configured
- [ ] Azure App Service created (Python 3.13, 2GB RAM minimum)
- [ ] MongoDB Atlas cluster created (3-node replica set)
- [ ] Pinecone index created (1024-dim vectors)
- [ ] Redis cluster created (optional, for caching)
- [ ] DNS records updated
- [ ] SSL/TLS certificates configured
- [ ] CDN configured (optional)

### Database & Storage

- [ ] MongoDB indexes created
  ```
  db.tasks.createIndex({"task_id": 1, "user_id": 1})
  db.task_behaviors.createIndex({"task_id": 1})
  db.prediction_results.createIndex({"task_id": 1})
  db.ab_experiment_data.createIndex({"experiment_id": 1, "group": 1})
  db.fairness_alerts.createIndex({"timestamp": -1})
  db.audit_log.createIndex({"timestamp": -1})
  ```
- [ ] Backup strategy configured
- [ ] Point-in-time recovery tested
- [ ] Data encryption enabled
- [ ] Access control configured

### Monitoring & Logging

- [ ] Application Performance Monitoring (APM) enabled
  - [ ] Azure Application Insights configured
  - [ ] Custom metrics exported
- [ ] Centralized logging configured
  - [ ] MongoDB audit_log collection configured
  - [ ] Log retention policy set (90 days)
- [ ] Alert rules configured
  - [ ] Accuracy drift > 5%
  - [ ] API latency > 5s
  - [ ] Error rate > 1%
  - [ ] Rate limit violations
  - [ ] Fairness violations

### Security Hardening

- [ ] Secrets stored in Azure Key Vault (or equivalent)
- [ ] API rate limiting tested (60 req/min)
- [ ] DDoS protection enabled
- [ ] WAF (Web Application Firewall) rules configured
- [ ] API authentication scheme implemented
- [ ] CORS whitelist configured
- [ ] Secret rotation schedule set
  - [ ] Pinecone API key: weekly
  - [ ] Groq API key: monthly
- [ ] Firewall rules configured

---

### Local Development Setup

```powershell
# 1. Clone repository
git clone https://github.com/your-org/aegis-ai.git
cd aegis-ai

# 2. Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cp .env.example .env
# Edit .env with local values:
# GROQ_API_KEY=xxx
# MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net
# PINECONE_API_KEY=xxx
# PINECONE_INDEX_NAME=aegis-vectors
# LOG_LEVEL=debug
# EXECUTION_TIMEOUT_SECONDS=300
```

### Docker Deployment

```bash
# Build image
docker build -t aegis-ai:latest .

# Run container
docker run -e GROQ_API_KEY=$GROQ_API_KEY \
           -e MONGODB_URI=$MONGODB_URI \
           -e PINECONE_API_KEY=$PINECONE_API_KEY \
           -p 8000:8000 \
           aegis-ai:latest

# Push to registry
docker push your-registry/aegis-ai:latest
```

### Azure App Service Deployment

```bash
# Using Azure CLI
az login
az group create --name aegis-rg --location eastus

# Create App Service Plan
az appservice plan create \
  --name aegis-plan \
  --resource-group aegis-rg \
  --sku B2 \
  --is-linux

# Create Web App
az webapp create \
  --resource-group aegis-rg \
  --plan aegis-plan \
  --name aegis-api \
  --runtime "PYTHON|3.13"

# Deploy code
az webapp deployment source config-zip \
  --resource-group aegis-rg \
  --name aegis-api \
  --src deploy.zip
```

---

## Secret Management

### Azure Key Vault Integration

```python
# Load secrets from Azure Key Vault
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://aegis-kv.vault.azure.net/",
                     credential=credential)

groq_key = client.get_secret("groq-api-key")
mongodb_uri = client.get_secret("mongodb-uri")
```

### Environment Variables (Production)

**Required:**

```
GROQ_API_KEY=sk-...
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/aegis
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=aegis-production
LOG_LEVEL=info
EXECUTION_TIMEOUT_SECONDS=300
ALLOWED_ORIGINS=https://app.aegis.com,https://dash.aegis.com
```

**Optional:**

```
REDIS_URL=redis://redis-host:6379
SENTRY_DSN=https://...@sentry.io/...
ENABLE_PROFILING=false
```

### Secret Rotation

**Automated Rotation (weekly for Pinecone, monthly for Groq):**

```bash
# Create rotation script (rotate_secrets.sh)
#!/bin/bash
# 1. Generate new API key in Pinecone/Groq console
# 2. Store in Azure Key Vault
az keyvault secret set --vault-name aegis-kv \
  --name "pinecone-api-key" \
  --value "NEW_KEY_VALUE"
# 3. Restart application
az webapp restart --name aegis-api --resource-group aegis-rg
# 4. Verify in logs
az webapp log tail --name aegis-api --resource-group aegis-rg
```

**Schedule in CI/CD (GitHub Actions):**

```yaml
name: Rotate Secrets
on:
  schedule:
    - cron: "0 2 * * 0" # Weekly Sunday 2 AM UTC

jobs:
  rotate:
    runs-on: ubuntu-latest
    steps:
      - name: Rotate Pinecone API Key
        run: scripts/rotate_pinecone.sh
      - name: Rotate Groq API Key
        run: scripts/rotate_groq.sh
```

---

## Monitoring & Alerts

### Key Metrics to Monitor

**Model Performance:**

- Accuracy (target: > 78.4%)
- Precision, Recall, F1 Score
- ROC-AUC (target: > 0.85)
- Calibration Error (ECE < 0.1)
- Prediction latency (p99 < 5s)

**Business Metrics:**

- Task success rate (target: > 90%)
- Abandonment rate (target: < 5%)
- Mean completion time
- CSAT score (target: > 4.0)

**System Health:**

- API latency (p99 < 5s)
- Error rate (< 1%)
- Uptime (target: > 99.9%)
- Database connection pool utilization
- Memory usage
- CPU usage

**Security:**

- Rate limit violations
- Authentication failures
- Fairness violations
- Audit log entries
- Secret rotation completion

### Azure Application Insights Setup

```python
# In main.py
from azure.monitor.opentelemetry import configure_azure_monitor

configure_azure_monitor()

from opentelemetry import metrics, trace

# Use for custom metrics
meter = metrics.get_meter(__name__)
success_counter = meter.create_counter("predictions_success")

# Use for custom traces
tracer = trace.get_tracer(__name__)
```

### Custom Alert Rules

```json
{
  "name": "High Accuracy Drift",
  "condition": "accuracy_drift > 0.05",
  "severity": "critical",
  "action": "notify_ops",
  "notification": {
    "email": "ops@aegis.com",
    "slack": "#alerts"
  }
}
```

---

## Scaling & Performance

### Horizontal Scaling

**Azure App Service Scaling:**

```bash
# Auto-scale configuration
az appservice plan update \
  --name aegis-plan \
  --resource-group aegis-rg \
  --number-of-workers 3

# Enable auto-scale
az monitor autoscale create \
  --resource-group aegis-rg \
  --resource-name aegis-api \
  --resource-type "microsoft.web/sites" \
  --min-count 2 \
  --max-count 10
```

### Performance Optimization

**Database:**

- Connection pooling: 10-20 connections
- Query optimization: indexes on task_id, user_id, timestamp
- Archive old data (> 1 year) to cold storage

**API:**

- Enable gzip compression
- Use HTTP/2
- Cache responses (5-10 minutes)
- Implement pagination (max 100 results)

### Capacity Planning

| Component           | Recommended | Max         |
| ------------------- | ----------- | ----------- |
| App Service Workers | 3-5         | 20          |
| MongoDB Connections | 10          | 100         |
| Pinecone Index Size | 1M vectors  | 10M vectors |
| Daily Requests      | 100K        | 1M          |

---

## Troubleshooting

### Common Issues

#### 1. High API Latency (> 5s)

**Diagnosis:**

```bash
# Check logs
az webapp log tail --name aegis-api

# Check database performance
db.collection.aggregate([{$indexStats: {}}])
```

**Solutions:**

- [ ] Increase App Service tier
- [ ] Add database indexes
- [ ] Enable caching (Redis)
- [ ] Scale to more workers

#### 2. Accuracy Drift (> 5% drop)

**Solutions:**

- [ ] Retrain model with fresh data
- [ ] Check for data distribution shift
- [ ] Validate recent predictions
- [ ] Increase training frequency

#### 3. Rate Limiting / 429 Errors

**Solutions:**

- [ ] Increase rate limit (for trusted clients)
- [ ] Implement request batching
- [ ] Add API key quota tiers

#### 4. MongoDB Connection Errors

**Solutions:**

- [ ] Verify connection string
- [ ] Check IP whitelist
- [ ] Increase connection pool size

---

## Operations Runbook

### Daily Operations

**Morning Checklist (9 AM):**

1. [ ] Check system health dashboard
2. [ ] Review error logs
3. [ ] Verify all integrations active
4. [ ] Check backup completion

**Evening Handoff (6 PM):**

1. [ ] Export daily metrics report
2. [ ] Note any incidents/issues
3. [ ] Verify overnight backups scheduled

### Weekly Operations

**Monday 9 AM:**

- [ ] Review weekly performance report
- [ ] Check model accuracy trend
- [ ] Rotate Pinecone API key (if due)

**Friday 4 PM:**

- [ ] Backup verification
- [ ] Security audit log review
- [ ] Capacity planning assessment

### Monthly Operations

**First Monday of Month:**

- [ ] Rotate Groq API key
- [ ] Full security assessment
- [ ] Cost analysis & optimization

---

## Support & Escalation

**On-Call Support:**

- Level 1: Automated alerts → ops@aegis.com
- Level 2: System Administrator (on-call)
- Level 3: Platform Engineering team

---

**Status:** ✅ Production Ready (20/20 Requirements Complete)

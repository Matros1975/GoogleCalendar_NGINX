# Azure Deployment Specification: ElevenLabs Webhook Service

## Executive Summary

Migration of the ElevenLabs webhook transcription service from Oracle Cloud to Microsoft Azure. The service processes voice call transcripts, performs AI-powered ticket extraction using OpenAI, and creates support tickets in TopDesk with automated transcript attachment.

**Business Requirements:**
- Handle multiple concurrent webhook calls from ElevenLabs
- Auto-scale based on load (0-100+ requests/minute)
- Sub-3 second response time for webhook acknowledgment
- 99.9% uptime SLA
- Secure webhook signature validation
- Integration with TopDesk API and OpenAI API
- Cost-effective (target: €50-150/month for typical load)

---

## Architecture Overview

### Recommended Azure Services

**Primary Option: Azure Container Apps** (Recommended)
- Serverless container platform with auto-scaling
- Built-in HTTPS with custom domain support
- Pay-per-use pricing model
- Native container deployment
- Integrated monitoring and logging

**Alternative Options:**
1. Azure App Service (Linux Containers) - Always-on option
2. Azure Kubernetes Service (AKS) - Enterprise-grade, higher cost
3. Azure Functions (Container) - Event-driven, cold start issues

---

## Technical Specifications

### 1. Service Configuration

#### Container Specifications
```yaml
Base Image: python:3.11-slim
Container Registry: Azure Container Registry (ACR)
Application Framework: FastAPI (async)
Package Manager: pip
Python Version: 3.11+

Resource Requirements:
  CPU: 0.5-2.0 vCPU (auto-scale)
  Memory: 512MB-4GB (auto-scale)
  Storage: Ephemeral (logs to Azure Monitor)
```

#### Application Structure
```
/app
├── src/
│   ├── handlers/
│   │   └── transcription_handler.py  # Main webhook processor
│   ├── utils/
│   │   ├── topdesk_client.py        # TopDesk API client
│   │   ├── email_sender.py          # SMTP notification
│   │   └── storage.py               # Transcript storage
│   ├── models/
│   │   └── webhook_models.py        # Pydantic schemas
│   └── server.py                    # FastAPI app
├── Dockerfile
├── requirements.txt
└── .env (managed via Azure Key Vault)
```

### 2. Networking & Security

#### Domain & SSL
```
Custom Domain: webhook.yourdomain.com (or Azure-provided *.azurecontainerapps.io)
SSL/TLS: Managed certificate (Let's Encrypt via Azure)
Protocol: HTTPS only (HTTP redirect to HTTPS)
```

#### IP Whitelisting
```
Source IP Restriction: ElevenLabs webhook IP ranges
Method: Azure Container Apps Ingress IP restrictions
Fallback: Application-level validation if Azure doesn't support IP filtering

ElevenLabs IP Ranges (to be confirmed):
- 52.1.0.0/16 (example - verify with ElevenLabs)
- 35.0.0.0/16 (example - verify with ElevenLabs)
```

#### Webhook Security
```
Authentication Method: HMAC SHA-256 signature validation
Header: elevenlabs-signature
Format: t={timestamp},v0={hmac_hex}
Secret Storage: Azure Key Vault
Signature Validation: Server-side before processing
Replay Attack Prevention: 5-minute timestamp tolerance
```

### 3. Auto-Scaling Configuration

#### Container Apps Scaling Rules
```yaml
Minimum Replicas: 0 (scale to zero when idle)
Maximum Replicas: 10 (adjust based on budget/load)

Scaling Triggers:
  - HTTP Concurrent Requests: 10 per replica
  - CPU: > 70% triggers scale-out
  - Memory: > 75% triggers scale-out
  
Scale-Out Time: 30-60 seconds
Scale-In Time: 2-5 minutes (graceful shutdown)

Cold Start Mitigation:
  - Option 1: Set minimum replicas to 1 (always warm)
  - Option 2: Use Azure Application Insights availability tests to keep warm
  - Option 3: Accept cold start (typically < 10 seconds)
```

### 4. Environment Variables & Secrets

#### Azure Key Vault Integration
```yaml
Key Vault Name: elevenlabs-webhook-kv
Access Method: Managed Identity (system-assigned)

Secrets to Store:
  - ELEVENLABS_WEBHOOK_SECRET
  - TOPDESK_USERNAME
  - TOPDESK_PASSWORD
  - OPENAI_API_KEY
  - GMAIL_SMTP_PASSWORD (if using Gmail)

Configuration Variables (Container Apps Environment Variables):
  - TOPDESK_URL: https://pietervanforeest-test.topdesk.net/tas/api
  - GMAIL_SMTP_SERVER: smtp.gmail.com
  - GMAIL_SMTP_PORT: 587
  - GMAIL_SMTP_USERNAME: your-email@gmail.com
  - NOTIFICATION_EMAIL_TO: support@company.com
  - STORAGE_ENABLED: true
  - STORAGE_BASE_PATH: /mnt/transcripts (or Azure Blob)
```

### 5. Storage Strategy

#### Option A: Azure Blob Storage (Recommended)
```yaml
Storage Account: elevenlabstranscripts
Container: transcripts
Access Tier: Cool (infrequent access)
Redundancy: LRS (Locally Redundant)
Lifecycle Policy: Delete after 90 days

Directory Structure:
  /transcripts/YYYY/MM/DD/{conversation_id}.json

Estimated Cost: ~€2-5/month for 10GB
```

#### Option B: Ephemeral Storage (Cost-Saving)
```yaml
Storage: Container filesystem (temporary)
Retention: Only during processing
Cost: €0
Trade-off: No long-term transcript storage
```

### 6. Monitoring & Logging

#### Azure Monitor Integration
```yaml
Application Insights: Enabled
Instrumentation: OpenTelemetry SDK

Metrics to Track:
  - Request rate (requests/minute)
  - Response time (p50, p95, p99)
  - Error rate (4xx, 5xx)
  - OpenAI API latency
  - TopDesk API latency
  - Ticket creation success rate
  - Transcript attachment success rate

Log Categories:
  - INFO: Successful ticket creation
  - WARNING: Fallback extraction used, API degradation
  - ERROR: Ticket creation failures, email notification failures
  - DEBUG: Payload details, API responses

Alerts:
  - Error rate > 5% for 5 minutes
  - Average response time > 10 seconds
  - OpenAI API failures
  - TopDesk API failures
```

#### Custom Metrics Dashboard
```
Azure Dashboard Components:
- Real-time request rate chart
- Success/failure pie chart
- Response time histogram
- Cost analysis (per-month)
- Top error messages table
```

### 7. CI/CD Pipeline

#### GitHub Actions Workflow
```yaml
Trigger: Push to main branch
Build Steps:
  1. Checkout code
  2. Build Docker image
  3. Run unit tests (pytest)
  4. Push to Azure Container Registry
  5. Deploy to Azure Container Apps (staging)
  6. Run integration tests
  7. Deploy to production (if tests pass)
  8. Send deployment notification

Environment-Specific Deployments:
  - staging: Auto-deploy on PR merge
  - production: Manual approval gate
```

#### Azure DevOps Pipeline Alternative
```yaml
Repository: Azure Repos or GitHub
Pipeline: azure-pipelines.yml

Stages:
  - Build:
      - Docker image build
      - Security scanning (Trivy)
      - Push to ACR
  - Test:
      - Unit tests
      - Integration tests
      - Load tests (optional)
  - Deploy (Staging):
      - Deploy to staging Container App
      - Smoke tests
  - Deploy (Production):
      - Manual approval
      - Blue-green deployment
      - Health check validation
```

### 8. Disaster Recovery & Backup

#### Backup Strategy
```yaml
Configuration Backup:
  - Infrastructure as Code (Bicep/Terraform)
  - Store in Git repository
  - Automated deployment scripts

Data Backup (if using Blob Storage):
  - Geo-redundant storage option (GRS)
  - Daily snapshots (retention: 30 days)
  - Cross-region replication (optional)

Secret Rotation:
  - Key Vault secret versioning
  - 90-day rotation schedule
  - Automated rotation via Azure Automation
```

#### Recovery Objectives
```
RTO (Recovery Time Objective): 30 minutes
RPO (Recovery Point Objective): 1 hour
Failover Strategy: Multi-region deployment (optional, higher cost)
```

---

## Cost Estimation (Monthly)

### Azure Container Apps (Recommended)
```
Scenario: Low to Medium Load (100-500 requests/day)

Container Apps:
  - Consumption plan (0.000012 EUR/vCPU-second + 0.000002 EUR/GiB-second)
  - Estimated: 10,000 requests/month, avg 2s processing time
  - vCPU hours: ~5.5 hours/month = €6
  - Memory hours: ~11 GB-hours/month = €1
  - HTTP requests: Free tier covers most
  Total: €7-15/month

Azure Container Registry:
  - Basic tier: €4.50/month
  - 10GB storage included

Azure Key Vault:
  - Standard tier: €0.03/10,000 operations
  - 5 secrets: €0.00/month
  - Operations: ~€1/month

Azure Blob Storage (Optional):
  - Cool tier: €0.015/GB
  - 10GB storage: €0.15/month
  - Operations: ~€2/month
  Total: €2-3/month

Application Insights:
  - First 5GB free
  - Estimated ingestion: 1-2GB/month
  - Cost: €0-2/month

Total Monthly Cost: €15-30/month (low load)
                    €30-60/month (medium load)
                    €60-120/month (high load with scaling)
```

### Comparison with Other Options

| Service | Monthly Cost | Auto-Scale | Cold Start | Complexity |
|---------|-------------|------------|------------|------------|
| Container Apps | €15-60 | ✅ Excellent | ~5-10s | Low |
| App Service (B1) | €13 + extras | ⚠️ Manual | None | Low |
| AKS | €70-200 | ✅ Excellent | None | High |
| Functions | €10-40 | ✅ Good | ~10-30s | Medium |

---

## Deployment Steps (For Azure DevOps Team)

### Phase 1: Infrastructure Setup (Week 1)

#### 1.1 Azure Resource Group
```bash
# Create resource group
az group create \
  --name rg-elevenlabs-webhook-prod \
  --location westeurope

# Tags
az group update \
  --name rg-elevenlabs-webhook-prod \
  --tags environment=production service=webhook project=elevenlabs
```

#### 1.2 Azure Container Registry
```bash
# Create ACR
az acr create \
  --name elevenlabswebhookacr \
  --resource-group rg-elevenlabs-webhook-prod \
  --sku Basic \
  --admin-enabled true

# Login to ACR
az acr login --name elevenlabswebhookacr
```

#### 1.3 Azure Key Vault
```bash
# Create Key Vault
az keyvault create \
  --name elevenlabs-webhook-kv \
  --resource-group rg-elevenlabs-webhook-prod \
  --location westeurope \
  --enable-rbac-authorization false

# Add secrets
az keyvault secret set --vault-name elevenlabs-webhook-kv \
  --name ELEVENLABS-WEBHOOK-SECRET --value "your-secret-here"

az keyvault secret set --vault-name elevenlabs-webhook-kv \
  --name TOPDESK-USERNAME --value "api_user"

az keyvault secret set --vault-name elevenlabs-webhook-kv \
  --name TOPDESK-PASSWORD --value "password"

az keyvault secret set --vault-name elevenlabs-webhook-kv \
  --name OPENAI-API-KEY --value "sk-..."
```

#### 1.4 Azure Blob Storage (Optional)
```bash
# Create storage account
az storage account create \
  --name elevenlabstranscripts \
  --resource-group rg-elevenlabs-webhook-prod \
  --location westeurope \
  --sku Standard_LRS \
  --access-tier Cool

# Create container
az storage container create \
  --account-name elevenlabstranscripts \
  --name transcripts \
  --public-access off
```

### Phase 2: Application Deployment (Week 2)

#### 2.1 Build and Push Docker Image
```bash
# Clone repository
git clone https://github.com/your-org/elevenlabs-webhook.git
cd elevenlabs-webhook/Servers/ElevenLabsWebhook

# Build Docker image
docker build -t elevenlabswebhookacr.azurecr.io/webhook:latest .

# Push to ACR
docker push elevenlabswebhookacr.azurecr.io/webhook:latest
```

#### 2.2 Create Container Apps Environment
```bash
# Create Container Apps environment
az containerapp env create \
  --name elevenlabs-webhook-env \
  --resource-group rg-elevenlabs-webhook-prod \
  --location westeurope
```

#### 2.3 Deploy Container App
```bash
# Create container app with managed identity
az containerapp create \
  --name elevenlabs-webhook-app \
  --resource-group rg-elevenlabs-webhook-prod \
  --environment elevenlabs-webhook-env \
  --image elevenlabswebhookacr.azurecr.io/webhook:latest \
  --target-port 8000 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 10 \
  --cpu 0.5 \
  --memory 1Gi \
  --registry-server elevenlabswebhookacr.azurecr.io \
  --registry-username $(az acr credential show -n elevenlabswebhookacr --query username -o tsv) \
  --registry-password $(az acr credential show -n elevenlabswebhookacr --query passwords[0].value -o tsv) \
  --env-vars \
    "TOPDESK_URL=https://pietervanforeest-test.topdesk.net/tas/api" \
    "STORAGE_ENABLED=true" \
  --secrets \
    "elevenlabs-secret=keyvaultref:https://elevenlabs-webhook-kv.vault.azure.net/secrets/ELEVENLABS-WEBHOOK-SECRET,identityref:system" \
    "topdesk-username=keyvaultref:https://elevenlabs-webhook-kv.vault.azure.net/secrets/TOPDESK-USERNAME,identityref:system" \
    "topdesk-password=keyvaultref:https://elevenlabs-webhook-kv.vault.azure.net/secrets/TOPDESK-PASSWORD,identityref:system" \
    "openai-key=keyvaultref:https://elevenlabs-webhook-kv.vault.azure.net/secrets/OPENAI-API-KEY,identityref:system"

# Grant Key Vault access to managed identity
PRINCIPAL_ID=$(az containerapp show \
  --name elevenlabs-webhook-app \
  --resource-group rg-elevenlabs-webhook-prod \
  --query identity.principalId -o tsv)

az keyvault set-policy \
  --name elevenlabs-webhook-kv \
  --object-id $PRINCIPAL_ID \
  --secret-permissions get list
```

#### 2.4 Configure Custom Domain (Optional)
```bash
# Add custom domain
az containerapp hostname add \
  --name elevenlabs-webhook-app \
  --resource-group rg-elevenlabs-webhook-prod \
  --hostname webhook.yourdomain.com

# Bind certificate (managed certificate)
az containerapp hostname bind \
  --name elevenlabs-webhook-app \
  --resource-group rg-elevenlabs-webhook-prod \
  --hostname webhook.yourdomain.com \
  --environment elevenlabs-webhook-env \
  --validation-method CNAME
```

### Phase 3: Monitoring Setup (Week 3)

#### 3.1 Application Insights
```bash
# Create Application Insights
az monitor app-insights component create \
  --app elevenlabs-webhook-insights \
  --location westeurope \
  --resource-group rg-elevenlabs-webhook-prod \
  --application-type web

# Get instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app elevenlabs-webhook-insights \
  --resource-group rg-elevenlabs-webhook-prod \
  --query instrumentationKey -o tsv)

# Update container app with instrumentation key
az containerapp update \
  --name elevenlabs-webhook-app \
  --resource-group rg-elevenlabs-webhook-prod \
  --set-env-vars "APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=$INSTRUMENTATION_KEY"
```

#### 3.2 Configure Alerts
```bash
# Error rate alert
az monitor metrics alert create \
  --name webhook-error-rate \
  --resource-group rg-elevenlabs-webhook-prod \
  --scopes $(az containerapp show --name elevenlabs-webhook-app --resource-group rg-elevenlabs-webhook-prod --query id -o tsv) \
  --condition "avg Percentage CPU > 80" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action email support@company.com

# Response time alert
az monitor metrics alert create \
  --name webhook-slow-response \
  --resource-group rg-elevenlabs-webhook-prod \
  --scopes $(az containerapp show --name elevenlabs-webhook-app --resource-group rg-elevenlabs-webhook-prod --query id -o tsv) \
  --condition "avg RequestDuration > 10000" \
  --window-size 5m \
  --evaluation-frequency 1m
```

### Phase 4: Testing & Validation (Week 4)

#### 4.1 Health Check
```bash
# Get the webhook URL
WEBHOOK_URL=$(az containerapp show \
  --name elevenlabs-webhook-app \
  --resource-group rg-elevenlabs-webhook-prod \
  --query properties.configuration.ingress.fqdn -o tsv)

# Test health endpoint
curl https://$WEBHOOK_URL/elevenlabs/health
```

#### 4.2 Load Testing
```bash
# Use Azure Load Testing or Apache Bench
ab -n 1000 -c 10 -p test-payload.json -T application/json \
  https://$WEBHOOK_URL/elevenlabs/webhook
```

#### 4.3 Integration Testing
```python
# Test webhook with valid signature
import requests, hmac, time, json
from hashlib import sha256

payload = {"type": "post_call_transcription", "conversation_id": "test"}
timestamp = int(time.time())
secret = "your-secret"

payload_str = json.dumps(payload)
full_payload = f"{timestamp}.{payload_str}"
signature = hmac.new(secret.encode(), full_payload.encode(), sha256).hexdigest()

headers = {
    "elevenlabs-signature": f"t={timestamp},v0={signature}",
    "content-type": "application/json"
}

response = requests.post(f"https://{WEBHOOK_URL}/elevenlabs/webhook", 
                        json=payload, headers=headers)
print(response.status_code, response.text)
```

---

## Migration Checklist

### Pre-Migration
- [ ] Backup current Oracle VM configuration
- [ ] Export all environment variables
- [ ] Document current TopDesk integration
- [ ] Test application locally in Docker
- [ ] Verify all dependencies in requirements.txt
- [ ] Review and update Dockerfile for Azure

### Migration
- [ ] Create Azure resources (ACR, Key Vault, Storage)
- [ ] Upload secrets to Key Vault
- [ ] Build and push Docker image to ACR
- [ ] Deploy Container App (staging environment)
- [ ] Configure custom domain and SSL
- [ ] Set up monitoring and alerts
- [ ] Configure auto-scaling rules
- [ ] Test webhook with ElevenLabs sandbox

### Post-Migration
- [ ] Update ElevenLabs webhook URL
- [ ] Monitor first 24 hours closely
- [ ] Validate ticket creation in TopDesk
- [ ] Verify transcript storage
- [ ] Check cost metrics
- [ ] Document operational procedures
- [ ] Decommission Oracle VM (after 2-week validation)

---

## Security Considerations

### 1. Network Security
```yaml
- HTTPS only (TLS 1.2+)
- IP whitelisting for ElevenLabs IPs
- No public endpoints except webhook
- Private endpoints for Azure services (optional, higher cost)
```

### 2. Authentication & Authorization
```yaml
- Webhook signature validation (HMAC SHA-256)
- Managed Identity for Azure service access
- No hardcoded secrets in code
- Key Vault for secret management
- RBAC for Azure resource access
```

### 3. Data Protection
```yaml
- Encryption at rest (Azure Storage encryption)
- Encryption in transit (HTTPS/TLS)
- PII data handling: Minimal retention
- GDPR compliance: 90-day auto-deletion
- Audit logging enabled
```

### 4. Compliance
```yaml
- ISO 27001 (Azure compliance)
- SOC 2 Type II (Azure compliance)
- GDPR (data residency in EU)
- Regular security scans (Trivy, Snyk)
```

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Response Time (p95) | < 3 seconds | Application Insights |
| Response Time (p99) | < 5 seconds | Application Insights |
| Uptime | > 99.9% | Azure Monitor |
| Error Rate | < 0.5% | Application Insights |
| Cold Start Time | < 10 seconds | Manual testing |
| Scale-Out Time | < 60 seconds | Load testing |
| Ticket Creation Success | > 98% | Custom logs |
| Concurrent Requests | 100+ | Load testing |

---

## Operational Runbook

### Common Issues & Resolution

#### Issue 1: High Error Rate
```
Symptoms: Error rate > 5% in Application Insights
Diagnosis:
  1. Check Application Insights exceptions
  2. Review TopDesk API logs
  3. Check OpenAI API status
Resolution:
  1. Verify TopDesk credentials in Key Vault
  2. Check OpenAI API key validity
  3. Review network connectivity
  4. Scale up container resources if CPU/memory high
```

#### Issue 2: Slow Response Time
```
Symptoms: p95 > 5 seconds
Diagnosis:
  1. Check OpenAI API latency in logs
  2. Check TopDesk API latency
  3. Review container CPU/memory usage
Resolution:
  1. Increase min replicas to avoid cold starts
  2. Optimize OpenAI prompt length
  3. Scale up container resources
  4. Enable caching for TopDesk categories/priorities
```

#### Issue 3: Ticket Creation Failures
```
Symptoms: TopDesk API returns 400/404
Diagnosis:
  1. Check TopDesk client logs
  2. Verify category/priority values
  3. Check caller ID validity
Resolution:
  1. Update category/priority cache
  2. Verify TopDesk API endpoint
  3. Check TopDesk credentials
  4. Review payload structure in logs
```

### Maintenance Windows
```
Recommended: Sunday 02:00-04:00 UTC
Frequency: Monthly for updates
Procedure:
  1. Notify stakeholders 48 hours in advance
  2. Deploy to staging first
  3. Run integration tests
  4. Deploy to production with blue-green
  5. Monitor for 1 hour post-deployment
```

---

## Support Contacts

| Role | Contact | Responsibility |
|------|---------|----------------|
| Azure DevOps Team | devops@company.com | Infrastructure, deployment |
| Application Owner | dev-team@company.com | Application bugs, features |
| TopDesk Admin | topdesk-admin@company.com | TopDesk integration issues |
| ElevenLabs Support | support@elevenlabs.io | Webhook issues, IP changes |
| OpenAI Support | support@openai.com | API issues, rate limits |

---

## Appendix

### A. Required Azure Permissions
```
Resource Group: Contributor
Key Vault: Key Vault Secrets Officer
Container Registry: AcrPush, AcrPull
Container Apps: Contributor
Storage Account: Storage Blob Data Contributor
Monitor: Monitoring Contributor
```

### B. Environment Variables Reference
```bash
# TopDesk Configuration
TOPDESK_URL=https://pietervanforeest-test.topdesk.net/tas/api
TOPDESK_USERNAME=<from Key Vault>
TOPDESK_PASSWORD=<from Key Vault>

# OpenAI Configuration
OPENAI_API_KEY=<from Key Vault>
OPENAI_MODEL=gpt-4o-mini
OPENAI_API_BASE=https://api.openai.com/v1  # Optional

# ElevenLabs Configuration
ELEVENLABS_WEBHOOK_SECRET=<from Key Vault>

# Email Notification
GMAIL_SMTP_SERVER=smtp.gmail.com
GMAIL_SMTP_PORT=587
GMAIL_SMTP_USERNAME=<from config>
GMAIL_SMTP_PASSWORD=<from Key Vault>
NOTIFICATION_EMAIL_TO=support@company.com

# Storage Configuration
STORAGE_ENABLED=true
STORAGE_BASE_PATH=/mnt/transcripts
AZURE_STORAGE_ACCOUNT=elevenlabstranscripts
AZURE_STORAGE_CONTAINER=transcripts

# Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=<from App Insights>
```

### C. Dockerfile Reference
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/elevenlabs/health')"

# Start application
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### D. Sample Azure Pipeline (YAML)
```yaml
# azure-pipelines.yml
trigger:
  branches:
    include:
      - main

variables:
  azureSubscription: 'Azure-Production'
  resourceGroup: 'rg-elevenlabs-webhook-prod'
  containerRegistry: 'elevenlabswebhookacr.azurecr.io'
  containerApp: 'elevenlabs-webhook-app'
  imageName: 'webhook'
  imageTag: '$(Build.BuildId)'

stages:
- stage: Build
  jobs:
  - job: BuildAndPush
    pool:
      vmImage: 'ubuntu-latest'
    steps:
    - task: Docker@2
      displayName: 'Build Docker Image'
      inputs:
        command: build
        dockerfile: 'Servers/ElevenLabsWebhook/Dockerfile'
        tags: |
          $(imageTag)
          latest
        repository: $(imageName)
    
    - task: Docker@2
      displayName: 'Push to ACR'
      inputs:
        command: push
        containerRegistry: $(containerRegistry)
        repository: $(imageName)
        tags: |
          $(imageTag)
          latest

- stage: Test
  dependsOn: Build
  jobs:
  - job: IntegrationTests
    pool:
      vmImage: 'ubuntu-latest'
    steps:
    - script: |
        pip install pytest requests
        pytest tests/integration/
      displayName: 'Run Integration Tests'

- stage: DeployStaging
  dependsOn: Test
  jobs:
  - deployment: DeployToStaging
    environment: 'staging'
    pool:
      vmImage: 'ubuntu-latest'
    strategy:
      runOnce:
        deploy:
          steps:
          - task: AzureCLI@2
            displayName: 'Deploy to Staging Container App'
            inputs:
              azureSubscription: $(azureSubscription)
              scriptType: 'bash'
              scriptLocation: 'inlineScript'
              inlineScript: |
                az containerapp update \
                  --name elevenlabs-webhook-staging \
                  --resource-group $(resourceGroup)-staging \
                  --image $(containerRegistry)/$(imageName):$(imageTag)

- stage: DeployProduction
  dependsOn: DeployStaging
  jobs:
  - deployment: DeployToProduction
    environment: 'production'
    pool:
      vmImage: 'ubuntu-latest'
    strategy:
      runOnce:
        deploy:
          steps:
          - task: AzureCLI@2
            displayName: 'Deploy to Production Container App'
            inputs:
              azureSubscription: $(azureSubscription)
              scriptType: 'bash'
              scriptLocation: 'inlineScript'
              inlineScript: |
                az containerapp update \
                  --name $(containerApp) \
                  --resource-group $(resourceGroup) \
                  --image $(containerRegistry)/$(imageName):$(imageTag)
          
          - task: AzureCLI@2
            displayName: 'Health Check'
            inputs:
              azureSubscription: $(azureSubscription)
              scriptType: 'bash'
              scriptLocation: 'inlineScript'
              inlineScript: |
                FQDN=$(az containerapp show \
                  --name $(containerApp) \
                  --resource-group $(resourceGroup) \
                  --query properties.configuration.ingress.fqdn -o tsv)
                
                HEALTH_STATUS=$(curl -s https://$FQDN/elevenlabs/health | jq -r .status)
                
                if [ "$HEALTH_STATUS" != "healthy" ]; then
                  echo "Health check failed!"
                  exit 1
                fi
```

---

## Conclusion

**Recommendation: YES, Azure Container Apps is an excellent choice for this service.**

**Key Advantages:**
1. ✅ **Scalability**: Auto-scales from 0 to 10+ replicas based on load
2. ✅ **Cost-Effective**: €15-60/month typical (vs €0 Oracle Free Tier but better reliability)
3. ✅ **Fully Managed**: No VM management, automatic patching, built-in monitoring
4. ✅ **Security**: Managed identity, Key Vault integration, HTTPS by default
5. ✅ **Performance**: Sub-second cold starts, excellent response times
6. ✅ **DevOps Ready**: Native CI/CD integration, blue-green deployments

**Migration Effort**: 2-4 weeks with proper testing

**Next Steps**:
1. Approve budget (€30-100/month estimated)
2. Assign Azure DevOps team
3. Create Azure subscription/resource group
4. Follow Phase 1-4 deployment steps
5. Conduct parallel running for 2 weeks before full migration

---

**Document Version**: 1.0  
**Created**: December 1, 2025  
**Author**: Development Team  
**Approved By**: _[Pending]_

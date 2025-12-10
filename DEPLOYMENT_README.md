# ElevenLabsWebhook Azure Deployment - Complete Documentation

## 📚 Documentation Overview

This folder contains all documentation needed to deploy the ElevenLabsWebhook service to Azure Container Apps using GitHub Actions.

---

## 📄 Document Guide

### For Your Client (Azure Administrator)

**Start Here:**
1. **CLIENT_EMAIL_TEMPLATE.md** - Email template with quick instructions
2. **AZURE_PERMISSIONS_SETUP.md** - Detailed step-by-step guide for granting permissions
3. **azure_permissions_checklist.png** - Visual checklist (attached to email)

**Purpose:** Your client needs to grant two Azure permissions for the automated deployment to work.

---

### For You (Developer)

**Setup Documents:**
1. **github-secrets-reference.md** - Quick reference for GitHub secrets configuration
2. **azure-deployment-setup.md** - Complete deployment setup guide

**Troubleshooting:**
3. **DEPLOYMENT_TROUBLESHOOTING.md** - Solutions for common deployment issues

---

## 🚀 Quick Start Guide

### Step 1: Send to Client (5 minutes)
1. Open `CLIENT_EMAIL_TEMPLATE.md`
2. Customize with client's name
3. Attach:
   - `AZURE_PERMISSIONS_SETUP.md`
   - `azure_permissions_checklist.png`
4. Send email

### Step 2: Configure GitHub Secrets (5 minutes)
1. Go to: https://github.com/Matros1975/GoogleCalendar_NGINX/settings/secrets/actions
2. Use `github-secrets-reference.md` to add 4 secrets:
   - `AZURE_CLIENT_ID`
   - `AZURE_TENANT_ID`
   - `AZURE_SUBSCRIPTION_ID`
   - `ACR_LOGIN_SERVER`

### Step 3: Wait for Client (Client does this)
Client grants two permissions:
- **AcrPush** on Container Registry
- **Contributor** on Resource Group

### Step 4: Deploy (Automatic)
Once permissions are granted:
- Push any change to `Servers/ElevenLabsWebhook/` on `azure-main` branch
- Or re-run the existing workflow
- Monitor at: https://github.com/Matros1975/GoogleCalendar_NGINX/actions

---

## ✅ Deployment Checklist

### Prerequisites
- [ ] GitHub Actions workflow created (`.github/workflows/deploy-elevenlabs-webhook.yml`)
- [ ] Service principal created (`github-elevenlabs-webhook`)
- [ ] Federated credential configured for OIDC
- [ ] Azure Container App exists (`elevenlabswebhook`)
- [ ] Azure Container Registry exists (`elevenlabsacr12345`)

### Configuration (You)
- [ ] GitHub secret: `AZURE_CLIENT_ID` = `0575d31e-4474-4d16-998f-3453af124c11`
- [ ] GitHub secret: `AZURE_TENANT_ID` = `6444e6d8-0dcf-49a1-8a93-8a359bc2251d`
- [ ] GitHub secret: `AZURE_SUBSCRIPTION_ID` = `660df680-5d2a-451e-bcae-68f7373cb102`
- [ ] GitHub secret: `ACR_LOGIN_SERVER` = `elevenlabsacr12345.azurecr.io`

### Permissions (Client)
- [ ] **AcrPush** role assigned to service principal on ACR
- [ ] **Contributor** role assigned to service principal on Resource Group
- [ ] Permissions verified (wait 5-10 minutes after assignment)

### Deployment
- [ ] Workflow triggered (push to `azure-main` or manual re-run)
- [ ] Workflow completed successfully
- [ ] Service health check passes: https://elevenlabswebhook.kindriver-c1a923f6.westeurope.azurecontainerapps.io/health

---

## 🔧 Technical Details

### Service Principal
- **Name:** `github-elevenlabs-webhook`
- **Application ID:** `0575d31e-4474-4d16-998f-3453af124c11`
- **Object ID:** `e544575d-db2e-4ab0-b8c8-dd12c6c5f4eb`
- **Authentication:** OIDC (Federated Credentials)

### Azure Resources
- **Subscription:** `660df680-5d2a-451e-bcae-68f7373cb102`
- **Tenant:** `6444e6d8-0dcf-49a1-8a93-8a359bc2251d`
- **Resource Group:** `rg-elevenlabs`
- **Region:** West Europe
- **Container Registry:** `elevenlabsacr12345.azurecr.io`
- **Container App:** `elevenlabswebhook`
- **Service URL:** https://elevenlabswebhook.kindriver-c1a923f6.westeurope.azurecontainerapps.io

### GitHub Repository
- **Repository:** `Matros1975/GoogleCalendar_NGINX`
- **Deployment Branch:** `azure-main`
- **Workflow File:** `.github/workflows/deploy-elevenlabs-webhook.yml`
- **Trigger Path:** `Servers/ElevenLabsWebhook/**`

### Deployment Workflow
1. **Trigger:** Push to `azure-main` with changes in `Servers/ElevenLabsWebhook/`
2. **Build:** Docker image from `Servers/ElevenLabsWebhook/Dockerfile`
3. **Tag:** Git commit SHA + `latest`
4. **Push:** To `elevenlabsacr12345.azurecr.io/elevenlabswebhook`
5. **Deploy:** Update Container App with new image
6. **Verify:** Health check endpoint

---

## 📊 Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  Developer pushes to azure-main branch                      │
│  (changes in Servers/ElevenLabsWebhook/)                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions Workflow Triggered                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Checkout Code                                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Azure Login (OIDC)                                      │
│     - Uses federated credential                             │
│     - No passwords or keys                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Login to Azure Container Registry                       │
│     - Requires: AcrPush permission                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Build Docker Image                                      │
│     - Context: Servers/ElevenLabsWebhook                    │
│     - Dockerfile: Servers/ElevenLabsWebhook/Dockerfile      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Push Image to ACR                                       │
│     - Tag: {commit-sha}                                     │
│     - Tag: latest                                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  6. Update Container App                                    │
│     - Requires: Contributor permission                      │
│     - Updates image to new version                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  7. Verify Deployment                                       │
│     - Check container app status                            │
│     - Service is live!                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🆘 Need Help?

### Common Issues
See `DEPLOYMENT_TROUBLESHOOTING.md` for solutions to:
- ACR access token errors
- Authorization failures
- Secret configuration issues
- Federated credential problems
- Docker build failures
- Container App update issues

### Verification Commands

**Check GitHub Secrets:**
```
Go to: https://github.com/Matros1975/GoogleCalendar_NGINX/settings/secrets/actions
Verify all 4 secrets exist
```

**Check Azure Permissions:**
```bash
# ACR permission
az role assignment list \
  --assignee "0575d31e-4474-4d16-998f-3453af124c11" \
  --scope "/subscriptions/660df680-5d2a-451e-bcae-68f7373cb102/resourceGroups/rg-elevenlabs/providers/Microsoft.ContainerRegistry/registries/elevenlabsacr12345"

# Resource Group permission
az role assignment list \
  --assignee "0575d31e-4474-4d16-998f-3453af124c11" \
  --scope "/subscriptions/660df680-5d2a-451e-bcae-68f7373cb102/resourceGroups/rg-elevenlabs"
```

**Check Service Health:**
```bash
curl https://elevenlabswebhook.kindriver-c1a923f6.westeurope.azurecontainerapps.io/health
```

### Support Resources
- **GitHub Actions Logs:** https://github.com/Matros1975/GoogleCalendar_NGINX/actions
- **Azure Portal:** https://portal.azure.com
- **Container App:** Search for `elevenlabswebhook` in Azure Portal
- **Container Registry:** Search for `elevenlabsacr12345` in Azure Portal

---

## 📝 Notes

### Security
- Uses OIDC authentication (no passwords or secrets stored)
- Permissions are scoped to minimum required resources
- Service principal has no interactive login capability
- All credentials are managed through Azure AD

### Automation
- Deployment is fully automated on push to `azure-main`
- Only triggers when files in `Servers/ElevenLabsWebhook/` change
- Includes Docker layer caching for faster builds
- Automatic rollback on deployment failure

### Monitoring
- GitHub Actions provides deployment logs
- Azure Container Apps provides runtime logs
- Health check endpoint for service monitoring
- Deployment history tracked in GitHub Actions

---

## 🎯 Success Criteria

Deployment is successful when:
1. ✅ GitHub Actions workflow completes without errors
2. ✅ Container App shows "Running" status in Azure Portal
3. ✅ Health endpoint returns: `{"status":"healthy","service":"elevenlabs-webhook"}`
4. ✅ Service is accessible at the Container App URL

---

## 📅 Maintenance

### Regular Updates
- Push code changes to `azure-main` branch
- Workflow automatically builds and deploys
- Monitor deployment in GitHub Actions
- Verify service health after deployment

### Troubleshooting
- Check GitHub Actions logs first
- Verify Azure permissions haven't changed
- Check GitHub secrets are still valid
- Review Azure Container App logs if needed

---

**Last Updated:** December 10, 2024
**Version:** 1.0
**Status:** Ready for deployment (pending Azure permissions)

# Deployment Troubleshooting Guide

## Common Issues and Solutions

### Issue 1: "Exceeded max number of attempts to get ACR access token"

**Symptom:** Deployment fails at "Login to Azure Container Registry" step

**Cause:** Service principal doesn't have AcrPush permission

**Solution:**
1. Verify the service principal has **AcrPush** role on the container registry
2. Check role assignments:
   ```bash
   az role assignment list \
     --assignee "0575d31e-4474-4d16-998f-3453af124c11" \
     --scope "/subscriptions/660df680-5d2a-451e-bcae-68f7373cb102/resourceGroups/rg-elevenlabs/providers/Microsoft.ContainerRegistry/registries/elevenlabsacr12345"
   ```
3. If missing, add the role (see AZURE_PERMISSIONS_SETUP.md)
4. Wait 5-10 minutes for permissions to propagate
5. Re-run the workflow

---

### Issue 2: "The client does not have authorization to perform action"

**Symptom:** Deployment fails at "Deploy to Azure Container Apps" step

**Cause:** Service principal doesn't have Contributor permission on resource group

**Solution:**
1. Verify the service principal has **Contributor** role on `rg-elevenlabs`
2. Check role assignments:
   ```bash
   az role assignment list \
     --assignee "0575d31e-4474-4d16-998f-3453af124c11" \
     --scope "/subscriptions/660df680-5d2a-451e-bcae-68f7373cb102/resourceGroups/rg-elevenlabs"
   ```
3. If missing, add the role (see AZURE_PERMISSIONS_SETUP.md)
4. Wait 5-10 minutes for permissions to propagate
5. Re-run the workflow

---

### Issue 3: "Secret not found" or "Invalid client secret"

**Symptom:** Deployment fails at "Azure Login via OIDC" step

**Cause:** GitHub secrets are not configured or incorrect

**Solution:**
1. Go to: https://github.com/Matros1975/GoogleCalendar_NGINX/settings/secrets/actions
2. Verify all 4 secrets exist:
   - `AZURE_CLIENT_ID`
   - `AZURE_TENANT_ID`
   - `AZURE_SUBSCRIPTION_ID`
   - `ACR_LOGIN_SERVER`
3. Check values match (see github-secrets-reference.md):
   - AZURE_CLIENT_ID: `0575d31e-4474-4d16-998f-3453af124c11`
   - AZURE_TENANT_ID: `6444e6d8-0dcf-49a1-8a93-8a359bc2251d`
   - AZURE_SUBSCRIPTION_ID: `660df680-5d2a-451e-bcae-68f7373cb102`
   - ACR_LOGIN_SERVER: `elevenlabsacr12345.azurecr.io`
4. If any are missing or incorrect, update them
5. Re-run the workflow

---

### Issue 4: "Federated credential not found"

**Symptom:** OIDC authentication fails

**Cause:** Federated credential is missing or misconfigured

**Solution:**
1. Verify federated credential exists:
   ```bash
   az ad app federated-credential list \
     --id "0575d31e-4474-4d16-998f-3453af124c11"
   ```
2. Should show credential with:
   - Name: `github-elevenlabs-webhook-azure-main`
   - Subject: `repo:Matros1975/GoogleCalendar_NGINX:ref:refs/heads/azure-main`
3. If missing, recreate it:
   ```bash
   az ad app federated-credential create \
     --id "0575d31e-4474-4d16-998f-3453af124c11" \
     --parameters '{
       "name":"github-elevenlabs-webhook-azure-main",
       "issuer":"https://token.actions.githubusercontent.com",
       "subject":"repo:Matros1975/GoogleCalendar_NGINX:ref:refs/heads/azure-main",
       "audiences":["api://AzureADTokenExchange"]
     }'
   ```

---

### Issue 5: Workflow doesn't trigger

**Symptom:** Push to azure-main doesn't start the workflow

**Cause:** No files changed in `Servers/ElevenLabsWebhook/**` path

**Solution:**
1. The workflow only triggers when files in `Servers/ElevenLabsWebhook/` change
2. Either:
   - Make a change to a file in that directory
   - Or manually trigger the workflow:
     - Go to: https://github.com/Matros1975/GoogleCalendar_NGINX/actions
     - Click on the workflow
     - Click "Re-run all jobs"

---

### Issue 6: Docker build fails

**Symptom:** "Build and push Docker image" step fails

**Possible Causes & Solutions:**

**A. Missing Dockerfile**
- Verify `Servers/ElevenLabsWebhook/Dockerfile` exists
- Check file is committed to git

**B. Missing dependencies**
- Verify `Servers/ElevenLabsWebhook/requirements.txt` exists
- Check all Python packages are available on PyPI

**C. Missing source files**
- Verify `Servers/ElevenLabsWebhook/src/` directory exists
- Check all required files are committed to git

**D. Build context issues**
- Review the Dockerfile COPY commands
- Ensure paths are relative to `Servers/ElevenLabsWebhook/`

---

### Issue 7: Container App update fails

**Symptom:** "Deploy to Azure Container Apps" step fails

**Possible Causes & Solutions:**

**A. Container App doesn't exist**
- Verify the container app exists:
  ```bash
  az containerapp show \
    --name elevenlabswebhook \
    --resource-group rg-elevenlabs
  ```
- If it doesn't exist, create it first in Azure Portal

**B. Wrong container app name**
- Check the workflow uses correct name: `elevenlabswebhook`
- Verify in Azure Portal the exact name matches

**C. Image tag issues**
- Check the image was pushed successfully
- Verify ACR contains the image:
  ```bash
  az acr repository show-tags \
    --name elevenlabsacr12345 \
    --repository elevenlabswebhook
  ```

---

## Verification Checklist

Before running deployment, verify:

- [ ] All 4 GitHub secrets are configured correctly
- [ ] Service principal has **AcrPush** role on ACR
- [ ] Service principal has **Contributor** role on resource group
- [ ] Federated credential exists for the branch
- [ ] Container App `elevenlabswebhook` exists in Azure
- [ ] Dockerfile exists at `Servers/ElevenLabsWebhook/Dockerfile`
- [ ] Source code exists at `Servers/ElevenLabsWebhook/src/`

---

## How to Re-run a Failed Deployment

### Method 1: Re-run from GitHub UI
1. Go to: https://github.com/Matros1975/GoogleCalendar_NGINX/actions
2. Click on the failed workflow run
3. Click "Re-run all jobs" button
4. Monitor the progress

### Method 2: Push a new commit
```bash
cd "d:\Pranay\Projects\Upwork_project\Aipilots\Azure_Function\MCP\v4 - Copy\GoogleCalendar_NGINX"
git checkout azure-main

# Make a small change (e.g., update README)
echo "" >> Servers/ElevenLabsWebhook/README.md

git add Servers/ElevenLabsWebhook/README.md
git commit -m "Trigger deployment"
git push origin azure-main
```

---

## Getting Help

### View Detailed Logs
1. Go to: https://github.com/Matros1975/GoogleCalendar_NGINX/actions
2. Click on the workflow run
3. Click on "Build and Deploy to Azure Container Apps" job
4. Expand each step to see detailed logs
5. Look for error messages in red

### Test Azure Access Locally
```bash
# Login to Azure
az login

# Test ACR access
az acr login --name elevenlabsacr12345

# Test Container App access
az containerapp show \
  --name elevenlabswebhook \
  --resource-group rg-elevenlabs
```

### Check Service Health
Once deployed, verify the service is running:
```bash
# Check health endpoint
curl https://elevenlabswebhook.kindriver-c1a923f6.westeurope.azurecontainerapps.io/health

# Expected response:
# {"status":"healthy","service":"elevenlabs-webhook"}
```

---

## Contact Information

If issues persist:
1. Check the detailed setup guide: `AZURE_PERMISSIONS_SETUP.md`
2. Review GitHub Actions logs for specific error messages
3. Verify all prerequisites are met using the checklist above
4. Contact your Azure administrator for permission-related issues

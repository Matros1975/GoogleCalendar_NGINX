# 📦 Deployment Package for Client

## What You Have

I've created a complete deployment package for the ElevenLabsWebhook service. Here's everything you need to share with your client and complete the setup.

---

## 📧 For Your Client

### Email Template
**File:** `CLIENT_EMAIL_TEMPLATE.md`

This is a ready-to-send email that explains:
- What permissions are needed
- Quick 5-minute setup steps
- Both Azure Portal and CLI methods
- Why these permissions are required

**Action:** 
1. Open the file
2. Replace `[Client Name]` and `[Your Name]`
3. Send to your client with attachments

### Attachments for Client
1. **AZURE_PERMISSIONS_SETUP.md** - Detailed step-by-step guide with screenshots
2. **azure_permissions_checklist.png** - Visual checklist they can follow

---

## 🔧 For You (Developer)

### Setup Documents

**1. DEPLOYMENT_README.md** (Start Here)
- Master document with complete overview
- Quick start guide
- Technical details
- Workflow diagram
- Success criteria

**2. github-secrets-reference.md**
- Quick copy-paste reference for GitHub secrets
- All 4 secrets with exact values
- Instructions for adding them

**3. azure-deployment-setup.md**
- Complete deployment setup guide
- All Azure configuration values
- Verification commands
- Troubleshooting steps

**4. DEPLOYMENT_TROUBLESHOOTING.md**
- Solutions for common issues
- Verification checklist
- How to re-run deployments
- Debugging commands

### Visual Assets

**1. azure_permissions_checklist.png**
- Visual checklist for client
- Shows both required permissions
- Easy to follow steps

**2. deployment_architecture.png**
- Technical architecture diagram
- Shows complete deployment flow
- GitHub → GitHub Actions → Azure
- Highlights required permissions

---

## ✅ Next Steps (In Order)

### Step 1: Configure GitHub Secrets (You - 5 minutes)

1. Go to: https://github.com/Matros1975/GoogleCalendar_NGINX/settings/secrets/actions
2. Click "New repository secret" for each:

**Secret 1:**
- Name: `AZURE_CLIENT_ID`
- Value: `0575d31e-4474-4d16-998f-3453af124c11`

**Secret 2:**
- Name: `AZURE_TENANT_ID`
- Value: `6444e6d8-0dcf-49a1-8a93-8a359bc2251d`

**Secret 3:**
- Name: `AZURE_SUBSCRIPTION_ID`
- Value: `660df680-5d2a-451e-bcae-68f7373cb102`

**Secret 4:**
- Name: `ACR_LOGIN_SERVER`
- Value: `elevenlabsacr12345.azurecr.io`

### Step 2: Send Email to Client (You - 2 minutes)

1. Open `CLIENT_EMAIL_TEMPLATE.md`
2. Customize with names
3. Attach:
   - `AZURE_PERMISSIONS_SETUP.md`
   - `azure_permissions_checklist.png`
4. Send email

### Step 3: Wait for Client (Client - 5 minutes)

Client needs to grant two permissions:
- ✅ **AcrPush** on Container Registry `elevenlabsacr12345`
- ✅ **Contributor** on Resource Group `rg-elevenlabs`

### Step 4: Verify Permissions (You - 2 minutes)

After client confirms, verify:

```bash
# Check ACR permission
az role assignment list \
  --assignee "0575d31e-4474-4d16-998f-3453af124c11" \
  --scope "/subscriptions/660df680-5d2a-451e-bcae-68f7373cb102/resourceGroups/rg-elevenlabs/providers/Microsoft.ContainerRegistry/registries/elevenlabsacr12345"

# Check Resource Group permission
az role assignment list \
  --assignee "0575d31e-4474-4d16-998f-3453af124c11" \
  --scope "/subscriptions/660df680-5d2a-451e-bcae-68f7373cb102/resourceGroups/rg-elevenlabs"
```

### Step 5: Trigger Deployment (You - 1 minute)

Option A - Re-run existing workflow:
1. Go to: https://github.com/Matros1975/GoogleCalendar_NGINX/actions
2. Click on the failed workflow
3. Click "Re-run all jobs"

Option B - Push new commit:
```bash
cd "d:\Pranay\Projects\Upwork_project\Aipilots\Azure_Function\MCP\v4 - Copy\GoogleCalendar_NGINX"
git checkout azure-main
echo "" >> Servers/ElevenLabsWebhook/README.md
git add Servers/ElevenLabsWebhook/README.md
git commit -m "Trigger deployment after permissions setup"
git push origin azure-main
```

### Step 6: Monitor Deployment (You - 5 minutes)

1. Watch workflow: https://github.com/Matros1975/GoogleCalendar_NGINX/actions
2. Wait for completion (usually 3-5 minutes)
3. Verify health check:
   ```bash
   curl https://elevenlabswebhook.kindriver-c1a923f6.westeurope.azurecontainerapps.io/health
   ```
4. Expected response: `{"status":"healthy","service":"elevenlabs-webhook"}`

---

## 📋 Quick Reference

### GitHub Secrets (4 required)
```
AZURE_CLIENT_ID          = 0575d31e-4474-4d16-998f-3453af124c11
AZURE_TENANT_ID          = 6444e6d8-0dcf-49a1-8a93-8a359bc2251d
AZURE_SUBSCRIPTION_ID    = 660df680-5d2a-451e-bcae-68f7373cb102
ACR_LOGIN_SERVER         = elevenlabsacr12345.azurecr.io
```

### Azure Permissions (2 required)
```
Service Principal: github-elevenlabs-webhook
Permission 1: AcrPush on elevenlabsacr12345
Permission 2: Contributor on rg-elevenlabs
```

### Important URLs
```
GitHub Secrets:    https://github.com/Matros1975/GoogleCalendar_NGINX/settings/secrets/actions
GitHub Actions:    https://github.com/Matros1975/GoogleCalendar_NGINX/actions
Service Health:    https://elevenlabswebhook.kindriver-c1a923f6.westeurope.azurecontainerapps.io/health
Azure Portal:      https://portal.azure.com
```

---

## 🎯 Success Checklist

- [ ] All 4 GitHub secrets configured
- [ ] Email sent to client with attachments
- [ ] Client granted AcrPush permission
- [ ] Client granted Contributor permission
- [ ] Permissions verified (wait 5-10 minutes after grant)
- [ ] Deployment triggered (re-run or new commit)
- [ ] Workflow completed successfully
- [ ] Health check returns healthy status
- [ ] Service is accessible at Container App URL

---

## 📊 What Happens After Setup

Once everything is configured:

1. **Automatic Deployments**
   - Any push to `azure-main` branch
   - With changes in `Servers/ElevenLabsWebhook/`
   - Triggers automatic build and deploy

2. **Deployment Process**
   - Builds Docker image
   - Pushes to Azure Container Registry
   - Updates Azure Container App
   - Takes 3-5 minutes total

3. **Monitoring**
   - View logs in GitHub Actions
   - Check service health endpoint
   - Monitor in Azure Portal

---

## 🆘 If Something Goes Wrong

1. **Check GitHub Actions logs** - Most detailed error information
2. **Review DEPLOYMENT_TROUBLESHOOTING.md** - Common issues and solutions
3. **Verify secrets** - Make sure all 4 are correct
4. **Verify permissions** - Both roles must be assigned
5. **Wait for propagation** - Azure permissions take 5-10 minutes

---

## 📞 Support

All documentation is in this folder:
- `DEPLOYMENT_README.md` - Master overview
- `AZURE_PERMISSIONS_SETUP.md` - Client setup guide
- `DEPLOYMENT_TROUBLESHOOTING.md` - Problem solving
- `CLIENT_EMAIL_TEMPLATE.md` - Email template
- `github-secrets-reference.md` - Secrets reference

Visual assets:
- `azure_permissions_checklist.png` - Setup checklist
- `deployment_architecture.png` - Architecture diagram

---

## 🎉 You're Ready!

Everything is set up and documented. Just follow the steps above and you'll have automated deployments running in about 15 minutes total.

**Total Time Estimate:**
- Your setup: ~10 minutes
- Client setup: ~5 minutes
- First deployment: ~5 minutes
- **Total: ~20 minutes**

Good luck! 🚀

Subject: Azure Permissions Required for ElevenLabsWebhook Deployment

Hi [Client Name],

I've set up automated deployment for the ElevenLabsWebhook service to Azure Container Apps using GitHub Actions. To complete the setup, I need you to grant two permissions in Azure.

## What's Needed

The service principal `github-elevenlabs-webhook` needs two role assignments:

1. **AcrPush** role on Container Registry `elevenlabsacr12345`
2. **Contributor** role on Resource Group `rg-elevenlabs`

## Quick Steps (5 minutes)

### Step 1: AcrPush on Container Registry

1. Go to [Azure Portal](https://portal.azure.com)
2. Search for `elevenlabsacr12345` and open it
3. Click **"Access control (IAM)"** in the left menu
4. Click **"+ Add"** → **"Add role assignment"**
5. Select role: **"AcrPush"** → Click **"Next"**
6. Click **"+ Select members"**
7. Search for and select: **"github-elevenlabs-webhook"**
8. Click **"Select"** → **"Next"** → **"Review + assign"** (twice)

### Step 2: Contributor on Resource Group

1. In Azure Portal, search for `rg-elevenlabs` and open it
2. Click **"Access control (IAM)"** in the left menu
3. Click **"+ Add"** → **"Add role assignment"**
4. Select role: **"Contributor"** → Click **"Next"**
5. Click **"+ Select members"**
6. Search for and select: **"github-elevenlabs-webhook"**
7. Click **"Select"** → **"Next"** → **"Review + assign"** (twice)

## Alternative: Using Azure CLI

If you prefer command line, you can run these two commands:

```bash
# Grant AcrPush role
az role assignment create \
  --assignee "0575d31e-4474-4d16-998f-3453af124c11" \
  --role "AcrPush" \
  --scope "/subscriptions/660df680-5d2a-451e-bcae-68f7373cb102/resourceGroups/rg-elevenlabs/providers/Microsoft.ContainerRegistry/registries/elevenlabsacr12345"

# Grant Contributor role
az role assignment create \
  --assignee "0575d31e-4474-4d16-998f-3453af124c11" \
  --role "Contributor" \
  --scope "/subscriptions/660df680-5d2a-451e-bcae-68f7373cb102/resourceGroups/rg-elevenlabs"
```

## Why These Permissions?

- **AcrPush**: Allows GitHub Actions to push Docker images to your container registry
- **Contributor**: Allows GitHub Actions to update the Container App with new deployments

These permissions are scoped only to the specific resources needed and use secure OIDC authentication (no passwords or keys).

## Verification

After adding the permissions:
1. Go to the Container Registry → Access control (IAM) → Role assignments
2. Search for `github-elevenlabs-webhook` - you should see **AcrPush**
3. Go to the Resource Group → Access control (IAM) → Role assignments
4. Search for `github-elevenlabs-webhook` - you should see **Contributor**

## Detailed Documentation

I've attached a comprehensive guide (`AZURE_PERMISSIONS_SETUP.md`) with screenshots and troubleshooting steps if needed.

## Next Steps

Once you've granted these permissions:
1. I'll configure the GitHub secrets
2. The deployment will run automatically when code is pushed to the `azure-main` branch
3. The service will be live at: https://elevenlabswebhook.kindriver-c1a923f6.westeurope.azurecontainerapps.io

Please let me know once you've completed these steps, or if you have any questions!

Best regards,
[Your Name]

---

**Attachments:**
- AZURE_PERMISSIONS_SETUP.md (detailed step-by-step guide)
- azure_permissions_checklist.png (visual checklist)

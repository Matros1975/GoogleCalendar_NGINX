# Azure Permissions Setup for GitHub Actions Deployment

## Overview

To enable automated deployment of the ElevenLabsWebhook service via GitHub Actions, the service principal `github-elevenlabs-webhook` needs specific permissions in Azure.

---

## Required Permissions

The service principal needs **two role assignments**:

1. **AcrPush** - To push Docker images to Azure Container Registry
2. **Contributor** - To update the Azure Container App

---

## Method 1: Azure Portal (Recommended for non-technical users)

### Step 1: Grant AcrPush Role on Container Registry

1. **Navigate to Azure Container Registry**
   - Go to [Azure Portal](https://portal.azure.com)
   - Search for `elevenlabsacr12345` in the top search bar
   - Click on the Container Registry

2. **Open Access Control (IAM)**
   - In the left menu, click **"Access control (IAM)"**

3. **Add Role Assignment**
   - Click the **"+ Add"** button at the top
   - Select **"Add role assignment"**

4. **Select Role**
   - In the **"Role"** tab, search for `AcrPush`
   - Select **"AcrPush"**
   - Click **"Next"**

5. **Select Members**
   - In the **"Members"** tab, click **"+ Select members"**
   - In the search box, type: `github-elevenlabs-webhook`
   - Select **"github-elevenlabs-webhook"** from the results
   - Click **"Select"**
   - Click **"Next"**

6. **Review and Assign**
   - Review the settings:
     - Role: **AcrPush**
     - Member: **github-elevenlabs-webhook**
   - Click **"Review + assign"**
   - Click **"Review + assign"** again to confirm

### Step 2: Grant Contributor Role on Resource Group

1. **Navigate to Resource Group**
   - In Azure Portal, search for `rg-elevenlabs`
   - Click on the **"rg-elevenlabs"** resource group

2. **Open Access Control (IAM)**
   - In the left menu, click **"Access control (IAM)"**

3. **Add Role Assignment**
   - Click the **"+ Add"** button at the top
   - Select **"Add role assignment"**

4. **Select Role**
   - In the **"Role"** tab, search for `Contributor`
   - Select **"Contributor"**
   - Click **"Next"**

5. **Select Members**
   - In the **"Members"** tab, click **"+ Select members"**
   - In the search box, type: `github-elevenlabs-webhook`
   - Select **"github-elevenlabs-webhook"** from the results
   - Click **"Select"**
   - Click **"Next"**

6. **Review and Assign**
   - Review the settings:
     - Role: **Contributor**
     - Member: **github-elevenlabs-webhook**
   - Click **"Review + assign"**
   - Click **"Review + assign"** again to confirm

---

## Method 2: Azure CLI (For technical users)

If you prefer using the command line, run these two commands:

### Command 1: Grant AcrPush Role

```bash
az role assignment create \
  --assignee "0575d31e-4474-4d16-998f-3453af124c11" \
  --role "AcrPush" \
  --scope "/subscriptions/660df680-5d2a-451e-bcae-68f7373cb102/resourceGroups/rg-elevenlabs/providers/Microsoft.ContainerRegistry/registries/elevenlabsacr12345"
```

### Command 2: Grant Contributor Role

```bash
az role assignment create \
  --assignee "0575d31e-4474-4d16-998f-3453af124c11" \
  --role "Contributor" \
  --scope "/subscriptions/660df680-5d2a-451e-bcae-68f7373cb102/resourceGroups/rg-elevenlabs"
```

---

## Verification

After adding the permissions, verify they were applied correctly:

### Using Azure Portal:

1. **For ACR Permission:**
   - Go to Container Registry `elevenlabsacr12345`
   - Click "Access control (IAM)"
   - Click "Role assignments" tab
   - Search for `github-elevenlabs-webhook`
   - You should see **AcrPush** role listed

2. **For Resource Group Permission:**
   - Go to Resource Group `rg-elevenlabs`
   - Click "Access control (IAM)"
   - Click "Role assignments" tab
   - Search for `github-elevenlabs-webhook`
   - You should see **Contributor** role listed

### Using Azure CLI:

```bash
# Verify ACR permission
az role assignment list \
  --assignee "0575d31e-4474-4d16-998f-3453af124c11" \
  --scope "/subscriptions/660df680-5d2a-451e-bcae-68f7373cb102/resourceGroups/rg-elevenlabs/providers/Microsoft.ContainerRegistry/registries/elevenlabsacr12345" \
  --query "[].{Role:roleDefinitionName}" -o table

# Verify Resource Group permission
az role assignment list \
  --assignee "0575d31e-4474-4d16-998f-3453af124c11" \
  --scope "/subscriptions/660df680-5d2a-451e-bcae-68f7373cb102/resourceGroups/rg-elevenlabs" \
  --query "[].{Role:roleDefinitionName}" -o table
```

Expected output should show:
- **AcrPush** for the Container Registry
- **Contributor** for the Resource Group

---

## Important Notes

### Service Principal Details
- **Name**: `github-elevenlabs-webhook`
- **Application (client) ID**: `0575d31e-4474-4d16-998f-3453af124c11`
- **Purpose**: Enables GitHub Actions to deploy to Azure Container Apps

### Security
- These permissions are scoped to only the necessary resources
- **AcrPush**: Only allows pushing images to the specific container registry
- **Contributor**: Only allows managing resources in the `rg-elevenlabs` resource group
- The service principal uses OIDC (OpenID Connect) for authentication, which is more secure than using passwords or keys

### Why These Permissions Are Needed

1. **AcrPush on Container Registry**
   - Allows GitHub Actions to push Docker images to `elevenlabsacr12345.azurecr.io`
   - Without this, the workflow will fail at the "Push Docker image" step

2. **Contributor on Resource Group**
   - Allows GitHub Actions to update the Container App `elevenlabswebhook`
   - Without this, the workflow will fail at the "Deploy to Azure Container Apps" step

---

## Troubleshooting

### "Cannot find service principal" error
- Make sure you're searching for exactly: `github-elevenlabs-webhook`
- The service principal exists in the Azure AD tenant: `6444e6d8-0dcf-49a1-8a93-8a359bc2251d`

### "Insufficient permissions" error
- You need to be an **Owner** or **User Access Administrator** on the resource to assign roles
- Contact your Azure subscription administrator if you don't have these permissions

### Role assignment not showing up
- Wait 5-10 minutes for Azure to propagate the permissions
- Try refreshing the page or logging out and back in

---

## Next Steps After Permissions Are Granted

1. ✅ Verify permissions are applied (see Verification section above)
2. ✅ Ensure GitHub Secrets are configured (see `github-secrets-reference.md`)
3. ✅ Trigger the deployment by pushing to `azure-main` branch
4. ✅ Monitor deployment at: https://github.com/Matros1975/GoogleCalendar_NGINX/actions

---

## Support

If you encounter any issues:
- Check the GitHub Actions workflow logs for specific error messages
- Verify all 4 GitHub secrets are configured correctly
- Ensure both role assignments are in place
- Contact your Azure administrator for permission-related issues

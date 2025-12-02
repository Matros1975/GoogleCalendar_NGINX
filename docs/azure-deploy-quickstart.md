# Quickstart: Deploy ElevenLabs Webhook to Azure (Container Apps)

This quickstart collects the most common deployment commands and environment configuration you'll need to deploy the ElevenLabs webhook service to Azure Container Apps.

Prereqs
- Azure CLI installed and logged in (az login)
- Docker installed and configured
- GitHub repo cloned
- A Service Principal for GitHub Actions (store its JSON in the AZURE_CREDENTIALS secret)

Quick command summary (PowerShell):

```powershell
# create resource group
az group create --name rg-elevenlabs-webhook-prod --location westeurope

# deploy infrastructure (uses infra/azure/main.bicep)
az deployment group create --resource-group rg-elevenlabs-webhook-prod --template-file infra/azure/main.bicep --parameters acrName=elevenlabswebhookacr storageAccountName=elevenlabstranscripts keyVaultName=elevenlabs-webhook-kv

# build image and push
az acr login --name elevenlabswebhookacr
docker build -t elevenlabswebhookacr.azurecr.io/elevenlabs-webhook:latest Servers/ElevenLabsWebhook
docker push elevenlabswebhookacr.azurecr.io/elevenlabs-webhook:latest

# update container app (create if missing)
az containerapp update --name elevenlabs-webhook-app --resource-group rg-elevenlabs-webhook-prod --image elevenlabswebhookacr.azurecr.io/elevenlabs-webhook:latest || \
  az containerapp create --name elevenlabs-webhook-app --resource-group rg-elevenlabs-webhook-prod --environment elevenlabs-webhook-env --image elevenlabswebhookacr.azurecr.io/elevenlabs-webhook:latest --ingress external --target-port 8000 --min-replicas 0 --max-replicas 10
```

Notes
- Use Azure Key Vault to store ELEVENLABS_WEBHOOK_SECRET, OPENAI_API_KEY, TOPDESK credentials, and GMAIL_SMTP_PASSWORD. Give the Container App managed identity 'get' permission to Key Vault secrets.
- Add the following GitHub secrets: AZURE_CREDENTIALS, ACR_NAME, AZURE_RESOURCE_GROUP, CONTAINERAPPS_ENV, CONTAINERAPP_NAME.
- The repo already includes a GitHub Actions workflow at `.github/workflows/azure-containerapps.yml` — update required secrets before enabling.

Health check
- After deployment get the FQDN using:
```bash
az containerapp show --name elevenlabs-webhook-app --resource-group rg-elevenlabs-webhook-prod --query properties.configuration.ingress.fqdn -o tsv
curl https://<fqdn>/elevenlabs/health
```

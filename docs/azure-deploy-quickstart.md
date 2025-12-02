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

Branching & safe deploy workflow (main -> azure-main)
------------------------------------------------

To prevent mixing the Oracle-deployed `main` branch with Azure deployment changes, this repository implements a two-branch flow:

- `main` — your team (client) continues daily work here. This branch remains the canonical source-of-truth for application code.
- `azure-main` — a deployment-only branch which receives a selective sync from `main` and is the branch that CI deploys to Azure.

How it works:

1. When changes land in `main` that touch one of these folders: `Servers`, `scripts`, `nginx`, `instructions`, `future_features`, `docs`, a GitHub Action will automatically sync only these paths into the `azure-main` branch.
2. The `azure-main` branch has the Azure CI/CD deploy workflow enabled (the file `.github/workflows/azure-containerapps.yml` runs on pushes to `azure-main`). This keeps deployments isolated from other changes on `main`.
3. Any manual or direct changes made to `azure-main` will be used to build the image and deploy — allowing you to maintain Azure-specific infra and secrets in that branch without mixing them into `main`.

Developer flow (recommended):

1. Continue working on `main` as usual and push/merge PRs there.
2. Changes to the selected folders above on `main` will be auto-synced into the `azure-main` branch.
3. The `azure-main` branch triggers the deployment workflow automatically. If you need to make an Azure-specific change (e.g., update container app config or secrets references), make it directly on `azure-main`.

If you prefer a manual promotion instead of automatic sync, you can disable the sync workflow and push to the `azure-main` branch manually instead.

Notes and gotchas:
- The sync action only copies the listed folders; other files on `azure-main` (for instance infra files or deploy scripts) remain under manual control.
- The sync commit uses the repository token to push into `azure-main`; confirm that branch protection rules allow the Action to push (or create an allow-list if needed).
- Because the deploy workflow triggers on `azure-main`, merging a PR to `main` will result in the changes being synced and the deploy triggering automatically afterwards.


Health check
- After deployment get the FQDN using:
```bash
az containerapp show --name elevenlabs-webhook-app --resource-group rg-elevenlabs-webhook-prod --query properties.configuration.ingress.fqdn -o tsv
curl https://<fqdn>/elevenlabs/health
```

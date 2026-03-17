# PowerShell helper script: scripts/deploy_to_azure.ps1
# Usage (interactive):
#   ./deploy_to_azure.ps1 -ResourceGroup rg-elevenlabs-webhook-prod -Location westeurope -AcrName elevenlabswebhookacr -StorageAccount elevenlabstranscripts -KeyVault elevenlabs-webhook-kv -ContainerAppsEnv elevenlabs-webhook-env -ContainerApp elevenlabs-webhook-app

param(
  [Parameter(Mandatory=$true)] [string]$ResourceGroup,
  [Parameter(Mandatory=$false)][string]$Location = 'westeurope',
  [Parameter(Mandatory=$true)][string]$AcrName,
  [Parameter(Mandatory=$true)][string]$StorageAccount,
  [Parameter(Mandatory=$true)][string]$KeyVault,
  [Parameter(Mandatory=$true)][string]$ContainerAppsEnv,
  [Parameter(Mandatory=$true)][string]$ContainerApp
)

set -e

Write-Host "Deploying to resource group: $ResourceGroup in $Location"

Write-Host 'Logging in (ensure AZ CLI is installed and you have access)'
az account show > $null 2>&1 || az login

Write-Host 'Creating resource group if missing...'
az group create --name $ResourceGroup --location $Location | Write-Host

Write-Host 'Deploying core infra (Bicep)'
az deployment group create --resource-group $ResourceGroup --template-file infra/azure/main.bicep --parameters acrName=$AcrName storageAccountName=$StorageAccount keyVaultName=$KeyVault containerappsEnvName=$ContainerAppsEnv containerAppName=$ContainerApp | Write-Host

# Build & push image to ACR
Write-Host 'Building docker image and pushing to ACR'
$imageTag = (git rev-parse --short HEAD) 2>$null
if (-not $imageTag) { $imageTag = [Guid]::NewGuid().ToString().Substring(0,8) }
$imageFull = "$AcrName.azurecr.io/elevenlabs-webhook:$imageTag"

az acr login --name $AcrName
docker build -t $imageFull Servers/ElevenLabsWebhook
docker push $imageFull

Write-Host 'Updating container app with new image'
az containerapp update --name $ContainerApp --resource-group $ResourceGroup --image $imageFull || (
  az containerapp create --name $ContainerApp --resource-group $ResourceGroup --environment $ContainerAppsEnv --image $imageFull --ingress external --target-port 8000 --min-replicas 0 --max-replicas 10 --cpu 0.5 --memory 1Gi
)

Write-Host 'Deployment completed — check the container app URL and health endpoint'

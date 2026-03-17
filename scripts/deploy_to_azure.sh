#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP=${1:-rg-elevenlabs-webhook-prod}
LOCATION=${2:-westeurope}
ACR_NAME=${3:-elevenlabswebhookacr}
STORAGE_ACCOUNT=${4:-elevenlabstranscripts}
KEY_VAULT=${5:-elevenlabs-webhook-kv}
CONTAINERAPPS_ENV=${6:-elevenlabs-webhook-env}
CONTAINERAPP=${7:-elevenlabs-webhook-app}

echo "Deploying to $RESOURCE_GROUP in $LOCATION"

az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

echo "Deploying Bicep template..."
az deployment group create --resource-group "$RESOURCE_GROUP" --template-file infra/azure/main.bicep --parameters acrName=$ACR_NAME storageAccountName=$STORAGE_ACCOUNT keyVaultName=$KEY_VAULT containerappsEnvName=$CONTAINERAPPS_ENV containerAppName=$CONTAINERAPP

IMAGE_TAG=$(git rev-parse --short HEAD || echo "$(date +%s)")
IMAGE_FULL=${ACR_NAME}.azurecr.io/elevenlabs-webhook:${IMAGE_TAG}

echo "Build image and push to ACR: $IMAGE_FULL"
az acr login --name $ACR_NAME
docker build -t $IMAGE_FULL Servers/ElevenLabsWebhook
docker push $IMAGE_FULL

echo "Update / create container app"
az containerapp update --name "$CONTAINERAPP" --resource-group "$RESOURCE_GROUP" --image "$IMAGE_FULL" || \
  az containerapp create --name "$CONTAINERAPP" --resource-group "$RESOURCE_GROUP" --environment "$CONTAINERAPPS_ENV" --image "$IMAGE_FULL" --ingress 'external' --target-port 8000 --min-replicas 0 --max-replicas 10 --cpu 0.5 --memory 1Gi

echo "Deployment done — check https://<fqdn>/elevenlabs/health"

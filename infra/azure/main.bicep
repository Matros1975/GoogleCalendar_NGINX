// Bicep template: infra/azure/main.bicep
// Creates ACR, Container Apps environment, Container App placeholder, Key Vault, Storage Account, App Insights

@description('Location for all resources')
param location string = resourceGroup().location

@description('ACR name (must be globally unique)')
param acrName string

@description('Container Apps environment name')
param containerappsEnvName string = 'elevenlabs-capps-env'

@description('Container App name')
param containerAppName string = 'elevenlabs-webhook-app'

@description('Storage account name (must be globally unique)')
param storageAccountName string

@description('Key vault name')
param keyVaultName string = 'elevenlabs-webhook-kv'

@description('Application Insights name')
param appInsightsName string = 'elevenlabs-webhook-insights'

resource acr 'Microsoft.ContainerRegistry/registries@2022-12-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  adminUserEnabled: false
}

resource storage 'Microsoft.Storage/storageAccounts@2022-09-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Cool'
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  properties: {
    Application_Type: 'web'
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2022-11-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      name: 'standard'
      family: 'A'
    }
    accessPolicies: []
    enabledForDeployment: false
    enabledForTemplateDeployment: true
    enabledForDiskEncryption: false
  }
}

resource containerAppsEnv 'Microsoft.App/managedEnvironments@2022-03-01' = {
  name: containerappsEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
    }
  }
}

// Container App placeholder — image must be set after build/push
resource containerApp 'Microsoft.App/containerApps@2022-03-01' = {
  name: containerAppName
  location: location
  properties: {
    kubeEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
      }
    }
    template: {
      containers: [
        {
          name: containerAppName
          image: 'mcr.microsoft.com/oss/azure/sample/web-app:latest' // placeholder
          resources: {
            cpu: 0.5
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 3
      }
    }
  }
  dependsOn: [containerAppsEnv]
}

output acrLoginServer string = acr.properties.loginServer
output containerAppId string = containerApp.id
output keyVaultUri string = 'https://${keyVault.name}.vault.azure.net/'

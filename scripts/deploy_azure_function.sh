#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <resource-group> <function-app-name> <storage-account> [region]"
  exit 1
fi

RG="$1"
APP="$2"
STORAGE="$3"
LOCATION="${4:-eastus}"
PLAN="${APP}-plan"
RUNTIME="python"
PY_VER="3.10"

export AZURE_CONFIG_DIR="${AZURE_CONFIG_DIR:-/tmp/.azure}"

echo "Checking Azure login..."
az account show >/dev/null

echo "Creating resource group: $RG"
az group create --name "$RG" --location "$LOCATION" >/dev/null

echo "Creating storage account: $STORAGE"
az storage account create \
  --name "$STORAGE" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --sku Standard_LRS >/dev/null

echo "Creating Function App plan: $PLAN"
az functionapp plan create \
  --name "$PLAN" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --sku B1 \
  --is-linux >/dev/null

echo "Creating Function App: $APP"
az functionapp create \
  --resource-group "$RG" \
  --plan "$PLAN" \
  --name "$APP" \
  --storage-account "$STORAGE" \
  --runtime "$RUNTIME" \
  --runtime-version "$PY_VER" \
  --functions-version 4 \
  --os-type Linux >/dev/null

echo "Configuring app settings..."
az functionapp config appsettings set \
  --name "$APP" \
  --resource-group "$RG" \
  --settings \
    FUNCTIONS_WORKER_RUNTIME=python \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true \
    ENABLE_ORYX_BUILD=true >/dev/null

echo "Packaging source..."
TMP_ZIP="/tmp/${APP}-$(date +%s).zip"
zip -rq "$TMP_ZIP" . -x@.funcignore

echo "Deploying package..."
az functionapp deployment source config-zip \
  --resource-group "$RG" \
  --name "$APP" \
  --src "$TMP_ZIP" >/dev/null

echo "Deployment complete."
echo "Health URL: https://${APP}.azurewebsites.net/api/health"

#!/usr/bin/env bash
set -euo pipefail

# Fixed by request
RG="pwm-explaingithub-ai-rg"

# Optional overrides
LOCATION="${LOCATION:-eastus}"
APP_NAME="${1:-${FUNCTION_APP_NAME:-pwm-explaingithub-ai-func-v2}}"
STORAGE_NAME="${2:-${STORAGE_ACCOUNT_NAME:-}}"
ACR_NAME="${ACR_NAME:-pwmexplaingithubaiacr}"
PLAN_NAME="${PLAN_NAME:-pwm-explaingithub-ai-ep-plan}"
PLAN_SKU="${PLAN_SKU:-EP1}"
FALLBACK_PLAN_SKU="${FALLBACK_PLAN_SKU:-B1}"
IMAGE_REPO="${IMAGE_REPO:-explaingithub-api}"
IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d%H%M%S)}"
ENV_FILE="${ENV_FILE:-.env}"

# Storage account constraints: 3-24 chars, lowercase letters/numbers only.
if [[ -z "${STORAGE_NAME}" ]]; then
  STORAGE_NAME="pwmexplaingithub$(date +%s | tail -c 7)"
fi
STORAGE_NAME="$(echo "${STORAGE_NAME}" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9')"
STORAGE_NAME="${STORAGE_NAME:0:24}"

# ACR constraints: 5-50 chars, alphanumeric only.
ACR_NAME="$(echo "${ACR_NAME}" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9')"

if [[ -z "${APP_NAME}" ]]; then
  echo "Function app name cannot be empty."
  exit 1
fi

if [[ "${#STORAGE_NAME}" -lt 3 ]]; then
  echo "Storage account name must be at least 3 chars after normalization."
  exit 1
fi

if [[ "${#ACR_NAME}" -lt 5 ]]; then
  echo "ACR name must be at least 5 chars after normalization."
  exit 1
fi

export AZURE_CONFIG_DIR="${AZURE_CONFIG_DIR:-/tmp/.azure}"

echo "Using:"
echo "  Resource Group : ${RG}"
echo "  Location       : ${LOCATION}"
echo "  Function App   : ${APP_NAME}"
echo "  Storage        : ${STORAGE_NAME}"
echo "  ACR            : ${ACR_NAME}"
echo "  Plan           : ${PLAN_NAME} (${PLAN_SKU})"
echo "  Image          : ${IMAGE_REPO}:${IMAGE_TAG}"

echo "Checking Azure login..."
az account show >/dev/null 2>&1 || {
  echo "Not logged in. Run: AZURE_CONFIG_DIR=${AZURE_CONFIG_DIR} az login --use-device-code"
  exit 1
}

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Create it with required app settings before deploy."
  exit 1
fi

trim() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf "%s" "$s"
}

echo "Loading app settings from ${ENV_FILE}..."
declare -A ENV_KV=()
while IFS= read -r raw_line || [[ -n "${raw_line}" ]]; do
  line="${raw_line%$'\r'}"
  [[ -z "$(trim "${line}")" ]] && continue
  [[ "${line}" =~ ^[[:space:]]*# ]] && continue

  if [[ "${line}" == export* ]]; then
    line="${line#export }"
  fi

  if [[ "${line}" != *"="* ]]; then
    continue
  fi

  key="$(trim "${line%%=*}")"
  value="$(trim "${line#*=}")"

  if [[ ! "${key}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    continue
  fi

  if [[ "${value}" =~ ^\"(.*)\"$ ]]; then
    value="${BASH_REMATCH[1]}"
  elif [[ "${value}" =~ ^\'(.*)\'$ ]]; then
    value="${BASH_REMATCH[1]}"
  fi

  ENV_KV["${key}"]="${value}"
  export "${key}=${value}"
done < "${ENV_FILE}"

echo "Ensuring resource group exists..."
if az group show --name "${RG}" >/dev/null 2>&1; then
  echo "Resource group exists."
else
  az group create --name "${RG}" --location "${LOCATION}" >/dev/null
  echo "Resource group created."
fi

echo "Ensuring storage account exists..."
if az storage account show --name "${STORAGE_NAME}" --resource-group "${RG}" >/dev/null 2>&1; then
  echo "Storage account exists."
else
  az storage account create \
    --name "${STORAGE_NAME}" \
    --resource-group "${RG}" \
    --location "${LOCATION}" \
    --sku Standard_LRS >/dev/null
  echo "Storage account created."
fi

echo "Ensuring ACR exists..."
if az acr show --name "${ACR_NAME}" --resource-group "${RG}" >/dev/null 2>&1; then
  echo "ACR exists."
else
  az acr create \
    --name "${ACR_NAME}" \
    --resource-group "${RG}" \
    --location "${LOCATION}" \
    --sku Basic \
    --admin-enabled true >/dev/null
  echo "ACR created."
fi

az acr update --name "${ACR_NAME}" --admin-enabled true >/dev/null
ACR_LOGIN_SERVER="$(az acr show --name "${ACR_NAME}" --resource-group "${RG}" --query loginServer -o tsv)"
ACR_USERNAME="$(az acr credential show --name "${ACR_NAME}" --query username -o tsv)"
ACR_PASSWORD="$(az acr credential show --name "${ACR_NAME}" --query 'passwords[0].value' -o tsv)"
FULL_IMAGE="${ACR_LOGIN_SERVER}/${IMAGE_REPO}:${IMAGE_TAG}"

echo "Ensuring hosting plan exists..."
if az functionapp plan show --name "${PLAN_NAME}" --resource-group "${RG}" >/dev/null 2>&1; then
  echo "Plan exists."
else
  if az functionapp plan create \
    --name "${PLAN_NAME}" \
    --resource-group "${RG}" \
    --location "${LOCATION}" \
    --sku "${PLAN_SKU}" \
    --is-linux >/dev/null; then
    echo "Plan created with SKU ${PLAN_SKU}."
  else
    echo "Primary plan SKU ${PLAN_SKU} failed (likely quota)."
    echo "Falling back to Dedicated Linux plan SKU ${FALLBACK_PLAN_SKU}..."
    az appservice plan create \
      --name "${PLAN_NAME}" \
      --resource-group "${RG}" \
      --location "${LOCATION}" \
      --sku "${FALLBACK_PLAN_SKU}" \
      --is-linux >/dev/null
    echo "Fallback plan created with SKU ${FALLBACK_PLAN_SKU}."
  fi
fi

echo "Building container in ACR..."
if ! az acr build \
  --registry "${ACR_NAME}" \
  --image "${IMAGE_REPO}:${IMAGE_TAG}" \
  .; then
  echo "ACR build failed. Fetching latest build logs..."
  az acr task logs --registry "${ACR_NAME}" --no-format || true
  exit 1
fi

echo "Ensuring Function App exists..."
if az functionapp show --name "${APP_NAME}" --resource-group "${RG}" >/dev/null 2>&1; then
  echo "Function app exists."
else
  az functionapp create \
    --resource-group "${RG}" \
    --plan "${PLAN_NAME}" \
    --name "${APP_NAME}" \
    --storage-account "${STORAGE_NAME}" \
    --functions-version 4 \
    --os-type Linux \
    --image "${FULL_IMAGE}" \
    --registry-server "https://${ACR_LOGIN_SERVER}" \
    --registry-username "${ACR_USERNAME}" \
    --registry-password "${ACR_PASSWORD}" >/dev/null
  echo "Function app created."
fi

echo "Updating Function App container image..."
az functionapp config container set \
  --name "${APP_NAME}" \
  --resource-group "${RG}" \
  --image "${FULL_IMAGE}" \
  --registry-server "https://${ACR_LOGIN_SERVER}" \
  --registry-username "${ACR_USERNAME}" \
  --registry-password "${ACR_PASSWORD}" >/dev/null

echo "Applying app settings..."
REQUIRED_ENV_VARS=(
  "OPENAI_API_KEY"
  "SUPABASE_URL"
  "SUPABASE_SERVICE_KEY"
  "CREDENTIAL_ENCRYPTION_KEY"
)

MISSING=0
for VAR_NAME in "${REQUIRED_ENV_VARS[@]}"; do
  if [[ -z "${!VAR_NAME:-}" ]]; then
    echo "Missing required value in ${ENV_FILE}: ${VAR_NAME}"
    MISSING=1
  fi
done

if [[ "${MISSING}" -ne 0 ]]; then
  echo "Set missing values in ${ENV_FILE}, then rerun deploy."
  exit 1
fi

declare -A APP_SETTINGS=()
APP_SETTINGS["FUNCTIONS_WORKER_RUNTIME"]="python"
APP_SETTINGS["WEBSITES_ENABLE_APP_SERVICE_STORAGE"]="false"
APP_SETTINGS["OPENAI_API_KEY"]="${OPENAI_API_KEY}"
APP_SETTINGS["SUPABASE_URL"]="${SUPABASE_URL}"
APP_SETTINGS["SUPABASE_SERVICE_KEY"]="${SUPABASE_SERVICE_KEY}"
APP_SETTINGS["CREDENTIAL_ENCRYPTION_KEY"]="${CREDENTIAL_ENCRYPTION_KEY}"

for key in "${!ENV_KV[@]}"; do
  APP_SETTINGS["${key}"]="${ENV_KV[${key}]}"
done

SETTINGS=()
for key in "${!APP_SETTINGS[@]}"; do
  SETTINGS+=("${key}=${APP_SETTINGS[${key}]}")
done

az functionapp config appsettings set \
  --name "${APP_NAME}" \
  --resource-group "${RG}" \
  --settings "${SETTINGS[@]}" >/dev/null

echo "Restarting Function App..."
az functionapp restart --name "${APP_NAME}" --resource-group "${RG}" >/dev/null

echo "Deployment finished."
echo "Function list:"
az functionapp function list --resource-group "${RG}" --name "${APP_NAME}" --query "[].name" -o tsv || true
echo "Health URL: https://${APP_NAME}.azurewebsites.net/api/health"

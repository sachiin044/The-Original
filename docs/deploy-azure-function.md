# Deploy to Azure Function App

## 1) Login

```bash
export AZURE_CONFIG_DIR=/tmp/.azure
az login --use-device-code
```

## 2) Run deploy script

```bash
chmod +x scripts/deploy_azure_function.sh
scripts/deploy_azure_function.sh <resource-group> <function-app-name> <storage-account> [region]
```

Example:

```bash
scripts/deploy_azure_function.sh repolens-rg repolens-func repolensstor123 eastus
```

## 3) Set required runtime secrets

This app will fail startup unless these are configured:

- `OPENAI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `CREDENTIAL_ENCRYPTION_KEY` (valid Fernet key)

Set them:

```bash
az functionapp config appsettings set \
  --resource-group <resource-group> \
  --name <function-app-name> \
  --settings \
    OPENAI_API_KEY="<value>" \
    SUPABASE_URL="<value>" \
    SUPABASE_SERVICE_KEY="<value>" \
    CREDENTIAL_ENCRYPTION_KEY="<value>" \
    PINECONE_API_KEY="<value>" \
    PINECONE_INDEX_NAME="<value>"
```

## 4) Verify

```bash
curl -i "https://<function-app-name>.azurewebsites.net/api/health"
```

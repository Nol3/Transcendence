#!/bin/sh

set -e

export VAULT_ADDR=http://vault:8200
export VAULT_TOKEN=root

echo "[VAULT-INIT] Waiting for Vault..."

until vault status >/dev/null 2>&1; do
    sleep 1
done

echo "[VAULT-INIT] Vault is ready"

# Prevent regeneration on restart
if vault kv get secret/transcendence >/dev/null 2>&1; then
    echo "[VAULT-INIT] Secrets already initialized"
    exit 0
fi

echo "[VAULT-INIT] Generating application secrets"

JWT_SECRET=$(vault write -field=random_bytes sys/tools/random/64 format=base64)
DJANGO_SECRET_KEY=$(vault write -field=random_bytes sys/tools/random/64 format=base64)
INTERNAL_API_KEY=$(vault write -field=random_bytes sys/tools/random/32 format=hex)

vault kv put secret/transcendence \
    JWT_SECRET="$JWT_SECRET" \
    DJANGO_SECRET_KEY="$DJANGO_SECRET_KEY" \
    INTERNAL_API_KEY="$INTERNAL_API_KEY"

echo "[VAULT-INIT] Secrets stored successfully"

#
# Future candidates for Vault storage:
#
# - POSTGRES_PASSWORD
# - SMTP_PASSWORD
# - GOOGLE_CLIENT_SECRET
# - 42_OAUTH_CLIENT_SECRET
# - THIRD_PARTY_API_KEYS
#
# Note:
# These secrets should usually NOT be generated automatically,
# because external services or other containers must already know
# their values. They should be provisioned manually and then stored
# in Vault as the central source of truth.
#
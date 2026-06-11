# HashiCorp Vault - Secrets Management Guide

## Objective

We use Vault to **manage secrets** (we must use it to store **API KEYS, credentials, environment variables**), instead of storing them in other places of the repository

## Start Vault

Vault is already declared in the docker-compose file, so using the docker setup file would start the service

This setup uses **dev mode** which is far enough to meet the requirements of the evaluation. In this mode, we do not need authentication from the services, as it is not required in the subject. Prod mode would need authentication, which is overkill for the purposes of the project.

The only and fixed token to access vault is defined in the compose.yaml file, so no authentication system is used.

Our guess is that Vault should be initialized and filled with secrets (from vault-init.sh) before the rest of the services that need credentials, so they can retrieve them once they are initialized

## Interact with Vault

Vault's default port is 8200, so we leave it as it is in the docker network

## How we should store secrets

The storage of secrets should be done at startup time, once the Vault has been initialized, automatically (probably with a script that generated random keys)

A sample script is proposed in **scripts/vault-init.sh**, and it is copied and run at container initialization time, inside the container.

## How we would retrieve secrets

From vault container:

```bash
    vault kv get secret/transcendence
```

to get a single value:

```bash
    vault kv get -field=DB_PASSWORD secret/transcendece
```

## Using Vault in Backend

The backend retrieves secrets from Vault at runtime using **AppRole Authentication**.

### AppRole Authentication (Production / Docker mode)
The `vault-init` container configures an AppRole named `django-role` with a read-only policy for `secret/data/transcendence`. It generates a **Role ID** and a **Secret ID** and writes them to a shared volume path `/vault_creds/credentials.env`.

The backend reads these credentials and logs into Vault at `/v1/auth/approle/login` to obtain a client token, which is then used to retrieve the secrets.

No manual token setup is needed in Docker.

### Development Fallback (Local mode outside Docker)
When running Django locally without Docker (`USE_VAULT=false` or if credentials are not found), Django falls back gracefully to standard `.env` variables using `decouple`.

For manual Vault testing in development, you can set `VAULT_TOKEN` or `VAULT_ROLE_ID` and `VAULT_SECRET_ID` in your local environment.

### Secret Rotation
1. Update the secret value in Vault using the CLI: `vault kv put secret/transcendence KEY=NEW_VALUE`
2. Restart the Django container (e.g. `docker compose restart backend`) to pull the new secrets into memory. Since AppRole tokens have a limited TTL (1 hour), they will automatically expire, and restarting the backend re-authenticates and pulls fresh secrets.

## Recommended usage

Backend should

1. Fetch secrets from Vault
2. Export them as environment variables
3. Start the application

### Current Vault-managed secrets

The following secrets are generated automatically during the first startup (these act as example):

- JWT_SECRET
- DJANGO_SECRET_KEY
- INTERNAL_API_KEY

These secrets are application-specific and can safely be generated automatically.

### Future Vault-managed secrets

Vault can also store:

- Database passwords
- SMTP credentials
- OAuth client secrets
- Third-party API keys

However, these values should generally be provisioned manually because they must match credentials configured in external systems.



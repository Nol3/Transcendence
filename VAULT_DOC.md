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

The backend should retrieve secrets from Vault at runtime

Required environment variables:

``` YAML
    environment:
        - VAULT_ADDR: http://vault:8200
        - VAULT_token: root
```

to inject a secret in a service:

``` bash
    export DB_PASSWORD=$(vault kv get -field=DB_PASSWORD secret/transcendence)
```

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



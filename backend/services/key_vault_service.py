import os
from typing import Any

try:
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
except ImportError:
    DefaultAzureCredential = None
    SecretClient = None


_client: Any | None = None


def key_vault_url() -> str | None:
    return os.getenv("AZURE_KEY_VAULT_URL") or os.getenv("KEY_VAULT_URL")


def key_vault_configured() -> bool:
    return bool(key_vault_url())


def key_vault_sdk_available() -> bool:
    return DefaultAzureCredential is not None and SecretClient is not None


def get_secret_client() -> Any:
    global _client

    if _client is not None:
        return _client

    url = key_vault_url()
    if not url:
        raise RuntimeError("Missing AZURE_KEY_VAULT_URL")

    if not key_vault_sdk_available():
        raise RuntimeError("azure-keyvault-secrets SDK is not installed")

    _client = SecretClient(vault_url=url, credential=DefaultAzureCredential())
    return _client


def get_secret(name: str) -> str | None:
    if not name:
        return None

    try:
        client = get_secret_client()
        return client.get_secret(name).value
    except Exception as exc:
        print(f"[key-vault] get secret failed for {name}: {exc}")
        return None


def get_env_or_secret(env_name: str, secret_name_env: str | None = None) -> str | None:
    value = os.getenv(env_name)
    if value:
        return value

    if not key_vault_configured():
        return None

    secret_name = os.getenv(secret_name_env or f"{env_name}_SECRET_NAME")
    if not secret_name:
        return None

    return get_secret(secret_name)


def key_vault_status() -> dict[str, Any]:
    return {
        "configured": key_vault_configured(),
        "sdkAvailable": key_vault_sdk_available(),
        "url": key_vault_url(),
        "usesDefaultAzureCredential": True,
        "secretNameEnvPattern": "<ENV_NAME>_SECRET_NAME",
    }

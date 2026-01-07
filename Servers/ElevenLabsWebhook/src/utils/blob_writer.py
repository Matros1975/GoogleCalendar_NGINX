import os
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError

CONNECT_STR = os.getenv("AzureWebJobsStorage_elevenlabswebhook")
CONTAINER_NAME = os.getenv("BLOB_CONTAINER_NAME", "webhook-logs")

if not CONNECT_STR:
    raise RuntimeError("Azure storage connection string not set")

_blob_service_client = BlobServiceClient.from_connection_string(CONNECT_STR)
_container_client = _blob_service_client.get_container_client(CONTAINER_NAME)

try:
    _container_client.create_container()
except ResourceExistsError:
    pass
except Exception:
    # Never block app startup for logging infra
    pass


def write_logs_to_blob(blob_path: str, logs: list[str]) -> None:
    blob_client = _container_client.get_blob_client(blob_path)
    content = "\n".join(logs) + "\n"

    blob_client.upload_blob(
        content.encode("utf-8"),
        overwrite=True
    )

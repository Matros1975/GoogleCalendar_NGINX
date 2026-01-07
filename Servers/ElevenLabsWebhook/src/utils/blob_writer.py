import os
from azure.storage.blob import BlobServiceClient

CONNECT_STR = os.getenv("AzureWebJobsStorage_elevenlabswebhook")
CONTAINER_NAME = os.getenv("BLOB_CONTAINER_NAME", "webhook-logs")

_blob_service_client = BlobServiceClient.from_connection_string(CONNECT_STR)
_container_client = _blob_service_client.get_container_client(CONTAINER_NAME)


def write_logs_to_blob(blob_path: str, logs: list[str]) -> None:
    blob_client = _container_client.get_blob_client(blob_path)
    content = "\n".join(logs) + "\n"

    blob_client.upload_blob(
        content.encode("utf-8"),
        overwrite=True
    )

import logging
import os
from datetime import datetime
from azure.storage.blob import BlobServiceClient

# -----------------------
# Azure Blob config
# -----------------------
CONNECT_STR = os.getenv("AzureWebJobsStorage_elevenlabswebhook")
CONTAINER_NAME = os.getenv("BLOB_CONTAINER_NAME", "webhook-logs")

if not CONNECT_STR:
    raise RuntimeError("Azure storage connection string not set")

blob_service_client = BlobServiceClient.from_connection_string(CONNECT_STR)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)

try:
    container_client.create_container()
except Exception:
    pass

# -----------------------
# Custom Blob Log Handler (STABLE)
# -----------------------
class AzureBlobLogHandler(logging.Handler):
    def emit(self, record):
        try:
            log_entry = self.format(record) + "\n"

            now = datetime.utcnow()
            folder = f"logs/{now.year}/{now.month:02d}/{now.day:02d}"
            blob_name = f"{folder}/webhook_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.log"
            blob_client = container_client.get_blob_client(blob_name)

            try:
                existing = blob_client.download_blob().readall().decode("utf-8")
            except Exception:
                existing = ""

            blob_client.upload_blob(
                existing + log_entry,
                overwrite=True
            )

        except Exception as e:
            print(f"[LOGGER ERROR] {e}")


# -----------------------
# Logger setup
# -----------------------
def setup_logger():
    logger = logging.getLogger("ticketcategorizer")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    handler = AzureBlobLogHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # This line SHOULD create the blob immediately
    logger.info("Logger initialized (direct blob logging)")
    return logger

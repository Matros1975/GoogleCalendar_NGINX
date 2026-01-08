import os
import json
import asyncio
import pytest
from httpx import AsyncClient, ASGITransport

import src.main as main_module


class FakeBlobClient:
    def __init__(self, name, uploads):
        self.name = name
        self._uploads = uploads

    def upload_blob(self, data, overwrite=True, content_settings=None):
        self._uploads.append((self.name, data.decode("utf-8")))


class FakeContainer:
    def __init__(self, uploads):
        self._uploads = uploads

    def create_container(self):
        pass

    def get_blob_client(self, name):
        return FakeBlobClient(name, self._uploads)


class FakeService:
    def __init__(self, uploads):
        self._uploads = uploads

    @classmethod
    def from_connection_string(cls, conn):
        # return an instance - tests will monkeypatch attribute to this class
        return cls([])

    def get_container_client(self, name):
        return FakeContainer(self._uploads)


@pytest.mark.asyncio
async def test_single_request_creates_one_blob(monkeypatch, sample_transcription_payload):
    uploads = []

    # monkeypatch BlobServiceClient to use our fake that records uploads
    class MyService(FakeService):
        def __init__(self):
            super().__init__(uploads)

        @classmethod
        def from_connection_string(cls, conn):
            return cls()

    monkeypatch.setattr("src.utils.logger.BlobServiceClient", MyService)

    os.environ["AzureWebJobsStorage_elevenlabswebhook"] = "fake"
    os.environ["BLOB_CONTAINER_NAME"] = "testcontainer"
    os.environ.pop("BLOB_PREFIX", None)

    # Initialize minimal app components (fail-safe validator that accepts requests in tests)
    class DummyValidator:
        def validate(self, signature, body):
            return True, ""

    from src.handlers.transcription_handler import TranscriptionHandler
    from src.handlers.audio_handler import AudioHandler
    from src.handlers.call_failure_handler import CallFailureHandler

    main_module.hmac_validator = DummyValidator()
    main_module.transcription_handler = TranscriptionHandler()
    main_module.audio_handler = AudioHandler()
    main_module.call_failure_handler = CallFailureHandler()

    payload_bytes = json.dumps(sample_transcription_payload).encode("utf-8")
    headers = {
        "elevenlabs-signature": "t=0,v0=fake",
        "content-type": "application/json",
        "x-conversation-id": "conv-1",
    }

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/webhook",
            content=payload_bytes,
            headers=headers,
        )

    assert response.status_code == 200
    # Exactly one upload
    assert len(uploads) == 1
    name, body = uploads[0]
    assert name.startswith("logs/")
    assert name.endswith("_conv-1.log")
    # The payload fixture has its own conversation_id - ensure it appears in the blob
    assert sample_transcription_payload["conversation_id"] in body


@pytest.mark.asyncio
async def test_concurrent_requests_do_not_mix_logs(monkeypatch, sample_transcription_payload):
    uploads = []

    class MyService(FakeService):
        def __init__(self):
            super().__init__(uploads)

        @classmethod
        def from_connection_string(cls, conn):
            return cls()

    monkeypatch.setattr("src.utils.logger.BlobServiceClient", MyService)

    os.environ["AzureWebJobsStorage_elevenlabswebhook"] = "fake"
    os.environ["BLOB_CONTAINER_NAME"] = "testcontainer"

    # Initialize minimal app components (fail-safe validator that accepts requests in tests)
    class DummyValidator:
        def validate(self, signature, body):
            return True, ""

    from src.handlers.transcription_handler import TranscriptionHandler
    from src.handlers.audio_handler import AudioHandler
    from src.handlers.call_failure_handler import CallFailureHandler

    main_module.hmac_validator = DummyValidator()
    main_module.transcription_handler = TranscriptionHandler()
    main_module.audio_handler = AudioHandler()
    main_module.call_failure_handler = CallFailureHandler()

    # Two different conversation ids
    payload_a = dict(sample_transcription_payload)
    payload_a["conversation_id"] = "conv-A"
    payload_b = dict(sample_transcription_payload)
    payload_b["conversation_id"] = "conv-B"

    bytes_a = json.dumps(payload_a).encode("utf-8")
    bytes_b = json.dumps(payload_b).encode("utf-8")

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async def post_a():
            return await client.post(
                "/webhook",
                content=bytes_a,
                headers={"elevenlabs-signature": "t=0,v0=fake", "content-type": "application/json", "x-conversation-id": "conv-A"},
            )

        async def post_b():
            return await client.post(
                "/webhook",
                content=bytes_b,
                headers={"elevenlabs-signature": "t=0,v0=fake", "content-type": "application/json", "x-conversation-id": "conv-B"},
            )

        res_a, res_b = await asyncio.gather(post_a(), post_b())

    assert res_a.status_code == 200
    assert res_b.status_code == 200

    # Two uploads, each containing only its own conversation id
    assert len(uploads) == 2
    names = [u[0] for u in uploads]
    assert any(n.endswith("_conv-A.log") for n in names)
    assert any(n.endswith("_conv-B.log") for n in names)

    for name, body in uploads:
        if name.endswith("_conv-A.log"):
            assert "conversation_id: conv-A" in body
            assert "conversation_id: conv-B" not in body
        if name.endswith("_conv-B.log"):
            assert "conversation_id: conv-B" in body
            assert "conversation_id: conv-A" not in body

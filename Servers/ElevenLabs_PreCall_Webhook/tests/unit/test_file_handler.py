"""
Unit tests for file handler.
"""

import pytest
import base64
import os
import tempfile
from src.utils.file_handler import FileHandler


class TestFileHandler:
    """Test suite for FileHandler."""
    
    @pytest.fixture
    def file_handler(self):
        """Create file handler without storage."""
        return FileHandler(storage_path=None, enable_storage=False)
    
    @pytest.fixture
    def file_handler_with_storage(self):
        """Create file handler with temporary storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = FileHandler(storage_path=tmpdir, enable_storage=True)
            yield handler
    
    @pytest.fixture
    def sample_wav_bytes(self):
        """Sample WAV file header."""
        # Minimal WAV file header
        return b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00' + b'\x00' * 100
    
    @pytest.fixture
    def sample_mp3_bytes(self):
        """Sample MP3 file header."""
        # MP3 with ID3 tag
        return b'ID3\x04\x00\x00\x00\x00\x00\x00' + b'\x00' * 100
    
    def test_decode_base64_audio_valid(self, file_handler):
        """Test decoding valid base64 audio."""
        original = b"test audio data"
        encoded = base64.b64encode(original).decode("utf-8")
        
        decoded = file_handler.decode_base64_audio(encoded)
        
        assert decoded == original
    
    def test_decode_base64_audio_with_data_url(self, file_handler):
        """Test decoding base64 with data URL prefix."""
        original = b"test audio data"
        encoded = base64.b64encode(original).decode("utf-8")
        data_url = f"data:audio/mp3;base64,{encoded}"
        
        decoded = file_handler.decode_base64_audio(data_url)
        
        assert decoded == original
    
    def test_decode_base64_audio_invalid(self, file_handler):
        """Test decoding invalid base64."""
        with pytest.raises(ValueError, match="Invalid base64 audio data"):
            file_handler.decode_base64_audio("not-valid-base64!!!")
    
    def test_validate_audio_size_valid(self, file_handler):
        """Test audio size validation with valid size."""
        # 1MB audio
        audio_bytes = b'\x00' * (1024 * 1024)
        
        is_valid, error = file_handler.validate_audio_size(audio_bytes, max_size_mb=10.0)
        
        assert is_valid is True
        assert error is None
    
    def test_validate_audio_size_too_large(self, file_handler):
        """Test audio size validation with oversized file."""
        # 11MB audio
        audio_bytes = b'\x00' * (11 * 1024 * 1024)
        
        is_valid, error = file_handler.validate_audio_size(audio_bytes, max_size_mb=10.0)
        
        assert is_valid is False
        assert "too large" in error.lower()
        assert "11" in error  # Size mentioned
    
    def test_get_audio_format_wav(self, file_handler, sample_wav_bytes):
        """Test WAV format detection."""
        fmt = file_handler.get_audio_format(sample_wav_bytes)
        assert fmt == "wav"
    
    def test_get_audio_format_mp3(self, file_handler, sample_mp3_bytes):
        """Test MP3 format detection."""
        fmt = file_handler.get_audio_format(sample_mp3_bytes)
        assert fmt == "mp3"
    
    def test_get_audio_format_ogg(self, file_handler):
        """Test OGG format detection."""
        ogg_bytes = b'OggS\x00\x02' + b'\x00' * 100
        fmt = file_handler.get_audio_format(ogg_bytes)
        assert fmt == "ogg"
    
    def test_get_audio_format_unknown(self, file_handler):
        """Test unknown format detection."""
        unknown_bytes = b'UNKN\x00\x00' + b'\x00' * 100
        fmt = file_handler.get_audio_format(unknown_bytes)
        assert fmt == "unknown"
    
    def test_get_audio_format_too_short(self, file_handler):
        """Test format detection with too short data."""
        short_bytes = b'\x00' * 5
        fmt = file_handler.get_audio_format(short_bytes)
        assert fmt == "unknown"
    
    def test_save_voice_sample_storage_disabled(self, file_handler):
        """Test saving when storage is disabled."""
        audio_bytes = b"test audio"
        result = file_handler.save_voice_sample(audio_bytes, "test.mp3")
        
        assert result is None
    
    def test_save_voice_sample_storage_enabled(self, file_handler_with_storage):
        """Test saving when storage is enabled."""
        audio_bytes = b"test audio content"
        filename = "test_voice.mp3"
        
        filepath = file_handler_with_storage.save_voice_sample(audio_bytes, filename)
        
        assert filepath is not None
        assert os.path.exists(filepath)
        
        # Verify content
        with open(filepath, "rb") as f:
            saved_content = f.read()
        assert saved_content == audio_bytes
    
    def test_create_file_from_bytes(self, file_handler):
        """Test creating file-like object from bytes."""
        audio_bytes = b"test audio data"
        filename = "voice_sample.mp3"
        
        file_obj = file_handler.create_file_from_bytes(audio_bytes, filename)
        
        assert file_obj.name == filename
        assert file_obj.read() == audio_bytes
        
        # Reset and read again
        file_obj.seek(0)
        assert file_obj.read() == audio_bytes
    
    def test_validate_audio_size_edge_cases(self, file_handler):
        """Test audio size validation edge cases."""
        # Exactly at limit
        audio_bytes = b'\x00' * (10 * 1024 * 1024)
        is_valid, error = file_handler.validate_audio_size(audio_bytes, max_size_mb=10.0)
        assert is_valid is True
        
        # Just over limit
        audio_bytes = b'\x00' * (10 * 1024 * 1024 + 1)
        is_valid, error = file_handler.validate_audio_size(audio_bytes, max_size_mb=10.0)
        assert is_valid is False
    
    def test_storage_path_creation(self):
        """Test that storage path is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "subdir", "storage")
            handler = FileHandler(storage_path=storage_path, enable_storage=True)
            
            # Storage path should be created
            assert os.path.exists(storage_path)

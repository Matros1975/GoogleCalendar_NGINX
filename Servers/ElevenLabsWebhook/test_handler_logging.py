"""
Test the exact scenario: importing transcription_handler and calling logger.info
"""
import os
import sys

# Set environment (same as debug config)
os.environ['LOG_DIR'] = '/home/ubuntu/GoogleCalendar_NGINX/logs'
os.environ['LOG_FILENAME'] = 'webhook.log'
os.environ['PYTHONPATH'] = '/home/ubuntu/GoogleCalendar_NGINX/Servers/ElevenLabsWebhook'

# First, setup root logger (this is what main.py does)
from src.utils.logger import setup_logger
setup_logger()  # Configure root logger

# Now import the handler (this creates logger = logging.getLogger(__name__))
from src.handlers import transcription_handler

print("=" * 70)
print("TEST: Simulating line 170 execution during debugging")
print("=" * 70)

# Get the module's logger
import logging
logger = logging.getLogger('src.handlers.transcription_handler')

print(f"\nLogger name: {logger.name}")
print(f"Logger level: {logging.getLevelName(logger.level)}")
print(f"Logger handlers: {len(logger.handlers)} direct, inherits from root")
print(f"Root logger handlers: {len(logging.getLogger().handlers)}")

for handler in logging.getLogger().handlers:
    if hasattr(handler, 'baseFilename'):
        print(f"  📝 File handler: {handler.baseFilename}")

print("\n" + "-" * 70)
print("Executing: logger.info('Processing post_call_transcription webhook')")
print("-" * 70)

# Execute the exact line from transcription_handler.py:170
logger.info("Processing post_call_transcription webhook")

print("✅ Line 170 executed")
print("=" * 70)

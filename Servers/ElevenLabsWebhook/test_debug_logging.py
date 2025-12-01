"""
Simulate the exact scenario from transcription_handler.py line 170
"""
import logging
import os

# Set environment variables (same as debug config)
os.environ['LOG_DIR'] = '/home/ubuntu/GoogleCalendar_NGINX/logs'
os.environ['LOG_FILENAME'] = 'webhook.log'

from src.utils.logger import setup_logger

# Get logger the same way as in transcription_handler.py
logger = logging.getLogger(__name__)
# Initialize it
setup_logger(__name__)

print("=" * 60)
print("SIMULATING DEBUG SCENARIO")
print("=" * 60)
print(f"Log file: {os.environ['LOG_DIR']}/{os.environ['LOG_FILENAME']}")
print("\nExecuting line 170 equivalent:")
print("  logger.info('Processing post_call_transcription webhook')")
print("-" * 60)

# This is the exact line from transcription_handler.py:170
logger.info("Processing post_call_transcription webhook")

print("-" * 60)
print("✅ Line executed - log should be visible NOW")
print("\nTo verify, run:")
print("  tail -1 /home/ubuntu/GoogleCalendar_NGINX/logs/webhook.log")
print("=" * 60)

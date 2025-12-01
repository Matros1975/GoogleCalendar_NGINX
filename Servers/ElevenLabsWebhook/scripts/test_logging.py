#!/usr/bin/env python3
"""Test script to verify log rotation functionality."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.logger import setup_logger

# Set LOG_DIR to local logs directory for testing
os.environ['LOG_DIR'] = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.environ['LOG_LEVEL'] = 'INFO'

# Initialize logger
logger = setup_logger("test_logger")

# Write test messages
logger.info("=" * 80)
logger.info("Log rotation test started")
logger.info("=" * 80)
logger.info("Writing test messages to verify file logging...")

# Write some test data
for i in range(10):
    logger.info(f"Test message {i+1}: This is a test to verify logging is working correctly.")
    logger.debug(f"Debug message {i+1}: This should not appear unless LOG_LEVEL=DEBUG")
    logger.warning(f"Warning message {i+1}: Testing warning level logs")
    
logger.info("=" * 80)
logger.info("Test completed successfully!")
logger.info("=" * 80)

# Show log file location
log_dir = os.environ.get('LOG_DIR', '/var/log/elevenlabs-webhook')
print(f"\n✅ Logs written to: {log_dir}/webhook.log")
print(f"View logs with: tail -f {log_dir}/webhook.log\n")

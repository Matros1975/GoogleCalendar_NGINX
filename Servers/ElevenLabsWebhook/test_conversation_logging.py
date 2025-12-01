"""
Test conversation_id logging feature.
"""
import asyncio
import os

# Set environment
os.environ['LOG_DIR'] = '/home/ubuntu/GoogleCalendar_NGINX/logs'
os.environ['LOG_FILENAME'] = 'webhook.log'
os.environ['LOG_LEVEL'] = 'INFO'

from src.utils.logger import setup_logger, conversation_context
import logging

# Setup logger
setup_logger()
logger = logging.getLogger(__name__)

async def simulate_webhook_handling(conv_id: str, agent_id: str):
    """Simulate handling a webhook with conversation context."""
    # Set conversation context
    conversation_context.set(conv_id)
    
    logger.info(f"Processing webhook for agent {agent_id}")
    logger.info("Validating payload")
    await asyncio.sleep(0.1)  # Simulate async work
    logger.info("Creating TopDesk ticket")
    await asyncio.sleep(0.1)
    logger.info("Ticket created successfully")

async def main():
    """Test concurrent webhook processing with different conversation IDs."""
    print("=" * 70)
    print("Testing Conversation ID Logging")
    print("=" * 70)
    print(f"Log file: /home/ubuntu/GoogleCalendar_NGINX/logs/webhook.log")
    print()
    
    # Simulate 3 concurrent webhooks with different conversation IDs
    tasks = [
        simulate_webhook_handling("conv_001", "agent_A"),
        simulate_webhook_handling("conv_002", "agent_B"),
        simulate_webhook_handling("conv_003", "agent_C"),
    ]
    
    print("Simulating 3 concurrent webhook calls...")
    await asyncio.gather(*tasks)
    print()
    print("✅ All webhooks processed!")
    print()
    print("Check log file for conversation IDs:")
    print("  grep 'conv_001' /home/ubuntu/GoogleCalendar_NGINX/logs/webhook.log")
    print("  grep 'conv_002' /home/ubuntu/GoogleCalendar_NGINX/logs/webhook.log")
    print("  grep 'conv_003' /home/ubuntu/GoogleCalendar_NGINX/logs/webhook.log")

if __name__ == "__main__":
    asyncio.run(main())

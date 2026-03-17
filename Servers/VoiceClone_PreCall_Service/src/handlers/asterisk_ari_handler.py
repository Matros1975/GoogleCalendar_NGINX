"""
Asterisk ARI (Asterisk REST Interface) Handler
Handles incoming SIP calls via Asterisk and connects them to ElevenLabs voice agents
"""
import asyncio
import logging
from typing import Optional
import aiohttp
from aiohttp import ClientSession, ClientWebSocketResponse

logger = logging.getLogger(__name__)


class AsteriskARIHandler:
    """Handles Asterisk ARI WebSocket connection and call events"""
    
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        app_name: str,
        call_controller,
        audio_service,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.app_name = app_name
        self.call_controller = call_controller
        self.audio_service = audio_service
        
        self.base_url = f"http://{host}:{port}/ari"
        self.ws_url = f"ws://{host}:{port}/ari/events?app={app_name}&api_key={username}:{password}"
        
        self.session: Optional[ClientSession] = None
        self.ws: Optional[ClientWebSocketResponse] = None
        self.running = False
        
    async def start(self):
        """Start the ARI WebSocket connection"""
        logger.info(f"🚀 Starting Asterisk ARI handler for app '{self.app_name}'")
        logger.info(f"📡 Connecting to {self.host}:{self.port}")
        
        self.session = aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self.username, self.password)
        )
        
        try:
            # Connect to WebSocket
            self.ws = await self.session.ws_connect(
                self.ws_url,
                heartbeat=30,
                timeout=aiohttp.ClientTimeout(total=None)
            )
            
            logger.info("✅ Connected to Asterisk ARI WebSocket")
            self.running = True
            
            # Start event loop
            asyncio.create_task(self._event_loop())
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Asterisk ARI: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the ARI connection"""
        logger.info("🛑 Stopping Asterisk ARI handler")
        self.running = False
        
        if self.ws and not self.ws.closed:
            await self.ws.close()
        
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _event_loop(self):
        """Main event loop for processing ARI events"""
        logger.info("🔄 ARI event loop started")
        
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    event = msg.json()
                    await self._handle_event(event)
                    
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.warning("⚠️ WebSocket closed by server")
                    break
                    
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"❌ WebSocket error: {self.ws.exception()}")
                    break
                    
        except Exception as e:
            logger.error(f"❌ Error in ARI event loop: {e}", exc_info=True)
        
        finally:
            logger.info("🔄 ARI event loop stopped")
            self.running = False
    
    async def _handle_event(self, event: dict):
        """Handle incoming ARI events"""
        event_type = event.get("type")
        
        logger.debug(f"📨 Received ARI event: {event_type}")
        
        if event_type == "StasisStart":
            await self._handle_stasis_start(event)
            
        elif event_type == "StasisEnd":
            await self._handle_stasis_end(event)
            
        elif event_type == "ChannelDestroyed":
            await self._handle_channel_destroyed(event)
            
        else:
            logger.debug(f"📭 Unhandled event type: {event_type}")
    
    async def _handle_stasis_start(self, event: dict):
        """Handle StasisStart event (call entered our application)"""
        channel = event.get("channel", {})
        channel_id = channel.get("id")
        caller_id = channel.get("caller", {}).get("number", "unknown")
        args = event.get("args", [])
        
        logger.info(f"📞 Incoming call from {caller_id} (channel: {channel_id})")
        
        try:
            # Get voice clone configuration based on caller or dialed number
            voice_clone_id = args[0] if args else "test"
            logger.info(f"🎤 Connecting to voice clone: {voice_clone_id}")
            
            # Send ring indication (early media with 180 Ringing)
            await self._ring_channel(channel_id)
            logger.info(f"📞 Sending ring indication to {channel_id}")
            
            # Let it ring for a moment
            await asyncio.sleep(2)
            
            # Now answer the call
            await self._answer_channel(channel_id)
            logger.info(f"✅ Call answered: {channel_id}")
            
            # Play test audio AFTER answering
            logger.info(f"🔊 Playing test audio on channel {channel_id}")
            await self._play_sound(channel_id, "sound:hello")
            
            # Keep channel alive
            await asyncio.sleep(10)
            
            logger.info(f"✅ Test complete for channel {channel_id}")
            
            # TODO: Create external media channel for ElevenLabs
            # external_host = await self._create_external_media(channel_id)
            # await self.call_controller.handle_incoming_call(...)
                
        except Exception as e:
            logger.error(f"❌ Error handling StasisStart: {e}", exc_info=True)
            await self._hangup_channel(channel_id)
    
    async def _handle_stasis_end(self, event: dict):
        """Handle StasisEnd event (call left our application)"""
        channel = event.get("channel", {})
        channel_id = channel.get("id")
        
        logger.info(f"📴 Call ended (channel: {channel_id})")
        
        # TODO: Notify call controller when it's implemented
        # try:
        #     await self.call_controller.handle_call_end(channel_id)
        # except Exception as e:
        #     logger.error(f"❌ Error handling StasisEnd: {e}", exc_info=True)
    
    async def _handle_channel_destroyed(self, event: dict):
        """Handle ChannelDestroyed event"""
        channel = event.get("channel", {})
        channel_id = channel.get("id")
        cause_txt = channel.get("cause_txt", "Unknown")
        
        logger.info(f"🔚 Channel destroyed: {channel_id} (cause: {cause_txt})")
    
    async def _ring_channel(self, channel_id: str):
        """Send ring indication to channel (180 Ringing with early media)"""
        url = f"{self.base_url}/channels/{channel_id}/ring"
        try:
            async with self.session.post(url) as resp:
                if resp.status == 204:
                    logger.info(f"✅ Ringing channel: {channel_id}")
                else:
                    error = await resp.text()
                    logger.warning(f"⚠️ Failed to ring channel: {error}")
        except Exception as e:
            logger.warning(f"⚠️ Error ringing channel: {e}")
    
    async def _answer_channel(self, channel_id: str):
        """Answer a channel"""
        url = f"{self.base_url}/channels/{channel_id}/answer"
        async with self.session.post(url) as resp:
            if resp.status == 204:
                logger.info(f"✅ Answered channel: {channel_id}")
            else:
                error = await resp.text()
                logger.error(f"❌ Failed to answer channel: {error}")
                raise Exception(f"Failed to answer channel: {error}")
    
    async def _hangup_channel(self, channel_id: str):
        """Hangup a channel"""
        url = f"{self.base_url}/channels/{channel_id}"
        try:
            async with self.session.delete(url) as resp:
                if resp.status in (204, 404):
                    logger.info(f"✅ Hung up channel: {channel_id}")
                else:
                    error = await resp.text()
                    logger.warning(f"⚠️ Failed to hangup channel: {error}")
        except Exception as e:
            logger.warning(f"⚠️ Error hanging up channel: {e}")
    
    async def _create_bridge(self) -> Optional[str]:
        """Create a mixing bridge for holding calls"""
        url = f"{self.base_url}/bridges"
        try:
            async with self.session.post(url, json={"type": "mixing"}) as resp:
                if resp.status == 200:
                    bridge = await resp.json()
                    bridge_id = bridge.get("id")
                    logger.info(f"✅ Created bridge: {bridge_id}")
                    return bridge_id
                else:
                    error = await resp.text()
                    logger.error(f"❌ Failed to create bridge: {error}")
                    return None
        except Exception as e:
            logger.error(f"❌ Error creating bridge: {e}")
            return None
    
    async def _add_channel_to_bridge(self, bridge_id: str, channel_id: str):
        """Add a channel to a bridge"""
        url = f"{self.base_url}/bridges/{bridge_id}/addChannel"
        try:
            async with self.session.post(url, json={"channel": channel_id}) as resp:
                if resp.status == 204:
                    logger.info(f"✅ Added channel {channel_id} to bridge {bridge_id}")
                else:
                    error = await resp.text()
                    logger.error(f"❌ Failed to add channel to bridge: {error}")
        except Exception as e:
            logger.error(f"❌ Error adding channel to bridge: {e}")
    
    async def _play_sound(self, channel_id: str, media: str):
        """Play a sound file to a channel"""
        url = f"{self.base_url}/channels/{channel_id}/play"
        try:
            async with self.session.post(url, json={"media": media}) as resp:
                if resp.status == 201:
                    logger.info(f"✅ Playing {media} to channel {channel_id}")
                else:
                    error = await resp.text()
                    logger.warning(f"⚠️ Could not play sound: {error}")
        except Exception as e:
            logger.warning(f"⚠️ Error playing sound: {e}")
    
    async def _create_external_media(self, channel_id: str) -> Optional[str]:
        """
        Create an external media channel for ElevenLabs
        Returns the external host:port where ElevenLabs should connect
        """
        # TODO: Implement external media channel creation
        # This will create a bridge between Asterisk RTP and ElevenLabs
        # For now, return placeholder
        logger.warning("⚠️ External media channel creation not yet implemented")
        return None

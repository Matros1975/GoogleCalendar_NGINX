"""
SIP handler for native SIP protocol support.

Implements voice cloning workflow using PJSUA2 SIP library.
This is an optional handler that can be enabled alongside Twilio.

Note: Requires pjsua2 library which needs system packages:
    apt-get install -y python3-pjsua2 libpjproject-dev
"""

import asyncio
import time
from typing import Optional
from pathlib import Path

try:
    import pjsua2 as pj
    PJSUA2_AVAILABLE = True
except ImportError:
    PJSUA2_AVAILABLE = False
    pj = None

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from src.models.call_context import CallContext
from src.models.call_instructions import CallInstructions
from src.services.call_controller import CallController
from src.services.audio_service import AudioService
from src.utils.logger import get_logger

logger = get_logger(__name__)


class WebSocketBridge:
    """
    Bridge between RTP audio (SIP call) and WebSocket (ElevenLabs).
    
    Handles bidirectional audio streaming between SIP call and
    ElevenLabs WebSocket for voice cloning.
    """
    
    def __init__(self, websocket_url: str, call_id: str):
        """
        Initialize WebSocket bridge.
        
        Args:
            websocket_url: ElevenLabs WebSocket URL
            call_id: Call identifier for logging
        """
        if not WEBSOCKETS_AVAILABLE:
            raise RuntimeError("websockets library not available - install with: pip install websockets>=12.0")
        
        self.websocket_url = websocket_url
        self.call_id = call_id
        self.websocket = None
        self.running = False
    
    async def start(self):
        """Start WebSocket connection."""
        try:
            logger.info(f"Connecting to WebSocket for call {self.call_id}")
            self.websocket = await websockets.connect(self.websocket_url)
            self.running = True
            logger.info(f"WebSocket connected for call {self.call_id}")
        except Exception as e:
            logger.error(f"Failed to connect WebSocket for call {self.call_id}: {e}")
            raise
    
    async def stop(self):
        """Stop WebSocket connection."""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            logger.info(f"WebSocket closed for call {self.call_id}")
    
    async def send_audio(self, audio_data: bytes):
        """
        Send audio to WebSocket.
        
        Args:
            audio_data: Audio bytes (PCM format)
        """
        if self.websocket and self.running:
            try:
                await self.websocket.send(audio_data)
            except Exception as e:
                logger.error(f"Error sending audio to WebSocket: {e}")
                self.running = False
    
    async def receive_audio(self) -> Optional[bytes]:
        """
        Receive audio from WebSocket.
        
        Returns:
            Audio bytes or None if error
        """
        if self.websocket and self.running:
            try:
                audio_data = await self.websocket.recv()
                return audio_data
            except Exception as e:
                logger.error(f"Error receiving audio from WebSocket: {e}")
                self.running = False
                return None
        return None


class VoiceCloneCall(pj.Call if PJSUA2_AVAILABLE else object):
    """
    SIP call handler with voice cloning integration.
    
    Manages SIP call lifecycle and integrates with CallController
    for voice cloning workflow.
    """
    
    def __init__(self, account, call_controller: CallController, audio_service: AudioService, call_id: int = -1):
        """
        Initialize SIP call handler.
        
        Args:
            account: PJSUA2 account
            call_controller: Business logic controller
            audio_service: Audio file service
            call_id: PJSUA2 call ID
        """
        if not PJSUA2_AVAILABLE:
            raise RuntimeError("pjsua2 library not available - see installation instructions in module docstring")
        
        super().__init__(account, call_id)
        self.controller = call_controller
        self.audio_service = audio_service
        self.websocket_bridge = None
        self.call_context = None
        self.instructions = None
    
    def onCallState(self, prm):
        """
        Callback for call state changes.
        
        Args:
            prm: Call state info
        """
        try:
            ci = self.getInfo()
            logger.info(f"SIP call {ci.id} state: {ci.stateText}")
            
            if ci.state == pj.PJSIP_INV_STATE_INCOMING:
                self._handle_incoming(ci)
            elif ci.state == pj.PJSIP_INV_STATE_CONFIRMED:
                asyncio.create_task(self._handle_confirmed(ci))
            elif ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
                self._handle_disconnected(ci)
                
        except Exception as e:
            logger.exception(f"Error in onCallState: {e}")
    
    def _handle_incoming(self, call_info):
        """
        Handle incoming call - answer it.
        
        Args:
            call_info: PJSUA2 call info
        """
        try:
            # Extract caller information
            remote_uri = call_info.remoteUri
            local_uri = call_info.localUri
            
            logger.info(f"Incoming SIP call from {remote_uri} to {local_uri}")
            
            # Create call context
            self.call_context = CallContext(
                call_id=f"SIP-{call_info.id}",
                caller_number=self._extract_number(remote_uri),
                recipient_number=self._extract_number(local_uri),
                status="ringing",
                protocol="sip"
            )
            
            # Answer call
            call_prm = pj.CallOpParam()
            call_prm.statusCode = pj.PJSIP_SC_OK
            self.answer(call_prm)
            
        except Exception as e:
            logger.error(f"Error handling incoming call: {e}")
            self.hangup(pj.CallOpParam())
    
    async def _handle_confirmed(self, call_info):
        """
        Handle call confirmation - start voice cloning workflow.
        
        Args:
            call_info: PJSUA2 call info
        """
        try:
            if not self.call_context:
                logger.error("Call context not initialized")
                return
            
            # Update call context
            self.call_context.status = "in-progress"
            
            # Get instructions from controller
            self.instructions = await self.controller.handle_inbound_call(self.call_context)
            
            # Execute instructions
            await self._execute_instructions()
            
        except Exception as e:
            logger.exception(f"Error handling confirmed call: {e}")
            self.hangup(pj.CallOpParam())
    
    def _handle_disconnected(self, call_info):
        """
        Handle call disconnection - cleanup.
        
        Args:
            call_info: PJSUA2 call info
        """
        try:
            logger.info(f"SIP call {call_info.id} disconnected")
            
            # Close WebSocket if active
            if self.websocket_bridge:
                asyncio.create_task(self.websocket_bridge.stop())
                
        except Exception as e:
            logger.error(f"Error handling disconnected call: {e}")
    
    async def _execute_instructions(self):
        """Execute call instructions from controller."""
        try:
            if not self.instructions:
                return
            
            # Play greeting audio if present
            if self.instructions.greeting_audio:
                await self._play_speech(self.instructions.greeting_audio.text)
            
            # If processing, start polling for status
            if self.instructions.clone_status == "processing":
                await self._poll_status()
            
            # If completed, connect to WebSocket
            elif self.instructions.clone_status == "completed" and self.instructions.websocket:
                await self._connect_websocket(self.instructions.websocket)
            
            # If failed, hangup
            elif self.instructions.should_hangup:
                if self.instructions.error_message:
                    await self._play_speech(self.instructions.error_message)
                self.hangup(pj.CallOpParam())
                
        except Exception as e:
            logger.exception(f"Error executing instructions: {e}")
            self.hangup(pj.CallOpParam())
    
    async def _poll_status(self):
        """Poll for clone status until ready or failed."""
        max_attempts = 30  # 30 attempts * 2 seconds = 60 seconds max
        attempt = 0
        
        while attempt < max_attempts:
            await asyncio.sleep(2)
            attempt += 1
            
            try:
                # Check status
                instructions = await self.controller.check_clone_status(self.call_context.call_id)
                
                if instructions.clone_status == "completed" and instructions.websocket:
                    logger.info(f"Clone ready for {self.call_context.call_id}")
                    await self._connect_websocket(instructions.websocket)
                    break
                    
                elif instructions.clone_status == "failed":
                    logger.error(f"Clone failed for {self.call_context.call_id}")
                    if instructions.error_message:
                        await self._play_speech(instructions.error_message)
                    self.hangup(pj.CallOpParam())
                    break
                    
                # Still processing - play hold music
                if instructions.hold_audio:
                    await self._play_audio_file(instructions.hold_audio.url)
                    
            except Exception as e:
                logger.error(f"Error polling status: {e}")
                break
    
    async def _play_speech(self, text: str):
        """
        Play text-to-speech.
        
        Note: This is a placeholder. In production, you would:
        1. Use a TTS service to generate audio
        2. Stream to call via RTP
        
        Args:
            text: Text to speak
        """
        logger.info(f"[SIP] Would play speech: {text}")
        # TODO: Implement TTS audio streaming
    
    async def _play_audio_file(self, url: str):
        """
        Play audio file to call.
        
        Note: This is a placeholder. In production, you would:
        1. Download audio file
        2. Stream to call via RTP
        
        Args:
            url: Audio file URL
        """
        try:
            audio_path = await self.audio_service.get_audio_file(url)
            logger.info(f"[SIP] Would play audio: {audio_path}")
            # TODO: Implement audio file streaming via RTP
        except Exception as e:
            logger.error(f"Error playing audio file: {e}")
    
    async def _connect_websocket(self, ws_instruction):
        """
        Connect to ElevenLabs WebSocket for voice streaming.
        
        Args:
            ws_instruction: WebSocket connection instruction
        """
        try:
            logger.info(f"Connecting to WebSocket for {self.call_context.call_id}")
            
            # Create WebSocket bridge
            self.websocket_bridge = WebSocketBridge(
                websocket_url=ws_instruction.url,
                call_id=self.call_context.call_id
            )
            
            await self.websocket_bridge.start()
            
            # TODO: Implement bidirectional audio streaming
            # This would involve:
            # 1. Capturing audio from SIP call (RTP)
            # 2. Sending to WebSocket
            # 3. Receiving audio from WebSocket
            # 4. Playing to SIP call (RTP)
            
            logger.info(f"WebSocket connected for {self.call_context.call_id}")
            
        except Exception as e:
            logger.exception(f"Error connecting to WebSocket: {e}")
            self.hangup(pj.CallOpParam())
    
    def _extract_number(self, uri: str) -> str:
        """
        Extract phone number from SIP URI.
        
        Args:
            uri: SIP URI (e.g., sip:+1234567890@domain.com)
            
        Returns:
            Phone number
        """
        try:
            # Extract between 'sip:' and '@'
            if "sip:" in uri:
                uri = uri.split("sip:")[1]
            if "@" in uri:
                uri = uri.split("@")[0]
            return uri.strip()
        except Exception:
            return uri


class VoiceCloneAccount(pj.Account if PJSUA2_AVAILABLE else object):
    """
    SIP account that handles incoming calls.
    """
    
    def __init__(self):
        """
        Initialize account - callbacks will be set by pjsua2.
        """
        if not PJSUA2_AVAILABLE:
            raise RuntimeError("pjsua2 library not available")
        
        super().__init__()
        self.controller = None
        self.audio_service = None
        self.active_calls = {}
    
    def set_services(self, call_controller: CallController, audio_service: AudioService):
        """
        Set services after account creation.
        
        Args:
            call_controller: Business logic controller
            audio_service: Audio file service
        """
        self.controller = call_controller
        self.audio_service = audio_service
    
    def onIncomingCall(self, prm):
        """
        Handle incoming call - create VoiceCloneCall instance.
        
        Args:
            prm: PJSUA2 OnIncomingCallParam
        """
        try:
            logger.info(f"📞 Incoming SIP call detected (call_id={prm.callId})")
            
            # Create call handler
            call = VoiceCloneCall(self, self.controller, self.audio_service, prm.callId)
            self.active_calls[prm.callId] = call
            
            logger.info(f"Created call handler for call_id={prm.callId}")
            
        except Exception as e:
            logger.exception(f"Error handling incoming call: {e}")


class SIPServer:
    """
    SIP server for handling incoming calls.
    
    Uses PJSUA2 library to create a SIP endpoint and handle calls.
    """
    
    def __init__(self, call_controller: CallController, audio_service: AudioService, host: str = "0.0.0.0", port: int = 5060):
        """
        Initialize SIP server.
        
        Args:
            call_controller: Business logic controller
            audio_service: Audio file service
            host: Bind address
            port: SIP port
        """
        if not PJSUA2_AVAILABLE:
            raise RuntimeError(
                "pjsua2 library not available. Please install system packages:\n"
                "  apt-get install -y python3-pjsua2 libpjproject-dev\n"
                "Then restart the service."
            )
        
        self.controller = call_controller
        self.audio_service = audio_service
        self.host = host
        self.port = port
        self.endpoint = None
        self.transport = None
        self.account = None
    
    async def start(self):
        """Start SIP server."""
        try:
            logger.info(f"Starting SIP server on {self.host}:{self.port}")
            
            # Create endpoint
            self.endpoint = pj.Endpoint()
            self.endpoint.libCreate()
            
            # Initialize endpoint
            ep_cfg = pj.EpConfig()
            self.endpoint.libInit(ep_cfg)
            
            # Create transport (UDP)
            transport_cfg = pj.TransportConfig()
            transport_cfg.port = self.port
            self.transport = self.endpoint.transportCreate(pj.PJSIP_TRANSPORT_UDP, transport_cfg)
            
            # Start endpoint
            self.endpoint.libStart()
            
            # Create account for incoming calls
            self.account = VoiceCloneAccount()
            self.account.set_services(self.controller, self.audio_service)
            
            acc_cfg = pj.AccountConfig()
            acc_cfg.idUri = f"sip:{self.host}:{self.port}"
            self.account.create(acc_cfg)
            
            logger.info(f"✅ SIP server started on {self.host}:{self.port}")
            
        except Exception as e:
            logger.exception(f"Failed to start SIP server: {e}")
            raise
    
    async def stop(self):
        """Stop SIP server."""
        try:
            logger.info("Stopping SIP server...")
            
            if self.account:
                self.account.shutdown()
            
            if self.endpoint:
                self.endpoint.libDestroy()
            
            logger.info("✅ SIP server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping SIP server: {e}")

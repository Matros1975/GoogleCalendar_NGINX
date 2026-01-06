# Asterisk + VoiceClone Service Setup

## Architecture

```
Linphone (macOS)
    ↓ SIP INVITE (port 5060)
    ↓
Asterisk Container (SIP/RTP handler)
    ↓ ARI WebSocket (port 8088)
    ↓ Events: StasisStart, StasisEnd
    ↓
Python Service Container
    ↓ HTTP API
    ↓
ElevenLabs Voice Agent
```

## Quick Start

### 1. Build and Start Services

```bash
cd /home/ubuntu/GoogleCalendar_NGINX/Servers/VoiceClone_PreCall_Service

# Build both containers
docker-compose build

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f asterisk
docker-compose logs -f voiceclone-service
```

### 2. Verify Asterisk is Running

```bash
# Check Asterisk version
docker exec asterisk-voiceclone asterisk -rx "core show version"

# Check PJSIP endpoints
docker exec asterisk-voiceclone asterisk -rx "pjsip show endpoints"

# Check ARI status
curl http://localhost:8088/ari/api-docs/resources.json \
  -u voiceclone:voiceclone_secret_2024
```

### 3. Test with Linphone

**SIP URI:** `sip:test@92.5.238.158:5060`

1. Open Linphone on your macOS laptop
2. Add a new SIP account (or use direct call)
3. Call: `sip:test@92.5.238.158:5060`
4. Asterisk should answer and connect to Python service

### 4. Monitor Call Flow

```bash
# Watch Asterisk console
docker exec -it asterisk-voiceclone asterisk -rvvv

# In Asterisk console:
pjsip set logger on
core set verbose 5

# Watch Python service logs
docker-compose logs -f voiceclone-service
```

## Configuration Files

### Asterisk Configs

- **`docker/asterisk/configs/pjsip.conf`**: SIP endpoint configuration
  - Anonymous endpoint accepts calls from any IP
  - External IP: `92.5.238.158` (your Oracle VM public IP)
  - Codecs: ulaw, alaw, opus
  
- **`docker/asterisk/configs/extensions.conf`**: Dialplan
  - Routes all incoming calls to Stasis app `voiceclone-app`
  - Passes extension and caller ID to Python service
  
- **`docker/asterisk/configs/ari.conf`**: ARI credentials
  - Username: `voiceclone`
  - Password: `voiceclone_secret_2024`
  
- **`docker/asterisk/configs/rtp.conf`**: RTP media configuration
  - Ports: `16384-32768`
  - STUN: `stun.l.google.com:19302`

### Python Service Environment

Add to your `.env`:

```bash
# Asterisk ARI Configuration
ASTERISK_ARI_HOST=127.0.0.1
ASTERISK_ARI_PORT=8088
ASTERISK_ARI_USERNAME=voiceclone
ASTERISK_ARI_PASSWORD=voiceclone_secret_2024
ASTERISK_ARI_APP=voiceclone-app

# Enable SIP handler
ENABLE_SIP_HANDLER=true
```

## Network Architecture

### Using `network_mode: host`

Both containers use host networking for simplicity:

- **Asterisk**: Needs direct access to ports 5060 (SIP) and 16384-32768 (RTP)
- **Python Service**: Connects to Asterisk on `127.0.0.1:8088` (localhost)

**Ports exposed on host:**
- `5060/udp`: SIP signaling
- `8088/tcp`: Asterisk HTTP/ARI
- `8000/tcp`: Python service HTTP API
- `16384-32768/udp`: RTP media streams

### Firewall Rules (Already configured)

```bash
# UFW rules
sudo ufw allow 5060/udp
sudo ufw allow 16384:32768/udp

# Oracle Cloud Security List (already added by you)
# Ingress: 0.0.0.0/0 → 5060/udp
# Ingress: 0.0.0.0/0 → 16384-32768/udp
```

## Troubleshooting

### Asterisk Not Starting

```bash
# Check container logs
docker-compose logs asterisk

# Check Asterisk CLI
docker exec -it asterisk-voiceclone asterisk -rvvv

# Verify configuration syntax
docker exec asterisk-voiceclone asterisk -rx "pjsip reload"
```

### No SIP Packets Received

```bash
# Verify firewall (should see packets)
sudo tcpdump -i any -n port 5060 -v

# Check Asterisk is listening
docker exec asterisk-voiceclone netstat -uln | grep 5060
```

### Python Service Can't Connect to ARI

```bash
# Test ARI endpoint
curl http://localhost:8088/ari/api-docs/resources.json \
  -u voiceclone:voiceclone_secret_2024

# Check WebSocket
wscat -c ws://localhost:8088/ari/events?app=voiceclone-app \
  -H "Authorization: Basic $(echo -n 'voiceclone:voiceclone_secret_2024' | base64)"
```

### Call Connects but No Audio

```bash
# Check RTP ports are open
sudo ufw status | grep 16384

# Verify NAT/STUN configuration
docker exec asterisk-voiceclone asterisk -rx "pjsip show settings"

# Check RTP debug
docker exec asterisk-voiceclone asterisk -rx "rtp set debug on"
```

## Call Flow Details

### 1. SIP INVITE Arrives

```
Linphone → 92.5.238.158:5060 (INVITE sip:test@92.5.238.158)
         ↓
Asterisk receives on pjsip transport-udp
         ↓
Matches [anonymous] endpoint (0.0.0.0/0)
         ↓
Routes to context [incoming]
```

### 2. Dialplan Execution

```
extensions.conf [incoming]:
  exten => test,1,Answer()               ; Answer call immediately
        => n,Stasis(voiceclone-app)      ; Pass to ARI application
        => n,Hangup()                    ; Hangup when done
```

### 3. ARI Event Sent

```
Asterisk → WebSocket → Python Service
Event: {
  "type": "StasisStart",
  "channel": {
    "id": "1234567890.1",
    "caller": {"number": "YOUR_LINPHONE_NUMBER"}
  },
  "args": ["test"]
}
```

### 4. Python Service Handles Call

```python
async def _handle_stasis_start(event):
    channel_id = event["channel"]["id"]
    caller_id = event["channel"]["caller"]["number"]
    
    # Answer already done by dialplan
    
    # Create external media channel for ElevenLabs
    external_host = await create_external_media(channel_id)
    
    # Connect to ElevenLabs voice agent
    await call_controller.handle_incoming_call(
        channel_id, caller_id, "test", external_host
    )
```

## Next Steps

1. **Implement External Media Channel**
   - Bridge Asterisk RTP to ElevenLabs WebSocket/SIP
   - Handle audio transcoding if needed
   
2. **Add Voice Clone Selection**
   - Map caller ID or dialed number to voice clone config
   - Query database for agent settings
   
3. **Implement Call Recording**
   - Use Asterisk MixMonitor or ARI recording
   
4. **Add Call Metrics**
   - Track call duration, quality, latency
   - Store in database

## Latency Analysis

```
Component                     Latency    Notes
────────────────────────────────────────────────────────────
Network (Linphone → Asterisk) 5-30ms     Your ISP + Internet
Asterisk SIP Processing       2-5ms      SIP parsing, routing
Asterisk RTP Forwarding       2-8ms      Packet forwarding
ARI WebSocket Event           1-3ms      Localhost communication
Python Event Handler          1-5ms      Event processing
Network (Asterisk → ElevenLabs) 10-50ms  Internet + ElevenLabs
ElevenLabs Processing         50-150ms   AI voice generation
────────────────────────────────────────────────────────────
Total One-Way Latency:        71-251ms   Acceptable for voice AI
```

**Target:** < 300ms end-to-end (meets voice agent requirements)

## Production Recommendations

1. **Use separate network instead of host mode**
   - Create Docker network: `docker network create voiceclone-net`
   - Configure proper port mappings
   - Improves security and isolation

2. **Add TLS for ARI**
   - Configure `http.conf` with SSL certificates
   - Use `wss://` instead of `ws://`

3. **Implement health checks**
   - Already configured in docker-compose.yml
   - Monitor with: `docker-compose ps`

4. **Add call analytics**
   - Store CDRs (Call Detail Records) in database
   - Track success/failure rates

5. **Optimize RTP path**
   - Use `directmedia=yes` if possible
   - Configure STUN/TURN for NAT traversal

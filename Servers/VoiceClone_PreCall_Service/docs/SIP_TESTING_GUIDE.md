# SIP Testing Guide

This guide explains how to test the SIP handler functionality using softphone applications.

## Overview

The VoiceClone Pre-Call Service now supports **dual protocols**:
- **Twilio** (TwiML-based webhooks) - Primary protocol
- **Native SIP** (PJSUA2-based) - Optional secondary protocol

## Prerequisites

### System Requirements
- Linux-based system (Ubuntu/Debian recommended)
- Python 3.11+
- PJSUA2 library installed

### Installing PJSUA2

On Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y python3-pjsua2 libpjproject-dev
```

### Enable SIP Handler

Add to `.env`:
```bash
ENABLE_SIP_HANDLER=true
SIP_HOST=0.0.0.0
SIP_PORT=5060
```

## SIP Softphone Setup

### Option 1: Linphone (Recommended)

1. **Install Linphone**
   ```bash
   sudo apt-get install linphone
   ```

2. **Configure Account**
   - Open Linphone
   - Go to Settings → Accounts → Add
   - Configure:
     - Username: `test`
     - Domain: `localhost:5060` (or your server IP)
     - Display name: `Test User`
     - Transport: `UDP`
     - Register: `No` (for local testing)

3. **Make Test Call**
   - Enter SIP URI: `sip:voiceclone@localhost:5060`
   - Click Call
   - You should hear the greeting message

### Option 2: Zoiper

1. **Install Zoiper**
   - Download from https://www.zoiper.com/

2. **Configure Account**
   - Add new account
   - Domain: Your server IP or hostname
   - Port: 5060
   - Protocol: UDP

3. **Test Call**
   - Dial: `sip:voiceclone@<server-ip>:5060`

## Testing Workflow

### 1. Start Service with SIP Enabled

```bash
cd /home/ubuntu/GoogleCalendar_NGINX/Servers/VoiceClone_PreCall_Service
source .venv/bin/activate
export ENABLE_SIP_HANDLER=true
python -m src.main
```

Check logs for:
```
✅ SIP server started on 0.0.0.0:5060
```

### 2. Make Test Call

Using Linphone or Zoiper, call:
```
sip:test@<server-ip>:5060
```

### 3. Expected Behavior

1. **Call Answered**
   - SIP server answers immediately
   - Log: `Incoming SIP call from...`

2. **Greeting Played**
   - You should hear: "Hello thanks for calling. Please hold..."
   - Log: `[SIP] Would play speech: ...`

3. **Voice Cloning Started**
   - Background cloning process starts
   - Log: `🎤 Cloning voice for...`

4. **Status Polling**
   - System polls every 2 seconds
   - Log: `⏳ Clone still processing for...`

5. **Clone Complete**
   - WebSocket connection established
   - Log: `✅ Voice clone ready: ...`
   - Log: `WebSocket connected for...`

### 4. Check Database

```sql
SELECT call_id, caller_id, status, cloned_voice_id, created_at 
FROM call_logs 
WHERE protocol = 'sip' 
ORDER BY created_at DESC 
LIMIT 10;
```

## Troubleshooting

### SIP Server Not Starting

**Error**: `pjsua2 library not available`

**Solution**: Install PJSUA2
```bash
sudo apt-get install -y python3-pjsua2 libpjproject-dev
```

### Call Not Connecting

**Issue**: "Connection refused"

**Solutions**:
1. Check SIP port is open:
   ```bash
   sudo netstat -tulpn | grep 5060
   ```

2. Check firewall:
   ```bash
   sudo ufw allow 5060/udp
   sudo ufw allow 16384:32768/udp  # RTP media
   ```

3. Verify service is listening:
   ```bash
   curl -f http://localhost:8000/health
   ```

### No Audio

**Issue**: Call connects but no audio

**Current Limitation**: Audio streaming (TTS and RTP) is **not yet implemented** in this version. The SIP handler includes placeholder methods for:
- `_play_speech()` - TODO: Implement TTS streaming
- `_play_audio_file()` - TODO: Implement audio file streaming via RTP
- `_connect_websocket()` - TODO: Implement bidirectional audio streaming

These will be implemented in future versions.

### WebSocket Connection Fails

**Issue**: Clone completes but WebSocket doesn't connect

**Check**:
1. ElevenLabs API key is valid
2. ElevenLabs agent ID is correct
3. Network connectivity to `api.elevenlabs.io`

## Docker Testing

### Build with SIP Support

```bash
cd /home/ubuntu/GoogleCalendar_NGINX/Servers/VoiceClone_PreCall_Service
docker build -t voiceclone-sip:test .
```

### Run Container

```bash
docker run -it --rm \
  -p 8000:8000 \
  -p 5060:5060/udp \
  -p 16384-32768:16384-32768/udp \
  -e ENABLE_SIP_HANDLER=true \
  -e ELEVENLABS_API_KEY="your_key" \
  -e ELEVENLABS_AGENT_ID="your_agent_id" \
  -e DATABASE_URL="your_db_url" \
  -e WEBHOOK_SECRET="your_secret" \
  voiceclone-sip:test
```

### Docker Compose

Uncomment SIP ports in `docker-compose.yml`:
```yaml
ports:
  - "8000:8000"
  - "5060:5060/udp"
  - "16384-32768:16384-32768/udp"
```

Then:
```bash
docker-compose up voiceclone-precall
```

## Performance Testing

### Load Testing with SIPp

1. **Install SIPp**
   ```bash
   sudo apt-get install sip-tester
   ```

2. **Run Load Test**
   ```bash
   sipp -sn uac -r 1 -l 10 <server-ip>:5060
   ```

3. **Monitor**
   ```bash
   docker stats voiceclone-precall
   ```

## Logging

### Enable Debug Logging

Set in `.env`:
```bash
LOG_LEVEL=DEBUG
```

### Key Log Messages

- `📞 Inbound call:` - Call received
- `🎤 Cloning voice for` - Clone started
- `⏳ Clone still processing` - Status check
- `✅ Voice clone ready` - Clone completed
- `WebSocket connected` - Ready for conversation
- `❌ Clone failed` - Error occurred

## Security Considerations

1. **Firewall Rules**
   - Only open SIP port (5060) to trusted networks
   - Use VPN or IP whitelisting for production

2. **Authentication**
   - Current version has no SIP authentication
   - For production, implement SIP digest authentication

3. **Encryption**
   - Consider using TLS for SIP signaling (SIPS)
   - Use SRTP for encrypted media

## Next Steps

1. Implement audio streaming (TTS and RTP)
2. Add SIP authentication
3. Support SIP over TLS (SIPS)
4. Add call recording
5. Implement call transfer

## Support

For issues or questions:
- Check logs: `/var/log/mcp-services/voiceclone.log`
- Review GitHub issues
- Contact development team

#!/bin/bash
#
# Test Twilio Webhook Endpoints Locally
#
# This script simulates Twilio webhook requests for testing the VoiceClone service
# without requiring actual Twilio infrastructure.
#
# Prerequisites:
#   - Set SKIP_WEBHOOK_SIGNATURE_VALIDATION=true in .env for local testing
#   - Service running on localhost:8000 or set VOICECLONE_URL

set -e

# Configuration
VOICECLONE_URL="${VOICECLONE_URL:-http://localhost:8000}"
CALL_SID="CAtest123456789abcdef0123456789"
FROM_NUMBER="+31612345678"
TO_NUMBER="+31201234567"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================="
echo "Twilio Webhook Test Script"
echo "========================================="
echo ""
echo "Target URL: $VOICECLONE_URL"
echo "Call SID: $CALL_SID"
echo ""

# Test 1: Inbound call webhook
echo -e "${YELLOW}Test 1: POST /webhooks/inbound (Inbound Call)${NC}"
echo "Simulating Twilio inbound call webhook..."

RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -X POST "${VOICECLONE_URL}/webhooks/inbound" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "CallSid=${CALL_SID}" \
  -d "AccountSid=ACtest123456789" \
  -d "From=${FROM_NUMBER}" \
  -d "To=${TO_NUMBER}" \
  -d "CallStatus=ringing" \
  -d "Direction=inbound" \
  -d "ApiVersion=2010-04-01")

HTTP_BODY=$(echo "$RESPONSE" | sed -e 's/HTTP_STATUS\:.*//g')
HTTP_STATUS=$(echo "$RESPONSE" | tr -d '\n' | sed -e 's/.*HTTP_STATUS://')

if [ "$HTTP_STATUS" -eq 200 ]; then
  echo -e "${GREEN}✓ Inbound call endpoint responded with 200 OK${NC}"
  echo "Response (TwiML):"
  echo "$HTTP_BODY" | xmllint --format - 2>/dev/null || echo "$HTTP_BODY"
else
  echo -e "${RED}✗ Inbound call endpoint failed with HTTP $HTTP_STATUS${NC}"
  echo "Response:"
  echo "$HTTP_BODY"
  exit 1
fi

echo ""
echo "Waiting 3 seconds for voice cloning to start..."
sleep 3
echo ""

# Test 2: Status callback webhook
echo -e "${YELLOW}Test 2: POST /webhooks/status-callback (Check Clone Status)${NC}"
echo "Simulating Twilio status callback webhook..."

RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -X POST "${VOICECLONE_URL}/webhooks/status-callback?call_sid=${CALL_SID}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "CallSid=${CALL_SID}" \
  -d "CallStatus=in-progress")

HTTP_BODY=$(echo "$RESPONSE" | sed -e 's/HTTP_STATUS\:.*//g')
HTTP_STATUS=$(echo "$RESPONSE" | tr -d '\n' | sed -e 's/.*HTTP_STATUS://')

if [ "$HTTP_STATUS" -eq 200 ]; then
  echo -e "${GREEN}✓ Status callback endpoint responded with 200 OK${NC}"
  echo "Response (TwiML):"
  echo "$HTTP_BODY" | xmllint --format - 2>/dev/null || echo "$HTTP_BODY"
  
  # Check if response contains "processing" or "completed"
  if echo "$HTTP_BODY" | grep -q "wss://api.elevenlabs.io"; then
    echo -e "${GREEN}✓ Voice clone completed! TwiML contains ElevenLabs WebSocket URL${NC}"
  elif echo "$HTTP_BODY" | grep -q "<Redirect>"; then
    echo -e "${YELLOW}⏳ Voice clone still processing, TwiML redirects back for retry${NC}"
  else
    echo -e "${YELLOW}⚠ Unknown TwiML response state${NC}"
  fi
else
  echo -e "${RED}✗ Status callback endpoint failed with HTTP $HTTP_STATUS${NC}"
  echo "Response:"
  echo "$HTTP_BODY"
  exit 1
fi

echo ""
echo "========================================="
echo -e "${GREEN}All tests passed!${NC}"
echo "========================================="
echo ""
echo "Next Steps:"
echo "1. Check service logs: docker compose logs -f voiceclone-precall"
echo "2. Verify database records: docker compose exec postgres psql -U postgres -d voice_clones -c 'SELECT * FROM call_log;'"
echo "3. Test with real Twilio: Configure webhook URL in Twilio console"
echo ""
echo "Webhook URLs for Twilio configuration:"
echo "  Inbound: ${VOICECLONE_URL}/webhooks/inbound"
echo "  Status Callback: ${VOICECLONE_URL}/webhooks/status-callback"
echo ""

# Centralized Log Directory

This directory contains application log files for **all MCP services**.

## Configuration

All services write logs to this shared directory with individual filenames:

- **Shared directory**: `./logs/` (repository root)
- **Rotation size**: 2 MB per file
- **Rotated format**: `{service}_YYYYMMDD_HHMMSS.log`
- **Backup count**: 10 rotated files per service

## Log Files by Service

### ElevenLabs Webhook Service
- **Current**: `webhook.log`
- **Rotated**: `webhook_20251129_143022.log`
- **Environment**: `LOG_FILENAME=webhook.log`

### Google Calendar MCP
- **Current**: `calendar.log`
- **Rotated**: `calendar_20251129_140000.log`
- **Environment**: `LOG_FILENAME=calendar.log`

### TopDesk Custom MCP
- **Current**: `topdesk.log`
- **Rotated**: `topdesk_20251129_141500.log`
- **Environment**: `LOG_FILENAME=topdesk.log`

### Gmail MCP
- **Current**: `gmail.log`
- **Rotated**: `gmail_20251129_142000.log`
- **Environment**: `LOG_FILENAME=gmail.log`

## Environment Variables

- `LOG_DIR`: `/var/log/mcp-services` (Docker) or `./logs` (local)
- `LOG_FILENAME`: Service-specific filename (e.g., `webhook.log`, `calendar.log`)
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR (default: INFO)
- `LOG_FORMAT`: "text" or "json" (default: text)

## Directory Structure

```
logs/
├── README.md
├── webhook.log                    # ElevenLabs Webhook (current)
├── webhook_20251129_143022.log    # Rotated
├── calendar.log                   # Calendar MCP (current)
├── calendar_20251129_140000.log   # Rotated
├── topdesk.log                    # TopDesk MCP (current)
├── topdesk_20251129_141500.log    # Rotated
├── gmail.log                      # Gmail MCP (current)
└── gmail_20251129_142000.log      # Rotated
```

## Viewing Logs

### All Logs
```bash
# View all current logs
tail -f logs/*.log

# Search all logs for errors
grep ERROR logs/*.log

# Search specific service
grep ERROR logs/webhook.log
```

### Individual Services
```bash
# ElevenLabs Webhook
tail -f logs/webhook.log

# Calendar MCP
tail -f logs/calendar.log

# TopDesk MCP
tail -f logs/topdesk.log
```

## Docker Logging

When running in Docker, logs are mapped from container to host:

**Container Path:** `/var/log/mcp-services/{service}.log`  
**Host Path:** `./logs/{service}.log`

```bash
# View from Docker (stdout + file logs)
docker logs -f elevenlabs-webhook

# Access log files from inside container
docker exec elevenlabs-webhook tail -f /var/log/mcp-services/webhook.log

# Or view directly on host
tail -f logs/webhook.log
```

## Log Rotation

Each service automatically rotates logs when file reaches 2MB:

1. Current file closed (e.g., `webhook.log`)
2. Renamed with timestamp (e.g., `webhook_20251129_143022.log`)
3. New current file created
4. Oldest rotated files deleted after 10 backups

## Cleanup

Remove old rotated logs:
```bash
# Remove logs older than 7 days
find logs/ -name "*_*.log" -mtime +7 -delete

# Remove all rotated logs (keep current)
rm logs/*_*.log

# Remove specific service rotated logs
rm logs/webhook_*.log
```

## Troubleshooting

### No logs appearing
```bash
# Check LOG_DIR is set
echo $LOG_DIR

# Check directory permissions
ls -ld logs/

# Check service is logging to stdout
docker logs elevenlabs-webhook
```

### Disk space issues
```bash
# Check total log size
du -sh logs/

# Check individual files
ls -lh logs/

# Manually trigger cleanup
find logs/ -name "*_*.log" -mtime +7 -delete
```

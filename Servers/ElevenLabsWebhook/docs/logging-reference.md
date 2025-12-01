# ElevenLabs Webhook Logging - Quick Reference

## Log File Locations

### Development (Local)
```bash
Location: ./logs/webhook.log
View:     tail -f logs/webhook.log
```

### Docker Container
```bash
Location: /var/log/elevenlabs-webhook/webhook.log (inside container)
Volume:   elevenlabs-logs (Docker named volume)

# View logs from host
docker logs -f elevenlabs-webhook                    # Console output (stdout)
docker exec elevenlabs-webhook tail -f /var/log/elevenlabs-webhook/webhook.log  # File logs

# Copy log file to host
docker cp elevenlabs-webhook:/var/log/elevenlabs-webhook/webhook.log ./webhook.log
```

### Production (Oracle VM)
```bash
Location: /var/log/elevenlabs-webhook/webhook.log
View:     tail -f /var/log/elevenlabs-webhook/webhook.log

# If running via systemd
journalctl -u elevenlabs-webhook -f
```

## Log Rotation Details

| Setting | Value |
|---------|-------|
| **Max file size** | 2 MB |
| **Rotated format** | `webhook_YYYYMMDD_HHMMSS.log` |
| **Backup count** | 10 files |
| **Rotation trigger** | When current log reaches 2 MB |

## Environment Variables

```bash
LOG_DIR=/var/log/elevenlabs-webhook    # Directory for log files
LOG_LEVEL=INFO                          # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=text                         # text or json
```

## Docker Volume Management

```bash
# Inspect volume
docker volume inspect elevenlabs-logs

# List files in volume
docker exec elevenlabs-webhook ls -lh /var/log/elevenlabs-webhook/

# Backup logs from Docker volume
docker run --rm -v elevenlabs-logs:/logs -v $(pwd):/backup alpine tar czf /backup/elevenlabs-logs-backup.tar.gz /logs

# Restore logs to Docker volume
docker run --rm -v elevenlabs-logs:/logs -v $(pwd):/backup alpine tar xzf /backup/elevenlabs-logs-backup.tar.gz -C /
```

## Troubleshooting

### No logs appearing in file
```bash
# Check LOG_DIR is set correctly
docker exec elevenlabs-webhook env | grep LOG_DIR

# Check directory exists and has permissions
docker exec elevenlabs-webhook ls -ld /var/log/elevenlabs-webhook/

# Check if volume is mounted
docker inspect elevenlabs-webhook | grep -A 10 Mounts
```

### Disk space issues
```bash
# Check log file sizes
docker exec elevenlabs-webhook du -sh /var/log/elevenlabs-webhook/*

# Remove old rotated logs manually
docker exec elevenlabs-webhook find /var/log/elevenlabs-webhook/ -name "webhook_*.log" -mtime +7 -delete
```

### View logs by level
```bash
# Errors only
docker exec elevenlabs-webhook grep ERROR /var/log/elevenlabs-webhook/webhook.log

# Warnings and errors
docker exec elevenlabs-webhook grep -E "WARNING|ERROR" /var/log/elevenlabs-webhook/webhook.log
```

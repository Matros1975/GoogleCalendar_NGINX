# Alternative: Add DuckDNS to existing MCP container

## Method 1: Modify existing Dockerfile

Add to your main Dockerfile:

```dockerfile
# Install cron and required tools
RUN apk add --no-cache dcron curl bind-tools

# Copy DuckDNS script
COPY scripts/duckdns-update.sh /usr/local/bin/duckdns-update.sh
RUN chmod +x /usr/local/bin/duckdns-update.sh

# Add cron job
RUN echo "*/5 * * * * /usr/local/bin/duckdns-update.sh" | crontab -

# Modify entrypoint to start cron
RUN echo '#!/bin/sh' > /docker-entrypoint-combined.sh && \
    echo 'crond -b' >> /docker-entrypoint-combined.sh && \
    echo 'exec "$@"' >> /docker-entrypoint-combined.sh && \
    chmod +x /docker-entrypoint-combined.sh

ENTRYPOINT ["/docker-entrypoint-combined.sh"]
```

## Method 2: Add environment variables to docker-compose.yml

```yaml
calendar-mcp:
  environment:
    - DUCKDNS_DOMAIN=yourdomain
    - DUCKDNS_TOKEN=6fb5210e-71c6-4327-bbf9-af8283a08b37
    # ... existing environment variables
```

## Method 3: External cron job on host

Create `/etc/cron.d/duckdns-update`:

```bash
# Update DuckDNS every 5 minutes
*/5 * * * * ubuntu /home/ubuntu/GoogleCalendar_NGINX/scripts/duckdns-update.sh
```

## Pros/Cons

### Dedicated Container (Recommended)
✅ Clean separation of concerns
✅ Easy to maintain and debug
✅ Can restart independently
✅ Minimal resource usage
❌ One more container

### Combined with MCP
✅ Fewer containers
✅ Shared environment
❌ Mixed responsibilities
❌ Harder to debug
❌ MCP restart affects DNS updates
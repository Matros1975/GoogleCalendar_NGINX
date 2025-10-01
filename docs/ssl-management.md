# SSL Certificate Management

## Overview

SSL certificate management for matrosmcp.duckdns.org is now fully containerized using a dedicated `ssl-renewer` container. This replaces the previous host-level cron job approach with a consistent, portable, and maintainable containerized solution.

## Architecture

### Container Structure

The SSL renewal system consists of:

1. **ssl-renewer Container**: Dedicated Alpine-based container that handles certificate renewal
2. **Certificate Storage**: Let's Encrypt certificates stored in `/etc/letsencrypt` on the host
3. **Docker Integration**: Container can restart NGINX via Docker socket access
4. **Logging**: Centralized logging to Docker volume `ssl-renewal-logs`

### Components

```
Servers/NGINX/ssl-renewer/
├── Dockerfile              # Container build configuration
├── ssl-renewal.sh          # Main renewal logic script
├── ssl-crontab             # Cron schedule (twice daily)
└── health-check.sh         # Container health monitoring
```

## How It Works

### Renewal Schedule

The SSL certificate renewal runs **twice daily**:
- **3:30 AM** (Europe/Amsterdam timezone)
- **3:30 PM** (Europe/Amsterdam timezone)

This schedule ensures:
- Redundancy if one run fails
- Timely renewal before certificate expiration
- Minimal impact during low-traffic hours

### Renewal Process

1. **Check Certificate Expiry**: Verifies if certificate expires within 30 days
2. **Run Certbot**: Executes `certbot renew` if renewal is needed
3. **Detect Changes**: Compares certificate file modification time before/after renewal
4. **Restart NGINX**: Only restarts NGINX if certificate was actually renewed
5. **Test HTTPS**: Validates HTTPS endpoint after restart
6. **Log Results**: Comprehensive logging of all steps

### Smart Restart Logic

The container only restarts NGINX when:
- Certificate renewal was successful
- Certificate file modification time changed
- This prevents unnecessary NGINX restarts

## Configuration

### Environment Variables

Set in `docker-compose.yml` for the `ssl-renewer` service:

```yaml
environment:
  - DOMAIN=matrosmcp.duckdns.org          # Domain to renew
  - TZ=Europe/Amsterdam                    # Timezone for cron schedule
  - COMPOSE_PROJECT_PATH=/compose          # Path to docker-compose.yml
  - NGINX_CONTAINER=nginx-proxy            # NGINX container name
  - CERT_EXPIRY_DAYS=30                    # Renewal threshold (days)
```

### Volume Mounts

Required volumes for the ssl-renewer container:

```yaml
volumes:
  - /etc/letsencrypt:/etc/letsencrypt:rw          # Certificate storage (read-write)
  - /var/run/docker.sock:/var/run/docker.sock:ro  # Docker API access (read-only)
  - ./docker-compose.yml:/compose/docker-compose.yml:ro  # Compose file
  - ssl-renewal-logs:/var/log/ssl-renewal          # Log storage
```

## Deployment

### Initial Setup

1. **Ensure Let's Encrypt certificates exist**:
   ```bash
   # If certificates don't exist, create them first
   # See docs/letsencrypt-setup-guide.md
   ```

2. **Deploy the container**:
   ```bash
   cd /path/to/GoogleCalendar_NGINX
   docker compose up -d ssl-renewer
   ```

3. **Verify container is running**:
   ```bash
   docker compose ps ssl-renewer
   docker compose logs ssl-renewer
   ```

### Monitoring

#### Check Container Health

```bash
# View container status
docker compose ps ssl-renewer

# Check health status
docker inspect ssl-renewer --format='{{.State.Health.Status}}'

# View recent logs
docker compose logs --tail=50 ssl-renewer
```

#### View Renewal Logs

```bash
# View logs from container
docker compose exec ssl-renewer cat /var/log/ssl-renewal/renewal.log

# View recent log entries
docker compose exec ssl-renewer tail -f /var/log/ssl-renewal/renewal.log

# View logs from host (via volume)
docker volume inspect ssl-renewal-logs
```

#### Manual Renewal Test

To test renewal manually:

```bash
# Execute renewal script manually
docker compose exec ssl-renewer /scripts/ssl-renewal.sh

# Or force renewal (for testing)
docker compose exec ssl-renewer certbot renew --force-renewal
```

### Troubleshooting

#### Container Won't Start

```bash
# Check container logs
docker compose logs ssl-renewer

# Common issues:
# - Docker socket not accessible
# - /etc/letsencrypt not mounted correctly
# - Missing certificates
```

#### Renewal Fails

```bash
# Check certbot logs
docker compose exec ssl-renewer cat /var/log/ssl-renewal/renewal.log

# Common issues:
# - Port 80 not accessible (firewall)
# - Domain DNS not pointing to server
# - Rate limit exceeded (Let's Encrypt)
```

#### NGINX Not Restarting

```bash
# Verify Docker socket access
docker compose exec ssl-renewer docker ps

# Check NGINX container name
docker compose ps nginx-proxy

# Test manual restart
docker compose exec ssl-renewer docker restart nginx-proxy
```

## Migration from Host Cron

### Previous Setup (Host-Level)

The old system used host-level cron jobs:
```bash
# /etc/cron.d/ssl-renewal or crontab -l
30 3,15 * * * /home/ubuntu/GoogleCalendar_NGINX/scripts/renew-certificate.sh
```

### Migration Steps

1. **Remove host-level cron job**:
   ```bash
   # Check existing cron jobs
   sudo crontab -l | grep -i certbot
   sudo crontab -l | grep -i renew
   
   # Remove the cron job
   sudo crontab -e
   # Delete the SSL renewal line
   
   # Or if using /etc/cron.d/
   sudo rm -f /etc/cron.d/ssl-renewal
   ```

2. **Deploy containerized solution**:
   ```bash
   cd /home/ubuntu/GoogleCalendar_NGINX
   git pull origin main
   docker compose up -d ssl-renewer
   ```

3. **Verify migration**:
   ```bash
   # Confirm host cron removed
   sudo crontab -l | grep -i certbot  # Should show nothing
   
   # Confirm container running
   docker compose ps ssl-renewer
   
   # Check container logs
   docker compose logs ssl-renewer
   ```

### Rollback Procedure

If you need to rollback to host-level cron:

1. **Stop containerized renewal**:
   ```bash
   docker compose stop ssl-renewer
   docker compose rm -f ssl-renewer
   ```

2. **Restore host cron job**:
   ```bash
   sudo crontab -e
   # Add: 30 3,15 * * * /home/ubuntu/GoogleCalendar_NGINX/scripts/renew-certificate.sh
   ```

## Testing

### Infrastructure Tests

Run the SSL renewer infrastructure tests:

```bash
cd /home/ubuntu/GoogleCalendar_NGINX

# Run all SSL renewer tests
./tests/infrastructure/ssl-renewer/01-container-health.test.sh
./tests/infrastructure/ssl-renewer/02-cron-schedule.test.sh
./tests/infrastructure/ssl-renewer/03-log-rotation.test.sh

# Or run all infrastructure tests
./tests/infrastructure/run-all-tests.sh
```

### Manual Testing

#### Test Renewal Logic

```bash
# Run renewal script manually (won't renew if not needed)
docker compose exec ssl-renewer /scripts/ssl-renewal.sh

# Check logs for output
docker compose exec ssl-renewer tail /var/log/ssl-renewal/renewal.log
```

#### Test NGINX Restart

```bash
# Verify container can restart NGINX
docker compose exec ssl-renewer docker restart nginx-proxy

# Check NGINX status
docker compose ps nginx-proxy
```

#### Test Certificate Expiry Check

```bash
# Check certificate expiry date
docker compose exec ssl-renewer openssl x509 -enddate -noout -in /etc/letsencrypt/live/matrosmcp.duckdns.org/fullchain.pem
```

## Security Considerations

### Container Security

- **No Privileged Mode**: Container runs without privileged access
- **Read-Only Docker Socket**: Docker socket mounted read-only
- **No New Privileges**: `security_opt: no-new-privileges:true`
- **Resource Limits**: CPU and memory limits enforced
- **Minimal Packages**: Alpine base with only required tools

### Certificate Security

- Certificates stored on host at `/etc/letsencrypt`
- Container has read-write access to renew certificates
- Private keys never logged or exposed
- HTTPS tested after renewal to verify functionality

## Maintenance

### Log Cleanup

Logs are stored in Docker volume `ssl-renewal-logs`. To manage:

```bash
# View log size
docker volume inspect ssl-renewal-logs

# Access logs
docker compose exec ssl-renewer ls -lh /var/log/ssl-renewal/

# Clean old logs (if needed)
docker compose exec ssl-renewer sh -c "echo '' > /var/log/ssl-renewal/renewal.log"
```

### Container Updates

To update the ssl-renewer container:

```bash
# Pull latest code
git pull origin main

# Rebuild container
docker compose build ssl-renewer

# Recreate container
docker compose up -d ssl-renewer

# Verify
docker compose logs ssl-renewer
```

## Related Documentation

- [Let's Encrypt Setup Guide](./letsencrypt-setup-guide.md)
- [SSL Implementation Summary](./ssl-implementation-summary.md)
- [Oracle Cloud SSL Setup](./oracle-cloud-ssl-setup.md)
- [Docker Documentation](./docker.md)

## Support

For issues or questions:
- Check logs: `docker compose logs ssl-renewer`
- Review documentation: `docs/` directory
- Check certificate status: `openssl x509 -in /etc/letsencrypt/live/matrosmcp.duckdns.org/fullchain.pem -noout -text`
- Test HTTPS: `curl -I https://matrosmcp.duckdns.org/health`

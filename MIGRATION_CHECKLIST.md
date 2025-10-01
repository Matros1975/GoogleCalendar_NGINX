# Migration Checklist: Multi-MCP Deployment Refactor

This checklist helps you migrate from the old structure to the new multi-MCP `Servers/` directory structure.

## Pre-Migration

- [ ] **Backup current deployment**
  ```bash
  # Backup configuration
  cp docker-compose.yml docker-compose.yml.old
  cp -r nginx nginx.old
  
  # Export current configuration
  docker compose config > config-backup.yml
  
  # Backup environment files
  cp .env.production .env.production.old
  ```

- [ ] **Document current state**
  ```bash
  # Save container status
  docker compose ps > containers-before.txt
  
  # Save running configuration
  docker compose logs > logs-before.txt
  ```

- [ ] **Run pre-migration tests**
  ```bash
  # If you have the test suite, run baseline
  ./tests/infrastructure/run-all-tests.sh --save-results baseline.txt
  ```

## Migration Steps

### 1. Update Repository

- [ ] **Pull latest changes**
  ```bash
  git fetch origin
  git checkout main
  git pull
  ```

- [ ] **Review changes**
  ```bash
  # Check what changed
  git log --oneline -10
  
  # Review refactor documentation
  cat REFACTOR.md
  ```

### 2. Stop Current Deployment

- [ ] **Stop running containers**
  ```bash
  docker compose down
  ```

- [ ] **Keep volumes** (don't use `-v` flag to preserve tokens and data)

### 3. Verify New Configuration

- [ ] **Check docker-compose.yml is valid**
  ```bash
  docker compose config
  ```

- [ ] **Verify file paths exist**
  ```bash
  ls -la Servers/GoogleCalendarMCP/Dockerfile
  ls -la Servers/NGINX/conf.d/mcp-proxy.conf
  ```

- [ ] **Check OAuth credentials are accessible**
  ```bash
  ls -la gcp-oauth.keys.json
  ```

### 4. Update Configuration Files

- [ ] **Update NGINX domain (if needed)**
  ```bash
  # Edit Servers/NGINX/conf.d/mcp-proxy.conf
  # Update server_name to your domain
  ```

- [ ] **Verify SSL certificates location**
  ```bash
  # Certificates should be at:
  # /etc/letsencrypt/live/YOUR_DOMAIN/ (mounted read-only)
  # OR
  # Servers/NGINX/ssl/ (for self-signed)
  ```

- [ ] **Check bearer tokens are configured**
  ```bash
  ls -la nginx/auth/tokens
  # OR
  cat .env.production | grep BEARER_TOKEN
  ```

### 5. Rebuild Containers

- [ ] **Clean build (recommended)**
  ```bash
  docker compose build --no-cache
  ```

  **OR Quick build**
  ```bash
  docker compose build
  ```

### 6. Deploy New Structure

- [ ] **Start containers**
  ```bash
  docker compose up -d
  ```

- [ ] **Watch startup logs**
  ```bash
  docker compose logs -f
  ```

- [ ] **Wait for containers to be healthy**
  ```bash
  # Wait ~60 seconds for health checks
  docker compose ps
  ```

### 7. Verify Deployment

- [ ] **Check container status**
  ```bash
  docker compose ps
  # All containers should be "Up" and "healthy"
  ```

- [ ] **Test health endpoint**
  ```bash
  curl -k https://localhost/health
  # Should return: {"status":"healthy"}
  ```

- [ ] **Test OAuth callback endpoint**
  ```bash
  curl -k https://localhost/oauth/callback
  # Should return 400 or similar (not 502/503)
  ```

- [ ] **Verify NGINX routing**
  ```bash
  # With valid bearer token
  curl -k -H "Authorization: Bearer YOUR_TOKEN" https://localhost/
  ```

### 8. Test Google OAuth

- [ ] **Run OAuth flow (if needed)**
  ```bash
  docker compose exec calendar-mcp npm run auth
  ```

- [ ] **Verify tokens are saved**
  ```bash
  docker compose exec calendar-mcp ls -la /home/nodejs/.config/google-calendar-mcp/
  ```

### 9. Run Post-Migration Tests

- [ ] **Run infrastructure tests**
  ```bash
  ./tests/infrastructure/run-all-tests.sh --save-results post-migration.txt
  ```

- [ ] **Compare with baseline**
  ```bash
  diff baseline.txt post-migration.txt
  ```

- [ ] **Test MCP functionality**
  ```bash
  # Use your MCP client to:
  # - List calendars
  # - List events
  # - Create test event
  # - Delete test event
  ```

### 10. Monitoring

- [ ] **Check logs for errors**
  ```bash
  docker compose logs calendar-mcp | grep -i error
  docker compose logs nginx-proxy | grep -i error
  ```

- [ ] **Monitor resource usage**
  ```bash
  docker stats
  ```

- [ ] **Verify SSL certificate**
  ```bash
  echo | openssl s_client -connect localhost:443 -servername YOUR_DOMAIN 2>/dev/null | grep "Verify return code"
  ```

## Rollback (If Needed)

If something goes wrong, you can rollback:

- [ ] **Stop new deployment**
  ```bash
  docker compose down
  ```

- [ ] **Restore old configuration**
  ```bash
  mv docker-compose.yml.old docker-compose.yml
  mv nginx.old nginx
  ```

- [ ] **Restart with old configuration**
  ```bash
  docker compose up -d
  ```

- [ ] **Report issues**
  - Check logs: `docker compose logs`
  - Review test results
  - Open GitHub issue with details

## Post-Migration Cleanup

Once everything is working:

- [ ] **Remove backup files**
  ```bash
  rm -rf nginx.old docker-compose.yml.old .env.production.old
  rm config-backup.yml containers-before.txt logs-before.txt
  ```

- [ ] **Update documentation**
  - Update any custom documentation
  - Update deployment notes
  - Share migration experience

- [ ] **Schedule certificate renewal** (if using Let's Encrypt)
  ```bash
  # Test renewal
  sudo certbot renew --dry-run
  
  # Setup auto-renewal if not already configured
  ```

## Verification Checklist

After migration, verify these are working:

- [ ] ✅ Containers start successfully
- [ ] ✅ Health endpoints respond
- [ ] ✅ OAuth flow works
- [ ] ✅ Bearer token authentication works
- [ ] ✅ TLS/SSL certificates valid
- [ ] ✅ MCP tools accessible
- [ ] ✅ Calendar operations work
- [ ] ✅ Logs are clean (no critical errors)
- [ ] ✅ Resource usage is normal
- [ ] ✅ Automated tests pass

## Getting Help

If you encounter issues:

1. **Check documentation**
   - `REFACTOR.md` - Migration details
   - `README.md` - Updated architecture
   - `DEPLOYMENT.md` - Deployment guide
   - `Servers/README.md` - Service management

2. **Review logs**
   ```bash
   docker compose logs calendar-mcp
   docker compose logs nginx-proxy
   ```

3. **Run diagnostics**
   ```bash
   ./tests/infrastructure/run-all-tests.sh
   ```

4. **Check common issues**
   - Path mismatches in volume mounts
   - SSL certificate location
   - Bearer token configuration
   - OAuth credentials path

5. **Open GitHub issue**
   - Include migration checklist status
   - Attach relevant logs
   - Describe error messages
   - Include test results

## Success Criteria

Migration is complete when:

✅ All containers are healthy
✅ All infrastructure tests pass
✅ MCP server responds to requests
✅ OAuth authentication works
✅ SSL/TLS is properly configured
✅ No critical errors in logs
✅ Performance is normal or better

**Congratulations!** Your deployment is now using the multi-MCP architecture and you can easily add new MCP servers by following the guide in `Servers/README.md`.

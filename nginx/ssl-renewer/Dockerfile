FROM alpine:latest

# Install required packages
RUN apk add --no-cache \
    certbot \
    docker-cli \
    docker-cli-compose \
    dcron \
    bash \
    curl \
    tzdata \
    openssl

# Create directories
RUN mkdir -p /var/log/ssl-renewal && \
    mkdir -p /scripts && \
    mkdir -p /compose

# Copy scripts
COPY ssl-renewal.sh /scripts/ssl-renewal.sh
COPY ssl-crontab /scripts/ssl-crontab
COPY health-check.sh /scripts/health-check.sh
RUN chmod +x /scripts/ssl-renewal.sh /scripts/health-check.sh

# Install crontab
RUN crontab /scripts/ssl-crontab

# Create startup script
RUN echo '#!/bin/bash' > /start.sh && \
    echo 'echo "Starting SSL Certificate Renewal Service..."' >> /start.sh && \
    echo 'echo "Domain: ${DOMAIN:-matrosmcp.duckdns.org}"' >> /start.sh && \
    echo 'echo "Schedule: Twice daily at 3:30 AM/PM ${TZ:-UTC}"' >> /start.sh && \
    echo 'echo "Log file: /var/log/ssl-renewal/renewal.log"' >> /start.sh && \
    echo 'echo ""' >> /start.sh && \
    echo '# Test certbot and docker availability' >> /start.sh && \
    echo 'if ! command -v certbot &> /dev/null; then' >> /start.sh && \
    echo '    echo "ERROR: certbot not found!"' >> /start.sh && \
    echo '    exit 1' >> /start.sh && \
    echo 'fi' >> /start.sh && \
    echo 'if ! command -v docker &> /dev/null; then' >> /start.sh && \
    echo '    echo "ERROR: docker not found!"' >> /start.sh && \
    echo '    exit 1' >> /start.sh && \
    echo 'fi' >> /start.sh && \
    echo 'echo "✓ certbot version: $(certbot --version 2>&1 | head -1)"' >> /start.sh && \
    echo 'echo "✓ docker version: $(docker --version)"' >> /start.sh && \
    echo 'echo ""' >> /start.sh && \
    echo 'echo "Starting cron daemon..."' >> /start.sh && \
    echo '# Start cron daemon in foreground' >> /start.sh && \
    echo 'crond -f -d 8' >> /start.sh && \
    chmod +x /start.sh

# Set timezone
ENV TZ=UTC
ENV DOMAIN=matrosmcp.duckdns.org
ENV COMPOSE_PROJECT_PATH=/compose

HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
    CMD /scripts/health-check.sh

CMD ["/start.sh"]

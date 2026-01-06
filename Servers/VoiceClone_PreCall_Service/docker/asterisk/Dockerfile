FROM alpine:3.19

# Install Asterisk from Alpine repos (much simpler)
RUN apk add --no-cache \
    asterisk \
    asterisk-sounds-en \
    asterisk-sounds-moh \
    curl

# Create directories for configurations
RUN mkdir -p /etc/asterisk /var/lib/asterisk /var/log/asterisk /var/spool/asterisk

# Expose ports
# 5060 UDP - SIP
# 5038 TCP - AMI (Asterisk Manager Interface)
# 8088 TCP - ARI HTTP/WebSocket
# 16384-32768 UDP - RTP media
EXPOSE 5060/udp 5038/tcp 8088/tcp 16384-32768/udp

# Configuration files will be mounted as volumes from host
# See docker-compose.yml for volume mounts

# Start Asterisk in foreground
CMD ["asterisk", "-cvvvf"]

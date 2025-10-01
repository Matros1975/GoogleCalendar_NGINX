# SSL Certificate Setup for NGINX

This directory should contain your SSL certificates:

1. cert.pem - Your SSL certificate
2. key.pem - Your SSL private key

## Option 1: Let's Encrypt (Recommended)
```bash
# Install certbot on your Oracle VM
sudo yum install certbot python3-certbot-nginx

# Get certificates
sudo certbot certonly --standalone -d your-domain.com

# Copy certificates to this directory
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./key.pem
sudo chown $USER:$USER *.pem
```

## Option 2: Self-Signed Certificates (Development/Testing)
```bash
# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout key.pem \
    -out cert.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/OU=OrgUnit/CN=your-domain.com"
```

## Option 3: Commercial Certificate
- Upload your certificate files as cert.pem and key.pem
- Ensure proper file permissions (readable by nginx user)

## File Permissions
```bash
chmod 644 cert.pem
chmod 600 key.pem
```
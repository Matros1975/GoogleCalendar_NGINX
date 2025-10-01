#!/bin/bash
# Oracle VM Deployment Setup Script
# Run this script on your Oracle VM to set up the secure MCP deployment

set -e

echo "🚀 Setting up Google Calendar MCP with NGINX proxy on Oracle VM..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root for security reasons"
   exit 1
fi

print_status "Checking prerequisites..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    print_status "Run: curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if user is in docker group
if ! groups | grep -q docker; then
    print_warning "User is not in docker group. Adding user to docker group..."
    sudo usermod -aG docker $USER
    print_warning "Please log out and log back in for group changes to take effect"
    print_warning "Then run this script again"
    exit 1
fi

print_status "Prerequisites check passed ✓"

# Create necessary directories
print_status "Creating directory structure..."
mkdir -p Servers/NGINX/ssl nginx/auth logs

# Check if OAuth credentials exist
if [[ ! -f "gcp-oauth.keys.json" ]]; then
    print_error "Google OAuth credentials file 'gcp-oauth.keys.json' not found!"
    print_status "Please copy your Google OAuth credentials to this directory:"
    print_status "cp /path/to/your/gcp-oauth.keys.json ./gcp-oauth.keys.json"
    exit 1
fi

print_status "Google OAuth credentials found ✓"

# Generate bearer tokens if not configured
if [[ ! -f ".env.production" ]]; then
    print_status "Creating production environment configuration..."
    cp .env.production.example .env.production
    
    # Generate secure bearer tokens
    TOKEN1=$(openssl rand -hex 32)
    TOKEN2=$(openssl rand -hex 32)
    
    sed -i.bak "s/your-secure-token-1/$TOKEN1/" .env.production
    sed -i.bak "s/your-secure-token-2/$TOKEN2/" .env.production
    rm .env.production.bak
    
    print_status "Generated secure bearer tokens and saved to .env.production"
    print_warning "IMPORTANT: Save these bearer tokens securely for API access:"
    echo -e "${YELLOW}Token 1: $TOKEN1${NC}"
    echo -e "${YELLOW}Token 2: $TOKEN2${NC}"
else
    print_status "Production environment configuration exists ✓"
fi

# Setup SSL certificates
print_status "Setting up SSL certificates..."
if [[ ! -f "Servers/NGINX/ssl/cert.pem" || ! -f "Servers/NGINX/ssl/key.pem" ]]; then
    print_warning "SSL certificates not found. You have several options:"
    echo "1. Use Let's Encrypt (recommended for production)"
    echo "2. Generate self-signed certificates (development/testing)"
    echo "3. Upload your own certificates"
    echo ""
    read -p "Choose option (1/2/3): " ssl_option
    
    case $ssl_option in
        1)
            print_status "Setting up Let's Encrypt..."
            read -p "Enter your domain name: " domain_name
            
            # Update nginx config with domain
            sed -i.bak "s/your-domain.com/$domain_name/" Servers/NGINX/conf.d/mcp-proxy.conf
            rm Servers/NGINX/conf.d/mcp-proxy.conf.bak
            
            print_status "Please run these commands to get Let's Encrypt certificates:"
            echo "sudo yum install certbot -y"
            echo "sudo certbot certonly --standalone -d $domain_name"
            echo "sudo cp /etc/letsencrypt/live/$domain_name/fullchain.pem Servers/NGINX/ssl/cert.pem"
            echo "sudo cp /etc/letsencrypt/live/$domain_name/privkey.pem Servers/NGINX/ssl/key.pem"
            echo "sudo chown \$USER:\$USER Servers/NGINX/ssl/*.pem"
            echo ""
            print_warning "Run the above commands, then re-run this script"
            exit 0
            ;;
        2)
            print_status "Generating self-signed certificates..."
            read -p "Enter domain name (or localhost): " domain_name
            
            openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                -keyout Servers/NGINX/ssl/key.pem \
                -out Servers/NGINX/ssl/cert.pem \
                -subj "/C=US/ST=State/L=City/O=MCP/OU=Calendar/CN=$domain_name"
            
            chmod 644 Servers/NGINX/ssl/cert.pem
            chmod 600 Servers/NGINX/ssl/key.pem
            
            # Update nginx config with domain
            sed -i.bak "s/your-domain.com/$domain_name/" Servers/NGINX/conf.d/mcp-proxy.conf
            rm Servers/NGINX/conf.d/mcp-proxy.conf.bak
            
            print_status "Self-signed certificates generated ✓"
            ;;
        3)
            print_status "Please copy your SSL certificates to:"
            print_status "  - Servers/NGINX/ssl/cert.pem (certificate)"
            print_status "  - Servers/NGINX/ssl/key.pem (private key)"
            print_status "Then re-run this script"
            exit 0
            ;;
        *)
            print_error "Invalid option"
            exit 1
            ;;
    esac
else
    print_status "SSL certificates found ✓"
fi

# Build and start services
print_status "Building and starting services..."
docker compose build

print_status "Starting services..."
docker compose up -d

# Wait for services to be ready
print_status "Waiting for services to start..."
sleep 10

# Authenticate with Google
print_status "Setting up Google OAuth authentication..."
print_warning "This will open a browser window for OAuth authentication"
docker compose exec calendar-mcp npm run auth

# Test the setup
print_status "Testing the deployment..."
if curl -k -f https://localhost/health > /dev/null 2>&1; then
    print_status "Health check passed ✓"
else
    print_warning "Health check failed - services may still be starting"
fi

print_status "✅ Deployment setup complete!"
echo ""
print_status "Next steps:"
echo "1. Configure your domain DNS to point to this server"
echo "2. Update firewall rules to allow ports 80 and 443"
echo "3. Test API access with bearer tokens"
echo ""
print_status "API Usage:"
echo "Base URL: https://your-domain.com"
echo "Health Check: curl https://your-domain.com/health"
echo "Authenticated Request: curl -H 'Authorization: Bearer YOUR_TOKEN' https://your-domain.com/endpoint"
echo ""
print_status "Bearer tokens are saved in .env.production file"
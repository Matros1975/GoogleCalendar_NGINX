#!/bin/bash
# Bearer Token Management Script
# Use this script to manage API access tokens

set -e

# Configuration
ENV_FILE=""

# Try to find .env.production in multiple locations
if [[ -f "Servers/GoogleCalendarMCP/.env.production" ]]; then
    ENV_FILE="Servers/GoogleCalendarMCP/.env.production"
elif [[ -f ".env.production" ]]; then
    ENV_FILE=".env.production"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Function to generate a secure token
generate_token() {
    openssl rand -hex 32
}

# Function to display current tokens
show_tokens() {
    print_header "Current Bearer Tokens"
    if [[ -n "$ENV_FILE" && -f "$ENV_FILE" ]]; then
        tokens=$(grep "BEARER_TOKENS=" "$ENV_FILE" | cut -d'=' -f2)
        if [[ -n "$tokens" ]]; then
            IFS=',' read -ra TOKEN_ARRAY <<< "$tokens"
            for i in "${!TOKEN_ARRAY[@]}"; do
                echo -e "${YELLOW}Token $((i+1)):${NC} ${TOKEN_ARRAY[i]}"
            done
        else
            print_warning "No bearer tokens configured"
        fi
    else
        print_error ".env.production file not found"
        print_status "Expected locations:"
        print_status "  - Servers/GoogleCalendarMCP/.env.production"
        print_status "  - .env.production"
    fi
}

# Function to add a new token
add_token() {
    local new_token
    if [[ -n "$1" ]]; then
        new_token="$1"
    else
        new_token=$(generate_token)
        print_status "Generated new token: $new_token"
    fi
    
    if [[ -n "$ENV_FILE" && -f "$ENV_FILE" ]]; then
        current_tokens=$(grep "BEARER_TOKENS=" "$ENV_FILE" | cut -d'=' -f2)
        if [[ -n "$current_tokens" ]]; then
            updated_tokens="$current_tokens,$new_token"
        else
            updated_tokens="$new_token"
        fi
        
        # Update the file
        sed -i.bak "s/BEARER_TOKENS=.*/BEARER_TOKENS=$updated_tokens/" "$ENV_FILE"
        rm "$ENV_FILE.bak"
        
        print_status "Token added successfully"
        print_warning "Restart the service to apply changes:"
        echo "docker compose restart"
    else
        print_error ".env.production file not found"
        exit 1
    fi
}

# Function to remove a token
remove_token() {
    local token_to_remove="$1"
    
    if [[ -z "$token_to_remove" ]]; then
        print_error "Token to remove not specified"
        exit 1
    fi
    
    if [[ -n "$ENV_FILE" && -f "$ENV_FILE" ]]; then
        current_tokens=$(grep "BEARER_TOKENS=" "$ENV_FILE" | cut -d'=' -f2)
        
        # Remove the token from the comma-separated list
        updated_tokens=$(echo "$current_tokens" | sed "s/$token_to_remove,\?//g" | sed 's/,$//g' | sed 's/^,//g')
        
        # Update the file
        sed -i.bak "s/BEARER_TOKENS=.*/BEARER_TOKENS=$updated_tokens/" "$ENV_FILE"
        rm "$ENV_FILE.bak"
        
        print_status "Token removed successfully"
        print_warning "Restart the service to apply changes:"
        echo "docker compose restart"
    else
        print_error ".env.production file not found"
        exit 1
    fi
}

# Function to test a token
test_token() {
    local token="$1"
    local endpoint="${2:-https://localhost/health}"
    
    if [[ -z "$token" ]]; then
        print_error "Token not specified"
        exit 1
    fi
    
    print_status "Testing token against $endpoint..."
    
    response=$(curl -k -s -w "%{http_code}" -H "Authorization: Bearer $token" "$endpoint" -o /tmp/token_test_response)
    http_code="${response: -3}"
    
    if [[ "$http_code" == "200" ]]; then
        print_status "✅ Token is valid"
        if [[ "$endpoint" == *"/health"* ]]; then
            echo "Response:"
            cat /tmp/token_test_response | jq . 2>/dev/null || cat /tmp/token_test_response
        fi
    elif [[ "$http_code" == "401" ]]; then
        print_error "❌ Token is invalid or expired"
    elif [[ "$http_code" == "403" ]]; then
        print_error "❌ Token is valid but access is forbidden"
    else
        print_warning "⚠️  Unexpected response: HTTP $http_code"
        cat /tmp/token_test_response
    fi
    
    rm -f /tmp/token_test_response
}

# Function to rotate all tokens
rotate_tokens() {
    print_header "Token Rotation"
    print_warning "This will generate new tokens and invalidate all existing ones"
    read -p "Are you sure? (y/N): " confirm
    
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        new_token1=$(generate_token)
        new_token2=$(generate_token)
        new_tokens="$new_token1,$new_token2"
        
        # Update the file
        if [[ -n "$ENV_FILE" && -f "$ENV_FILE" ]]; then
            sed -i.bak "s/BEARER_TOKENS=.*/BEARER_TOKENS=$new_tokens/" "$ENV_FILE"
            rm "$ENV_FILE.bak"
            
            print_status "Tokens rotated successfully"
            echo -e "${YELLOW}New Token 1:${NC} $new_token1"
            echo -e "${YELLOW}New Token 2:${NC} $new_token2"
            print_warning "Save these tokens securely!"
            print_warning "Restart the service to apply changes:"
            echo "docker compose restart"
        else
            print_error ".env.production file not found"
            exit 1
        fi
    else
        print_status "Token rotation cancelled"
    fi
}

# Main script
case "${1:-help}" in
    "show"|"list")
        show_tokens
        ;;
    "add")
        add_token "$2"
        ;;
    "remove")
        if [[ -z "$2" ]]; then
            print_error "Usage: $0 remove <token>"
            exit 1
        fi
        remove_token "$2"
        ;;
    "test")
        if [[ -z "$2" ]]; then
            print_error "Usage: $0 test <token> [endpoint]"
            exit 1
        fi
        test_token "$2" "$3"
        ;;
    "rotate")
        rotate_tokens
        ;;
    "generate")
        new_token=$(generate_token)
        print_status "Generated token: $new_token"
        echo "Use './manage-tokens.sh add $new_token' to add it to the configuration"
        ;;
    "help"|*)
        print_header "Bearer Token Management"
        echo "Usage: $0 <command> [arguments]"
        echo ""
        echo "Commands:"
        echo "  show              Display current tokens"
        echo "  add [token]       Add a new token (generates one if not provided)"
        echo "  remove <token>    Remove a specific token"
        echo "  test <token> [url] Test a token against an endpoint"
        echo "  rotate            Generate new tokens and invalidate old ones"
        echo "  generate          Generate a new token (doesn't add it)"
        echo "  help              Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 show"
        echo "  $0 add"
        echo "  $0 test abc123 https://your-domain.com/health"
        echo "  $0 remove abc123"
        echo "  $0 rotate"
        ;;
esac
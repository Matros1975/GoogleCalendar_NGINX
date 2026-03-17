# Stop all running elevenlabs-webhook containers
docker ps -q --filter ancestor=elevenlabs-webhook | ForEach-Object { docker stop $_ }

# Rebuild
docker build -t elevenlabs-webhook .

# Start fresh
docker run -d -p 3004:3004 --env-file .env elevenlabs-webhook

# Show new container ID
docker ps --filter ancestor=elevenlabs-webhook
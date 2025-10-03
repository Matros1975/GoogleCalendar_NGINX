#!/usr/bin/env node

/**
 * Standalone Authentication Server for Gmail MCP
 * 
 * This script starts a local authentication server to handle the OAuth2 flow
 * for Gmail API access. It can be run independently from the main MCP server.
 * 
 * Usage:
 *   node build/auth-server.js
 *   npm run auth
 */

import { initializeOAuth2Client } from './auth/client.js';
import { AuthServer } from './auth/server.js';

async function main() {
  try {
    process.stderr.write('Starting Gmail authentication server...\n');
    
    // Initialize OAuth client
    const oauth2Client = await initializeOAuth2Client();

    // Create and start the auth server
    const authServer = new AuthServer(oauth2Client);

    // Start with browser opening (true by default)
    const success = await authServer.start(true);

    if (!success && !authServer.authCompletedSuccessfully) {
      // Failed to start and tokens weren't already valid
      process.stderr.write(
        'Authentication failed. Could not start server or validate existing tokens.\n' +
        'Check port availability (3500-3505) and try again.\n'
      );
      process.exit(1);
    } else if (authServer.authCompletedSuccessfully) {
      // Auth was successful (either existing tokens were valid or flow completed just now)
      process.stderr.write('Authentication successful.\n');
      
      // Stop the server and exit cleanly
      await authServer.stop();
      process.exit(0);
    }

    // Keep the server running and wait for authentication
    process.stderr.write('Waiting for authentication to complete...\n');
    
    // Handle graceful shutdown
    const shutdown = async () => {
      process.stderr.write('\nShutting down authentication server...\n');
      await authServer.stop();
      process.exit(0);
    };

    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);

  } catch (error: unknown) {
    process.stderr.write(`Authentication server error: ${error instanceof Error ? error.message : error}\n`);
    process.exit(1);
  }
}

main();

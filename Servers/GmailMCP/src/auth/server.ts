import { OAuth2Client } from 'google-auth-library';
import { TokenManager } from './tokenManager.js';
import http from 'http';
import { URL } from 'url';
import open from 'open';
import { initializeOAuth2Client } from './client.js';

export class AuthServer {
  private baseOAuth2Client: OAuth2Client; // Used by TokenManager for validation/refresh
  private flowOAuth2Client: OAuth2Client | null = null; // Used specifically for the auth code flow
  private server: http.Server | null = null;
  private tokenManager: TokenManager;
  private portRange: { start: number; end: number };
  private activeConnections: Set<import('net').Socket> = new Set(); // Track active socket connections
  public authCompletedSuccessfully = false; // Flag for standalone script

  constructor(oauth2Client: OAuth2Client) {
    this.baseOAuth2Client = oauth2Client;
    this.tokenManager = new TokenManager(oauth2Client);
    this.portRange = { start: 3500, end: 3505 };
  }

  private createServer(): http.Server {
    const server = http.createServer(async (req, res) => {
      const url = new URL(req.url || '/', `http://${req.headers.host}`);
      
      if (url.pathname === '/') {
        // Root route - show auth link
        const clientForUrl = this.flowOAuth2Client || this.baseOAuth2Client;
        const scopes = [
          'https://www.googleapis.com/auth/gmail.modify',
          'https://www.googleapis.com/auth/gmail.settings.basic'
        ];
        const authUrl = clientForUrl.generateAuthUrl({
          access_type: 'offline',
          scope: scopes,
          prompt: 'consent'
        });
        
        const accountMode = this.tokenManager.getAccountMode();
        
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(`
          <h1>Gmail Authentication</h1>
          <p><strong>Account Mode:</strong> <code>${accountMode}</code></p>
          <p>You are authenticating for the <strong>${accountMode}</strong> account.</p>
          <a href="${authUrl}">Authenticate with Google</a>
        `);
        
      } else if (url.pathname === '/oauth2callback') {
        // OAuth callback route
        const code = url.searchParams.get('code');
        if (!code) {
          res.writeHead(400, { 'Content-Type': 'text/plain' });
          res.end('Authorization code missing');
          return;
        }
        
        if (!this.flowOAuth2Client) {
          res.writeHead(500, { 'Content-Type': 'text/plain' });
          res.end('Authentication flow not properly initiated.');
          return;
        }
        
        try {
          const { tokens } = await this.flowOAuth2Client.getToken(code);
          await this.tokenManager.saveTokens(tokens);
          this.authCompletedSuccessfully = true;

          const tokenPath = this.tokenManager.getTokenPath();
          const accountMode = this.tokenManager.getAccountMode();
          
          res.writeHead(200, { 'Content-Type': 'text/html' });
          res.end(`
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Authentication Successful</title>
                <style>
                    body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #f4f4f4; margin: 0; }
                    .container { text-align: center; padding: 2em; background-color: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                    h1 { color: #4CAF50; }
                    p { color: #333; margin-bottom: 0.5em; }
                    code { background-color: #eee; padding: 0.2em 0.4em; border-radius: 3px; font-size: 0.9em; }
                    .account-mode { background-color: #e3f2fd; padding: 1em; border-radius: 5px; margin: 1em 0; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Gmail Authentication Successful!</h1>
                    <div class="account-mode">
                        <p><strong>Account Mode:</strong> <code>${accountMode}</code></p>
                        <p>Your authentication tokens have been saved for the <strong>${accountMode}</strong> account.</p>
                    </div>
                    <p>Tokens saved to:</p>
                    <p><code>${tokenPath}</code></p>
                    <p>You can now close this browser window.</p>
                </div>
            </body>
            </html>
          `);
        } catch (error: unknown) {
          this.authCompletedSuccessfully = false;
          const message = error instanceof Error ? error.message : 'Unknown error';
          process.stderr.write(`✗ Gmail: Token save failed: ${message}\n`);

          res.writeHead(500, { 'Content-Type': 'text/html' });
          res.end(`
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Authentication Failed</title>
                <style>
                    body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #f4f4f4; margin: 0; }
                    .container { text-align: center; padding: 2em; background-color: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                    h1 { color: #F44336; }
                    p { color: #333; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Gmail Authentication Failed</h1>
                    <p>An error occurred during authentication:</p>
                    <p><code>${message}</code></p>
                    <p>Please try again or check the server logs.</p>
                </div>
            </body>
            </html>
          `);
        }
      } else {
        // 404 for other routes
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('Not Found');
      }
    });

    // Track connections at server level
    server.on('connection', (socket) => {
      this.activeConnections.add(socket);
      socket.on('close', () => {
        this.activeConnections.delete(socket);
      });
    });
    
    return server;
  }

  private async tryPort(port: number, credentials: any): Promise<boolean> {
    return new Promise((resolve) => {
      const server = this.createServer();
      this.server = server;

      // Reconfigure OAuth2Client with this port's redirect URI
      this.flowOAuth2Client = new OAuth2Client({
        clientId: credentials.client_id,
        clientSecret: credentials.client_secret,
        redirectUri: `http://localhost:${port}/oauth2callback`,
      });

      server.listen(port, async () => {
        process.stderr.write(`Gmail authentication server running at http://localhost:${port}\n`);
        resolve(true);
      });

      server.on('error', () => {
        server.close();
        this.server = null;
        this.flowOAuth2Client = null;
        resolve(false);
      });
    });
  }

  async start(openBrowser = true): Promise<boolean> {
    // First check if tokens are already valid
    const tokensLoaded = await this.tokenManager.loadSavedTokens();
    if (tokensLoaded) {
      const valid = await this.tokenManager.validateTokens();
      if (valid) {
        process.stderr.write('Gmail: Valid tokens already exist. Authentication not needed.\n');
        this.authCompletedSuccessfully = true;
        return true;
      }
    }

    // Load credentials to get client_id and client_secret for the flow
    const credentials = await initializeOAuth2Client();
    const credentialsData = {
      client_id: (credentials as any)._clientId,
      client_secret: (credentials as any)._clientSecret,
    };

    // Try to start server on available port
    for (let port = this.portRange.start; port <= this.portRange.end; port++) {
      const success = await this.tryPort(port, credentialsData);
      if (success && this.server) {
        if (openBrowser) {
          try {
            await open(`http://localhost:${port}`);
          } catch (error) {
            process.stderr.write(`Gmail: Could not open browser. Please visit http://localhost:${port} manually.\n`);
          }
        }
        return true;
      }
    }

    return false;
  }

  async stop(): Promise<void> {
    return new Promise((resolve) => {
      if (!this.server) {
        resolve();
        return;
      }

      // Force close all active connections
      this.activeConnections.forEach((socket) => {
        socket.destroy();
      });
      this.activeConnections.clear();

      this.server.close(() => {
        this.server = null;
        this.flowOAuth2Client = null;
        resolve();
      });

      // Fallback timeout if close doesn't complete
      setTimeout(() => {
        if (this.server) {
          this.server = null;
          this.flowOAuth2Client = null;
        }
        resolve();
      }, 1000);
    });
  }
}

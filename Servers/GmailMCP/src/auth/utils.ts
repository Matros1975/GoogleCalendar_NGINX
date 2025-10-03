import * as fs from 'fs/promises';
import * as path from 'path';
import * as os from 'os';

export interface OAuthCredentials {
  client_id: string;
  client_secret: string;
  redirect_uris: string[];
}

const CONFIG_DIR = path.join(os.homedir(), '.config', 'gmail-mcp');
const DEFAULT_KEYS_FILENAME = 'gcp-oauth.keys.json';

export function getKeysFilePath(): string {
  // Check environment variable first
  if (process.env.GMAIL_OAUTH_CREDENTIALS) {
    return process.env.GMAIL_OAUTH_CREDENTIALS;
  }

  // Check for GOOGLE_OAUTH_CREDENTIALS as fallback (shared with Calendar MCP)
  if (process.env.GOOGLE_OAUTH_CREDENTIALS) {
    return process.env.GOOGLE_OAUTH_CREDENTIALS;
  }

  // Check current directory
  const cwdPath = path.join(process.cwd(), DEFAULT_KEYS_FILENAME);
  try {
    if (require('fs').existsSync(cwdPath)) {
      return cwdPath;
    }
  } catch (e) {
    // Ignore and continue
  }

  // Default to config directory
  return path.join(CONFIG_DIR, DEFAULT_KEYS_FILENAME);
}

export function getTokensFilePath(): string {
  return path.join(CONFIG_DIR, 'tokens.json');
}

export async function ensureConfigDir(): Promise<void> {
  try {
    await fs.mkdir(CONFIG_DIR, { recursive: true });
  } catch (error) {
    // Directory might already exist, which is fine
  }
}

export function generateCredentialsErrorMessage(): string {
  const keysPath = getKeysFilePath();
  return `
Gmail OAuth credentials not found.

Please follow these steps:

1. Go to Google Cloud Console (https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Enable the Gmail API
4. Create OAuth 2.0 credentials (Desktop app type)
5. Download the credentials JSON file
6. Save it as one of the following:
   - ${keysPath}
   - ./gcp-oauth.keys.json (in current directory)
   - Set GMAIL_OAUTH_CREDENTIALS environment variable to the file path

Required scopes:
- https://www.googleapis.com/auth/gmail.modify
- https://www.googleapis.com/auth/gmail.settings.basic

For detailed setup instructions, see: docs/authentication.md
  `.trim();
}

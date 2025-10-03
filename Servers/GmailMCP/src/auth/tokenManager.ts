import { OAuth2Client, Credentials } from 'google-auth-library';
import fs from 'fs/promises';
import { getTokensFilePath, ensureConfigDir } from './utils.js';
import { GaxiosError } from 'gaxios';

// Interface for multi-account token storage
interface MultiAccountTokens {
  normal?: Credentials;
  test?: Credentials;
}

export class TokenManager {
  private oauth2Client: OAuth2Client;
  private tokenPath: string;
  private accountMode: 'normal' | 'test';

  constructor(oauth2Client: OAuth2Client) {
    this.oauth2Client = oauth2Client;
    this.tokenPath = getTokensFilePath();
    this.accountMode = (process.env.GOOGLE_ACCOUNT_MODE as 'normal' | 'test') || 'normal';
    this.setupTokenRefresh();
  }

  // Method to expose the token path
  public getTokenPath(): string {
    return this.tokenPath;
  }

  // Method to get current account mode
  public getAccountMode(): 'normal' | 'test' {
    return this.accountMode;
  }

  // Method to switch account mode (useful for testing)
  public setAccountMode(mode: 'normal' | 'test'): void {
    this.accountMode = mode;
  }

  private async loadMultiAccountTokens(): Promise<MultiAccountTokens> {
    try {
      const fileContent = await fs.readFile(this.tokenPath, "utf-8");
      const parsed = JSON.parse(fileContent);
      
      // Check if this is the old single-account format
      if (parsed.access_token || parsed.refresh_token) {
        // Convert old format to new multi-account format
        const multiAccountTokens: MultiAccountTokens = {
          normal: parsed
        };
        await this.saveMultiAccountTokens(multiAccountTokens);
        return multiAccountTokens;
      }
      
      // Already in multi-account format
      return parsed as MultiAccountTokens;
    } catch (error: unknown) {
      if (error instanceof Error && 'code' in error && error.code === 'ENOENT') {
        // File doesn't exist, return empty structure
        return {};
      }
      throw error;
    }
  }

  private async saveMultiAccountTokens(multiAccountTokens: MultiAccountTokens): Promise<void> {
    await ensureConfigDir();
    await fs.writeFile(this.tokenPath, JSON.stringify(multiAccountTokens, null, 2), {
      mode: 0o600,
    });
  }

  private setupTokenRefresh(): void {
    this.oauth2Client.on("tokens", async (newTokens) => {
      try {
        const multiAccountTokens = await this.loadMultiAccountTokens();
        const currentTokens = multiAccountTokens[this.accountMode] || {};
        
        const updatedTokens = {
          ...currentTokens,
          ...newTokens,
          refresh_token: newTokens.refresh_token || currentTokens.refresh_token,
        };
        
        multiAccountTokens[this.accountMode] = updatedTokens;
        await this.saveMultiAccountTokens(multiAccountTokens);
        
        if (process.env.NODE_ENV !== 'test') {
          process.stderr.write(`Gmail: Tokens updated and saved for ${this.accountMode} account\n`);
        }
      } catch (error: unknown) {
        process.stderr.write(`Gmail: Failed to save updated tokens: ${error instanceof Error ? error.message : error}\n`);
      }
    });
  }

  async loadSavedTokens(): Promise<boolean> {
    try {
      const multiAccountTokens = await this.loadMultiAccountTokens();
      const tokens = multiAccountTokens[this.accountMode];
      
      if (!tokens) {
        return false;
      }

      this.oauth2Client.setCredentials(tokens);
      return true;
    } catch (error: unknown) {
      return false;
    }
  }

  async saveTokens(tokens: Credentials): Promise<void> {
    const multiAccountTokens = await this.loadMultiAccountTokens();
    multiAccountTokens[this.accountMode] = tokens;
    await this.saveMultiAccountTokens(multiAccountTokens);
  }

  async validateTokens(): Promise<boolean> {
    try {
      const credentials = this.oauth2Client.credentials;
      if (!credentials || !credentials.refresh_token) {
        return false;
      }

      // Try to refresh the token to validate it
      const response = await this.oauth2Client.refreshAccessToken();
      if (response.credentials) {
        this.oauth2Client.setCredentials(response.credentials);
        return true;
      }
      return false;
    } catch (error: unknown) {
      if (error && typeof error === 'object' && 'code' in error) {
        const gaxiosError = error as GaxiosError;
        if (gaxiosError.code === '400' || gaxiosError.code === '401') {
          return false;
        }
      }
      // For other errors, log but don't consider them as validation failures
      process.stderr.write(`Gmail: Token validation error: ${error instanceof Error ? error.message : error}\n`);
      return false;
    }
  }

  async clearTokens(): Promise<void> {
    try {
      const multiAccountTokens = await this.loadMultiAccountTokens();
      delete multiAccountTokens[this.accountMode];
      await this.saveMultiAccountTokens(multiAccountTokens);
      this.oauth2Client.setCredentials({});
    } catch (error) {
      process.stderr.write(`Gmail: Failed to clear tokens: ${error instanceof Error ? error.message : error}\n`);
    }
  }
}

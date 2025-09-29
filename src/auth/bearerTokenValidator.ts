export interface BearerTokenConfig {
  tokens: string[];
}

export class BearerTokenValidator {
  private validTokens: Set<string>;

  constructor(config: BearerTokenConfig) {
    this.validTokens = new Set(config.tokens);
  }

  /**
   * Validate a bearer token
   */
  validateToken(token: string): boolean {
    if (!token) return false;
    
    // Remove 'Bearer ' prefix if present
    const cleanToken = token.replace(/^Bearer\s+/i, '');
    
    return this.validTokens.has(cleanToken);
  }

  /**
   * Add a new token at runtime
   */
  addToken(token: string): void {
    this.validTokens.add(token);
  }

  /**
   * Remove a token at runtime
   */
  removeToken(token: string): void {
    this.validTokens.delete(token);
  }
}
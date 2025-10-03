import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { google, gmail_v1 } from 'googleapis';
import { z } from "zod";
import { zodToJsonSchema } from "zod-to-json-schema";
import { OAuth2Client } from 'google-auth-library';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

// Import auth components
import { initializeOAuth2Client } from './auth/client.js';
import { AuthServer } from './auth/server.js';
import { TokenManager } from './auth/tokenManager.js';

// Import utilities
import { createEmailMessage } from './utils/email.js';
import { listLabels, findLabelByName } from './services/labelManager.js';

// Get directory name for ESM
const __dirname = dirname(fileURLToPath(import.meta.url));

// OAuth2 configuration
let oauth2Client: OAuth2Client;
let tokenManager: TokenManager;

/**
 * Schema definitions for Gmail tools
 */
const SendEmailSchema = z.object({
  to: z.array(z.string()).describe("List of recipient email addresses"),
  subject: z.string().describe("Email subject"),
  body: z.string().describe("Email body content (used for text/plain or when htmlBody not provided)"),
  htmlBody: z.string().optional().describe("HTML version of the email body"),
  mimeType: z.enum(['text/plain', 'text/html', 'multipart/alternative']).optional().default('text/plain').describe("Email content type"),
  cc: z.array(z.string()).optional().describe("List of CC recipients"),
  bcc: z.array(z.string()).optional().describe("List of BCC recipients"),
  inReplyTo: z.string().optional().describe("Message-ID of the message to reply to"),
});

const ListEmailsSchema = z.object({
  maxResults: z.number().optional().default(10).describe("Maximum number of emails to return (default: 10, max: 100)"),
  query: z.string().optional().describe("Gmail search query (e.g., 'is:unread', 'from:example@gmail.com')"),
  labelIds: z.array(z.string()).optional().describe("Filter by label IDs (e.g., ['INBOX', 'UNREAD'])"),
});

const GetEmailSchema = z.object({
  messageId: z.string().describe("ID of the email message to retrieve"),
  format: z.enum(['minimal', 'full', 'raw', 'metadata']).optional().default('full').describe("Format of the email to return"),
});

const ListLabelsSchema = z.object({});

/**
 * Main application logic
 */
async function main() {
  // Check if running auth command
  if (process.argv[2] === 'auth') {
    await runAuthServer();
    return;
  }

  // Initialize OAuth2 client
  oauth2Client = await initializeOAuth2Client();
  tokenManager = new TokenManager(oauth2Client);

  // Load saved tokens
  const tokensLoaded = await tokenManager.loadSavedTokens();
  if (!tokensLoaded) {
    process.stderr.write('No authentication tokens found. Please run: npm run auth\n');
    process.exit(1);
  }

  // Validate tokens
  const valid = await tokenManager.validateTokens();
  if (!valid) {
    process.stderr.write('Invalid or expired tokens. Please run: npm run auth\n');
    process.exit(1);
  }

  // Initialize Gmail API
  const gmail = google.gmail({ version: 'v1', auth: oauth2Client });

  // Create MCP Server
  const server = new Server({
    name: "gmail",
    version: "1.0.0",
  }, {
    capabilities: {
      tools: {},
    },
  });

  // Register tools
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
      tools: [
        {
          name: "send_email",
          description: "Send an email via Gmail. Supports plain text and HTML content.",
          inputSchema: zodToJsonSchema(SendEmailSchema),
        },
        {
          name: "list_emails",
          description: "List emails from Gmail inbox with optional filtering",
          inputSchema: zodToJsonSchema(ListEmailsSchema),
        },
        {
          name: "get_email",
          description: "Get a specific email by ID with full content",
          inputSchema: zodToJsonSchema(GetEmailSchema),
        },
        {
          name: "list_labels",
          description: "List all Gmail labels (system and user-created)",
          inputSchema: zodToJsonSchema(ListLabelsSchema),
        },
      ],
    };
  });

  // Handle tool calls
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    try {
      switch (name) {
        case "send_email": {
          const validatedArgs = SendEmailSchema.parse(args);
          const emailMessage = createEmailMessage(validatedArgs);
          const encodedMessage = Buffer.from(emailMessage)
            .toString('base64')
            .replace(/\+/g, '-')
            .replace(/\//g, '_')
            .replace(/=+$/, '');

          const response = await gmail.users.messages.send({
            userId: 'me',
            requestBody: {
              raw: encodedMessage,
            },
          });

          return {
            content: [
              {
                type: "text",
                text: `Email sent successfully!\nMessage ID: ${response.data.id}\nThread ID: ${response.data.threadId}`,
              },
            ],
          };
        }

        case "list_emails": {
          const validatedArgs = ListEmailsSchema.parse(args);
          const response = await gmail.users.messages.list({
            userId: 'me',
            maxResults: Math.min(validatedArgs.maxResults || 10, 100),
            q: validatedArgs.query,
            labelIds: validatedArgs.labelIds,
          });

          const messages = response.data.messages || [];
          
          if (messages.length === 0) {
            return {
              content: [
                {
                  type: "text",
                  text: "No emails found matching the criteria.",
                },
              ],
            };
          }

          // Fetch details for each message
          const emailDetails = await Promise.all(
            messages.slice(0, Math.min(validatedArgs.maxResults || 10, 100)).map(async (msg) => {
              const detail = await gmail.users.messages.get({
                userId: 'me',
                id: msg.id!,
                format: 'metadata',
                metadataHeaders: ['From', 'To', 'Subject', 'Date'],
              });

              const headers = detail.data.payload?.headers || [];
              const from = headers.find(h => h.name === 'From')?.value || '';
              const subject = headers.find(h => h.name === 'Subject')?.value || '';
              const date = headers.find(h => h.name === 'Date')?.value || '';

              return {
                id: detail.data.id,
                threadId: detail.data.threadId,
                snippet: detail.data.snippet,
                from,
                subject,
                date,
                labelIds: detail.data.labelIds || [],
              };
            })
          );

          const emailList = emailDetails.map((email, idx) => 
            `${idx + 1}. ${email.subject}\n   From: ${email.from}\n   Date: ${email.date}\n   ID: ${email.id}\n   Snippet: ${email.snippet}`
          ).join('\n\n');

          return {
            content: [
              {
                type: "text",
                text: `Found ${messages.length} emails:\n\n${emailList}`,
              },
            ],
          };
        }

        case "get_email": {
          const validatedArgs = GetEmailSchema.parse(args);
          const response = await gmail.users.messages.get({
            userId: 'me',
            id: validatedArgs.messageId,
            format: validatedArgs.format,
          });

          const message = response.data;
          const headers = message.payload?.headers || [];
          const from = headers.find(h => h.name === 'From')?.value || '';
          const to = headers.find(h => h.name === 'To')?.value || '';
          const subject = headers.find(h => h.name === 'Subject')?.value || '';
          const date = headers.find(h => h.name === 'Date')?.value || '';

          // Extract body
          let body = '';
          if (message.payload?.body?.data) {
            body = Buffer.from(message.payload.body.data, 'base64').toString('utf-8');
          } else if (message.payload?.parts) {
            const textPart = message.payload.parts.find(part => part.mimeType === 'text/plain');
            if (textPart?.body?.data) {
              body = Buffer.from(textPart.body.data, 'base64').toString('utf-8');
            }
          }

          return {
            content: [
              {
                type: "text",
                text: `Email Details:\n\nFrom: ${from}\nTo: ${to}\nSubject: ${subject}\nDate: ${date}\nMessage ID: ${message.id}\nThread ID: ${message.threadId}\n\n--- Body ---\n${body || message.snippet || 'No body content'}`,
              },
            ],
          };
        }

        case "list_labels": {
          const labelsData = await listLabels(gmail);
          
          const systemLabelsText = labelsData.system.map((l: any) => 
            `- ${l.name} (ID: ${l.id})`
          ).join('\n');
          
          const userLabelsText = labelsData.user.length > 0
            ? labelsData.user.map((l: any) => `- ${l.name} (ID: ${l.id})`).join('\n')
            : 'None';

          return {
            content: [
              {
                type: "text",
                text: `Gmail Labels\n\nSystem Labels (${labelsData.count.system}):\n${systemLabelsText}\n\nUser Labels (${labelsData.count.user}):\n${userLabelsText}\n\nTotal: ${labelsData.count.total} labels`,
              },
            ],
          };
        }

        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    } catch (error: any) {
      return {
        content: [
          {
            type: "text",
            text: `Error: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  });

  // Connect to transport
  const transport = new StdioServerTransport();
  await server.connect(transport);
  
  process.stderr.write('Gmail MCP Server running on stdio transport\n');
}

/**
 * Run authentication server
 */
async function runAuthServer(): Promise<void> {
  try {
    // Initialize OAuth client
    const oauth2Client = await initializeOAuth2Client();

    // Create and start the auth server
    const authServerInstance = new AuthServer(oauth2Client);

    // Start with browser opening (true by default)
    const success = await authServerInstance.start(true);

    if (!success && !authServerInstance.authCompletedSuccessfully) {
      // Failed to start and tokens weren't already valid
      process.stderr.write(
        "Authentication failed. Could not start server or validate existing tokens. Check port availability (3500-3505) and try again.\n"
      );
      process.exit(1);
    } else if (authServerInstance.authCompletedSuccessfully) {
      // Auth was successful (either existing tokens were valid or flow completed just now)
      process.stderr.write("Authentication successful.\n");
      process.exit(0);
    }

    // Keep the server running if needed
    process.on('SIGINT', async () => {
      await authServerInstance.stop();
      process.exit(0);
    });
  } catch (error: unknown) {
    process.stderr.write(`Authentication server error: ${error instanceof Error ? error.message : error}\n`);
    process.exit(1);
  }
}

// Run main function
main().catch((error) => {
  process.stderr.write(`Server error: ${error}\n`);
  process.exit(1);
});

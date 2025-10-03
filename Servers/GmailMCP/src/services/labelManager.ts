/**
 * Label Manager for Gmail MCP Server
 * Provides comprehensive label management functionality
 */
import { gmail_v1 } from 'googleapis';

// Type definitions for Gmail API labels
export interface GmailLabel {
  id: string;
  name: string;
  type?: string;
  messageListVisibility?: string;
  labelListVisibility?: string;
  messagesTotal?: number;
  messagesUnread?: number;
  color?: {
    textColor?: string;
    backgroundColor?: string;
  };
}

/**
 * Creates a new Gmail label
 * @param gmail - Gmail API instance
 * @param labelName - Name of the label to create
 * @param options - Optional settings for the label
 * @returns The newly created label
 */
export async function createLabel(gmail: gmail_v1.Gmail, labelName: string, options: {
  messageListVisibility?: string;
  labelListVisibility?: string;
} = {}) {
  try {
    // Default visibility settings if not provided
    const messageListVisibility = options.messageListVisibility || 'show';
    const labelListVisibility = options.labelListVisibility || 'labelShow';

    const response = await gmail.users.labels.create({
      userId: 'me',
      requestBody: {
        name: labelName,
        messageListVisibility,
        labelListVisibility,
      },
    });

    return response.data;
  } catch (error: any) {
    // Handle duplicate labels more gracefully
    if (error.message && error.message.includes('already exists')) {
      throw new Error(`Label "${labelName}" already exists. Please use a different name.`);
    }
    
    throw new Error(`Failed to create label: ${error.message}`);
  }
}

/**
 * Lists all Gmail labels
 * @param gmail - Gmail API instance
 * @returns Object containing system and user labels
 */
export async function listLabels(gmail: gmail_v1.Gmail) {
  try {
    const response = await gmail.users.labels.list({
      userId: 'me',
    });

    const labels = response.data.labels || [];
    
    // Group labels by type for better organization
    const systemLabels = labels.filter((label: GmailLabel) => label.type === 'system');
    const userLabels = labels.filter((label: GmailLabel) => label.type === 'user');

    return {
      all: labels,
      system: systemLabels,
      user: userLabels,
      count: {
        total: labels.length,
        system: systemLabels.length,
        user: userLabels.length
      }
    };
  } catch (error: any) {
    throw new Error(`Failed to list labels: ${error.message}`);
  }
}

/**
 * Finds a label by name
 * @param gmail - Gmail API instance
 * @param labelName - Name of the label to find
 * @returns The found label or null if not found
 */
export async function findLabelByName(gmail: gmail_v1.Gmail, labelName: string) {
  try {
    const labelsResponse = await listLabels(gmail);
    const allLabels = labelsResponse.all;
    
    // Case-insensitive match
    const foundLabel = allLabels.find(
      (label: GmailLabel) => label.name.toLowerCase() === labelName.toLowerCase()
    );
    
    return foundLabel || null;
  } catch (error: any) {
    throw new Error(`Failed to find label: ${error.message}`);
  }
}

/**
 * Creates label if it doesn't exist or returns existing label
 * @param gmail - Gmail API instance
 * @param labelName - Name of the label to create
 * @param options - Optional settings for the label
 * @returns The new or existing label
 */
export async function getOrCreateLabel(gmail: gmail_v1.Gmail, labelName: string, options: {
  messageListVisibility?: string;
  labelListVisibility?: string;
} = {}) {
  try {
    // First try to find an existing label
    const existingLabel = await findLabelByName(gmail, labelName);
    
    if (existingLabel) {
      return existingLabel;
    }
    
    // If not found, create a new one
    return await createLabel(gmail, labelName, options);
  } catch (error: any) {
    throw new Error(`Failed to get or create label: ${error.message}`);
  }
}

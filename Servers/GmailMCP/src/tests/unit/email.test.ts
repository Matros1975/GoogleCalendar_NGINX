import { describe, it, expect } from 'vitest';
import { validateEmail, createEmailMessage } from '../../utils/email.js';

describe('Email Utilities', () => {
  describe('validateEmail', () => {
    it('should validate correct email addresses', () => {
      expect(validateEmail('test@example.com')).toBe(true);
      expect(validateEmail('user.name@domain.co.uk')).toBe(true);
      expect(validateEmail('user+tag@example.com')).toBe(true);
    });

    it('should reject invalid email addresses', () => {
      expect(validateEmail('invalid')).toBe(false);
      expect(validateEmail('invalid@')).toBe(false);
      expect(validateEmail('@domain.com')).toBe(false);
      expect(validateEmail('user@')).toBe(false);
      expect(validateEmail('')).toBe(false);
    });
  });

  describe('createEmailMessage', () => {
    it('should create a plain text email', () => {
      const args = {
        to: ['recipient@example.com'],
        subject: 'Test Subject',
        body: 'Test body content',
        mimeType: 'text/plain',
      };

      const message = createEmailMessage(args);
      
      expect(message).toContain('To: recipient@example.com');
      expect(message).toContain('Subject: Test Subject');
      expect(message).toContain('Content-Type: text/plain; charset=UTF-8');
      expect(message).toContain('Test body content');
    });

    it('should create an HTML email', () => {
      const args = {
        to: ['recipient@example.com'],
        subject: 'Test HTML',
        body: 'Plain text',
        htmlBody: '<p>HTML content</p>',
        mimeType: 'text/html',
      };

      const message = createEmailMessage(args);
      
      expect(message).toContain('To: recipient@example.com');
      expect(message).toContain('Subject: Test HTML');
      expect(message).toContain('Content-Type: text/html; charset=UTF-8');
      expect(message).toContain('<p>HTML content</p>');
    });

    it('should create a multipart email with both text and HTML', () => {
      const args = {
        to: ['recipient@example.com'],
        subject: 'Test Multipart',
        body: 'Plain text version',
        htmlBody: '<p>HTML version</p>',
        mimeType: 'multipart/alternative',
      };

      const message = createEmailMessage(args);
      
      expect(message).toContain('To: recipient@example.com');
      expect(message).toContain('Subject: Test Multipart');
      expect(message).toContain('Content-Type: multipart/alternative');
      expect(message).toContain('Plain text version');
      expect(message).toContain('<p>HTML version</p>');
    });

    it('should include CC and BCC recipients', () => {
      const args = {
        to: ['recipient@example.com'],
        cc: ['cc@example.com'],
        bcc: ['bcc@example.com'],
        subject: 'Test CC/BCC',
        body: 'Test body',
        mimeType: 'text/plain',
      };

      const message = createEmailMessage(args);
      
      expect(message).toContain('To: recipient@example.com');
      expect(message).toContain('Cc: cc@example.com');
      expect(message).toContain('Bcc: bcc@example.com');
    });

    it('should throw error for invalid email addresses', () => {
      const args = {
        to: ['invalid-email'],
        subject: 'Test',
        body: 'Test',
        mimeType: 'text/plain',
      };

      expect(() => createEmailMessage(args)).toThrow('Recipient email address is invalid');
    });

    it('should handle multiple recipients', () => {
      const args = {
        to: ['user1@example.com', 'user2@example.com'],
        subject: 'Test Multiple',
        body: 'Test body',
        mimeType: 'text/plain',
      };

      const message = createEmailMessage(args);
      
      expect(message).toContain('To: user1@example.com, user2@example.com');
    });

    it('should handle in-reply-to header', () => {
      const args = {
        to: ['recipient@example.com'],
        subject: 'Re: Original Subject',
        body: 'Reply body',
        mimeType: 'text/plain',
        inReplyTo: '<message-id@example.com>',
      };

      const message = createEmailMessage(args);
      
      expect(message).toContain('In-Reply-To: <message-id@example.com>');
      expect(message).toContain('References: <message-id@example.com>');
    });
  });
});

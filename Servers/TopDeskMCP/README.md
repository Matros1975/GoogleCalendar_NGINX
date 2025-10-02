# TopDesk MCP Server

A Model Context Protocol (MCP) server implementation for TopDesk API integration.

## Overview

This MCP server exposes the TopDesk API via the MCP protocol, allowing AI assistants and other MCP clients to interact with TopDesk incidents, operators, and persons.

## Features

- **Incident Management**: Create, retrieve, update, archive, and manage TopDesk incidents
- **Time Tracking**: Register and retrieve time spent on incidents
- **Escalation**: Escalate and de-escalate incidents
- **Attachments**: Download and convert incident attachments to Markdown
- **Operators**: Query and manage TopDesk operators and operator groups
- **Persons**: Create, retrieve, update, and manage TopDesk persons
- **FIQL Queries**: Support for advanced filtering using FIQL syntax

## Configuration

The server requires the following environment variables:

- `TOPDESK_URL`: The base URL of your TopDesk instance (e.g., `https://yourcompany.topdesk.net`)
- `TOPDESK_USERNAME`: The username for authentication
- `TOPDESK_PASSWORD`: The API token/password for authentication
- `TOPDESK_MCP_TRANSPORT`: Transport mode (`stdio`, `streamable-http`, or `sse`) - defaults to `http`
- `TOPDESK_MCP_HOST`: Host to listen on - defaults to `0.0.0.0`
- `TOPDESK_MCP_PORT`: Port to listen on - defaults to `3030`

## Deployment

This server runs as a Docker container behind NGINX proxy with the same security measures as other MCP servers in this deployment.

## Health Check

The server includes a health check endpoint at `/health` for Docker health monitoring.

## Documentation

For more information about the topdesk-mcp package, see:
- [PyPI Package](https://pypi.org/project/topdesk-mcp/)
- [TopDesk API Documentation](https://developers.topdesk.com/)

## Security

- Runs as non-root user
- Read-only root filesystem
- No new privileges
- Resource limits enforced
- IP allowlist and bearer token authentication via NGINX proxy

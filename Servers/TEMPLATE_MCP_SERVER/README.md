# Your MCP Server Template

This is a template directory for adding new MCP servers to the deployment.

## Quick Start

1. **Copy this template**:
   ```bash
   cp -r Servers/TEMPLATE_MCP_SERVER Servers/YourServerName
   ```

2. **Add your server code**:
   - Place source files in this directory
   - Create a Dockerfile
   - Define dependencies (package.json, requirements.txt, etc.)

3. **Update docker-compose.yml** in the project root

4. **Update NGINX configuration** in `nginx/conf.d/`

5. **Test your setup**

See parent `Servers/README.md` for detailed instructions.

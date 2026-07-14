/**
 * greeter — a minimal MCP server written in TypeScript.
 *
 * Purpose in this repo: prove the MCP tool layer is language-agnostic and
 * demonstrate TypeScript (a JD "strong plus"). It exposes one tool, `now`,
 * returning the server time — a stand-in for a real TS-side integration
 * (e.g. a Google Workspace or Ads API client) added in a later phase.
 *
 * Build:  npm install && npm run build   ->   dist/server.js
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new McpServer({ name: "greeter", version: "0.1.0" });

server.registerTool(
  "now",
  {
    description: "Return the current server time in ISO-8601 (UTC). Proves the TS MCP server is live.",
  },
  async () => {
    const iso = new Date().toISOString();
    return { content: [{ type: "text", text: JSON.stringify({ now: iso, tz: "UTC" }) }] };
  }
);

const transport = new StdioServerTransport();
await server.connect(transport);

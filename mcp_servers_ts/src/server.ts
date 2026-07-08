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
import { z } from "zod";

const server = new McpServer({ name: "greeter", version: "0.1.0" });

server.tool(
  "now",
  "Return the current server time in ISO-8601 (UTC). Proves the TS MCP server is live.",
  { tz: z.string().optional().describe("IANA timezone, defaults to UTC") },
  async ({ tz }) => {
    const iso = new Date().toISOString();
    return { content: [{ type: "text", text: JSON.stringify({ now: iso, tz: tz ?? "UTC" }) }] };
  }
);

const transport = new StdioServerTransport();
await server.connect(transport);

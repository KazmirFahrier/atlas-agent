import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /ask + /healthz to the local orchestrator (orchestrator/serve.py on :8080).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/ask": "http://localhost:8080",
      "/healthz": "http://localhost:8080",
    },
  },
});

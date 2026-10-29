/// <reference types="vitest/config" />
import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The React app is served by FastAPI at /app/ (backend/app/main.py). In development the
// Vite server proxies the API and the legacy sign-in page to the FastAPI server, so the
// session cookie works exactly as in production.
const api = process.env.CS_IRCFS_API ?? "http://127.0.0.1:8000";

export default defineConfig({
  base: "/app/",
  plugins: [react()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    port: 5173,
    proxy: {
      "/api": api,
      "/login.html": api,
      "/register.html": api,
      "/assets": api,
      "/favicon.ico": api,
    },
  },
  // Source maps stay on for local debugging only. A shipped .map file reconstructs every
  // screen's source, including comments and the API shapes, so production builds omit it.
  // Set VITE_SOURCEMAP=true for an exception (for example a staging-only investigation).
  build: { outDir: "dist", sourcemap: process.env.VITE_SOURCEMAP === "true", chunkSizeWarningLimit: 900 },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"], // e2e/ is run by Playwright, not Vitest
    css: false,
  },
});

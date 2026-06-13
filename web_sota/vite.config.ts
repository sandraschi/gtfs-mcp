import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    allowedHosts: ['goliath'],
    port: 10912,
    strictPort: true,
    host: "127.0.0.1",
    proxy: {
      "/api": {
        target: "http://127.0.0.1:10913",
        changeOrigin: true,
      },
      "/health": {
        target: "http://127.0.0.1:10913",
        changeOrigin: true,
      },
      "/mcp": {
        target: "http://127.0.0.1:10913",
        changeOrigin: true,
      },
    },
  },
});

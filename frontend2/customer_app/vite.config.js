import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

const devPort = Number(process.env.VITE_PORT || 5173);
const hmrHost = process.env.VITE_HMR_HOST || "localhost";
const hmrClientPort = Number(process.env.VITE_HMR_CLIENT_PORT || devPort);
const hmrProtocol = process.env.VITE_HMR_PROTOCOL || "ws";
const usePolling = process.env.VITE_USE_POLLING === "true";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: devPort,
    strictPort: true,
    watch: {
      usePolling,
    },
    hmr: {
      host: hmrHost,
      clientPort: hmrClientPort,
      protocol: hmrProtocol,
    },
  },
  resolve: {
    alias: {
      "@shared": path.resolve(__dirname, "../shared"),
    },
  },
});

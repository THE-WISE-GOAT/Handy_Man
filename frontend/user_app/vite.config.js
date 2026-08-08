import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

const devPort = Number(process.env.VITE_PORT || 5173);
const hmrHost = process.env.VITE_HMR_HOST || "3.95.60.14";
const hmrClientPort = Number(process.env.VITE_HMR_CLIENT_PORT || 5173);
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
    // Explicitly allow Vite to serve outside the standard root for shared folders
    fs: {
      allow: [path.resolve(__dirname), path.resolve(__dirname, "../shared")],
    },
  },
  resolve: {
    // 1. FORCE Vite to resolve duplicate dependencies to a single instance
    dedupe: ["react", "react-dom", "react-router-dom"],
    alias: {
      "@shared": path.resolve(__dirname, "../shared"),
      // Explicitly direct outside files to find your core packages locally
      "react-router-dom": path.resolve(
        __dirname,
        "node_modules/react-router-dom",
      ),
      react: path.resolve(__dirname, "node_modules/react"),
      "react-dom": path.resolve(__dirname, "node_modules/react-dom"),
    },
  },
});

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

// During dev, proxy API + WebSocket to the FastAPI backend on :8000.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg", "push-handler.js"],
      workbox: {
        // Bring in our push + notification-click handlers.
        importScripts: ["push-handler.js"]
      },
      manifest: {
        name: "Kanbanpy Pro",
        short_name: "Kanbanpy",
        description: "Your Kanban board, on your NAS, on every screen.",
        theme_color: "#0b0c10",
        background_color: "#0b0c10",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" }
        ]
      }
    })
  ],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true }
    }
  }
});

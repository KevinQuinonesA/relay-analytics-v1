import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In dev, /api goes to the backend on BACKEND_PORT; in Docker, nginx proxies it.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": `http://localhost:${process.env.BACKEND_PORT ?? "8000"}` },
  },
});

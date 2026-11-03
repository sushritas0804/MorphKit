import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const port = process.env.MORPHKIT_PORT ?? "8765";
const token = process.env.MORPHKIT_TOKEN ?? "";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: `http://127.0.0.1:${port}`,
        headers: token ? { "x-morphkit-token": token } : undefined,
      },
    },
  },
});

import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const destino = loadEnv(mode, ".", "API_PROXY_TARGET").API_PROXY_TARGET || "http://127.0.0.1:8000";
  return {
    server: { proxy: { "/api": destino } },
    preview: { proxy: { "/api": destino } },
  };
});

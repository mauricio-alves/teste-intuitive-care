import { defineConfig, loadEnv } from "vite";
import { fileURLToPath, URL } from "node:url";
import vue from "@vitejs/plugin-vue";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  const proxyConfig = {
    target: env.VITE_API_URL || "http://localhost:8000",
    changeOrigin: true,
  };

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
    server: {
      port: 5173,
      host: env.VITE_API_URL ? true : "localhost",
      proxy: {
        "/api": proxyConfig,
      },
    },
    preview: {
      port: 5173,
      host: env.VITE_API_URL ? true : "localhost",
      proxy: {
        "/api": proxyConfig,
      },
    },
  };
});

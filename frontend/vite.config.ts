import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://13.51.64.37",
        changeOrigin: true,
      },
      "/media": {
        target: "http://13.51.64.37",
        changeOrigin: true,
      },
    },
  },
});

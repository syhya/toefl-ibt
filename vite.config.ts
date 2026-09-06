import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { readFileSync } from "node:fs";
export default defineConfig({
  plugins: [
    react(),
    {
      name: "offline-font-license",
      generateBundle() {
        this.emitFile({
          type: "asset",
          fileName: "licenses/OpenSans-OFL.txt",
          source: readFileSync(
            new URL("./public/fonts/OFL-OpenSans.txt", import.meta.url),
            "utf8",
          ),
        });
      },
    },
  ],
  publicDir: false,
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:4173" },
  },
  build: { outDir: "dist", sourcemap: false },
});

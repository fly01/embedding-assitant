import { fileURLToPath } from "node:url";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [vue()],
  build: {
    emptyOutDir: false,
    lib: {
      entry: fileURLToPath(new URL("./src/index.ts", import.meta.url)),
      formats: ["es"],
      fileName: "framed-assistant",
      cssFileName: "framed-assistant",
    },
    rollupOptions: {
      external: ["vue"],
    },
  },
});

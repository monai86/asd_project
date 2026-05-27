import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  resolve: {
    alias: {
      "@shared": resolve(__dirname, "../shared/src")
    }
  },
  server: {
    fs: {
      allow: [
        resolve(__dirname),
        resolve(__dirname, "../shared")
      ]
    }
  }
});

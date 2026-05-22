import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config.js";

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: "jsdom",
      setupFiles: ["./vitest.setup.js"],
      globals: true,
      css: false,
      include: ["src/**/*.{test,spec}.{js,jsx}"],
      coverage: {
        provider: "v8",
        reporter: ["text", "html"],
        exclude: [
          "node_modules/",
          "dist/",
          "src/instrument.js",
          "src/main.jsx",
          "**/*.config.js",
          "src/lib/mock-data.js",
        ],
      },
    },
  })
);

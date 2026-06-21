import { defineConfig } from "tsup";

export default defineConfig([
  {
    entry: { index: "src/index.ts" },
    format: ["cjs", "esm"],
    dts: true,
    splitting: false,
    sourcemap: true,
    clean: true,
    external: ["@filenest/core", "@filenest/node", "next"],
    platform: "node",
  },
  {
    entry: { server: "src/server/index.ts" },
    format: ["cjs", "esm"],
    dts: true,
    splitting: false,
    sourcemap: true,
    external: ["@filenest/core", "@filenest/node", "next", "server-only"],
    platform: "node",
  },
]);

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import { fileURLToPath, URL } from "node:url";
import compression from "vite-plugin-compression";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    // SWC for faster builds (10-20x faster than Babel)
    react(),
    // Gzip compression for production
    compression({
      algorithm: "gzip",
      ext: ".gz",
    }),
    // Brotli compression (better than gzip)
    compression({
      algorithm: "brotliCompress",
      ext: ".br",
    }),
  ],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    // Target modern browsers for smaller bundles
    target: "esnext",
    // Enable minification
    minify: "esbuild",
    // Generate source maps for debugging
    sourcemap: false,
    // Chunk splitting for better caching
    rollupOptions: {
      output: {
        manualChunks: {
          // Group React together
          "react-vendor": ["react", "react-dom"],
          // Group MUI + Emotion together to avoid circular dependency issues
          "mui-vendor": [
            "@mui/material",
            "@mui/icons-material",
            "@emotion/react",
            "@emotion/styled",
          ],
        },
        // Asset naming for better caching
        assetFileNames: "assets/[name]-[hash][extname]",
        chunkFileNames: "chunks/[name]-[hash].js",
        entryFileNames: "entries/[name]-[hash].js",
      },
    },
    // Reduce chunk size warnings threshold
    chunkSizeWarningLimit: 500,
  },
  // Optimize dependencies
  optimizeDeps: {
    include: [
      "react",
      "react-dom",
      "@mui/material",
      "@mui/icons-material",
      "@emotion/react",
      "@emotion/styled",
      "axios",
    ],
  },
});

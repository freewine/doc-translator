import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // Enable code splitting
    rollupOptions: {
      output: {
        // Manual chunk splitting for better caching
        manualChunks: {
          // Vendor chunks
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          'ant-design': ['ant-design-vue', '@ant-design/icons-vue'],
          'apollo': ['@apollo/client', 'graphql'],
        },
      },
    },
    // Optimize chunk size
    chunkSizeWarningLimit: 1000,
    // Enable minification (esbuild is faster than terser)
    minify: 'esbuild',
  },
  // Optimize dependencies
  optimizeDeps: {
    include: ['vue', 'vue-router', 'pinia', 'ant-design-vue', '@apollo/client'],
  },
})

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  base: '/memetic-flow/',
  resolve: {
    alias: {
      '@components': path.resolve(__dirname, '../frontend/src/components'),
    },
    // Ensure dependencies imported by aliased frontend components
    // resolve from demo-site/node_modules, not frontend/node_modules
    dedupe: ['d3', 'vue', 'vue-router'],
  },
  optimizeDeps: {
    include: ['d3'],
  },
  server: {
    port: 4000,
  },
})

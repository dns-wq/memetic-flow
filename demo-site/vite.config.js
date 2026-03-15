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
  },
  server: {
    port: 4000,
  },
})

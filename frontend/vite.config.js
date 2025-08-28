import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001,
    strictPort: false,
    proxy: {
      '/clean': {
        target: 'http://localhost:3000',
        changeOrigin: true
      },
      '/scrape': {
        target: 'http://localhost:3000',
        changeOrigin: true
      },
      '/scrape-clean': {
        target: 'http://localhost:3000',
        changeOrigin: true
      },
      '/health': {
        target: 'http://localhost:3000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist'
  }
})

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/upload': 'http://localhost:8765',
      '/status': 'http://localhost:8765',
      '/download': 'http://localhost:8765',
      '/collections': 'http://localhost:8765',
      '/chat': 'http://localhost:8765',
    }
  }
})

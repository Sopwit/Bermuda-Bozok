import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
      proxy: {
        '/health': 'http://127.0.0.1:8000',
        '/locations': 'http://127.0.0.1:8000',
        '/weather': 'http://127.0.0.1:8000',
        '/planning': 'http://127.0.0.1:8000',
        '/recommendations': 'http://127.0.0.1:8000',
        '/get-advice': 'http://127.0.0.1:8000',
      },
    },
  })

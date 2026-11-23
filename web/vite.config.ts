import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev: the browser talks to Vite (:5173); /api and /ws are proxied to FastAPI (:8000).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true },
    },
  },
  test: { environment: 'node' },
})

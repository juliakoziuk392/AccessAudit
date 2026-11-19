import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// У режимі розробки запити /api йдуть на Python-сервер (порт 8000)
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})

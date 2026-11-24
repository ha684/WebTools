import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // `make dev` runs the API on :8000; the UI calls it via same-origin /api
    proxy: { '/api': 'http://localhost:8000' },
  },
  test: { environment: 'node' },
})

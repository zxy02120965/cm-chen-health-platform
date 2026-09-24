import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  // Use IPv4 explicitly so localhost resolution cannot route the proxy to
  // ::1 while the development API listens on 127.0.0.1.
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
})

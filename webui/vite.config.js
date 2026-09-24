import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Antarmuka SELA disajikan langsung oleh server lokal py-xiaozhi
// (src/ui/web/server.py) pada origin yang sama, jadi tidak perlu proxy:
// koneksi WebSocket /ws dan API /api/* otomatis menuju server yang sama.
//
// Saat `npm run dev`, jalankan server py-xiaozhi (port 8765) lebih dulu lalu
// buka http://localhost:5173 - permintaan /ws dan /api diteruskan ke sana.
export default defineConfig({
  base: './',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8765', changeOrigin: true },
      '/ws': { target: 'ws://127.0.0.1:8765', ws: true },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    chunkSizeWarningLimit: 1600,
  },
})

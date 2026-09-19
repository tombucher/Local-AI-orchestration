import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Le frontend appelle l'API en chemin relatif (/api) ; ce proxy la route vers le
// backend. VITE_PROXY_TARGET = http://backend:8000 dans Docker, localhost sur l'hôte.
const proxyTarget = process.env.VITE_PROXY_TARGET || 'http://localhost:8000'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // Accès depuis un autre hôte (Tailscale : mon-mac.tailnet.ts.net)
    allowedHosts: true,
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
        // Streaming SSE (idéation) : pas de buffering
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            if (String(proxyRes.headers['content-type'] || '').includes('text/event-stream')) {
              proxyRes.headers['cache-control'] = 'no-cache'
              proxyRes.headers['x-accel-buffering'] = 'no'
            }
          })
        },
      },
      '/health': { target: proxyTarget, changeOrigin: true },
    },
  },
})

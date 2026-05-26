import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  server: {
    host: '0.0.0.0',
    port: 5000,
    strictPort: true,
    allowedHosts: true,
    hmr: { clientPort: 443 },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 5000,
    strictPort: true,
    allowedHosts: true,
  },
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      includeAssets: ['favicon.svg', 'logo.png', 'pwa-192x192.png', 'pwa-512x512.png'],
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        // Take control immediately — no waiting for old SW to die
        skipWaiting: true,
        clientsClaim: true,
        // SPA fallback: all navigation requests serve index.html
        navigateFallback: 'index.html',
        navigateFallbackDenylist: [/^\/api\//],
        // Prevent stale cache from serving old app shell
        cleanupOutdatedCaches: true,
      },
      devOptions: {
        // Disable SW in dev so it never intercepts HMR or causes blank pages
        enabled: false,
      },
      manifest: {
        name: 'Smart Automated Analytics System',
        short_name: 'SAAS',
        description: 'Decentralized Analytics Dashboard for Department Managers',
        theme_color: '#4f46e5',
        background_color: '#0a0a0b',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
        ],
      },
    }),
  ],
})

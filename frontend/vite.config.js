import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  server: {
    host: '0.0.0.0',
    port: 5000,
    strictPort: true,
    allowedHosts: ['localhost', '127.0.0.1', '.ngrok.io', '.ngrok-free.app'],
    hmr: { clientPort: 5000 },
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
    allowedHosts: ['localhost', '127.0.0.1', '.ngrok.io', '.ngrok-free.app'],
  },
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      includeAssets: ['favicon.svg', 'logo.png', 'pwa-192x192.png', 'pwa-512x512.png'],
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        skipWaiting: true,
        clientsClaim: true,
        navigateFallback: 'index.html',
        navigateFallbackDenylist: [/^\/api\//],
        cleanupOutdatedCaches: true,
        // Aggressive runtime caching for API responses
        runtimeCaching: [
          {
            urlPattern: /^\/api\/summary/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-summary',
              expiration: { maxEntries: 10, maxAgeSeconds: 120 },
            },
          },
          {
            urlPattern: /^\/api\/(kpis|forecasts|dashboard)/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-data',
              expiration: { maxEntries: 50, maxAgeSeconds: 60 },
            },
          },
        ],
      },
      devOptions: {
        enabled: false,
      },
      manifest: {
        name: 'CNPS Smart Automated Analytics System',
        short_name: 'CNPS Analytics',
        description: 'Institutional analytics for CNPS — contributions, pensions, AT/MP',
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
  build: {
    // Enable source maps only in non-production
    sourcemap: process.env.NODE_ENV !== 'production',
    // Chunk size warnings
    chunkSizeWarningLimit: 250,
    // Aggressive code splitting
    rollupOptions: {
      output: {
        manualChunks: {
          // React core
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          // UI icons
          'vendor-icons': ['lucide-react'],
          // Charts (heavy - split separately)
          'vendor-charts': ['recharts'],
          // Supabase
          'vendor-supabase': ['@supabase/supabase-js'],
        },
      },
    },
    // Minification
    minify: 'esbuild',
    // CSS code splitting
    cssCodeSplit: true,
  },
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'lucide-react',
      'recharts',
      '@supabase/supabase-js',
    ],
    // Force pre-bundling of these
    force: true,
  },
})
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  // One .env at the repo root serves every module; Vite only exposes VITE_* to the browser.
  envDir: '..',
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icon.svg'],
      workbox: {
        // Precache everything, fixtures and fonts included, so demo mode runs with no network.
        globPatterns: ['**/*.{js,css,html,svg,png,woff2}'],
        navigateFallback: '/index.html',
      },
      manifest: {
        name: 'প্রবাসী Shield',
        short_name: 'প্রবাসী Shield',
        description: 'এজেন্টকে টাকা দেওয়ার আগে চাকরির অফার যাচাই করুন।',
        lang: 'bn',
        start_url: '/',
        display: 'standalone',
        orientation: 'portrait',
        background_color: '#F5F0E1',
        theme_color: '#F5F0E1',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
    }),
  ],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
})

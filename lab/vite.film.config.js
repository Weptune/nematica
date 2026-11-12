import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Film renders of the real data (no interface): npm run film, then open film.html?shot=hero
export default defineConfig({
  base: './',
  plugins: [react()],
  build: { outDir: 'film-dist', emptyOutDir: true, rollupOptions: { input: { film: 'film.html' } } },
})

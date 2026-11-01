import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The public site serves web/. Build the lab into that site as a first-class route.
export default defineConfig({
  base: './',
  plugins: [react()],
  build: { outDir: '../web/lab', emptyOutDir: true },
})

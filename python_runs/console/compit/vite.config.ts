// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tsconfigPaths from 'vite-tsconfig-paths'
import path from 'node:path'



export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  resolve: {
    alias: {
      // external absolute alias must also exist here for the bundler:
      'shared-functions': path.resolve('/var/www/functions')
    }
  }
})


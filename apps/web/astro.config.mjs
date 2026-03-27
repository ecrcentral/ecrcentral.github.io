import { defineConfig } from 'astro/config'
import sitemap from '@astrojs/sitemap'
import { resolve } from 'path'
import { fileURLToPath } from 'url'

const __dirname = fileURLToPath(new URL('.', import.meta.url))
const dataDir = resolve(__dirname, '../../data')

export default defineConfig({
  output: 'static',
  site: 'https://ecrcentral.org',
  integrations: [sitemap()],
  build: {
    assets: 'assets',
  },
  vite: {
    resolve: {
      alias: {
        '@data': dataDir,
      },
    },
    server: {
      fs: {
        allow: [__dirname, dataDir],
      },
    },
  },
})

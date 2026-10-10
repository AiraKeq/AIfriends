import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  // Django serves this build through django.contrib.staticfiles: STATIC_URL is
  // '/static/' and STATICFILES_DIRS is backend/static, so the file on disk at
  // backend/static/frontend/index.html is reachable at /static/frontend/index.html.
  // Vite prepends base to every emitted URL, so base must be that full prefix --
  // '/assets/' would produce /assets/assets/... because the asset dir is already
  // called assets.
  base: '/static/frontend/',
  build: {
    // fileURLToPath + import.meta.url instead of __dirname: __dirname is a
    // CommonJS variable that Vite only shims today; configLoader: 'native'
    // will make it genuinely undefined.
    outDir: fileURLToPath(new URL('../backend/static/frontend', import.meta.url)),
    emptyOutDir: true,
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})

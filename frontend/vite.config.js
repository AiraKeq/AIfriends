import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ command }) => ({
    plugins: [
        vue(),
        vueDevTools(),
        tailwindcss(),
    ],

    // 开发页面从根路径打开，构建资源由 Django 静态目录提供
    base: command === 'serve' ? '/' : '/static/frontend/',

    build: {
        outDir: fileURLToPath(
            new URL('../backend/static/frontend', import.meta.url)
        ),
        emptyOutDir: true,
    },

    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url)),
        },
    },
}))
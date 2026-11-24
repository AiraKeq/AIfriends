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

    // 开发时 Django 的媒体文件要透传，否则卡片/头像的 /media/... 会打到 5173，
    // 变成一屏破图（后端返回的是相对路径，构建后同源才不出问题）。
    server: {
        proxy: {
            '/media': 'http://127.0.0.1:8000',
        },
    },

    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url)),
        },
    },
}))
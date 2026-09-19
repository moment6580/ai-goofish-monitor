import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: path.resolve(__dirname, '../dist'),
    emptyOutDir: true,
    rollupOptions: {
      output: {
        // 视图保持 eager 打包以保证切换零延迟；仅将体积大且极少变动的
        // 第三方依赖拆分为独立 chunk，提升浏览器缓存命中率。
        manualChunks: {
          'vendor-vue': ['vue', 'vue-router', 'vue-i18n'],
          'vendor-ui': ['reka-ui', 'lucide-vue-next', 'class-variance-authority', 'clsx', 'tailwind-merge'],
        },
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/auth': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
      },
    },
  },
})

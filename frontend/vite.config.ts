import { defineConfig } from 'vite'
import type { PluginOption } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(async () => {
  const plugins: PluginOption[] = [react(), tailwindcss()];
  try {
    const sourceTagsModulePath = './.vite-source-tags.js';
    const sourceTagsModule = await import(sourceTagsModulePath) as { sourceTags?: () => PluginOption };
    if (typeof sourceTagsModule.sourceTags === 'function') {
      const sourceTagsPlugin = sourceTagsModule.sourceTags();
      plugins.push(sourceTagsPlugin);
    }
  } catch (error) {
    void error;
  }
  return {
    plugins,
    server: {
      proxy: {
        '/health': 'http://127.0.0.1:8000',
        '/locations': 'http://127.0.0.1:8000',
        '/weather': 'http://127.0.0.1:8000',
        '/planning': 'http://127.0.0.1:8000',
        '/recommendations': 'http://127.0.0.1:8000',
        '/get-advice': 'http://127.0.0.1:8000',
      },
    },
  };
})

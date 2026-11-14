// @ts-check
import { defineConfig } from 'astro/config';
import node from '@astrojs/node';

// https://astro.build/config
// Modo servidor: las páginas se generan en cada petición con los datos de la API de Django.
export default defineConfig({
  output: 'server',
  adapter: node({ mode: 'standalone' }),
});

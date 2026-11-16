// @ts-check
import { defineConfig } from 'astro/config';
import node from '@astrojs/node';
import vercel from '@astrojs/vercel';

// https://astro.build/config
// Modo servidor: las páginas se generan en cada petición con los datos de la API de Django.
// Vercel define la variable VERCEL al compilar: ahí se usa su adaptador; en Docker (local), el de Node.
export default defineConfig({
  output: 'server',
  adapter: process.env.VERCEL ? vercel() : node({ mode: 'standalone' }),
});

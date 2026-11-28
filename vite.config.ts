import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The public address, for link previews and canonical links in index.html
// (%VITE_SITE_URL%). The deploy workflow sets it from public/CNAME.
process.env.VITE_SITE_URL ??= 'https://www.cimabecco.it';

// VITE_ variables are bundled into the public client. Reject secret credentials.
const browserKey = process.env.VITE_SUPABASE_KEY || '';
if (/^sb_secret_/i.test(browserKey) || /service_role/i.test(browserKey)) {
  throw new Error('Refusing to bundle a Supabase secret/service-role key. Use a publishable key.');
}

export default defineConfig({
  plugins: [react()],
  // Set to '/<repo-name>/' if deploying to GitHub Pages under a project path.
  base: process.env.VITE_BASE ?? '/',
  // Not Vite's default 5173 — that collides with other local servers and you end
  // up staring at a different project wondering why nothing works. `strictPort`
  // makes a collision fail loudly instead of silently sliding to another port.
  server: { port: 5180, strictPort: true, host: true, open: true },
  optimizeDeps: { exclude: ['maplibre-gl'] },
  build: {
    outDir: 'dist',
    // Source maps are opt-in for debugging, not public by default.
    sourcemap: process.env.VITE_BUILD_SOURCEMAP === 'true',
    // maplibre-gl is larger than 500 kB minified; raising the warning keeps the
    // build output clean while we still report genuinely oversized app chunks.
    chunkSizeWarningLimit: 1500,
  },
});

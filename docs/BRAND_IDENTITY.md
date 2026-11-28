# Cima Becco — identità del simbolo (28/11/2026)

## Concetto
Due V sovrapposte. La cima è la lettura immediata; le corna dello stambecco sono la seconda lettura. Niente occhi, muso, sole o raggi nella versione statica canonica. Il simbolo vive come SVG in `public/brand/cima-becco-mark.svg` e come componente React unico `Mark` in `src/components/icons.tsx`.

## Palette e tipografia
Verde bosco `#143d2f`, verde acido `#e4ffbe`, fucsia `#ff2677`; caratteri già in uso: Bricolage Grotesque (display), Space Grotesk (testi), Barlow Condensed (logotipo/accenti). Non introdurre un secondo sistema visivo.

## Microinterazioni
- Navbar: apertura lieve delle corna con hover/focus; il logo resta un link alla home.
- Footer: pulsante dello stambecco, click/tastiera/touch, battute alternate e raggi/occhi solo dopo attivazione.
- Vietati loop automatici, spostamenti di layout e animazioni di logo dentro i marker ripetuti sulle mappe.
- `prefers-reduced-motion: reduce` disabilita le trasformazioni e le transizioni; i testi continuano a funzionare.

## Distribuzione
- Header e footer: `SiteChrome.tsx` (un solo punto di integrazione).
- Favicon: `public/favicon.svg`.
- PWA: `public/icons/icon-192.png`, `icon-512.png`, `icon-maskable-512.png`, icona SVG e `site.webmanifest`.
- Apple touch: `public/icons/apple-touch-icon.png`.
- Anteprima social: `public/og-image.png`.

Il linguaggio irriverente è ammesso soltanto nel branding editoriale; mai in avvisi di sicurezza, percorribilità, meteo o schede fattuali. Manutenere i vettori e le icone dalla stessa geometria.

## Checklist rapida
Verificare navbar 320–390px, contrasto, hover desktop, tap e tastiera, SVG multipli nella stessa pagina, favicon a 16–24px, PWA maskable, `prefers-reduced-motion`, build e test. Test locali disponibili in `brandMark.test.tsx`.

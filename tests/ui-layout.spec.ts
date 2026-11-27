import { test, expect } from '@playwright/test';

const categories = [
  { hash:'#rifugi', heading:'RIFUGI.' },
  { hash:'#bivacchi', heading:'BIVACCHI.' },
  { hash:'#paesi', heading:'PAESI.' },
] as const;

for (const item of categories) {
  test('esplorazione '+item.heading+' desktop, mappa e risultati nello stesso viewport', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/'+item.hash);
    await expect(page.locator('.cb-explore-heading h1')).toHaveText(item.heading);
    const bar = await page.locator('.cb-explore-overview').boundingBox();
    const work = await page.locator('.cb-explore-workspace').boundingBox();
    const list = await page.locator('.cb-explore-list').boundingBox();
    const map = await page.locator('.cb-explore-map-panel').boundingBox();
    expect(bar).not.toBeNull();expect(work).not.toBeNull();
    expect(list).not.toBeNull();expect(map).not.toBeNull();
    expect(bar!.height).toBeLessThan(115);
    expect(work!.height).toBeGreaterThan(650);
    expect(Math.abs((work!.y + work!.height)-900)).toBeLessThan(4);
    expect(Math.abs((list!.x + list!.width)-map!.x)).toBeLessThan(3);
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+2);
    expect(overflow).toBe(false);
  });
}

test('mobile: filtro compatto, lista e mappa si alternano senza sbordare', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/#rifugi');
  await expect(page.locator('.cb-explore-heading h1')).toHaveText('RIFUGI.');
  const bar=await page.locator('.cb-explore-overview').boundingBox();
  const work=await page.locator('.cb-explore-workspace').boundingBox();
  expect(bar!.height).toBeLessThan(105);
  expect(work!.height).toBeGreaterThan(620);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(392);
  await expect(page.locator('.cb-explore-list')).toBeVisible();
  await page.getByRole('button',{name:'Mappa',exact:true}).click();
  await expect(page.locator('.cb-explore-map-panel')).toBeVisible();
  await expect(page.locator('.cb-explore-list')).toBeHidden();
  await page.getByRole('button',{name:'Elenco',exact:true}).click();
  await expect(page.locator('.cb-explore-list')).toBeVisible();
});

test('home: hero utilizzabile senza illustrazioni e con navigazione responsive',async ({page})=>{
  for (const width of [390,768,1440]) {
    await page.setViewportSize({width,height:900});
    await page.goto('/');
    await expect(page.locator('.cb-hero-v3 h1')).toContainText('DOVE SI VA?');
    await expect(page.locator('.cb-hero-v3-directory a')).toHaveCount(5);
    await expect(page.getByRole('link',{name:/Esplora i sentieri/})).toBeVisible();
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+2);
    expect(overflow).toBe(false);
  }
});

for(const section of ['rifugi','bivacchi','paesi'] as const){
  test('scheda '+section+': layout condiviso e larghezza corretta',async({page})=>{
    await page.setViewportSize({width:390,height:844});
    await page.goto('/#'+section);
    const first=page.locator('.cb-explore-card-detail').first();
    await expect(first).toBeVisible({timeout:20000});
    await first.click();
    await expect(page.locator('.cb-location-profile h1')).toBeVisible();
    await expect(page.locator('.cb-detail-metrics')).toBeVisible();
    await expect(page.locator('.cb-detail-facts')).toBeVisible();
    for(const width of [320,375,390,768,1024,1440]){
      await page.setViewportSize({width,height:844});
      const sizes=await page.evaluate(()=>({
        viewport:window.innerWidth,
        scroll:document.documentElement.scrollWidth,
        content:document.querySelector('.cb-location-content')?.getBoundingClientRect().width ?? 0,
      }));
      expect(sizes.scroll).toBeLessThanOrEqual(sizes.viewport+2);
      expect(sizes.content).toBeGreaterThan(0);
      expect(sizes.content).toBeLessThanOrEqual(sizes.viewport+1);
    }
  });
}
test('trekking: scheda condivisa senza overflow',async({page})=>{
  await page.setViewportSize({width:375,height:812});
  await page.goto('/#atlante/trekking');
  const first=page.locator('.cb-atlas-trek').first();
  await expect(first).toBeVisible({timeout:20000});
  await first.click();
  await expect(page.locator('.cb-trek-profile h1')).toBeVisible();
  await expect(page.locator('.cb-trek-profile .cb-detail-metrics')).toBeVisible();
  for(const width of [320,375,768,1024]){
    await page.setViewportSize({width,height:812});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+2)).toBe(false);
  }
});

test('permalink percorso: mappa e stage occupano la larghezza mobile', async ({page}) => {
  await page.setViewportSize({width:390,height:844});
  await page.goto('/route/osm-hiking-13956722/');
  await expect(page.locator('.map-page .stage')).toBeVisible();
  for(const width of [320,375,390,430,768]) {
    await page.setViewportSize({width,height:844});
    for(const selector of ['.map-page .stage','.map-page .map-wrap']) {
      const box=await page.locator(selector).boundingBox();
      expect(box?.width ?? 0).toBeGreaterThanOrEqual(width-2);
    }
  }
});

test('navbar: stessa larghezza in home, catalogo e permalink', async ({page}) => {
  for (const width of [320,390,768,1440]) {
    await page.setViewportSize({width,height:900});
    for (const path of ['/', '/#rifugi', '/#routes', '/route/osm-hiking-13956722/']) {
      await page.goto(path);
      const header=page.locator('.site-header').first();
      await expect(header).toBeVisible();
      await expect.poll(async()=> (await header.boundingBox())?.width ?? 0)
        .toBeGreaterThanOrEqual(width-2);
      expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(width+2);
    }
  }
});


test('permalink: scheda sentiero completa, mappa responsive e un solo titolo', async ({page}) => {
  test.setTimeout(90_000);
  await page.setViewportSize({width:390,height:844});
  await page.goto('/route/osm-hiking-13956722/');
  await page.emulateMedia({reducedMotion:'reduce'});
  const panel=page.locator('.route-panel.in-sidebar.is-full-detail');
  await expect(panel).toBeVisible({timeout:45_000});
  await expect(panel.locator('h1.route-title-heading')).toBeVisible();
  await expect(panel.getByLabel('Dati principali del percorso')).toBeVisible();
  await expect(panel.getByLabel('Quote e pendenze del percorso')).toBeVisible();
  await expect(panel.locator('.route-more-toggle')).toHaveCount(0);
  await expect(page.locator('.site-header input[type=search]')).toBeVisible();
  for(const width of [320,375,390,768,1024,1440]){
    await page.setViewportSize({width,height:844});
    const sizes=await page.evaluate(()=>{
      const stage=document.querySelector('.map-page .stage')!.getBoundingClientRect();
      const panel=document.querySelector('.route-panel.in-sidebar')!.getBoundingClientRect();
      const map=document.querySelector('.map-page .map-wrap')!.getBoundingClientRect();
      const offenders=[...document.querySelectorAll<HTMLElement>('.route-panel *, .site-header *')]
        .map(el=>{
          const rect=el.getBoundingClientRect();
          return {tag:el.tagName,cls:typeof el.className==='string'?el.className.slice(0,80):'',right:Math.round(rect.right),left:Math.round(rect.left),width:Math.round(rect.width),scroll:el.scrollWidth,client:el.clientWidth};
        })
        .filter(item=>item.right>innerWidth+2||item.width>innerWidth+2)
        .sort((a,b)=>b.right-a.right).slice(0,16);
      return {scroll:document.documentElement.scrollWidth,viewport:innerWidth,stage:stage.width,panel:panel.width,map:map.width,offenders};
    });
    expect(sizes.scroll, JSON.stringify({width,offenders:sizes.offenders})).toBeLessThanOrEqual(width+2);
    expect(sizes.stage).toBeGreaterThanOrEqual(width-2);
    expect(sizes.panel).toBeGreaterThan(width<900?width*.9:width*.35);
    expect(sizes.map).toBeGreaterThan(width<900?width*.9:width*.35);
  }
});

test('esplorazione sentieri: la scheda completa apre un permalink reale', async ({page}) => {
  test.setTimeout(80_000);
  await page.setViewportSize({width:1280,height:850});
  await page.goto('/#routes');
  const first=page.locator('.result-item.route-item .result-card').first();
  await expect(first).toBeVisible({timeout:45_000});
  await first.click();
  const panel=page.locator('.map-wrap .route-panel');
  await expect(panel).toBeVisible({timeout:20_000});
  const link=panel.locator('a.route-more-toggle');
  await expect(link).toBeVisible();
  const href=await link.getAttribute('href');
  expect(href).toMatch(/^\/(?:route\/|#route\/)/);
  await link.click();
  await expect(page.locator('.route-panel.in-sidebar.is-full-detail')).toBeVisible({timeout:45_000});
  expect(new URL(page.url()).pathname + new URL(page.url()).hash).toContain('route/');
});

test('ricerca da URL con parametri: collegamento assoluto alla scheda locale', async ({page}) => {
  test.setTimeout(80_000);
  await page.goto('/?utm_source=regressione#routes');
  const search=page.getByRole('searchbox',{name:/Cerca una cima, un sentiero/});
  await expect(search).toBeVisible();
  await search.fill('Bivacco Comici');
  const suggestion=page.locator('.searchbar-results button').filter({hasText:'Bivacco Comici'}).first();
  await expect(suggestion).toBeVisible({timeout:30_000});
  await suggestion.click();
  await expect(page).toHaveURL(/\/bivacchi\/osm-w-152273223\/$/,{timeout:30_000});
  await expect(page.locator('.cb-location-profile h1')).toBeVisible();
});

test('navbar: la ricerca globale resta disponibile in tutte le sezioni', async ({page})=>{
  for(const path of ['/', '/#rifugi', '/#paesi', '/#atlante/trekking', '/route/osm-hiking-13956722/']){
    await page.setViewportSize({width:390,height:844});
    await page.goto(path);
    await expect(page.locator('.site-header input[type=search]')).toBeVisible();
    await expect.poll(async()=> (await page.locator('.site-header').boundingBox())?.width ?? 0)
      .toBeGreaterThanOrEqual(388);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(392);
  }
});

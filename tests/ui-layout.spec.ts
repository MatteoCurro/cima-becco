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
    await expect(page.locator('.cb-browse-tabs a.is-active')).toHaveText(item.heading.replace('.','')==='PAESI'?'Paesi':item.heading==='RIFUGI.'?'Rifugi':'Bivacchi');
    const bar = await page.locator('.cb-browse-bar').boundingBox();
    const work = await page.locator('.cb-explore-workspace').boundingBox();
    const list = await page.locator('.cb-explore-list').boundingBox();
    const map = await page.locator('.cb-explore-map-panel').boundingBox();
    expect(bar).not.toBeNull();expect(work).not.toBeNull();
    expect(list).not.toBeNull();expect(map).not.toBeNull();
    expect(bar!.height).toBeLessThan(120);
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
  await expect(page.locator('.cb-browse-tabs a.is-active')).toHaveText('Rifugi');
  const bar=await page.locator('.cb-browse-bar').boundingBox();
  const work=await page.locator('.cb-explore-workspace').boundingBox();
  expect(bar!.height).toBeLessThan(115);
  expect(work!.height).toBeGreaterThan(580);
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
      const offenders=[...document.querySelectorAll<HTMLElement>('body, #root, .map-page, .map-page *')]
        .map(el=>{
          const rect=el.getBoundingClientRect();
          const css=getComputedStyle(el);
          return {tag:el.tagName,cls:typeof el.className==='string'?el.className.slice(0,65):'',
            right:Math.round(rect.right),left:Math.round(rect.left),width:Math.round(rect.width),
            scroll:el.scrollWidth,client:el.clientWidth,position:css.position,overflow:css.overflowX};
        })
        .filter(item=>(item.scroll>item.client+3 && item.client>0)||item.right>innerWidth+2)
        .sort((a,b)=>(b.scroll-b.client)-(a.scroll-a.client)).slice(0,22);
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

test('permalink borgo privo di metadati: pagina vera e mappa locale',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/borghi/osm-n-240044790/');
  await expect(page.locator('.cb-location-profile h1')).toContainText('Abfaltersbach',{timeout:30_000});
  await expect(page.locator('.cb-location-sidebar .cb-atlas-map')).toBeVisible();
  await expect(page.locator('.cb-location-sidebar .cb-map-layer-switches')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(392);
});

test('unico selettore: cambia categoria e mostra solo i filtri pertinenti',async({page})=>{
  await page.setViewportSize({width:1280,height:850});
  await page.goto('/#rifugi');
  const selector=page.getByRole('navigation',{name:'Esplora e filtra le risorse'});
  await expect(selector.getByRole('tab',{name:'Rifugi'})).toHaveAttribute('aria-selected','true');
  await expect(selector.getByRole('button',{name:'Con recapiti'})).toBeVisible();
  await selector.getByRole('tab',{name:'Sentieri'}).click();
  await expect(page).toHaveURL(/#routes$/);
  await expect(page.locator('.cb-browse-tabs a.is-active')).toHaveText('Sentieri');
  await expect(page.getByRole('group',{name:'Tipologia di sentiero'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Con recapiti'})).toHaveCount(0);
});

test('cima: hero nella colonna sinistra e mappa nel 58% destro',async({page})=>{
  test.setTimeout(90_000);
  const response=await page.request.get('/data/peaks/index.json');
  expect(response.ok()).toBeTruthy();
  const index=await response.json() as {top:[number,string,number,number,...unknown[]][]};
  const [id,,lat,lng]=index.top[0];
  const tile=(n:number)=>Math.floor(n/5)*5;
  const token=(n:number)=>n<0?'m'+(-n):String(n);
  const slug=`gn${id}-${token(tile(lat))}x${token(tile(lng))}`;
  await page.setViewportSize({width:1366,height:800});
  await page.goto('/#venue/'+slug);
  await expect(page.locator('.venue-detail-content.cb-venue-document')).toBeVisible({timeout:45_000});
  await expect(page.locator('.cb-venue-hero-media')).toBeVisible();
  await expect(page.locator('.cb-venue-map-pane .mini-map')).toBeVisible();
  const sizes=await page.evaluate(()=>{
    const left=document.querySelector('.cb-venue-grid>.venue-detail-head')!.getBoundingClientRect();
    const right=document.querySelector('.cb-venue-grid>.venue-detail-side')!.getBoundingClientRect();
    return {left:left.width,right:right.width,space:innerWidth,overflow:document.documentElement.scrollWidth};
  });
  expect(sizes.left).toBeGreaterThan(450);
  expect(sizes.right).toBeGreaterThan(sizes.left);
  expect(sizes.overflow).toBeLessThanOrEqual(1368);
  await page.setViewportSize({width:390,height:844});
  const mobile=await page.locator('.cb-venue-map-pane').boundingBox();
  expect(mobile?.width||0).toBeGreaterThanOrEqual(388);
});

test('navbar e filtri: occupano l’intera larghezza e non hanno slot fissi',async({page})=>{
  test.setTimeout(150_000);
  for(const width of [1024,1440]){
    await page.setViewportSize({width,height:900});
    for(const path of ['/#routes','/#map','/#rifugi','/#paesi']){
      await page.goto(path);
      // WebKit può sostituire il nav una seconda volta durante il mount React.
      // Misuriamo in modo atomico e attendiamo la stabilizzazione, senza
      // interpretare boundingBox() di un nodo smontato come larghezza 0.
      await expect.poll(async()=>page.evaluate(expectedWidth=>{
        const selectors=['.site-header','.site-header-row','.cb-browse-bar','.cb-browse-tabs','.cb-browse-facets'];
        const rects=selectors.map(selector=>document.querySelector(selector)?.getBoundingClientRect());
        const tabs=document.querySelectorAll('.cb-browse-tabs > a, .cb-browse-tabs > span.is-upcoming');
        const last=tabs.length?tabs[tabs.length-1].getBoundingClientRect():null;
        if(rects.some(r=>!r)||!last)return false;
        return rects.every(r=>r && r.left>=-2 && r.left<=2 && r.right>=expectedWidth-2)
          && last.right>expectedWidth-48;
      },width),{timeout:20000,message:'Layout navbar e tabs '+path+' a '+width+' px'}).toBe(true);
    }
  }
});

test('mappe: stesso canvas full-bleed e intestazione, senza barre che sottraggono altezza',async({page})=>{
  test.setTimeout(100_000);
  await page.setViewportSize({width:1440,height:900});
  for(const config of [
    {path:'/#routes',outer:'.map-page .map-wrap',canvas:'.map-page .map-wrap > .map'},
    {path:'/#rifugi',outer:'.cb-explore-map-panel',canvas:'.cb-explore-map-panel .cb-atlas-map-wrap'},
    {path:'/#paesi',outer:'.cb-explore-map-panel',canvas:'.cb-explore-map-panel .cb-atlas-map-wrap'},
    {path:'/route/osm-hiking-13956722/',outer:'.map-page .map-wrap',canvas:'.map-page .map-wrap > .cb-atlas-map-wrap'},
  ]){
    await page.goto(config.path);
    const outer=page.locator(config.outer);
    const canvas=page.locator(config.canvas);
    await expect(outer).toBeVisible({timeout:30000});
    await expect(canvas).toBeVisible({timeout:30000});
    await expect(outer.locator('.cb-map-context')).toBeVisible();
    const box=await outer.boundingBox(), inner=await canvas.boundingBox();
    expect(box).not.toBeNull();expect(inner).not.toBeNull();
    expect(box!.x+box!.width,config.path).toBeGreaterThan(1438);
    expect(Math.abs(box!.width-inner!.width),config.path).toBeLessThanOrEqual(3);
    expect(Math.abs(box!.height-inner!.height),config.path).toBeLessThanOrEqual(3);
    expect(await canvas.evaluate(el=>getComputedStyle(el).borderRadius)).toBe('0px');
  }
  await page.setViewportSize({width:390,height:844});
  await page.goto('/#rifugi');
  await page.getByRole('button',{name:'Mappa',exact:true}).click();
  const wrap=page.locator('.cb-explore-map-panel .cb-atlas-map-wrap');
  await expect(wrap).toBeVisible();
  const b=await wrap.boundingBox();
  expect(b?.width||0).toBeGreaterThanOrEqual(388);
  await expect(page.locator('.cb-explore-map-topline')).toHaveCount(0);
});

test('scheda luogo: gli strumenti dei livelli non si sovrappongono a note flottanti',async({page})=>{
  await page.setViewportSize({width:1280,height:850});
  await page.goto('/borghi/osm-n-240044790/');
  await expect(page.locator('.cb-location-profile h1')).toContainText('Abfaltersbach');
  const map=page.locator('.cb-location-sidebar');
  await expect(map.locator('.cb-map-context')).toBeVisible();
  await expect(map.locator('.cb-map-layer-switches button').first()).toBeVisible();
  await expect(map.locator('.cb-location-map-note')).toHaveCount(0);
  const positions=await page.evaluate(()=>{
    const h=document.querySelector('.cb-location-sidebar .cb-map-context')!.getBoundingClientRect();
    const layers=document.querySelector('.cb-location-sidebar .cb-map-layer-switches')!.getBoundingClientRect();
    return {headingBottom:h.bottom,layerTop:layers.top};
  });
  expect(positions.layerTop).toBeGreaterThan(positions.headingBottom+8);
});

test('permalink rifugio: header e griglia flush alla viewport, breadcrumb non sposta la mappa',async({page})=>{
  test.setTimeout(100_000);
  for(const width of [1664,1280,390]){
    await page.setViewportSize({width,height:914});
    await page.goto('/rifugi/osm-w-39173072/');
    await expect(page.locator('.cb-location-profile h1')).toContainText('Karlsbader Hütte',{timeout:40000});
    await expect(page.locator('.cb-location-content > .cb-location-back')).toBeVisible();
    const layout=await page.evaluate(()=>{
      const selectors=['.cb-explore-page','.site-header','.site-header-row',
        '.cb-explore-detail-shell','.cb-location-profile','.cb-location-body',
        '.cb-location-content','.cb-location-sidebar'];
      const boxes=Object.fromEntries(selectors.map(selector=>{
        const el=document.querySelector(selector)!;
        const r=el.getBoundingClientRect(),style=getComputedStyle(el);
        return [selector,{left:r.left,right:r.right,top:r.top,width:r.width,
          maxWidth:style.maxWidth,paddingLeft:style.paddingLeft,marginLeft:style.marginLeft}];
      }));
      return {boxes,viewport:innerWidth,scrollWidth:document.documentElement.scrollWidth};
    });
    const r=(selector:string)=>layout.boxes[selector] as {left:number;right:number;top:number;width:number;maxWidth:string;paddingLeft:string};
    for(const selector of ['.cb-explore-page','.site-header','.site-header-row',
      '.cb-explore-detail-shell','.cb-location-profile','.cb-location-body']){
      expect(r(selector).left,JSON.stringify({width,selector,layout})).toBeGreaterThanOrEqual(-2);
      expect(r(selector).left,JSON.stringify({width,selector,layout})).toBeLessThanOrEqual(2);
      expect(r(selector).right,JSON.stringify({width,selector,layout})).toBeGreaterThanOrEqual(width-2);
      expect(r(selector).right,JSON.stringify({width,selector,layout})).toBeLessThanOrEqual(width+2);
    }
    expect(r('.cb-explore-detail-shell').maxWidth).toBe('none');
    expect(r('.cb-explore-detail-shell').paddingLeft).toBe('0px');
    expect(layout.scrollWidth,JSON.stringify(layout)).toBeLessThanOrEqual(width+2);
    if(width>900){
      expect(Math.abs(r('.cb-location-sidebar').top-r('.cb-location-body').top)).toBeLessThanOrEqual(2);
      expect(Math.abs(r('.cb-location-content').width/width-.42)).toBeLessThan(.03);
      expect(Math.abs(r('.cb-location-sidebar').width/width-.58)).toBeLessThan(.03);
    }else expect(r('.cb-location-sidebar').width).toBeGreaterThanOrEqual(width-2);
  }
});

test('altimetro permalink: grafico muove il cursore sulla mappa e lo azzera uscendo',async({page})=>{
  test.setTimeout(100_000);
  await page.setViewportSize({width:1440,height:900});
  await page.goto('/route/osm-hiking-13956722/');
  const cursor=page.locator('#cb-route-map .cb-atlas-map-wrap');
  await expect(cursor).toHaveAttribute('data-cursor-ready','true',{timeout:50_000});
  const svg=page.locator('.route-panel .profile-chart svg').first();
  await expect(svg).toBeVisible({timeout:70_000});
  await svg.scrollIntoViewIfNeeded();
  const bounds=await svg.boundingBox();
  expect(bounds).not.toBeNull();
  await page.mouse.move(bounds!.x+bounds!.width*.23,bounds!.y+bounds!.height*.5);
  await expect.poll(()=>cursor.getAttribute('data-route-cursor')).not.toBe('none');
  const before=await cursor.getAttribute('data-route-cursor');
  await page.mouse.move(bounds!.x+bounds!.width*.78,bounds!.y+bounds!.height*.5);
  await expect.poll(async()=>await cursor.getAttribute('data-route-cursor')).not.toBe(before);
  await page.mouse.move(10,10);
  await expect(cursor).toHaveAttribute('data-route-cursor','none');
});

test('header documenti: la ricerca riempie davvero la colonna senza max-width ereditati',async({page})=>{
  for(const path of ['/rifugi/osm-w-39173072/','/route/osm-hiking-13956722/']){
    for(const width of [390,1280,1664]){
      await page.setViewportSize({width,height:900});
      await page.goto(path);
      await expect(page.locator('.site-header .home-search')).toBeVisible({timeout:45_000});
      const layout=await page.evaluate(()=>{
        const hdr=document.querySelector('.site-header')!.getBoundingClientRect();
        const row=document.querySelector('.site-header-row')!.getBoundingClientRect();
        const col=document.querySelector('.site-header-center')!.getBoundingClientRect();
        const input=document.querySelector('.site-header .home-search')! as HTMLElement;
        const rect=input.getBoundingClientRect();
        return {hdr:hdr.width,row:row.width,center:col.width,search:rect.width,max:getComputedStyle(input).maxWidth,
          scroll:document.documentElement.scrollWidth};
      });
      expect(layout.hdr).toBeGreaterThanOrEqual(width-2);
      expect(layout.row).toBeGreaterThanOrEqual(width-2);
      expect(layout.max).toBe('none');
      expect(layout.search).toBeGreaterThan(layout.center-(width<744?3:65));
      expect(layout.scroll).toBeLessThanOrEqual(width+2);
    }
  }
});

test('hero rifugio: emblema dentro la foto e attribuzione leggibile',async({page})=>{
  for(const width of [390,1440]){
    await page.setViewportSize({width,height:900});
    await page.goto('/rifugi/osm-w-39173072/');
    const hero=page.locator('.cb-location-hero-media');
    await expect(hero).toBeVisible({timeout:45_000});
    const logo=hero.locator('.cb-location-avatar');
    const credit=hero.locator('figcaption');
    await expect(logo).toBeVisible();
    const a=await logo.boundingBox(),b=await credit.boundingBox();
    expect(a).not.toBeNull();expect(b).not.toBeNull();
    expect(a!.y+a!.height).toBeLessThan(b!.y);
  }
});


test('catalogo rifugi: filtri quota e posti non allargano il documento',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/#rifugi');
  const altitude=page.getByRole('combobox',{name:'Quota minima'});
  await expect(altitude).toBeVisible({timeout:30000});
  await altitude.selectOption('1500');
  await expect(page.getByRole('button',{name:/Azzera filtri/})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2)).toBe(true);
  await page.getByRole('button',{name:/Azzera filtri/}).click();
  await expect(altitude).toHaveValue('');
});

test('catalogo trekking: navigazione di categoria davvero full-width',async({page})=>{
  for(const width of [390,1024,1440]){
    await page.setViewportSize({width,height:900});
    await page.goto('/#atlante/trekking');
    await expect(page.locator('.cb-browse-bar')).toBeVisible();
    const sizes=await page.evaluate(()=>{
      const nav=document.querySelector('.cb-browse-bar')!.getBoundingClientRect();
      const main=document.querySelector('.cb-atlas-shell')!.getBoundingClientRect();
      return {navLeft:nav.left,navRight:nav.right,mainWidth:main.width,scroll:document.documentElement.scrollWidth};
    });
    expect(sizes.navLeft).toBeGreaterThanOrEqual(-2);
    expect(sizes.navRight).toBeGreaterThanOrEqual(width-2);
    expect(sizes.mainWidth).toBeGreaterThanOrEqual(width-2);
    expect(sizes.scroll).toBeLessThanOrEqual(width+2);
  }
});


test('site chrome: header e footer coprono la viewport, senza max-width ereditati',async({page})=>{
  test.setTimeout(120_000);
  for(const width of [320,390,768,1024,1440]){
    await page.setViewportSize({width,height:900});
    for(const url of ['/','/#rifugi','/route/osm-hiking-13956722/']){
      await page.goto(url);
      await expect(page.locator('.site-header').first()).toBeVisible();
      await expect(page.locator('.site-footer').first()).toBeAttached({timeout:30000});
      const boxes=await page.evaluate(()=>{
        const header=document.querySelector('.site-header')!.getBoundingClientRect();
        const footer=document.querySelector('.site-footer')!.getBoundingClientRect();
        const footerInner=document.querySelector('.site-footer-inner')!.getBoundingClientRect();
        return {
          header:[header.left,header.right],footer:[footer.left,footer.right],
          inner:[footerInner.left,footerInner.right],
          overflow:document.documentElement.scrollWidth,
        };
      });
      for(const [left,right] of [boxes.header,boxes.footer,boxes.inner]){
        expect(left,JSON.stringify({url,width,boxes})).toBeGreaterThanOrEqual(-2);
        expect(right,JSON.stringify({url,width,boxes})).toBeGreaterThanOrEqual(width-2);
      }
      expect(boxes.overflow,JSON.stringify({url,width,boxes})).toBeLessThanOrEqual(width+2);
    }
  }
});

test('dossier: Vai a non cambia il permalink e porta la sezione sotto la testata',async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.setViewportSize({width:390,height:844});
  await page.goto('/#rifugi');
  const first=page.locator('.cb-explore-card-detail').first();
  await expect(first).toBeVisible({timeout:20000});
  await first.click();
  const original=page.url();
  const nav=page.getByRole('navigation',{name:'Naviga questa scheda'});
  await expect(nav.getByRole('button',{name:/Contatti/})).toBeVisible();
  await nav.getByRole('button',{name:/Contatti/}).click();
  expect(page.url()).toBe(original);
  const top=await page.locator('#cb-place-contacts').evaluate(el=>el.getBoundingClientRect().top);
  const header=await page.locator('.site-header').evaluate(el=>el.getBoundingClientRect().bottom);
  expect(top).toBeGreaterThanOrEqual(header-2);
  expect(top).toBeLessThan(header+60);
  await nav.getByRole('button',{name:/Mappa/}).click();
  expect(page.url()).toBe(original);
  const map=await page.locator('#cb-place-map').boundingBox();
  expect(map?.y ?? 0).toBeGreaterThanOrEqual(100);
  expect(map?.y ?? 10000).toBeLessThan(300);
});

test('Font Awesome: simboli inline SVG, nessun emoji di fallback nelle schede',async({page})=>{
  await page.goto('/#rifugi');
  await page.locator('.cb-explore-card-detail').first().click();
  await expect(page.locator('.cb-location-avatar svg.cb-fa-icon')).toBeVisible();
  const links=page.locator('.cb-detail-jump button .cb-fa-icon');
  expect(await links.count()).toBeGreaterThan(3);
  const computed=await links.first().evaluate(el=>({
    viewBox:el.getAttribute('viewBox'),paths:el.querySelectorAll('path').length,
    width:el.getBoundingClientRect().width,
  }));
  expect(computed.paths).toBeGreaterThan(0);
  expect(computed.viewBox).toMatch(/^0 0 /);
  expect(computed.width).toBeGreaterThan(5);
});


test('scheda rifugio: profilo completo CAI, mappa non ridimensionata e sezioni navigabili',async({page})=>{
  test.setTimeout(90_000);
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.setViewportSize({width:390,height:844});
  await page.goto('/#rifugi');
  await expect(page.locator('.cb-explore-card-detail').first()).toBeVisible({timeout:20000});
  await page.locator('.cb-explore-card-detail').first().click();
  await expect(page.locator('.cb-refuge-profile h1')).toBeVisible();
  await expect(page.locator('.cb-refuge-gallery')).toBeVisible();
  await expect(page.locator('#cb-refuge-stay')).toBeVisible();
  await expect(page.locator('#cb-refuge-access')).toBeAttached();
  const original=page.url();
  const nav=page.getByRole('navigation',{name:'Naviga questa scheda'});
  await nav.getByRole('button',{name:/Ospitalità/}).click();
  expect(page.url()).toBe(original);
  const top=await page.locator('#cb-refuge-stay').evaluate(el=>el.getBoundingClientRect().top);
  const header=await page.locator('.site-header').evaluate(el=>el.getBoundingClientRect().bottom);
  expect(top).toBeGreaterThanOrEqual(header-4);
  expect(top).toBeLessThan(header+80);
  for(const width of [320,390,768,1280]){
    await page.setViewportSize({width,height:850});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(width+2);
    const map=await page.locator('.cb-location-sidebar').boundingBox();
    expect(map?.width ?? 0).toBeGreaterThan(width>900?width*.55:width-3);
  }
});

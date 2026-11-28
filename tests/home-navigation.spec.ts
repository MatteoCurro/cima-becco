import { test, expect } from '@playwright/test';

test('Home: i collegamenti principali aprono la categoria giusta',async({page})=>{
  await page.goto('/');
  await expect(page.locator('.cb-hero-v3-directory-link')).toHaveCount(5);
  await page.locator('.cb-hero-v3-directory-link[href="#routes"]').click();
  await expect(page).toHaveURL(/#routes$/);
  await expect(page.locator('.cb-browse-tabs a.is-active')).toHaveText('Sentieri',{timeout:30_000});
  // Switch within the already mounted MapApp: #map must no longer keep routes.
  await page.evaluate(()=>{window.location.hash='#map';});
  await expect(page.locator('.cb-browse-tabs a.is-active')).toHaveText('Cime',{timeout:30_000});
});

test('Home: un click su Cime ignora la precedente modalità Sentieri',async({page})=>{
  await page.addInitScript(()=>sessionStorage.setItem('hillgpx:mode','routes'));
  await page.goto('/');
  await page.locator('.cb-hero-v3-directory-link[href="#map"]').click();
  await expect(page).toHaveURL(/#map$/);
  await expect(page.locator('.cb-browse-tabs a.is-active')).toHaveText('Cime',{timeout:30_000});
});

test('Menu Esplora: chiusura con Escape e clic fuori',async({page})=>{
  await page.goto('/');
  const trigger=page.locator('.cb-explore-trigger');
  const menu=page.locator('#cb-explore-menu');
  await trigger.click();
  await expect(menu).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(menu).toHaveCount(0);
  await trigger.click();
  await expect(menu).toBeVisible();
  await page.locator('.home-main').click({position:{x:8,y:8}});
  await expect(menu).toHaveCount(0);
});

test('Rotellina: scorrimento verticale della pagina e carosello accessibile',async({page})=>{
  await page.setViewportSize({width:1280,height:850});
  await page.goto('/');
  const row=page.locator('.home-row-track').first();
  await expect(row).toBeVisible({timeout:30_000});
  await row.scrollIntoViewIfNeeded();
  await expect(row).toHaveAttribute('role','region');
  const r=await row.boundingBox();
  expect(r).not.toBeNull();
  await page.mouse.move(r!.x+r!.width/2,r!.y+r!.height/2);
  const before=await page.evaluate(()=>window.scrollY);
  await page.mouse.wheel(0,410);
  await expect.poll(()=>page.evaluate(()=>window.scrollY)).toBeGreaterThan(before);
});

test('Ricerca cime: trova una vetta non presente fra le 74 vette in evidenza',async({page})=>{
  await page.goto('/');
  const search=page.getByRole('searchbox',{name:/Cerca una cima, un sentiero/});
  await search.fill('Monte Piana');
  await expect(page.locator('.searchbar-results .result-name').filter({hasText:/^Monte Piana$/}).first())
    .toBeVisible({timeout:30_000});
});


test('Home: focus editoriale stabile nel giorno e senza vette GeoNames legacy',async({page})=>{
  await page.setViewportSize({width:1440,height:900});
  await page.goto('/');
  await expect(page.getByRole('heading',{name:/Cime delle Dolomiti|Le vette più alte/})).toHaveCount(0);
  await expect(page.locator('.cb-home-daily')).toBeVisible({timeout:30_000});
  const title=await page.locator('#cb-home-daily-title').textContent();
  await expect(page.locator('.cb-home-focus-grid .cb-home-focus-card')).toHaveCount(6);
  const links=await page.locator('.cb-home-focus-grid a[href]').evaluateAll(items=>
    items.map(item=>item.getAttribute('href')||''));
  expect(links.some(href=>/\/route\/[^/]+\/$/.test(href))).toBe(true);
  expect(links.some(href=>/\/(comuni|borghi)\/[^/]+\/$/.test(href))).toBe(true);
  expect(links.some(href=>/\/rifugi\/[^/]+\/$/.test(href))).toBe(true);
  expect(links.every(href=>!href.includes('/place/gn'))).toBe(true);
  await page.reload();
  await expect(page.locator('.cb-home-daily')).toBeVisible({timeout:30_000});
  expect(await page.locator('#cb-home-daily-title').textContent()).toBe(title);
  await page.setViewportSize({width:390,height:844});
  await expect(page.locator('.cb-home-focus-grid')).toBeVisible();
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(2);
});

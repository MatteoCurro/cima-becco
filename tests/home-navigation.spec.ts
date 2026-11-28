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

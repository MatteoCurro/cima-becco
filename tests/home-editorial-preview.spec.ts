import { test, expect } from '@playwright/test';

// Questa verifica richiede gli asset generati da npm run build.
test.skip(!process.env.CB_HOME_PREVIEW, 'Richiede preview della build pubblicata');
test('Home: focus editoriale stabile nel giorno e senza vette GeoNames legacy',async({page})=>{
  await page.setViewportSize({width:1440,height:900});
  await page.goto('/');
  await expect(page.getByRole('heading',{name:/Cime delle Dolomiti|Le vette più alte/})).toHaveCount(0);
  await expect(page.locator('.cb-home-daily')).toBeVisible({timeout:30_000});
  const title=await page.locator('#cb-home-daily-title').textContent();
  expect(await page.locator('.cb-home-focus-grid .cb-home-focus-card').count()).toBeGreaterThanOrEqual(5);
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

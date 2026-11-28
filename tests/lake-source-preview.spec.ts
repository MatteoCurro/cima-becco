import {test,expect} from '@playwright/test';

test('sourced lake previews open on direct URL without being a canonical G2 page',async({page,request})=>{
  const r=await request.get('/data/atlas/natural-lake-census-map-v1.json');
  expect(r.ok()).toBeTruthy();
  const data=await r.json();
  expect(data.sourcePreviewsReady).toBeGreaterThan(250);
  const first=data.records.find((x:{previewOnly:boolean;previewSlug:string|null})=>
    x.previewOnly && x.previewSlug);
  expect(first).toBeTruthy();
  await page.goto('/laghi/censiti/'+first.previewSlug+'/');
  await expect(page.getByRole('heading',{name:first.name,exact:true})).toBeVisible();
  await expect(page.getByText('SCHEDA DI CENSIMENTO', {exact:false}).first()).toBeVisible();
  await expect(page.getByText('Quello che sappiamo.')).toBeVisible();
  await expect(page.locator('.cb-atlas-map')).toBeVisible();
  await expect(page.locator('h1')).toHaveCount(1);
  const robots=await request.get('/laghi/censiti/'+first.previewSlug+'/');
  // Dev fallback is SPA; the release build checks static meta robots separately.
  expect(robots.ok()).toBeTruthy();
  await page.setViewportSize({width:375,height:812});
  await expect(page.locator('h1')).toBeVisible();
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(3);
});

test('source index links to a real documentary page; unverified titles never get a permalink',async({page,request})=>{
  const r=await request.get('/data/atlas/natural-lake-census-map-v1.json');
  const data=await r.json();
  const nonames=data.records.filter((x:{previewSlug:string|null})=>!x.previewSlug);
  expect(nonames.length).toBeGreaterThan(0);
  await page.goto('/laghi/');
  const first=page.locator('.cb-lake-source-rows a[href*="/laghi/censiti/"]').first();
  await expect(first).toBeVisible();
  const href=await first.getAttribute('href');
  await first.click();
  await expect(page).toHaveURL(/\/laghi\/censiti\/[a-z0-9-]+\/?$/);
  expect(href).toContain('/laghi/censiti/');
  await expect(page.locator('h1')).toBeVisible();
  expect(data.records.some((x:{name:string|null;previewSlug:string|null})=>
    x.name==='N.D.'&&x.previewSlug)).toBe(false);
});

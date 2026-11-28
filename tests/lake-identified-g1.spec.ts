import {test,expect} from '@playwright/test';

test('un lago G1 con QID e punto GeoNames apre la scheda senza perimetro inventato',async({page,request})=>{
  const response=await request.get('/data/atlas/natural-lake-points-g1-v1.json');
  expect(response.ok()).toBeTruthy();
  const dataset=await response.json();
  expect(dataset.counts.profiles).toBeGreaterThanOrEqual(10);
  expect(dataset.counts.pointOnly).toBeGreaterThanOrEqual(7);
  expect(dataset.counts.withVerifiedP18).toBeGreaterThanOrEqual(3);
  const entry=dataset.entities.find((x:{geo:{area:unknown}})=>x.geo.area===null);
  expect(entry).toBeTruthy();
  await page.goto('/laghi/identificati/'+entry.slug+'/');
  await expect(page.getByRole('heading',{name:entry.name,exact:true}).first()).toBeVisible();
  await expect(page.getByText('IDENTIFICATO · G1', {exact:false}).first()).toBeVisible();
  await expect(page.getByText('Non ancora disponibile: la mappa mostra solo il punto geografico')).toBeVisible();
  await expect(page.locator('h1')).toHaveCount(1);
  await expect(page.locator('[aria-label*="Mappa topografica"]')).toBeVisible();
  await page.setViewportSize({width:375,height:812});
  await expect(page.getByRole('heading',{name:entry.name,exact:true}).first()).toBeVisible();
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(3);
});

test('P18 verificata compare solo nella scheda G1 del giusto lago',async({page,request})=>{
  const data=await (await request.get('/data/atlas/natural-lake-points-g1-v1.json')).json();
  const withPhoto=data.entities.find((x:{media:unknown[]})=>x.media.length>0);
  expect(withPhoto).toBeTruthy();
  await page.goto('/laghi/identificati/'+withPhoto.slug+'/');
  await expect(page.locator('.cb-location-hero-media img')).toHaveAttribute('src',withPhoto.media[0].url);
  await expect(page.getByText('LAGO IDENTIFICATO · G1', {exact:false}).first()).toBeVisible();
  const noPhoto=data.entities.find((x:{media:unknown[]})=>x.media.length===0);
  expect(noPhoto).toBeTruthy();
  await page.goto('/laghi/identificati/'+noPhoto.slug+'/');
  await expect(page.locator('.cb-location-hero-media img')).toHaveCount(0);
});

test('la lista laghi include G1 ma non confonde i due dossier G2',async({page,request})=>{
  const data=await (await request.get('/data/atlas/natural-lake-points-g1-v1.json')).json();
  await page.goto('/laghi/');
  await expect(page.getByRole('heading',{name:'UN NOME, UNA POSIZIONE, UNA STORIA DA COMPLETARE.'})).toBeVisible();
  const links=page.locator('.cb-lake-g1-grid a[href*="/laghi/identificati/"]');
  await expect(links).toHaveCount(data.counts.profiles);
  await expect(page.locator('.cb-lake-g1-grid a[href$="/lago-sorapis/"]')).toHaveCount(0);
  await expect(page.locator('.cb-lake-g1-grid a[href$="/lago-di-landro/"]')).toHaveCount(0);
});

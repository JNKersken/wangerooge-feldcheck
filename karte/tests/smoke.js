// Smoke test of the built web app in a real browser (CI): starts, no script errors, main paths work.
// Usage: node karte/tests/smoke.js [url]   (repo root served, e.g. python3 -m http.server 8000)
const { chromium } = require('playwright');
const URL_ = process.argv[2] || 'http://127.0.0.1:8000/index.html';
(async () => {
  const b = await chromium.launch(process.env.CHROMIUM ? {executablePath: process.env.CHROMIUM} : {});
  const ctx = await b.newContext({viewport: {width: 390, height: 844}, deviceScaleFactor: 2, permissions: ['geolocation'],
    geolocation: {latitude: 53.7907, longitude: 7.8693, accuracy: 6}});
  const p = await ctx.newPage(); const errs = []; let fails = 0;
  p.on('pageerror', (e) => errs.push(e.message));
  await ctx.route('https://api.github.com/**', (r) => r.fulfill({status: 201, body: '{}'}));   // never send anything for real
  p.setDefaultTimeout(15000);
  const ok = (c, m) => { console.log((c ? 'OK   ' : 'FAIL ') + m); if (!c) fails++; };
  const step = async (m, fn) => { try { await fn(); } catch (e) { ok(false, `${m}: ${e.message.split('\n')[0]}`); } };
  await step('Start', async () => {
    await p.goto(URL_); await p.waitForSelector('.tour', {timeout: 8000});
    ok(true, 'App startet, Einführung erscheint');
    await p.keyboard.press('Escape'); ok(!(await p.$('.tour')), 'Escape schließt die Einführung');
    ok(await p.evaluate(() => document.querySelectorAll('.leaflet-tile-loaded').length > 0), 'Kartenkacheln geladen');
  });
  await step('Prüfen', async () => {
    await p.click('#bNext'); await p.waitForSelector('#vOk');
    ok((await p.textContent('#sheet h2')).trim().length > 0, 'Nächstes offenes Objekt mit Titel');
    await p.click('#vOk'); ok((await p.textContent('#badge')) === '1', 'Bewertung gespeichert, Zähler am Menü');
    await p.click('#vUndo'); ok(await p.isHidden('#badge'), 'Rücknahme');
    await p.click('#vClose');
  });
  await step('Liste', async () => {
    await p.click('#btnList'); await p.waitForSelector('#listPanel .li');
    ok(await p.evaluate(() => document.querySelectorAll('#listPanel .li').length) > 50, 'Liste der offenen Objekte');
    await p.keyboard.press('Escape');
  });
  await step('Menü', async () => {
    await p.click('#btnMenu'); await p.waitForSelector('#menuPanel .grp');
    ok(/Version \d/.test(await p.textContent('#menuPanel')), 'Menü mit Version');
  });
  await step('PDF', async () => {
    await p.click('#bPdf'); await p.waitForSelector('#pv svg', {timeout: 30000});
    ok(true, 'PDF-Vorschau lädt Kartenblatt');
    await p.click('#pdfClose');
  });
  await step('GPS', async () => {
    await p.click('#btnGps'); await p.waitForFunction(() => document.getElementById('btnGps').dataset.st === 'on', null, {timeout: 10000});
    ok(true, 'GPS-Position kommt an');
  });
  await step('Offline', async () => {
    await p.reload(); await p.waitForTimeout(1500);
    ok(await p.evaluate(async () => !!(await navigator.serviceWorker.getRegistration())), 'Service Worker registriert');
  });
  ok(!errs.length, 'keine Skriptfehler' + (errs.length ? ': ' + errs.join(' | ') : ''));
  await b.close(); process.exit(fails ? 1 : 0);
})();

'use strict';
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const variants = ['baseline', 'double-submit', 'composition-unchecked', 'error-clears', 'error-unassociated', 'stale-applies', 'focus-leak', 'restore-lost', 'cache-unscoped', 'plural-wrong'];
const files = new Map([['/', ['index.html', 'text/html; charset=utf-8']], ['/app.js', ['app.js', 'text/javascript; charset=utf-8']]]);
async function main() {
  const playwright = require(process.argv[2]);
  const server = http.createServer((request, response) => {
    const url = new URL(request.url, 'http://127.0.0.1');
    const file = files.get(url.pathname);
    if (!file) { response.writeHead(404); response.end(); return; }
    response.writeHead(200, {'Content-Type': file[1], 'Cache-Control': 'no-store'});
    response.end(fs.readFileSync(path.join(__dirname, file[0])));
  });
  let browser;
  const output = {protocol_version: 1, stack: 'real-browser', variants: [], at: 'NOT_VERIFIED', operating_system_ime: 'NOT_VERIFIED'};
  try {
    await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
    const origin = 'http://127.0.0.1:' + server.address().port;
    const options = {headless: true, timeout: 20000};
    if (process.argv[3] !== 'bundled') options.channel = process.argv[3];
    browser = await playwright.chromium.launch(options);
    output.browser_version = browser.version();
    output.playwright_version = require(path.join(process.argv[2], 'package.json')).version;
    output.channel = process.argv[3];
    for (const variant of variants) {
      const context = await browser.newContext({serviceWorkers: 'block', locale: 'en-US'});
      const forbidden = [];
      await context.route('**/*', route => {
        if (new URL(route.request().url()).origin === origin) return route.continue();
        forbidden.push(route.request().url()); return route.abort();
      });
      const page = await context.newPage(); page.setDefaultTimeout(4000);
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      const row = {variant, checks: [], errors};
      const visit = () => page.goto(origin + '/?variant=' + variant, {waitUntil: 'load'});
      const check = (id, passed, observed) => row.checks.push({id, status: passed ? 'PASSED' : 'FAILED', observed});
      try {
        await visit();
        await page.locator('#draft').fill('draft text'); await page.locator('#draft').press('Enter');
        const enter = await page.evaluate(() => fixture.actions);
        await page.locator('#submit').click(); const click = await page.evaluate(() => fixture.actions);
        check('single_enter_and_click', enter === 1 && click === 2, {enter, afterClick: click});
        await visit(); await page.locator('#draft').focus();
        await page.locator('#draft').dispatchEvent('compositionstart', {data: '文'});
        await page.keyboard.press('Enter'); const during = await page.evaluate(() => fixture.actions);
        await page.locator('#draft').dispatchEvent('compositionend', {data: '文'});
        await page.keyboard.press('Enter'); const after = await page.evaluate(() => fixture.actions);
        check('composition_guard', during === 0 && after === 1, {during, after, syntheticComposition: true});
        await visit(); await page.locator('#draft').fill('retain me');
        await page.evaluate(() => fixture.fail());
        const error = await page.evaluate(() => ({value: document.getElementById('draft').value, focus: document.activeElement.id, invalid: document.getElementById('draft').getAttribute('aria-invalid'), described: document.getElementById('draft').getAttribute('aria-describedby'), message: document.getElementById('error').textContent}));
        check('error_preserves_draft_focus', error.value === 'retain me' && error.focus === 'draft', error);
        const aria = await page.locator('body').ariaSnapshot();
        check('error_associated', error.invalid === 'true' && error.described === 'error' && error.message.length > 0 && aria.includes('textbox "Draft"') && aria.includes('alert'), {error, aria});
        await visit(); await page.locator('#draft').fill('new screen draft');
        await page.evaluate(async () => { fixture.pending(); fixture.navigate(); fixture.finishOld(); await Promise.resolve(); });
        const stale = await page.evaluate(() => ({status: document.getElementById('status').textContent, value: document.getElementById('draft').value}));
        check('stale_navigation_rejected', stale.status === 'new-screen' && stale.value === 'new screen draft', stale);
        await visit(); await page.locator('#open').click(); await page.locator('#dialogField').focus();
        await page.keyboard.press('Tab'); const tab = await page.evaluate(() => document.activeElement.id);
        await page.keyboard.press('Shift+Tab'); const reverse = await page.evaluate(() => document.activeElement.id);
        check('dialog_keyboard_trapped', tab === 'close' && reverse === 'dialogField', {tab, reverse});
        await visit(); await page.locator('#open').click();
        await page.evaluate(() => document.getElementById('open').remove()); await page.keyboard.press('Escape');
        const restore = await page.evaluate(() => ({hidden: document.getElementById('dialog').hidden, focus: document.activeElement.id, log: fixture.focusLog}));
        check('escape_restores_mounted_fallback', restore.hidden && restore.focus === 'heading', restore);
        await visit();
        const locale = await page.evaluate(() => { fixture.render('tenant-A', 'en', 1); return fixture.render('tenant-B', 'ar', 2); });
        check('tenant_locale_cache_separated', locale.tenant === 'tenant-B' && locale.locale === 'ar' && locale.direction === 'rtl', locale);
        await visit(); const plural = await page.evaluate(() => fixture.render('tenant-B', 'ar', 2));
        check('plural_rtl_timezone', plural.text === 'عنصران' && plural.direction === 'rtl' && /[٠۰0]?[٣۳3]/.test(plural.date), plural);
        check('no_runtime_errors_or_external_requests', errors.length === 0 && forbidden.length === 0, {errors, blockedRequests: forbidden.length});
      } catch (error) { row.infrastructure_error = error.name + ': ' + error.message; }
      finally { await context.close(); }
      output.variants.push(row);
    }
  } catch (error) { output.infrastructure_error = error.name + ': ' + error.message; process.exitCode = 2; }
  finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
  console.log(JSON.stringify(output));
}
main().catch(error => { console.log(JSON.stringify({infrastructure_error: error.message})); process.exitCode = 2; });

const {test, before, after} = require('node:test');
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const path = require('node:path');
const {chromium} = require('playwright');
let browser;
const servers = [];
async function serve(disabled = false) {
  const child = spawn(process.env.PYTHON || 'python', ['-B', '-m', 'tests.ui.serve_landing'], {
    cwd: path.resolve(__dirname, '../..'),
    env: {...process.env, ...(disabled ? {SCOP_NO_SIGNUPS:'1'} : {})}
  });
  servers.push(child);
  return new Promise((resolve, reject) => {
    child.stdout.once('data', data => resolve(data.toString().trim()));
    child.once('error', reject);
    child.once('exit', code => reject(new Error('Preview exited ' + code)));
  });
}
before(async () => {
  browser = await chromium.launch({headless:true, executablePath:process.env.SCOP_CHROMIUM || undefined});
});
after(async () => {
  await browser?.close();
  servers.forEach(child => child.kill());
});

test('responsive original hero, keyboard navigation, actual signup and failure state', async () => {
  const origin = await serve();
  const page = await browser.newPage();
  const external = [];
  page.on('request', request => { if (!request.url().startsWith(origin)) external.push(request.url()); });
  await page.goto(origin);
  await page.keyboard.press('Tab');
  assert.ok(await page.getByRole('link', {name:'Skip to content'}).evaluate(node => node === document.activeElement));
  assert.match(await page.locator('h1').innerText(), /One ecosystem/);
  await page.locator('h1').click();
  for (const [width,height,label] of [[1440,1000,'desktop'],[1024,900,'small-desktop'],[768,1024,'tablet'],[390,844,'mobile']]) {
    await page.setViewportSize({width,height});
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({path:`/tmp/scop-landing-${label}.png`, fullPage:true});
  }
  assert.equal(external.length, 0);
  await page.locator('#submit').click();
  assert.match(await page.locator('#email-error').innerText(), /valid email/);
  assert.ok(await page.locator('#email').evaluate(node => node === document.activeElement));
  await page.locator('#email').fill('tester@example.com');
  await page.locator('#tool').fill('Test tool');
  await page.locator('#problem').fill('Reviewing generated code takes time.');
  await page.locator('#submit').click();
  assert.match(await page.locator('#consent-error').innerText(), /consent/);
  await page.locator('#consent').check();
  const saved = page.waitForResponse(response => response.url().endsWith('/api/signup'));
  await page.locator('#submit').click();
  assert.equal((await saved).status(), 201);
  await page.getByText('Your interest has been saved. Thank you for helping shape SCOP.', {exact:true}).waitFor();
  await page.locator('#email').fill('tester@example.com');
  await page.locator('#tool').fill('Test tool');
  await page.locator('#problem').fill('Another test response.');
  await page.locator('#consent').check();
  await page.route('**/api/signup', route => route.fulfill({status:503,contentType:'application/json',body:'{"error":"unavailable"}'}));
  await page.locator('#submit').click();
  await page.getByText(/We could not confirm your submission/).waitFor();
  await page.close();
});

test('unconfigured signup storage disables collection honestly', async () => {
  const page = await browser.newPage();
  await page.goto(await serve(true));
  assert.ok(await page.locator('#submit').isDisabled());
  assert.match(await page.locator('#form-status').innerText(), /unavailable/);
  await page.close();
});


test('scroll depth changes on desktop and resets for reduced motion and mobile', async () => {
  const page = await browser.newPage({viewport:{width:1440,height:1000}, reducedMotion:'no-preference'});
  await page.goto(await serve());
  assert.ok(await page.evaluate(async () => {
    const image = new Image();
    image.src = '/assets/hero.webp';
    await image.decode();
    return image.naturalWidth === 1672 && image.naturalHeight === 941;
  }));
  await page.mouse.move(1100, 180);
  await page.waitForFunction(() => document.querySelector('.hero-art').style.transform.includes('translate3d('));
  const before = await page.locator('.hero-art').evaluate(node => getComputedStyle(node).transform);
  await page.evaluate(() => scrollTo(0, 350));
  await page.waitForFunction(value => getComputedStyle(document.querySelector('.hero-art')).transform !== value, before);
  for (const layer of ['.hero-art', '.hero-depth', '.hero-content']) {
    assert.notEqual(await page.locator(layer).evaluate(node => getComputedStyle(node).transform), 'none');
  }
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.waitForFunction(() => getComputedStyle(document.querySelector('.hero-art')).transform === 'none');
  await page.evaluate(() => scrollTo(0, 500));
  assert.equal(await page.locator('.hero-content').evaluate(node => getComputedStyle(node).transform), 'none');
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.setViewportSize({width:390,height:844});
  await page.waitForFunction(() => getComputedStyle(document.querySelector('.hero-art')).transform === 'none');
  const colors = await page.locator('body *').evaluateAll(nodes => nodes.flatMap(node => {
    const css = getComputedStyle(node);
    return [css.color, css.backgroundColor, css.borderTopColor];
  }));
  assert.ok(colors.every(color => {
    const channels = color.match(/\d+/g);
    if (!channels) return true;
    const rgb = channels.slice(0,3).map(Number);
    return Math.max(...rgb) - Math.min(...rgb) < 35 || (rgb[2] >= rgb[1] && rgb[1] >= rgb[0] && rgb[2] <= 110);
  }));
  await page.close();
});

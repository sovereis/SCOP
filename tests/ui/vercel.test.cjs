const {test} = require('node:test');
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const path = require('node:path');
const {chromium} = require('playwright');

test('production bootstrap, same-origin routes and unavailable database UI', async () => {
  const browser = await chromium.launch({headless:true, executablePath:process.env.SCOP_CHROMIUM || undefined});
  try {
    for (const disabled of [false,true]) {
      const child = spawn(process.env.PYTHON || 'python',['-B','-m','tests.ui.serve_vercel'], {
        cwd:path.resolve(__dirname,'../..'),env:{...process.env,...(disabled?{SCOP_NO_PRODUCTION_STORE:'1'}:{})}});
      const page = await browser.newPage();
      try {
        const origin = await new Promise((resolve,reject)=>{
          child.stdout.once('data',data=>resolve(data.toString().trim()));
          child.once('error',reject);
          child.once('exit',code=>reject(new Error('Server exited '+code)));
        });
        await page.goto(origin);
        assert.equal((await page.request.get(origin+'/assets/hero.webp')).status(),200);
        assert.equal((await page.request.get(origin+'/server/scop_workspace.py')).status(),404);
        if (disabled) {
          await page.getByText('Signups are unavailable. Please try again later.',{exact:true}).waitFor();
          assert.ok(await page.locator('#submit').isDisabled());
        } else {
          await page.waitForFunction(()=>!document.querySelector('#submit').disabled);
          await page.locator('#email').fill('test@example.com');
          await page.locator('#tool').fill('test tool');
          await page.locator('#problem').fill('test challenge');
          await page.locator('#consent').check();
          await page.locator('#submit').click();
          await page.getByText('Your interest has been saved. Thank you for helping shape SCOP.',{exact:true}).waitFor();
        }
      } finally {await page.close();child.kill();}
    }
  } finally {await browser.close();}
});

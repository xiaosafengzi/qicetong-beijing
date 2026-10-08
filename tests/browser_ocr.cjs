/* Optional real-OCR browser smoke test against an isolated QCT_TEST_URL server. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const fixture = await browser.newPage({ viewport: { width: 1450, height: 240 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await fixture.setContent('<div style="font:64px Microsoft YaHei;background:white;padding:40px;color:black">职工总数: 80, 人, 2025</div>');
    const picture = await fixture.locator('div').screenshot();
    await page.goto(process.env.QCT_TEST_URL || 'http://127.0.0.1:8879');
    await page.getByRole('link', { name: '政策与材料', exact: true }).click();
    await page.locator('#asset-file').setInputFiles({ name: '模拟人员记录.png', mimeType: 'image/png', buffer: picture });
    await page.getByRole('button', { name: '本地 OCR 识别' }).click();
    await page.locator('#visual-verified').waitFor({ timeout: 60000 });
    assert((await page.locator('#dialog').innerText()).includes('职工总数'));
    assert(await page.getByRole('button', { name: '确认候选', exact: true }).count() > 0);
    await page.getByRole('button', { name: '确认候选', exact: true }).first().click();
    assert((await page.locator('#toast').innerText()).includes('对照原图'));
    await page.locator('#visual-verified').check();
    await page.getByRole('button', { name: '确认候选', exact: true }).first().click();
    await page.locator('#dialog .badge.pass').filter({ hasText: '已确认' }).first().waitFor();
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ passed: true, flow: '图片上传→真实本地 OCR→人工核对后确认', console_errors: errors }));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });

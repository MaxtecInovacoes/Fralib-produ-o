const { chromium } = require('playwright');
(async() => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1400 } });
  await page.goto('https://app.seunegociofralib.site/sites/2/start-academia-6ee318c7/', { waitUntil: 'networkidle', timeout: 120000 });
  await page.screenshot({ path: 'C:/fralib/reports/visual-validation/start-academia-job574-top.png' });
  const text = await page.evaluate(() => document.body.innerText.slice(0, 1400));
  console.log(text);
  await browser.close();
})();

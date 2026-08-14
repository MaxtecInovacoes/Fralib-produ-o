const { chromium } = require('playwright');
(async() => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1400 } });
  await page.goto('https://app.seunegociofralib.site/sites/2/start-academia-6ee318c7/', { waitUntil: 'networkidle', timeout: 120000 });
  await page.screenshot({ path: 'C:/fralib/reports/visual-validation/start-academia-job571-viewport-top.png' });
  await page.evaluate(() => window.scrollTo(0, 2200));
  await page.waitForTimeout(800);
  await page.screenshot({ path: 'C:/fralib/reports/visual-validation/start-academia-job571-mid.png' });
  await browser.close();
})();

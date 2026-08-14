const { chromium } = require('playwright');
(async() => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 4800 }, deviceScaleFactor: 1 });
  const url = 'https://app.seunegociofralib.site/sites/2/start-academia-6ee318c7/';
  await page.goto(url, { waitUntil: 'networkidle', timeout: 120000 });
  await page.screenshot({ path: 'C:/fralib/reports/visual-validation/start-academia-job571-desktop.png', fullPage: true });
  const metrics = await page.evaluate(() => {
    const h2 = [...document.querySelectorAll('h2')].find(el => el.textContent && el.textContent.includes('A academia que Campina Grande do Sul precisava'));
    const anchor = h2 ? h2.closest('a') : null;
    const section = h2 ? h2.closest('section') : null;
    return {
      title: document.title,
      sectionCount: document.querySelectorAll('section').length,
      imgCount: document.querySelectorAll('img').length,
      h1Count: document.querySelectorAll('h1').length,
      h2Rect: h2 ? h2.getBoundingClientRect().toJSON() : null,
      anchorRect: anchor ? anchor.getBoundingClientRect().toJSON() : null,
      anchorTag: anchor ? anchor.tagName : null,
      sectionRect: section ? section.getBoundingClientRect().toJSON() : null,
      bodyTextSample: document.body.innerText.slice(0, 400),
    };
  });
  console.log(JSON.stringify(metrics, null, 2));
  await browser.close();
})();

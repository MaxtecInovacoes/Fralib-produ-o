const { chromium } = require('playwright');
(async() => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 2200 } });
  await page.goto('https://app.seunegociofralib.site/sites/2/start-academia-6ee318c7/', { waitUntil: 'networkidle', timeout: 120000 });
  const metrics = await page.evaluate(() => {
    const body = document.body;
    const html = document.documentElement;
    const main = document.querySelector('main');
    const firstSection = document.querySelector('section');
    const styles = (el) => el ? getComputedStyle(el) : null;
    const rootVars = styles(html);
    return {
      innerWidth: window.innerWidth,
      devicePixelRatio: window.devicePixelRatio,
      bodyRect: body.getBoundingClientRect().toJSON(),
      htmlRect: html.getBoundingClientRect().toJSON(),
      mainRect: main ? main.getBoundingClientRect().toJSON() : null,
      firstSectionRect: firstSection ? firstSection.getBoundingClientRect().toJSON() : null,
      bodyStyle: {
        zoom: styles(body).zoom,
        transform: styles(body).transform,
        scale: styles(body).scale,
        width: styles(body).width,
        maxWidth: styles(body).maxWidth,
        display: styles(body).display,
      },
      htmlStyle: {
        zoom: styles(html).zoom,
        transform: styles(html).transform,
        fontSize: styles(html).fontSize,
      },
      mainStyle: main ? {
        transform: styles(main).transform,
        zoom: styles(main).zoom,
        width: styles(main).width,
        maxWidth: styles(main).maxWidth,
      } : null,
      offending: [...document.querySelectorAll('*')].map(el => ({
        tag: el.tagName,
        cls: el.className,
        style: el.getAttribute('style') || '',
        transform: styles(el).transform,
        zoom: styles(el).zoom,
        width: styles(el).width,
        rect: el.getBoundingClientRect().toJSON()
      })).filter(x => x.transform !== 'none' || (x.zoom && x.zoom !== '1')).slice(0, 80)
    };
  });
  console.log(JSON.stringify(metrics, null, 2));
  await browser.close();
})();

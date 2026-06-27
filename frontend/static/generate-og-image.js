const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function generateOGImage() {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();

  // Set viewport size to match OG image dimensions
  await page.setViewport({
    width: 1200,
    height: 630,
    deviceScaleFactor: 1
  });

  // Load the HTML template
  const htmlPath = path.join(__dirname, 'og-image.html');
  const html = fs.readFileSync(htmlPath, 'utf8');

  // Set HTML content
  await page.setContent(html, {
    waitUntil: 'networkidle0'
  });

  // Wait for fonts to load
  await page.waitForTimeout(2000);

  // Take screenshot
  await page.screenshot({
    path: path.join(__dirname, 'og-image.png'),
    type: 'png',
    quality: 100
  });

  await browser.close();

  console.log('✅ OG image generated successfully: og-image.png');
}

generateOGImage().catch(console.error);
#!/usr/bin/env node
/**
 * Playwright Accessibility Tree Capturer
 * URL을 받아서 headless Chromium으로 접속 → accessibility snapshot → JSON stdout
 *
 * Usage: node capture-a11y.js <url> [timeout_ms]
 */
const { chromium } = require('playwright');

const url = process.argv[2];
const timeout = parseInt(process.argv[3] || '30000');

if (!url) {
  console.error('Usage: node capture-a11y.js <url> [timeout_ms]');
  process.exit(1);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout });
    await page.waitForTimeout(2000);  // JS 렌더링 대기

    const snapshot = await page.locator(':root').ariaSnapshot();
    console.log(snapshot);
  } catch (e) {
    console.error('CAPTURE_ERROR:', e.message);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();

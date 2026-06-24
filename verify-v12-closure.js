const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  console.log('Step 1: Navigate to home page');
  await page.goto('http://localhost:5173');
  await page.screenshot({ path: '01-homepage.png', fullPage: true });

  console.log('Step 2: Check if logged in, if not login');
  const loginButton = await page.locator('text=/登录|立即开始/').first();
  if (await loginButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    await loginButton.click();
    await page.waitForURL('**/login', { timeout: 5000 });
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'password123');
    await page.locator('button:has-text("登录")').click();
    await page.waitForURL('**/workspace', { timeout: 5000 });
    await page.screenshot({ path: '02-workspace.png', fullPage: true });
  }

  console.log('Step 3: Navigate to workspace');
  if (!page.url().includes('/workspace')) {
    await page.goto('http://localhost:5173/workspace');
    await page.waitForTimeout(1000);
  }

  console.log('Step 4: Find contract');
  await page.waitForTimeout(2000);
  const contracts = await page.locator('button, a, div').filter({ hasText: /合同|Contract/i }).all();
  if (contracts.length === 0) {
    console.log('❌ No contracts found');
    await page.screenshot({ path: '03-no-contracts.png', fullPage: true });
    await browser.close();
    return;
  }

  await contracts[0].click();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '04-contract-detail.png', fullPage: true });

  console.log('Step 5: Look for draft button');
  await page.waitForTimeout(1000);
  const draftButton = await page.locator('button').filter({ hasText: /整理草稿|进入草稿|草稿/i }).first();
  const draftVisible = await draftButton.isVisible({ timeout: 3000 }).catch(() => false);

  if (draftVisible) {
    console.log('✅ Found draft button');
    await draftButton.click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: '07-edit-mode.png', fullPage: true });

    const reReviewBtn = await page.locator('button').filter({ hasText: /重新审查/i }).first();
    const reReviewVisible = await reReviewBtn.isVisible({ timeout: 2000 }).catch(() => false);
    if (reReviewVisible) {
      const isDisabled = await reReviewBtn.isDisabled().catch(() => true);
      console.log(isDisabled ? '❌ Re-review disabled' : '✅ Re-review enabled');
    }
  } else {
    console.log('⚠️ Draft button not found');
  }

  await page.waitForTimeout(2000);
  await page.screenshot({ path: '11-final.png', fullPage: true });
  console.log('Done');
  await browser.close();
})();

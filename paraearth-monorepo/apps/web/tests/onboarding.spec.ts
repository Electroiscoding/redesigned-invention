import { test, expect } from '@playwright/test';

test.describe('ParaEarth Onboarding Flow', () => {
  test('should securely submit API key, route to config, and launch simulation', async ({ page }) => {
    // 1. Visit the Vault Page
    await page.goto('http://localhost:3001/vault');
    await expect(page.locator('h2')).toHaveText('ParaEarth Vault');

    // 2. Submit Mock OpenRouter API Key
    const keyInput = page.locator('input#apiKey');
    await keyInput.fill('sk-or-v1-mock-test-key-123');

    // Intercept the API call to avoid needing the real backend running
    await page.route('**/api/session', async (route) => {
      const json = { success: true, token: 'mock-proxy-token', message: 'Secured.' };
      await route.fulfill({ json });
    });

    await page.locator('button[type="submit"]').click();

    // 3. Should route to Config Page
    await page.waitForURL('**/config');
    await expect(page.locator('h1')).toHaveText('Configure World');

    // 4. Check that Proxy Token was set in Session Storage
    const proxyToken = await page.evaluate(() => sessionStorage.getItem('proxy-token'));
    expect(proxyToken).toBe('mock-proxy-token');

    // 5. Select preset and population, then launch
    await page.locator('select#preset').selectOption('ocean-world');

    // Update the slider (simulate dragging)
    const populationSlider = page.locator('input#population');
    await populationSlider.fill('500');

    await page.locator('button').click();

    // 6. Verify routing to the Observer Mode simulation
    await page.waitForURL('**/observer');
    await expect(page.locator('h2')).toContainText('ParaEarth / O-Mode');
  });
});
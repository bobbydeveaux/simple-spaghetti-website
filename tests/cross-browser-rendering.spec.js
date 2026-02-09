// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Cross-browser rendering tests for Simple Bolognese Website
 * Tests based on LLD Section 9 E2E test specifications
 */

test.describe('Cross-Browser Rendering Tests', () => {

  test.beforeEach(async ({ page }) => {
    // Navigate to the main page before each test
    await page.goto('/');
  });

  test('page loads successfully with correct title', async ({ page }) => {
    // Test Case: Page title verification
    await expect(page).toHaveTitle('Test Pizza Page');

    // Verify URL is correct
    expect(page.url()).toContain('localhost:8000');
  });

  test('displays correct content text', async ({ page }) => {
    // Test Case: Body text content verification
    const bodyText = await page.locator('body').textContent();
    expect(bodyText).toContain('I love pizza');

    // Ensure the exact text is present and visible
    const pizzaText = page.getByText('I love pizza');
    await expect(pizzaText).toBeVisible();
  });

  test('applies correct CSS styling - body background', async ({ page }) => {
    // Test Case: CSS rendering verification - body background
    const body = page.locator('body');

    // Check computed styles
    const backgroundColor = await body.evaluate((element) => {
      return window.getComputedStyle(element).backgroundColor;
    });

    // Verify red background (accepts different red formats)
    expect(
      backgroundColor === 'red' ||
      backgroundColor === 'rgb(255, 0, 0)' ||
      backgroundColor.includes('255, 0, 0')
    ).toBeTruthy();
  });

  test('applies correct CSS styling - footer background', async ({ page }) => {
    // Test Case: CSS rendering verification - footer background
    const footer = page.locator('footer');

    // Ensure footer exists
    await expect(footer).toBeVisible();

    // Check footer background color
    const footerBackgroundColor = await footer.evaluate((element) => {
      return window.getComputedStyle(element).backgroundColor;
    });

    // Verify blue background (accepts different blue formats)
    expect(
      footerBackgroundColor === 'blue' ||
      footerBackgroundColor === 'rgb(0, 0, 255)' ||
      footerBackgroundColor.includes('0, 0, 255')
    ).toBeTruthy();
  });

  test('has valid HTML structure', async ({ page }) => {
    // Test Case: HTML structure validation

    // Check for proper HTML5 doctype
    const doctype = await page.evaluate(() => {
      return document.doctype.name;
    });
    expect(doctype).toBe('html');

    // Verify essential HTML elements exist
    await expect(page.locator('html')).toBeVisible();
    await expect(page.locator('head')).toHaveCount(1);
    await expect(page.locator('body')).toBeVisible();
    await expect(page.locator('title')).toHaveCount(1);
    await expect(page.locator('footer')).toBeVisible();
  });

  test('has no JavaScript errors in console', async ({ page }) => {
    // Test Case: Console error checking
    const consoleErrors = [];

    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Let page fully load
    await page.waitForLoadState('networkidle');

    // Verify no console errors occurred
    expect(consoleErrors).toHaveLength(0);
  });

  test('loads with minimal network requests', async ({ page }) => {
    // Test Case: Network request verification
    const requests = [];

    page.on('request', request => {
      requests.push(request.url());
    });

    await page.waitForLoadState('networkidle');

    // Should only have one request (the HTML file)
    expect(requests.length).toBeLessThanOrEqual(2); // HTML + potential favicon
    expect(requests[0]).toContain('localhost:8000');
  });

  test('content is accessible and readable', async ({ page }) => {
    // Test Case: Basic accessibility verification

    // Check that main text is accessible
    const pizzaText = page.getByText('I love pizza');
    await expect(pizzaText).toBeVisible();

    // Verify text is not hidden or transparent
    const textColor = await pizzaText.evaluate((element) => {
      const styles = window.getComputedStyle(element);
      return {
        color: styles.color,
        opacity: styles.opacity,
        visibility: styles.visibility,
        display: styles.display
      };
    });

    expect(textColor.visibility).not.toBe('hidden');
    expect(textColor.display).not.toBe('none');
    expect(textColor.opacity).not.toBe('0');
  });

  test('renders consistently across viewport sizes', async ({ page }) => {
    // Test Case: Responsive behavior verification

    // Test desktop size
    await page.setViewportSize({ width: 1200, height: 800 });
    await expect(page.getByText('I love pizza')).toBeVisible();

    // Test tablet size
    await page.setViewportSize({ width: 768, height: 1024 });
    await expect(page.getByText('I love pizza')).toBeVisible();

    // Test mobile size
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.getByText('I love pizza')).toBeVisible();

    // Content should remain visible across all sizes
  });

  test('page loads within performance targets', async ({ page }) => {
    // Test Case: Performance verification

    const startTime = Date.now();
    await page.waitForLoadState('networkidle');
    const loadTime = Date.now() - startTime;

    // Should load within 2 seconds (very generous for such a simple page)
    expect(loadTime).toBeLessThan(2000);

    // Check page size is reasonable
    const response = await page.goto('/');
    const contentLength = response.headers()['content-length'];
    if (contentLength) {
      expect(parseInt(contentLength)).toBeLessThan(1024); // Under 1KB
    }
  });

  test('browser-specific rendering differences are acceptable', async ({ page, browserName }) => {
    // Test Case: Cross-browser rendering tolerance

    // All browsers should display the same content
    await expect(page.getByText('I love pizza')).toBeVisible();

    // Document basic rendering info for comparison
    const renderingInfo = await page.evaluate((browser) => {
      const body = document.body;
      const computedStyle = window.getComputedStyle(body);

      return {
        browser: browser,
        fontFamily: computedStyle.fontFamily,
        fontSize: computedStyle.fontSize,
        backgroundColor: computedStyle.backgroundColor,
        userAgent: navigator.userAgent.split(' ').slice(0, 3).join(' ') // Simplified UA
      };
    }, browserName);

    console.log(`Rendering info for ${browserName}:`, renderingInfo);

    // Key elements should be present regardless of browser
    await expect(page.locator('body')).toHaveCSS('background-color', /red|rgb\(255,\s*0,\s*0\)/);
    await expect(page.locator('footer')).toHaveCSS('background-color', /blue|rgb\(0,\s*0,\s*255\)/);
  });
});
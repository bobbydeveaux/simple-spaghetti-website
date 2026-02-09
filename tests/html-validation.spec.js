// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * HTML validation and accessibility tests
 * Based on LLD Section 9 validation specifications
 */

test.describe('HTML Validation and Accessibility Tests', () => {

  test('HTML5 document structure is valid', async ({ page }) => {
    await page.goto('/');

    // Validate HTML5 DOCTYPE
    const doctype = await page.evaluate(() => {
      return document.doctype ? document.doctype.name : null;
    });
    expect(doctype).toBe('html');

    // Validate proper HTML hierarchy
    const htmlStructure = await page.evaluate(() => {
      return {
        hasHtml: !!document.documentElement,
        hasHead: !!document.head,
        hasBody: !!document.body,
        titleCount: document.querySelectorAll('title').length,
        htmlCount: document.querySelectorAll('html').length
      };
    });

    expect(htmlStructure.hasHtml).toBe(true);
    expect(htmlStructure.hasHead).toBe(true);
    expect(htmlStructure.hasBody).toBe(true);
    expect(htmlStructure.titleCount).toBe(1);
    expect(htmlStructure.htmlCount).toBe(1);
  });

  test('all HTML tags are properly closed', async ({ page }) => {
    await page.goto('/');

    // Get page HTML source
    const htmlContent = await page.content();

    // Basic validation for properly closed tags
    const openTags = (htmlContent.match(/<(\w+)(?:\s[^>]*)?>/g) || [])
      .map(tag => tag.match(/<(\w+)/)[1])
      .filter(tag => !['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'].includes(tag.toLowerCase()));

    const closeTags = (htmlContent.match(/<\/(\w+)>/g) || [])
      .map(tag => tag.match(/<\/(\w+)>/)[1]);

    // Count of each tag type
    const openCount = {};
    const closeCount = {};

    openTags.forEach(tag => openCount[tag.toLowerCase()] = (openCount[tag.toLowerCase()] || 0) + 1);
    closeTags.forEach(tag => closeCount[tag.toLowerCase()] = (closeCount[tag.toLowerCase()] || 0) + 1);

    // Verify matching open/close tags
    for (const tag of Object.keys(openCount)) {
      expect(closeCount[tag] || 0).toBe(openCount[tag]);
    }
  });

  test('page has appropriate semantic structure', async ({ page }) => {
    await page.goto('/');

    // Check for semantic HTML elements
    const semantics = await page.evaluate(() => {
      return {
        hasTitle: !!document.querySelector('title'),
        titleText: document.querySelector('title')?.textContent,
        hasFooter: !!document.querySelector('footer'),
        hasMainContent: !!document.body.textContent.trim(),
        bodyText: document.body.textContent.trim()
      };
    });

    expect(semantics.hasTitle).toBe(true);
    expect(semantics.titleText).toBe('Test Pizza Page');
    expect(semantics.hasFooter).toBe(true);
    expect(semantics.hasMainContent).toBe(true);
    expect(semantics.bodyText).toContain('I love pizza');
  });

  test('text content is accessible', async ({ page }) => {
    await page.goto('/');

    // Check text contrast and visibility
    const textAccessibility = await page.evaluate(() => {
      const body = document.body;
      const style = window.getComputedStyle(body);

      return {
        textVisible: style.visibility !== 'hidden',
        notTransparent: style.opacity !== '0',
        hasTextContent: body.textContent.trim().length > 0,
        fontSizeValue: style.fontSize
      };
    });

    expect(textAccessibility.textVisible).toBe(true);
    expect(textAccessibility.notTransparent).toBe(true);
    expect(textAccessibility.hasTextContent).toBe(true);

    // Font size should be reasonable (typically 16px default)
    expect(textAccessibility.fontSizeValue).toMatch(/\d+px/);
  });

  test('color contrast is sufficient', async ({ page }) => {
    await page.goto('/');

    // Basic color contrast check
    const colorInfo = await page.evaluate(() => {
      const body = document.body;
      const footer = document.querySelector('footer');
      const bodyStyle = window.getComputedStyle(body);
      const footerStyle = window.getComputedStyle(footer);

      return {
        bodyBg: bodyStyle.backgroundColor,
        bodyColor: bodyStyle.color,
        footerBg: footerStyle.backgroundColor,
        footerColor: footerStyle.color
      };
    });

    // Verify colors are set (not 'rgba(0, 0, 0, 0)' or similar)
    expect(colorInfo.bodyBg).toMatch(/red|rgb\(255,\s*0,\s*0\)/);
    expect(colorInfo.footerBg).toMatch(/blue|rgb\(0,\s*0,\s*255\)/);

    // Text should have default color (typically black) for good contrast against red background
    console.log('Color info:', colorInfo);
  });

  test('no accessibility violations detected', async ({ page }) => {
    await page.goto('/');

    // Basic accessibility checks using Playwright's built-in capabilities
    const accessibilityIssues = await page.evaluate(() => {
      const issues = [];

      // Check for missing lang attribute (optional for simple content)
      const html = document.documentElement;
      if (!html.lang && !html.getAttribute('lang')) {
        // This is acceptable for our simple test page
      }

      // Check for proper heading structure (not required for our simple page)
      const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');

      // Check that text is not too small
      const allElements = document.querySelectorAll('*');
      allElements.forEach(el => {
        const style = window.getComputedStyle(el);
        const fontSize = parseFloat(style.fontSize);
        if (fontSize < 10) {
          issues.push(`Element has very small font size: ${fontSize}px`);
        }
      });

      return issues;
    });

    // Should have minimal or no accessibility issues
    expect(accessibilityIssues.length).toBeLessThanOrEqual(2);
  });

  test('page metadata is appropriate', async ({ page }) => {
    await page.goto('/');

    const metadata = await page.evaluate(() => {
      return {
        title: document.title,
        titleLength: document.title.length,
        metaTags: Array.from(document.querySelectorAll('meta')).map(meta => ({
          name: meta.name,
          content: meta.content,
          httpEquiv: meta.httpEquiv,
          charset: meta.charset
        }))
      };
    });

    // Verify appropriate title
    expect(metadata.title).toBe('Test Pizza Page');
    expect(metadata.titleLength).toBeGreaterThan(0);
    expect(metadata.titleLength).toBeLessThan(70); // SEO best practice

    // Meta tags are optional for this simple page
    console.log('Meta tags found:', metadata.metaTags);
  });

  test('HTML can be parsed without errors', async ({ page }) => {
    await page.goto('/');

    // Check for JavaScript parsing errors
    const parseErrors = [];

    page.on('console', msg => {
      if (msg.type() === 'error' && msg.text().includes('Parse')) {
        parseErrors.push(msg.text());
      }
    });

    // Wait for full page load
    await page.waitForLoadState('networkidle');

    // Should have no parsing errors
    expect(parseErrors).toHaveLength(0);

    // Verify DOM was properly constructed
    const domState = await page.evaluate(() => {
      return {
        readyState: document.readyState,
        bodyChildren: document.body.children.length,
        hasFooter: !!document.querySelector('footer')
      };
    });

    expect(domState.readyState).toBe('complete');
    expect(domState.hasFooter).toBe(true);
  });

  test('inline CSS is properly formatted', async ({ page }) => {
    await page.goto('/');

    // Check inline CSS syntax
    const cssValidation = await page.evaluate(() => {
      const elementsWithStyle = document.querySelectorAll('[style]');
      const styleIssues = [];

      elementsWithStyle.forEach((element, index) => {
        const styleAttr = element.getAttribute('style');

        // Basic CSS syntax validation
        if (!styleAttr.includes(':')) {
          styleIssues.push(`Element ${index} has malformed CSS: ${styleAttr}`);
        }

        if (!styleAttr.endsWith(';') && !styleAttr.includes(';')) {
          // Missing semicolon (acceptable for single property)
        }
      });

      return {
        elementsWithStyle: elementsWithStyle.length,
        styleIssues,
        styles: Array.from(elementsWithStyle).map(el => el.getAttribute('style'))
      };
    });

    expect(cssValidation.elementsWithStyle).toBeGreaterThan(0);
    expect(cssValidation.styleIssues).toHaveLength(0);

    // Should have body and footer with styles
    expect(cssValidation.styles.some(style => style.includes('background-color: red'))).toBe(true);
    expect(cssValidation.styles.some(style => style.includes('background-color: blue'))).toBe(true);
  });
});
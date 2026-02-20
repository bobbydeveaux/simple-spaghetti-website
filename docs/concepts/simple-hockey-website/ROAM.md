# ROAM Analysis: simple-hockey-website

**Feature Count:** 1
**Created:** 2026-02-18T18:50:12Z

## Risks

1. **Navigation Links Broken** (Medium): Cross-page links between index.html, schedule.html, and history.html may use incorrect relative paths, causing 404 errors depending on deployment directory structure.

2. **Cross-Browser Rendering Inconsistency** (Low): CSS flexbox/grid layouts and CSS custom properties may render differently across Chrome, Firefox, Safari, and Edge, especially for the standings table and schedule layouts.

3. **JavaScript Execution Errors** (Low): Embedded data arrays in app.js (standings, schedule, history) may fail to render if syntax errors exist, DOM isn't ready, or data structures are malformed.

4. **Theme Inconsistency** (Low): If styles.css isn't properly linked or loaded on all three pages, the dark blue (#1a3a5c) / ice white (#e8f4f8) theme will be inconsistent across pages.

5. **Data Display Issues** (Medium): All page content is dynamically rendered via JavaScript from data arrays in app.js. If JavaScript fails or is disabled, all three pages will show empty content with no standings, schedule, or history displayed.

6. **No Mobile Responsiveness** (Medium): Static table layouts for standings (6 teams) and schedule (5+ games) may not adapt to mobile screens, causing horizontal scrolling or unreadable content on phones.

7. **Accessibility Non-Compliance** (Medium): Missing semantic HTML, ARIA labels, or insufficient color contrast may prevent use by assistive technology users.

---

## Obstacles

- **JavaScript Dependency for Content**: All page content is rendered via JavaScript. If JS fails or is disabled, pages appear empty with no fallback content strategy defined.

- **Cross-Browser Testing**: Must verify rendering across Chrome, Firefox, Safari, and Edge for table layouts, flexbox, and CSS custom properties.

- **Data Population**: Need realistic sample data for standings (6 teams with W-L-Pts), schedule (5+ upcoming games with date/opponent/time/venue), and history (5+ milestones with year/description).

- **Static Hosting Requirement**: Need a web server or CDN to properly test navigation between pages; file:// protocol may block some functionality with relative path requests.

---

## Assumptions

1. **Modern Browser Support with ES6**: Users will access site with ES6-compatible browsers (Chrome 60+, Firefox 55+, Safari 11+, Edge 79+). This is required for app.js arrow functions, template literals, and const/let declarations.

2. **Static Hosting Available**: Project will be deployed to Apache/Nginx or CDN (Cloudflare Pages, GitHub Pages) that properly serves .html, .css, and .js files with correct MIME types.

3. **Relative Path Strategy**: Using relative paths for CSS/JS links (e.g., `./styles.css`, `./app.js`) will work regardless of deployment location.

4. **No External Dependencies**: Vanilla JS/CSS approach eliminates third-party library failure risks.

5. **Color Theme Appropriacy**: Dark blue (#1a3a5c) on ice white (#e8f4f8) provides sufficient contrast (approximately 10.5:1 ratio) for readability per WCAG AA guidelines.

6. **JavaScript Enabled**: Users have JavaScript enabled in their browsers, as all content (standings, schedule, history) is dynamically rendered from data arrays in app.js.

---

## Mitigations

### Navigation Links Broken
- Use consistent relative paths: `<a href="./index.html">`, `<a href="./schedule.html">`, `<a href="./history.html">`
- Test all links by serving locally with `python -m http.server 8000` or VS Code Live Server
- Add fallback navigation in site footer on all pages

### Cross-Browser Rendering Inconsistency
- Use CSS reset or normalize.css for baseline consistency
- Test in Chrome, Firefox, Safari, Edge before deployment
- Avoid cutting-edge CSS features; use widely-supported properties (flexbox, CSS custom properties)
- Document acceptable minor variations in test results

### JavaScript Execution Errors
- Wrap rendering logic in `DOMContentLoaded` event listener to ensure DOM is ready before rendering
- Add console.log statements for debugging during development
- Include error handling in render functions with user-friendly fallback message
- Validate JSON-like data structures in app.js before rendering (check for required properties)

### Theme Inconsistency
- Verify `<link rel="stylesheet" href="styles.css">` present in all three HTML files `<head>` section
- Use CSS custom properties for colors to ensure consistency: `--primary: #1a3a5c; --bg: #e8f4f8;`
- Test all three pages to confirm theme loads correctly with consistent colors

### Data Display Issues
- Add `<noscript>` fallback content in each HTML file explaining that JavaScript is required to view content
- Implement try-catch blocks in render functions to prevent total page failure if one data set has errors
- Consider static HTML fallbacks for critical content (standings table) visible even if JS disabled

### No Mobile Responsiveness
- Add viewport meta tag to all HTML files: `<meta name="viewport" content="width=device-width, initial-scale=1.0">`
- Use CSS media queries for basic mobile adjustments (stack table columns on small screens, adjust font sizes)
- Test with Chrome DevTools device emulation to verify standings table doesn't cause horizontal scrolling

### Accessibility Non-Compliance
- Use semantic HTML5 elements: `<header>`, `<nav>`, `<main>`, `<table>`, `<footer>`
- Add `alt` attributes to any images
- Ensure color contrast meets WCAG AA (4.5:1 for text) - verify #1a3a5c on #e8f4f8 exceeds this
- Add `aria-label` to navigation links if needed
- Ensure table headers have proper `<th scope="col">` attributes for screen readers
- Add proper `<caption>` element to tables for context

---

## Appendix: Plan Documents

### PRD
# Product Requirements Document: Simple Hockey Fan Website

**Created:** 2026-02-18T18:37:35Z | **Status:** Draft

## 1. Overview
3-page hockey fan website (standings, schedule, history) with dark blue/ice white theme. Static HTML/CSS/JS.

## 2. Goals
- G1: Display team standings on landing page
- G2: Show upcoming games schedule  
- G3: Present hockey history timeline
- G4: Apply hockey-themed visual design

## 3. Non-Goals
- NG1: No user authentication
- NG2: No real-time data
- NG3: No backend/database

## 4. User Stories
- US1: Fan views standings to track team position
- US2: Fan sees schedule to not miss games
- US3: New fan learns hockey history
- US4: Visitor navigates between pages

## 5. Acceptance Criteria
- AC1: Standings table with 6 teams (name, W-L-Pts)
- AC2: Schedule shows 5+ upcoming games
- AC3: History page with 5+ milestones
- AC4: Dark blue (#1a3a5c) / ice white (#e8f4f8) theme

## 6. Functional Requirements
- FR-001: Standings table for 6 teams
- FR-002: Schedule page with 5+ games  
- FR-003: History page with timeline
- FR-004: Navigation on all pages

## 7. Non-Functional Requirements
- Performance: <2s load, no external APIs
- Security: Static content only
- Scalability: Vanilla HTML/CSS/JS
- Reliability: Modern browser support

## 8. Dependencies
None - pure HTML5, CSS3, JavaScript

## 9. Out of Scope
User accounts, live scores, backend, mobile app

## 10. Success Metrics
All pages load, navigation works, theme consistent

### HLD
# High-Level Design: simple-spaghetti-repo

**Created:** 2026-02-18T18:40:12Z
**Status:** Draft

## 1. Architecture Overview

Static 3-page website with client-side rendering. Single-tier architecture - no backend, no database. All content served as static HTML/CSS/JS files. Browser fetches pages directly from web server/CDN.

---

## 2. System Components

- **index.html**: Landing page with standings table (6 teams: name, W-L, Pts)
- **schedule.html**: Schedule page displaying 5+ upcoming games
- **history.html**: Timeline page with 5+ hockey milestones
- **styles.css**: Shared stylesheet with dark blue (#1a3a5c) / ice white (#e8f4f8) theme
- **app.js**: Navigation logic and dynamic data rendering

---

## 3. Data Model

Data embedded in JavaScript as static arrays:
- **Standings**: `[{team, wins, losses, points}]` (6 entries)
- **Schedule**: `[{date, opponent, time, venue}]` (5+ entries)
- **History**: `[{year, milestone}]` (5+ entries)

---

## 4. API Contracts

N/A - Static site with no backend. Data hardcoded in JavaScript files.

---

## 5. Technology Stack

### Backend
None - static HTML/CSS/JS only

### Frontend
HTML5, CSS3, Vanilla JavaScript (ES6+)

### Infrastructure
Static file hosting (Apache/Nginx or CDN like Cloudflare Pages)

### Data Storage
None - data embedded in JS files

---

## 6. Integration Points

None - no external APIs or services

---

## 7. Security Architecture

Static content only. No user input handling. No sensitive data. CSP header optional.

---

## 8. Deployment Architecture

Single static web server. Files deployed via FTP/SFTP or git push to static host.

---

## 9. Scalability Strategy

Static files cached at CDN edge. Unlimited horizontal scaling - serve same files to all users.

---

## 10. Monitoring & Observability

Basic: Manual browser testing for cross-browser compatibility. No runtime metrics needed.

---

## 11. Architectural Decisions (ADRs)

- **ADR-001**: Use vanilla JS instead of frameworks - aligns with "no dependencies" goal, reduces complexity
- **ADR-002**: Embed data in JS rather than JSON files - simplifies deployment to single-tier static host

---

## Appendix: PRD Reference

See PRD above - all requirements captured in sections 1-10.

### LLD
The LLD has been successfully created with 38 lines, well under the 40-line limit. Here's a summary of the changes:

**Summary:**
- Created `/docs/plans/simple-spaghetti-website/LLD.md` with 12 sections
- **File Structure**: 5 files specified (index.html, schedule.html, history.html, styles.css, app.js)
- **Component Designs**: Header navigation with standings, schedule, and history pages
- **Function Signatures**: JS arrays for data and render functions
- **Test Plan**: HTML validation, local server test, browser rendering
- **Deployment**: Git push to static host, rollback via git revert

The LLD captures all implementation-critical details from the HLD while staying within the TRIVIAL complexity tier limits (40 lines max).
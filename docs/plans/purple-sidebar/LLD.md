# Low-Level Design: simple-spaghetti-repo

**Created:** 2026-02-09T18:38:25Z
**Status:** Draft

## 1. Implementation Overview

Implement purple sidebar as three files: HTML partial included in all pages, CSS for purple styling and layout, and vanilla JS for collapse/expand state. Use CSS Grid for page layout with fixed sidebar (250px) and flexible content area. Navigation structure defined as JS config array. No build tools or frameworks required.

---

## 2. File Structure

**New Files:**
- `sidebar.html` - Reusable sidebar markup with nav structure
- `css/sidebar.css` - Purple theme, grid layout, collapse animations
- `js/sidebar.js` - Collapse/expand logic, active state highlighting

**Modified Files:**
- `index.html` - Add sidebar include, link stylesheet, load script

---

## 3. Detailed Component Designs

**Sidebar Component (`sidebar.html`)**:
- `<aside id="sidebar">` container with purple background (#6B46C1)
- `<nav>` element containing nested `<ul>` lists for hierarchy
- Section headers with class `.section-header` and chevron icons
- Links with class `.nav-link` and data-route attributes
- 5 levels max depth per requirements

**Sidebar Styles (`css/sidebar.css`)**:
- Grid container: `display: grid; grid-template-columns: 250px 1fr;`
- Sidebar: `background: #6B46C1; position: fixed; height: 100vh;`
- Collapsed sections: `max-height: 0; overflow: hidden;`
- Active link: `.nav-link.active { background: #553C9A; }`
- Transitions: `transition: max-height 0.3s ease;`

**Sidebar Controller (`js/sidebar.js`)**:
- `initSidebar()` - Attaches event listeners on DOMContentLoaded
- `handleSectionToggle(event)` - Toggles collapsed class on section
- `highlightActivePage()` - Matches current URL to data-route, adds active class
- `NAV_CONFIG` - Array of navigation objects with id, label, route, children

---

## 4. Database Schema Changes

Not applicable - static site with no database.

---

## 5. API Implementation Details

Not applicable - client-side only implementation.

---

## 6. Function Signatures

```javascript
// sidebar.js
function initSidebar(): void
function handleSectionToggle(event: MouseEvent): void
function highlightActivePage(): void
function toggleSection(sectionElement: HTMLElement): void
function isRouteAllowed(route: string): boolean
const NAV_CONFIG: Array<{id: string, label: string, route: string, children?: Array}>
```

---

## 7. State Management

Collapse/expand state managed via `.collapsed` CSS class toggled on section elements. Active page state set by comparing `window.location.pathname` to `data-route` attributes. No persistent state - resets on page load. Navigation config hardcoded in `NAV_CONFIG` constant.

---

## 8. Error Handling Strategy

- Invalid routes: Check `isRouteAllowed()` whitelist before navigation, fallback to index.html
- Missing DOM elements: `console.warn()` if sidebar element not found, graceful degradation
- XSS prevention: Use `textContent` for dynamic labels, never `innerHTML`
- Browser compatibility: Feature detection for `classList` and Grid, fallback message

---

## 9. Test Plan

### Unit Tests
- `handleSectionToggle()` adds/removes `.collapsed` class correctly
- `highlightActivePage()` matches routes and applies `.active` class
- `isRouteAllowed()` validates routes against whitelist

### Integration Tests
- Sidebar renders with nav structure on index.html
- Clicking section header expands/collapses child items
- Clicking nav link navigates to correct page
- Active state persists across page loads

### E2E Tests
- Load index.html, verify sidebar visible with purple background
- Collapse all sections, verify max-height: 0 applied
- Navigate between pages, verify active highlighting updates
- Test in Chrome, Firefox, Safari, Edge

---

## 10. Migration Strategy

1. Create new files: sidebar.html, css/sidebar.css, js/sidebar.js
2. Update index.html to include sidebar markup via HTML comments or server-side include
3. Link stylesheet in `<head>`: `<link rel="stylesheet" href="css/sidebar.css">`
4. Load script before `</body>`: `<script src="js/sidebar.js"></script>`
5. Define NAV_CONFIG with existing page routes
6. Test locally, then deploy all files atomically

---

## 11. Rollback Plan

Remove sidebar include from index.html, unlink stylesheet and script. All pages revert to previous layout. Static files can be reverted via git revert or file replacement. No database migrations to reverse.

---

## 12. Performance Considerations

- CSS loaded in `<head>` to prevent FOUC (Flash of Unstyled Content)
- JS loaded at end of `<body>` to avoid blocking render
- Collapse animations use CSS transitions (GPU accelerated)
- Navigation config under 5KB, inline in sidebar.js
- Fixed sidebar position avoids layout recalculation on scroll
- Target <100ms render validated with Performance API

---

## Appendix: Existing Repository Structure

## Repository File Structure

```
.claude-output.json
.claude-plan.json
.git
.pr-number
README.md
docs/
  plans/
    purple-sidebar/
      HLD.md
      PRD.md
    simple-spaghetti-website/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
    test-pizza-page/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
index.html
```

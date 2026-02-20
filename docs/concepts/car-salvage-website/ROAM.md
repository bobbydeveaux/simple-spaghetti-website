# ROAM Analysis: car-salvage-website

**Feature Count:** 3
**Created:** 2026-02-20T07:13:24Z

## Risks

1. **Formspree Third-Party Dependency** (Medium): The contact form relies entirely on Formspree's free tier (50 submissions/month). If Formspree changes its free tier limits, introduces breaking API changes, or experiences an outage, the contact form silently fails with no fallback. There is no server-side error handling to catch this.

2. **ES6 Module MIME Type Misconfiguration** (Medium): Netlify must serve `.js` files with `Content-Type: application/javascript` for `<script type="module">` to work. If `netlify.toml` is misconfigured or the CDN caches incorrect headers, all three pages break simultaneously since both `cars.js` and `filter.js` are ES modules.

3. **CSP Header Over-Restriction** (Medium): The planned Content Security Policy in `netlify.toml` must explicitly allow `https://formspree.io` for `connect-src`/`form-action` and `https://placehold.co` for `img-src`. An overly strict or incorrectly scoped CSP will silently block form submissions and break all placeholder images without obvious error messages for end users.

4. **Placeholder Image Service Availability** (Low): `placehold.co` (or equivalent) is an external dependency with no SLA. If it returns errors or throttles requests, all car listings and detail pages will show broken image icons, significantly degrading perceived quality.

5. **Mock Data UK Accuracy** (Low): If salvage categories (Cat S, Cat N), MOT expiry dates, or repair note terminology don't match UK industry norms, the site undermines buyer confidence — the core value proposition. Cat B is listed in goals but excluded from the data model, creating an inconsistency.

6. **No Automated Test Execution** (Low): The LLD test plan is manual browser-based smoke testing. There is no test runner, no CI gate on PRs, and no automated regression check. Filter logic bugs introduced during development will only be caught by manual QA.

7. **`innerHTML` XSS Surface** (Low): `renderCards` and `renderDetail` set DOM via `innerHTML` using template literals built from the `cars.js` data array. Although the data is hardcoded, this pattern becomes a vulnerability if data is ever sourced externally without sanitisation.

---

## Obstacles

- **Formspree endpoint ID is a placeholder**: The LLD references `https://formspree.io/f/{id}` — a real Formspree account must be created and the endpoint ID committed to `contact.html` before the form is functional. This is a manual prerequisite that blocks feature `car-salvage-website-feat-detail-contact`.

- **No Netlify site or `netlify.toml` CSP values are defined yet**: The `netlify.toml` for CSP headers and redirect rules (`/car?id=*` → `car.html`) cannot be written correctly until the Formspree endpoint domain and any image CDN domains are confirmed, otherwise the CSP will require an update immediately after first deploy.

- **No real or licensed car images exist**: The entire site depends on placeholder images. There is no plan documented for sourcing actual vehicle photos, meaning the site cannot be handed off to the client as production-ready without an additional asset-gathering step outside this project's scope.

- **Cat B inconsistency between PRD goals and data model**: The PRD goals mention `Cat S/N/B` but the HLD data model enum lists only `"Cat S"` / `"Cat N"`. This ambiguity must be resolved before `data/cars.js` is authored, as retrofitting a third category affects filter UI labels and filter logic.

---

## Assumptions

1. **Formspree free tier is sufficient** — Assumed 50 submissions/month covers expected enquiry volume for a showcase site. *Validation*: Confirm with the client whether they expect more than ~50 enquiries/month before launch; upgrade to Formspree's paid tier if needed.

2. **Target audience uses modern browsers supporting ES6 modules** — The vanilla JS approach with `<script type="module">` has no transpilation fallback. *Validation*: Check Netlify Analytics post-launch for any `nomodule` fallback hits; if >5% of sessions show issues, add a `<script nomodule>` warning banner.

3. **`placehold.co` (or equivalent) is acceptable for production** — The LLD notes placeholder images should be replaced with compressed WebP "in production" but no timeline or handoff process is defined. *Validation*: Clarify with the client whether placeholder images are acceptable at launch or if real photos are required before go-live.

4. **Netlify free tier is sufficient for hosting** — No bandwidth or build minute limits are expected to be hit for a static 3-page site. *Validation*: Confirm the client has or can create a Netlify account on the free tier; check that the repo is public or the client has a Netlify plan supporting private repo deployments.

5. **UK salvage category enum is Cat S and Cat N only** — The implementation assumes two categories drive all filter UI options. *Validation*: Confirm with the client whether Cat B write-off vehicles (not legally road-registrable) should appear in listings at all; if yes, the data model and filter UI require a third enum value and a prominent disclaimer.

---

## Mitigations

### Risk 1 — Formspree Third-Party Dependency
- Add a visible `mailto:` fallback link adjacent to the form (`<a href="mailto:...">Email us directly</a>`) so users can contact the company even if Formspree is down.
- Document the Formspree account credentials and endpoint ID in the client handoff notes, not in the repo, so the client can manage their own account.
- Set Formspree to send confirmation emails to the business so failed submissions (no email received) are detectable without log access.

### Risk 2 — ES6 Module MIME Type Misconfiguration
- Explicitly add `[[headers]]` rules in `netlify.toml` for `/*.js` paths setting `Content-Type: application/javascript` rather than relying on Netlify defaults.
- Include a post-deploy smoke test checklist item: open browser DevTools Network tab and confirm both `cars.js` and `filter.js` load with `200` status and correct MIME type.

### Risk 3 — CSP Header Over-Restriction
- Draft the CSP header in `netlify.toml` before writing any HTML, using `Content-Security-Policy-Report-Only` mode first during development so violations are logged without breaking functionality.
- Explicitly enumerate required directives: `form-action https://formspree.io`, `img-src https://placehold.co`, `connect-src https://formspree.io`, `default-src 'self'`.
- Switch to enforcing mode only after manually verifying form submission and image loading on the Netlify preview URL.

### Risk 4 — Placeholder Image Service Availability
- Use `https://placehold.co/800x500` as primary and add an `onerror="this.src='css/fallback-car.svg'"` attribute on all `<img>` tags, with a simple inline SVG car silhouette committed to the repo.
- This keeps the site visually coherent even if the external image service is unreachable.

### Risk 5 — Mock Data UK Accuracy
- Resolve the Cat S/N/B inconsistency (see Obstacles) before authoring `data/cars.js`.
- Use MOT expiry dates at least 6 months from 2026-02-20 to avoid showing vehicles as already MOT-expired at launch.
- Include a brief `disclaimer` field or footer note: "All vehicles have passed MOT and are fully roadworthy. Salvage history disclosed in accordance with BVRLA guidelines."

### Risk 6 — No Automated Test Execution
- Extract `applyFilters` and `sortCars` as pure functions in `filter.js` (already planned) and add a minimal `tests/filter.test.js` using Node's built-in `node:test` runner — no test framework dependency required.
- Add a `package.json` with a single `"test": "node --test tests/"` script so tests can be run locally and optionally in a Netlify build plugin or GitHub Actions workflow.

### Risk 7 — `innerHTML` XSS Surface
- Sanitise any string interpolated into template literals using a single utility: `const esc = s => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');`
- Apply `esc()` to all vehicle string fields (`make`, `model`, `repairNotes` entries) in `buildCardHTML` and `renderDetail`, even though current data is hardcoded, to establish a safe pattern if data sourcing ever changes.

---

## Appendix: Plan Documents

### PRD
# Product Requirements Document: Car Salvage Website

I want a website where a company can list cars that they've recovered from salvage and then rebuilt them into road worth cars. please use a tonne of mock data to make a website with 12-15 cars all with the UK categorising of salvageable and fully repaired MOT'd etc.

**Created:** 2026-02-20T07:10:35Z
**Status:** Draft

## 1. Overview

**Concept:** Car Salvage Website

**Description:** A static showcase website for a UK car salvage company displaying 12–15 rebuilt vehicles with UK salvage categories (Cat S, Cat N), MOT status, repair history, and pricing — built with rich mock data.

---

## 2. Goals

- Display 12–15 salvage-to-roadworthy cars with full UK categorisation (Cat S/N/B) and MOT status
- Communicate vehicle repair quality and roadworthiness to build buyer confidence
- Provide filterable/browsable car listings with key specs visible at a glance
- Present company contact details clearly to drive enquiries

---

## 3. Non-Goals

- No user accounts, login, or saved favourites
- No online purchasing or payment processing
- No admin CMS — data is hardcoded mock data
- No live MOT/DVLA API integration

---

## 4. User Stories

- As a buyer, I want to browse all available cars so I can find one that suits me
- As a buyer, I want to see the salvage category and MOT status so I understand the vehicle's history
- As a buyer, I want to filter by price or make so I can narrow my search quickly
- As a buyer, I want to view a detail page per car so I can see full specs and repair notes
- As a visitor, I want to contact the company so I can enquire about a vehicle

---

## 5. Acceptance Criteria

**Listings page:** Given I visit the site, when I view the listings, then I see 12–15 cars with make, model, price, salvage category badge, and MOT status.

**Detail page:** Given I click a car, when the page loads, then I see full specs, repair history, MOT expiry date, and photos.

**Filter:** Given I use the filter controls, when I select a category or price range, then only matching cars display.

**Contact:** Given I click contact, when the form/details load, then I can submit an enquiry or call/email the company.

---

## 6. Functional Requirements

- **FR-001** Listings page showing all cars with thumbnail, make/model, year, mileage, price, salvage category badge (Cat S/N), MOT status
- **FR-002** Individual car detail page with full specs, repair notes, MOT expiry, and image gallery (mock images)
- **FR-003** Filter/sort controls by salvage category, price range, and make
- **FR-004** Contact page/section with phone, email, and simple enquiry form (no backend required)
- **FR-005** 12–15 hardcoded mock vehicles covering Cat S, Cat N, fully repaired, various makes

---

## 7. Non-Functional Requirements

### Performance
Page load under 3s on standard broadband; optimised images.

### Security
Static site — no server-side input handling. Contact form submits via mailto or static form service (e.g. Formspree).

### Scalability
Static HTML/CSS/JS — no scaling concerns for a showcase site.

### Reliability
Hosted on a static host (GitHub Pages / Netlify); 99.9% uptime expected.

---

## 8. Dependencies

- Static hosting platform (Netlify or GitHub Pages)
- Placeholder image service (e.g. placeholder.com or Unsplash mock URLs) for car photos
- Optional: Formspree or similar for contact form handling

---

## 9. Out of Scope

- Live inventory management or CMS
- Online payment or reservation system
- DVLA/MOT API integration
- User accounts or wishlist functionality

---

## 10. Success Metrics

- All 12–15 cars render correctly with accurate UK salvage category labels
- Filter functionality works without errors across all categories
- Contact form submits successfully
- Site passes basic accessibility check (no console errors, readable contrast)

---

## Appendix: Clarification Q&A

### Clarification Questions & Answers

### HLD
# High-Level Design: simple-spaghetti-repo

**Created:** 2026-02-20T07:11:29Z
**Status:** Draft

## 1. Architecture Overview

Static multi-page website. No backend, no server-side logic. All data is hardcoded in a JS file. Pages are plain HTML rendered by the browser; filtering/sorting runs entirely client-side.

---

## 2. System Components

- **Listings page** (`index.html`) — renders all car cards from mock data with filter controls
- **Detail page** (`car.html`) — reads a URL param (`?id=`) and renders a single vehicle's full details
- **Contact page** (`contact.html`) — phone/email display and Formspree-backed enquiry form
- **Mock data module** (`data/cars.js`) — exports 12–15 vehicle objects as a JS array
- **Filter module** (`js/filter.js`) — client-side filter/sort logic (category, price, make)

---

## 3. Data Model

Single entity: **Vehicle**

| Field | Type | Example |
|---|---|---|
| id | string | `"car-001"` |
| make | string | `"Ford"` |
| model | string | `"Focus"` |
| year | number | `2018` |
| mileage | number | `42000` |
| price | number | `6995` |
| salvageCategory | enum | `"Cat S"` / `"Cat N"` |
| motExpiry | date string | `"2026-11-14"` |
| repairNotes | string[] | `["New front panel", "Airbag replaced"]` |
| images | string[] | Placeholder URLs |
| sold | boolean | `false` |

---

## 4. API Contracts

No API. Data flows as a static JS module imported via `<script>` tags. No HTTP requests except optional Formspree POST for contact form.

**Contact form POST** (Formspree):
- `POST https://formspree.io/f/{id}`
- Fields: `name`, `email`, `message`, `vehicle_id` (hidden)

---

## 5. Technology Stack

### Backend
None — fully static.

### Frontend
- Vanilla HTML5, CSS3, JavaScript (ES6 modules)
- No frameworks — keeps the build toolchain-free
- CSS custom properties for theming; responsive grid for listings

### Infrastructure
- Netlify (preferred) or GitHub Pages for hosting
- Formspree free tier for contact form

### Data Storage
Hardcoded JS array in `data/cars.js` — no database required.

---

## 6. Integration Points

| System | Purpose | Notes |
|---|---|---|
| Formspree | Contact form submission | Free tier; no backend needed |
| Placeholder image service | Mock car photos | e.g. `https://placehold.co/800x500` |

---

## 7. Security Architecture

- Static site — no server-side attack surface
- Contact form handled by Formspree (they manage spam/CSRF)
- No secrets stored in code; Formspree endpoint ID is public by design
- Content Security Policy header set via `netlify.toml` to restrict scripts

---

## 8. Deployment Architecture

```
Git push → Netlify CI → build (no build step needed) → CDN edge deploy
```

Single `netlify.toml` configures redirect rules (`/car?id=*` → `car.html`) and security headers. No containers, no servers.

---

## 9. Scalability Strategy

Not applicable — static CDN-hosted files scale infinitely for a showcase site with no dynamic load.

---

## 10. Monitoring & Observability

- Netlify Analytics (built-in) for page views and traffic
- Browser console errors caught during manual QA
- No alerting needed for a static site

---

## 11. Architectural Decisions (ADRs)

**ADR-1: No framework (vanilla JS)**
Rationale: A showcase site with 3 pages and one data file needs no React/Vue overhead. Zero build toolchain reduces complexity and deployment friction.

**ADR-2: Data as a JS module, not JSON fetched via XHR**
Rationale: Avoids CORS issues when opening files locally (file:// protocol) and removes async complexity.

**ADR-3: Multi-page over SPA**
Rationale: Shareable/bookmarkable URLs per car (`car.html?id=car-001`) with no router code needed.

---

## Appendix: PRD Reference

*(See PRD document: Product Requirements Document: Car Salvage Website, created 2026-02-20)*

### LLD
# Low-Level Design: simple-spaghetti-repo

**Created:** 2026-02-20T07:12:06Z
**Status:** Draft

## 1. Implementation Overview

Three static HTML pages sharing a JS data module. No build step. Filter logic runs in-browser on page load and filter change events.

---

## 2. File Structure

```
car-salvage/
  index.html        # Listings page with filter controls
  car.html          # Single vehicle detail page
  contact.html      # Contact info + Formspree form
  data/cars.js      # 12-15 vehicle objects (ES module)
  js/filter.js      # Filter/sort logic
  css/style.css     # Global styles + responsive grid
  netlify.toml      # Redirect rules + CSP headers
```

---

## 3. Detailed Component Designs

**data/cars.js** — static export, no functions:
```js
export const cars = [
  { id: "car-001", make: "Ford", model: "Focus", year: 2018,
    mileage: 42000, price: 6995, salvageCategory: "Cat S",
    motExpiry: "2026-11-14", repairNotes: ["New front panel"],
    images: ["https://placehold.co/800x500"], sold: false },
  // ...14 more
];
```

**js/filter.js** — pure functions, no DOM side-effects:
```js
export function applyFilters(cars, { category, maxPrice, make })
export function sortCars(cars, sortKey)  // "price-asc" | "price-desc" | "year-desc"
```

**index.html** — inline `<script type="module">`:
- Imports `cars`, `applyFilters`, `sortCars`
- On DOMContentLoaded: renders all cards
- On filter input `change`: re-renders filtered list
- `renderCards(cars)` builds card HTML via template literal, sets `#listings` innerHTML

**car.html** — reads `?id=` param, finds vehicle, renders detail view or "Not found".

**contact.html** — static HTML form with `action="https://formspree.io/f/{id}"`, hidden `vehicle_id` field populated from URL param if present.

---

## 4. Database Schema Changes

None — data is a static JS array.

---

## 5. API Implementation Details

No API. Formspree handles contact form POST externally. No custom endpoint logic required.

---

## 6. Function Signatures

```js
// js/filter.js
export function applyFilters(cars: Vehicle[], filters: FilterState): Vehicle[]
export function sortCars(cars: Vehicle[], sortKey: string): Vehicle[]

// inline in index.html
function renderCards(cars: Vehicle[]): void
function buildCardHTML(car: Vehicle): string

// inline in car.html
function getCarById(cars: Vehicle[], id: string): Vehicle | undefined
function renderDetail(car: Vehicle): void
```

---

## 7. State Management

No framework state. DOM is the source of truth. Filter inputs read on each `change` event; filtered array recomputed and DOM replaced via `innerHTML`.

---

## 8. Error Handling Strategy

- `car.html`: if `id` param missing or no match → render `<p>Vehicle not found.</p>`
- `index.html`: if filter returns empty array → render `<p>No vehicles match your filters.</p>`
- Contact form: Formspree handles submission errors; form uses `method="POST"` with standard redirect on success

---

## 9. Test Plan

### Unit Tests
- `applyFilters`: category filter, price cap, make filter, combined filters, empty result
- `sortCars`: price ascending, price descending, year descending

### Integration Tests
- `index.html`: load in browser, change filter → assert card count updates
- `car.html?id=car-001`: assert vehicle title and price render correctly
- `car.html?id=invalid`: assert "not found" message appears

### E2E Tests
- Manual smoke test: open each page, submit contact form (Formspree test mode), verify redirect

---

## 10. Migration Strategy

New directory `car-salvage/` added to existing repo root. No changes to existing files. Deploy via Netlify pointed at `car-salvage/` as publish directory.

---

## 11. Rollback Plan

Revert the Git commit adding `car-salvage/`. Netlify redeploys automatically from the previous commit. Zero downtime — static files only.

---

## 12. Performance Considerations

- All assets served from Netlify CDN edge nodes
- No JS bundles; ES modules load only two small files (`<5 KB` each)
- Images are external placeholders; replace with compressed WebP in production
- `netlify.toml` sets `Cache-Control: max-age=86400` for CSS/JS assets

---

## Appendix: Existing Repository Structure

*(See repository file tree in task context above.)*
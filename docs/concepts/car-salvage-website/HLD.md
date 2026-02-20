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
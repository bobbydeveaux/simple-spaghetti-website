# Low-Level Design: simple-spaghetti-repo

**Created:** 2026-02-20T07:12:06Z
**Status:** In Progress — Listings page complete (Sprint 2)

## 1. Implementation Overview

Three static HTML pages sharing JS data and logic modules. No build step. Filter logic runs in-browser on page load and filter change events. ES module scripts are external files (CSP prohibits inline scripts via `script-src 'self'`).

---

## 2. File Structure

```
car-salvage/
  index.html        # Listings page with filter controls  ← DONE
  car.html          # Single vehicle detail page           (pending)
  contact.html      # Contact info + Formspree form        (pending)
  data/cars.js      # 15 vehicle objects + helper fns      ← DONE
  js/filter.js      # applyFilters / sortCars pure fns     ← DONE
  js/listings.js    # Listings page controller (DOM)       ← DONE
  css/style.css     # Global styles + responsive grid      ← DONE
  netlify.toml      # Redirect rules + CSP headers         ← DONE
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
export function applyFilters(cars, { category, make, fuelType, maxPrice })
export function sortCars(cars, sortKey)  // "price-asc" | "price-desc" | "year-desc" | "year-asc" | "mileage-asc"
```

**js/listings.js** — page controller, external ES module (CSP: `script-src 'self'`):
- Imports `cars`, `getUniqueMakes` from `../data/cars.js`
- Imports `applyFilters`, `sortCars` from `./filter.js`
- On DOMContentLoaded: populates make dropdown, wires event listeners, renders initial cards
- On filter/sort `change`: calls `applyFilters` + `sortCars`, calls `renderCards`
- `buildCardHTML(car)` returns full card HTML string via template literal
- `renderCards(cars)` sets `#listings` innerHTML; shows empty-state if no results

**index.html** — references `<script type="module" src="js/listings.js">`:
- Filter panel with selects for category, make, fuel type, max price + Reset button
- Sort controls (price asc/desc, year desc/asc, mileage asc)
- `#listings` grid with `aria-live="polite"` for accessible updates
- `#listings-count` paragraph updated on each render

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
// FilterState = { category: string, make: string, fuelType: string, maxPrice: number|null }
export function sortCars(cars: Vehicle[], sortKey: string): Vehicle[]

// js/listings.js
function buildCardHTML(car: Vehicle): string
function renderCards(cars: Vehicle[]): void
function populateMakeDropdown(): void
function getFilters(): FilterState
function update(): void
function resetFilters(): void

// js/car.js (pending)
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
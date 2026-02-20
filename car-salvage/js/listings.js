/**
 * listings.js — Controller for the car listings page (index.html).
 *
 * Responsibilities:
 *  - Populate dynamic filter dropdowns (makes) from data module
 *  - Listen for filter/sort changes and re-render the card grid
 *  - Build accessible vehicle card HTML via template literals
 *  - Handle mobile navigation toggle
 */

import { cars, getUniqueMakes } from '../data/cars.js';
import { applyFilters, sortCars } from './filter.js';

// ---------------------------------------------------------------------------
// DOM references (set once after DOMContentLoaded)
// ---------------------------------------------------------------------------
let listingsGrid;
let listingsCount;
let filterCategory;
let filterMake;
let filterFuel;
let filterPrice;
let filterSort;
let filterReset;
let navToggle;
let navLinks;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Format a price as UK pounds: 9995 → "£9,995" */
function formatPrice(price) {
  return '\u00a3' + price.toLocaleString('en-GB');
}

/** Format mileage with thousands separator: 42000 → "42,000 miles" */
function formatMileage(miles) {
  return miles.toLocaleString('en-GB') + ' miles';
}

/** Salvage category badge HTML */
function categoryBadgeHTML(cat) {
  const cls = cat === 'Cat S' ? 'badge--cat-s' : 'badge--cat-n';
  return `<span class="badge ${cls}">${cat}</span>`;
}

/** MOT status badge HTML */
function motBadgeHTML(passed) {
  const cls = passed ? 'badge--mot-pass' : 'badge--mot-fail';
  const label = passed ? 'MOT Pass' : 'MOT Fail';
  return `<span class="badge ${cls}">${label}</span>`;
}

/** Fuel type badge HTML */
function fuelBadgeHTML(fuelType) {
  let cls = 'badge--fuel';
  if (fuelType === 'Electric') cls = 'badge--electric';
  else if (fuelType.toLowerCase().includes('hybrid')) cls = 'badge--hybrid';
  return `<span class="badge ${cls}">${fuelType}</span>`;
}

// ---------------------------------------------------------------------------
// Card HTML builder
// ---------------------------------------------------------------------------

/**
 * Build the full HTML string for one vehicle card.
 * @param {Object} car - Vehicle object from cars.js
 * @returns {string} HTML string for an <article> card element
 */
function buildCardHTML(car) {
  const soldOverlay = car.sold
    ? `<div class="vehicle-card__sold-overlay" aria-hidden="true">
        <span class="vehicle-card__sold-label">SOLD</span>
      </div>`
    : '';

  const cardClass = car.sold ? 'vehicle-card vehicle-card--sold' : 'vehicle-card';
  const detailHref = `car.html?id=${encodeURIComponent(car.id)}`;

  return `
    <article class="${cardClass}" data-id="${car.id}">
      <div class="vehicle-card__image-wrap">
        <img
          class="vehicle-card__image"
          src="${car.images[0]}"
          alt="${car.year} ${car.make} ${car.model}"
          loading="lazy"
          width="800"
          height="500"
        >
        <div class="vehicle-card__badges">
          ${categoryBadgeHTML(car.salvageCategory)}
          ${motBadgeHTML(car.motPassed)}
        </div>
        ${soldOverlay}
      </div>

      <div class="vehicle-card__body">
        <div>
          <h2 class="vehicle-card__title">
            ${car.make} ${car.model}
            <span class="vehicle-card__year">${car.year}</span>
          </h2>
        </div>

        <ul class="vehicle-card__specs" aria-label="Key specs">
          <li class="vehicle-card__spec">
            <span class="vehicle-card__spec-icon" aria-hidden="true">&#9881;</span>
            ${car.engine}
          </li>
          <li class="vehicle-card__spec">
            <span class="vehicle-card__spec-icon" aria-hidden="true">&#128205;</span>
            ${formatMileage(car.mileage)}
          </li>
          <li class="vehicle-card__spec">
            <span class="vehicle-card__spec-icon" aria-hidden="true">&#128663;</span>
            ${car.bodyStyle}
          </li>
          <li class="vehicle-card__spec">
            <span class="vehicle-card__spec-icon" aria-hidden="true">&#8645;</span>
            ${car.transmission}
          </li>
        </ul>

        <div>
          ${fuelBadgeHTML(car.fuelType)}
        </div>
      </div>

      <div class="vehicle-card__footer">
        <div>
          <span class="vehicle-card__price">${formatPrice(car.price)}</span>
          <span class="vehicle-card__price-sub">inc. VAT</span>
        </div>
        ${
          car.sold
            ? '<span class="badge badge--sold">Sold</span>'
            : `<a href="${detailHref}" class="btn btn--primary btn--sm">View Car</a>`
        }
      </div>
    </article>
  `;
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

/**
 * Render the given vehicles into the listings grid and update the count label.
 * @param {Array<Object>} filteredCars
 */
function renderCards(filteredCars) {
  if (filteredCars.length === 0) {
    listingsGrid.innerHTML = `
      <div class="listings-empty" role="status">
        <div class="listings-empty__icon" aria-hidden="true">&#128269;</div>
        <p>No vehicles match your current filters.</p>
        <p class="text-sm mt-4">Try adjusting or resetting the filter criteria above.</p>
      </div>
    `;
    listingsCount.textContent = 'Showing 0 vehicles';
    return;
  }

  listingsGrid.innerHTML = filteredCars.map(buildCardHTML).join('');

  const count = filteredCars.length;
  listingsCount.textContent = `Showing ${count} vehicle${count !== 1 ? 's' : ''}`;
}

// ---------------------------------------------------------------------------
// Filter state & update
// ---------------------------------------------------------------------------

/** Read current filter values from the form controls. */
function getFilters() {
  return {
    category: filterCategory.value,
    make: filterMake.value,
    fuelType: filterFuel.value,
    maxPrice: filterPrice.value ? Number(filterPrice.value) : null,
  };
}

/** Apply current filters + sort and re-render. */
function update() {
  const filters = getFilters();
  const sortKey = filterSort.value;
  const filtered = applyFilters(cars, filters);
  const sorted = sortCars(filtered, sortKey);
  renderCards(sorted);
}

// ---------------------------------------------------------------------------
// Populate dynamic dropdowns
// ---------------------------------------------------------------------------

/** Insert one <option> per unique make into the make dropdown. */
function populateMakeDropdown() {
  const makes = getUniqueMakes();
  const fragment = document.createDocumentFragment();
  makes.forEach((make) => {
    const opt = document.createElement('option');
    opt.value = make;
    opt.textContent = make;
    fragment.appendChild(opt);
  });
  filterMake.appendChild(fragment);
}

// ---------------------------------------------------------------------------
// Mobile navigation toggle
// ---------------------------------------------------------------------------

function toggleMobileNav() {
  const isOpen = navLinks.classList.toggle('is-open');
  navToggle.setAttribute('aria-expanded', String(isOpen));
}

// ---------------------------------------------------------------------------
// Reset
// ---------------------------------------------------------------------------

function resetFilters() {
  filterCategory.value = '';
  filterMake.value = '';
  filterFuel.value = '';
  filterPrice.value = '';
  filterSort.value = 'price-asc';
  update();
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

function init() {
  // Grab DOM references
  listingsGrid   = document.getElementById('listings');
  listingsCount  = document.getElementById('listings-count');
  filterCategory = document.getElementById('filter-category');
  filterMake     = document.getElementById('filter-make');
  filterFuel     = document.getElementById('filter-fuel');
  filterPrice    = document.getElementById('filter-price');
  filterSort     = document.getElementById('filter-sort');
  filterReset    = document.getElementById('filter-reset');
  navToggle      = document.getElementById('nav-toggle');
  navLinks       = document.getElementById('nav-links');

  // Populate dynamic dropdowns
  populateMakeDropdown();

  // Wire up filter controls
  filterCategory.addEventListener('change', update);
  filterMake.addEventListener('change', update);
  filterFuel.addEventListener('change', update);
  filterPrice.addEventListener('change', update);
  filterSort.addEventListener('change', update);
  filterReset.addEventListener('click', resetFilters);

  // Mobile nav
  navToggle.addEventListener('click', toggleMobileNav);

  // Initial render (all cars, sorted by price ascending)
  update();
}

document.addEventListener('DOMContentLoaded', init);

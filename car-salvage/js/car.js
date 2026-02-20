/**
 * car.js — Vehicle detail page logic for Phoenix Auto Salvage.
 *
 * Reads the ?id= URL parameter, finds the matching vehicle from the data
 * module, and renders the full detail view (or a "not found" state).
 *
 * Exported functions match the signatures defined in the LLD:
 *   getCarById(cars, id) → Vehicle | undefined
 *   renderDetail(car)    → void
 */

import { cars } from '../data/cars.js';

// ---------------------------------------------------------------------------
// Helper utilities
// ---------------------------------------------------------------------------

/**
 * Get a vehicle by its id.
 * @param {typeof cars} vehicles
 * @param {string} id
 * @returns {typeof cars[0] | undefined}
 */
export function getCarById(vehicles, id) {
  return vehicles.find((c) => c.id === id);
}

/**
 * Format a price as UK pounds sterling (e.g. £6,995).
 * @param {number} price
 * @returns {string}
 */
function formatPrice(price) {
  return '£' + price.toLocaleString('en-GB');
}

/**
 * Format mileage with thousands separator (e.g. 42,000 miles).
 * @param {number} mileage
 * @returns {string}
 */
function formatMileage(mileage) {
  return mileage.toLocaleString('en-GB') + ' miles';
}

/**
 * Format an ISO date string as a UK long date (e.g. 14 November 2026).
 * @param {string} dateStr
 * @returns {string}
 */
function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

/**
 * Return the badge modifier class for a UK salvage category.
 * @param {string} category
 * @returns {string}
 */
function categoryBadgeClass(category) {
  if (category === 'Cat S') return 'badge--cat-s';
  if (category === 'Cat N') return 'badge--cat-n';
  return '';
}

/**
 * Return the badge modifier class for a fuel type.
 * @param {string} fuelType
 * @returns {string}
 */
function fuelBadgeClass(fuelType) {
  if (fuelType === 'Electric') return 'badge--electric';
  if (fuelType.includes('Hybrid')) return 'badge--hybrid';
  return 'badge--fuel';
}

// ---------------------------------------------------------------------------
// Render helpers
// ---------------------------------------------------------------------------

/**
 * Build HTML for the image gallery thumbnails.
 * @param {string[]} images
 * @param {string} make
 * @param {string} model
 * @param {number} year
 * @returns {string}
 */
function buildThumbsHTML(images, make, model, year) {
  return images
    .map(
      (src, i) => `
        <button class="gallery__thumb${i === 0 ? ' active' : ''}"
                aria-label="View image ${i + 1} of ${images.length}"
                data-index="${i}">
          <img src="${src}"
               alt="${year} ${make} ${model} — photo ${i + 1}"
               loading="lazy"
               width="90"
               height="60" />
        </button>`,
    )
    .join('');
}

/**
 * Build HTML rows for the specification table.
 * @param {typeof cars[0]} car
 * @returns {string}
 */
function buildSpecRowsHTML(car) {
  const rows = [
    ['Make', car.make],
    ['Model', car.model],
    ['Year', String(car.year)],
    ['Colour', car.colour],
    ['Mileage', formatMileage(car.mileage)],
    ['Engine', car.engine],
    ['Transmission', car.transmission],
    ['Fuel Type', car.fuelType],
    ['Body Style', car.bodyStyle],
    ['Salvage Category', car.salvageCategory],
    ['MOT Expiry', formatDate(car.motExpiry)],
    ['MOT Status', car.motPassed ? 'Pass' : 'Fail'],
  ];
  return rows
    .map(
      ([label, value]) => `
        <tr>
          <th scope="row">${label}</th>
          <td>${value}</td>
        </tr>`,
    )
    .join('');
}

/**
 * Build HTML list items for the repair notes.
 * @param {string[]} notes
 * @returns {string}
 */
function buildRepairNotesHTML(notes) {
  return notes
    .map((note) => `<li class="repair-notes__item">${note}</li>`)
    .join('');
}

// ---------------------------------------------------------------------------
// Page renderers
// ---------------------------------------------------------------------------

/**
 * Render the full vehicle detail page.
 * Populates #page-banner-wrap and #vehicle-detail in the DOM.
 * @param {typeof cars[0]} car
 */
export function renderDetail(car) {
  // Update browser tab title
  document.title = `${car.year} ${car.make} ${car.model} — Phoenix Auto Salvage`;

  // Page banner
  const bannerWrap = document.getElementById('page-banner-wrap');
  bannerWrap.innerHTML = `
    <div class="page-banner">
      <div class="container">
        <h1 class="page-banner__title">${car.year} ${car.make} ${car.model}</h1>
        <nav class="page-banner__breadcrumb" aria-label="Breadcrumb">
          <a href="index.html">All Cars</a> &rsaquo; ${car.make} ${car.model}
        </nav>
      </div>
    </div>`;

  const motBadgeClass = car.motPassed ? 'badge--mot-pass' : 'badge--mot-fail';
  const motBadgeLabel = car.motPassed ? 'MOT Pass' : 'MOT Fail';
  const soldBadge = car.sold
    ? '<span class="badge badge--sold">Sold</span>'
    : '';

  const ctaSection = car.sold
    ? `<p class="text-muted">This vehicle has been sold.
         <a href="index.html">Browse all available cars</a>.
       </p>`
    : `<div class="detail-cta-group">
         <a href="contact.html?id=${car.id}" class="btn btn--primary btn--lg">Enquire About This Car</a>
         <a href="index.html" class="btn btn--outline">Back to All Cars</a>
       </div>`;

  const thumbsSection =
    car.images.length > 1
      ? `<div class="gallery__thumbs" role="list" aria-label="Image thumbnails">
           ${buildThumbsHTML(car.images, car.make, car.model, car.year)}
         </div>`
      : '';

  // Main detail HTML
  const detailHTML = `
    <div class="vehicle-detail">

      <!-- Left: image gallery -->
      <div class="gallery">
        <div class="gallery__main">
          <img id="gallery-main-img"
               src="${car.images[0]}"
               alt="${car.year} ${car.make} ${car.model} — main photo"
               width="800"
               height="500" />
        </div>
        ${thumbsSection}
      </div>

      <!-- Right: detail panel -->
      <div class="detail-panel">

        <div class="detail-header">
          <h2 class="detail-header__title">${car.year} ${car.make} ${car.model}</h2>
          <p class="detail-header__subtitle">${car.bodyStyle} &mdash; ${car.colour}</p>
          <div class="detail-header__badges">
            <span class="badge ${categoryBadgeClass(car.salvageCategory)}"
                  title="UK salvage category">${car.salvageCategory}</span>
            <span class="badge ${motBadgeClass}">${motBadgeLabel}</span>
            <span class="badge ${fuelBadgeClass(car.fuelType)}">${car.fuelType}</span>
            ${soldBadge}
          </div>
        </div>

        <div>
          <p class="detail-price">${formatPrice(car.price)}</p>
          <span class="detail-price__note">Asking price — no VAT. Includes current UK MOT.</span>
        </div>

        <p>${car.description}</p>

        ${ctaSection}

        <!-- Specifications -->
        <div class="info-card">
          <h3 class="info-card__heading">Specifications</h3>
          <table class="spec-table">
            <tbody>
              ${buildSpecRowsHTML(car)}
            </tbody>
          </table>
        </div>

        <!-- Repair History -->
        <div class="repair-notes">
          <p class="repair-notes__title">Repair History</p>
          <ul class="repair-notes__list" role="list">
            ${buildRepairNotesHTML(car.repairNotes)}
          </ul>
        </div>

      </div>
    </div>`;

  document.getElementById('vehicle-detail').innerHTML = detailHTML;

  // Wire up thumbnail gallery clicks
  const mainImg = document.getElementById('gallery-main-img');
  const thumbBtns = document.querySelectorAll('.gallery__thumb');

  thumbBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.dataset.index, 10);
      mainImg.src = car.images[idx];
      mainImg.alt = `${car.year} ${car.make} ${car.model} — photo ${idx + 1}`;
      thumbBtns.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });
}

/**
 * Render a "Vehicle not found" state.
 * Populates #page-banner-wrap and #vehicle-detail in the DOM.
 */
function renderNotFound() {
  document.title = 'Vehicle Not Found — Phoenix Auto Salvage';

  const bannerWrap = document.getElementById('page-banner-wrap');
  bannerWrap.innerHTML = `
    <div class="page-banner">
      <div class="container">
        <h1 class="page-banner__title">Vehicle Not Found</h1>
        <nav class="page-banner__breadcrumb" aria-label="Breadcrumb">
          <a href="index.html">All Cars</a> &rsaquo; Not Found
        </nav>
      </div>
    </div>`;

  document.getElementById('vehicle-detail').innerHTML = `
    <div class="listings-empty">
      <div class="listings-empty__icon" aria-hidden="true">&#128269;</div>
      <p>Vehicle not found.</p>
      <a href="index.html" class="btn btn--primary mt-6">Browse All Cars</a>
    </div>`;
}

// ---------------------------------------------------------------------------
// Bootstrap — read ?id= and render
// ---------------------------------------------------------------------------

const params = new URLSearchParams(window.location.search);
const id = params.get('id');

if (!id) {
  renderNotFound();
} else {
  const car = getCarById(cars, id);
  if (car) {
    renderDetail(car);
  } else {
    renderNotFound();
  }
}

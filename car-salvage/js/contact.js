/**
 * contact.js — Contact page initialisation
 *
 * Responsibilities:
 *  1. Mobile nav toggle
 *  2. Pre-fill the enquiry form from URL query params (?id=car-001)
 */

/* --------------------------------------------------------------------------
   Mobile navigation toggle
   -------------------------------------------------------------------------- */
const navToggle = document.querySelector('.nav-toggle');
const navLinks = document.querySelector('.nav-links');

if (navToggle && navLinks) {
  navToggle.addEventListener('click', () => {
    const isOpen = navLinks.classList.toggle('is-open');
    navToggle.setAttribute('aria-expanded', String(isOpen));
  });
}

/* --------------------------------------------------------------------------
   Pre-fill form from URL params
   e.g. contact.html?id=car-001&make=Ford&model=Focus&year=2018
   -------------------------------------------------------------------------- */
(function prefillFromParams() {
  const params = new URLSearchParams(window.location.search);
  const vehicleId = params.get('id');
  const make = params.get('make');
  const model = params.get('model');
  const year = params.get('year');

  const vehicleIdField = document.getElementById('field-vehicle-id');
  const subjectField = document.getElementById('field-subject');
  const vehicleSummary = document.getElementById('vehicle-enquiry-summary');

  if (vehicleId && vehicleIdField) {
    vehicleIdField.value = vehicleId;
  }

  if (vehicleId && subjectField && !subjectField.value) {
    let label = vehicleId;
    if (make && model) {
      label = year ? `${year} ${make} ${model}` : `${make} ${model}`;
    }
    subjectField.value = `Enquiry about ${label}`;
  }

  if (vehicleId && vehicleSummary) {
    let displayText = vehicleId;
    if (make && model) {
      displayText = year ? `${year} ${make} ${model}` : `${make} ${model}`;
    }
    vehicleSummary.textContent = `You are enquiring about: ${displayText}`;
    vehicleSummary.removeAttribute('hidden');
  }
})();

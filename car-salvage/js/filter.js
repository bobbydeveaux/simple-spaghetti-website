/**
 * filter.js — Pure filter and sort helpers for the listings page.
 *
 * No DOM side-effects. All functions take arrays and return new arrays.
 */

/**
 * Filter an array of vehicles by the supplied criteria.
 *
 * @param {Array<Object>} cars     - Full vehicle array from cars.js
 * @param {Object}        filters  - Active filter state
 * @param {string}  [filters.category]  - "Cat S" | "Cat N" | "" (all)
 * @param {string}  [filters.make]      - Make name | "" (all)
 * @param {string}  [filters.fuelType]  - Fuel type | "" (all)
 * @param {number|null} [filters.maxPrice] - Maximum price inclusive, or null for no cap
 * @returns {Array<Object>} Filtered (unsorted) vehicle array
 */
export function applyFilters(cars, { category = '', make = '', fuelType = '', maxPrice = null } = {}) {
  return cars.filter((car) => {
    if (category && car.salvageCategory !== category) return false;
    if (make && car.make !== make) return false;
    if (fuelType && car.fuelType !== fuelType) return false;
    if (maxPrice !== null && car.price > maxPrice) return false;
    return true;
  });
}

/**
 * Return a sorted copy of the vehicles array.
 *
 * @param {Array<Object>} cars    - Vehicle array to sort
 * @param {string}        sortKey - One of: "price-asc" | "price-desc" | "year-desc" | "year-asc" | "mileage-asc"
 * @returns {Array<Object>} New sorted array (original is not mutated)
 */
export function sortCars(cars, sortKey) {
  const sorted = [...cars];

  switch (sortKey) {
    case 'price-asc':
      return sorted.sort((a, b) => a.price - b.price);
    case 'price-desc':
      return sorted.sort((a, b) => b.price - a.price);
    case 'year-desc':
      return sorted.sort((a, b) => b.year - a.year);
    case 'year-asc':
      return sorted.sort((a, b) => a.year - b.year);
    case 'mileage-asc':
      return sorted.sort((a, b) => a.mileage - b.mileage);
    default:
      return sorted;
  }
}

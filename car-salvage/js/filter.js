/**
 * Filter and sort logic for the car salvage listings page.
 * All functions are pure — they do not mutate the input array.
 */

/**
 * Apply filters to a list of vehicles.
 *
 * @param {Object[]} cars - Array of vehicle objects from data/cars.js
 * @param {Object} filters
 * @param {string} [filters.category] - Salvage category to filter by, e.g. "Cat S" or "Cat N".
 *   Pass an empty string or omit to include all categories.
 * @param {number} [filters.maxPrice] - Maximum price (inclusive). Pass 0 or omit to disable.
 * @param {string} [filters.make] - Vehicle make to filter by, e.g. "Ford".
 *   Pass an empty string or omit to include all makes.
 * @returns {Object[]} Filtered array (new array, input untouched).
 */
export function applyFilters(cars, { category = "", maxPrice = 0, make = "" } = {}) {
  return cars.filter((car) => {
    if (category && car.salvageCategory !== category) return false;
    if (maxPrice > 0 && car.price > maxPrice) return false;
    if (make && car.make !== make) return false;
    return true;
  });
}

/**
 * Sort a list of vehicles by a given key.
 *
 * Supported sort keys:
 *   "price-asc"   — cheapest first
 *   "price-desc"  — most expensive first
 *   "year-desc"   — newest first
 *
 * Unknown sort keys return a copy of the array in its original order.
 *
 * @param {Object[]} cars - Array of vehicle objects.
 * @param {string} sortKey - One of "price-asc", "price-desc", "year-desc".
 * @returns {Object[]} Sorted array (new array, input untouched).
 */
export function sortCars(cars, sortKey) {
  const copy = [...cars];

  switch (sortKey) {
    case "price-asc":
      return copy.sort((a, b) => a.price - b.price);
    case "price-desc":
      return copy.sort((a, b) => b.price - a.price);
    case "year-desc":
      return copy.sort((a, b) => b.year - a.year);
    default:
      return copy;
  }
}

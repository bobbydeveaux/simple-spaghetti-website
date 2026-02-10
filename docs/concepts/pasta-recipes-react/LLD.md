# Low-Level Design: simple-spaghetti-repo

**Created:** 2026-02-10T14:41:08Z
**Status:** Draft

## 1. Implementation Overview

React SPA built with Vite using functional components and hooks. Recipe data loaded from static JSON file at app bootstrap. React Router v6 for navigation between list view (`/`), detail view (`/recipe/:id`), and category views (`/category/:type`). Tailwind CSS for responsive styling. No state management library needed - useState and useContext for simple global state (search/filter). Component composition with reusable RecipeCard. Images lazy-loaded using native loading attribute.

---

## 2. File Structure

```
src/
  App.jsx                    # Root component with Router setup
  main.jsx                   # Entry point, renders App
  components/
    RecipeList.jsx           # Grid view of filtered recipes
    RecipeDetail.jsx         # Full recipe page
    RecipeCard.jsx           # Reusable recipe preview card
    SearchBar.jsx            # Search input with onChange handler
    FilterPanel.jsx          # Checkbox/dropdown filters
    Navigation.jsx           # Header with nav links
  context/
    RecipeContext.jsx        # Global recipe data and filters
  data/
    recipes.json             # Static recipe data
  utils/
    filterHelpers.js         # filterRecipes, searchRecipes functions
public/
  images/                    # Recipe photos
index.html                   # Vite entry HTML
vite.config.js               # Vite configuration
tailwind.config.js           # Tailwind setup
package.json
```

---

## 3. Detailed Component Designs

**RecipeContext.jsx**: Context provider wrapping app. Loads recipes.json on mount, provides `{ recipes, filters, setFilters, filteredRecipes }`. useMemo for filteredRecipes computed from filters.

**RecipeList.jsx**: Maps filteredRecipes to RecipeCard grid. Displays SearchBar and FilterPanel above grid. If no results, shows "No recipes found" message.

**RecipeCard.jsx**: Props: `{ recipe }`. Renders image, title, difficulty badge, cook time. Link wrapper to `/recipe/${recipe.id}`.

**RecipeDetail.jsx**: useParams to get recipe ID. Find recipe from context. Render title, image, description, ingredients (unordered list), instructions (ordered list), metadata (prep/cook time, servings, region).

**SearchBar.jsx**: Controlled input calling `setFilters({ ...filters, search: value })` on onChange. Debounce optional but not required for <20 recipes.

**FilterPanel.jsx**: Dropdowns/checkboxes for pastaType, region, difficulty. Each calls setFilters with updated filter object.

**Navigation.jsx**: Fixed header with logo, links to Home, About. Hamburger menu for mobile (Tailwind responsive classes).

---

## 4. Database Schema Changes

N/A - Static JSON data only. No database required.

---

## 5. API Implementation Details

N/A - No backend APIs. All data access via imported JSON file.

---

## 6. Function Signatures

```javascript
// utils/filterHelpers.js
export function filterRecipes(recipes, filters) {
  // filters: { search, pastaType, region, difficulty }
  // Returns: Recipe[]
}

export function searchRecipes(recipes, query) {
  // query: string
  // Returns: Recipe[] matching title or ingredients
}

// context/RecipeContext.jsx
export function RecipeProvider({ children }) {
  // Provides: { recipes, filters, setFilters, filteredRecipes }
}

// components/RecipeCard.jsx
export default function RecipeCard({ recipe }) {
  // recipe: { id, title, image, difficulty, cookTime, ... }
}

// components/RecipeDetail.jsx
export default function RecipeDetail() {
  // Uses useParams() to get :id from route
}
```

---

## 7. State Management

React Context API for global state. RecipeContext holds recipes array (loaded once), filters object `{ search: '', pastaType: '', region: '', difficulty: '' }`, and computed filteredRecipes. Components use useContext(RecipeContext) to access. setFilters updates filter state, triggering re-render of RecipeList. No Redux needed for simple filter state.

---

## 8. Error Handling Strategy

- Image load failures: Use onError handler to replace src with placeholder image
- Missing recipe ID: RecipeDetail shows "Recipe not found" if ID doesn't match
- JSON parse errors: Wrap fetch/import in try-catch, display error boundary fallback
- No user-facing error codes needed for static site

---

## 9. Test Plan

### Unit Tests
- filterHelpers.js: Test filterRecipes with various filter combinations, empty filters, no matches
- searchRecipes: Test case-insensitive search, partial matches, special characters
- RecipeCard: Render test with mock recipe, check image src and title display

### Integration Tests
- RecipeContext: Load recipes, apply filters, verify filteredRecipes updates
- RecipeList: Render with context, verify grid displays correct number of cards after filtering
- Navigation: Click links, verify route changes using MemoryRouter

### E2E Tests
- Search flow: Type query, verify results update instantly
- Filter flow: Select difficulty filter, verify only matching recipes shown
- Recipe detail: Click card, verify detail page shows ingredients and instructions
- Mobile responsive: Test hamburger menu toggle, verify layout at 320px width

---

## 10. Migration Strategy

New greenfield project - no migration required. Steps:
1. Initialize Vite React project: `npm create vite@latest`
2. Install dependencies: `react-router-dom`, `tailwindcss`
3. Create file structure above
4. Populate recipes.json with 15-20 recipe objects
5. Build components incrementally: Navigation → RecipeList → RecipeCard → Filters → RecipeDetail
6. Test locally with `npm run dev`
7. Build production bundle: `npm run build`

---

## 11. Rollback Plan

Static site deployment - rollback via hosting platform:
- Vercel/Netlify: Revert to previous deployment via dashboard (one-click rollback)
- GitHub Pages: Revert commit and re-trigger deploy action
- No database migrations to reverse
- No API versioning concerns

---

## 12. Performance Considerations

- Image optimization: Compress images to <200KB, use WebP format with JPG fallback
- Lazy loading: Add `loading="lazy"` to img tags in RecipeCard
- Code splitting: Dynamic import for RecipeDetail route: `lazy(() => import('./RecipeDetail'))`
- Bundle size: Keep under 300KB gzipped - Tailwind purge removes unused CSS
- Memoization: useMemo for filteredRecipes computation to avoid re-filtering on unrelated re-renders
- Virtual scrolling: Not needed for <50 recipes, but implement if list grows

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
  concepts/
    cool-penguin-page/
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
    happy-llama-page/
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
    pasta-recipes-react/
      HLD.md
      PRD.md
    pigeon-website/
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
  plans/
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

# ROAM Analysis: pasta-recipes-react

**Feature Count:** 4
**Created:** 2026-02-10T14:42:21Z

## Risks

1. **Recipe Data Quality and Consistency** (Medium): The static recipes.json file requires manual curation of 15-20 recipes with consistent schema (all required fields: id, title, description, image URLs, pastaType, region, difficulty, times, ingredients, instructions). Missing fields or inconsistent data structures will cause runtime errors in components. Image URLs must be valid and accessible.

2. **Image Asset Management** (Medium): Recipe images need to be sourced, optimized (<200KB), and hosted. If using external CDN, broken links will degrade user experience. If bundling locally in `/public/images/`, project size could bloat. Image optimization (WebP with JPG fallback) adds build complexity.

3. **Mobile Responsiveness Complexity** (Low): Tailwind CSS configuration and responsive design for 320px+ viewports requires careful testing across devices. Hamburger menu implementation, grid layouts, and filter panel positioning on mobile may require iteration to meet usability standards.

4. **Search and Filter Performance Degradation** (Low): While <20 recipes should perform well with client-side filtering, the filterRecipes function running on every keystroke could cause lag if implementation is inefficient (nested loops, multiple array iterations). Real-time search requirement of <1s could be missed without proper optimization.

5. **Lack of Error Boundary Implementation** (Medium): The LLD mentions error boundaries but doesn't specify implementation details. Without proper error boundaries wrapping RecipeContext and route components, a single recipe with malformed data could crash the entire application.

6. **Build Tool and Dependency Version Drift** (Low): Project depends on React 18+, React Router v6, Vite, and Tailwind CSS. Version compatibility issues between these dependencies could surface during initial setup or future updates. Vite configuration for Tailwind integration requires specific setup steps.

7. **Missing Test Infrastructure** (Medium): LLD includes comprehensive test plan but no mention of test framework setup (Jest, Vitest, React Testing Library). Without test infrastructure configured early, tests won't be written, and bugs will slip through to production.

---

## Obstacles

- **No recipe content available**: 15-20 pasta recipes with complete metadata (ingredients, instructions, prep/cook times, regions, difficulty levels) need to be researched, written, and structured before development can begin on data-dependent features.

- **Image sourcing and licensing**: High-quality recipe images must be obtained through photography, stock photos (licensed), or creative commons sources. Unclear image rights could delay deployment.

- **Unclear deployment target**: HLD mentions "Netlify, Vercel, or GitHub Pages" but no decision made. Different platforms have different configuration requirements (build commands, environment variables, routing setup for SPA).

- **No design mockups or UI specifications**: While components are defined, there are no visual designs for layout, color schemes, typography, or spacing. This may lead to implementation delays or misalignment with user expectations.

---

## Assumptions

1. **Recipe data can be curated manually within project timeline**: Assumes team has access to 15-20 authentic pasta recipes with complete information, or can create them. Validation: Confirm recipe sources and content creation capacity before sprint begins.

2. **Static JSON approach scales to 20 recipes**: Assumes client-side filtering of 20 recipe objects with full text content will perform within <1s search requirement. Validation: Benchmark filterRecipes with realistic data payload (~50-100KB JSON) on low-end mobile devices.

3. **No backend or CMS needed initially**: Assumes content updates are infrequent enough that redeployment for recipe changes is acceptable. Validation: Confirm with stakeholders that manual redeployment workflow is acceptable for first version.

4. **Team has React and Tailwind expertise**: Assumes developers are proficient with React hooks, Context API, React Router v6, and Tailwind utility classes. Validation: Assess team skill levels and allocate learning time if needed.

5. **Browser support limited to modern browsers**: Assumes target users are on browsers supporting ES6+, CSS Grid, lazy loading attribute. Validation: Confirm no IE11 or legacy browser support required.

---

## Mitigations

### Risk 1: Recipe Data Quality and Consistency
- **Action 1**: Create JSON schema validation using Ajv or Zod library to validate recipes.json at build time
- **Action 2**: Implement TypeScript or PropTypes for Recipe interface to catch missing fields during development
- **Action 3**: Build a simple Node.js script to validate recipe data structure before committing (pre-commit hook)
- **Action 4**: Create a recipe template markdown file with all required fields documented as a guide for content creation

### Risk 2: Image Asset Management
- **Action 1**: Use placeholder service (placeholder.com or unsplash.it) during initial development to unblock component work
- **Action 2**: Implement fallback image URL in RecipeCard onError handler to gracefully handle broken images
- **Action 3**: Add image optimization step to build process using vite-plugin-imagemin or sharp
- **Action 4**: Host images on free CDN (Cloudinary free tier) with automatic WebP conversion to offload optimization

### Risk 3: Mobile Responsiveness Complexity
- **Action 1**: Implement mobile-first development approach, building 320px layout first then scaling up
- **Action 2**: Use Tailwind's responsive preview plugin or browser dev tools device emulation for continuous testing
- **Action 3**: Add Lighthouse CI to verify mobile responsiveness score >90 before deployment
- **Action 4**: Limit initial scope to 2-3 breakpoints (mobile, tablet, desktop) instead of pixel-perfect responsive design

### Risk 4: Search and Filter Performance Degradation
- **Action 1**: Implement useMemo for filteredRecipes computation in RecipeContext to prevent unnecessary re-filtering
- **Action 2**: Add debounce (300ms) to search input using useDeferredValue or custom debounce hook
- **Action 3**: Profile filterHelpers.js functions with realistic data using Chrome DevTools Performance tab
- **Action 4**: Benchmark search performance on target devices and optimize filter logic (single pass instead of multiple filters)

### Risk 5: Lack of Error Boundary Implementation
- **Action 1**: Create ErrorBoundary component wrapper in first sprint before building feature components
- **Action 2**: Wrap RecipeContext.Provider and Router with ErrorBoundary to catch context and routing errors
- **Action 3**: Add try-catch blocks around recipes.json import with user-friendly error message
- **Action 4**: Implement fallback UI for ErrorBoundary showing "Something went wrong" with reload button

### Risk 6: Build Tool and Dependency Version Drift
- **Action 1**: Lock dependency versions in package.json (no ^ or ~ prefixes) for initial setup
- **Action 2**: Test Vite + Tailwind integration with minimal reproduction before scaffolding full project
- **Action 3**: Document exact setup steps in README for Vite, React Router, and Tailwind configuration
- **Action 4**: Use npm ci instead of npm install in deployment pipeline to ensure consistent builds

### Risk 7: Missing Test Infrastructure
- **Action 1**: Set up Vitest + React Testing Library in project setup phase (Feature 1) before writing components
- **Action 2**: Configure test coverage thresholds (70%+ for utils, 60%+ for components) in vitest.config.js
- **Action 3**: Add test script to package.json and CI pipeline to block merges without passing tests
- **Action 4**: Write tests incrementally alongside component development (TDD approach for filterHelpers.js)

---

## Appendix: Plan Documents

### PRD
# Product Requirements Document: Medium sized React website about pasta recipes

**Created:** 2026-02-10T14:39:56Z
**Status:** Draft

## 1. Overview

**Concept:** Medium sized React website about pasta recipes

**Description:** Medium sized React website about pasta recipes

---

## 2. Goals

- Create an intuitive recipe browsing experience with category filtering (pasta type, region, difficulty)
- Enable users to search and discover pasta recipes quickly
- Provide detailed recipe information including ingredients, steps, cooking time, and servings
- Build a responsive, mobile-friendly interface that works across all devices

---

## 3. Non-Goals

- User authentication or personal recipe saving features
- Recipe submission or user-generated content
- Social features (comments, ratings, sharing)
- E-commerce or ingredient purchasing functionality
- Video content or interactive cooking tutorials

---

## 4. User Stories

- As a home cook, I want to browse pasta recipes by category so that I can find recipes matching my ingredients
- As a beginner, I want to filter by difficulty level so that I can find recipes appropriate for my skill
- As a mobile user, I want to view recipes on my phone so that I can cook while following instructions
- As a recipe explorer, I want to search by ingredient or pasta type so that I can quickly find specific recipes
- As a meal planner, I want to see cooking time and servings so that I can plan my meals efficiently
- As a culinary enthusiast, I want to explore regional Italian pasta dishes so that I can expand my cooking repertoire

---

## 5. Acceptance Criteria

**Recipe Browsing:**
- Given I am on the homepage, when I view the recipe list, then I see at least 15-20 pasta recipes with images and titles
- Given I select a category filter, when applied, then only recipes matching that category are displayed

**Recipe Detail:**
- Given I click on a recipe card, when the detail page loads, then I see ingredients list, step-by-step instructions, prep/cook time, and servings
- Given I am viewing a recipe, when I scroll, then the layout remains readable and properly formatted

**Search:**
- Given I enter a search term, when I submit, then results matching recipe name or ingredients are displayed within 1 second

---

## 6. Functional Requirements

- FR-001: Display recipe cards with image, title, cooking time, and difficulty on the homepage
- FR-002: Implement category filtering by pasta type (spaghetti, penne, lasagna, etc.), region (Northern, Southern, Central Italy), and difficulty
- FR-003: Provide search functionality with real-time filtering by recipe name and key ingredients
- FR-004: Render recipe detail pages with structured content: ingredients list, numbered instructions, prep/cook time, servings, and description
- FR-005: Implement responsive navigation menu with links to home, categories, and about sections

---

## 7. Non-Functional Requirements

### Performance
- Recipe list and detail pages must load in under 2 seconds on standard broadband connections
- Images should be optimized and lazy-loaded to minimize initial page load time

### Security
- All external API calls (if used) must be made over HTTPS
- Input sanitization for search queries to prevent XSS vulnerabilities

### Scalability
- Architecture should support expansion to 50+ recipes without performance degradation
- Component structure should allow easy addition of new recipe categories

### Reliability
- Website should maintain 99% uptime when deployed
- Graceful error handling for missing images or recipe data

---

## 8. Dependencies

- React 18+ for UI framework
- React Router for client-side routing
- CSS framework (e.g., Tailwind CSS or Material-UI) for responsive styling
- Recipe data source (JSON file or headless CMS like Contentful)
- Image hosting service or local assets for recipe photos

---

## 9. Out of Scope

- Backend API development or database implementation
- User accounts, login, or personalization features
- Recipe rating, commenting, or social sharing capabilities
- Shopping list generation or grocery delivery integration
- Nutritional information or dietary restriction filtering
- Recipe video tutorials or cooking timers

---

## 10. Success Metrics

- Users can find and view a recipe within 3 clicks from the homepage
- Recipe detail pages provide all necessary cooking information without external links
- Website maintains responsive design across mobile (320px+), tablet, and desktop viewports
- Search returns relevant results for 90%+ of common pasta-related queries

---

## Appendix: Clarification Q&A

### Clarification Questions & Answers


### HLD
# High-Level Design: simple-spaghetti-repo

**Created:** 2026-02-10T14:40:29Z
**Status:** Draft

## 1. Architecture Overview

Single-page application (SPA) architecture using React. Client-side rendering with static recipe data stored in JSON files. No backend server required - deployed as static files to CDN/hosting service. React Router handles client-side navigation between recipe list, detail pages, and category views.

---

## 2. System Components

- **RecipeList Component**: Displays grid of recipe cards with filtering and search capabilities
- **RecipeDetail Component**: Renders individual recipe with ingredients, instructions, metadata
- **SearchBar Component**: Real-time search input with filtering logic
- **FilterPanel Component**: Category, region, and difficulty filter controls
- **Navigation Component**: Responsive header with routing links
- **RecipeCard Component**: Reusable card displaying recipe preview
- **Data Layer**: JSON file with recipe data loaded at application bootstrap

---

## 3. Data Model

**Recipe Entity:**
- id (string), title (string), description (string), image (string URL)
- pastaType (enum: spaghetti, penne, lasagna, etc.)
- region (enum: Northern, Southern, Central)
- difficulty (enum: easy, medium, hard)
- prepTime (number, minutes), cookTime (number, minutes), servings (number)
- ingredients (array of strings), instructions (array of strings)

---

## 4. API Contracts

No external APIs. Data access via imported JSON:
- `recipes.json` structure: `{ recipes: Recipe[] }`
- Client-side filtering: `filterRecipes(recipes, { search, pastaType, region, difficulty })`
- Client-side search: `searchRecipes(recipes, query)` matches title and ingredients

---

## 5. Technology Stack

### Backend
None - static site only

### Frontend
- React 18.x with hooks
- React Router v6 for routing
- Tailwind CSS for responsive styling
- Vite as build tool and dev server

### Infrastructure
- Static hosting (Netlify, Vercel, or GitHub Pages)
- CDN for asset delivery

### Data Storage
- Static JSON files bundled with application
- Recipe images stored in `/public/images/` or external CDN

---

## 6. Integration Points

None. Self-contained static application with no external service dependencies.

---

## 7. Security Architecture

- Input sanitization: DOMPurify or React's built-in XSS protection for search queries
- Content Security Policy (CSP) headers configured in hosting platform
- HTTPS enforced via hosting provider
- No authentication/authorization required (public site)

---

## 8. Deployment Architecture

Static build artifacts deployed to CDN-backed hosting:
- `npm run build` generates optimized production bundle
- Deploy `/dist` folder to Netlify/Vercel
- Automatic HTTPS, CDN caching, and global distribution
- Single deployment artifact - no separate services

---

## 9. Scalability Strategy

Client-side rendering scales horizontally via CDN edge caching. Recipe data (<1MB JSON) loaded once per session. Image lazy-loading prevents bandwidth bottlenecks. To scale to 50+ recipes: paginate recipe list or implement virtual scrolling if performance degrades.

---

## 10. Monitoring & Observability

- Hosting platform analytics (Vercel/Netlify) for page views, load times
- Browser console errors logged via window.onerror handler
- Lighthouse CI in deployment pipeline for performance regression detection
- No application-level logging required for static site

---

## 11. Architectural Decisions (ADRs)

**ADR-001: Static JSON over CMS**
Chose local JSON for simplicity - no API latency, no external dependencies, easier development. Trade-off: content updates require redeployment.

**ADR-002: Client-side filtering over server pagination**
20 recipes fit comfortably in memory. Client-side search provides instant results (<1s requirement). Avoids backend complexity.

**ADR-003: Tailwind CSS over component library**
Tailwind provides responsive utilities without large bundle size of Material-UI. Custom design flexibility for recipe layout.

---

## Appendix: PRD Reference

# Product Requirements Document: Medium sized React website about pasta recipes

**Created:** 2026-02-10T14:39:56Z
**Status:** Draft

## 1. Overview

**Concept:** Medium sized React website about pasta recipes

**Description:** Medium sized React website about pasta recipes

---

## 2. Goals

- Create an intuitive recipe browsing experience with category filtering (pasta type, region, difficulty)
- Enable users to search and discover pasta recipes quickly
- Provide detailed recipe information including ingredients, steps, cooking time, and servings
- Build a responsive, mobile-friendly interface that works across all devices

---

## 3. Non-Goals

- User authentication or personal recipe saving features
- Recipe submission or user-generated content
- Social features (comments, ratings, sharing)
- E-commerce or ingredient purchasing functionality
- Video content or interactive cooking tutorials

---

## 4. User Stories

- As a home cook, I want to browse pasta recipes by category so that I can find recipes matching my ingredients
- As a beginner, I want to filter by difficulty level so that I can find recipes appropriate for my skill
- As a mobile user, I want to view recipes on my phone so that I can cook while following instructions
- As a recipe explorer, I want to search by ingredient or pasta type so that I can quickly find specific recipes
- As a meal planner, I want to see cooking time and servings so that I can plan my meals efficiently
- As a culinary enthusiast, I want to explore regional Italian pasta dishes so that I can expand my cooking repertoire

---

## 5. Acceptance Criteria

**Recipe Browsing:**
- Given I am on the homepage, when I view the recipe list, then I see at least 15-20 pasta recipes with images and titles
- Given I select a category filter, when applied, then only recipes matching that category are displayed

**Recipe Detail:**
- Given I click on a recipe card, when the detail page loads, then I see ingredients list, step-by-step instructions, prep/cook time, and servings
- Given I am viewing a recipe, when I scroll, then the layout remains readable and properly formatted

**Search:**
- Given I enter a search term, when I submit, then results matching recipe name or ingredients are displayed within 1 second

---

## 6. Functional Requirements

- FR-001: Display recipe cards with image, title, cooking time, and difficulty on the homepage
- FR-002: Implement category filtering by pasta type (spaghetti, penne, lasagna, etc.), region (Northern, Southern, Central Italy), and difficulty
- FR-003: Provide search functionality with real-time filtering by recipe name and key ingredients
- FR-004: Render recipe detail pages with structured content: ingredients list, numbered instructions, prep/cook time, servings, and description
- FR-005: Implement responsive navigation menu with links to home, categories, and about sections

---

## 7. Non-Functional Requirements

### Performance
- Recipe list and detail pages must load in under 2 seconds on standard broadband connections
- Images should be optimized and lazy-loaded to minimize initial page load time

### Security
- All external API calls (if used) must be made over HTTPS
- Input sanitization for search queries to prevent XSS vulnerabilities

### Scalability
- Architecture should support expansion to 50+ recipes without performance degradation
- Component structure should allow easy addition of new recipe categories

### Reliability
- Website should maintain 99% uptime when deployed
- Graceful error handling for missing images or recipe data

---

## 8. Dependencies

- React 18+ for UI framework
- React Router for client-side routing
- CSS framework (e.g., Tailwind CSS or Material-UI) for responsive styling
- Recipe data source (JSON file or headless CMS like Contentful)
- Image hosting service or local assets for recipe photos

---

## 9. Out of Scope

- Backend API development or database implementation
- User accounts, login, or personalization features
- Recipe rating, commenting, or social sharing capabilities
- Shopping list generation or grocery delivery integration
- Nutritional information or dietary restriction filtering
- Recipe video tutorials or cooking timers

---

## 10. Success Metrics

- Users can find and view a recipe within 3 clicks from the homepage
- Recipe detail pages provide all necessary cooking information without external links
- Website maintains responsive design across mobile (320px+), tablet, and desktop viewports
- Search returns relevant results for 90%+ of common pasta-related queries

---

## Appendix: Clarification Q&A

### Clarification Questions & Answers


### LLD
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

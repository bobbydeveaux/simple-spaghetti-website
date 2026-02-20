The refined ROAM is clean and correct. Here's a summary of what changed and why:

**Risks — 2 added:**
- **Risk 8: `sold` Field Behaviour Undefined** — The HLD data model has `sold: boolean` but no FR, AC, or epic feature mentions how sold vehicles are displayed. This could silently break the "12–15 cars" acceptance criterion if sold vehicles are filtered out.
- **Risk 9: No JavaScript Fallback** — All three pages render entirely via ES6 modules. JS-disabled users see blank pages with no indication of why. A single `<noscript>` tag per page resolves this.

**Obstacles — 1 added, 1 refined:**
- **Added: Netlify redirect notation is misleading** — The HLD describes `/car?id=*` → `car.html` but Netlify `[[redirects]]` doesn't support query-string-conditional routing. The correct implementation is a path-level rewrite (`/car` → `/car.html`) that passes query strings through automatically. Writing it wrong results in silent failure.
- **Refined: Cat B obstacle** — Updated to note the epic YAML (`car-salvage-website-feat-foundation`) also explicitly scopes to Cat S/N only, meaning the epic has de-facto resolved it — but client sign-off is still the blocker.

**Assumptions — 1 added, 1 refined:**
- **Added: Assumption 6** — All mock vehicles start as `sold: false` to sidestep Risk 8 until the client defines sold-vehicle behaviour.
- **Refined: Assumption 5** — Now cross-references the epic feature description alignment on Cat S/N only.

**Mitigations — 2 added:**
- Risk 8 and Risk 9 mitigations added. Risk 6 mitigation updated to reference GitHub Actions rather than a Netlify build plugin (simpler, more standard).
# High-Level Design: simple-spaghetti-repo

**Created:** 2026-02-18T21:43:53Z
**Status:** Draft

## 1. Architecture Overview

Static single-page website. No backend, no database, no server-side logic. All content is hardcoded HTML served directly from a CDN/static host.

---

## 2. System Components

- **index.html** — single page with cottage photos, descriptions, and contact section
- **CSS** — styling (inline or single stylesheet)
- **Images** — cottage photo assets

---

## 3. Data Model

No dynamic data model. Cottage content (name, description, photo path, contact details) is hardcoded in HTML.

---

## 4. API Contracts

None. Static site with no API.

---

## 5. Technology Stack

### Backend
None.

### Frontend
HTML5, CSS3. Vanilla JS optional for smooth scroll only.

### Infrastructure
GitHub Pages or Netlify (free static hosting).

### Data Storage
None. Assets served as static files.

---

## 6. Integration Points

None. No external APIs or services.

---

## 7. Security Architecture

Static HTML only — no forms, no user input, no server. Attack surface is effectively zero. HTTPS enforced via host provider.

---

## 8. Deployment Architecture

Push HTML/CSS/images to Git repository. Host auto-deploys on push (GitHub Pages or Netlify). No build step required.

---

## 9. Scalability Strategy

CDN-backed static hosting scales automatically. No action required.

---

## 10. Monitoring & Observability

Host provider uptime monitoring sufficient. Optional: add free Netlify Analytics or Google Analytics snippet.

---

## 11. Architectural Decisions (ADRs)

**ADR-1: Static HTML over CMS** — A CMS adds unnecessary complexity for a single cottage listing. Plain HTML meets all requirements with zero maintenance overhead.

---

## Appendix: PRD Reference

*(See PRD: Cottage Website, 2026-02-18)*
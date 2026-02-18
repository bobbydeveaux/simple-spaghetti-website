# High-Level Design: simple-spaghetti-repo

**Created:** 2026-02-18T18:40:12Z
**Status:** Draft

## 1. Architecture Overview

Static 3-page website with client-side rendering. Single-tier architecture - no backend, no database. All content served as static HTML/CSS/JS files. Browser fetches pages directly from web server/CDN.

---

## 2. System Components

- **index.html**: Landing page with standings table (6 teams: name, W-L, Pts)
- **schedule.html**: Schedule page displaying 5+ upcoming games
- **history.html**: Timeline page with 5+ hockey milestones
- **styles.css**: Shared stylesheet with dark blue (#1a3a5c) / ice white (#e8f4f8) theme
- **app.js**: Navigation logic and dynamic data rendering

---

## 3. Data Model

Data embedded in JavaScript as static arrays:
- **Standings**: `[{team, wins, losses, points}]` (6 entries)
- **Schedule**: `[{date, opponent, time, venue}]` (5+ entries)
- **History**: `[{year, milestone}]` (5+ entries)

---

## 4. API Contracts

N/A - Static site with no backend. Data hardcoded in JavaScript files.

---

## 5. Technology Stack

### Backend
None - static HTML/CSS/JS only

### Frontend
HTML5, CSS3, Vanilla JavaScript (ES6+)

### Infrastructure
Static file hosting (Apache/Nginx or CDN like Cloudflare Pages)

### Data Storage
None - data embedded in JS files

---

## 6. Integration Points

None - no external APIs or services

---

## 7. Security Architecture

Static content only. No user input handling. No sensitive data. CSP header optional.

---

## 8. Deployment Architecture

Single static web server. Files deployed via FTP/SFTP or git push to static host.

---

## 9. Scalability Strategy

Static files cached at CDN edge. Unlimited horizontal scaling - serve same files to all users.

---

## 10. Monitoring & Observability

Basic: Manual browser testing for cross-browser compatibility. No runtime metrics needed.

---

## 11. Architectural Decisions (ADRs)

- **ADR-001**: Use vanilla JS instead of frameworks - aligns with "no dependencies" goal, reduces complexity
- **ADR-002**: Embed data in JS rather than JSON files - simplifies deployment to single-tier static host

---

## Appendix: PRD Reference

See PRD above - all requirements captured in sections 1-10.
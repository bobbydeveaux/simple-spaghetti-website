# Product Requirements Document: Car Salvage Website

I want a website where a company can list cars that they've recovered from salvage and then rebuilt them into road worth cars. please use a tonne of mock data to make a website with 12-15 cars all with the UK categorising of salvageable and fully repaired MOT'd etc.

**Created:** 2026-02-20T07:10:35Z
**Status:** Draft

## 1. Overview

**Concept:** Car Salvage Website

**Description:** A static showcase website for a UK car salvage company displaying 12–15 rebuilt vehicles with UK salvage categories (Cat S, Cat N), MOT status, repair history, and pricing — built with rich mock data.

---

## 2. Goals

- Display 12–15 salvage-to-roadworthy cars with full UK categorisation (Cat S/N/B) and MOT status
- Communicate vehicle repair quality and roadworthiness to build buyer confidence
- Provide filterable/browsable car listings with key specs visible at a glance
- Present company contact details clearly to drive enquiries

---

## 3. Non-Goals

- No user accounts, login, or saved favourites
- No online purchasing or payment processing
- No admin CMS — data is hardcoded mock data
- No live MOT/DVLA API integration

---

## 4. User Stories

- As a buyer, I want to browse all available cars so I can find one that suits me
- As a buyer, I want to see the salvage category and MOT status so I understand the vehicle's history
- As a buyer, I want to filter by price or make so I can narrow my search quickly
- As a buyer, I want to view a detail page per car so I can see full specs and repair notes
- As a visitor, I want to contact the company so I can enquire about a vehicle

---

## 5. Acceptance Criteria

**Listings page:** Given I visit the site, when I view the listings, then I see 12–15 cars with make, model, price, salvage category badge, and MOT status.

**Detail page:** Given I click a car, when the page loads, then I see full specs, repair history, MOT expiry date, and photos.

**Filter:** Given I use the filter controls, when I select a category or price range, then only matching cars display.

**Contact:** Given I click contact, when the form/details load, then I can submit an enquiry or call/email the company.

---

## 6. Functional Requirements

- **FR-001** Listings page showing all cars with thumbnail, make/model, year, mileage, price, salvage category badge (Cat S/N), MOT status
- **FR-002** Individual car detail page with full specs, repair notes, MOT expiry, and image gallery (mock images)
- **FR-003** Filter/sort controls by salvage category, price range, and make
- **FR-004** Contact page/section with phone, email, and simple enquiry form (no backend required)
- **FR-005** 12–15 hardcoded mock vehicles covering Cat S, Cat N, fully repaired, various makes

---

## 7. Non-Functional Requirements

### Performance
Page load under 3s on standard broadband; optimised images.

### Security
Static site — no server-side input handling. Contact form submits via mailto or static form service (e.g. Formspree).

### Scalability
Static HTML/CSS/JS — no scaling concerns for a showcase site.

### Reliability
Hosted on a static host (GitHub Pages / Netlify); 99.9% uptime expected.

---

## 8. Dependencies

- Static hosting platform (Netlify or GitHub Pages)
- Placeholder image service (e.g. placeholder.com or Unsplash mock URLs) for car photos
- Optional: Formspree or similar for contact form handling

---

## 9. Out of Scope

- Live inventory management or CMS
- Online payment or reservation system
- DVLA/MOT API integration
- User accounts or wishlist functionality

---

## 10. Success Metrics

- All 12–15 cars render correctly with accurate UK salvage category labels
- Filter functionality works without errors across all categories
- Contact form submits successfully
- Site passes basic accessibility check (no console errors, readable contrast)

---

## Appendix: Clarification Q&A

### Clarification Questions & Answers
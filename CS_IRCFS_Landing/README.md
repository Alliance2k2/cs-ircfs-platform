# CS-IRCFS — Landing page + dashboard preview

Open `index.html` in any modern browser. No build step is required.

## Files
- `index.html`: responsive landing page
- `styles.css`: design system, responsive layout, animations
- `script.js`: mobile menu, progressive reveal, verified project fact counters, FAQ, EN/RW navigation toggle
- `assets/logo.png`: standalone CS-IRCFS logo icon
- `dashboard/index.html`: previously designed, standalone 15-screen dashboard prototype

## Important distinctions
- This is a front-end **concept demonstration**, not an authenticated/live deployed system.
- The PADAB values (650 ha, two pump stations and 65.5 km canals) and 200 targeted citizen monitors come from the supplied project proposal. They are not real-time impact statistics.
- Example USSD shortcodes mentioned in the platform proposal are not confirmed production allocations.
- Photo backgrounds use Unsplash URLs as optional enhancements. CSS and locally drawn hero artwork provide offline fallbacks, but the photos require internet to load.
- The EN/RW language toggle translates **navigation only**, not full-page content. For deployment, localize all page and accessibility text and validate Kinyarwanda with project stakeholders.
- Before production replace prototype links, add backend/authentication, real baseline datasets, privacy compliance and working USSD/SMS provider integration.

# CS-IRCFS web pages

FastAPI serves this folder at `/`, so the pages and the API share one address and no separate web server is needed. Start the platform with `..\start-local.ps1` (or `..\start-local.ps1 -Demo` for sample data) and open `http://127.0.0.1:8000`.

## Folder layout

```
dashboard/
├── *.html              pages (served at /index.html, /planner.html, ...)
└── assets/
    ├── css/            stylesheets
    ├── js/             page scripts
    ├── img/            logo and site icons (made from the CS-IRCFS emblem)
    ├── fonts/          DM Sans and Manrope
    ├── data/           map data (Bugesera district outline)
    └── vendor/         Bootstrap 5.3.3 and Bootstrap Icons 1.11.3
favicon.ico, site.webmanifest   browser tab icon and install icons
```

Paths in the table below are relative to `assets/`.

| Files | Page |
| --- | --- |
| `index.html` + `css/landing.css` + `js/landing.js` | Public home page: live totals, sector map with irrigation advice, how it works, FAQ |
| `planner.html`, `act-now.html`, `channels.html`, `schemes.html`, `trends.html`, `advice.html`, `nutrition.html`, `map.html`, `feedback.html`, `cooperatives.html` + `js/app.js` | District dashboard pages (see below) |
| `js/trends.js` | Twelve-month trend charts on the dashboard |
| `report.html` | Monthly district report (print or save as PDF) |
| `simulator.html` + `js/simulator.js` + `css/simulator.css` | Feature-phone simulator for USSD `*801#` and SMS `8448` |
| `management.html` + `js/management.js` + `css/management.css`, `css/management-overrides.css` | Platform Management: data tables, forms, accounts |
| `login.html`, `register.html` + `css/auth.css` | Staff sign-in and registration |
| `backend-console.html` + `js/backend-console.js` + `css/backend-console.css`, `css/backend-console-overrides.css` | Technical console for developers |
| `js/shared.js` + `css/shared.css` | Used by every page: API calls, sign-in session, EN/RW switch, notices, dialogs |
| `js/app-shell.js` + `css/app-shell.css` | One shell for every signed-in page (planner, management, report, simulator, technical console): sidebar built from a single navigation list, top bar with breadcrumb, jump-to search (Ctrl K), API status and Act Now bell, dark photo page hero, footer, collapsible sidebar and mobile drawer |
| `css/dashboard-theme.css` | Dashboard components: KPI cards, panels, trend charts, progress bars, tables |
| `css/brand.css` | Logo and heading font for the report, simulator and technical console |
| `css/fonts.css` | DM Sans (text) and Manrope (headings), stored locally |
| `css/bootstrap-theme.css` | Bootstrap in the CS-IRCFS colours; keeps the original look on the dashboard pages |
| `vendor/` | Bootstrap 5.3.3 and Bootstrap Icons 1.11.3, stored locally so pages work without internet |
| `data/bugesera-boundary.geojson` | District outline for the map |

## Adding a signed-in page

Give `<body>` a `data-page` name, use the shell skeleton, and load `assets/js/app-shell.js` after `shared.js` and before the page script:

```html
<body data-page="mypage">
  <div class="app-layout">
    <aside class="app-sidebar" data-app-sidebar></aside>
    <div class="app-main">
      <header class="app-topbar" data-app-topbar></header>
      <main class="app-content">
        <header class="app-hero compact">…title and actions…</header>
        …page content…
      </main>
      <footer class="app-footer" data-app-footer></footer>
    </div>
  </div>
  <div class="app-backdrop" data-app-backdrop hidden></div>
```

Add the page to `GROUPS` and `CRUMBS` in `app-shell.js` so it appears in the sidebar.

## Styling with Bootstrap

Every page loads its stylesheets in the same order:

1. `assets/vendor/bootstrap-5.3.3/css/bootstrap.min.css`
2. `assets/vendor/bootstrap-icons-1.11.3/bootstrap-icons.min.css`
3. `assets/css/bootstrap-theme.css`
4. The page's own stylesheets from `assets/css/`

Scripts end with `assets/vendor/bootstrap-5.3.3/js/bootstrap.bundle.min.js`, then `assets/js/shared.js`, then the page script from `assets/js/`.

- `index.html`, `login.html` and `register.html` are built on Bootstrap (grid, navbar, accordion, forms) and set `<html data-ui="bootstrap">`.
- The dashboard pages keep their original CSS. Without `data-ui="bootstrap"`, `assets/css/bootstrap-theme.css` undoes Bootstrap's base reset so these pages look exactly as designed, while Bootstrap components and icons (`<i class="bi bi-...">`) are available.
- Notices use the class `cs-toast`, not `toast`, because Bootstrap hides `.toast` elements.

## How the dashboard gets data

- Every figure comes from the platform API. There is no demonstration or sample data in the pages.
- The planner connects on load. If the API answers, the sidebar shows **LIVE DATABASE** and the page refreshes every 15 seconds; a notice appears when new Act Now items arrive.
- Without a connection the pages show dashes and a notice that says why: **Sign in** (no session), **no access** (role cannot open the page) or **platform not reachable** (with a Reconnect button).
- To use a different API, add `?api=https://host/api/v1` to the address. Links between pages keep this setting.

## Dashboard pages

Each sidebar item is its own page. All of them load `js/app.js`, which reads `<body data-page>` and fetches only that page's data:

| Page | File | Features |
| --- | --- | --- |
| Overview | `planner.html` | Greeting hero, key figures, module grid with live counts |
| Act now | `act-now.html` | Prioritised queue, filters, case dialog (assign, act, notify the cell) |
| Field channels | `channels.html` | Message feed with type filters, asset report form, farmer codes |
| Scheme performance | `schemes.html` | Harvest against target; **Manage schemes** tab to add and edit schemes (administrators) |
| Trends | `trends.html` | Four 12-month charts, totals, table view |
| Irrigation advice | `advice.html` | Advice by sector, decision rules, send advice by SMS |
| Household nutrition | `nutrition.html` | Stunting risk gauge and risk by cell |
| Map & observations | `map.html` | Full-page map with layer chips |
| Community feedback | `feedback.html` | Grievance list with search and status filters, response health |

## Interactions

- **Act Now:** filter by type, open a case or grievance, set status, owner, action and deadline, see the history, then **Notify the community by SMS** (preview first, then send).
- **Irrigation advice:** preview, then SMS each sector's advice to its cooperatives.
- **Map:** layer chips for schemes, infrastructure, crop reports, pest heatmap, rainfall and drought, nutrition risk, and farmers.
- **EN / RW** switch on every page. Kinyarwanda strings live in `assets/js/shared.js` and should be reviewed by the field team.
- **Export** in Platform Management downloads the visible rows as CSV.

# CS-IRCFS web pages

FastAPI serves this folder at `/`, so the pages and the API share one address and no separate web server is needed. Start the platform with `..\start-local.ps1` (or `..\start-local.ps1 -Demo` for sample data) and open `http://127.0.0.1:8000`.

| File | Page |
| --- | --- |
| `index.html` | Public home page: live totals, sector map with irrigation advice, how it works, FAQ |
| `planner.html` + `app.js` + `planner-extra.css` | District dashboard |
| `trends.js` | Twelve-month trend charts on the dashboard |
| `report.html` | Monthly district report (print or save as PDF) |
| `simulator.html` + `simulator.js` + `simulator.css` | Feature-phone simulator for USSD `*801#` and SMS `8448` |
| `management.html` + `management.js` | Platform Management: data tables, forms, accounts |
| `login.html`, `register.html` | Staff sign-in and registration |
| `backend-console.html` | Technical console for developers |
| `shared.js` + `shared.css` | Used by every page: API calls, sign-in session, EN/RW switch, notices, dialogs |
| `bugesera-boundary.geojson` | District outline for the map |

## How the dashboard gets data

- On load, the dashboard tries the API straight away. If the API answers, the badge shows **LIVE DATABASE** and the page refreshes every 15 seconds. A notice appears when new Act Now items arrive.
- If the API needs sign-in, the page shows labelled **demonstration data** until someone signs in with a District Planner, officer or administrator account. A service API key can still be pasted through **Connect live data**.
- To use a different API, add `?api=https://host/api/v1` to the address. Links between pages keep this setting.

## Interactions

- **Act Now:** filter by type, open a case or grievance, set status, owner, action and deadline, see the history, then **Notify the community by SMS** (preview first, then send).
- **Irrigation advice:** preview, then SMS each sector's advice to its cooperatives.
- **Map:** layer chips for schemes, infrastructure, crop reports, pest heatmap, rainfall and drought, nutrition risk, and farmers.
- **EN / RW** switch on every page. Kinyarwanda strings live in `shared.js` and should be reviewed by the field team.
- **Export** in Platform Management downloads the visible rows as CSV.

# CS-IRCFS Planner Dashboard

The dashboard starts in demonstration mode, allowing the competition story to be shown before the live USSD gateway and official scheme data are ready. Click **Connect local API** to load the running FastAPI backend's dashboard summary and Act Now queue.

The Scheme selector lists records from PostgreSQL in live mode. PADAB and APEFA Solar are seeded as inactive reference names, so they appear with a **reference** label; their area, yield targets, and boundaries remain unverified and blank. In demonstration mode, the dropdown shows the same scheme names while the separate data-source badge identifies the sample data. The selector filters Act Now rows and map features; overview totals remain district-wide.

In local API mode, use **Simulate an irrigation report** to submit an offline or faulty asset. Open the resulting Act Now case, set its status and action, and record a simulated SMS response after resolving it. This records a notification timestamp; it does not contact a phone. The scheme filter applies to Act Now items. Scheme outcome and response-health panels remain placeholders until verified data and calculation rules exist.

If the API requires a key, click **Connect local API** and enter the administrator key from the ignored project `.env` file. The key is kept in this browser tab's session storage. A custom API endpoint can be selected with `?api=http://127.0.0.1:8002/api/v1`; the link to Platform Management preserves that choice.

On the management page, **Export** downloads the currently visible table rows as UTF-8 CSV. Search-hidden rows are excluded. The filename identifies whether the rows came from PostgreSQL or from demonstration data; an empty table exports headers only.

**Add** now opens forms for users, irrigation schemes, citizen reports, rainfall/irrigation reports, and community feedback. These forms save to the PostgreSQL API after connection; foreign-key ID fields must refer to existing records. The Analytics button opens the planner's Act Now queue, while Analytics export downloads the visible queue rows.

## Run locally

1. Start the API from `../backend`: `python -m uvicorn app.main:app --reload`.
2. From this folder, serve the dashboard: `python -m http.server 8080`.
3. Open `http://127.0.0.1:8080`.

The production GIS step will replace the illustrated map with a Leaflet map and verified PADAB/APEFA boundaries, assets, and observation layers.

## Technical Operations Console

Open `http://127.0.0.1:8080/backend-console.html` only for a technical explanation of the backend flow, live API status, stored-report totals, urgent queue count, and direct links to each readable endpoint. District Planners should use the main dashboard. The default FastAPI `/docs` page remains available for developers who need to test POST/PATCH requests.

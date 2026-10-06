# Presentation demo script (about 10 minutes)

## Before you present

1. In VS Code, open **Terminal → Run Task → CS-IRCFS: Start demo**, or run `.\start-local.ps1 -ResetDemo` for fresh data.
2. In the browser, open two tabs:
   - **Tab A:** `http://127.0.0.1:8000/planner.html`
   - **Tab B:** `http://127.0.0.1:8000/simulator.html`
3. Check that the sidebar badge says **LIVE DATABASE**. If it says demonstration data, the platform is not running.
4. Zoom the browser to 90% so whole panels fit on the projector.

The demo data is invented and labelled as such. Say so once at the start: *"These are demonstration records; targets are placeholders until the feasibility-study figures are confirmed."*

## The story

| # | Show | Say |
| --- | --- | --- |
| 1 | **Home page** (`/`): *How it works* | "Citizens are the sensors. No smartphone or internet is needed: a farmer dials *801# or texts 8448." |
| 2 | **Tab A**: press **▶ Presentation tour**, then step through 1–3 | Overview figures, field channels, and the automatic Act Now triage. |
| 3 | **Tab B**: choose a Citizen Science Monitor, press **Dial** and answer `2` → `2` → `1` → `5` | "A fall-armyworm report on maize, severity 5, in Kinyarwanda. The English translation is under the phone." Point at **✓ Saved: Crop report**. |
| 4 | **Tab A**: within 15 seconds a notice says "1 new item in Act Now" | "The report is already a critical case. No one typed anything into the dashboard." |
| 5 | **Tab B → SMS tab**: tap `IMVURA 12`, then `NYAMATA NZANA 5` | "Rain-gauge readings and keyword alerts. Every report gets an answer back with local advice: that is our Local Insights mechanic. Every third weather report earns 100 RWF airtime." |
| 6 | **Tab A → Scheme performance** | "Objective 1: farmer-reported harvest compared with each scheme's yield target. Objective 2: PADAB's recurring *technical* bottleneck is flagged automatically." |
| 7 | **Irrigation advice → Send advice to cooperatives** (preview only) | "The Irrigation Scheduling Assistant turns 7-day rainfall into SMS advice per sector. Ngeruka and Mareba are in a dry spell." Press **Cancel**, or send it. |
| 8 | **Household nutrition** | "Three USSD questions give a stunting-risk score, so we can see which cells need attention." |
| 9 | **Map**: switch on *Pest heatmap*, then *Rainfall & drought*, then *Nutrition risk* | "The same evidence, by location." |
| 10 | **Act Now → Feedback filter → Open** a *Resettlement/Downstream Impact* case → set **Resolved** with an action → **Save** → **Notify the community by SMS** → **Send** | "Closing the loop: everyone registered in that cell is told what was done. That is what keeps people reporting." |
| 11 | **RW** switch at the top right | "The interface is bilingual, and the phone menus are Kinyarwanda first." |
| 12 | **Platform Management → Irrigation schemes → Edit figures** | "When the official feasibility-study target is confirmed, the planner enters it here, with its source, and verification uses it straight away." |

## If something goes wrong

| Problem | Fix |
| --- | --- |
| The badge shows *Demonstration data* | The platform is not running. Start the demo task and refresh. |
| The map is blank grey | There is no internet for the map tiles. The markers and panels still work; explain that the base map needs a connection. |
| You want a clean slate | `.\start-local.ps1 -ResetDemo` |

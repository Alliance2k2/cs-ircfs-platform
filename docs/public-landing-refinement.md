# Public landing refinement - 3 November 2026

> Historical proposal, superseded at the user's request. The original page layout has been restored; see [current interface changes](current-interface-changes.md). Test results below describe that earlier proposal.


Branch: `feature/public-landing-refinement`. Local work only; no commit, push, merge or deployment. Previous uncommitted redesign and unrelated files were retained. A source snapshot is in ignored `backend/.pytest-tmp/refinement-before/`.

## Changes

- Exact requested headline, concise purpose and navigation branding; announcement strip, duplicate context strip, closing workflow and footer emblem removed.
- Nine sections in requested order: hero, challenge, research, workflow, technology, pilots, evidence, stakeholders, FAQs.
- Three photographic research cards with consistent aspect ratios. PADAB Mwesa Valley and APEFA Ngeruka/Mareba have paired photographic cards and explicit evaluation requirements.
- All pilot photographs are labeled Rwanda context, not actual pilot sites. No hectares, yields, operational coverage or outcomes invented. Official source documents and actual site photographs remain inputs for district confirmation.
- Phone walkthrough remains manual, keyboard accessible and explicitly illustrative; it sends nothing. Staff simulator, authentication and `/app/` links retained.
- Public activity and readiness now belong to the scientific evidence section. Public aggregation behavior and privacy safeguards retained.
- Forest green, primary green, mint, water blue, Manrope and DM Sans retained. Local optimized images/fonts, responsive layouts, lazy images and reduced-motion behavior retained.

## Modified files

Current refinement: `dashboard/index.html`, `dashboard/assets/css/landing.css`, `dashboard/assets/js/public-copy.js`, `dashboard/photography.html`, `dashboard/privacy.html` (stylesheet cache revision), three `dashboard/assets/img/public/community*` derivatives, `frontend/e2e/14-public-website.spec.ts`, `frontend/scripts/capture-public.mjs`, this report and `docs/images/public-refinement/`.

Earlier uncommitted redesign files remain listed in [the previous report](public-website-redesign.md); no backend business logic, authentication, API, migration or production configuration changed here.

## Photography

New community photo: [Rwanda GV4 lo](https://commons.wikimedia.org/wiki/File:Rwanda_GV4_lo_(4108941860).jpg), Neil Palmer / CIAT, 9 November 2009, farmers near Gatuna; [CC BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0/). Downloaded from the source record, inspected, resized and recompressed to 640/1000px WebP and JPEG; display crop disclosed and derivatives retain the license.

Existing Rwanda images and credits: [public photography page](../dashboard/photography.html) and [original report](public-website-redesign.md). No image represents CS-IRCFS participants or documented pilot conditions. No licensed actual pilot infrastructure/solar installation photograph was available in the repository; context photographs are explicitly labeled rather than presented as site evidence.

## Review artifacts

Before images were preserved from the immediately preceding local redesign capture, rather than recreated from Git HEAD: [desktop](images/public-refinement/before-desktop.jpg), [mobile](images/public-refinement/before-mobile.jpg).

After: [desktop](images/public-refinement/width-1440.jpg), [mobile](images/public-refinement/width-390.jpg), [Kinyarwanda mobile](images/public-refinement/kinyarwanda-390.jpg). Also includes 360, 768 and 1024px captures. All show isolated synthetic data. [Machine-readable measurements](images/public-refinement/verification.json).

## Validation

Completed checks so far:

- Public browser suite: **16 passed** (five role sign-in setups plus eleven public checks). Includes phone walkthrough, route availability, protected API boundary, empty/error activity, keyboard controls, five widths in English/Kinyarwanda, no-JavaScript reading and Axe scans on all three public pages.
- Backend security and simulator profiles: **26 passed**, one existing Starlette/httpx deprecation warning (73.04 seconds).
- ESLint: passed.
- Static validation: exact nine-section order, no top strip, all local links/assets and fragment targets resolve.
- Initial screenshots: all five widths had zero broken images and zero horizontal overflow. One cold-cache mobile lab navigation: LCP 2,576ms, FCP 2,460ms, CLS 0.000005745; 319,349 resource bytes, 14 requests, zero third-party requests. This is a single local lab run, not field Core Web Vitals.
- Normal local server `http://127.0.0.1:8000/` returned HTTP 200 and the new headline.

Broader validation:

- TypeScript and production Vite build: passed (2,310 modules). Existing runtime font-path notices and large Mapbox chunk warning remain; the public page does not load this application bundle.
- Full browser suite: **33 passed, 2 failed** in one 15.4-minute run. Failures: `03-priority-actions` did not observe the Saved toast within 30 seconds; `06-climate-advice` remained in Loading rather than showing its advice table within 30 seconds. All eleven public checks passed again, including final order assertions.
- Full frontend unit suite: **57 passed, 2 failed** across 16 files. The nutrition privacy and field-report origin tests timed out finding a table while the page was still Loading. Focused rerun of the two affected unit files: **9 passed** (18.79 seconds). All 59 unique unit tests therefore passed across the full run and focused rerun, but the original full run was not clean. No staff implementation was changed to mask these failures.
- Staff workflow focused rerun: **7 passed, 1 failed**. Case resolution passed. Climate advice reached preview but expected three sectors while later full-suite tests had added Rweru as a fourth sector. This is shared-fixture contamination when rerunning against an already-mutated database. Fresh-fixture climate rerun: **7 passed** (five role setups plus both climate checks, 37.3 seconds). All 35 unique browser checks passed across the full run and targeted reruns; do not describe the initial full run as 35/35.

 The first build/unit attempts were blocked by sandbox `spawn EPERM`; reruns use subprocess permission. An initial backend attempt from the repository root could not import `app`; the successful run above used the backend directory. A concurrent screenshot refresh timed out during heavy validation; initial captures remain available. Native Kinyarwanda review and official pilot source confirmation remain necessary before field publication. Automated accessibility checks cannot certify all WCAG 2.2 AA requirements; human/device review remains appropriate.


Final screenshots were refreshed after all content changes: five widths, zero broken images, zero horizontal overflow. Final single mobile lab run: LCP 5,320ms, FCP 4,204ms, CLS 0.000005745, 319,834 resource bytes, 14 requests, zero third-party requests. Loading remains a performance follow-up: the earlier 2.58-second result varied to 5.32 seconds in this run, so this does not establish good loading Core Web Vitals. Confirm on deployed hosting and representative mobile hardware. Final `git diff --check` passed; only Windows line-ending notices appeared. No remote actions were performed.

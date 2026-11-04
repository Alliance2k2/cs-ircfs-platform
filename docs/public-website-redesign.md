# Public website redesign — 3 November 2026

> Historical proposal, superseded at the user's request. The original page layout has been restored; see [current interface changes](current-interface-changes.md). Test results below describe that earlier proposal.


## Initial audit

Branch at inspection: `feature/platform-modernization`, head `491c56a`. The only untracked user file is `create_motivational_letter_pdf.py`; it is unrelated and will remain untouched. Redesign branch: `feature/public-landing-redesign`. No push, merge or deployment is authorized for this work.

FastAPI mounts `dashboard/` at `/` after the API and React `/app/` routes. The public page is `dashboard/index.html`, styled by `assets/css/landing.css` and driven by `assets/js/landing.js`. Shared JavaScript provides classic sign-in/session utilities. Public activity comes from unauthenticated `/api/v1/public/overview`, which returns aggregates and sector summaries, excludes simulator records and identifies demonstration mode. No protected records need to be fetched by the landing page.

Reusable foundations: established green/blue/amber palette, locally served Manrope/DM Sans, existing logo, local Bootstrap Icons, authentic Kinyarwanda phone-menu content, privacy notice, public aggregates and existing authentication/simulator destinations. The internal dashboard and all backend services remain outside this visual change.

The two root-level WhatsApp JPEGs are design-reference collages with illustrative interface figures, not verified documentary pilot photographs. They were inspected but were not reused as field evidence or as the public dashboard preview. The existing identity is retained; the new preview is captured from the real application with synthetic fixtures.

Weaknesses: the autoplay UHD third-party video dominates essential rendering and bandwidth; animated orbits and a large emblem compete with the message; four hero actions dilute the next step; external stock pictures have no visible source/license trail and repeat; some copy implies active telecom and immediate results; evidence review, missing baselines and project status are insufficiently explained. Language switching traverses raw text nodes, so new content and dynamic updates are hard to maintain. There is no focused public-page browser coverage.

## Information architecture and implementation plan

1. Header: About, How it works, Research areas, Pilot sites, FAQs, EN/RW selection and a distinct staff entry.
2. Editorial hero: one clear project statement, local responsive photograph, project and workflow actions, geographic context and honest pilot label.
3. About/problem: water, timely observations and the need to close the feedback loop.
4. Five-step workflow: report, organize, review, act, communicate.
5. Three research areas: food security, irrigation/climate and community accountability.
6. Intended pilot context: PADAB Mwesa Valley and APEFA in Ngeruka/Mareba, without invented geographic boundaries or outcomes.
7. Technology: a controllable, illustrative feature-phone walkthrough and a real application capture using synthetic data only.
8. Scientific trust: report/evidence labels, approved references and truthful missing-data explanations.
9. Public activity: the existing aggregate endpoint, with distinct loading, demo, empty and unavailable states.
10. People: six stakeholder roles, without granting access outside existing authentication.
11. Status, FAQ and footer: capabilities versus activation/field validation, privacy and photography credits.

Implementation is buildless HTML/CSS/JavaScript in the existing public files. Page content will use explicit translation keys; Kinyarwanda drafts remain identified as requiring native review. No new animation framework or runtime external media dependency is needed. Related public privacy/photography pages share the refined presentation. Responsive and keyboard tests will cover 360, 390, 768, 1024 and 1440 px; screenshots, actual commands/results and image provenance will be recorded here after verification.

## Delivered design

The hero now leads with the reporting purpose and a credited farmer photograph, two project-exploration actions and a separate staff entry. The full project name is retained in the footer. The page follows the outline above, with six stakeholder roles, nine FAQs and explicit distinctions between developed software, demonstrations, provider activation and district validation. No new impact statistics, endorsements, locations or partnerships were invented.

The old external autoplay videos, animated orbits, ticker and decorative layers are removed. Nothing essential depends on a third-party media host. Four licensed context photographs have local responsive WebP versions and JPEG fallbacks; below-the-fold images load lazily. The feature-phone walkthrough advances only when requested and submits nothing. A real dashboard capture uses an isolated seeded test database, with visible synthetic-data labeling. The public aggregation endpoint is unchanged; loading, zero-record, demonstration, unavailable and retry states are separate. Database labels are inserted as text, not HTML.

Language copy is explicitly keyed in `public-copy.js`. EN/RW switching persists and is synchronized with the classic helper's language state. Kinyarwanda is a draft and carries a visible native-review notice. The privacy and photography reference pages remain in English. No claim of native acceptance or complete accessibility certification is made.

### Preserved boundaries

FastAPI routes, database connections/schema, authentication, approval rules, backend channel workflows and the React `/app/` workspace are unchanged. The public page does not fetch private staff endpoints. Staff sign-in, registration, the protected simulator, privacy and dashboard destinations remain linked. Existing classic session/query-API helpers remain in use. The privacy notice's retention/anonymity wording now describes the actual policy prerequisites and operational limitations instead of implying a published policy already exists.

### Files

| File or directory | Change |
| --- | --- |
| `dashboard/index.html` | Public information architecture, source/status labels and semantic markup |
| `dashboard/assets/css/landing.css` | Public layout, responsive rules, focus, print and reduced motion |
| `dashboard/assets/css/public-fonts.css` | Existing local fonts with an optional loading policy to avoid late text movement on slow connections |
| `dashboard/assets/js/landing.js` | Accessible menu, language synchronization, manual phone walkthrough and aggregate activity states |
| `dashboard/assets/js/public-copy.js` | Explicit English/Kinyarwanda draft catalog |
| `dashboard/assets/css/public-icons.css`, `assets/fonts/public-icons.woff2` | 36-glyph subset of existing Bootstrap Icons, 4,104-byte font plus small CSS |
| `dashboard/assets/img/public/` | Local licensed photo derivatives and synthetic dashboard capture |
| `dashboard/privacy.html`, `dashboard/photography.html` | Related public reference presentation, truthful privacy text, image credits/licenses |
| `frontend/e2e/14-public-website.spec.ts` | Public interaction, layout, failure, no-JS and Axe checks |
| `frontend/scripts/capture-public.mjs` | Reproducible synthetic-only screenshots and mobile lab measurement |
| `frontend/package.json`, `package-lock.json` | Development-only Axe helper; no new public runtime framework |
| `docs/images/public-redesign/` | Screenshots and measured verification JSON |
| `README.md`, `docs/design-system.md`, this document | Review guide and design documentation |

### Image inventory and licenses

All local photo derivatives retain their original license. Resizing, WebP/JPEG recompression, metadata removal and display cropping are disclosed in the public photography page. These photographs show other Rwandan locations, not PADAB/APEFA sites or CS-IRCFS participants. Photographer use does not imply endorsement.

| Local basename / placement | Photographer / original | License |
| --- | --- | --- |
| `maize` / hero | Neil Palmer / CIAT, [Rwanda maize, Nyagatare](https://commons.wikimedia.org/wiki/File:Rwanda_maize_lo_(4108178537).jpg), 2009 | [CC BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0/) |
| `landscape` / project explanation | Baloona, [Farm outside Kigali](https://commons.wikimedia.org/wiki/File:Farm_outside_of_Kigali,_Rwanda.jpg), 2011 | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| `sunset` / food-security research | Peace Batuma, [Maize plantation with sunset view](https://commons.wikimedia.org/wiki/File:Maize_plantation_with_sunset_view.jpg), 2022 | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| `rice` / irrigation-climate research | Irakoze (Clronin7), [Karongirice2, Karongi](https://commons.wikimedia.org/wiki/File:Karongirice2.jpg), 2020 | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| `dashboard-preview.webp` / technology | Actual CS-IRCFS application capture, isolated synthetic E2E environment | Repository application artwork; no real participant data |
| Community feedback illustration | Original HTML/icon composition, explicitly labeled illustration | Repository artwork with MIT-licensed Bootstrap Icons |

No AI documentary imagery was created. Existing logo and local typography are retained. Bootstrap icon license: `dashboard/assets/vendor/bootstrap-icons-1.11.3/LICENSE`; original classic assets are untouched. Pillow and FontTools were development-only preparation tools and were not added to backend runtime requirements.

## Review locally

The existing local platform at **http://localhost:8000/** serves the redesign immediately. Refresh the page; use Ctrl+Shift+R if an old stylesheet is cached. If the platform is stopped, run `./start-local.ps1 -Demo` from the repository root. This keeps the existing separate demonstration database and does not activate telecom.

To reproduce synthetic captures, start `./.venv/Scripts/python.exe backend/scripts/run_e2e_server.py --port 8772`, then run `node scripts/capture-public.mjs` from `frontend/`. The capture script refuses to use a participant/production URL and waits for the demonstration badge. Stop that temporary server afterward. The normal local platform need not be stopped.

Screenshots: [desktop 1440](images/public-redesign/width-1440.jpg), [laptop 1024](images/public-redesign/width-1024.jpg), [tablet 768](images/public-redesign/width-768.jpg), [mobile 390](images/public-redesign/width-390.jpg), [mobile 360](images/public-redesign/width-360.jpg), [Kinyarwanda mobile](images/public-redesign/kinyarwanda-390.jpg). Measured values and capture conditions are in [verification.json](images/public-redesign/verification.json). They are local lab observations, not real-user Core Web Vitals or an invented Lighthouse score.

## External dependencies and limits

Native Kinyarwanda review, real pilot-site photography with appropriate permission, district acceptance, telecom activation and actual hosted performance/availability remain external work. Automated checks cannot replace screen-reader/usability sessions with local users. No production configuration, migrations, authentication bypasses, remote pushes, merges or deployments were made for this redesign.

## Commands executed and actual verification

- Backend: `python -m pytest --basetemp=.pytest-tmp/public-redesign-final -o cache_dir=.pytest-tmp/public-redesign-cache -q` — **298 passed**, with 12 existing dependency deprecation warnings. Databases were isolated test fixtures.
- Frontend: `npm test -- --maxWorkers=1 --no-file-parallelism --testTimeout=60000 --retry=1` — **59 passed in 16 files**. Earlier runs under concurrent local load had timeout failures. The final run used a larger local timeout and one retry; one test needed its retry. Application assertions and production timeouts were not weakened.
- `npm run lint`, `npm run build` — passed. Build includes both TypeScript projects. Existing public-font path/build notices and the large Mapbox chunk notice remain; this redesign does not change the dashboard bundle.
- `node --check dashboard/assets/js/landing.js`, `node --check dashboard/assets/js/public-copy.js`, `node --check frontend/scripts/capture-public.mjs` — passed.
- Focused public browser suite: **16 passed**, including five role sign-in setup checks plus eleven public tests. It covers both languages at 360/390/768/1024/1440 px, keyboard navigation, persistence, real public aggregates and links, failure/retry/zero states, HTML-safe labels, no protected API requests and no-JavaScript/external-media fallback.
- Axe: no automated WCAG A/AA violations in the landing page, privacy notice or photography credits. This is automated coverage, not a WCAG certification or a substitute for assistive-technology testing.
- Complete browser suite: **34 passed, one sign-in page-render wait timed out** on the first full run. The focused sign-in/sign-out rerun then passed (six checks including role setup), so every one of the 35 checks was exercised successfully across those runs. No authentication code was changed to address the local timing failure.
- Local test-server startup also hit contention/port cleanup delays. The complete browser verification used the existing isolated synthetic server on port 8772 through a temporary local config, with 120-second test and 30-second expectation waits for the focused rerun. CI configuration remains unchanged. Equivalent browser command: `npx playwright test --config ../backend/.pytest-tmp/playwright-review.config.ts`; this temporary config is not a deployment artifact. Normal clean-machine command remains `npm run e2e` after `npm run build`.
- Actual rendered desktop, tablet and mobile captures were inspected. Their measured document width equals the viewport width and all images loaded. `git diff --check` passed.

Performance figures are preserved verbatim in `images/public-redesign/verification.json`. The capture command is `node scripts/capture-public.mjs`, using a fresh Chrome context, cold cache, a 390 px viewport, 1.6 Mbps download, 150 ms latency and 4× CPU slowdown. The final capture is performed after the test workers finish. No hosted or real-user performance score is asserted.

| Final mobile lab observation | Measured value |
| --- | --- |
| First contentful paint | 8.636 s |
| Largest contentful paint | 9.200 s |
| Cumulative layout shift | 0.000005745 |
| Initial transferred resource bytes | 316,911 bytes (about 317 kB) |
| Resource requests / third-party requests | 14 / 0 |

The initial resource total fell from roughly 527 kB before icon subsetting to roughly 317 kB, and the final font policy kept layout shift close to zero in this navigation. **Throttled loading speed remains a performance follow-up**: this run does not demonstrate good loading Core Web Vitals. Profile on the actual hosted deployment and representative lower-cost Android devices before making that claim. Do not interpret the local Windows lab timing as a production SLA or a Lighthouse score.

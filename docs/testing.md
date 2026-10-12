# Testing

Four layers, all run by CI (`.github/workflows/ci.yml`) on every pull request and every push to `main`.

| Layer | Where | Command | What it proves |
| --- | --- | --- | --- |
| Backend | `backend/tests/` (pytest) | `cd backend && python -m pytest -q` | API rules, roles, privacy, metrics, USSD/SMS flows, migrations on SQLite |
| Migrations on PostGIS | CI job "Migrations on PostGIS" | (CI only) | A fresh PostGIS database upgrades to head, matches the models (blocking), downgrades one step and upgrades again, and accepts the seed scripts. On SQLite, `test_every_name_fits_postgresql` catches identifiers longer than PostgreSQL's 63 characters |
| Frontend unit | `frontend/src/**/*.test.tsx` (Vitest, Testing Library) | `cd frontend && npm test` | Components and pages against stubbed API answers: states, validation, access, privacy display |
| Browser end-to-end | `frontend/e2e/` (Playwright) | `cd frontend && npm run build && npm run e2e` | Ten workflows in a real browser against a real server |

`npm run typecheck` and `npm run lint` cover the end-to-end tests too.

## Browser end-to-end tests

Playwright starts `backend/scripts/run_e2e_server.py`, which:

- creates a temporary SQLite database with Alembic and adds the demonstration data;
- creates one active account per role (`admin@e2e.test`, `planner@e2e.test`, `officer@e2e.test`, `monitor@e2e.test`, `leader@e2e.test`, password `e2e-password-2026`; these exist only in that temporary file);
- runs with real sign-in (`ENVIRONMENT=staging`, `REQUIRE_API_KEY=true`);
- forces SMS and airtime to dry-run and turns off the weather forecast, Mapbox, staff alerts and the weekly scheduler, whatever the project `.env` contains;
- refuses to seed any database other than its own temporary file.

So the tests cannot send a message, charge airtime, or change a shared database.

| # | File | Workflow |
| --- | --- | --- |
| 1 | `01-sign-in.spec.ts` | Sign in returns to the requested page; sign out ends the session; a wrong password is refused |
| 2 | `02-roles.spec.ts` | A monitor gets no staff tools and sees masked data; a cooperative leader starts on field reports |
| 3 | `03-priority-actions.spec.ts` | Resolve a case (action required), assign, set a deadline, see the history, preview and send the closing-the-loop SMS |
| 4 | `04-field-reports.spec.ts` | Reject needs a reason; verify a report and find it among verified reports; CSV export has no phone numbers |
| 5 | `05-grievances.spec.ts` | Work a grievance through to resolution without any phone number shown; preview the cell message |
| 6 | `06-climate-advice.spec.ts` | Preview, cancel, then send weekly advice; officers cannot send |
| 7 | `07-simulator.spec.ts` | Register a caller's location, send a USSD rain reading and an SMS; they show in operations as simulator data and never in field reports |
| 8 | `08-accounts.spec.ts` | Register, refused until approved, approve with confirmation, change role, sign in, audit log entry |
| 9 | `09-evaluation.spec.ts` | A baseline without a source is refused; with a source the evaluation shows it as documented and yield achievement stays "not computable" with reasons; CSV export |
| 10 | `10-navigation-reports.spec.ts` | Ctrl+K search, breadcrumbs, trends table, monthly report by month, nutrition privacy notice, map without a token, language switch |

Locally the installed Google Chrome is used. Set `PYTHON` to the interpreter with the backend requirements, for example on Windows:

```powershell
cd frontend
npm run build
$env:PYTHON = "..\.venv\Scripts\python"; npm run e2e
```

On failure Playwright keeps a trace and a screenshot in `frontend/test-results/`; CI uploads them as the `playwright-report` artifact.

## Writing a new test

- Unit tests render with `renderWithProviders` and stub the API with `stubApi` (`frontend/src/test/render.tsx`); the longest matching path prefix answers.
- End-to-end tests sign in through `asRole("planner")` from `e2e/fixtures.ts`. Workflows run one at a time because they change shared server state. Prefer role and label locators; tables render both a desktop table and phone cards, so scope queries to `getByRole("table")`.

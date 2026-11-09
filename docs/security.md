# Security and privacy

> November hardening: database errors exclude SQL parameters; structured request logs replace raw Uvicorn URLs; channel bodies/IDs are bounded; production wildcard CORS is refused; local auth and backup artifacts are excluded from Docker context. Provider key rotation and proxy log redaction still require owner action. See [the validation report](engineering-validation-2026-11-06.md).

> Current implementation and operator instructions: [November completion](platform-completion-2026-11.md). This supersedes earlier remaining-work lists; official data, native review, telecom acceptance and hosted verification still require external inputs.

This page records the platform's security decisions, the settings that enforce them, and what is still open. It was written during the October 2026 audit ([audit-2026-10.md](audit-2026-10.md)).

## What the platform protects

| Data | Who may see it | How |
| --- | --- | --- |
| Phone numbers of farmers and monitors | District officers, planners, administrators | Masked (`+250 7•• ••• 456`) for monitors and cooperative leaders in the channel feed; field-user, message and reward lists are staff-only |
| Message text (USSD/SMS) | District officers, planners, administrators | Hidden from monitors and cooperative leaders |
| Grievances | District staff, without the sender | `reporter_id` is never stored; the USSD session and the SMS acknowledgement are logged with the phone `withheld` |
| Household nutrition answers | District officers, planners, administrators | `/nutrition-surveys` is staff-only; monitors see the anonymised aggregate (`/analytics/nutrition-summary`) |
| Public home page | Anyone | Counts and sector names only (`/public/overview`) |

Area-level access (sector-limited accounts) applies to records; district totals stay district-wide because they contain no personal data. See [roadmap.md](roadmap.md) limitation 5.

## Threats and controls

| Threat | Control | Where |
| --- | --- | --- |
| Forged USSD/SMS reports posted to the public callbacks | Shared secret in the callback URL (`GATEWAY_CALLBACK_TOKEN`, constant-time compare); optional provider IP allow-list (`GATEWAY_ALLOWED_IPS`). Africa's Talking does not sign callbacks, so this is the provider-supported approach | `routes/channels.py` `verify_gateway` |
| One client flooding the callbacks | 30 messages a minute **per phone number**, counted in the database (shared by all workers). An IP limit would throttle all real traffic, which arrives from a few gateway addresses | `routes/channels.py` `throttle` |
| Gateway retries creating duplicate reports | Retries with the same USSD `sessionId`+text or SMS `id` replay the stored reply | `routes/channels.py` |
| Simulator tests polluting evidence or costing money | Simulator has its own signed-in endpoints; its records are `data_origin = simulator` and excluded from figures; SMS and airtime are forced to dry-run inside the simulator, whatever the provider settings | `routes/channels.py`, `services/sms.py` `simulation()` |
| Anyone on the internet self-registering and reading field data | New accounts (email or Google) start **pending**; an administrator activates them in Administration → Accounts (`/app/admin`), after a confirmation, and the change is audited. The pending status is only revealed to someone who knows the password | `routes/auth.py` |
| Password guessing | PBKDF2-SHA256 (210 000 rounds), 10 sign-in attempts a minute per client address | `routes/auth.py` |
| Session theft | Random 256-bit tokens, only a SHA-256 hash stored, httpOnly + SameSite=Lax cookie, `Secure` required in production, sessions deleted on suspension and logout | `core/security.py`, `routes/auth.py` |
| Rate limits defeated or shared behind a proxy | uvicorn runs with `--proxy-headers`; `FORWARDED_ALLOW_IPS` names the trusted proxy (`*` on Render, `127.0.0.1` by default) | `Dockerfile` |
| Unsafe deployment settings | `ENVIRONMENT=production` refuses to start without `REQUIRE_API_KEY=true`, PostgreSQL, `COOKIE_SECURE=true`, a CORS list free of localhost, and a `GATEWAY_CALLBACK_TOKEN` of at least 24 characters | `core/config.py` `guard_runtime` |
| Clickjacking, MIME sniffing, referrer leaks | `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`; HSTS in production | `main.py` `security_headers` |
| Development auth bypass reaching a server | The bypass only exists when `ENVIRONMENT=development` and `REQUIRE_API_KEY=false`, and logs a warning at startup | `core/security.py`, `main.py` |
| Chargeable messages during tests | The test suite forces `SMS_PROVIDER=dry_run` and `AIRTIME_PROVIDER=dry_run`; the browser end-to-end server also clears provider credentials, staff alerts, the forecast and Mapbox, and seeds only its own temporary SQLite file | `tests/conftest.py`, `scripts/run_e2e_server.py` |
| Untraceable staff changes | Account, case, grievance, verification, scheme, export and advice-send actions are written to the append-only `audit_events` table, readable in Administration → Audit log | `services/audit.py` |
| Re-identifying households from small groups | Nutrition scores are hidden for any cell (and any month in trends) with fewer than five households; the map only draws cells above that size | `services/analytics.py`, `services/reporting.py` |
| Locations and notes leaking through maps, or invented positions | `/map-data` draws only recorded GPS points and counts the rest; farmers' names and home locations, report notes and fault descriptions go to district staff only; `/geography/farmers` is staff-only; simulator tests are left out | `routes/map_data.py`, `routes/geography.py` |
| Pages showing data a role must not see | The dashboard hides pages by the same role rules the API enforces; the API is the protection | `frontend/src/app/access.tsx` |

Every control above has an automated test in `backend/tests/test_security.py` or `test_auth.py`.

## Settings

| Setting | Production value |
| --- | --- |
| `ENVIRONMENT` | `production` (use `staging` for a local PostgreSQL with real sign-in) |
| `REQUIRE_API_KEY` | `true` |
| `COOKIE_SECURE` | `true` (HTTPS only) |
| `CORS_ORIGINS` | empty when the dashboard is served by the API |
| `GATEWAY_CALLBACK_TOKEN` | a random secret of 24+ characters, also in the Africa's Talking callback URLs |
| `GATEWAY_ALLOWED_IPS` | optional: Africa's Talking callback addresses |
| `FORWARDED_ALLOW_IPS` | the address of the trusted proxy |
| `MAPBOX_ACCESS_TOKEN` | a **public** Mapbox token (`pk.`), restricted to the site's URLs in Mapbox; it is visible to browsers by design, and secret `sk.` tokens are refused |

## Open items

1. **Content Security Policy.** The legacy HTML pages use inline scripts and load Mapbox GL from unpkg, so a strict CSP would break them. Add one when the React app replaces them.
2. **Data protection impact assessment.** Rwanda's Law N° 058/2021 on the protection of personal data and privacy requires a lawful basis, purpose limitation and, for this kind of processing, registration with the National Cyber Security Authority. The district should complete the DPIA and registration before the pilot; this repository cannot do that.
3. **Retention.** No automatic deletion of inbound messages or sessions yet. Decide retention periods with the district and add a scheduled clean-up.
4. **Sign-in throttling per account.** The limit is per client address; add a per-email lockout if password guessing is seen.
5. **Audit log of staff reads.** Changes and CSV exports are audited; reads of personal data on screen are not.
6. **Timing correlation.** A grievance's time can still be matched to the time a phone number was first registered. Only first-time callers are affected; a delayed registration timestamp would close this.

## November 2026 scientific workflow controls

Target creation and approval are administrator-only and audited; immutable version replacement is explicit. Report correction/verification is district-staff-only, rejects out-of-area changes and retains original observations. Creation checks scoped reporter references as well as submitted cells. Corrections cannot set origin, verification status or audit fields. Simulator and demo reports are excluded from scientific outcomes, including source-linked incident counts. Existing dry-run and anonymous grievance controls remain. No compliance determination or production activation is implied.

## Batch 5: climate and maintenance (November 2026)

Climate references require administrator creation/approval. Outage and maintenance writes require district staff and scope checks against verified asset/event cells. Outage overlaps and completion are serialized through inventory row locks on PostgreSQL; actual concurrent-worker contention remains a staging test. Read-only monitors do not receive free-text maintenance descriptions/actions. Demonstration references cannot be approved and demo repairs cannot close real outages. All new write operations are audited.

## Batch 6 training and operations boundaries

Simulator profiles use staff-specific non-dialable identities and never reuse a real caller's profile, consent, location or opt-out state. Training profiles are excluded from operational participant registries/counts, maps, cooperative measures and broadcast recipients; real-report references and registry updates reject them. Source-aware callback retry keys separate live/training traffic. Existing historical profile contamination cannot be inferred safely and requires an operator review. `/metrics` requires administrator authentication and stores bounded route-template labels.

Ordinary live SMS/rewards are dispatched only from committed queue rows, with an atomic state claim. Unknown provider outcomes are held for review instead of blindly retried; provider acceptance is not proof of handset receipt. Anonymous replies remain synchronous to avoid persisting a grievance-to-phone link in the queue. See [Batch 6 limitations and operating procedure](batch6-platform-reliability.md).

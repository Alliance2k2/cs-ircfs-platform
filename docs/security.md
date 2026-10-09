# Security and privacy

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
| Anyone on the internet self-registering and reading field data | New accounts (email or Google) start **pending**; an administrator activates them in Platform Management → Accounts. The pending status is only revealed to someone who knows the password | `routes/auth.py` |
| Password guessing | PBKDF2-SHA256 (210 000 rounds), 10 sign-in attempts a minute per client address | `routes/auth.py` |
| Session theft | Random 256-bit tokens, only a SHA-256 hash stored, httpOnly + SameSite=Lax cookie, `Secure` required in production, sessions deleted on suspension and logout | `core/security.py`, `routes/auth.py` |
| Rate limits defeated or shared behind a proxy | uvicorn runs with `--proxy-headers`; `FORWARDED_ALLOW_IPS` names the trusted proxy (`*` on Render, `127.0.0.1` by default) | `Dockerfile` |
| Unsafe deployment settings | `ENVIRONMENT=production` refuses to start without `REQUIRE_API_KEY=true`, PostgreSQL, `COOKIE_SECURE=true`, a CORS list free of localhost, and a `GATEWAY_CALLBACK_TOKEN` of at least 24 characters | `core/config.py` `guard_runtime` |
| Clickjacking, MIME sniffing, referrer leaks | `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`; HSTS in production | `main.py` `security_headers` |
| Development auth bypass reaching a server | The bypass only exists when `ENVIRONMENT=development` and `REQUIRE_API_KEY=false`, and logs a warning at startup | `core/security.py`, `main.py` |
| Chargeable messages during tests | The test suite forces `SMS_PROVIDER=dry_run` and `AIRTIME_PROVIDER=dry_run` | `tests/conftest.py` |

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

1. **Content Security Policy.** The legacy HTML pages use inline scripts and load Leaflet from unpkg, so a strict CSP would break them. Add one when the React app replaces them.
2. **Data protection impact assessment.** Rwanda's Law N° 058/2021 on the protection of personal data and privacy requires a lawful basis, purpose limitation and, for this kind of processing, registration with the National Cyber Security Authority. The district should complete the DPIA and registration before the pilot; this repository cannot do that.
3. **Retention.** No automatic deletion of inbound messages or sessions yet. Decide retention periods with the district and add a scheduled clean-up.
4. **Sign-in throttling per account.** The limit is per client address; add a per-email lockout if password guessing is seen.
5. **Audit log of staff reads.** Case and grievance changes are audited; reads of personal data are not.
6. **Timing correlation.** A grievance's time can still be matched to the time a phone number was first registered. Only first-time callers are affected; a delayed registration timestamp would close this.

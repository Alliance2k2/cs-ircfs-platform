# Controlled staging smoke and rollback checklist

Status: procedure prepared; hosted execution requires the actual URL and owner approval. Use an isolated staging database and approved test identities. Never use real participant data to prove a release works.

## Before deployment

- Confirm the intended branch, exact commit and all CI jobs, including Docker. Keep the last known-good image digest/commit.
- Obtain approval for the staging deployment. Production, DNS, billing, live messages and retention apply need their own explicit authorization.
- Use a separate PostgreSQL/PostGIS database, HTTPS hostname, secrets and callback token. Disable development bypass; require authentication; restrict CORS to exact origins or empty same-origin configuration. Production must use Secure cookies.
- Verify the previously exposed provider key was revoked in its owner console; do not paste it into logs/issues. Keep SMS/airtime dry-run, ALLOW_LIVE_MESSAGES=false and scheduled advice/private reply routing off until independently approved.
- Back up the intended database and rehearse restore to a different explicitly named disposable database. Encrypt off-site copies and approve retention. Do not test recovery by overwriting production.
- Build the complete frontend/container before serving it. Run migrations before app startup. The current schema head remains 20261102_28; no new revision is needed by this patch.

## Read-only smoke checks

From backend, using the approved staging URL:

```powershell
python scripts/verify_deployment.py https://YOUR-STAGING --environment staging
```

Record commit, URL, date, operator and all results. It checks liveness/readiness, built app, login, script policy, disabled bypass and blocked anonymous personal endpoints. Optional administrator API checks read DEPLOYMENT_CHECK_API_KEY from the environment; never put the key on a command line or in documentation. A passing localhost run is not a hosted staging pass.

- Sign out: protected app navigation goes to login and protected APIs refuse anonymous requests.
- Sign in using approved test accounts: verify monitor, officer, planner and administrator scopes; pending registrations do not self-promote.
- Verify the original registry tools and add/edit forms without saving unnecessary records. Check mobile navigation, named search, keyboard operation and language fallback.
- In the simulator only, register a fresh synthetic caller, restart as the same caller, report a valid reading, reject invalid values and confirm training-origin exclusions. Repeat with a new caller. Verify pending controls cannot mix callers or erase an answer.
- Confirm empty/retired inventory does not display development pump examples. Import only sourced district-approved manifests; do not fabricate inventory to satisfy readiness.
- Review evidence screens for missing references, units, crop/season/year matching, approved baselines and unverified/demo exclusions. Empty evidence must not turn into an impact claim or a zero measurement.
- Verify logs contain request IDs and route/status information, not callback tokens, credentials, SQL parameters or participant messages. Configure reverse-proxy query redaction separately.

## Separately approved sandbox/device rehearsal

Use provider sandbox credentials, dedicated test participants and explicit authorization. Confirm provider callback formats, secret/IP checks, repeated delivery receipts, unknown-outcome handling, carrier timeout/restart behavior and real feature-phone usability. Do not resend uncertain deliveries or enable paid providers merely because automated mocks passed. Live USSD is currently Kinyarwanda-first; English on the simulator is a staff aid, not a field language selector.

## Rollback

1. Stop optional workers/schedulers and prevent writes while deciding rollback scope.
2. Record the failing commit, symptoms, readiness state and sanitized logs.
3. Redeploy the previous known-good application artifact after checking schema compatibility.
4. Do not automatically downgrade migrations or delete receipt/audit history. If a database restore is required, obtain explicit approval, preserve a fresh backup and rehearse the exact procedure in a new disposable database first.
5. Repeat read-only smoke checks and document the operator's decision before reopening access.

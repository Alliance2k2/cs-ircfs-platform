# Production activation checklist

These items require owner decisions, provider-console access, or physical field validation and cannot be completed by repository code alone.

## Before external activation

- [ ] Revoke the previously exposed Africa's Talking API key in the Africa's Talking account.
- [ ] Create a new sandbox key for pilot testing, then create separately scoped production credentials.
- [ ] Configure USSD and SMS callback URLs with the shared secret and remove the old callback URLs.
- [ ] Restrict callbacks by provider IP addresses where supported.
- [ ] Keep SMS and airtime providers in `dry_run` until all callback and delivery tests pass.
- [ ] Enable live delivery only in the production environment after an approval sign-off.

## GitHub and deployment protection

- [ ] Require backend tests, migrations, frontend checks, browser workflows, and Docker builds before merging.
- [ ] Protect `main`; require a pull request and at least one review.
- [ ] Configure separate staging and production GitHub environments.
- [ ] Add production secrets to GitHub Environments, not repository variables.
- [ ] Require explicit approval for production deployment.
- [ ] Verify staging through `/ready`, `/health`, `/metrics`, a sample callback, and a smoke migration before production.

## Pilot and data governance

- [ ] Assign an accountable data protection owner and restore owner.
- [ ] Approve the consent and opt-out wording in Kinyarwanda.
- [ ] Test the USSD/SMS journey with cooperative members and monitors.
- [ ] Verify connectivity, callback retries, and low-bandwidth use on representative devices.
- [ ] Validate PADAB and APEFA hectares, crop targets, assets, and source documents.
- [ ] Calibrate rainfall thresholds using local historical records.
- [ ] Approve retention periods, export access, grievance handling, and withdrawal procedures.
- [ ] Schedule quarterly restore rehearsals and encrypted off-site backup copies.

## Verification completed by this repository

- Migration 20261029_21 aligns consent timestamp storage with the UTC-aware model decorator.
- Docker probes use `/ready`; `/health` remains process-only liveness.
- Operational JSON metrics are available at `/metrics`.
- The district handover package includes a custom-format backup script and restore instructions.

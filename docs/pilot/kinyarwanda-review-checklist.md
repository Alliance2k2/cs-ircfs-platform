# Kinyarwanda and agricultural terminology review

Status: BLOCKED pending native-speaking field staff and agronomy review. Existing strings and the new missing-inventory USSD message are drafts, not approved translations.

The 6 November inventory contains 697 dashboard keys: 39 Kinyarwanda drafts and 658 English fallbacks; no native approvals. Generate the current pack rather than copying an outdated key list:

```powershell
cd backend
python scripts/translation_review.py --output reviewed-pack-draft.json
```

- Name the native reviewer, agricultural/domain reviewer and institutional evidence reference.
- Review all visible navigation, form labels, empty/loading/error states and account-access wording with monitors, farmers and district staff.
- Verify crop names, irrigation asset terms, rainfall millimetres, harvest tonnes, measured area/hectares and observation dates in Africa/Kigali. Distinguish missing values, a recorded zero and an unverified observation.
- Review the new no-inventory message with cooperatives. Do not translate example pump names into claims of official field inventory.
- Walk every USSD branch on real feature phones: onboarding sector/cell selection, returning users, invalid choices, decimal inputs, restart after carrier timeout and protected grievance wording. Live USSD is RW-first; a separate selectable/persisted phone language is not implemented.
- Explain that simulator English is a staff translation aid. Test dashboard EN/RW selection and fallback on reload; do not label English fallback strings as translated.
- Test longer reviewed text at 390px, zoom and keyboard-only navigation. Verify consent/opt-out/retention and avoid promising absolute anonymity.
- Preserve every interpolation placeholder and every current key; record approved status per entry only after review.

Validate the completed pack with `python scripts/translation_review.py --check-reviewed reviewed-pack.json`. Applying it with `--apply-reviewed` is a separate reviewed source change, not part of the current draft export. Archive reviewer/evidence references with the pilot acceptance record.

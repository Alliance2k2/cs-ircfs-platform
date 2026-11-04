# Current interface changes - 4 November 2026

The original public page layout is retained. Changes are limited to the requested hero wording, five licensed Rwanda card photographs, a compact context/credit note and removal of the public API reference footer link. The phone demonstration and existing platform routes remain intact.

The staff dashboard defaults to white surfaces and dark green accents. A new explicit dark-mode choice is still available; an older saved dark preference no longer forces dark mode. Platform management prominently links to the original user, cooperative, irrigation scheme and report tools. Empty asset/category reference lists were confirmed as zero records, rather than missing controls.

The local demo launcher now requires normal account authentication, retaining its separate database and dry-run providers. The registration approval explanation was removed from the public form; access review rules remain enforced. Google sign-in uses the official rendered popup button with asynchronous SDK initialization and a loading-failure message.

## Verification

- Dashboard TypeScript and production build passed; existing font-path and Mapbox chunk warnings remain.
- Chrome checks passed for the light default despite an older dark preference, asset editor visibility, and original Add user / Add cooperative / Add scheme controls. No records were created.
- Chrome checks passed for login and registration form visibility, a protected API returning 401 and the dashboard redirecting signed-out visitors to login.
- Actual Google button renders. Mocked credential and registration responses verified error/success messages without submitting real credentials or creating accounts.
- Google reports that both localhost and 127.0.0.1 origins are unauthorized for the configured client ID. The Google Cloud client owner must add the intended local origins; external OAuth configuration is not fixed by this commit.
- Public footer check passed: reporting/privacy links retained, API reference removed.
- Earlier full-suite results and failures are preserved in historical redesign reports; they must not be presented as a new full-suite run for this final revision.

## Photography and review

[Sources and licenses](../dashboard/photography.html). Context photographs are not project participants or pilot-site evidence. The [desktop](images/original-with-photos/width-1440.jpg) and [mobile](images/original-with-photos/width-390.jpg) captures show the restored layout before subsequent small hero/authentication/footer edits. Earlier rejected redesign captures remain historical only.

Local database activation, backups, credentials and runtime logs are not committed. This change does not deploy or merge the branch.

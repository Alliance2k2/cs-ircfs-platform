# Data governance and retention policy

This operational policy supports Law N° 058/2021 privacy principles for citizen participation and telecom field data. It is a project control, not legal advice.

## Purpose and minimisation

The platform collects phone numbers only to provide transactional replies, closing-the-loop updates, opt-out handling, and limited airtime incentives. Names, cooperative details, and report notes are additional personal data and must not be exported unless required by an authorised use case.

## Consent and withdrawal

- The first accepted inbound USSD/SMS message records `consent_at`.
- `HAGARIKA`, `STOP`, `UNSUBSCRIBE`, or `KURURA` sets `opted_out_at` and suppresses broadcasts.
- `ONGERA`, `SUBSCRIBE`, `START`, or `KOMEZA` clears `opted_out_at`.
- Opting out does not prevent a direct transactional reply to a message the person sent.

## Roles and access

- Farmers and field users may submit reports they are authorised to create.
- Monitors and cooperative leaders receive masked phone identifiers.
- District officers and planners may access personal data only where their role and cell scope require it.
- Administrators must review exports through audit logs.
- CSV exports omit phone numbers, names, and verification notes.

## Retention defaults

Defaults are configurable through environment variables:

| Data | Default | Policy action |
|---|---:|---|
| Field-user personal profile | 730 days after last validated account activity or opt-out, whichever the approved deletion review permits | Anonymise or delete after review; preserve required statistical evidence separately |
| Authentication sessions | 12 hours | Automatic expiry |
| Audit logs | 365 days | Delete only under an approved archival schedule |
| Generated/export copies | 30 days | Delete from storage and retain only an audit record |
| Verified scientific field observations | Longer where approved as the project evidence record | Remove direct identifiers when retention of the personal profile expires |

Actual deletion is not automatic for scientific reports because removing a report can invalidate monitoring evidence. Identifiers are separated/anonymised while the observation remains with its verification and provenance metadata.

## Export and deletion procedure

1. Record the requester, purpose, date range, role, and approved scope in an audit entry.
2. Export the minimum necessary fields; never include telephone numbers in public or research exports.
3. Re-identifiable exports must use access-controlled storage and expire after `EXPORT_RETENTION_DAYS`.
4. For deletion requests, the district data owner verifies identity and scope.
5. The administrator removes or anonymises field-user profile data while retaining audit trails and de-identified reports required for evidence.
6. The system records the completion date. Downstream copies and provider records are reviewed separately.

## Provider and backup controls

- SMS/Airtime credentials must remain outside source control.
- Live callback credentials and callback IP/token allow-lists must be validated before production.
- Backups inherit the same sensitivity and retention constraints as live data.
- Restoration rehearsals must confirm encrypted storage, access restrictions, and deletion propagation.

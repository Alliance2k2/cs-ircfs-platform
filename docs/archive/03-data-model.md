# Initial Data Model

The following model preserves every core table named in the brief and adds the minimum supporting structure needed for secure relationships and follow-up.

| Table | Key fields / purpose |
| --- | --- |
| `sectors` | `id`, `name`, geometry; administrative sectors. |
| `cells` | `id`, `sector_id`, `name`, geometry; cell-level geography. |
| `users` | `id`, name, phone, role, `cell_id`, status; registered users and roles. |
| `irrigation_schemes` | `id`, name, partner, sector, geometry, hectares, verified baseline yield target, and status; initially PADAB and APEFA. |
| `citizen_science_logs` | reporter, scheme/location, crop/variety, planting/expected/reported harvest, observation type, pest/disease, severity, description, timestamp. |
| `irrigation_climate_logs` | reporter, scheme/location, asset, operational status, downtime, bottleneck category, rainfall amount, irrigation condition, infrastructure issue, timestamp. |
| `community_feedback` | optional reporter (to allow anonymous feedback), scheme/location, category, message, case status, assigned planner, follow-up action, timestamps. |

## Relationships

```text
sectors 1 ── * cells 1 ── * users
cells   1 ── * citizen_science_logs
cells   1 ── * irrigation_climate_logs
users   1 ── * all report tables
irrigation_schemes 1 ── * irrigation_climate_logs
users (planner) 1 ── * community_feedback follow-up
```

## Data rules

- A user role must be one of the approved roles.
- Dates use ISO `YYYY-MM-DD`; planting dates cannot be in the future.
- Rainfall is numeric, non-negative, and within an agreed field maximum.
- A report needs a reporter *or an anonymous submission token*, category, date/time, and location (cell or valid coordinates).
- Feedback status uses a defined workflow, proposed as `open → assigned → in_progress → resolved → closed`.
- Phone numbers are normalised and unique where used as an identity; anonymous grievance contact data must be separately protected.
- Scheme yield targets, pump/canal inventories, and model thresholds require a source, version, reviewer, and effective date; never hard-code unverified historical assumptions.

Exact crops, disease vocabulary, units, valid rainfall range, scheme boundaries, and retention rules are field-design decisions to confirm before the database migration is written.

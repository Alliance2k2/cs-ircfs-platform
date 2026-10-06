# Solution Architecture

```text
Farmers / Monitors / Cooperative Leaders
                │
          USSD and SMS
                │
     Provider webhooks / gateway
                │
     FastAPI application (REST API)
       ├─ authentication and roles
       ├─ validation and business rules
       ├─ report and follow-up workflows
       └─ analytics endpoints
                │
 PostgreSQL + PostGIS geographic database
                │
 Web dashboard + Leaflet interactive map
                │
 District planners and decision support
```

## Components

| Component | Responsibility |
| --- | --- |
| FastAPI | Secure REST API, provider webhooks, validation, business logic, and responses. |
| PostgreSQL/PostGIS | Relational, geographic, secure, integrity-protected storage. |
| USSD/SMS adapter | Translates gateway requests and messages into validated reports. |
| Dashboard | Planner views, filtering, follow-up, analytics, and KPI summaries. |
| Leaflet | Interactive geographic visualisation. |
| Docker and cloud/server | Repeatable deployment, operations, and scaling. |

## API groups from the brief

`/users`, `/citizen-reports`, `/irrigation-reports`, `/rainfall`, `/feedback`, `/analytics`.

Every endpoint must authenticate, validate input, perform a database operation, handle errors, and return an appropriate response.

## Later decision support

After sufficient reliable data exists, compute harvest performance:

`reported_harvest / expected_harvest × 100`

Classify bottlenecks as technical, social, institutional, or environmental. A future irrigation recommendation module can combine historical rainfall, seasonal forecasts, and current conditions.

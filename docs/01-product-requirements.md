# Product Requirements — CS-IRCFS

## 1. Problem and outcome

Farmers, Citizen Science Monitors, and cooperatives generate information about production, irrigation, rainfall, pests, diseases, and local challenges. Today it is not consistently collected or delivered to District Planners in a timely, structured form.

CS-IRCFS will provide a reliable, accessible, low-bandwidth system that turns community reports into decision-ready information for district planning.

## 2. Users and permissions

| Role | Main responsibilities |
| --- | --- |
| Farmer | Submit crop information, pest/disease and irrigation-problem reports, and feedback. |
| Citizen Science Monitor | Collect agricultural observations, rainfall readings, and community-level reports. |
| Cooperative Leader | Coordinate farmers, submit rainfall measurements, and report irrigation conditions. |
| District Officer / Planner | Monitor and analyse reports, identify bottlenecks, and follow up on community issues. |
| System Administrator | Manage users, configuration, data access, and security. |

Access must be role-based: community users create their own reports; planners view and manage reports in their authorised area; administrators manage the whole platform.

## 3. Information to collect

### Agricultural

- Farmer identity/profile and location
- Crop type
- Planting date
- Expected harvest
- Reported harvest (needed for performance analysis)
- Pest and disease reports

### Irrigation, climate, and community

- Rainfall measurements
- Irrigation conditions and problems
- Infrastructure problems
- Community feedback: complaint, suggestion, status, and follow-up action
- Location information: sector, cell, optional coordinates, and irrigation scheme

## 4. User-facing reporting channels

### USSD

Designed for basic phones and unreliable internet. It must be short, Kinyarwanda-first, simple to navigate, and tested with users before rollout.

Initial menu:

1. Crop Production Report
2. Irrigation and Rainfall Report
3. Community Feedback

Initial crop flow: select service → crop production → crop type → planting date → expected harvest → confirm → submit.

### SMS

An alternative where a USSD session is unavailable. Initial format: `CATEGORY LOCATION VALUE`.

Supported categories: crop information, pests/diseases, rainfall, irrigation problems, and community feedback. Final command formats must be validated during field design.

## 5. Planner dashboard

The dashboard must give planners a rapid overview and paths to detailed reports.

- Overview KPIs: registered farmers, total reports, active schemes, open complaints
- Farmers and crop reports
- Pest and disease reports
- Irrigation and rainfall
- Community feedback and follow-up
- PADAB and APEFA scheme views
- Analytics
- Interactive map: schemes, farmer reports, pests, rainfall, and infrastructure problems

## 6. Quality, security, and operational requirements

- Authenticate all API access and authorise by role.
- Validate all inputs; required values cannot be blank.
- Enforce accepted date formats, reasonable rainfall values, valid locations, and predefined roles.
- Store data securely with integrity constraints.
- Ensure clear API errors and safe retries for USSD/SMS providers.
- Support backup, monitoring, technical documentation, and user training before production.

## 7. Pilot and success measures

Pilot with selected agricultural cooperatives in Bugesera. Measure usability, USSD/SMS workflow success, data quality, technical problems, feedback, and adoption.

Indicators: registered farmers, submitted reports, active users, irrigation reports, pest reports, community complaints, response time, data errors, and user feedback.

# Concept Note

# Citizen Science for Irrigation Resilience and Climate-Smart Food Security (CS-IRCFS)

**A field reporting, irrigation, accountability and decision-support platform for Bugesera District, Rwanda**

**Proposed location:** Bugesera District, Rwanda  
**Current status:** Functional technology platform; pilot readiness subject to field validation, production telecom approval and official scheme baselines  
**Proposed duration:** 18 months  
**Target population:** Smallholder farmers, Citizen Science Monitors, cooperatives, district officers and irrigation scheme managers  
**Prepared for:** [Funding agency / government institution / implementing partner]  
**Prepared by:** [Organisation name and contact]  

---

## 1. Executive Summary

Smallholder farmers and district institutions in Bugesera face recurring pressures from variable rainfall, irrigation infrastructure constraints, pest and disease risks, household food and nutrition insecurity, and gaps between reported field conditions and district decision-making. Communication with farmers is also fragmented: national and local advisories are difficult to tailor to scheme-level and sector-level conditions, while evidence of infrastructure failure, crop performance or community grievances may not reach decision-makers in time.

The Citizen Science for Irrigation Resilience and Climate-Smart Food Security (CS-IRCFS) project addresses this gap through a low-cost, inclusive and locally managed digital platform. The platform enables farmers, Citizen Science Monitors and cooperatives to submit information using any mobile phone through Kinyarwanda USSD and SMS channels, without requiring internet access or a smartphone. The platform turns these reports into usable district evidence, maps, dashboards, case workflows and advisory messages.

CS-IRCFS combines citizen-generated field data with rainfall forecasts, district irrigation schemes and institutional accountability processes. Its modules support crop and harvest reporting, pest and disease alerts, household nutrition risk screening, irrigation and climate advice, infrastructure bottleneck reporting, anonymous grievances, case management and closing-the-loop communication with affected communities.

The proposed intervention will undertake a real-phone pilot involving up to three cooperatives, validate local USSD language and workflows, enter official PADAB and APEFA Solar scheme data, train cooperative Data Champions, and establish district ownership and sustainable operations. The platform will be hosted through a PostgreSQL/PostGIS and Docker-based deployment stack and administered according to defined roles, sector-based access restrictions, data protection, audit and incident-management procedures.

## 2. Problem Statement

### 2.1 Limited timely field intelligence

District and scheme managers do not always receive consistent, georeferenced and timely evidence about rainfall, crop health, irrigation performance, infrastructure breakdowns and household nutrition conditions. When information is collected, it may remain in separate forms, spreadsheets or institutions and therefore cannot readily inform coordinated action.

### 2.2 Connectivity and device exclusion

Many intended users may not have reliable internet access or smartphones. Mobile solutions that depend on apps or constant connectivity can exclude vulnerable groups and delay reporting in the rural areas where evidence is most needed. Any practical solution must work for basic and feature phones and be available in Kinyarwanda.

### 2.3 Weak linkage between reporting and action

Reporting alone does not produce resilience. Communities need to know that a report has been received, prioritized, assigned and resolved. District systems must also be able to close the feedback loop through SMS or USSD, especially when infrastructure repairs, irrigation schedules, pest warnings or grievance responses affect multiple users.

### 2.4 Data gaps in irrigation evaluation

Irrigation scheme performance should be evaluated against documented baselines, crop-specific yields, seasonal results, asset conditions and recurring bottlenecks. Where these baselines and supporting datasets are missing, scheme performance claims may be inaccurate. Scientific thresholds and advisories also require local calibration rather than automatic reliance on unverified assumptions.

### 2.5 Accountability and trust

Farmers may be reluctant to report resettlement impacts, environmental harm, unfair treatment, service failures or other sensitive grievances if their identity is exposed. The platform therefore needs to separate location-based grievance reporting from personal identity and establish transparent case-management procedures without creating anonymity-related risks.

## 3. Geographic and Institutional Context

The proposed pilot is in Bugesera District, with an initial focus on cooperatives serving the pilot sectors and the PADAB and APEFA Solar irrigation schemes. District planners, extension officers, cooperative leaders, monitors, scheme managers and district IT staff will form the core institutional partnership.

The platform is designed around the district's sector and cell geography. Reports can be associated with the reporting user's sector and cell while protecting household-level details. District-level users can view aggregate trends and scheme information, while accounts limited by area access only see records authorised for their assigned sectors.

## 4. Project Goal

To improve timely evidence-based decision-making, climate resilience, irrigation management, farmer response and institutional accountability in Bugesera District through an accessible citizen-science information platform.

## 5. Specific Objectives

1. Establish an inclusive field-reporting channel through Kinyarwanda USSD and SMS accessible on basic and feature phones.
2. Strengthen local crop, rainfall, pest and disease, infrastructure, nutrition and grievance data collection.
3. Improve the prioritisation and resolution of urgent and recurring field issues through traceable case workflows and closing-the-loop notifications.
4. Provide district planners with credible scheme-performance, monthly, geographic and trend information to guide irrigation and climate-smart agricultural decisions.
5. Build local capacity among cooperative Data Champions, district staff and IT administrators.
6. Produce verified baselines, operating procedures, data governance controls and a costed model for district-owned scale-up.
7. Test whether citizen-generated reports and locally tailored advisories improve response timeliness, user participation and scheme monitoring.

## 6. Target Groups and Expected Reach

| Group | Proposed role | Illustrative contribution / expected benefit |
|---|---|---|
| Smallholder farmers | Submit rain, crop, pest, infrastructure and nutrition information; receive advisories | Timely local information and improved access to responses |
| Citizen Science Monitors | Receive training and coordinate field reporting | Increased data quality, response participation and local ownership |
| Cooperatives and Data Champions | Validate reports, support users and promote adoption | Reduced reporting barriers and trusted field coordination |
| District officers | Review cases, manage schemes, issue advice and monitor progress | Faster prioritisation and improved district-wide planning |
| Irrigation scheme managers | Access asset and bottleneck evidence | Better maintenance planning and evaluation |
| Households submitting grievances | Report concerns anonymously by cell | Safer access to accountability channels |
| District IT and data staff | Operate, secure and maintain the platform | Local ownership and long-term sustainability |

The number of direct beneficiaries will be confirmed during the baseline and pilot mobilisation process. The initial pilot is expected to involve three cooperatives and selected sectors, with scale-up based on demonstrated adoption, operational performance and data quality.

## 7. Proposed Intervention

### 7.1 Establish and validate field channels

- Configure USSD service `*801#` and SMS keyword reporting with an approved national short code or gateway arrangement.
- Provide Kinyarwanda reporting for harvests, rainfall, pests or diseases, infrastructure bottlenecks and nutrition information.
- Support first-time location registration and keep menus short, numeric and suitable for feature phones.
- Test callback security, replay protection, phone-number protection, delivery statuses, airtime incentives and error handling.

### 7.2 Populate verified reference data

- Enter official PADAB and APEFA Solar irrigation scheme names, crop targets, units, seasons, hectares, assets and implementing-partner information from verified documents.
- Load Bugesera sector and cell boundaries and validate scheme-to-location relationships.
- Establish grievance categories, asset inventories, user organisations and operational reporting categories.
- Define the sources and approval status of every evaluation baseline.

### 7.3 Configure district decision support

- Deploy the district dashboard for prioritisation, scheme evaluation, crop reports, irrigation advice, rainfall trends, nutrition summaries, maps, grievances and monthly reporting.
- Configure Act Now cases for severe pest or disease reports and recurring infrastructure problems.
- Assign incident owners, deadlines, status workflows and close-out evidence.
- Produce printable monthly reports and exportable evidence summaries.

### 7.4 Support two-way communication

- Provide immediate local tips in response to selected field reports.
- Send sector irrigation advice based on rain-gauge readings and server-accessible rainfall forecasts.
- Alert district staff about urgent cases.
- Preview and send closing-the-loop SMS to affected communities after an issue is resolved.
- Establish delivery logs and provider callback reconciliation.

### 7.5 Pilot, train and hand over

- Train cooperative Data Champions and district users.
- Conduct usability sessions with real feature phones and native Kinyarwanda speakers.
- Run controlled simulations before live service activation.
- Support an initial pilot with real phone users and review progress monthly.
- Hand over hosting, operating procedures, backups, access administration, incident management and performance monitoring.

## 8. Core Results

### Output 1: Accessible reporting service operational

- Kinyarwanda USSD and SMS channels tested and deployed.
- Basic-phone users able to report crop, rain, infrastructure, nutrition and grievance information.
- Callback authentication, retry control and provider monitoring implemented.

### Output 2: District evidence and response workflows operational

- Geographical field data and scheme information available in the dashboard.
- Act Now cases created for severe or recurring issues.
- District staff can assign, review, update and close cases.
- Monthly reports and trend summaries generated from verified field evidence.

### Output 3: Irrigation advisories and citizen feedback improved

- Irrigation guidance combines citizen rain-gauge readings and available forecast information.
- Farmer reports are acknowledged and receive locally relevant tips.
- Closed cases trigger controlled closing-the-loop communication.

### Output 4: Verified scientific and operational baselines established

- Official scheme baselines and source documents recorded.
- Rainfall thresholds reviewed by technical specialists and calibrated with local evidence.
- Yield achievement is reported only where area, crop, season, unit and target data are complete.
- Model and threshold limitations are documented.

### Output 5: Institutional capacity and handover delivered

- Cooperative and district staff trained.
- User manuals, operating procedures, security procedures and support processes completed.
- District-owned hosting and maintenance plan approved.

## 9. Monitoring, Evaluation and Learning Framework

| Level | Indicator | Illustrative measurement |
|---|---|---|
| Reach | Registered and active field users | Number and proportion by sector, organisation and reporting channel |
| Uptake | Reports submitted and successfully processed | Monthly USSD and SMS report counts with duplicate and rejected rates |
| Data quality | Valid geolocation and required-field completeness | Completeness, consistency, repeatability and source provenance |
| Responsiveness | Median time from urgent report to case assignment and resolution | Case timestamps and workflow audit history |
| User trust | Grievance resolution and closing-the-loop rate | Number resolved and communication delivery outcome |
| Scheme intelligence | Documents, baselines and assets linked to schemes | Verified baseline and asset coverage |
| Irrigation advice | Reports and advisories sent | Sector coverage, delivery status and farmer acknowledgement |
| Participation | Cooperative contribution and repeat participation | Users reporting at least once, repeat reporting and Data Champion activity |
| Adoption | District users actively reviewing dashboard evidence | Number of active staff, report views and monthly report downloads |
| Sustainability | Platform operating costs and support capacity | Monthly telecom, hosting, maintenance and incident costs |

A baseline shall be established before the live pilot. Indicators will be disaggregated only where aggregation protects personal identity and data protection requirements. Nutrition data will remain staff-only and threshold-based; grievance submissions will remain anonymous with cell-level evidence only.

## 10. Proposed Activities and Timeline

| Phase | Duration | Principal activities |
|---|---|---:|
| Inception and baseline | Months 1–2 | Stakeholder validation, data protection review, baseline, official requirements and success metrics |
| System and reference-data preparation | Months 3–4 | Scheme baselines, asset inventories, grievance categories, Kinyarwanda review and telecom setup |
| Controlled testing | Months 5–6 | Phone testing, security testing, backup testing, staff training and simulations |
| Limited pilot | Months 7–10 | Three-cooperative pilot, dashboards, advisory service and case management |
| Evaluation and improvement | Months 11–14 | User feedback, data-quality review, threshold assessment, workflow improvements and scale-up recommendations |
| Handover and sustainability planning | Months 15–18 | Capacity building, district operating model, procurement plan, documentation and final evaluation |

## 11. Technical Architecture

The platform uses:

- **Field interfaces:** USSD and SMS callbacks; Kinyarwanda-first menus and keyword workflows.
- **Application layer:** Python and FastAPI.
- **Data layer:** PostgreSQL/PostGIS with Alembic migrations and role-based application access.
- **Web interface:** React/TypeScript district dashboard and existing public or management interfaces during migration.
- **Mapping:** sector, cell, scheme, report and asset geographic layers.
- **Deployment:** Docker and Docker Compose, with migration and startup controls.
- **Integration:** Africa's Talking-compatible telecom callbacks and Open-Meteo rainfall forecast access.

The system must be deployed only with production credentials, callback authentication, secure sessions and site-specific configuration approved by the district.

## 12. Safeguarding, Privacy and Ethics

The project will apply privacy-by-design principles, including:

- Graceful location data collection through sector and cell selection.
- Masking or restricting phone numbers and household information where district staff do not need them.
- Anonymous grievance collection that stores the cell rather than the reporter's identity.
- Staff-only access to household nutrition records.
- Role-based and sector-based access controls.
- Data classification, audit logs, access reviews and export controls.
- Automatic retention and deletion rules for inbound telecom and operational data.
- Consent or ethical review where required for identifiable household and farmer research data.
- A data protection impact assessment and compliance review under applicable Rwanda law.
- Publication of aggregate data only unless explicit legal and ethical conditions permit individual-level disclosure.

Grievance anonymity will not be represented as absolute anonymity where timing, network or operational metadata could create re-identification risk. Formal safeguards and escalation arrangements will be documented before the pilot.

## 13. Indicative Budget Categories

The final budget should be developed from quotations, staffing plans and telecom-provider terms.

| Category | Illustrative items |
|---|---|
| Personnel | Project coordination, software engineering, data management, agronomy/irrigation expertise and field facilitation |
| Telecommunication | USSD/SMS short-code costs, gateway fees, inbound/outbound SMS and airtime incentives |
| Infrastructure | Hosting, PostgreSQL/PostGIS, backups, monitoring, domain, SSL and technical support |
| Field implementation | Cooperative mobilisation, transport, devices for demonstrators, training and real-phone testing |
| Data and evidence | Scheme baseline collection, GIS preparation, rainfall data and independent expert review |
| Monitoring and evaluation | Baseline, user research, data-quality assessment and endline evaluation |
| Safeguarding and governance | Data protection assessment, legal review, audit, policies and incident-response procedures |
| Communications | Training materials, Kinyarwanda translation review, public information and feedback materials |
| Contingency | Controlled contingency subject to donor and implementing-partner rules |

## 14. Implementation and Governance

A project steering or technical working group should include representatives from:

- District administration and planning;
- Agriculture, irrigation and environmental functions;
- Cooperative leadership and farmer representatives;
- Information and communication technology staff;
- Agriculture/irrigation technical partners;
- Community protection, safeguarding and data governance representatives;
- Implementation and technical provider personnel.

A named district product owner will approve workflows and access policies. A technical lead will manage hosting, software updates and incidents. Cooperative Data Champions will support adoption and field quality but will not receive unrestricted district data access.

## 15. Risks and Mitigation

| Risk | Likelihood / Impact | Mitigation |
|---|---|---|
| Production USSD/SMS credentials or short code delayed | Medium / High | Use sandbox testing while approvals proceed; sequence launch around approved channels |
| Users find menus difficult | Medium / High | Native-speaker review, real-phone testing, numeric menus, field training and user feedback |
| Official baselines are unavailable or inconsistent | Medium / High | Record source provenance; mark incomplete evaluations; obtain official documents before scientific claims |
| Duplicate or missed callback events | Medium / High | Authenticate callbacks, enforce retry controls, reconcile delivery states and maintain provider logs |
| Connectivity or telecom failure interrupts services | Medium / Medium | Delivery retries, monitoring, offline-capable field materials and an emergency fallback protocol |
| Sensitive information is misused or disclosed | Low / High | Least privilege, masking, data minimisation, retention, exports controls, audit reviews and incident procedures |
| Farmer participation declines | Medium / Medium | Responsive closing-the-loop communication, Data Champion support, airtime incentives and transparent action reporting |
| Platform becomes externally dependent | Medium / Medium | Open operational documentation, trained district administrators, Docker deployment and sustainable procurement |
| Data is interpreted as proof beyond its quality | Medium / High | Show confidence, sample size, source and data gaps; require expert review of yield and rainfall conclusions |
| Partners cannot maintain the system | Low / High | Fund training, support, service-level agreements and a transition plan before pilot end |

## 16. Sustainability and Scale-Up

CS-IRCFS sustainability will depend on formal district ownership rather than software adoption alone. The scale-up plan will define:

- The district unit responsible for content, data quality and escalation;
- A named technical administrator for accounts, hosting, updates and backups;
- A service-level agreement for telecom and hosting costs;
- Annual maintenance, backup testing and cybersecurity review budgets;
- Data retention and deletion procedures;
- Local content ownership, including Kinyarwanda translation;
- A route for adding schemes, sectors, partner organisations and cooperatives without system redesign;
- Periodic calibration and independent review of irrigation, nutrition and scheme thresholds.

Scale-up will use evidence from pilot participation, case-response performance, data quality, user feedback and cost per active participant. Expansion should proceed only if systems, staffing, connectivity and local ownership are adequate.

## 17. Assumptions

- District and institutional partners will assign staff to pilot governance and implementation.
- Cooperatives will support mobilisation, training and field validation.
- Official yield, asset, crop, season and irrigation scheme information will be made available for evidence use.
- Production telecom credentials and a short code will be obtained.
- Internet connectivity will be sufficient for web, hosting and weather-forecast services, while reporting remains available through USSD/SMS.
- Local language and interface materials will be reviewed by native speakers.
- Budget, hosting, gateway pricing and user incentives will be confirmed through partner agreements.

## 18. Expected Project Legacy

By the end of the intervention, Bugesera District is expected to have:

- A functioning low-connectivity farmer reporting channel;
- A more complete and geographic evidence base for agricultural and irrigation decisions;
- A closed-loop response process for urgent field incidents and grievances;
- A documented record of irrigation scheme and asset conditions;
- A trained group of cooperative Data Champions and district administrators;
- Monthly decision reports based on verified data;
- Policies and technical controls for privacy, access, retention and incident management;
- A tested plan for district ownership and responsible scale-up.

## 19. Conclusion

CS-IRCFS offers an integrated approach to climate resilience and food security: farmers report through accessible mobile channels, local evidence is combined with scheme and rainfall data, district staff act through accountable workflows, and communities receive feedback on resolutions. The project should move through a carefully governed pilot because official baselines, telecom approvals, native-language validation and data protection measures are prerequisites for scientifically credible and ethically sound implementation.

The platform is ready to demonstrate, test and pilot core functions. The proposed project is therefore not primarily a request for another software design; it is a request to validate field use, establish evidence baselines, build district capacity, assess impact and convert a functioning platform into a sustainable public-service system.

---

## Suggested Annexes

- Stakeholder map
- Pilot log-frame and full results framework
- Institutional roles and responsibility matrix
- Data protection impact assessment
- Baseline questionnaire and sampling plan
- Telecom and short-code implementation plan
- Official PADAB/APEFA scheme baseline register
- Training plan and user materials
- Detailed budget and procurement plan
- Risk register
- Monitoring and evaluation plan
- Sustainability and cost-recovery plan

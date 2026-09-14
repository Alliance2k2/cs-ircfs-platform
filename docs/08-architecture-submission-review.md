# Architecture document submission review

Reviewed: 14 September 2026. Source: `../cs-ircfs-platform-architecture.docx`.

## Decision

**Revise before submitting as a standalone document.** The file begins at section 4, contains sections 4–9 only, has no title, executive summary, date, version, status legend, or references, and mixes current implementation with future proposals. It is suitable as an extract of a larger proposal only if sections 1–3, its sources, and the surrounding context are included.

## Corrections needed in the Word document

| Location | Current problem | Submission-ready correction |
| --- | --- | --- |
| Section 4 opening | Says historical PADAB and APEFA implementation records *are* model-training data and reports *verify* projected outcomes. Neither dataset is loaded or validated in the current platform. | Say the platform **proposes** outcome comparison after source records, permissions, target definitions, and reporting coverage are verified. |
| Architecture diagram | Shows a gateway, “Central Database Twilio / Africa's Talking API,” and dashboard, but omits the FastAPI validation and case workflow. It also appears to combine distinct components in single cells. | Redraw as phone → provider gateway → FastAPI authentication/validation → PostgreSQL/PostGIS → dashboard/case workflow → approved response channel. Label provider and shortcode **to be selected**. |
| USSD/SMS gateway | Presents `*801# / 8448` as assigned shortcodes. | Remove or mark as illustrative until a telecom/provider agreement confirms them. |
| Sections 4 and 9 | Forecaster, pest heatmaps, nutrition tracker, irrigation advice, automatic classification, and outgoing SMS read as implemented. | Mark each **planned**; distinguish the current report API, case queue, PostgreSQL/PostGIS storage, and browser demonstration. |
| Nutrition and grievance text | Proposes a stunting risk score and a cell-wide grievance “mass blast” without consent, clinical validation, or privacy review. | Avoid automated health scoring. Describe consent-based aggregate surveys only after safeguarding approval. Send case updates privately; cell-wide notices require authority approval and no personal details. |
| Section 5 roadmap | Refers to “Django/FastAPI or Node.js” and future PostgreSQL construction, although FastAPI and PostgreSQL/PostGIS are already selected and running. | State the selected stack and mark completed, in-progress, and future milestones separately. |
| Section 7 SQL | Sample SQL does not match the implemented schema: key and field names differ, no `geometry` columns appear, and incident case/history tables are absent. | Replace with [the audited implemented-schema section](09-implemented-database-schema.md); refer to migration `20260914_04` as the implemented revision. |
| Section 8 incentives | States a 100 RWF airtime reward every three reports as if agreed. | Move to a pilot hypothesis with a budget, consent, fraud-control, and funder approval gate; remove the amount until approved. |
| Section 9 model training | Claims studies and appraisal records provide “ground truth,” and that models and SMS advice can be calibrated from them. | Identify actual data owners and access status. Historical projections are baselines to examine, not ground truth; validation needs observed outcomes and expert review. |
| Throughout | Scheme figures, feasibility targets, objectives, and policy alignments lack inline references. | Add a source note at each factual claim and a references section. State whether a figure was planned, constructed, or currently operational. |

## Source checks

- AfDB describes PADAB's Mwesa Valley irrigation target as **650 hectares** in its [project overview](https://www.afdb.org/en/news-and-events/rwanda-bugesera-agricultural-development-support-project-3537). The [appraisal report](https://www.afdb.org/fileadmin/uploads/afdb/Documents/Project-and-Operations/RW-2006-063-EN-ADF-BD-WP-RWANDA-AR-PADAB.PDF) describes planned canals covering **75 km**, so the document's **65.5 km** figure needs a specific as-built or evaluation citation and date.
- [APEFA's project description](https://apefarwanda.org/bugesera-solar-powered-irrigation-system-installation/) supports the Ngeruka/Mareba location and solar-irrigation context. It does not establish that APEFA historical records are available for model training.
- Rwanda's [NST2 2024–2029](https://www.minecofin.gov.rw/fileadmin/user_upload/Minecofin/Publications/STRATEGIES/NST_2/NST2_2024-2029_Abridged.pdf) can support policy alignment, but the document should cite the specific priority and avoid implying NST2 approved this particular platform.

## Current implementation evidence

The live PostgreSQL database is reachable with PostGIS and Alembic revision `20260914_04`. The API includes users, crop and irrigation reports, feedback, incident cases, map data, and basic analytics. The dashboard can demonstrate report-to-case action. USSD/SMS provider integration, actual outgoing messages, verified scheme data, individual sign-in, production analytics, and pilot evidence remain future work. PADAB and APEFA Solar exist as inactive reference scheme names, without verified metrics or boundaries; the database has no sectors, cells, crop reports, or irrigation reports. The Word document must not imply a completed field pilot or validated outcome results. User and report counts can change during normal administration and should be checked immediately before submission.

![MISC Group brand graphic](data:image/png;base64...)

**ZETEO**

**USER REQUIREMENTS**

**SPECIFICATION**

Revision History

|             |               |                  |                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ----------- | ------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Version** | **Date**      | **Author**       | **Comments**                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 1.0         | 7 August 2026 | Azlan Bin Nazari | Initial draft. Content derived from the Data Driven & Digital 2025 v1.8 pack.                                                                                                                                                                                                                                                                                                                                                                |
| 1.1         | 7 August 2026 | Azlan Bin Nazari | Topped up with the VDT semantic model preparation requirements from FEED Requirements.docx — medallion architecture, AI agent scope, Gold Layer schema, design principles, assumptions and responsibility summary.                                                                                                                                                                                                                           |
| 1.2         | 7 August 2026 | Azlan Bin Nazari | Enhanced with the strategic business case, objectives, key business questions and benchmarking considerations, conversational analytics scope, delivery workstream deliverables, and supporting reference material.                                                                                                                                                                                                                          |
| 1.3         | 7 August 2026 | Azlan Bin Nazari | Project renamed to Zeteo. Added the Project Name and Rationale section linking the Greek meaning to the project vision, and updated references throughout.                                                                                                                                                                                                                                                                                   |
| 2.0         | 7 August 2026 | Azlan Bin Nazari | Restructured into three chapters — Business, Functional and Technical Requirements — with chapter boundaries defined against BABOK v3, ITIL 4 and DAMA-DMBOK. Multilevel numbered headings applied throughout.                                                                                                                                                                                                                               |
| 2.1         | 7 August 2026 | Azlan Bin Nazari | Quality pass — consistent table styling, added the Open Items and Decisions Register, and set the table of contents to refresh on open.                                                                                                                                                                                                                                                                                                      |
| 2.2         | 7 August 2026 | Azlan Bin Nazari | Editorial and structural review. Chapter 1 rationale and standards sections condensed; requirement IDs (BR, BQ, FR, TR, DP, A) introduced throughout; Chapter 3 rewritten as testable "shall" statements; scope boundary in section 2.1 reconciled with section 2.7; specialist AI agent rationale moved to the Appendix; hedging replaced by references to the Open Items and Decisions Register; duplicated technical assumptions removed. |

Project Team

|                                      |                          |
| ------------------------------------ | ------------------------ |
| **Role**                             | **Name**                 |
| Executive Sponsor & Value Owner      | CFO Group Finance        |
| Sponsor                              | Finance Leader & DGA     |
| Project Integration Management (PIM) | Shuufi                   |
| Analytics (ADA)                      | Azlan                    |
| Business Analysis (FER)              | Taqy                     |
| Data Transformation (EDH)            | Wimmy                    |
| Change Management Office (CMO)       | Pei Yoong                |
| BU Finance representative            | [To be nominated by BU]  |
| BU Operations SMEs                   | [To be nominated by BU]  |
| Support                              | DMG, PEX, CP, ICT (Apps) |

Acceptance Review & Sign Off

This is to certify that the User Requirement Specification (URS) document has been reviewed and formally accepted. The sign-off below indicates approval to proceed with the development phase of the project.

|                                                     |          |                    |
| --------------------------------------------------- | -------- | ------------------ |
| **Designation**                                     | **Name** | **Signature/Date** |
| CFO Group Finance (Executive Sponsor & Value Owner) |          |                    |
| Finance Leaders Caucus (FLC) — Chair                |          |                    |
| Project Director                                    |          |                    |
| Project Integration Management (PIM)                | Shuufi   |                    |
| Head, Data Governance & Analytics (DGA)             |          |                    |
| Analytics Lead (ADA)                                | Azlan    |                    |
| BU Finance (Value Owner)                            |          |                    |

Table of Contents

- [1 Introduction](#1-introduction)
- [2 Business Requirements](#2-business-requirements)
- [3 Functional Requirements](#3-functional-requirements)
- [4 Technical Requirements](#4-technical-requirements)
- [5 Appendices](#5-appendices)

Terminology/Definitions

|                                    |                                                                                                                                                                                                                              |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Term**                           | **Definition**                                                                                                                                                                                                               |
| Zeteo                              | The project name, from the Ancient Greek ζητέω (zētéō) — to seek, to inquire into, to investigate a matter through to resolution.                                                                                            |
| FAIR                               | Finance Analytics & Insights Report — the existing descriptive reporting suite built in Excel and Power BI.                                                                                                                  |
| FP&A                               | Financial Planning & Analysis model comparing Actual vs Budget vs Year-End Projection.                                                                                                                                       |
| VDT                                | Value Driver Tree — decomposition of CFROA, NPAT, Revenue, Expenses, Net Assets and CFFO into underlying operational drivers.                                                                                                |
| DGA                                | Data Governance & Analytics — the centralised analytics and enablement function.                                                                                                                                             |
| FLC                                | Finance Leaders Caucus — the enterprise steering committee for Zeteo.                                                                                                                                                        |
| PIM                                | Project Integration Management — coordinator and integrator of Zeteo activities.                                                                                                                                             |
| CMO                                | Change Management Office — enables sustained adoption of Zeteo-driven decisions and behaviours.                                                                                                                              |
| EDH                                | Enterprise Data Hub — ICT function responsible for data extraction, ingestion and Silver layer transformation.                                                                                                               |
| GPO / MDO                          | Global Process Owner / Master Data Owner — accountable for process and master data standards and for managing divergence.                                                                                                    |
| DDVC                               | Data Driven Value Creation.                                                                                                                                                                                                  |
| BU                                 | Business Unit.                                                                                                                                                                                                               |
| CFROA                              | Cash Flow Return on Assets.                                                                                                                                                                                                  |
| CFFO                               | Cash Flow from Operations.                                                                                                                                                                                                   |
| FSSC                               | Finance Shared Services Centre.                                                                                                                                                                                              |
| EDH Medallion Architecture         | Bronze (raw ingestion), Silver (cleansed / conformed) and Gold (modelled for reporting) zones on Azure Databricks.                                                                                                           |
| Gold Layer VDT table               | The modelled, aggregated dataset aligned to the VDT structure — one row per driver per time period — and the single source of truth for the Power BI report.                                                                 |
| AI Agent                           | A specialist, purpose-built agent operating from a fixed, versioned prompt and knowledge base, as distinct from a general-purpose LLM.                                                                                       |
| Needle-mover initiative            | A prioritised action agreed in the Finance–Operations discussion, with owner and timeline, classified as an analytics or non-analytics use case.                                                                             |
| Surrogate key                      | A key introduced at design phase to uniquely identify each aggregated Gold Layer row and eliminate row-count fan-out risk.                                                                                                   |
| Analyst Notes                      | A human-editable field in the Root Cause & Mitigation table for Finance and Operations commentary on AI-proposed causes and mitigations.                                                                                     |
| LightSpeed                         | The MISC transformation programme whose goals include Finance adopting a value-led approach.                                                                                                                                 |
| Resilient Core                     | The pillar of MISC’s strategy focused on improving operational outcomes — asset availability and utilisation, superior execution, and cost optimisation.                                                                     |
| 2030 Ambition                      | MISC’s ambition, which includes a target of a 50% uplift to Cash Flow from Operations.                                                                                                                                       |
| Input lever                        | An operational variable that mathematically drives an output business performance metric in the Value Driver Tree.                                                                                                           |
| Sensitivity analysis               | Analysis identifying which metrics affect the output the most.                                                                                                                                                               |
| Variability analysis               | Analysis identifying which metrics vary most often and to what extent.                                                                                                                                                       |
| Benchmarkable metric               | A metric defined so that like-for-like comparison against external peers or comparable internal instances is possible.                                                                                                       |
| Needle-mover / priority initiative | A prioritised improvement action with an owner, timeline and one-page scope and implementation roadmap.                                                                                                                      |
| UAT                                | User Acceptance Testing.                                                                                                                                                                                                     |
| RLS                                | Row-Level Security in Power BI, restricting data visibility by user role.                                                                                                                                                    |
| VOD                                | Vessel Operating Day — a unit of activity used in unit-cost and unit-rate metrics.                                                                                                                                           |
| TTM                                | Trailing Twelve Months.                                                                                                                                                                                                      |
| BABOK                              | A Guide to the Business Analysis Body of Knowledge (BABOK Guide v3), published by the International Institute of Business Analysis (IIBA). Source of the requirements classification schema used to structure this document. |
| ITIL 4                             | The IT service management framework published by Axelos / PeopleCert. Source of the utility and warranty concepts used to separate functional from technical requirements.                                                   |
| DAMA-DMBOK                         | The Data Management Body of Knowledge published by DAMA International. Source of the data management knowledge areas around which Chapter 4 is structured.                                                                   |
| Utility (ITIL)                     | The functionality offered by a product or service to meet a particular need — what the service does; fitness for purpose.                                                                                                    |
| Warranty (ITIL)                    | Assurance that a product or service will meet agreed requirements, typically covering availability, capacity, security and continuity — how the service performs; fitness for use.                                           |
| Non-functional requirement         | A requirement describing the conditions under which the solution must remain effective, or the qualities the solution must have (BABOK v3). Also called a quality-of-service requirement.                                    |
| Transition requirement             | A requirement describing a capability the solution must have, or a condition it must meet, to facilitate transition from the current to the future state; temporary in nature (BABOK v3).                                    |
| Data lineage                       | The description of where data originated, where it moves, and how it is transformed along the way (DAMA-DMBOK).                                                                                                              |

# 1 Introduction

## 1.1 Purpose

This document defines the business and technical requirements for Zeteo — a diagnostic analytics platform for the MSIC Group, driven by MISC Group Finance. Zeteo advances the Finance Analytics & Insights Report (FAIR) from descriptive reporting into a diagnostic framework that reveals the operational drivers behind financial results and supports data-driven value creation initiatives.

The document is the authoritative basis for project governance and approvals; intended audience includes Finance leadership, the Data Governance & Analytics (DGA) team, and the Platform & ICT Enablement function. Each chapter targets a distinct audience and approval decision, as described in section 1.4.

## 1.2 Project Name and Rationale

The project is named Zeteo, from the Ancient Greek ζητέω (zētéō) — to seek, to search for, to inquire into, to investigate. The classical sense is stronger than simple looking: it means to seek by inquiring, to investigate a matter through to a binding resolution — to get to the bottom of a matter. That is precisely the shift this project asks of Finance.

The name was chosen because each element of its meaning maps directly onto a commitment made in the project vision:

- To seek — Finance today sees what happened, not why. Zeteo goes looking for the driver behind the reported number.
- To inquire — the Value Driver Tree decomposes financial outcomes into the operational levers that produced them, and AI Agents (LLM Models) let users ask the question directly.
- To investigate through to resolution — the analysis runs from variance to root cause to a prioritised initiative with an owner and a timeline. An unresolved insight is not a result.
- To get to the bottom of a matter — clear data lineage ensure every figure can be traced to its source data, enabling trust and accountability.
- Seeking is a human act — Humans design the logic, approve the transformation and own the conclusion. AI accelerates the search by analyzing data, surfacing patterns, and generating hypotheses, but it does not decide or own outcomes, nor substitute human accountability.

The name therefore states the ambition plainly. MISC’s 2030 Ambition targets a 50% uplift to Cash Flow from Operations, and that uplift will not be found in the reported result — it sits in the operational levers underneath it. Zeteo is the discipline of going to look for it, and of not stopping until the matter is settled. Finance moves from book-keeper to investigator: from describing symptoms to diagnosing causes, from “what has happened” to “what would happen”, and from reporting performance to driving it.

References to FEED in earlier material — including the Data Driven & Digital 2025 pack and the FEED Requirements document — refer to this project.

## 1.3 Product Vision and Guiding Principles

Zeteo is not conceived as a one-off reporting deliverable but as an enduring diagnostic capability for Group Finance. This section states the long-term vision, the defining characteristics the product must hold as it evolves, and the philosophy that governs how it is built and used, so that later design and delivery decisions can be tested against a stable intent.

### 1.3.1 Long-term product vision

The long-term vision is for Zeteo to become the Group's standing diagnostic layer over financial performance — the place Finance and the business go to understand why a result occurred and what to do about it. Over successive phases it grows from a Value Driver Tree over core financial metrics into a broader diagnostic platform that connects financial outcomes to their operational drivers across business units, enriches that analysis with structured and unstructured context, and sustains a closed loop from variance, to root cause, to a prioritised initiative with an owner and a timeline. The ambition is durability and reuse: a governed, single-source-of-truth foundation that many consumption experiences — reports, the custom application, and AI-assisted enquiry — draw from, rather than a series of disconnected point solutions.

This is not an untested or theoretical ambition. Driver-based diagnostic analytics is a mature, proven discipline in other data-intensive industries, and Zeteo applies those established patterns to Group Finance. Manufacturing and process industries have long used driver trees and root-cause analysis (for example Six Sigma and Overall Equipment Effectiveness decomposition) to trace an output back to its contributing factors; retail and consumer businesses routinely decompose revenue and margin into price, volume and mix drivers; and digital and technology firms operate around metric trees and closed-loop KPI diagnostics that link an outcome to its levers and to a remediating action. What Zeteo does is bring this well-understood, achievable approach — a governed data foundation, a value driver tree, traceable root-cause analysis and a closed loop to action — to financial performance management, rather than inventing an unproven concept.

> **References:** For manufacturing driver-tree and root-cause analysis practice, see: Nakajima, S., _Introduction to TPM: Total Productive Maintenance_ (Productivity Press, 1988) — the originating text for Overall Equipment Effectiveness (OEE) decomposition; and George, M. L. et al., _The Lean Six Sigma Pocket Toolbook_ (McGraw-Hill, 2005) — the DMAIC framework and cause-and-effect driver analysis. For retail price/volume/mix decomposition, see: Farris, P. W. et al., _Marketing Metrics: The Manager's Guide to Measuring Marketing Performance_, 3rd ed. (Pearson, 2015), Chapter 2. For digital/technology metric trees and closed-loop KPI diagnostics, see: Croll, A. &amp; Yoskovitz, B., _Lean Analytics: Use Data to Build a Better Startup Faster_ (O'Reilly, 2013), Part III on metric-driven organisations. _(References not verified in this session — please confirm exact titles, editions and stable URLs if formal citations are required.)_

### 1.3.2 Product characteristics

As it evolves, Zeteo shall hold the following defining characteristics:

- Diagnostic, not merely descriptive — the product explains the drivers behind a number, not just the number itself.
- Single source of truth — all consumption draws from the governed Gold Layer, so every figure reconciles across reports, application and AI answers.
- Traceable and explainable — every figure and every AI-generated hypothesis can be traced to its source data and underlying logic.
- Governed and secure — data access, lineage and model definitions are governed centrally in Unity Catalog under agreed ownership.
- Extensible and modular — new value drivers, business units, data domains (including unstructured sources) and consumption surfaces can be added without re-platforming.
- Human-owned, AI-accelerated — AI surfaces patterns and generates hypotheses; humans design the logic, approve transformations and own the conclusion.
- Trusted and adopted — the product earns confidence through accuracy, transparency and a decision-support experience that fits how Finance and the business actually work.

### 1.3.3 Guiding philosophy

The philosophy behind Zeteo follows directly from its name — to seek by inquiring, and not to stop until the matter is settled:

- Seeking is a human act — humans own the questions, the judgement and the accountability; AI is a tool that accelerates the search, never a substitute for it.
- Insight must resolve — an insight that does not lead to an owned, time-bound action is not a result; the product is built to close the loop from analysis to initiative.
- Trust is earned through lineage — clarity of data lineage and transparent logic are prerequisites for adoption, not afterthoughts.
- Build on a governed foundation — invest once in a governed, single-source-of-truth data foundation and reuse it across every consumption experience.
- Evolve deliberately — deliver value in phases against a stable long-term intent, favouring extension over rebuild and preserving traceability as scope grows.

## 1.4 Document Structure and Requirements Classification

Zeteo is a large, multi-year programme spanning business change, analytics design and platform engineering. To keep the requirements unambiguous and separately approvable, this document is organised into three chapters — Business Requirements, Functional Requirements and Technical Requirements. The boundary between the three is not arbitrary; it follows established definitions from BABOK v3, ITIL 4 and DAMA-DMBOK, which are set out below so that every reader applies the same test when deciding where a requirement belongs.

### 1.4.1 Requirements classification — BABOK v3 (IIBA)

BABOK v3 defines a Requirements Classification Schema covering four requirement types. Their application in this document is:

|                                        |                                                                                                                                                                                                                                      |                                                                                                                                                                                |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **BABOK requirement type**             | **BABOK definition**                                                                                                                                                                                                                 | **Where it sits in this document**                                                                                                                                             |
| Business requirements                  | Statements of goals, objectives and outcomes that describe why a change has been initiated. They can apply to the whole enterprise, a business area or a specific initiative.                                                        | Chapter 2. The 2030 Ambition, the cost transparency problem, the objectives, and the value the solution must create.                                                           |
| Stakeholder requirements               | Describe the needs of stakeholders that must be met in order to achieve the business requirements. They act as the bridge between business requirements and solution requirements.                                                   | Chapter 2, expressed as the Key Business Questions and the Stakeholder and Tool User profiles — what each stakeholder group must be able to ask of, and do with, the solution. |
| Solution requirements — functional     | Describe the capabilities a solution must have in terms of the behaviour and information the solution will manage.                                                                                                                   | Chapter 3. What the dashboard and the analytical agents must do — drill-down, variance analysis, benchmarking, conversational query, driver ranking, root cause proposal.      |
| Solution requirements — non-functional | Describe the conditions under which the solution must remain effective, or the qualities the solution must have. Also referred to as quality-of-service requirements.                                                                | Chapter 4. Performance, traceability, auditability, security and access, refresh cadence, and the architectural constraints that deliver them.                                 |
| Transition requirements                | Describe the capabilities the solution must have, and the conditions it must meet, to facilitate transition from the current state to the future state. They are temporary in nature and cease to apply once the change is complete. | Chapter 2 (change management, adoption, upskilling) and Chapter 4 (pilot, UAT, data migration and proxy data, handover and knowledge transfer).                                |

This classification governs the placement of requirements in this document. Why the change is needed belongs in Chapter 2 even if it names a technology; what the solution must do belongs in Chapter 3 even if a business stakeholder raised it; how well, how fast, how securely or how traceably it must do it belongs in Chapter 4.

### 1.4.2 Service perspective — ITIL 4 (Axelos / PeopleCert)

ITIL 4 defines a service as a means of enabling value co-creation. Zeteo is a service in this sense — Finance and the business units co-create the value; the platform does not create it on their behalf. Two ITIL concepts draw the line between Chapters 3 and 4:

|                           |                                                                                                                                                                                        |                                                                                                                                                                                                                                  |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **ITIL 4 concept**        | **ITIL definition**                                                                                                                                                                    | **Application to Zeteo**                                                                                                                                                                                                         |
| Utility — fit for purpose | The functionality offered by a product or service to meet a particular need. Utility is what the service does.                                                                         | Chapter 3. Zeteo’s utility is diagnostic: decomposing a financial outcome into its operational drivers, ranking those drivers by contribution to variance, and proposing causes and mitigations.                                 |
| Warranty — fit for use    | Assurance that a product or service will meet agreed requirements. Warranty typically addresses availability, capacity, security and continuity. Warranty is how the service performs. | Chapter 4. Predictable Power BI query performance, append-only auditability, full lineage back to source, role-based access and row-level security, scheduled refresh reliability, and bounded, version-controlled AI behaviour. |
| Outcome                   | A result for a stakeholder enabled by one or more outputs.                                                                                                                             | Chapter 2. The output is a dashboard; the outcome is a prioritised, owned initiative that moves Cash Flow from Operations. Zeteo is measured on the latter.                                                                      |

Both must be satisfied. Utility without warranty produces insight Finance cannot defend in front of a CFO; warranty without utility produces a fast, secure, well-governed report that answers no question worth asking.

ITIL 4's four dimensions of service management map to this document as follows: organisations and people, and value streams and processes to Chapter 2; information and technology to Chapter 4.

### 1.4.3 Data management perspective — DAMA-DMBOK (DAMA International)

DAMA-DMBOK defines data management as the plans, policies, programmes and practices that deliver, control, protect and enhance data assets across their lifecycle. Chapter 4 is structured around the knowledge areas below:

|                                          |                                                                                                                                                                                                                     |                                                                                                                                                                             |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **DAMA-DMBOK knowledge area**            | **Scope of the knowledge area**                                                                                                                                                                                     | **Application to Zeteo**                                                                                                                                                    |
| Data Governance                          | Exercise of authority and control over the management of data assets — policy, stewardship, ownership and decision rights.                                                                                          | Global Process Owners and Master Data Owners govern process and master data standards; the prohibition on off-system postings is a governance control, not a technical one. |
| Data Architecture                        | The design of the structures and blueprints that align data assets with enterprise strategy.                                                                                                                        | The medallion architecture — Bronze, Silver and Gold zones with distinct ownership — and the Gold Layer VDT table as the single permitted source for the Power BI report.   |
| Data Modelling & Design                  | Discovering, analysing, representing and communicating data requirements in a precise form.                                                                                                                         | The Value Driver Tree, the Gold Layer schema, its grain, and the surrogate key strategy for controlling row-count fanout.                                                   |
| Data Integration & Interoperability      | Movement and consolidation of data within and between data stores, applications and organisations.                                                                                                                  | Ingestion from SAP, Anaplan and BU operational source systems through the Enterprise Data Hub; the Silver-to-Gold transformation job.                                       |
| Metadata Management                      | Collecting, categorising, maintaining and making accessible the data that describes the data.                                                                                                                       | Semantic annotation of tables and fields (business meaning, unit of measure, grain, refresh cadence) — the context on which the AI agent depends.                           |
| Data Quality                             | Planning, implementation and control of activities that apply quality management techniques to data, measured across dimensions including accuracy, completeness, consistency, timeliness, uniqueness and validity. | Data quality validation gates the Operational Driver Analysis agent; the analysis runs only on a Gold Layer refresh that has passed validation.                             |
| Data Warehousing & Business Intelligence | Planning, implementation and control processes that provide decision support data and enable knowledge workers to derive value from it.                                                                             | The Power BI semantic model, the dashboards structured by Value Driver Tree, and Power BI AI agents.                                                                        |
| Reference & Master Data                  | Managing shared data to reduce redundancy and improve quality through standardised definition and use of data values.                                                                                               | COA / GL account, profit centre, cost centre, budget structure, customer and asset master — the standardised objects on which comparability across entities depends.        |

DMBOK defines data lineage as where data originated, where it moves and how it is transformed. Lineage is what makes a diagnostic claim defensible, and the reason every Gold Layer row carries source, timestamp and transformation-version metadata.

### 1.4.4 How this document is organised

The table below summarises the three chapters, the question each answers, its primary audience, and the standards basis for its boundary.

|                            |                                                          |                                                                                                   |                                                                                       |
| -------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| **Chapter**                | **Question it answers**                                  | **Primary audience**                                                                              | **Standards basis**                                                                   |
| 2. Business Requirements   | Why are we doing this, and what value must it create?    | CFO Group Finance, Finance Leaders Caucus, BU CFOs, Change Management Office                      | BABOK business and stakeholder requirements; ITIL outcomes                            |
| 3. Functional Requirements | What must the solution do?                               | BU Finance, BU Operations SMEs, DGA business analysts, delivery team                              | BABOK functional solution requirements; ITIL utility                                  |
| 4. Technical Requirements  | How must it be built, performed, governed and sustained? | DGA, Enterprise Data Hub, Platform & ICT Enablement, internal delivery team, information security | BABOK non-functional solution requirements; ITIL warranty; DAMA-DMBOK knowledge areas |

### 1.4.5 Document conventions

Headings are numbered explicitly and may extend to the fifth level where the subject requires that precision, so that any requirement or design topic can be cited unambiguously by section number in review, change control and contractual correspondence. Additional heading levels are used only for durable, independently discussable topics; individual requirements, examples, assumptions and ordinary list items remain in their appropriate lists or tables. Items marked in square brackets are open points requiring confirmation before the relevant design is frozen. Requirements described as “illustrative” or “indicative” are working assumptions to be confirmed during the design phase, and are identified as such at the point of use.

# 2 Business Requirements

## 2.1 Definition and scope of this chapter

This chapter states the business and stakeholder requirements for Zeteo. In BABOK v3 terms, business requirements are statements of goals, objectives and outcomes that describe why a change has been initiated, and stakeholder requirements describe the needs of stakeholders that must be met in order to achieve them. In ITIL 4 terms, this chapter defines the outcomes Zeteo must enable — the results for stakeholders, not the outputs the project produces.

Nothing in this chapter prescribes a solution design. Where a technology is named, it is named as context or constraint, not as a requirement. The test for inclusion here is whether the statement would remain true if the solution were built differently. Section 2.7 is the one deliberate exception: it states scope for the project as a whole and therefore names delivery activities that are specified in Chapters 3 and 4.

## 2.2 Project background

MISC’s 2030 Ambition includes a target of a 50% uplift to Cash Flow from Operations (CFFO). One of the key pillars of MISC’s strategy, Resilient Core, focuses on improving operational outcomes — maximising asset availability and utilisation, superior execution, and cost optimisation. MISC has also been losing potential market share to competitors, with a number of global opportunities awarded to others and higher pricing hypothesised as one of the reasons for losing bids.

The complication is that MISC Finance does not currently have the tools to fully break costs down into detailed drivers. This prevents Finance from advising business units proactively on cost reduction, and makes engagement with entities on cost transparency and cost reduction difficult because the underlying visibility does not exist. Left unaddressed, this is a hindrance to the Finance teams achieving the LightSpeed transformation goal of adopting a value-led approach.

MISC Berhad’s Finance north-star is to elevate Finance to drive Enterprise Excellence by enhancing operational efficiency, leveraging data insights, enabling strategic initiatives, and fostering strategic collaborations for sustainable business growth.

Today, financial reporting across the Group is largely descriptive. The FP&A model (Actual vs Budget vs YEP) runs on Azure, RPA/Workato, Anaplan and SAP, while FAIR reporting is produced in Excel and Power BI, with outputs assembled in PowerPoint and BPC. Insight stops at what has happened rather than why it happened.

Zeteo introduces a diagnostic layer built on an Adaptive Deterministic Model and a Value Driver Tree (VDT) that decomposes CFROA, NPAT, Revenue, Expenses, Net Assets and CFFO into their underlying operational drivers. Rollout starts with the asset chartering businesses (Petroleum, Gas and Offshore) at Group and business unit level from Q4’25 through Q3’26, with continued expansion thereafter, followed by Finance COE use cases (SFM, Treasury, Group Tax and Corporate Procurement) and Enterprise Value Creation use cases from Q3’26 onwards.

A key success factor is that manual postings outside the systems are strictly prohibited, as off-system adjustments break the data lineage required for effective value steering.

## 2.3 Objectives and business goals

The objective of developing Zeteo is to drive value creation by improving the above-the-line (revenue), the bottom line (profitability) and the return on investment, with Finance leading the value agenda and Zeteo serving as the enabler.

### 2.3.1 Primary objectives

| ID    | Objective                           | Description                                                                                                                                               |
| ----- | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| BR-01 | Define the cost structure           | Decompose financial outcomes into the detailed operational levers that drive cost across entities.                                                        |
| BR-02 | Measure lever performance           | Quantify each lever's actual performance and its variance against budget, prior periods and comparable peers.                                             |
| BR-03 | Diagnose variance                   | Identify the root causes behind each lever's variance, whether adverse or favourable, and propose candidate responses.                                    |
| BR-04 | Drive action with entities          | Convert diagnostic findings into prioritised, owned value-creation initiatives — whether cost reduction or revenue improvement — agreed with each entity. |
| BR-05 | Support strategic financial targets | Make the operational levers behind the organisation's financial goals visible and actionable, so Finance can measurably contribute to their delivery.     |

### 2.3.2 Supporting business goals

| ID    | Goal                             | Description                                                                                                                                        |
| ----- | -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| BR-06 | Diagnostic over descriptive      | Move Finance from descriptive reporting (symptoms) to diagnostic insight — explaining “why it is happening” instead of merely “what has happened”. |
| BR-07 | Manage by exception              | Highlight what matters most for decision making by managing by exception and maximising the autonomy of business-as-usual activity.                |
| BR-08 | Prioritise high-impact use cases | Identify and prioritise high-impact data-driven value creation use cases from Zeteo diagnostic findings.                                           |
| BR-09 | Enable BU-owned value            | BU CFOs own the P&L outcome, BU Finance owns benefit tracking, BU Operations executes the agreed actions.                                          |
| BR-10 | Establish a data foundation      | Establish a consistent, traceable and self-sustaining data foundation that supports enterprise-wide diagnostics.                                   |
| BR-11 | Upskill Data Citizens            | Upskill the Finance fraternity as Data Citizens so that lower-value dashboarding use cases are progressively built by users with DGA guidance.     |

### 2.3.3 Sustaining value

Not every initiative can be traced distinctly to a value outcome, and some initiatives stem only from identified pain points rather than from diagnostic findings. To ensure value is realised continuously and does not decay once an initiative closes, the drivers behind each initiative are to be ingested into the Enterprise Data Hub (EDH) and monitored under a continuous "feed".

| ID    | Requirement                | Description                                                                                                                                                |
| ----- | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| BR-12 | Ingest initiative drivers  | The drivers behind each value-creation initiative shall be ingested into the EDH so value can be monitored beyond the life of the originating initiative.  |
| BR-13 | Monitor under a named feed | These drivers shall be monitored under a recurring "feed" with a named owner to sustain realised value and prevent value decay after an initiative closes. |

## 2.4 Key business questions

The following are the stakeholder requirements expressed as questions the solution must be able to answer. They are the primary acceptance test for Chapter 3.

> **Status — illustrative.** The questions in 2.4.1 and 2.4.2 are illustrative examples, not the confirmed set. They have not yet been validated in a stakeholder workshop and are provided to convey the intended type, granularity and framing of the questions Zeteo must answer. The confirmed set will be established through the workshop described in 2.5.2 and refined with management before the dashboard design is frozen; question IDs (BQ-nn) may be added, removed or reworded at that point.

### 2.4.1 Cost transparency and value creation questions

- BQ-01 — What is cost in $ and its % composition, for MISC Group overall and for each MISC entity?
- BQ-02 — What is the % split between front-office and back-office costs, at corporate level and at entity level?
- BQ-03 — What is revenue in $ and its % split between long-term and spot charter, and what are the effective unit rates by vessel type, per day, per distance travelled and per customer account?
- BQ-04 — What is cost in $ and its % composition per voyage (per unit distance travelled) for Petroleum and LNG shipping?
- BQ-05 — What is the cost in $ of repair and maintenance per vessel, per year, per operations day and per distance travelled?
- BQ-06 — What are the % availability and distance travelled per vessel per year, by vessel type?
- BQ-07 — What is third-party spend in $ and its % composition for MISC and its entities, and what are the major cost buckets?

### 2.4.2 Analysis and benchmarking considerations

The following considerations apply to each question above:

- BQ-08 — What are the most effective segmentation measures to ensure like-for-like comparison (e.g. by vessel type, per day, per distance travelled)?
- BQ-09 — Are these metrics in line with external peers?
- BQ-10 — Are these metrics in line with other comparable internal instances?
- BQ-11 — Can we drill down and identify which specific cost item(s) contributed to the deviation?
- BQ-12 — How can AI help focus Finance analysis on the key insights and levers only?

## 2.5 Delivery value stream and operating model

> **Scope and status — target (future-state) process.** This section describes the intended _to-be_ delivery value stream that Zeteo is being introduced to enable. It is context that gives rise to the requirements in Chapter 3, not a specification in itself. The current-state (as-is) process is out of scope for this URS. Steps are classified as either **operating model** (activities performed by people and governance forums) or **solution-enabled** (activities that Zeteo must support, each of which maps to one or more requirements in Chapter 3).

### 2.5.1 Diagnostic delivery value stream

The intended end-to-end diagnostic value stream, derived from the use-case sourcing and diagnostic cycle in the Data Driven & Digital 2025 pack, is set out below. The "Type" column identifies whether the step is an operating-model activity or a capability Zeteo must enable.

| #   | Step                                                                                             | Type             |
| --- | ------------------------------------------------------------------------------------------------ | ---------------- |
| 1   | Financial element selected from the Value Driver Tree                                            | Operating model  |
| 2   | FAIR descriptive baseline reviewed                                                               | Solution-enabled |
| 3   | Zeteo diagnostic dashboard designed and developed for that element (granular)                    | Solution-enabled |
| 4   | Operational causes hypothesised using an Open Domain Model and validated against fact-based data | Solution-enabled |
| 5   | Validated causes adapted back into the deterministic diagnostic model                            | Solution-enabled |
| 6   | Strategic initiatives sourced and assessed for effort and impact                                 | Operating model  |
| 7   | Prioritised annually                                                                             | Operating model  |
| 8   | Value creation executed and benefits tracked                                                     | Operating model  |

The solution-enabled steps (2–5) are the source of the functional requirements in Chapter 3. The operating-model steps (1, 6–8) describe how the organisation works with Zeteo and are governed through the forums in 2.6 and the sustaining-value feed in 2.3.3.

### 2.5.2 Use-case sourcing (operating model)

Use-case sourcing is an operating-model governance activity, not a Zeteo feature. The intended cadence is: Zeteo diagnostic potential use cases and operational requests (workshop) → viability assessment (effort and impact) → annual prioritisation → DDVC MVP process. This workshop is also where the illustrative business questions in 2.4 are validated and confirmed.

[Insert process map diagram — refer to the FEED Approach and Sourcing Data Driven Use Cases slides]

### 2.5.3 Operating model

Zeteo is designed around an operating model of CFO-led prioritisation, BU-owned value and centrally enabled diagnostics: the Finance Leaders Caucus (FLC) endorses focus areas and sequencing, business units own the value hypothesis and benefit tracking, and the DGA / Data Analytics function centrally builds and maintains the diagnostic models and dashboards. This operating model runs the value stream in 2.5.1 and is realised through the roles in 2.6. The dependencies and constraints on which it relies — cross-functional collaboration and the prohibition on off-system adjustments — are stated as assumptions in 2.9.

## 2.6 Stakeholders and tool users

The following users will utilise the solution. Estimated user counts are to be confirmed with each business unit.

|                                               |                                                                                                                   |                               |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| **Role**                                      | **Description**                                                                                                   | **Estimated number of users** |
| CFO Group Finance / BU CFOs                   | Executive sponsors and P&L owners. Use Zeteo insights to set enterprise value priorities and endorse focus areas. | [TBC]                         |
| BU Finance (Value Owner)                      | Own the value hypothesis and benefit tracking for Zeteo-related initiatives; primary day-to-day diagnostic users. | [TBC]                         |
| BU Operations SMEs                            | Interpret operational drivers behind financial variance and execute agreed mitigation actions.                    | [TBC]                         |
| DGA Business Analysts / Data Analytics        | Build and maintain the diagnostic models, dashboards and data pipelines; support use-case squads.                 | [TBC]                         |
| Finance Leaders Caucus / Core Committee / PIM | Governance users — track value hypotheses versus realised outcomes and escalate risks and blockers.               | [TBC]                         |
| **Total**                                     |                                                                                                                   | [TBC]                         |

## 2.7 Scope

### 2.7.1 In scope

The following activities and functionalities are included in the scope of this project. They are grouped into seven delivery themes (2.7.1.1 to 2.7.1.7) that broadly follow the delivery sequence; the numbering aids cross-reference and does not imply that the themes run strictly one after another.

#### 2.7.1.1 Coverage and pilot horizon

- Zeteo diagnostic dashboard at Group level and across the pilot businesses, starting with the asset chartering businesses (Petroleum, Gas, Offshore), Q4’25 to Q3’26, with expansion to further businesses as a post-pilot activity.

#### 2.7.1.2 Value Driver Tree and diagnostic modelling

- Human-led VDT design: tree structure, parent–child relationships, calculation logic and KPI definitions expressed in natural language, aligned with management, together with an agreed list of key hypotheses and benchmarkable metrics.
- A calculation model validating the comprehensiveness and accuracy of the VDT before it is built into the data platform.
- Diagnostic model development, including the adaptive deterministic model and validated cause library.
- Design and development of the Zeteo landing dashboard (granular) for each financial element in the Value Driver Tree.

#### 2.7.1.3 Data specification and engineering

- A Data Specification document covering source, owner, definition, type, frequency and relationship with other datasets, plus source-to-target mapping and transformation logic for key metrics (with proxy data where applicable).
- Data ingestion and transformation from source systems (e.g. SAP, Anaplan and BU operational systems) through EDH (Silver and Gold layer).
- AI-agent generation of the Gold transformation script, operational driver analysis and root cause & mitigation proposal, with human review and approval throughout.

#### 2.7.1.4 Dashboard design and build

- Dashboard mock-up and wireframing, defined visual types, initial KPI definitions and calculation logic, and user sign-off on the design.
- Build and configuration of live dashboards connected to curated datasets, including measures, calculated fields and filters, data refresh and performance optimisation, and role-based access and security.
- Enablement of AI agents on the semantic model and report.

#### 2.7.1.5 Diagnostic outputs and initiative simulation

- Sensitivity and variability analyses, a list of root causes behind performance issues, a list of potential solutions, a simulated (indicative) ranking of improvement initiatives and AI use cases, and a detailed one-page scope and implementation roadmap for each candidate initiative. This is a simulation exercise; the actual prioritisation of initiatives is a post-deployment activity.

#### 2.7.1.6 Pilot, rollout and handover

- Pilot dashboards published to a test workspace, user acceptance testing scenarios and results, consolidated feedback and an enhancement backlog, and refinement based on pilot input.
- Rollout to wider user groups with end-user enablement and walkthrough sessions, usage guidelines, dashboard documentation and a user manual.
- Handover and knowledge transfer to the MISC data and technology teams so that the dashboards can be maintained going forward.

#### 2.7.1.7 Enablement and change management

- Change management: leadership syndication, awareness sessions for the Finance fraternity, team-led workshops, and dashboard training for Finance Operations and Leadership.

### 2.7.2 Exclusions

The following activities and functionalities are not included in the scope of this piloting project. Exclusion does not mean an item is dropped or ignored; several are valid activities that belong to a later phase, a separate workstream, or a different owner. They are grouped below to make that distinction clear.

#### 2.7.2.1 Deferred to a later phase (post-pilot or post-deployment)

- Expansion of coverage to businesses beyond the pilot asset chartering businesses, which follows the pilot.
- Implementation of the prioritised improvement initiatives themselves. This pilot identifies, scopes and simulates a ranking for them; the actual prioritisation and execution are post-deployment activities owned by the business units.
- Use-case squad enablement per financial element (BU Finance value owner, BU Operations SMEs, DGA business analyst and the SI team) and facilitated Finance–Operations prioritisation of needle-mover initiatives, which is a post-deployment activity.
- Benefit tracking and value realisation reporting against the value hypotheses, which is a post-deployment activity.

#### 2.7.2.2 Delivered under a separate workstream or programme

- Finance COE use cases (SFM, Treasury, Group Tax and Corporate Procurement) — planned separately from Q3’26 onwards.
- Enterprise Value Creation use cases — planned separately from Q3’26 onwards.
- The FP&A project (Actual vs Budget vs YEP) and the FAIR descriptive reporting suite, which remain separate workstreams and are treated as source or adjacent systems.

#### 2.7.2.3 Owned by another function (out of scope for this project)

- Remediation of master data and data capture processes, which is governed under the Process & Data Governance framework by the Global Process Owners and Master Data Owners.
- Replacement or upgrade of source systems (SAP, Anaplan) and underlying ICT infrastructure procurement.

Functional exclusions are stated in section 3.9 and technical exclusions in section 4.13.

## 2.8 Delivery workstreams and deliverables

The table below summarises the deliverables and intended outcomes for each delivery workstream.

|                                              |                                                                                                                                                                                                                                                                                                                                                                                         |                                                                                                                                                                                                                                                                                                                                                                            |
| -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Workstream**                               | **Deliverables**                                                                                                                                                                                                                                                                                                                                                                        | **Outcomes**                                                                                                                                                                                                                                                                                                                                                               |
| 1. VDT design and hypothesis alignment       | Value Driver Tree structure, parent–child relationships and calculation logic aligned with management; list of key hypotheses to be addressed and benchmarkable metrics; calculation model validating comprehensiveness and accuracy of the VDT; diagnostic model design including the adaptive deterministic model and validated cause library.                                        | Management alignment around the VDT logic and key hypotheses; clarity around the critical input levers that drive business performance; understanding of the mathematical relationship between input levers and output business performance; a validated diagnostic model ready for data and engineering.                                                                  |
| 2. Data specification and preparation        | Data Specification document (source, owner, definition, type, frequency, relationship with other datasets); source-to-target mapping and transformation logic for key metrics, with proxy data if applicable; dashboard-ready data model with cleansing and transformation steps documented.                                                                                            | Every VDT metric is mapped to a named source, owner and definition, so its lineage can be traced end to end; a curated, dashboard-ready data model that feeds the dashboards and AI components consistently; Finance can reconcile dashboard figures back to source with repeatable results; known data gaps and proxy assumptions are documented for management decision. |
| 3. Solution platform and application         | Hosting platform and application environment to house the VDT models, data pipelines, dashboards and AI components; access, security and role provisioning aligned with MISC standards; deployment, monitoring and maintenance runbooks; environment separation (development, test and production) with promotion process.                                                              | A single, secure environment where the solution's data, analytics, dashboards and AI components are hosted, operated and maintained; clear ownership and operating model for the MISC technology teams; a platform that supports the pilot today and can scale to further phases.                                                                                          |
| 4. Analytics engineering (data and AI)       | Analytics data pipelines and models productionised from the dashboard-ready data model; feature and metric layer supporting descriptive and diagnostic analytics; AI/ML components for the prioritised diagnostic and use-case scenarios (for example anomaly detection, driver attribution and scenario simulation); documented engineering standards, lineage and refresh scheduling. | A reusable, governed analytics engineering foundation spanning data and AI, rather than one-off extracts; repeatable and traceable data and AI pipelines that Finance and the MISC data teams can trust and extend; readiness to scale diagnostic and AI use cases beyond the pilot.                                                                                       |
| 5. Dashboard design, build, test and rollout | Dashboard mock-up and wireframes; defined visual types and initial KPI definitions; pilot dashboards in a test workspace with UAT scenarios and results; consolidated feedback and enhancement backlog; live Power BI dashboards structured by Value Driver Tree; handover documentation and user manual.                                                                               | Live, fit-for-purpose dashboards available to support performance monitoring and insight generation by MISC management; sufficient handover and knowledge transfer to the MISC data and technology teams to maintain the dashboards going forward.                                                                                                                         |
| 6. Diagnostic and initiative prioritisation  | Sensitivity and variability analyses; list of root causes behind performance issues; list of potential solutions; prioritised list of improvement initiatives and AI use cases; detailed one-pager scoping and implementation roadmap for priority initiatives.                                                                                                                         | Clear understanding of sensitivity (which metrics affect output the most) and variability (which metrics vary often and to what extent); management alignment on the size of the prize; executive consensus on priority initiatives and clear next steps to implement them.                                                                                                |
| 7. Enablement and change management          | Leadership syndication and awareness sessions for the Finance fraternity; team-led workshops and dashboard training for Finance Operations and Leadership; usage guidelines and end-user walkthrough sessions; communication and engagement plan for the pilot rollout.                                                                                                                 | Finance community understands the Zeteo value proposition and how to use the dashboards in their day-to-day work; leadership endorsement and active sponsorship of the diagnostic approach; a self-sustaining user base that can onboard new users beyond the pilot.                                                                                                       |

## 2.9 Business assumptions

The following assumptions underpin the scope, deliverables and timeline set out above. Each is stated with its owner and the impact should it prove invalid, so that the assumption can be tracked and escalated. Assumptions that are also constraints or dependencies are cross-referenced to section 2.5.3; those awaiting confirmation are cross-referenced to the relevant open item in section 5.

| ID    | Assumption                                                                                                                                                                                                                            | Owner                  | Impact if invalid                                                                                                      |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| BA-01 | The key hypotheses and business questions are preliminary and will be confirmed with management before the dashboard design is frozen.                                                                                                | Group Finance          | Design rework and schedule slippage if hypotheses change after the design freeze.                                      |
| BA-02 | External peer benchmarks are available, or can be sourced, for the metrics identified as benchmarkable (2.7.1). This is pending confirmation under open item OI-08; if not confirmed, an alternative comparison basis will be agreed. | Group Finance          | Benchmarking views (e.g. FR-10) cannot be delivered as specified and must be rescoped to an internal comparison basis. |
| BA-03 | Source-system data (SAP, Anaplan and business-unit systems) is available, of sufficient quality, and refreshed with the timeliness the in-scope metrics require.                                                                      | Data / ICT             | Metrics are delayed, unreliable, or must be dropped; remediation effort falls outside scope (see exclusion 2.7.2.3).   |
| BA-04 | Where source data is incomplete, management accepts the use of proxy data as a stand-in for the affected metrics.                                                                                                                     | Group Finance          | Affected metrics cannot be shown, or are shown with caveats that reduce their decision value.                          |
| BA-05 | The delivery platform and licensing (Enterprise Data Hub, Power BI capacity and AI-agent enablement) are available for the full pilot window.                                                                                         | ICT                    | The pilot cannot be built or run to plan; timeline and scope must be revised.                                          |
| BA-06 | Business units nominate Finance and Operations representatives to the use-case squads within the timeline agreed with the Finance Leaders Caucus [timeline TBC].                                                                      | Business units         | Squads are under-resourced, slowing requirements capture and validation.                                               |
| BA-07 | The Finance Leaders Caucus endorses the focus areas and sequencing, and sustained cross-functional collaboration (Finance, Operations, Procurement, ICT and Data) is maintained throughout delivery.                                  | Finance Leaders Caucus | Priorities stall or conflict; dependent deliverables cannot proceed (see 2.5.3).                                       |
| BA-08 | The prohibition on manual postings and off-system adjustments is enforced as governance policy, not merely recommended, so that data lineage is preserved.                                                                            | Group Finance          | Data lineage is broken, undermining trust in the metrics and the diagnostic conclusions (see 2.5.3).                   |

The most material of these risks is data availability (BA-03, BA-04): source data may be missing, of insufficient quality, or not yet system-captured (OI-09), which would otherwise stall design and validation. The strategy for addressing this is to begin with simulated data. Rather than waiting for every source feed to be confirmed and cleansed, the pilot builds the Value Driver Tree, dashboards and diagnostic flow on a realistic simulated dataset that mirrors the intended schema, grain and driver hierarchy. This decouples early delivery from data readiness, kick-starts the requirements and design discussion with something concrete on screen, and brings the concept to life so that Finance and Operations can react to a working diagnostic rather than an abstract specification. As real source data becomes available it is substituted for the simulated feed against the same schema, with each remaining gap documented and closed before go-live in line with A-05. Because the simulated data conforms to the agreed VDT structure, the transition to live data is a data-source swap, not a redesign.

A further benefit of building on the simulated dataset is that it enables sensitivity analysis from day one. Because the Value Driver Tree makes the relationship between each operational driver and the financial outcome explicit, the solution can flex each driver in turn and observe its effect on CFROA and the downstream metrics, even before the corresponding source is live. This establishes end-to-end traceability from a driver to the value it moves, and it ranks the drivers by materiality. That ranking is the business case: it shows, in advance, which data sources are worth the investment to capture, store, ingest and cleanse, and by how much. A source that a sensitivity analysis proves to be a high-impact lever justifies the cost of a data-capture tool, a server, an access licence or a pipeline against a quantified expected value; a source that moves the outcome only marginally can be deferred. In this way the simulated pilot does more than de-risk delivery — it prioritises the data-maturity actions in section 4.6.1 by value, so that investment anywhere in the data lifecycle is directed where the sensitivity analysis shows it will most improve decision quality.

# 3 Functional Requirements

## 3.1 Definition and scope of this chapter

This chapter states the functional solution requirements. BABOK v3 defines functional requirements as those that describe the capabilities a solution must have in terms of the behaviour and information the solution will manage. ITIL 4 describes the same idea as utility — the functionality offered by a service to meet a particular need, or what the service does, expressed as fitness for purpose.

Each requirement in this chapter answers one or more of the key business questions in section 2.4, and is testable: it can be demonstrated in a review or a UAT scenario. Statements about how well, how fast, how securely or how traceably a capability performs are non-functional and belong in Chapter 4.

## 3.2 Value Driver Tree — authoritative blueprint

The Value Driver Tree is the foundation on which all downstream transformation, analysis and reporting rests. Its structure is defined first so that every subsequent requirement can reference it.

The choice of a Value Driver Tree is deliberate, and a central control against AI hallucination. A tree of financial metrics and operational drivers, with explicit parent–child relationships and human-approved calculation logic, gives the solution a fixed, auditable structure of ground truth: every figure resolves to a defined node, every node to a named source, and every relationship to an agreed formula. AI agents are therefore constrained to reason within this known structure — ranking, comparing and explaining movements across defined nodes — rather than inventing metrics, drivers or relationships that do not exist. This turns the VDT into a guardrail: it narrows the space in which the AI can operate to the organisation's own validated financial logic, so that its outputs remain traceable, reproducible and reconcilable rather than plausible-sounding but ungrounded. In this the VDT complements the specialist-agent rationale in section 5.4, which constrains the agent to the approved schema and VDT rules for the same reason.

| ID    | Requirement                                                                                                                                                                                                                                                                    |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| FR-01 | Each node in the tree shall be either a financial metric or an operational driver, with defined parent–child relationships and calculation logic expressed in natural language. The tree is the authoritative blueprint governing all downstream transformation and reporting. |
| FR-02 | The tree shall decompose CFROA, NPAT, Revenue, Expenses, Net Assets and CFFO into their underlying operational drivers.                                                                                                                                                        |
| FR-03 | The user shall be able to traverse from any financial outcome to the operational lever beneath it, and back.                                                                                                                                                                   |

## 3.3 Data layer — Gold Layer dataset scope

| ID    | Requirement                                                                                                                                                                                                                                          |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-04 | The Gold Layer VDT dataset shall expose aggregated driver values only — one row per driver per time period. Transactional line-item detail is excluded to keep the semantic model performant and the report consumable by a broad business audience. |

## 3.4 Presentation and navigation

| ID    | Requirement                                                                                                                                                                                     |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-05 | The solution shall provide a landing dashboard per financial element, with drill-down from CFROA, NPAT, Revenue, Expenses and CFFO to individual operational drivers via the Value Driver Tree. |
| FR-06 | The user shall be able to navigate from a business outcome to the actionable input levers beneath it, and pinpoint the specific lever or levers that produced a performance gap.                |
| FR-07 | Dashboard layout, page structure and navigation, visual types (charts, tables, KPIs, filters) and initial KPI definitions shall be agreed with users and signed off before build.               |

## 3.5 Diagnostic and analytical capabilities

| ID    | Requirement                                                                                                                                                                                        |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-08 | The solution shall present variance of actual against budget or plan, showing only the top factors of variance.                                                                                    |
| FR-09 | The user shall be able to decompose cost into detailed drivers and identify the cost item or items contributing to a deviation, at Group, entity, voyage and vessel level.                         |
| FR-10 | The solution shall present effective unit rates and cost per unit of activity: per operating day, per distance travelled, per voyage, per vessel and per customer account.                         |
| FR-11 | The solution shall present leading and lagging indicator views — lagging indicators to validate results, leading indicators to signal what is coming ahead.                                        |
| FR-12 | The solution shall highlight by exception any anomalies, outliers, errors and omissions, incidents and divergence from established norms.                                                          |
| FR-13 | The solution shall identify which metrics affect the output most (sensitivity) and which vary most often and by how much (variability).                                                            |
| FR-14 | The solution shall support like-for-like comparison against external peers and comparable internal instances, segmented by vessel type, per day, per distance travelled and other agreed measures. |
| FR-15 | The solution shall provide a use-case pipeline view supporting effort-versus-impact prioritisation (Quick Wins, Big Projects, Filler Tasks, Avoid/Minimise).                                       |

## 3.6 AI-assisted analysis

### 3.6.1 Operational Driver Analysis

| ID    | Requirement                                                                                                                                                                                                                                                                                                                                                                                                   |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-16 | On successful Gold Layer refresh and data quality validation, an AI agent shall rank Value Driver Tree nodes by absolute and relative contribution to period-over-period variance in a target financial metric. The output is one row per driver per period, carrying contribution value, percentage share, rank and direction. The value of N is configurable per financial metric and agreed during design. |

### 3.6.2 Root Cause & Mitigation Analysis

| ID    | Requirement                                                                                                                                                                                                                                                                                                                                          |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-17 | A further AI agent shall retrieve relevant passages from internal domain knowledge (operational SOPs, prior incident reports, business context documents) using semantic search, synthesise plausible root causes ranked by likelihood, and propose corresponding mitigation actions in natural language, with a human-editable Analyst Notes field. |

### 3.6.3 Hypothesis capture and the human decision layer

| ID    | Requirement                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-18 | Operational causes and mitigations proposed by an Open Domain Model or Large Language Model shall be flagged separately from fact-based findings until validated. The Root Cause & Mitigation output is a structured pre-read for a cross-functional Finance–Operations discussion that challenges, refines or confirms each proposal and produces a prioritised list of needle-mover initiatives with owners, timelines and a classification of analytics versus non-analytics use case. AI output informs the conversation; it does not replace it. |

### 3.6.4 Conversational analytics

| ID    | Requirement                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-19 | AI agents shall be enabled on the semantic model and report so that users can interrogate the data through natural-language queries — for example, asking for average operating cost per vessel operating day by charter type, year-on-year growth for spot charter vessel margins, or the ratio of preventive maintenance cost to total maintenance OpEx cost. The agents shall also surface proactive insights against VDT nodes, flagging material movements against a trailing average. |

## 3.7 Governance and guardrails

| ID    | Requirement                                                                                                                                         |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| FR-20 | The solution shall perform diagnostic analysis using an Adaptive Deterministic Model that constrains AI-generated explanations to validated causes. |
| FR-21 | Role-based access shall determine which entities, business units and cost views each user can see.                                                  |

## 3.8 Data fields — guiding principles

The detailed field-level schema, source-to-target mappings and Gold Layer table definition are design-phase deliverables to be signed off separately by the BI team and BU Operations. The principles below govern that work and establish the categories of data the solution requires.

| ID    | Principle                                                                                                                                                                                                                                                                 |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DF-01 | **Financial statement elements** — CFROA, NPAT, Revenue, Expenses, CFFO, Net Assets and their constituent P&L and balance sheet line items, sourced from SAP and the Anaplan FP&A model (budget, plan and year-end projection values).                                    |
| DF-02 | **Operational drivers** — the non-financial variables that move the financial elements (e.g. fuel consumption, voyage data, maintenance events, crew costs, charter terms), sourced from business-unit operational systems via the Enterprise Data Hub.                   |
| DF-03 | **Master data** — COA/GL accounts, profit centres, cost centres and budget structures, governed by the Master Data Owner and sourced from SAP master data.                                                                                                                |
| DF-04 | **VDT structure fields** — Driver ID, Driver Name, Parent Driver ID, Value, Unit and Period, forming the Gold Layer VDT table at the grain agreed with the BI team.                                                                                                       |
| DF-05 | **Lineage metadata** — source_table, ingestion_timestamp and transformation_version on every Gold Layer row, providing full traceability from report to source.                                                                                                           |
| DF-06 | **AI-agent output fields** — contribution value, percentage share, rank and direction (Operational Driver Analysis); proposed root causes, proposed mitigation actions and Analyst Notes (Root Cause & Mitigation).                                                       |
| DF-07 | **Dimensional attributes** — Site, Business Unit, Product and other slicing dimensions required by the report, confirmed with business units during design.                                                                                                               |
| DF-08 | The detailed field list, source-to-target mappings and Gold Layer schema shall be documented in a separate Data Specification, signed off by the BI team and BU Operations before build, with open points carried in the Open Items and Decisions Register (section 5.1). |

## 3.9 Functional exclusions

The following are explicitly out of scope for this release. Each is stated with its rationale and, where relevant, where the capability is expected to be delivered instead.

| Ref   | Exclusion                                        | Description, rationale and where delivered instead                                                                                                                                                                                                                                                                                                                                                    |
| ----- | ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| FX-01 | Transactional line-item detail and drill-through | The Gold Layer VDT table holds aggregated driver values only; the dashboard does not expose transaction-level records or line-item drill-through. This keeps the semantic model performant and the report consumable by a broad business audience. Detailed interrogation is intended to be delivered separately through a web application with a conversational AI agent, not through the dashboard. |
| FX-02 | Advanced conversational analytics                | Identification of deeper causal relationships, forecasting and prediction, and anomaly detection through the conversational interface are not included. These capabilities depend on future, more advanced deployments and are deferred beyond this release.                                                                                                                                          |
| FX-03 | Autonomous AI decision-making                    | The AI agent generates code and proposals from human-approved specifications only. It does not independently determine logic, data relationships, or final recommendations; the human decision layer retains authority over all outputs.                                                                                                                                                              |

# 4 Technical Requirements

## 4.1 Definition and scope of this chapter

This chapter states the technical and non-functional solution requirements. BABOK v3 defines non-functional requirements as those describing the conditions under which the solution must remain effective, or the qualities the solution must have. ITIL 4 describes the same idea as warranty — the assurance that a service will meet agreed requirements, covering availability, capacity, security and continuity, and expressed as fitness for use.

The chapter follows a scope-to-delivery sequence: governing principles and assumptions; architecture and platform dependencies; data ingestion, governance and transformation; consumption requirements; responsibilities; and exclusions. This sequence supports traceability to the DAMA-DMBOK knowledge areas in section 1.4.3 while presenting the requirements in implementation order.

## 4.2 Design principles

The following principles govern the design and delivery of the solution. They are ordered from the foundational human-authority principle through to operational stability.

| ID    | Principle                             | Description                                                                                                                                                                    |
| ----- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| DP-01 | Human-in-the-loop                     | All tree logic, data mappings and transformation scripts are defined or reviewed by a human before execution.                                                                  |
| DP-02 | Natural language first                | Requirements, VDT rules and semantic annotations are written in plain English to maximise readability and minimise misinterpretation.                                          |
| DP-03 | AI as accelerator, not decision-maker | The AI agent generates code from human-approved specifications; it accelerates delivery but does not decide logic or own outcomes.                                             |
| DP-04 | Single source of truth                | The Gold Layer table is the only data source permitted for the Power BI VDT report.                                                                                            |
| DP-05 | Separation of concerns                | Bronze, Silver and Gold are maintained as distinct zones with clear ownership.                                                                                                 |
| DP-06 | Aggregated scope                      | The Gold Layer VDT table exposes aggregated driver values only.                                                                                                                |
| DP-07 | Stability and cost control            | A human-approved, version-controlled script processes every refresh identically, and AI consumption is bounded to discrete VDT change events rather than continuous operation. |

## 4.3 Technical assumptions

The following assumptions must hold for delivery to proceed. They are ordered by the point in the delivery sequence at which each must be satisfied.

| ID   | Assumption                                                                                                                                               |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A-01 | Platform, access and connection prerequisites stated in sections 4.5 and 4.11 are available before build and test activities begin.                      |
| A-02 | The VDT structure is stable before transformation scripting begins; mid-flight changes to tree logic require re-generation of the transformation script. |
| A-03 | All natural language specifications provided to the AI agent are reviewed and signed off by a human SME before execution.                                |
| A-04 | The final Gold Layer structure, grain and schema are indicative at this stage and must be confirmed with the BI team during the design phase.            |
| A-05 | Where source data is not yet available, proxy data may be used for design and validation purposes, with the gap documented and closed before go-live.    |

## 4.4 Solution architecture

Data shall flow through the Enterprise Data Hub (EDH) medallion architecture on Azure Databricks:

- Bronze Layer — raw ingestion from source systems, with no transformation applied.
- Silver Layer — cleansed and conformed data, annotated with semantic context by human subject matter experts.
- Gold Layer — data modelled to the Value Driver Tree structure and ready for direct consumption by the Power BI semantic model and downstream diagnostic agents.

Bronze, Silver and Gold shall be maintained as distinct zones with defined ownership. The Gold Layer VDT table shall be the only source used by the Power BI VDT report.

The end-to-end processing sequence shall be: source ingestion → Silver Layer conformance and semantic annotation → human-approved Gold Layer schema design → AI-assisted generation of the Silver-to-Gold transformation script → human review, approval and scheduling → Gold Layer refresh and validation → operational-driver analysis → root-cause and mitigation proposals → Finance and Operations review and prioritisation.

### 4.4.1 Proposed solution architecture

The proposed target architecture builds on the medallion model above and comprises the following components, ordered from the governed data foundation, through the operational store, to the custom application, its technology stack, the AI services that sit on top of it, and the visualisation layer.

| Ref  | Component                     | Description                                                                                                                                                                                                                                                                                                                                                                                                               |
| ---- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SA-1 | Gold Unity Catalog foundation | The Gold Layer shall be governed in Databricks Unity Catalog and shall hold the finance and operational data aggregated to the Value Driver Tree structure. It is the single governed source for all downstream consumption, and the semantic model shall source exclusively from these Gold Unity Catalog tables, preserving the single-source-of-truth relationship defined in 4.4 and the schema governed under DF-08. |
| SA-2 | VDT operational store         | The Value Driver Tree shall be served from Databricks Lakebase to provide the low-latency, transactional store required by the application and interactive diagnostic flows, synchronised from the governed Gold Layer.                                                                                                                                                                                                   |
| SA-3 | Custom application            | A custom application shall be built and hosted on Databricks (Databricks Apps), providing the interactive user experience for diagnostic analysis over the VDT.                                                                                                                                                                                                                                                           |
| SA-4 | Application technology stack  | The application shall use FastAPI for the backend service layer, and Svelte with Vite for the frontend build and user interface.                                                                                                                                                                                                                                                                                          |
| SA-5 | AI and agent services         | The diagnostic and hypothesis-generation capabilities shall be delivered by AI services hosted on Databricks or provided by Microsoft Foundry, aligned to the approved AI-agent requirements in 4.10.                                                                                                                                                                                                                     |
| SA-6 | Data visualisation            | Power BI shall provide the reporting and dashboard visualisation layer, rendering the Value Driver Tree and supporting diagnostic views from the semantic model defined in SA-1.                                                                                                                                                                                                                                          |
| SA-7 | Unstructured data (future)    | In a future phase, unstructured data such as market insights and analyst reports shall be stored in a Databricks Unity Catalog volume, where applicable, to enrich diagnostic and hypothesis-generation context for the AI services defined in SA-5.                                                                                                                                                                      |

## 4.5 Platform, tool and environment dependencies

The following platform and environment prerequisites shall be in place. They are ordered from source systems of record through to the delivery tooling that binds them together.

| ID    | Requirement                                                                                                                                                          |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TR-22 | SAP shall remain the system of record for financial and master data, and Anaplan shall remain the source for the FP&A model.                                         |
| TR-18 | Azure Databricks shall provide the data ingestion, storage and transformation environment.                                                                           |
| TR-19 | The EDH environment shall provide accessible Bronze, Silver and Gold zones and scheduled jobs for the Silver-to-Gold transformation and Gold Layer refresh.          |
| TR-21 | Approved AI-agent and machine-learning services shall provide the diagnostic and hypothesis-generation capabilities.                                                 |
| TR-20 | Power BI shall provide visualisation and distribution of the Zeteo reports.                                                                                          |
| TR-23 | Platform & ICT Enablement shall provide the EDH pipelines, cloud infrastructure, security controls, access controls, integrations and APIs required by the solution. |
| TR-24 | Delivery shall use the organisation's approved development, version-control, testing, deployment and change-management tooling and methods.                          |

## 4.6 Data sources and ingestion

The in-scope sources are SAP financial and master data, the Anaplan FP&A model and business-unit operational systems. All source data shall be ingested through the EDH before it is consumed by the solution.

Ingestion pipeline configuration and scheduling shall be completed and approved for each source before dependent transformations are enabled. Where operational data requires a manual extract, the source, owner, format, transfer method and frequency shall be agreed with the relevant business unit and recorded in the Data Specification before build.

### 4.6.1 Data maturity assessment

Each in-scope source shall be graded against a data maturity matrix before it is relied upon, so that readiness is made explicit and the correct enabling action is identified. The matrix scores seven conditions in sequence — required data identified, captured, stored, accessible, ingested, cleaned, and transformed to Gold — and assigns a maturity grade with a recommended action. Only Gold-ready (A+) sources feed the production VDT table; sources below that grade are progressed through the indicated action, and, in line with the data-availability strategy in section 2.9, simulated data stands in for any source not yet at A+ so that design and validation can proceed in parallel.

| Identified | Captured | Stored | Accessible | Ingested | Cleaned | Transformed (Gold) | Grade | Recommended action                |
| ---------- | -------- | ------ | ---------- | -------- | ------- | ------------------ | ----- | --------------------------------- |
| Y          | Y        | Y      | Y          | Y        | Y       | Y                  | A+    | Gold-ready for value creation     |
| Y          | Y        | Y      | Y          | Y        | Y       | X                  | A     | Transform to Gold                 |
| Y          | Y        | Y      | Y          | Y        | X       | X                  | A-    | Data cleansing and cataloguing    |
| Y          | Y        | Y      | Y          | X        | X       | X                  | B+    | Build pipeline to ingest into EDH |
| Y          | Y        | Y      | X          | X        | X       | X                  | B     | Request access licence            |
| Y          | Y        | X      | X          | X        | X       | X                  | C     | Acquire server / storage          |
| Y          | X        | X      | X          | X        | X       | X                  | D     | Acquire data-capture tool         |
| X          | X        | X      | X          | X        | X       | X                  | E     | Assess data necessity             |

The maturity grade of each source, and the action required to raise it, shall be recorded in the Data Specification and cross-referenced to the relevant open item (for example OI-09 for data not yet system-captured).

## 4.7 Data dependencies and governance

Delivery depends on the following governed data conditions, ordered from upstream master-data and capture governance through to per-refresh validation and gap handling.

| ID    | Requirement                                                                                                                                                                                                                                              |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TR-26 | COA/GL account, profit centre, cost centre, budget structure, customer and asset master data used by the solution shall conform to standards approved by the respective Master Data Owners.                                                              |
| TR-27 | Source-data capture processes shall be defined and governed by the relevant Global Process Owners.                                                                                                                                                       |
| TR-28 | Responsibilities for Silver and Gold Layer transformations shall be agreed between EDH, DGA and the internal delivery team before build.                                                                                                                 |
| TR-29 | Each Gold Layer refresh shall pass the agreed data-quality validation checks before the Operational Driver Analysis agent is triggered.                                                                                                                  |
| TR-30 | Where an in-scope KPI is not captured in an approved source, the data gap, accountable owner and required remediation shall be recorded in the Open Items and Decisions Register. Procurement or source-system remediation remains outside this release. |

## 4.8 Data transformation (Silver to Gold)

### 4.8.1 Aggregation strategy

Pre-calculated aggregates shall be the default strategy for scheduled Power BI reporting because they provide predictable query performance and bounded per-refresh compute cost.

Where dimensional combinations create unacceptable row-count fan-out or ambiguous join cardinality, the Gold Layer design shall use a surrogate key to identify each aggregated row uniquely.

On-the-fly querying of the Silver Layer is not part of the scheduled Power BI solution. It may be considered for a future conversational interface where the required analysis combinations cannot be pre-calculated efficiently.

The Gold Layer schema design decision shall record the selected aggregation strategy and its expected volume, cardinality, performance and cost implications.

### 4.8.2 Refresh and change control

| ID    | Requirement                                                                                                                                                                                                                                         |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TR-01 | Refresh shall be append-only: new periods shall be appended and historical rows shall not be overwritten.                                                                                                                                           |
| TR-02 | The approved transformation script shall run unchanged for every routine scheduled refresh. The script shall be regenerated and reapproved only when a driver or metric is added, a calculation rule is modified, or the Gold Layer schema changes. |

## 4.9 Gold Layer schema, metadata and lineage

The Gold Layer VDT table is the terminal output of the core data pipeline and the single source of truth for the Power BI report. Its detailed fields, mappings and validation rules shall be defined in the Data Specification required by DF-08. The requirements below are ordered from table structure and grain through to lineage metadata and documentation.

| ID    | Requirement                                                                                                                                                                      |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TR-03 | The VDT table shall hold one row per VDT node, time period and applicable dimensional combination, with Driver ID, Driver Name, Parent Driver ID, Value, Unit and Period fields. |
| TR-04 | The table grain shall align to the lowest granularity approved for the Power BI report, such as site × week or legal entity × month.                                             |
| TR-05 | Column names and data types shall conform to the schema approved by the BI team in the Data Specification.                                                                       |
| TR-06 | Each Gold Layer row shall contain source_table, ingestion_timestamp and transformation_version metadata.                                                                         |
| TR-07 | Each Gold Layer table and field shall be documented with its business definition, unit of measure, grain, source and refresh cadence.                                            |

The Operational Driver Analysis and Root Cause & Mitigation tables shall be derived from the validated VDT table and shall retain references to the contributing VDT records and refresh version.

## 4.10 AI agent requirements

### 4.10.1 Specialist AI agent

| ID    | Requirement                                                                                                                                                                                                                                                                                                                                                                     |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TR-08 | The transformation scripting agent shall be constrained to the approved data schema and VDT rules; shall use a fixed, versioned prompt and knowledge base; shall follow the Azure Databricks environment and naming conventions; and shall produce version-controlled, reviewable outputs within a business-approved scope. The supporting rationale is set out in section 5.4. |

### 4.10.2 Agent access, knowledge and containment

The following controls are ordered from data-access scoping, through knowledge sourcing and version control, to external-retrieval containment.

| ID    | Requirement                                                                                                                                                                                                                                         |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TR-09 | The transformation scripting agent shall have read access only to the approved Silver Layer objects and write access only to the designated Gold Layer catalog or schema.                                                                           |
| TR-10 | The Root Cause & Mitigation agent shall retrieve internal domain context only from an approved, access-controlled knowledge base containing governed sources such as operational procedures, prior incident reports and business-context documents. |
| TR-11 | The transformation script, VDT specification, semantic annotations, agent prompts and generated outputs shall be version-controlled and subject to the approved change-management process.                                                          |
| TR-12 | External internet retrieval shall remain disabled unless data governance and information security approve its sources, data-handling controls, access method and output-review process.                                                             |

## 4.11 Power BI semantic model and integration

The requirements below follow the build order of the semantic model: connect, model, tune, secure, then govern any AI capability layered on top.

| ID    | Requirement                                                                                                                                                                             |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TR-13 | Power BI shall connect only to the approved Gold Layer tables using the Import, DirectQuery or other connection mode selected and documented during detailed design.                    |
| TR-14 | Measures, calculated fields, hierarchies and filters shall implement the approved VDT definitions and preserve parent-child navigation.                                                 |
| TR-15 | Refresh configuration and performance optimisation shall meet the service levels agreed for data currency, report load time and the expected concurrent user population.                |
| TR-16 | Access shall use approved role-based security, including row-level security wherever users must be restricted by business unit, legal entity or another governed dimension.             |
| TR-17 | Any AI capability enabled on the Power BI semantic model or report shall use only approved model objects and shall comply with the same access controls applied to the underlying data. |

## 4.12 Responsibility summary

The table below summarises ownership across each activity in the VDT pipeline, distinguishing human-led from AI-agent activity and identifying the medallion layer and frequency for each.

|                                                                       |                              |               |                                                               |
| --------------------------------------------------------------------- | ---------------------------- | ------------- | ------------------------------------------------------------- |
| **Activity**                                                          | **Owner**                    | **Layer**     | **Frequency**                                                 |
| Design VDT logic and KPI definitions                                  | Human                        | N/A           | One-time / as needed                                          |
| Identify source data tables                                           | Human                        | Bronze        | One-time per source                                           |
| Set up ingestion pipeline & schedule                                  | Human                        | Bronze        | One-time per source                                           |
| Annotate tables with semantic context                                 | Human                        | Silver        | One-time / as needed                                          |
| Design Gold Layer table schema                                        | Human                        | Gold          | One-time / as needed                                          |
| Generate VDT dataset build transformation script (PySpark/SQL)        | AI Agent                     | Silver → Gold | On VDT change only (new element, rule edit, or schema update) |
| Review & approve transformation script                                | Human                        | Silver → Gold | Per change request                                            |
| Schedule Gold Layer data refresh                                      | Human                        | Gold          | One-time / as needed                                          |
| Consume Gold Layer in Power BI                                        | Power BI / Human             | Gold          | Per report refresh                                            |
| Analyse top N operational drivers (variance attribution)              | AI Agent                     | Gold → Gold   | On Gold Layer refresh                                         |
| Review and validate operational driver analysis output                | Human (Finance)              | Gold          | Per refresh cycle                                             |
| Propose root causes and mitigation actions                            | AI Agent                     | Gold → Gold   | On driver analysis completion                                 |
| Review and refine root cause & mitigation proposals                   | Human (Finance / Operations) | Gold          | Per analysis cycle                                            |
| Facilitate Finance–Operations discussion and prioritise needle-movers | Human (Finance / Operations) | N/A           | Per analysis cycle                                            |

## 4.13 Technical exclusions

The following are explicitly out of scope for this release, with the rationale or governing condition for each.

| Ref   | Exclusion                                                                       | Description, rationale or governing condition                                                                                                                                                      |
| ----- | ------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TX-01 | Continuous AI agent involvement in routine data refreshes                       | AI consumption is bounded to discrete VDT change events; routine scheduled refreshes run the human-approved script without agent involvement (see DP-07).                                          |
| TX-02 | Internet search augmentation of the Root Cause & Mitigation agent               | Not permitted unless and until the data governance and information security approval conditions in TR-12 are satisfied.                                                                            |
| TX-03 | On-the-fly querying of the Silver Layer and ad-hoc conversational interrogation | A conversational interface for ad-hoc or transactional interrogation is not part of the scheduled Power BI solution.                                                                               |
| TR-25 | Transactional web application (deferred)                                        | A web application with a conversational AI agent for transactional line-item interrogation, supported by a separately governed detailed-data model and interface, is deferred to a future release. |
| TX-04 | Transaction-level records and line-item drill-through in Power BI               | The Gold Layer holds aggregated driver values only; transaction-level detail is not exposed in the dashboard.                                                                                      |
| TX-05 | Source-system and infrastructure procurement                                    | Replacement or upgrade of source systems and underlying ICT infrastructure procurement remains outside this release.                                                                               |

# 5 Appendices

## 5.1 Open Items and Decisions Register

The following points are unresolved at the time of writing. Each must be closed before the design it affects is frozen. The register is maintained through the project change control process.

|         |                                                                                                                                                                                                                                                                    |                              |                                          |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------- | ---------------------------------------- |
| **Ref** | **Open item**                                                                                                                                                                                                                                                      | **Owner**                    | **Required by**                          |
| OI-01   | Estimated user counts per role (section 2.6) are marked [TBC] and must be confirmed with each business unit, as they drive Power BI licensing and capacity sizing.                                                                                                 | BU Finance / DGA             | Before platform capacity sizing          |
| OI-02   | Source system and field names for the five operational driver groups — fuel and bunker consumption, voyage and route data, maintenance and dry-docking, crew cost and manning, and charter and contract data (section 3.7) — must be confirmed with BU Operations. | BU Operations / EDH          | Before Bronze Layer ingestion setup      |
| OI-03   | Final Gold Layer structure, grain and schema (section 4.9) are illustrative and must be agreed with the BI team.                                                                                                                                                   | DGA / BI team                | Before transformation scripting begins   |
| OI-04   | Choice between pre-calculated, surrogate-keyed and on-the-fly aggregation strategies (section 4.8.1) is to be assessed during Gold Layer schema design.                                                                                                            | DGA / delivery team          | Gold Layer schema design phase           |
| OI-05   | Value of N for the top-N operational driver analysis (section 3.4.1) is configurable per financial metric and must be agreed during design.                                                                                                                        | BU Finance / DGA             | Before Operational Driver Analysis build |
| OI-06   | Internet search augmentation of the Root Cause & Mitigation agent (sections 4.10.2 and 4.13) requires a data governance and information security assessment before it can be enabled.                                                                              | Information Security / DGA   | Before any external retrieval is enabled |
| OI-07   | The list of key hypotheses and business questions (section 2.4) is preliminary and must be refined with management.                                                                                                                                                | CFO Group Finance / FLC      | Before dashboard design is frozen        |
| OI-08   | Availability of external peer benchmarks for the metrics identified as benchmarkable (section 2.9) must be confirmed or an alternative comparison basis agreed.                                                                                                    | Group Finance                | Before benchmarking views are built      |
| OI-09   | Manual download source and frequency for operational data not yet system-captured (section 4.6) must be confirmed with the relevant business unit.                                                                                                                 | BU Finance / EDH             | Before ingestion pipeline setup          |
| OI-10   | Named individuals for the BU Finance representative and BU Operations SME roles in the project team are to be nominated by each business unit.                                                                                                                     | BU CFOs                      | Before use-case squad mobilisation       |
| OI-11   | Process map diagram (section 2.5) and dashboard mock-up screenshots (section 5.3) to be inserted once available.                                                                                                                                                   | DGA / internal delivery team | Before document sign-off                 |

## 5.2 Supporting reference material

The following reference material supports the requirements set out above.

_Value Driver Tree concept — business outcomes linked to actionable input levers._

```
                              ┌─────────────────────────┐
                              │        CFROA             │
                              │  Cash Flow Return on     │
                              │        Assets            │
                              └────────────┬────────────┘
                                           │
          ┌────────────────────────────────┼────────────────────────────────┐
          │                                │                                │
          ▼                                ▼                                ▼
┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
│      NPAT       │              │    Net Assets    │              │      CFFO       │
│  (Profitability) │              │  (Asset Base)    │              │  (Cash Flow)    │
└────────┬────────┘              └────────┬────────┘              └────────┬────────┘
         │                                │                                │
    ┌────┴────┐                      ┌────┴────┐                      ┌────┴────┐
    │         │                      │         │                      │         │
    ▼         ▼                      ▼         ▼                      ▼         ▼
┌───────┐ ┌───────┐            ┌─────────┐ ┌─────────┐          ┌───────┐ ┌───────┐
│Revenue│ │Expenses│            │  Fixed  │ │ Working │          │Operating│ │Investing│
│       │ │       │            │ Assets  │ │ Capital │          │  Cash   │ │  Cash   │
└───┬───┘ └───┬───┘            └────┬────┘ └────┬────┘          └───┬───┘ └───┬───┘
    │         │                     │           │                   │         │
    ▼         ▼                     ▼           ▼                   ▼         ▼
┌───────┐ ┌───────┐            ┌─────────┐ ┌─────────┐          ┌───────┐ ┌───────┐
│ Volume │ │  Unit  │            │  Vessel  │ │Receivables│          │  Opex  │ │ Capex  │
│  ×     │ │ Costs  │            │  Fleet   │ │Payables  │          │  Cash  │ │  Cash  │
│ Rate   │ │        │            │          │ │Inventory │          │  Flow  │ │  Flow  │
└───┬───┘ └───┬───┘            └────┬────┘ └────┬────┘          └───┬───┘ └───┬───┘
    │         │                     │           │                   │         │
    ▼         ▼                     ▼           ▼                   ▼         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         OPERATIONAL INPUT LEVERS                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │  Voyage  │ │  Bunker  │ │  Crew &  │ │  Repair  │ │  Asset   │ │ Charter  │ │
│  │  & Route │ │   Fuel   │ │ Manning  │ │   & M&R  │ │Uptime/Day│ │  Rates   │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘

  Figure — Illustrative Value Driver Tree: financial outcomes decomposed into
  operational input levers. Each node carries an explicit parent–child relationship
  and a defined calculation logic. The AI agent operates within this known structure.
```

> **Reference:** The Value Driver Tree (VDT) is a well-established management accounting and performance management technique. Also referred to as a value driver map, KPI tree, or driver-based model, it decomposes a high-level financial outcome (such as CFROA, NPAT, or CFFO) into its constituent operational drivers in a hierarchical tree structure, with explicit parent–child relationships and calculation logic at each node. The technique is widely documented in practitioner literature on driver-based planning and rolling forecasts, and is a standard element of the Chartered Institute of Management Accountants (CIMA) Strategic Scorecard and the broader value-based management discipline. For a representative treatment, see: CIMA, _Value Driver Trees: A Practical Guide to Building and Using Driver-Based Models_ (CIMA, 2018); and Morin, J. &amp; Jarrell, S., _Driving Shareholder Value: Value-Building Techniques for Creating Shareholder Wealth_ (McGraw-Hill, 2001), Chapter 5, "Value Driver Analysis." _(References not verified in this session — please confirm exact titles, editions and stable URLs if formal citations are required.)_

## 5.3 Report layout

[Insert Zeteo dashboard mock-up / demo screenshots — refer to the Demo and Mock dashboard slides in the Data Driven & Digital 2025 pack]

## 5.4 Rationale — specialist AI agent

Section 4.10.1 requires a specialist agent rather than a general-purpose model. The reasons are:

- VDT domain knowledge — a generic model has no awareness of the organisation’s VDT structure, KPI definitions, driver hierarchies or the semantic meaning of source tables, and cannot reliably map operational data to the correct financial metrics.
- Consistency and repeatability — generic models produce variable outputs across sessions. A specialist agent built around a fixed, versioned prompt and knowledge base ensures the same VDT specification always produces the same transformation logic, which is a prerequisite for auditable financial reporting.
- Reduced hallucination risk — a specialist agent constrained to the known data schema and VDT rules narrows the space in which errors can occur.
- Environment integration — a specialist agent understands the Azure Databricks environment, naming conventions and PySpark/SQL patterns, reducing the need for human correction of environment-specific code.
- Governed and auditable — the agent operates within a business-approved scope, and its inputs (VDT specification, semantic context) and outputs (transformation script) are version-controlled and reviewable.

## 5.5 Sustaining value — supporting rationale

This section provides the supporting rationale for Section 2.3.3 (Sustaining value) and the requirements BR-12 and BR-13. It addresses two themes: the decay of realised value when initiatives and their metrics are no longer monitored, and the widely quoted management adage on measurement.

### 5.5.1 Value decay when initiatives and metrics go unmonitored

Value creation is not a one-off event that is secured the moment an initiative closes. The benefit realised from a change tends to erode over time unless the drivers behind it are actively tracked and reinforced. This erosion is commonly described as "value decay" or "benefits leakage", and it is a recognised phenomenon in benefits realisation management and continuous-improvement practice:

- Benefits are realised gradually and can be lost gradually. Formal benefits-realisation frameworks treat benefit delivery as a lifecycle that continues well beyond project closure, with explicit "sustainment" or "hold-the-gains" stages precisely because realised benefits regress toward the old baseline once attention is withdrawn.
- Behaviour and process gains regress without reinforcement. Lean and Six Sigma practice formalises this in the "Control" phase of DMAIC (Define, Measure, Analyse, Improve, Control), whose entire purpose is to install monitoring, ownership and response mechanisms so that improvements are held rather than allowed to slip back.
- Not all value is traceable to a single initiative. Some value arises from addressing pain points rather than from a discrete diagnostic finding, which makes initiative-by-initiative attribution incomplete. Continuous monitoring of the underlying drivers — rather than of the initiative alone — is therefore required to detect and prevent decay.

The practical implication for Zeteo is that the drivers behind each initiative must be ingested into the Enterprise Data Hub (EDH) and monitored under a persistent "feed" with a named owner and a recurring cadence (BR-12, BR-13), so that realised value is sustained rather than allowed to decay.

References:

1. Project Management Institute (PMI), _Benefits Realization Management: A Practice Guide_ — lifecycle view of benefits identification, execution and sustainment. https://www.pmi.org/ _(reference not verified in this session — please confirm the exact title/edition and a stable URL if a citation is required)_
2. American Society for Quality (ASQ), "The Define, Measure, Analyze, Improve, Control (DMAIC) Process" — the Control phase and sustaining improvements. https://asq.org/quality-resources/dmaic _(reference not verified in this session — please confirm)_

### 5.5.2 On the measurement adage

The saying "you can't manage what you can't measure" (and its close variant "what gets measured gets managed") is frequently invoked to justify measurement and monitoring, and is commonly attributed to Peter Drucker. This attribution is disputed:

- No reliable primary source attributes "you can't manage what you can't measure" to Peter Drucker; the attribution appears to be apocryphal.
- W. Edwards Deming — the statistician and quality-management thinker (1900–1993) — is often cited in this context, but his actual position was a caution against over-reliance on visible figures, not an endorsement of "measure everything". Deming's "Seven Deadly Diseases of Management" explicitly include "running a company on visible figures alone", and he held that "the most important figures that one needs for management are unknown or unknowable".

For the purposes of this document, the argument for continuous monitoring rests on the value-decay evidence in A.1 rather than on the disputed adage. Where a measurement principle is cited, Deming's genuine caution — that value which is not continuously watched can erode, while some of the most important figures remain unmeasured — is the more defensible reference.

References:

3. W. Edwards Deming — biography, "Seven Deadly Diseases of Management", and the "unknown or unknowable figures" point. https://en.wikipedia.org/wiki/W._Edwards_Deming _(verified in this session)_
4. Discussion of the misattribution of "you can't manage what you can't measure" to Drucker. _(reference not verified — the source consulted could not be scraped in this session; please confirm a stable citation, e.g. a Quote Investigator entry, if a formal citation is required)_

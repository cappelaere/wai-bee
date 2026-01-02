# Scholarship Evaluation System — End-to-End Process

## Purpose

This document defines the **authoritative, repeatable process** for designing, validating, generating, and operating an AI-assisted scholarship evaluation system.

The system is:

* Schema-driven
* Auditable
* Deterministic
* Suitable for high-stakes decision support

All evaluation logic originates from a **single human-authored configuration file per scholarship**.

---

## Repository Structure (Authoritative)

```text
repo-root/
├── schemas/
│   └── config.schema.json        # Shared configuration schema (authoritative)
├── scripts/
│   ├── validate_config.py        # Validate scholarship configuration
│   ├── generate_artifacts.py     # Generate machine-consumable artifacts
│   └── generate_documents.py     # Generate human-readable documents
├── cross_field_rules.py          # Cross-field governance rules
├── SCHOLARSHIP_PROCESS.md        # This document
└── data/
    ├── WAI-Harvard-June-2026/
    │   └── config.yml            # Scholarship-specific single source of truth
    ├── Another-Scholarship/
    │   └── config.yml
```

### Rules

* Each scholarship owns **exactly one** `config.yml`
* All schemas are **centralized** under `/schemas`
* Generated artifacts and documents must **never** be edited manually
* All changes originate in `config.yml`

---

## Phase 0 — Inputs & Preconditions

Before creating or modifying a scholarship configuration, gather:

* Official scholarship description
* Eligibility requirements
* Required application artifacts
* Essay prompt(s)
* Governance and fairness constraints

No scripts are run in this phase.

---

## Phase 1 — Scholarship Configuration (Human-Authored)

### Step 1.1 — Create Scholarship Folder

Create a new folder under `/data`:

```text
data/<scholarship-id>/
```

Add a single file:

```text
config.yml
```

This file is the **only human-edited policy artifact**.

---

### Step 1.2 — Define Scholarship Intent

In `config.yml`, define:

* Purpose and goals
* Target audience
* Definition of excellence
* Program metadata

This captures **why the scholarship exists**.

---

### Step 1.3 — Define Eligibility & Submission Rules

Specify:

* Membership requirements
* Experience requirements
* Attendance commitment
* Required artifacts and limits (pages, word counts, restrictions)

These are **hard constraints**, not scoring criteria.

---

### Step 1.4 — Define Evaluation Artifacts & Facets

For each artifact (Application, Resume, Essay, Recommendation):

* Enable or disable evaluation
* Define **1–3 facets only**
* Each facet must include:

  * Name
  * Description
  * Expected evidence

Facets must be explicit, non-overlapping, and defensible.

---

### Step 1.5 — Define Scoring & Aggregation

Specify:

* Scoring scale and semantics
* Handling of missing evidence
* Aggregation weights

Weights must sum to **1.0**.

---

## Phase 2 — Configuration Validation (Mandatory)

Before **any generation**, validate the configuration.

### Validation Command

```bash
python scripts/validate_config.py data/<scholarship-id>
```

### Validation Layers

1. **Schema validation**

   * Uses `./schemas/config.schema.json`
   * Enforces structure, required fields, and facet limits

2. **Cross-field governance validation**

   * Aggregation weights sum to 1.0
   * Weights reference only enabled artifacts
   * Submission requirements align with enabled artifacts
   * Locked configurations are immutable

If validation fails, **no generation is permitted**.

---

## Phase 3 — Artifact Generation (Machine-Consumable)

Once validation succeeds, generate all machine-consumable artifacts.

### Artifact Generation Command

```bash
python scripts/generate_artifacts.py data/<scholarship-id>
```

### Generated Outputs

* `scholarship.json` (locked criteria contract)
* Output schemas (per artifact)
* Analysis prompts
* Repair prompts
* `agents.json`

These artifacts are deterministic and must not be edited manually.

---

## Phase 4 — Document Generation (Human-Readable)

After artifacts are generated, produce documentation for non-technical stakeholders.

### Document Generation Command

```bash
python scripts/generate_documents.py data/<scholarship-id>/
```

### What This Produces

```
data/<scholarship-id>/SCHOLARSHIP_OVERVIEW.md
```

This document:

* Is derived entirely from `config.yml`
* Contains no YAML, schemas, or AI prompts
* Is suitable for scholarship managers, review boards, legal, and sponsors
* May be regenerated at any time

Manual edits to generated documents are **not permitted**.

---

## Phase 5 — Runtime Evaluation Model

For each applicant:

1. Extract text per artifact
2. Run artifact-specific analysis prompts
3. Validate outputs against schemas
4. Repair outputs if needed
5. Aggregate scores using weights
6. Present ranked results for human review

Raw documents are not reprocessed after analysis.

---

## Governance Guarantees

This process guarantees:

* 🔒 Immutable evaluation criteria
* ⚖ Fair, facet-based scoring
* 📜 Full auditability
* 🧠 Model independence
* 🔁 Repeatability across cycles

---

## Change Policy

* Any change to criteria requires a **new scholarship folder**
* Locked configurations are never modified
* Historical evaluations remain reproducible

---

## End of Process

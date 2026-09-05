# TEST_INFRA — Marine Cargo Survey & QC Report Generation Platform

## 1. Test Architecture & Overview

The Marine Cargo Survey & QC Report Generation Platform test infrastructure is an **opaque-box, requirement-driven, progressive testing architecture** designed for high-stakes marine insurance and cargo surveying. In this domain, reports are legally binding documents submitted to insurers, port authorities, and courts. A single calculation drift, altered photo timestamp, or corrupted page counter can compromise a surveyor's professional standing and IRDAI licence.

### Core Testing Pillars

```
+---------------------------------------------------------------------------------------------------+
|                                  4-TIER TEST ARCHITECTURE                                         |
+---------------------------------------------------------------------------------------------------+
|  Tier 4: Real-World Scenarios (End-to-End Survey & QC Workflows)                                  |
|  - Mandarin 16 Boxes QC | Grapes =SUM() Import | Sea Multi-Unit (6 Ctrs) | Air Mod-7 AWB | Photos  |
+---------------------------------------------------------------------------------------------------+
|  Tier 3: Cross-Feature Combinations (Pairwise & Data Pipeline Interactions)                        |
|  - Transport Mode x Carriage Units x Block Sequences x Word Render x Traceability Gate            |
+---------------------------------------------------------------------------------------------------+
|  Tier 2: Boundary & Corner Cases (>=5 tests per feature R1-R7)                                    |
|  - Zero-division, check-digit validation, float detection, formula errors, untraced literals      |
+---------------------------------------------------------------------------------------------------+
|  Tier 1: Feature Coverage (>=5 tests per feature R1-R7)                                           |
|  - Scaffold & Auth | BlockState & Compute | DOCX Render | Spreadsheet Ingest | Photos | Miner    |
+---------------------------------------------------------------------------------------------------+
|  Progressive Testability & Isolation Layer (tests/e2e/helpers/ & conftest.py)                     |
|  - Live server / TestClient dual-mode, Contract Stubs, Synthetic Fixtures, Clean Environment     |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Progressive Testability Architecture

During phased implementation (Milestones M1 through M6), implementation components are delivered asynchronously. The test suite is designed with **Progressive Testability**:
1. **Zero Premature Failures**: Tests for unbuilt milestones check feature readiness via contract inspection or modular imports. If a milestone is pending, tests indicate `xfail(reason="Milestone M... pending implementation")` or dynamically exercise contract stubs rather than blowing up with unhandled `ModuleNotFoundError`.
2. **Instant Feedback on Delivery**: The moment an agent implements M1 (auth, reports sequence, DB schema), `pytest -m m1` or `pytest tests/e2e/tier1_feature_coverage/test_r1_scaffold_auth_db.py` executes synchronously against real endpoints.
3. **Dual Execution Mode**:
   - **In-Process / Direct Model Mode**: Direct invocation of Python domain services (`compute(state)`, `photo_ranges.py`, `spreadsheet.py`, `render_docx()`).
   - **HTTP Client Mode**: Exercising FastAPI endpoints (`/api/v1/auth`, `/api/v1/reports`, `/api/v1/assets`) via `httpx.AsyncClient` / `TestClient`.

---

## 3. Strict Compliance with CRITICAL-RULES

| Rule # | Critical Rule | Testing Verification Method |
|---|---|---|
| **CR-1** | Never store a computed value | Assert database schemas (`reports.block_state`) do not persist totals or ranges; assert `compute(block_state)` computes dynamically on read. |
| **CR-2** | `Decimal`, never `float` | AST and grep checks verifying zero `float(` calls in arithmetic modules; assert `Decimal` type across all sums and percentages. |
| **CR-2** | `ROUND_HALF_UP` 2 dp / 3 dp | Test exact replication of Mandarin (56.84%, 23.08%, 5.98%, 10.26%, 3.84%) and Grapes (6.230 kg, 50.702 kg, 93.81%, 4.46%, 1.73%). |
| **CR-2** | Never auto-correct data mismatch | Inject 3 kg discrepancy; assert system flags both sources rather than overwriting or forcing equality. |
| **CR-3** | Bit-exact photo original with SHA-256 | Upload test images, verify byte-for-byte SHA-256 equality before and after storage; verify derived display (800px) and report (1600px) copies are separate files. |
| **CR-3** | Photo series isolation | Test independent trays (`own_survey`, `consignees_cha`, `shippers_load_port`); assert numbering never crosses series. |
| **CR-4** | `PAGE x OF y` report body only | Verify Word footer contains native `PAGE` and `NUMPAGES` XML fields; verify annexures do not inflate body page count. |
| **CR-5** | Input Gate & Provenance | Verify every cell carries provenance tag (`surveyor_entered`, `csv_imported`, etc.); verify rejection of unverified inputs. |
| **CR-5** | Output Gate (Numeric Traceability) | Inject unrecorded numeric literal into DOCX; verify Gate fails with HTTP 422 and prevents download. |
| **CR-7** | Local & Offline Only | Verify zero calls to external APIs; assert no usage of AGPL `fitz` or Windows `docx2pdf`. |
| **CR-8** | Zero Client PII / Synthetic Data | All test fixtures use synthetic company names, fake vessel names, and dummy licence numbers (`IRDA/IND/SLA-XXXXXX`). Pre-commit scanner regex tested. |

---

## 4. Feature Inventory & Mapping (Week 1 / R1 - R7)

| Req | Feature Description | Tier 1 (Happy Path) | Tier 2 (Boundary/Edge) | Tier 3 (Cross-Feature) | Tier 4 (Scenario) |
|---|---|---|---|---|---|
| **R1** | Scaffold, DB (5 tables), Auth, Concurrency-Safe Report Numbers | `test_r1_scaffold_auth_db.py` (5 tests) | `test_r1_boundaries.py` (5 tests) | `test_pairwise_transport_blocks.py` | `test_scenario_sea_multi_unit.py` |
| **R2** | BlockState Pydantic models, `compute()` engine, Decimal arithmetic, LRM | `test_r2_blockstate_compute.py` (5 tests) | `test_r2_boundaries.py` (5 tests) | `test_data_pipeline_flow.py` | `test_scenario_mandarin_qc.py`, `test_scenario_grapes_formulas.py` |
| **R3** | Word document generation, template injection, 2-col photo plate, Numeric Gate | `test_r3_word_generation.py` (5 tests) | `test_r3_boundaries.py` (5 tests) | `test_data_pipeline_flow.py` | `test_scenario_photo_tray_renumber.py` |
| **R4** | Excel/CSV ingestion, `=SUM()` formula evaluation, column mapping | `test_r4_excel_csv_import.py` (5 tests) | `test_r4_boundaries.py` (5 tests) | `test_data_pipeline_flow.py` | `test_scenario_grapes_formulas.py` |
| **R5** | Photo bit-exact SHA-256, derived copies, EXIF, `photo_ranges.py` | `test_r5_photo_management.py` (5 tests) | `test_r5_boundaries.py` (5 tests) | `test_photo_lifecycle_flow.py` | `test_scenario_photo_tray_renumber.py` |
| **R6** | Corpus mining script (`mine_corpus.py`), 5 CSVs, deduplication | `test_r6_corpus_mining.py` (5 tests) | `test_r6_boundaries.py` (5 tests) | N/A (Standalone Tool) | Standalone corpus mining suite |
| **R7** | End-to-end form lifecycle, SEA/AIR transport mode, download | `test_r7_form_e2e_flow.py` (5 tests) | `test_r7_boundaries.py` (5 tests) | `test_pairwise_transport_blocks.py` | `test_scenario_air_mod7_awb.py` |

---

## 5. Test Tier Specifications

### Tier 1: Feature Coverage (>=5 tests per feature)
- Happy paths, basic valid inputs, standard response schemas.
- Minimum 35 discrete test cases across R1 through R7.
- Verifies nominal functionality: health endpoints return 200, compute returns correct row sums, photos upload and yield SHA-256 hashes, templates inject valid XML.

### Tier 2: Boundary & Corner Cases (>=5 tests per feature)
- Empty lists, zero rows, boundary limits (e.g., single photo, zero defect count).
- Zero division protection when grand total is 0.
- Check digit integrity: ISO 6346 (containers) and IATA Mod-7 (Air Waybills).
- Precision & rounding drift: Hare-Niemeyer largest remainder balancing to 100.00%.
- Adversarial gate test: Injecting untraced numbers (e.g. `999.99`) into DOCX and verifying download blockage.
- Minimum 35 discrete test cases across R1 through R7.

### Tier 3: Cross-Feature Combinations (Pairwise Coverage)
- Integration between transport modes (SEA vs AIR), block sequences, photo ranges, and Word generation.
- Validates the complete pipeline: Spreadsheet Ingest -> Table Block -> `compute()` -> Word Template Injection -> Numeric Traceability Gate.
- Photo Lifecycle: Upload -> Derived Copy Generation -> Divider Grouping -> Text Range Formatting -> 2-Column Word Plate Generation.
- Minimum 15 discrete test cases.

### Tier 4: Real-World Application Scenarios (>=5 Workflows)
1. **Mandarin QC 16 Boxes Survey**: Ingest real-world defect counts, calculate exact row totals (234), column totals (675), exact percentages, and verify formatting.
2. **Grapes Summary with Live `=SUM()` Formulas**: Ingest Excel sheet with active formula cells, extract values (not formula strings), calculate 3 decimal place kg weights (6.230 kg, 50.702 kg), apply Hare-Niemeyer LRM balancing.
3. **Sea Container Multi-Unit Survey (6 Units)**: Multi-container shipment, validate 6 ISO 6346 container numbers, execute CFS weighbridge reconciliation formula `gross - container_tare`, preserve surveyor-accepted 3 kg discrepancy.
4. **Air Cargo Shipment with Mod-7 AWB**: Validate 3-digit airline prefix + 7-digit serial + mod-7 check digit (`098-1234567-5`), calculate volumetric weight at IATA divisor 6,000 cm³/kg, determine chargeable weight, verify Montreal Convention notice period clause.
5. **Photo Tray Renumbering & Word Plate Generation**: Upload 12 photos, partition into 3 groups, assert range strings `(Photo Nos. 1 to 4)`, `(Photo Nos. 5 & 6)`, `(Photo Nos. 7 to 12)`. Delete photo #3, verify automatic re-derivation without gap or re-numbering drift, generate 2-column Word table with `cantSplit`.

---

## 6. Directory Layout

```
tests/
├── conftest.py
├── e2e/
│   ├── __init__.py
│   ├── conftest.py
│   ├── helpers/
│   │   ├── __init__.py
│   │   ├── api_client.py            # Progressive HTTP client (live API or test app)
│   │   ├── contract_stubs.py        # Contract validators and synthetic payloads
│   │   ├── synthetic_data.py        # Compliant test data (zero client PII, real arithmetic)
│   │   └── docx_inspector.py        # Inspects docx XML, tables, footers, charts
│   ├── tier1_feature_coverage/
│   │   ├── __init__.py
│   │   ├── test_r1_scaffold_auth_db.py
│   │   ├── test_r2_blockstate_compute.py
│   │   ├── test_r3_word_generation.py
│   │   ├── test_r4_excel_csv_import.py
│   │   ├── test_r5_photo_management.py
│   │   ├── test_r6_corpus_mining.py
│   │   └── test_r7_form_e2e_flow.py
│   ├── tier2_boundary_corner/
│   │   ├── __init__.py
│   │   ├── test_r1_boundaries.py
│   │   ├── test_r2_boundaries.py
│   │   ├── test_r3_boundaries.py
│   │   ├── test_r4_boundaries.py
│   │   ├── test_r5_boundaries.py
│   │   ├── test_r6_boundaries.py
│   │   └── test_r7_boundaries.py
│   ├── tier3_cross_feature/
│   │   ├── __init__.py
│   │   ├── test_pairwise_transport_blocks.py
│   │   ├── test_data_pipeline_flow.py
│   │   └── test_photo_lifecycle_flow.py
│   └── tier4_real_world_scenarios/
│       ├── __init__.py
│       ├── test_scenario_mandarin_qc.py
│       ├── test_scenario_grapes_formulas.py
│       ├── test_scenario_sea_multi_unit.py
│       ├── test_scenario_air_mod7_awb.py
│       └── test_scenario_photo_tray_renumber.py
```

---

## 7. Execution & Runner Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all E2E tests
pytest tests/e2e/ -v

# Run by Tier
pytest tests/e2e/tier1_feature_coverage/ -v
pytest tests/e2e/tier2_boundary_corner/ -v
pytest tests/e2e/tier3_cross_feature/ -v
pytest tests/e2e/tier4_real_world_scenarios/ -v

# Run by Milestone Tag
pytest -m m1 -v
pytest -m m2 -v
pytest -m m3 -v
```

---

## 8. Coverage & Pass Thresholds

- **Total Test Count**: >= 95 tests across Tiers 1-4.
- **Pass Threshold**: 100% pass on all implemented milestones; 0 unexpected errors.
- **Flakiness Threshold**: 0% flakiness (isolated fixtures, deterministic Decimal calculations).

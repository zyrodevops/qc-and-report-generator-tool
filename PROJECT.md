# Project: Marine Cargo Survey & QC Report Generation Platform (Week 2)

## Architecture
- **Backend**: FastAPI (Python 3.12+), SQLAlchemy 2.0 async, PostgreSQL 16, Redis 7, python-docx, LibreOffice 26.8.0.3 headless, pdfplumber.
- **Frontend**: React 19, TypeScript, Vite 8, Tailwind CSS v4, TipTap rich text, Lucide icons.
- **Data Flow**:
  - `block_state` is the single source of truth for all report content.
  - Never persist computed values. Both HTML preview and DOCX generation call the exact same pure function `compute(block_state)` in `backend/app/compute/arithmetic.py` and `backend/app/compute/photo_ranges.py`.
  - Calculations strictly use `Decimal` with `ROUND_HALF_UP` (2 dp for pcs/pct, 3 dp for kg) and Hare-Niemeyer Largest Remainder balancing for 100.00% defect totals.
  - Document conversion from `.docx` to `.pdf` via headless LibreOffice at `/usr/local/bin/libreoffice`.
  - Numeric Traceability Gate in `backend/app/render/gate.py` intercepts downloads, parses document text, and verifies every numeric token against authorized `block_state` + `compute()` values, blocking unverified files with HTTP 422.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Pure compute(block_state) shared engine | Single source of calculation truth using Decimal and Hare-Niemeyer balancing | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Backend HTML Preview Endpoint | GET /api/reports/{id}/preview/html returning A4 formatted HTML matching DOCX | M1 | ORIGINAL_REQUEST §R1 |
| 3 | Report Details Endpoint | GET /api/reports/{id} returning report metadata, version, and block_state | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Modular A4 HTML Preview UI | A4-dimensioned page containers (210mm x 297mm) with realistic pagination | M1 | ORIGINAL_REQUEST §R1 |
| 5 | Block Component Renderers | Render Particulars, Narrative, Measurements, Table, Photo Plate, Fixed Text | M1 | ORIGINAL_REQUEST §R1 |
| 6 | Zero-Drift Verification | Automated test asserting HTML preview values match DOCX values bit-for-bit | M1 | ORIGINAL_REQUEST §R1 |
| 7 | TipTap Rich Text Editor | Paragraph narrative editor restricted strictly to bold, italic, and bullet lists | M2 | ORIGINAL_REQUEST §R2 |
| 8 | Narrative Audit Logging | Flag edited narrative blocks as surveyor_edited and record audit logs | M2 | ORIGINAL_REQUEST §R2 |
| 9 | Live Keystroke Table Recompute | Editable table category cells; locked computed totals recomputed on keystroke | M2 | ORIGINAL_REQUEST §R2 |
| 10 | Client-Side Hare-Niemeyer | TypeScript implementation of Hare-Niemeyer balancing matching backend | M2 | ORIGINAL_REQUEST §R2 |
| 11 | Dynamic Photo Tray Reordering | HTML5 drag-and-drop photos across observation groups with instant re-indexing | M2 | ORIGINAL_REQUEST §R2 |
| 12 | Dynamic Photo Bracketed Ranges | Live update of (Photo No. X) and (Photo Nos. X to Y) narrative references | M2 | ORIGINAL_REQUEST §R2 |
| 13 | Report Versioning Schema | Add version column to reports table via Alembic migration | M2 | ORIGINAL_REQUEST §R2 |
| 14 | Optimistic Concurrency Check | PATCH /api/reports/{id}/block-state returns HTTP 409 Conflict on stale version | M2 | ORIGINAL_REQUEST §R2 |
| 15 | Client Concurrency Conflict UI | UI alert/modal prompting surveyor when 409 Conflict occurs | M2 | ORIGINAL_REQUEST §R2 |
| 16 | LibreOffice Headless PDF Converter | Convert .docx to .pdf via /usr/local/bin/libreoffice in temp directory | M3 | ORIGINAL_REQUEST §R3 |
| 17 | Backend PDF Preview Endpoint | GET /api/reports/{id}/preview/pdf serving generated PDF for browser display | M3 | ORIGINAL_REQUEST §R3 |
| 18 | Dual View Toggle UI | UI toggle between "Edit View" and "Proof View" with embedded PDF display | M3 | ORIGINAL_REQUEST §R3 |
| 19 | Dual Download Endpoints | GET /api/reports/{id}/download/docx and GET /api/reports/{id}/download/pdf | M3 | ORIGINAL_REQUEST §R3 |
| 20 | Dual Download UI Actions | Download DOCX and Download PDF buttons in report editor header | M3 | ORIGINAL_REQUEST §R3 |
| 21 | Numeric Traceability Gate Module | backend/app/render/gate.py verify_numeric_traceability(docx/pdf, block_state) | M4 | ORIGINAL_REQUEST §R4 |
| 22 | OpenXML & PDF Token Extraction | Extract all numbers, currencies, container IDs, and dates from rendered doc | M4 | ORIGINAL_REQUEST §R4 |
| 23 | Authorized Value Pool Resolver | Aggregate all raw inputs, computed values, metadata, and boilerplate tokens | M4 | ORIGINAL_REQUEST §R4 |
| 24 | Traceability Enforcement on Download | Intercept download endpoints; abort with HTTP 422 structured diff on untraced | M4 | ORIGINAL_REQUEST §R4 |
| 25 | Traceability Gate UI Alert | UI displays alert showing untraced values when 422 is returned | M4 | ORIGINAL_REQUEST §R4 |
| 26 | Adversary Traceability Test | Automated test injecting rogue literal (99999) asserting HTTP 422 download block | M4 | ORIGINAL_REQUEST §R4 |
| 27 | Zero False Positive Gate Test | Verified normal reports pass the gate cleanly without blocking | M4 | ORIGINAL_REQUEST §R4 |
| 28 | Temperature Logger Parser | Parse plain-text / PDF DeltaTrak and Escavox records without spike heuristics | M5 | ORIGINAL_REQUEST §R5 |
| 29 | Handwritten Tally Fallback UI | Side-by-side cropped scan preview with verification transcription grid | M5 | ORIGINAL_REQUEST §R5 |
| 30 | Mandarin FBIU5499689 Benchmark | Calculation regression test against Saanvi Mandarin (234/675 pcs, 54.96% sound) | M5 | ORIGINAL_REQUEST §R5 |
| 31 | Orange MMAU1200498 Benchmark | Calculation regression test against RGS Orange (144/680 pcs, 55.59% sound) | M5 | ORIGINAL_REQUEST §R5 |
| 32 | Grapes OOLU6232443 Benchmark | Calculation regression test against Grapes OOLU (6.230/50.702 kg, 93.81% sound) | M5 | ORIGINAL_REQUEST §R5 |
| 33 | Complete E2E Test Suite (Tiers 1-4) | Comprehensive opaque-box E2E test suite passing 100% | Final | ORIGINAL_REQUEST §AC |
| 34 | Adversarial Coverage Hardening (Tier 5) | White-box stress testing and gap elimination | Final | ORIGINAL_REQUEST §AC |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Zero-Drift Compute & A4 HTML Preview | Shared pure compute(), GET /api/reports/{id}, GET /api/reports/{id}/preview/html, frontend A4 preview components, zero-drift test | none | PLANNED |
| M2 | In-Place Editing & Optimistic Concurrency | TipTap narrative editor (bold/italic/bullets), live table keystroke recompute, photo drag-and-drop renumbering, version column, PATCH 409 Conflict | M1 | PLANNED |
| M3 | Proof View & Dual Download | Headless LibreOffice PDF converter, GET /download/docx, GET /download/pdf, GET /preview/pdf, Edit/Proof toggle in UI | M1 | PLANNED |
| M4 | Numeric Traceability Gate & Adversary Test | backend/app/render/gate.py, token extraction, download gate interception (HTTP 422 diff), adversary test with injected 99999 | M1, M3 | PLANNED |
| M5 | Document Ingestion, Loggers & Benchmarks | DeltaTrak/Escavox parser without spike heuristics, handwritten tally fallback UI, 3 benchmark regression tests (Mandarin, Orange, Grapes) | M1 | PLANNED |
| Final | E2E Test Pass & Adversarial Hardening | 100% pass across all E2E test tiers (Tiers 1-4) followed by Tier 5 adversarial coverage hardening | M1, M2, M3, M4, M5 | PLANNED |

## Interface Contracts
### Client ↔ Server (Reports & Previews)
- `GET /api/reports/{id}`:
  - Response: `ReportResponse` with `id`, `report_number`, `version: int`, `block_state: dict`, `status`, `created_at`, `updated_at`.
- `GET /api/reports/{id}/preview/html`:
  - Response: `text/html; charset=utf-8` containing server-rendered A4 HTML pages with zero-drift compute.
- `GET /api/reports/{id}/preview/pdf`:
  - Response: `application/pdf` generated via headless LibreOffice for inline Proof View iframe.
- `GET /api/reports/{id}/download/docx`:
  - Passes through Numeric Traceability Gate. Returns `application/vnd.openxmlformats-officedocument.wordprocessingml.document`. On untraced token: HTTP 422 JSON `{ "detail": "Numeric Traceability Gate failed", "untraced_tokens": [...] }`.
- `GET /api/reports/{id}/download/pdf`:
  - Passes through Numeric Traceability Gate. Returns `application/pdf`. On untraced token: HTTP 422 JSON `{ "detail": "Numeric Traceability Gate failed", "untraced_tokens": [...] }`.
- `PATCH /api/reports/{id}/block-state`:
  - Request body: `{ "version": int, "block_state": dict }`.
  - Behavior: Verifies `version == current_db_version`. If mismatch: HTTP 409 Conflict `{ "detail": "Conflict: Report has been modified by another session", "current_version": int }`. If match: increments version, strips `_computed`, updates DB, logs audit record.

### Compute Engine Contract
- `compute(block_state: Dict[str, Any]) -> Dict[str, Any]`:
  - Pure function, never mutates `block_state`.
  - Calculates row totals, column totals, Hare-Niemeyer balanced percentages (exact 100.00%).
  - Quantizes to `Decimal("0.01")` (pcs/pct) or `Decimal("0.001")` (kg).
  - Populates photo bracketed strings: `(Photo No. X)`, `(Photo Nos. X & Y)`, `(Photo Nos. X to Y)`.
  - All outputs placed strictly in `block["_computed"]`.

### Numeric Traceability Gate Contract
- `verify_numeric_traceability(docx_bytes: bytes, block_state: dict) -> Tuple[bool, List[str]]`:
  - Returns `(True, [])` if all numeric tokens match authorized pool.
  - Returns `(False, [untraced_tokens])` if any literal cannot be traced.

## Code Layout
- `backend/app/compute/`: `arithmetic.py`, `photo_ranges.py` (Pure computation engines)
- `backend/app/render/`:
  - `docx/`: `engine.py`, `templates/` (Word generation)
  - `html/`: `engine.py`, `templates/` (A4 HTML preview generation)
  - `pdf/`: `converter.py` (Headless LibreOffice wrapper)
  - `gate.py`: (Numeric Traceability Gate)
- `backend/app/api/`:
  - `reports.py`: CRUD, GET /api/reports/{id}
  - `generate.py`: Previews, downloads, block-state PATCH with optimistic concurrency
- `backend/app/ingest/`:
  - `instruments.py`: Temperature logger parsers (DeltaTrak, Escavox)
- `backend/alembic/versions/`: Database migrations (version column)
- `frontend/src/`:
  - `components/preview/`: `ReportPreview.tsx`, `PageContainer.tsx`, `blocks/*`
  - `components/narrative/`: `TipTapEditor.tsx`
  - `components/tables/`: `TableGrid.tsx`, `hareNiemeyer.ts`
  - `components/photos/`: `PhotoTray.tsx`
  - `components/ingest/`: `TallySheetGrid.tsx`
  - `pages/`: `ReportForm.tsx` (Dual toggle, Proof View iframe)
- `tests/`:
  - `backend/tests/`: Unit & integration tests
  - `tests/e2e/`: E2E test suites (Tiers 1-5)

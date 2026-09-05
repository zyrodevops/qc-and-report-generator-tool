# Original User Request

## 2026-09-04T12:56:53Z

Build Week 1 of the Marine Cargo Survey & QC Report Generation Platform — a web app for an IRDAI-licensed marine cargo surveyor to fill a form and generate a correctly formatted Word report. The platform is built around a **Block State** engine where every derived value (totals, photo numbers, annexure IDs) is computed fresh from JSON at render time and never stored.

Working directory: /home/agrim/CODES/qc-and-report-generator-tool

---

## CRITICAL RULES (read before writing any code)

These rules override everything else:

1. **Never store a computed value.** Totals, percentages, photo ranges, annexure IDs, weight differences — all computed at render time from Block State, thrown away after. One function `compute(block_state)` is called by Word renderer, HTML preview, and PDF — same function, same numbers, always.
2. **`Decimal`, never `float`** — for any number touching money, weight, or a percentage that ends up in a report. Rounding: `ROUND_HALF_UP`, 2 decimal places.
3. **Never auto-correct a data mismatch.** Check-digit failure, weight discrepancy, tally that doesn't tie — flag and show both sources; let the surveyor decide.
4. **Never recompress or overwrite a photo original.** Store bit-exact with SHA-256. Derived display/report copies only.
5. **No fabricated content.** Every value in output must trace to a user-supplied or user-confirmed source — enforced by the numeric traceability gate.
6. **No paid APIs, no PyMuPDF (AGPL), no docx2pdf (needs COM/Windows).** Use pdfplumber + pypdf + LibreOffice headless.
7. **Client data rules from commit #1:** `.gitignore` the sample-data folder before the first commit. Test fixtures must be synthetic (fake names/numbers, real arithmetic). IRDAI licence number in env var config only, never in code or committed templates. Add a pre-commit hook scanning for the licence-number pattern (`IRDA/IND/SLA-\d+`) and known client names.

---

## Requirements

### R1. Project scaffold, auth, and database

Set up the repo with Docker Compose (FastAPI + PostgreSQL + Redis), CI running tests, and basic email+password auth with sessions. Create the five database tables exactly as specified:

- `reports` — id, report_number (M-<n>-<year>, sequential per year, safe under concurrent requests via DB sequence or unique constraint + retry), family, state, template_id, status, block_state JSONB, created_at, updated_at
- `assets` — id, report_id, kind, sha256, original_path, derived_paths, exif JSONB
- `audit` — id, report_id, at, actor, action, path, before, after (immutable — insert-only)
- `templates` — id, name, family, mode, block_sequence JSONB
- `clauses` — id, key, version, text_with_slots, conditions JSONB

`.gitignore` must exclude a `sample-data/` folder before any commit. A pre-commit hook must scan staged files for the pattern `IRDA/IND/SLA-\d+` and block the commit if found.

### R2. Block State model and arithmetic engine (`compute`)

Implement Pydantic models for the first five block types: `particulars`, `narrative`, `measurements`, `table`, `fixed_text`.

The single function `compute(block_state) -> block_state_with_derived` must:
- For `table` blocks: compute row totals, column totals, grand total, and percentages using `decimal.Decimal` with `ROUND_HALF_UP` at 2 decimal places. Columns and unit (pcs/kg/mt) are data, not code — the function must handle any number of columns.
- Return every derived value as part of the output object; none are stored to the database.

Tests must reproduce these exact figures from real client data (use synthetic names/identifiers, keep the arithmetic):
- Mandarin row: 133+54+14+24+9 = 234; pcts 56.84/23.08/5.98/10.26/3.84
- Mandarin column totals: 371+172+51+47+34 = 675; pcts 54.96/25.48/7.56/6.96/5.04
- Grapes (kg, 3 dp): 5.190+0.606+0.434 = 6.230; grand total 47.562+2.264+0.876 = 50.702; pcts 93.81/4.46/1.73

### R3. Word document generation from Block State

Build the DOCX renderer that injects computed Block State into a cleaned copy of a real client `.docx` template (letterhead, header/footer, `PAGE x OF y` fields, fonts, table borders, signature block intact — **do not rebuild the letterhead from scratch**).

One renderer per block type. Implement renderers for: `particulars`, `narrative`, `fixed_text`, `measurements`, `table`, `photo_plate`.

**The chart is the riskiest item:** python-docx cannot create charts. Attempt: open the `.docx` as a zip, locate `word/charts/chart1.xml` + its embedded `.xlsx`, rewrite the cached data values there (this keeps a live editable Word chart). If this takes more than one day of work, fall back to a rendered PNG image and document the decision clearly. Do not spend more than one day on the chart injection approach.

`PAGE x OF y` must count the report body only, not the merged file with annexures.

**Note:** If no real client `.docx` template file is available in the working directory, build a synthetic placeholder template that has the correct structural skeleton (header, footer with PAGE x OF y field, a 2-column table style, a chart placeholder, and a signature block) so that the renderer can be fully implemented and tested. Document in a `TEMPLATE-NOTES.md` that the real client template must be substituted before production use.

### R4. Excel/CSV import into table blocks

Build the spreadsheet import pipeline: upload `.csv` or `.xlsx`, parse with pandas + openpyxl, present a column-mapping screen (map sheet columns to block category keys once per template, saved on the template), import data into the `table` block's rows. Formula cells must be read as **values**, not re-evaluated. The mapping is saved per template so the surveyor only maps once.

### R5. Photo management

Build a photo upload and management endpoint. For each uploaded photo:
- Store the original byte-for-byte with SHA-256 recorded at upload
- Generate separate display (max 800px) and report-sized (max 1600px) derived copies using Pillow — derived copies only, never recompressing the original
- Retain full EXIF data (store raw EXIF as JSON on the asset row)
- **Never recompress or overwrite the original**

Photo series: a report can have multiple series (own survey / consignee's CHA / shipper's load port), each with a label and provenance. Series are never merged or renumbered across each other.

Implement `backend/app/compute/photo_ranges.py`: given an ordered list of groups, each with asset IDs, compute the photo-number string: single → `(Photo No. 50)`, pair → `(Photo Nos. 39 & 40)`, range → `(Photo Nos. 55 to 59)`. Re-derive on every read. Assert: every photo belongs to exactly one group, ranges are contiguous and exhaustive, no gaps.

Word renderer for `photo_plate`: 2-column table, image + caption per cell.

### R6. Corpus mining script (standalone — not part of the app)

Write a standalone Python script (`tools/mine_corpus.py`) that, given a directory of `.docx` and `.doc` client reports, produces:
1. `inventory.csv` — per file: report number (parsed from filename/content), type (QC/survey), commodity, container count (counted from headings), photo count, page count, date
2. `block_sequences.csv` — per report: detected heading sequence (the real template structure)
3. `sentence_frequency.csv` — every sentence with names/numbers/dates replaced by `{PLACEHOLDER}`, grouped and counted descending
4. `defect_categories.csv` — defect column headers found per commodity
5. `arithmetic_errors.csv` — every table where the script's recomputed total disagrees with the printed total

De-duplicate by content hash before counting. Handle both `.docx` (python-docx) and `.doc` (antiword via subprocess) formats. Extract text to a cache so the drive is only read once. Include 3 synthetic test `.docx` fixtures in `tools/test_fixtures/` so the script can be tested without the real archive.

### R7. End-to-end form and report generation

Build a minimal React + TypeScript + Vite + Tailwind UI with three screens:
1. **Report list** — create a new report (pick template, set transport mode SEA/AIR, set report number)
2. **Report form** — generated from the report's block list; each block type has its own form section. Include: particulars (key/value rows), narrative (free text + clause-library reference selector), measurements (repeating rows: subject, min, max, unit), table (inline grid with import button), fixed_text (read-only display), photo upload + grouping tray (drag dividers to split series into observation groups)
3. **Download** — a button that triggers server-side DOCX generation and returns the `.docx` file

The form must include the transport module: a `transport` object set at report creation (mode: SEA or AIR) that drives which field sets appear.

---

## Acceptance Criteria

### Scaffold and data integrity
- [ ] `docker-compose up` starts FastAPI + Postgres + Redis with no errors; `pytest` passes a CI smoke test
- [ ] `sample-data/` is in `.gitignore` from the very first commit; pre-commit hook blocks a commit containing `IRDA/IND/SLA-\d+`
- [ ] Report numbers `M-<n>-<year>` are allocated sequentially with no duplicates even if two requests hit the endpoint simultaneously (verified by a concurrent-request test)

### Arithmetic correctness
- [ ] `compute()` returns 234 and percentages 56.84/23.08/5.98/10.26/3.84 for the Mandarin row test case
- [ ] `compute()` returns 675 and percentages 54.96/25.48/7.56/6.96/5.04 for the Mandarin column-total test case
- [ ] `compute()` returns 6.230 and 50.702 and percentages 93.81/4.46/1.73 for the Grapes (kg, 3dp) test case
- [ ] `compute()` uses `decimal.Decimal` throughout — a grep for `float(` in arithmetic code returns no results (excluding comments)

### Word output
- [ ] A `.docx` file downloads; python-docx can open it without errors
- [ ] Photo plate renders as a 2-column table with correct captions in the generated `.docx`
- [ ] `PAGE x OF y` field is present in the template and preserved in the generated output

### Photo integrity
- [ ] An uploaded photo's SHA-256 stored at upload matches a recomputed hash of the stored original bytes
- [ ] Deleting one photo from a group causes all subsequent photo numbers and every `(Photo Nos. …)` string to update correctly — verified by a unit test
- [ ] `photo_ranges.py` raises an assertion error if any photo is missing from a group or if ranges are non-contiguous

### Spreadsheet import
- [ ] A `.xlsx` file with live `=SUM()` formula cells is imported; formula cells are stored as their computed values, not as formula strings

### Corpus mining
- [ ] `mine_corpus.py` runs without errors on the 3 synthetic test fixtures and produces all five output CSVs
- [ ] `arithmetic_errors.csv` contains exactly the rows where the script's recomputed total disagrees with the printed total in the test fixtures

---

## Notes for agents

- The full spec is at `/home/agrim/CODES/qc-and-report-generator-tool/Survey-QC-Platform-Master-Spec.md` and `CRITICAL-RULES.md`. Read `CRITICAL-RULES.md` first.
- Week 1 scope is §14 Days 1–5 plus §13 (repo structure). Do not build preview/editing (Week 2) or multi-container/survey-report blocks (Week 3).
- Test fixtures must use synthetic data. Real arithmetic (133+54+14+24+9=234) may be kept — it is public math. All names, licence numbers, insurer names, and party names must be fake.
- Do not use: PyMuPDF/fitz, docx2pdf, float for any report numbers, paid APIs, generative AI for report content.
- The repo structure to follow is in §13 of the spec: `backend/app/{models,blocks,compute,render,ingest,api}/`, `frontend/src/`, `templates/`, `tools/`.

## 2026-09-05T03:30:14Z

Build Week 2 of the Marine Cargo Survey & QC Report Generation Platform: A4-styled in-browser HTML preview sharing the identical pure compute() engine with DOCX, interactive in-place editing (TipTap rich text editor, locked computed table cells, dynamic photo tray reordering), LibreOffice headless Proof View (pixel-exact PDF preview), and the mandatory Numeric Traceability Gate that blocks downloads if unverified numbers are detected.

Working directory: /home/agrim/CODES/qc-and-report-generator-tool
Integrity mode: development

---

## CRITICAL RULES (Strictly Enforced)
1. **Never store a computed value.** Totals, percentages, photo ranges, and annexure IDs are computed fresh at render time via pure function compute(block_state).
2. **`Decimal`, never `float`** for any report numbers, weights, or percentages. Rounding: ROUND_HALF_UP to 2 decimal places (pcs/pct) or 3 decimal places (kg).
3. **Never auto-correct a data mismatch.** Flag discrepancies and show both sources to the surveyor.
4. **Never recompress or overwrite an original photo.** Store bit-exact with SHA-256; derived copies only.
5. **Numeric Traceability Gate is mandatory.** Every number, date, and ID in output must trace to a confirmed source.
6. **No paid APIs, no PyMuPDF (AGPL), no docx2pdf (Windows-only).** Use LibreOffice headless for PDF conversion.
7. **Client data protection.** Do not commit real client reports or unredacted PII. Keep sample-data/ gitignored.

---

## Requirements

### R1. A4 HTML In-Browser Preview
Build server/client HTML preview rendering Block State into A4-dimensioned page containers using the report's typography, margins, and table border styling:
- **Zero-drift guarantee:** The HTML preview renderer and the DOCX renderer must call the exact same pure compute(block_state) function. All totals, percentages, and photo ranges in HTML must match DOCX bit-for-bit.
- Modular HTML component per block type: Particulars, Narrative, Measurements, Table, Photo Plate, Fixed Text.
- Realistic pagination preview with visual page breaks.

### R2. In-Place Editing & Optimistic Concurrency
Implement seamless data editing directly in the interface:
- **Narrative blocks:** TipTap rich-text editor per paragraph block (bold, italic, bullet lists only); flag edited blocks as surveyor_edited and record before/after states in the immutable audit log.
- **Table blocks:** Category input cells editable inline; **computed total and percentage cells remain strictly read-only and recompute live on every keystroke**. Rows can be added, removed, or reordered.
- **Photo Tray:** Drag-to-reorder photos across observation groups. Every photo number and bracketed range string (Photo Nos. X to Y) updates immediately without page reloads.
- **Optimistic Concurrency:** PATCH /api/reports/{id}/block-state checks an incrementing version number, rejecting stale overwrites with HTTP 409 Conflict.

### R3. Proof View & Dual Download (DOCX + PDF)
- **Proof View:** Convert generated .docx on the server using headless LibreOffice (libreoffice --headless --convert-to pdf) into an exact PDF representation and display in-browser via a PDF viewer (dual toggle: "Edit View" / "Proof View").
- **Download Endpoints:** Support both GET /api/reports/{id}/download/docx and GET /api/reports/{id}/download/pdf.

### R4. Numeric Traceability Gate (Safety Enforcement)
Before any .docx or .pdf file is downloaded or finalized:
- Extract every number, currency amount, container ID, and date from the rendered output document.
- Verify that every extracted value traces back to a user-entered field in block_state, a declared spreadsheet cell, or a verified document scan.
- If any number cannot be traced to an authorized source, **block the download immediately**, return HTTP 422 with a structured diff of the untraced values, and display an alert in the UI.
- Implement an automated adversary test that deliberately injects an untraced value and asserts the download is blocked.

### R5. Document Ingestion, Loggers & Benchmark Report Verification
- **Temperature Logger Parser:** Parse plain-text / PDF records from cold storage temperature loggers; extract reading ranges without hardcoded arbitrary "spike" heuristics.
- **Handwritten Tally Fallback:** Support image preview with side-by-side transcription grid for manual tally entry.
- **Historical Benchmark Verification:** Verify calculations against the 3 benchmark QC reports (Mandarin FBIU5499689, Orange MMAU1200498, Grapes OOLU6232443).

---

## Acceptance Criteria

### HTML Preview & Consistency
- [ ] HTML preview renders all block types in A4-dimensioned layout matching client styles.
- [ ] Automated test asserts that all numbers and percentages displayed in HTML preview match the values generated in the Word .docx report.

### In-Place Editing & Concurrency
- [ ] TipTap editor allows bold, italic, and bullet list formatting in narrative blocks.
- [ ] Editing a table cell updates row totals, column totals, and percentages instantly without server roundtrips.
- [ ] Reordering or deleting a photo immediately updates all photo plate captions and all narrative references (Photo Nos. ...).
- [ ] Concurrent edits with an outdated version number are rejected with HTTP 409 Conflict.

### Proof View & PDF Conversion
- [ ] Proof View generates and displays a PDF converted from the real .docx via headless LibreOffice (/usr/local/bin/libreoffice).
- [ ] Both .docx and .pdf downloads function correctly and deliver valid documents.

### Traceability Gate
- [ ] An automated test proves that injecting an untraceable numeric literal (e.g. 99999) into rendered output causes the download endpoint to abort and return HTTP 422.
- [ ] Normal reports with fully traceable numbers pass the gate with zero false positives.

### Verification Resources
- Existing test suite: backend/tests/ (53 passing tests) and tests/e2e/.
- LibreOffice binary available at /usr/local/bin/libreoffice.
- Real benchmark source files in sample-data/tally_sheets/Marine cargo/More reports and csv/.


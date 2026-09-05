# Marine Cargo Survey & QC Report Generation Platform
## Master Development Specification (consolidated)

**Client:** Marine Cargo Agencies (Mr. Baburao Bhosale) — surveyor, IRDAI licensed
**Prepared by:** Zyrodev
**Timeline:** 3 weeks (15 working days)
**Source documents merged into this spec:**
1. Scope of Work — Survey & QC Report Generation Platform (client-facing PDF)
2. Project Timeline Plan — 3 Weeks (day-by-day build plan for the developer)
3. Technical SOW & Architecture Specification v3.1 (architecture, data model, risk register)

> **How to use this document.** This is the single reference an agentic developer (or dev team) needs to build the whole system without going back to the original three files. A separate file, `CRITICAL-RULES.md`, extracts the handful of rules that are most likely to be violated by mistake and must be re-read before writing code and before every merge. Read that file first, then this one.

---

## 1. Project Summary

A web application, hosted on the client's own domain, where a marine cargo surveyor:

1. Picks a report type (a saved arrangement of sections/"blocks").
2. Uploads photographs (existing bulk uploader, reused as-is), spreadsheets/CSVs, and supporting documents (invoices, bills of lading, temperature-logger PDFs, scanned tally sheets).
3. Fills a form that is auto-generated from the blocks the chosen report type contains.
4. Clicks **Generate** — a finished Word report is assembled in seconds, with letterhead, tables, chart, numbered photo plates and annexures.
5. Previews it in the browser, edits text/tables/photos in place.
6. Downloads Word (.docx) and PDF.

**Impact:** reports that take 3–5 hours today take 20–45 minutes. A CSV-driven QC report takes 10–20 minutes.

**Six report products** (all built on one engine, as saved configurations, not six separate builds):
1. General Cargo – Sea Shipment
2. General Cargo – Air Shipment
3. Perishable Cargo – Sea Shipment
4. Perishable Cargo – Air Shipment
5. Perishable Cargo QC Report – Sea Shipment
6. Perishable Cargo QC Report – Air Shipment

**Multi-container support:** one shipment document spanning several containers/ULDs/pallet lots produces **one report**, with each unit as its own correctly numbered section — never one report per container.

---

## 2. Design Constraints, In Priority Order

1. **No fabricated content.** Every value in the output traces to a source the surveyor supplied or confirmed — enforced mechanically by the numeric traceability gate (§10.8).
2. **All arithmetic correct by construction.** No number is ever typed twice or computed by hand.
3. **Cargo-agnostic.** New cargo types, damage modes, report products are handled by composing existing blocks, not by new development.
4. **Mode-agnostic.** Sea and air are the same engine with a transport-mode property driving field sets, timeline stages, weight basis and clause selection.
5. **One shipment, one report.** A shipment covering several containers/ULDs/pallet lots produces a single report.
6. **No paid APIs.** Everything (OCR, etc.) runs locally.
7. **The surveyor remains the author of professional judgement** — cause of loss, liability, interpretation of readings. The system structures, computes, formats and cross-references; it never decides.

---

## 3. Architecture — Three Invariants

1. **Block State is the only source of truth.** A report is a single JSON structure ("Block State"). The Word file, the browser preview, and the PDF are all generated fresh from it, every time.
2. **Derived values are never stored.** Totals, percentages, photo numbers, photo ranges (e.g. "(Photo Nos. 41 to 44)"), annexure IDs, weight differences — all computed at render time and thrown away after. Never written to the database. One function, `compute(block_state)`, is called by the Word renderer, the HTML preview, and the PDF — same function, same numbers, always.
3. **Two gates.** Nothing enters state unverified (input verification / confirmation); nothing leaves output untraceable (numeric traceability gate).

Why rule 2 matters: if a total is stored, it can go stale — someone edits a row, the total doesn't update, and a wrong number lands in a legal document. If it's always calculated, that's impossible. This single rule is most of the quality guarantee.

---

## 4. The Block Model

Cargo is unbounded (perishables, dry bulk, break-bulk/project cargo, containerised general cargo, machinery, steel, vehicles, flexitanks/ISO tanks, fire/heavy-weather/jettison/general average, plus non-claim work: pre-shipment inspection, lashing/securing surveys, draft surveys, on/off-hire container surveys). But the **shapes of information** a survey report contains are a small, stable set: **15 block types**. A report is an ordered list of typed, optional, reorderable blocks. Templates are saved block sequences.

| # | Block type | Holds | Computed |
|---|---|---|---|
| 1 | `particulars` | ordered key/value rows; scalar, list, or money+currency | — |
| 2 | `parties` | repeating: role, name, address, reference | — |
| 3 | `attendance` | repeating: name, designation, representing | — |
| 4 | `timeline` | repeating: event type, date/date-range, location, basis (as reported / as stated by / confirmed) | transit days, elapsed intervals |
| 5 | `narrative` | paragraph(s) with typed slots; clause-library reference or free text | resolved slot values, photo/annexure references |
| 6 | `observations` | repeating: text, severity, dimensions, quantity, photo group ref | photo ranges |
| 7 | `measurements` | repeating: subject, qualifier, method, value or min/max, unit, photo group ref | unit conversions, ranges, aggregates |
| 8 | `table` | grouping column + N category columns + unit dimension (pcs/kg/mt/…) + rows | row totals, column totals, percentages, grand totals |
| 9 | `reconciliation` | repeating events; each: label, chosen formula, term values, reference figure | found value, difference, excess/shortage, summary |
| 10 | `instrument` | device type, serial/trip, config, summary stats, optional time series | derived stats, chart series |
| 11 | `inventory` | hierarchical: package → item → damage; qty, part number, photo group ref | counts, roll-ups, photo ranges |
| 12 | `photo_plate` | series: label, provenance, ordered assets, observation groups | numbering, ranges, plate layout |
| 13 | `annexures` | repeating: title, file, prefix group | IDs (A1…An), ordering, merge sequence |
| 14 | `fixed_text` | versioned static text — disclaimer, "ISSUED WITHOUT PREJUDICE", licence line, signature block | — |
| 15 | `unit_group` *(v3.1)* | a set of child blocks scoped to one carriage unit (container/ULD/pallet lot), repeated over the shipment's units | per-unit headings, per-unit photo ranges, shipment-level roll-ups |

**Every block is optional.** A pre-shipment lashing survey has no reconciliation or cause narrative; a draft survey has no defect table.

### 4.1 Stress-test: block sequences for cases outside the sample corpus

| Case | Block sequence |
|---|---|
| Draft survey (bulk weight by displacement) | particulars → measurements (drafts fore/aft/mid, density, constants) → reconciliation (calculated vs B/L) → narrative → photo_plate |
| Container rain / condensation | particulars → timeline → observations → measurements (moisture, dew point) → instrument (humidity logger) → narrative (cause) → photo_plate |
| Fire damage | particulars → timeline → observations → inventory (burnt/salvageable) → reconciliation (salvage value) → narrative (cause) → photo_plate → annexures |
| Pilferage / short-landing | particulars → observations (seal condition) → reconciliation (count declared vs found) → narrative (cause) → photo_plate |
| Pre-shipment lashing survey | particulars → observations → photo_plate → fixed_text (certificate) — no cause, no reconciliation |
| QC perishable (existing) | particulars → narrative (summary) → measurements → table → instrument (chart) → photo_plate → fixed_text |
| M-71 mis-declaration (existing) | particulars → parties → attendance → timeline → narrative ×2 → photo_plate ×3 → reconciliation ×3 → observations (per container) → narrative (cause) → annexures ×18 → fixed_text |
| Air general cargo, ground-handling damage | particulars (AWB) → parties → attendance → timeline (airport stages) → narrative → observations → inventory (package/part) → reconciliation (chargeable weight) → narrative (cause) → photo_plate → annexures → fixed_text |
| Air perishable, cool-chain break | particulars (AWB) → timeline (airport stages) → narrative → measurements (pulp temp, brix) → table (defects) → instrument (short-trip logger) → narrative (cause) → photo_plate → fixed_text |
| Multi-container sea shipment, 6 units | particulars → parties → attendance → timeline → narrative → **unit_group ×6** (particulars → table → reconciliation → observations, per container) → reconciliation (SHIPMENT roll-up) → narrative (cause) → annexures → fixed_text |

---

## 5. Templates and the Generated Form

A **template** = a saved, named block sequence with defaults ("Reefer perishable QC", "Container mis-declaration", "Project cargo handling damage", "Machinery damage inventory", "Draft survey", etc.). Templates are data, editable without a code change.

Workflow: pick nearest template → add/remove/reorder blocks for this case → **the form is generated from the resulting block list.** No form is hand-designed per cargo type.

Field-level config within a block (which categories a `table` carries, which measurement types a `measurements` block collects) is data too. A new commodity with unfamiliar defect categories needs a config entry, not code.

Phase 0 (§13, Day 1) mines the client's report archive for which blocks actually occur, in what sequences, how often — producing the real template set empirically.

---

## 6. Transport Mode: Sea vs Air

Transport mode is a **property of the shipment**, set once, carried through the report. Not a separate code path — the same block types render for both modes with mode-dependent field sets, labels, computations and clause selections.

| Concern | Sea | Air |
|---|---|---|
| Transport document | Bill of Lading (B/L) — document of title, negotiable | Air Waybill (AWB) — not a document of title, non-negotiable |
| Document hierarchy | Master B/L / House B/L | Master AWB (carrier) / House AWB (consolidator); survey may cover one HAWB inside a consolidation |
| Document number format | Carrier-specific alphanumeric | 3-digit airline prefix + 7-digit serial + check digit (serial mod 7), written 098-1234 5678 |
| Unit of carriage | Container — ISO 6346 id (4 letters + 7 digits, check digit), size/type code, seal no., marked tare | ULD (3-letter type + serial + owner code, e.g. AKE12345AA), or pallet lot, or loose pieces |
| Conveyance | Vessel name + voyage number | Flight number + date, possibly several legs with transhipment |
| Origin/destination | Port of loading/discharge; place of receipt/delivery | Airport of departure/destination (IATA codes); requested routing |
| Timeline stages | Shipped on board → sailed → discharged → CFS transfer → customs → delivery | Tendered/accepted → security screening → ULD build-up → uplift → transit/transhipment → arrival → breakdown/deconsolidation → airline/custodian warehouse → customs → delivery |
| Typical transit | Weeks | Hours to days |
| Weight basis | Gross/net/tare; VGM where applicable | Gross **and chargeable weight** = max(actual, volumetric); volumetric at IATA divisor 6,000 cm³/kg (≈166.67 kg/m³) |
| Liability & notice regime | Hague/Hague-Visby via Indian COGSA; Multimodal Transportation of Goods Act 1993 where applicable | Montreal Convention 1999 via Carriage by Air Act 1972 (as amended); per-kg limitation and short written-complaint window |
| Common damage mechanisms | Prolonged storage, reefer malfunction, condensation/container rain, stow/lashing failure, water ingress, seal integrity | Ground-handling impact, tarmac/apron temperature exposure, cool-chain break during transhipment, ULD build-up crushing, delay-driven decay |

**Consequences for subsystems (each an extension of an existing one, never a new one):**
- **Document extraction:** AWB field schema alongside B/L schema, same local OCR path. ISO 6346 / AWB check-digit validation added at entry.
- **Timeline block:** mode-specific stage vocabulary; transit duration computed from the mode's own start/end stages.
- **Reconciliation block:** air adds a volumetric-weight term and chargeable-weight comparison; formula remains surveyor-selected per weighing event.
- **Instrument block:** air perishable/pharma runs much shorter logger traces; the no-auto-excursion-detection rule (§9) applies unchanged and matters more here.
- **Clause library:** mode-aware selection — an air report's Next Step clause references its own written-complaint window and per-kg limitation; sea references its own notice period and package/unit limitation.

> **Legal figures are configuration, never code.** Liability limits and notice periods change (the Montreal per-kg limit has been revised; SDR values float daily). Held as versioned reference data with an effective date, shown to the surveyor with its source, confirmed explicitly, recorded in the audit trail. The system never asserts a legal limit the surveyor hasn't accepted. **Populating that table is the client's professional call — the platform only makes the applicable entry impossible to overlook.**

---

## 7. Multi-Unit Shipments (`unit_group`)

**Requirement:** one shipment document may cover several carriage units. Each unit gets its own particulars, tally figures, weight reconciliation and photo sequence, correctly numbered and kept separate. Output is **one report**, never one per unit.

**Construct:** `unit_group` holds a set of child blocks and repeats them over the shipment's `carriage_units`. Rendering iterates the unit list, emitting scoped children once per unit, with the unit's identity substituted into the group heading, e.g.:

```
1) CONDITION OF CONTAINER NO. CMAU2016593 & CARGO: (SEE SURVEY PHOTO NOS. 67 TO 106)
2) CONDITION OF CONTAINER NO. DFSU1851396 & CARGO: (SEE SURVEY PHOTO NOS. 107 TO 138)
3) CONDITION OF CONTAINER NO. FCIU4387412 & CARGO: (SEE SURVEY PHOTO NOS. 139 TO 172)
```
...with a shipment-level roll-up after them. (Modelled directly on real client reports M-71-2026, 6 containers, and M-244-2025, 9 containers.)

**Photograph numbering — two patterns, chosen per template:**
- `SHARED_SERIES_SEGMENTED` — one series across the whole report, each unit occupying a contiguous range (e.g. 67–106, 107–138, 139–172…). **Default**, matches existing client practice.
- `SERIES_PER_UNIT` — separate series per unit, each numbered from 1, for units surveyed as genuinely separate events.

Ranges are always computed, never typed, re-derived on every reorder/insert/delete. Contiguity and exhaustiveness are asserted across the whole document.

**Shipment-level roll-up:** a block can declare `scope: "SHIPMENT"` and roll up from a per-unit block (e.g. M-71 does this three times, once per weighing event). Roll-ups computed at render time, never stored.

**Design notes:**
- A single-unit shipment is simply n = 1 — same construct, no separate code path.
- Mode-agnostic — a carriage unit may be a sea container, air ULD, pallet lot, or loose-piece lot.
- Per-unit provenance — each unit's figures carry their own provenance tags.
- Unit groups can be reordered/added/removed in the preview like any other block.
- **Reconciliation caution carries forward with particular force:** per-unit B/L figures often derive from an averaged declared total (M-71: 6 × 21,148 kg = 126,888 vs declared 126,891 kg, a surveyor-accepted 3 kg difference). A multi-unit reconciler must surface such differences, never resolve them.

---

## 8. The Six Report Formats

Six saved block sequences over one engine — a grid of cargo class × transport mode, plus the QC variant.

| Format | Family | Mode | Distinguishing content |
|---|---|---|---|
| General Cargo – Sea Shipment | Survey | Sea | B/L particulars, container units, port timeline, inventory for package/part damage, cause & liability narrative |
| General Cargo – Air Shipment | Survey | Air | AWB particulars, ULD/pallet/loose units, airport timeline, chargeable-weight reconciliation, ground-handling cause patterns |
| Perishable Cargo – Sea Shipment | Survey | Sea | + measurements (pulp temp, brix, penetrometer), instrument for reefer loggers, defect table, physiological cause patterns |
| Perishable Cargo – Air Shipment | Survey | Air | + airport timeline, short-trip logger traces, apron-exposure/cool-chain-break cause patterns |
| Perishable Cargo QC Report – Sea Shipment | QC | Sea | Consignee-facing. Particulars, summary narrative, measurements, defect table, chart, photo plates, signature. **No** cause-of-loss/liability content |
| Perishable Cargo QC Report – Air Shipment | QC | Air | As above + AWB particulars and airport arrival details |

All six inherit the multi-unit construct (§7). Adding a seventh format (draft survey, lashing certificate, container condition survey) is a new saved sequence, not new development.

---

## 9. Data Model

Full JSON shape (illustrative values from real sanitised examples). This is what a `reports` row's `block_state JSONB` column holds.

```json
{
  "report": {
    "id": "uuid",
    "number": "M-102-2026",
    "family": "SURVEY_REPORT",
    "state": "FINAL",
    "template_id": "reefer-perishable-survey",
    "template_version": 4,
    "docx_template": "mca-survey-v3",
    "issued_date": "2026-07-17",
    "place": "Mumbai, India",
    "licence_no": "IRDA/IND/SLA-XXXXXX",
    "status": "DRAFT"
  },
  "transport": {
    "mode": "SEA",
    "document": {
      "kind": "BILL_OF_LADING",
      "level": "MASTER",
      "number": "MXO0788603",
      "date": "2026-03-20",
      "issuer": "CMA CGM",
      "check_digit_valid": true
    },
    "conveyances": [
      { "name": "COSCO ASIA", "reference": "0HCMWW1MA", "leg": 1, "transhipment_at": "Shanghai, China" },
      { "name": "CMA CGM MEDEA", "reference": "0MXIYW1MA", "leg": 2 }
    ],
    "origin": { "node": "Manzanillo Port, Mexico", "code": null },
    "destination": { "node": "Nhava Sheva Port, India", "code": null },
    "liability_regime": {
      "instrument": "Hague-Visby / Carriage of Goods by Sea Act (India)",
      "limit_basis": "package_or_kg",
      "notice_period_days": null,
      "reference_version": "regimes@2026-01",
      "confirmed_by": "surveyor",
      "confirmed_at": null
    }
  },
  "carriage_units": [
    { "id": "u1", "unit_type": "CONTAINER", "identifier": "CMAU2016593", "identifier_valid": true,
      "iso_type": "22G1", "size": "20'", "seal_no": "M0125887", "marked_tare_kg": "2190", "manufacture_date": "2010-12" },
    { "id": "u2", "unit_type": "ULD", "identifier": "AKE12345AA", "uld_type": "AKE", "owner_code": "AA" },
    { "id": "u3", "unit_type": "LOOSE", "pieces": 42 }
  ],
  "weights": {
    "gross_kg": "126891",
    "net_kg": "126891",
    "volumetric_kg": "COMPUTED",
    "chargeable_kg": "COMPUTED",
    "vgm_kg": null
  },
  "blocks": [
    { "id": "b1", "type": "particulars", "rows": [
        { "label": "Insurers", "value": ["AGCS Marine Insurance Company", "..."] },
        { "label": "Insured Value", "value": [{ "amount": "149999540.00", "currency": "USD" }] },
        { "label": "Container Nos.", "value": ["OTPU6766015"], "note": "40' Reefer" } ] },
    { "id": "b2", "type": "attendance", "rows": [
        { "name": "Mr. Baburao Bhosale", "designation": "Surveyor",
          "representing": "Marine Cargo Agencies Pvt. Ltd (On behalf of the Cargo Insurers)" } ] },
    { "id": "b3", "type": "timeline", "rows": [
        { "event": "DISCHARGE", "date": "2026-07-11", "location": "Nhava Sheva Port", "basis": "as reported" },
        { "event": "SURVEY", "date": "2026-07-15", "location": "Eskimo Cold Storage Unit-2, Kopar Khairane" } ],
      "computed": ["transit_days"] },
    { "id": "b4", "type": "narrative", "section": "PARAGRAPH 2: CIRCUMSTANCES OF LOSS",
      "clause": "circumstances.reefer_delivered_then_damage_found@v3",
      "slots": { "vessel": "VARANYABHUM", "voyage": "VRYB0012W", "external_condition": "externally sound",
                 "discovered_by": "the Consignees' representative", "moved_via_cfs": true },
      "additional_text": null, "source": "clause_library" },
    { "id": "b5", "type": "measurements", "unit_system": "metric", "rows": [
        { "subject": "pulp temperature", "method": "digital probe thermometer", "min": "0.9", "max": "1.1", "unit": "C", "photo_group": "pg2" },
        { "subject": "penetrometer", "qualifier": "Sound Kiwi (39 Count)", "min": "7.53", "max": "8.22", "unit": "LBS", "photo_group": "pg4" },
        { "subject": "brix", "min": "9.9", "max": "10.7", "unit": "pct" } ] },
    { "id": "b6", "type": "table", "title": "Defect breakdown", "unit": "pcs", "grouping_label": "Count",
      "source": { "kind": "csv", "file": "16 Boxes.xlsx", "sheet": "16 Boxes", "column_map": {} },
      "categories": [ { "key": "sound", "label": "Sound (Pcs)" }, { "key": "soft", "label": "Soft (Pcs)" }, { "key": "rotten", "label": "Rotten (Pcs)" } ],
      "rows": [ { "group": "39", "boxes_opened": 5, "values": { "sound": 401, "soft": 204, "rotten": 3 } } ],
      "computed": ["row_totals", "column_totals", "percentages", "grand_total"],
      "source_mapping": { "skin_disorder": "DROPPED", "butterfly": "DROPPED", "_confirmed_by": "surveyor", "_confirmed_at": "2026-07-16T11:04:00+05:30" } },
    { "id": "b7", "type": "reconciliation", "title": "CFS weighbridge, 22 June 2026",
      "formula": "GROSS_MINUS_CONTAINER_TARE", "reference_label": "Gross weight of cargo as per Bill of Lading", "annexure_prefix": "C",
      "rows": [ { "subject": "CMAU2016593", "slip_no": "59165", "slip_date": "2026-06-22", "gross": "11740", "container_tare": "2190", "reference": "21148" } ],
      "computed": ["found_gross", "difference", "direction", "summary"] },
    { "id": "b8", "type": "instrument", "device": "DeltaTrak FlashLink", "trip_no": "90287908", "annexure": "A",
      "setpoint": { "value": "0.0", "unit": "C", "source": "consignee_verbal", "attributed_to": "Consignee", "date": "2026-07-15" },
      "series_ref": "asset:logger1.pdf", "verdict": { "selection": "NO_SUBSTANTIAL_VARIATION", "author": "surveyor" } },
    { "id": "b9", "type": "photo_plate", "series_id": "survey", "label": "Survey Photo", "provenance": "own_survey", "columns": 2,
      "groups": [ { "id": "pg1", "observation": "Cargo produced for inspection", "asset_ids": ["a1", "..."] } ],
      "computed": ["numbering", "ranges", "plate_layout"] },
    { "id": "b10", "type": "annexures", "rows": [ { "prefix": "A", "title": "Temperature Recorder Trip 90287908", "asset_id": "a900" } ],
      "computed": ["ids", "merge_order", "documentation_list"] },
    { "id": "b11", "type": "fixed_text", "key": "disclaimer@v2" },
    { "id": "b20", "type": "unit_group", "repeat_for": "carriage_units",
      "heading_template": "{index}) CONDITION OF CONTAINER NO. {identifier} & CARGO: (SEE {photo_ref})",
      "photo_numbering": "SHARED_SERIES_SEGMENTED",
      "blocks": [
        { "type": "particulars", "scope": "UNIT" },
        { "type": "table", "scope": "UNIT" },
        { "type": "reconciliation", "scope": "UNIT" },
        { "type": "observations", "scope": "UNIT" } ],
      "computed": ["unit_headings", "per_unit_photo_ranges"] },
    { "id": "b21", "type": "reconciliation", "scope": "SHIPMENT", "rolls_up_from": "b20.reconciliation",
      "title": "WEIGHT SUMMARY", "computed": ["shipment_found_total", "shipment_difference", "direction"] }
  ],
  "assets": {
    "a1": { "kind": "photo", "sha256": "...", "original_path": "...", "derived": { "display": "...", "report": "..." },
            "exif": {}, "exif_integrity": "INTACT" }
  },
  "provenance": {
    "blocks.b6.rows[0].values.sound": { "source": "csv_imported", "confidence": 1.0, "confirmed_by": "kishan", "confirmed_at": "..." }
  },
  "audit": [ { "at": "...", "actor": "...", "action": "PREVIEW_EDIT", "path": "blocks.b4.additional_text", "before": null, "after": "..." } ]
}
```

**Notes:**
- `scope` is `SHIPMENT` by default; `UNIT` marks a block as living inside a `unit_group`.
- `identifier_valid` / `check_digit_valid` are **computed**, not entered. A failed check digit is flagged for confirmation — never auto-corrected.
- `volumetric_kg` / `chargeable_kg` computed from piece dimensions, appear only on air reports.
- `liability_regime` carries `reference_version`, `confirmed_by`, `confirmed_at` so no legal figure reaches a report unconfirmed.
- **Every computed field is derived at read time and never stored.** This is what makes both the arithmetic guarantee and safe preview-editing real.
- Existing single-container sea reports remain valid: they're simply `mode: "SEA"` with one entry in `carriage_units`.

**Database tables (Postgres):**

| Table | Key columns |
|---|---|
| `reports` | id, report_number, family, state, template_id, status, **block_state JSONB**, created_at, updated_at |
| `assets` | id, report_id, kind, sha256, original_path, derived_paths, exif JSONB |
| `audit` | id, report_id, at, actor, action, path, before, after |
| `templates` | id, name, family, mode, block_sequence JSONB |
| `clauses` | id, key, version, text_with_slots, conditions JSONB |

**Report numbering:** `M-<n>-<year>`, sequential per year, allocated on create. Must not produce duplicates under concurrent requests — use a DB sequence or a unique constraint with retry.

---

## 10. Subsystems

### 10.1 Form and Field-Notes Capture

The generated form is the primary input surface. It carries everything no file can supply: instruction provenance and channel; attendance; each event's date and basis; verbal statements with attribution; **what could not be inspected and why** (legally load-bearing); on-site test results (pulp temperature, brix, moisture, penetrometer); declared-vs-found particulars as separate fields.

Requirements: dropdowns/pickers wherever the value set is bounded; remembered values (recurring cold stores, vessels, consignees, CFSs); pre-fill from extracted documents; a **free-text "additional observations" field on every block** as the escape hatch. Must work on a phone, offline, syncing later (cold rooms have no signal).

Judgement fields are structured selections, not free prose: cause-pattern picker, contributing-factors multiselect, temperature verdict, advice/next-step selection — rendered in house wording by the clause library. The surveyor still makes every determination; they select it instead of typing it.

### 10.2 Photographs and Integrity

Reuse the client's existing bulk uploader as-is — do not rebuild it. Photos are held as **ordered trays per series**; multiple series per report, each with a label and provenance (own survey / consignee's CHA / shipper's load port). **Series are never merged.**

Surveyor drags dividers to segment a series into observation groups, writes one observation per group. **Numbering and ranges are computed, never typed**, re-derived on every reorder/insert/delete. House rendering convention: `(Photo Nos. 55 to 59)`, `(Photo Nos. 39 & 40)`, `(Photo No. 50)`. Validation asserts every photo belongs to exactly one group and ranges are contiguous/exhaustive.

**Integrity:** originals stored bit-exact and immutable, SHA-256 recorded at upload; display/report copies derived separately; full EXIF retained, exportable as a metadata annexure. (In a real client case, EXIF timestamps proved a shipper had altered stuffing photos — **never recompress or overwrite an original**.) Crops/rotations in preview apply to derived copies only.

### 10.3 Document Extraction

- **Text-layer PDFs:** pdfplumber (MIT) + pypdf (BSD). Not PyMuPDF (AGPL-3.0 — a licensing problem for a hosted web app).
- **Scanned PDFs (no text layer):** local OCR, Tesseract or PaddleOCR (both Apache-2.0, CPU, offline). Watermarked documents (e.g. diagonal "Non-Negotiable Copy") need preprocessing — adaptive thresholding, background subtraction.
- **Extraction is pre-fill only, never authority.** Every extracted field shown beside the crop it came from, for confirmation. The system must remain fully usable with extraction disabled entirely.
- **Normalisation:** dates to ISO with source convention recorded; ambiguous dates (day ≤ 12) flagged for confirmation (invoices can be DD/MM while a logger is MM/DD, in the same shipment). Locale-aware number parsing (Indian grouping, German grouping, plain). Units: °C/°F, kg/MT, LBS, multi-currency.
- **AWB field schema** sits alongside the B/L schema on the same OCR path (v3.1) — a second field map, not a second technology. ISO 6346 container check-digit and AWB mod-7 check-digit validation added at entry — flag failures, never auto-correct.

### 10.4 Tabular Data — CSV/Excel First, Handwriting as Fallback

CSV/Excel upload into a `table` block is the **primary** path for every table, reconciliation and inventory block: upload sheet → map columns once per template → done. Formula cells read as **values** (client workbooks contain live `=SUM()` formulas).

**Handwritten sheet capture is fallback only**, used when no spreadsheet exists — a data-entry accelerator with a mandatory verification gate, never a blind OCR pipeline: transcription grid beside the sheet image, each cell shows its **cropped source region**; per-cell confidence; low-confidence cells **block generation until confirmed**; dual-pass transcription with disagreement forcing adjudication; row/column checksums.

**Column-set flexibility is mandatory** — defect categories vary per commodity and may be merged/dropped between tally sheet and report (a domain decision by the surveyor, recorded with attribution, never inferred). Some commodities measured in kg to 3 decimals, others in pieces.

**Reconciliation formulas are selected per weighing event, never guessed** — a real report has three different formulas across three weighings of the same containers:
1. gross − (trailer + container combined tare)
2. gross − trailer tare − marked container tare
3. gross − marked container tare (container weighed alone)

**Highest-leverage upstream fix — redesign the pre-printed tally form:** one printed box per digit; pre-printed column headings per commodity; a printed row-total column as a free checksum; corner registration marks for automatic deskew (`cv2.aruco`); a QR code identifying commodity + form version; one sheet per page. This turns free-form handwriting recognition into isolated boxed-digit classification (LeNet-class CNN, CPU, trained on MNIST + the client's own verified sheets over time). Needs a client decision (§20) since the software is built around whichever form is in use.

### 10.5 Instrument Files (Temperature/Humidity Loggers)

Page 1 of a DeltaTrak FlashLink PDF has every statistic as plain machine-readable text (Trip #, Model #, Interval, Start Delay, Start/Stop times+temps, Trip Length, Data Points, Max/Min/Average, Mean±SD, Mean Kinetic Temperature, alarm config) — a regex reproduces the whole table. Later pages carry the time series for charting. **Unit ordering differs per file** (45.5°F/7.5°C vs 4.1°C/39.3°F) — detect, never assume. Multiple loggers per container supported.

Two hard constraints:
1. **There is no setpoint in the file.** If a carrying temperature came from a verbal statement, it's a form field with attribution — never inferred.
2. **No automatic excursion detection.** Present statistics and the plotted series with ingress/egress windows marked; interpretation is a surveyor selection (see §11, finding 8.1).

Generalises to humidity loggers, shock/tilt indicators, moisture meters, draft readings.

### 10.6 Document Assembly (DOCX generation)

**Build by injecting into a real template, never by reconstructing.** Letterhead, `PAGE x OF y` field codes, footer rules, table border styles, signature blocks, embedded charts preserved by editing a cleaned copy of an actual client report.

- **Native Word charts:** `python-docx` cannot create charts. Preference order: (a) keep the chart in the template and rewrite the embedded workbook's cached values + cell references (keeps a live, editable chart) → (b) generate chart XML directly → (c) fall back to a rendered PNG image. **Decide in week 1** — it constrains the template. If it takes more than a day, tell the client before falling back.
- **`PAGE x OF y` counts the report body only, not the merged file** (a real report says "Page 1 of 69" while the delivered merged PDF is 157 pages once annexures are appended).
- **Annexure assembly:** IDs allocated deterministically (A1…A6, B1…B6, C1…C6); narrative references resolved from the same structure so they can never drift; attachments merged after the body (pypdf); documentation list generated from the same source.
- One renderer per block type. Adding a block type is additive and touches nothing else.

### 10.7 Preview and In-Browser Editing

**The decisive rule: the preview edits the Block State, not the document.** An edit issues a patch against state; derived values recompute; affected blocks re-render. The DOCX is regenerated from state only on download. Editing a generated DOCX, or round-tripping it through HTML, would destroy letterhead/header-footer fidelity and chart fidelity, create two sources of truth, and break every accuracy guarantee — **rejected as an approach.**

**Two views:**

| Mode | What it is | Fidelity |
|---|---|---|
| **Edit** | HTML render in A4 page boxes, report's fonts/table styles, fully editable | Near-identical; browser vs Word differ on hyphenation/line/page breaks |
| **Proof** | The real DOCX rendered to PDF server-side (LibreOffice), shown in browser via pdf.js | Exact; read-only |

One click switches between them. Be upfront with the client that Edit view is close but not pixel-identical — that's precisely why Proof view exists.

**What's editable, per block type:**
- **Text** (narrative, observations, fixed_text): inline rich-text, constrained to bold/italic/lists (TipTap/ProseMirror or Lexical **per block**, never one page-wide contenteditable). Editing clause-generated text marks the block `surveyor_edited`, logs before/after to audit.
- **Tables** (table, reconciliation, inventory): input cells editable inline; **computed cells (totals/percentages) are locked and recompute live** — cannot be typed over. Add/delete/reorder rows. An explicit override requires a reason, recorded and flagged.
- **Photos** (photo_plate): drag to reorder, delete, replace, move between groups, rotate, crop. **Every photo number and every `(Photo Nos. …)` reference in the narrative recomputes instantly.** Crops/rotations apply to derived copies; originals untouched.
- **Blocks:** add, remove, reorder, duplicate — the form updates to match.
- **Charts:** regenerate from their table; no direct editing.

**Supporting behaviour:** autosave with optimistic concurrency (reject stale writes); named versions + revert; per-report locking if two surveyors open the same report; an outstanding-items panel listing every unconfirmed value, blocking download until cleared; numeric traceability gate re-run **at every download**, not just first generation.

### 10.8 Verification, Computation, and the Output Gate

- **Provenance on every field.** Tag each value: `surveyor_entered`, `csv_imported`, `ocr_verified`, `document_extracted_confirmed`, `computed`, `clause_library`, `surveyor_edited`. Rendering refuses any field with no source.
- **Rounding declared once and applied everywhere:** `decimal.Decimal`, `ROUND_HALF_UP`, 2 decimal places. **Never `float`.** Historical reports are internally inconsistent about rounding — the new engine will legitimately differ from old ones in the last digit; that's expected, don't chase it. Decide explicitly whether percentage columns are forced to sum to 100.00 (largest-remainder adjustment) or allowed to read e.g. 99.99.
- **Reconciliation is advisory, never automatic.** Real data does not always tie out (6 × 21,148 kg = 126,888 vs a declared 126,891 kg). Flag, explain, show both sources, let the surveyor resolve. Never silently adjust.
- **Numeric traceability gate.** Before every release/download: extract every number, date and identifier from the rendered document and assert each exists in Block State. Any untraceable literal is a **hard failure** that blocks download. Write a test that deliberately injects an untraceable number and confirms the gate catches it.
- **Audit trail (immutable, per report):** who entered/confirmed/edited each field and when; what extraction proposed vs what was accepted; every preview edit with before/after; clause-library versions used; photo hash manifest; output hash. This is itself a deliverable — the surveyor's own protection under an IRDAI licence.

### 10.9 Narrative: Clause Library, Not Generative AI

Measured evidence from the client's own corpus that this is a templating problem, not a generative-AI problem:
- QC summary prose overlaps 76–87% across commodities word-for-word (including an identical grammatical error reproduced in all three).
- Survey-report disclaimer boilerplate is 97.6–100% identical across reports two years apart, including an identical misspelling ("CIRCUMTANCES") appearing in all four — proof of copy-paste templating, since a generative model or a fresh writer would have auto-corrected it.
- Low word-overlap paragraphs (5–30%) still decompose into ~10 structured slots (vessel, voyage, arrival port/date, container, moved-via-CFS, delivery location/date, external condition, discoverer, etc.) — all form fields or document extractions. **Low overlap means the slots hold different values, not that the structure varies.**

**Decision: build a versioned, auditable clause library (not fine-tuning, not RAG-as-writer).**
- Fine-tuning transfers style, not facts — it would faithfully learn the corpus's own defects (including the misspelling and the §11.2 binding error), and with "no paid APIs" it would have to run locally and worse than a template drawn from the same data.
- RAG as report-writer risks cross-contamination — retrieved phrasing importing a fact from another shipment, very hard to catch at 76–87% surface similarity.
- **Retrieval as a precedent finder (Phase 2, not week 1–3):** given the current shipment's metadata, surface similar past reports as a ranked list of links for the surveyor to open — output is links, not prose, so hallucination surface is zero.

**Variation mechanisms a clause library actually needs** (all already present in the client's own reports):
1. **Conditional selection** on fact (e.g. sampling location: "inside the cold room" / "from the Container" / "inside the cold room and the container").
2. **Compositional assembly** — e.g. the defect list built from categories actually present, correct grammar for any count.
3. **Verbatim surveyor text** — the per-block `additional_text` escape hatch, inserted exactly as written, never rewritten.

Domain note: in insurance survey work, **consistent wording is a virtue** — insurers reading dozens of these a year expect the same structure; unexplained variation in legal phrasing is exposure, not polish.

---

## 11. Two Real Findings That Must Shape Validation

### 11.1 A naive "temperature excursion" detector would have inverted a real liability finding
One trip logged a mean of 0.2°C over 70 days but a maximum of 25.8°C recorded 4 minutes *after* the logger's stop time — the device warming up on a table after the container was opened for destuffing, not an in-transit event. A max(series) threshold rule would flag a severe excursion and blame the wrong party; the correct surveyor finding was "no substantial variation... during the entire sea transit," attributing the loss to physiological breakdown over storage time. **This is why automatic excursion/spike detection must never be built** — it produces a confidently wrong, deterministic answer, not a random one. If excursion analysis is ever added later, it needs voyage-phase segmentation from the B/L and an alarm band from the reefer manifest (not the logger), framed only as a review prompt.

### 11.2 A real delivered report contains a data-binding error — right numbers, wrong table
Prose said "320 pcs cut" and a specific breakdown, but the accompanying table was populated from the wrong spreadsheet sheet entirely (different totals, a missing row, values shifted into the wrong column). None of the numbers in the correct sentence appear anywhere in the table. This is the classic manual Excel→Word binding failure — and it is **exactly** what declared-source tables + locked computed cells (§10.7, §10.8) make structurally impossible. Two consequences: (a) this is the strongest argument for the whole platform; (b) **validation must never be "does it match the old report."** Validation means re-deriving each historical report from its sources and investigating every difference — some differences will be the tool catching a historical mistake, not a bug.

---

## 12. Technology Stack

| Layer | Use this | Notes |
|---|---|---|
| Backend | Python 3.11+, FastAPI | |
| Frontend | React + TypeScript + Vite + Tailwind | Offline-capable form is the hard part |
| Database | PostgreSQL | Block State in a JSONB column |
| Background jobs | Celery or RQ + Redis | A 300-photo report / 160-page PDF cannot run inside an HTTP request |
| File storage | Local filesystem or MinIO (S3-compatible), versioned | Never overwrite an original |
| Rich text editing | TipTap (ProseMirror) or Lexical | One small editor per paragraph block, **not** one page-wide contenteditable |
| Preview render | Server-rendered HTML, A4 page boxes | Edit mode |
| Proof render | LibreOffice headless → PDF → pdf.js | Exact, read-only |
| Read PDFs | pdfplumber (MIT) + pypdf (BSD) | |
| Merge PDFs | pypdf | For annexures |
| OCR (printed scans) | Tesseract or PaddleOCR (Apache-2.0) | Runs locally, no API |
| OCR (handwriting) | Local digit CNN on redesigned form; TrOCR (MIT) as fallback | CPU only |
| Image straightening | OpenCV `cv2.aruco` | For the redesigned tally form |
| Excel/CSV | pandas (BSD) + openpyxl (MIT) | |
| Identifier validation | Plain Python, no dependency | ISO 6346 container check digit; AWB mod-7 check digit |
| Money & percentages | `decimal.Decimal` | **Never `float`** |
| Build Word files | python-docx (MIT) + raw OOXML where needed | Template injection |
| Word → PDF | LibreOffice headless (MPL) | |
| Deployment | Docker + docker-compose | On client's domain — modest VPS or on-premises |

**Do NOT use:**
- ❌ **PyMuPDF / fitz** — AGPL-3.0; fine for a script, a licensing problem for a hosted web app. Use pdfplumber + pypdf.
- ❌ **docx2pdf** — drives a real MS Word install via COM; won't run on a Linux server. Use LibreOffice headless.
- ❌ **Any paid AI API** — client requirement is no paid APIs, everything local.
- ❌ **`float`** — for any number that appears in a report.

**Where the real recurring costs are:** storage (sample reports run 128–228 MB each; grows indefinitely with immutable photo originals), hosting, backups (non-negotiable for signed survey reports), and licensing (audit any new dependency — swapping an API fee for a licence problem, e.g. AGPL, is not a win). Compute is CPU-only, no GPU needed on the recommended path.

---

## 13. Project / Repo Structure

```
backend/
  app/
    main.py
    models/          # SQLAlchemy tables: report, asset, audit, template, clause
    blocks/          # one file per block type
      base.py        # Block base class + registry
      particulars.py
      table.py
      photo_plate.py
      reconciliation.py
      unit_group.py
      ...
    compute/
      arithmetic.py    # Decimal totals, percentages
      photo_ranges.py  # groups -> "(Photo Nos. 41 to 44)"
      annexures.py     # ID allocation + reference resolution
      rollups.py       # shipment-level totals across containers
    render/
      docx/            # Word renderers, one per block type
      html/            # preview renderers, one per block type
      template.py      # loads and injects into the .docx template
      chart.py         # rewrites the embedded chart workbook
      gate.py          # numeric traceability check
    ingest/
      spreadsheet.py
      pdf_text.py
      pdf_ocr.py
      handwriting.py
      instruments.py   # DeltaTrak FlashLink parser
      identifiers.py   # ISO 6346 + AWB check digits
    api/
frontend/
  src/
    pages/             # ReportList, ReportEdit, Preview
    components/
      form/            # form generated from the block list
      preview/         # one editable component per block type
      tables/          # grid with locked computed cells
      photos/          # drag-to-reorder tray
templates/
  mca-qc-v1.docx       # the real client report, content stripped
  mca-survey-v1.docx
```

**Governing rule:** for every block type there is one form component, one HTML renderer, one Word renderer. Adding a new block type should never require touching another block type.

---

## 14. Development Plan — Day by Day (3 Weeks / 15 Days)

### WEEK 1 — Build the engine
**Goal at end of week 1:** put data in via a form, click a button, get a correctly formatted Word file out. No preview/editing yet.

**Day 1 (morning) — Mine the report archive FIRST, before any app code.**
You'll be given ~400 (or ~100, per updated scope) of the client's past reports (50–90 GB). **Do not read them by hand** — write one throwaway script that walks the drive and produces:
1. **An inventory** — per file: report number, type (QC/survey), family, commodity, client, container count, photo count, page count, date → CSV.
2. **Which sections appear, in what order** — detect headings and record the sequence per report. **This is the single most valuable output** — it gives the real block sequences for the six templates instead of guessing.
3. **A sentence-frequency list** — every sentence, numbers/names/dates replaced with placeholders, grouped, counted → the wording/clause library. Top ~100 sentences cover most of every report.
4. **Defect categories used per commodity** — so table columns are configured from fact.
5. **An arithmetic check across all reports** — recompute every total/percentage and flag mismatches. Report this list separately — some are historical mistakes the client needs to know about before anyone else finds them.

Practical notes: extract text **once** into a cache and work off it; `.doc` (legacy binary) needs different handling than `.docx` (antiword vs python-docx/zip access); **de-duplicate** (match on report number + content hash, since drafts/duplicates inflate sentence frequency); **pick the template source from a recent report**, not an average (older letterheads differ); keep ~10–15 reports as a hand-checked reference set.

**Day 1 (afternoon) — Setup and database.**
- Repo, Docker compose (FastAPI + Postgres + Redis), CI running tests.
- Login/accounts for surveyors — email + password, sessions (keep simple).
- Create tables: `reports`, `assets`, `audit`, `templates`, `clauses` (see §9).
- Report numbering `M-<n>-<year>`, sequential per year, safe under concurrent requests.

**Day 2 — Block State and the arithmetic engine.**
- Pydantic models for block types; start with 5: particulars, narrative, measurements, table, fixed_text.
- Write `compute(block_state)` — the heart of the app.
- Arithmetic in `Decimal` only: row total = sum of row's category values; column total = sum down column; percentage = value/total × 100, `ROUND_HALF_UP`, 2 dp.
- **Write tests using the client's real numbers** (examples — must reproduce exactly):
  - Mandarin, count 55: 133+54+14+24+9 = 234; pct 56.84/23.08/5.98/10.26/3.84
  - Mandarin totals: 371+172+51+47+34 = 675; pct 54.96/25.48/7.56/6.96/5.04
  - Grapes (kg, 3 dp): 5.190+0.606+0.434 = 6.230; grand total 47.562/2.264/0.876 = 50.702; pct 93.81/4.46/1.73
- Note: table columns are **data**, not code — different commodities have different category counts/units; code must handle any number of columns and either unit.

**Day 3 — The Word template (start early, riskiest part).**
- Take a real client QC .docx, delete content, keep letterhead, header/footer, `PAGE x OF y` fields, fonts, table borders, chart, signature block.
- Load with python-docx, inject content in. **Do not rebuild the letterhead from scratch** — will cost two days and still not match.
- **The chart is the hard bit.** python-docx can't create charts. Open the docx as a zip, find `word/charts/chart1.xml` + its embedded `.xlsx`; rewrite the numbers there and the cached values in the chart XML — keeps a real, editable Word chart. If this takes more than a day, fall back to a PNG image and **tell the client before making that call.**
- Renderers for particulars, narrative, fixed_text.

**Day 4 — Excel/CSV import and the table block.**
- Upload .csv/.xlsx, parse with pandas/openpyxl.
- Column mapping screen: map sheet columns to block categories once per template, saved on the template.
- Read formula cells as **values**.
- Word renderer for table (computed totals/percentage rows) and measurements.

**Day 5 — Photos and the form.**
- **Connect the client's existing bulk photo uploader** — already built, just wire it in.
- Store every original byte-for-byte unchanged, SHA-256 recorded at upload; separate display/report copies; **never recompress or overwrite an original** (EXIF timestamps have been legal evidence in real cases).
- Extract/keep full EXIF.
- Photo series: several per report, each with label + source; **never merge or renumber across series**.
- Grouping UI: ordered tray, drag a divider to split into observation groups, type one observation per group.
- `photo_ranges.py`: span → `(Photo Nos. 55 to 59)`; pair → `(Photo Nos. 39 & 40)`; single → `(Photo No. 50)`. Recalculate on **every** read; assert contiguous, no gaps, every photo in exactly one group.
- Word renderer for photo_plate: 2-column table, image + caption per cell.
- Generate the form from the block list.

**✅ Week 1 done when:**
1. Archive mining done, and you can report: how many report types exist, which sections each uses, top ~100 sentences by frequency.
2. Can create a report, fill the form, import a spreadsheet, upload photos, download a `.docx`.
3. It opens in Word looking like a real client report (letterhead, fonts, table borders, chart, photo plates).
4. All 3 sample QC reports' numbers reproduce exactly through the arithmetic tests.
5. Deleting a photo automatically renumbers everything and fixes every text range.

---

### WEEK 2 — Preview, editing, go live
**Goal:** QC reports fully working and deployed on the client's domain, usable on a real job.

**Day 6–7 — HTML preview.**
- Server renders Block State to HTML in A4-sized page boxes using the report's fonts/table styles.
- **Critical:** the HTML renderer and the Word renderer must call the same `compute()`. If they compute separately, preview and download will one day disagree — that destroys trust in the tool.
- One HTML component per block type, mirroring the Word renderers.

**Day 8 — In-place editing.**
Edits change the data, not the document. Every edit is a PATCH to Block State → recompute → re-render affected blocks. Never edit the generated `.docx`.
- **Text:** TipTap editor per paragraph block (bold/italic/bullets only); mark `surveyor_edited`, log before/after to audit.
- **Tables:** input cells editable; **computed cells read-only, recompute live** — cannot be typed over. Rows addable/deletable/reorderable. Genuine overrides require a reason, logged.
- **Photos:** reorder/delete/replace/rotate/crop/move between groups; every number/range in text updates immediately. Crops/rotations to the report copy only, never the original.
- **Sections:** add/remove/reorder/duplicate here too.
- Autosave with optimistic concurrency (version number, reject stale writes). Named versions, revertible.

**Day 9 — Proof view, download, safety gate.**
- **Proof view:** real `.docx` through LibreOffice headless → PDF → pdf.js, read-only, pixel-exact. Two buttons: Edit view / Proof view.
- Download endpoint: `.docx` + `.pdf`.
- **Numeric traceability gate** before every download: extract every number/date/ID from the rendered doc, check each exists in Block State; if any can't be traced → **block the download**, show what failed. Write a test that deliberately injects an untraceable number and confirms it's caught.
- Outstanding items panel: unconfirmed items listed, blocks download until cleared.

**Day 10 — Document reading, validation, deploy.**
- Printed scans (invoice, B/L): OCR via Tesseract/PaddleOCR (no text layer at all, so OCR is the only route). B/L watermark needs adaptive thresholding. Show every extracted field next to its crop for confirmation. **Pre-fill only — the app must work fully with OCR off** (a dozen fields, two minutes to type).
- Dates: client invoice is DD/MM, temperature logger is MM/DD, in one shipment. Store ISO + source convention; confirm anything ambiguous (day ≤ 12).
- Temperature logger parser: regex against page 1 plain text; unit order detection per file; do NOT write automatic "temperature spike" detection (see §11.1).
- Handwritten tally sheets (fallback): sheet image + grid, cropped handwriting next to each read number, low-confidence cells highlighted and **block generation until confirmed**; read twice, flag disagreements.
- Rebuild the three sample QC reports from source files, compare to what the client issued, **investigate every difference** — "matches the old report" is not the pass condition; one real report has a table from the wrong sheet, and matching it would copy the mistake.
- Deploy to the domain, configure backups.

**✅ Week 2 done when:**
1. QC reports generate, preview, edit, and download — live on the client's domain.
2. Editing a table cell updates totals instantly; download matches preview.
3. Reordering photos fixes every text reference instantly.
4. The traceability gate blocks a deliberately corrupted report.
5. All three historical QC reports rebuilt, every difference explained in writing.

---

### WEEK 3 — Survey reports, multiple containers, air shipments
**Goal:** the full thing — all six report formats, multi-container support, tested against real cases, handed over.

**Day 11 — Easy blocks + sea/air support.**
- parties, attendance, timeline — repeating-row tables, quick to build.
- **Transport mode** set once per shipment (SEA/AIR), driving fields, timeline stages, wording (§6).
- Check digits (a couple of hours, pure functions, easy tests): ISO 6346 (container), AWB mod-7 check digit. **If a check fails, flag for confirmation — never auto-correct.**

**Day 12 — Reconciliation block.**
- Declared vs found weight; rows; formula selector; computed difference columns.
- **Formula chosen by the surveyor per weighing event, never guessed** (real example: three weighings of the same 6 containers, three different formulas — see §10.4).
- Air adds volumetric weight = (L×W×H cm)/6000, chargeable weight = max(actual gross, volumetric).
- **Never "fix" mismatches automatically** — show them, let the surveyor resolve (real example: 6×21,148=126,888 vs declared 126,891, accepted on purpose).

**Day 13 — `unit_group` — multiple containers in one report.**
- New block type holding child blocks, repeating once per container/ULD/pallet lot.
- Each unit gets its own particulars, tally table, weight reconciliation, observations, photo range, with identity in the heading — copy the client's exact existing format (see §7 numbering example).
- **Photo numbering — default to one shared series split into per-container ranges** (matches existing client practice); support separate-series-per-container as an option.
- **Shipment roll-up:** block with `scope: "SHIPMENT"` summing across units (client's report does this three times, once per weighing).
- **One container is just n = 1** — same code path, no special case for single-container reports.

**Day 14 — Annexures, machinery inventory, the six templates.**
- Annexures block: allocate IDs (A1…A6, B1…B6, C1…C6), resolve narrative references from the same list, merge attachment PDFs with pypdf, generate documentation list from the same source.
- ⚠️ `PAGE x OF y` counts report body only, not merged file (a real report says "Page 1 of 69" while the delivered PDF is 157 pages).
- Inventory block for machinery damage — nested package → part → damage, with part numbers/quantities. The fiddliest block; leave it last.
- **The six report formats** — saved block sequences (configuration, not code): see §8.
- Mode-aware wording, plus a reference table for notice periods and liability limits.
- ⚠️ **Never hardcode a legal figure** — hold as versioned reference data with an effective date, show the figure and source, make the surveyor confirm it before render.

**Day 15 — Validation and handover.**
- Rebuild the multi-container reports from source and check:
  - M-71: 6 containers, 3 weighings, 3 photo series (84/26/300), 18 annexures — per-container weights must sum to exactly 126,891 / 65,340 / 64,580 kg, giving shortages of nil / 61,551 / 62,311 kg.
  - M-244: 9 containers, 22 machinery packages with part-level damage.
- Fix whatever the surveyor asked for after seeing week 2's reports.
- Handover: deployment notes, backup procedure, how to add a new report type, training for surveyors.

**✅ Week 3 done when:**
1. All six report formats generate correctly.
2. A 6-container shipment produces one report with correct per-container sections, correct per-container photo ranges, correct shipment total.
3. Annexures merge in order with labels matching the text.
4. M-71 and M-244 rebuilt with every difference explained.
5. Deployed, backed up, documented, client trained.

---

## 15. Weekly v3.1 Addition Map (where the two new requirements land)

| Addition | Where | Effort |
|---|---|---|
| transport object, mode switch, carriage_units | Week 1, with the state model | Schema/form-field work, built in from the start |
| ISO 6346 and AWB check-digit validation | Week 1 | A few hours, pure functions with unit tests |
| unit_group block, per-unit headings/photo ranges | Week 1–2, alongside the photo-range solver | Range solver already segments a series; reused. n=1 is one code path |
| Shipment-level roll-ups (scope, rolls_up_from) | Week 2 | Aggregation over per-unit computed values |
| AWB field schema for extraction | Week 2, with B/L schema | A second field map on the same OCR path |
| Airport timeline vocabulary, air weight terms | Week 2 | Reference data + one computed column |
| Six report-format templates | Week 3, informed by corpus mining | Block sequences and clause selections — configuration |
| Mode-aware clause selection + liability/notice reference table | Week 3 | Data entry; **table contents are the client's professional call** |
| Multi-unit validation against M-71 (6 units) and M-244 (9 units) | Week 3 | Acceptance cases for §7 |

---

## 16. Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| Tally error reaches a signed report | Critical | Per-cell verification against crops; dual-pass disagreement; checksums; hard gate. Upstream: redesign the form |
| Fabricated/untraceable content in output | Critical | Provenance on every field; numeric traceability gate at download; no generative authoring |
| Confidential claim data leaving the premises | Critical | No external model calls; local models only; on-premises hosting preferred |
| Preview edit breaks arithmetic or provenance | High | Computed cells locked and recomputing; overrides require a reason and are flagged; edits patch state, never the document; audit records before/after |
| Surveyors do not adopt the structured form | High — largest project risk, non-technical | Make the form faster than Word for the surveyor's own purposes; pilot on live files in week 2; iterate before rollout. Degraded outcome is still photos+tables+arithmetic (~60% of value) |
| Expectation gap on who authors Cause of Loss | High | Settle in writing before start (§20) |
| Photo recompression destroys EXIF evidence | High | Immutable bit-exact originals + hashes; derived copies only; crops never touch originals |
| Silent date misparse (DD/MM vs MM/DD in one shipment) | High | ISO normalisation with source convention; confirm ambiguous dates |
| Wrong photo range after reorder | High | Ranges computed, never stored; re-derived on every mutation; contiguity assertions |
| Automated reconciliation "corrects" legitimate data | High | Advisory flags only; surveyor resolves |
| Excursion detector inverts a liability finding | High | Out of scope entirely (§11.1) |
| Storage growth outruns hosting (128–228 MB/report) | High | Size for years; on-premises with a large disk; retention policy |
| Block catalogue proves insufficient for some case | Medium | Phase 0 validates against ~100 reports before committing; additional_text escape hatch on every block; adding a block type is additive |
| Preview fidelity mistaken for exact | Medium | Two explicit modes; Proof mode is the genuine artefact, documented plainly |
| Chart cannot be generated | Medium | Resolve in week 1; rendered-image fallback |
| AGPL obligation on a web-deployed tool | Medium | Use pdfplumber/pypdf; audit licences |
| A wrong notice period/liability limit stated in an air report | Critical | Versioned reference data with effective date, never hardcoded; shown with source and confirmed by surveyor before render; recorded in audit trail |
| Photo ranges drift across unit boundaries in a multi-unit report | High | Ranges computed, never stored; contiguity/exhaustiveness asserted across the whole document; both numbering patterns explicitly declared per template; validated against M-71/M-244 |
| Shipment roll-up disagrees with per-unit figures | High | Roll-ups computed at render time from per-unit values, never stored/typed; M-71 three-weighing arithmetic is an acceptance case |
| Multi-unit reconciler "corrects" an averaged declared figure | High | Advisory only; the 126,888 vs 126,891 case is a regression test for *not* auto-resolving |
| Wrong transport-mode field set on a report (B/L fields on an air job) | Medium | Mode set once at report creation, drives the form; mode-inappropriate fields not rendered, not merely hidden |
| Container or AWB number mistranscribed | Medium | ISO 6346/AWB check-digit validation at entry; failure flagged for confirmation, never auto-corrected |
| Six formats diverge into six maintenance burdens | Medium | They're saved block sequences over one engine, not separate builds; corpus mining sets default contents |

---

## 17. Confidentiality and Data-Handling Rules (from commit #1)

What is sensitive: the client's **IRDAI licence number**, insurer names, policy numbers, insured values, consignees' commercial invoice values, vessel/party names, and at least one allegation against a named shipper.

**Rules:**
1. `.gitignore` the sample-data folder **before the first commit**. Real reports never enter the repo, not even temporarily.
2. **Test fixtures must be synthetic** — same shape, fake values (fake licence number, fake policy numbers, fake names). Real *arithmetic* (e.g. 133+54+14+24+9=234) is fine to keep; real *identities* are not.
3. **The IRDAI licence number goes in config**, not in code and not inside the `.docx` template — env var or a settings row. If it sits inside a committed template file, it is in git history forever.
4. **Redact before pasting anything into an AI coding tool.** Swap real names/numbers for placeholders.
5. **Add a pre-commit hook** that scans staged files for IRDA/licence-number patterns and known client/party names, and blocks the commit if found.
6. **Keep the repo private**, regardless of the above.
7. **Keep the archive on the machine you were given it on** — no personal storage, no cloud drives; delete the working copy when the project ends.
8. **Generated reports are client data too** — any real report the app produces during testing follows the same rules: not in the repo, not in a shared folder, not pasted anywhere.
9. **Git history keeps everything forever** — deleting a file in a later commit does not remove it from history or from any existing clone.
10. If something sensitive does get committed, **tell the client the same day** — cleaning git history gets much harder once others have cloned or the branch has been merged.

---

## 18. Deliverables Checklist

- [ ] Web application deployed on the client's domain, with user accounts for surveyors.
- [ ] Report generation engine producing Word (.docx) and PDF output matching the existing format — letterhead, fonts, table styles, chart, page numbering, photo plates.
- [ ] Browser preview with editing of text, tables, photos and sections, plus proof view and version history.
- [ ] Report-type templates for the client's main report products, as editable configuration.
- [ ] Input forms generated automatically from whichever sections a report type contains.
- [ ] Spreadsheet import with saved column mappings per report type.
- [ ] Document reader for invoices, B/Ls, packing lists, temperature-recorder files, with confirmation against source.
- [ ] Handwritten tally-sheet reader with cell-by-cell confirmation.
- [ ] Photo management — multiple sets, separate numbering, grouping, automatic ranges, originals preserved unaltered with checksums.
- [ ] Calculation engine: totals, percentages, weight reconciliation, unit conversion, transit durations.
- [ ] Annexure assembly with automatic labelling, referencing, PDF merging.
- [ ] Wording/clause library built from the client's own past reports, versioned and editable.
- [ ] Audit trail per report: who entered/changed each figure and when; what was extracted vs accepted.
- [ ] Redesigned tally form artwork for printing (pending client decision, §20).
- [ ] Deployment, backup setup, handover documentation, training for surveyors.
- [ ] Six report-format templates (General Cargo & Perishable Cargo, each Sea/Air, plus Perishable QC Sea/Air).
- [ ] Support for a single shipment document spanning multiple containers.

---

## 19. Not In Scope

- **Professional opinion.** The system assembles, formats, cross-checks findings — it never forms conclusions on cause of loss or liability. Those are surveyor selections rendered in house wording.
- **Automatic interpretation of instrument data.** Full stats + graph presented; whether a reading matters is the surveyor's judgement.
- **Signing and issue.** The system produces the document for signature; issuing remains the client's process.
- **Migration of past reports into the system as records.** The archive is read to build the wording library/templates, but old reports aren't loaded in as live records.
- **Integration with accounting, email, or claims systems.**
- **Changes to the existing bulk photo uploader**, beyond connecting it.
- **Excursion analysis with voyage-phase segmentation** (deferred, review-prompt-only, later phase).
- **A local digit classifier trained on accumulated verified sheets** (deferred).
- **Precedent finder** (deferred to Phase 2).
- **Offline phone app, template-editor UI** (good ideas, later, not now).

---

## 20. What To Have Ready Before Development Starts

*(Consolidated from "What We Need From You" and the roadmap's Phase 0 prerequisites.)*

| # | Item | Needed by |
|---|---|---|
| 1 | The client's **past reports archive** (the ~100–400 report corpus), so the dev team can mine block sequences, build the wording library, and see which report types to cover. This is the single highest-leverage input — nothing in weeks 1–3 works well without it. | Before start |
| 2 | **Clean Word originals** of one real QC report and one real survey report, to build the two DOCX templates from (letterhead, fonts, table styles, embedded chart). | Week 1, Day 3 |
| 3 | **One surveyor available** to test on live files and say what needs to change. | Week 2 onward |
| 4 | A decision on the **rounding convention** for percentages (e.g. force to sum to 100.00, or allow 99.99). | Week 1 |
| 5 | A decision on **which defect categories appear per commodity** in the report (vs. what the tally sheet records — some are merged/dropped). | Week 1 |
| 6 | A decision on **hosting**: the client's own office server vs. a hosted VPS (storage grows ~3 GB/month at current volume, before photo originals). | Week 1 |
| 7 | Access to / confirmation of the **existing bulk photo uploader**, so it can be wired in rather than rebuilt. | Week 1, Day 5 |
| 8 | Sample **spreadsheets** the client actually uses (tally sheets, weight slips, part lists) with live formulas intact, to design the column-mapping UI against real files. | Week 1, Day 4 |
| 9 | Sample **scanned documents** (invoices, bills of lading/air waybills, temperature-logger PDFs) including at least one watermarked and one handwritten example, to calibrate OCR/extraction. | Week 2, Day 10 |
| 10 | **Written agreement on the Cause-of-Loss boundary** — confirm the surveyor authors it via structured selections and the system never decides it. This is flagged as the one place expectation and deliverable could diverge; settle it in writing before coding starts, not after. | Before start |
| 11 | A decision on the **liability/notice-period reference table contents** (per transport mode) — the platform builds the confirmation mechanism, but populating actual figures (Hague-Visby limits, Montreal per-kg limits, notice periods) is the client's professional call. | Week 3, but flag early |
| 12 | A decision on whether to **redesign the pre-printed tally form** (recommended — collapses handwriting recognition to boxed-digit recognition). The software is built around whichever form is in use. | Week 1 decision point |
| 13 | **Legal/compliance sign-off** to move client data (the report archive) onto a development machine, with the confidentiality rules in §17 agreed and a pre-commit secret-scanning hook set up before the first commit. | Before start |
| 14 | Confirm the **6-report-format naming and grouping** (General/Perishable × Sea/Air, plus Perishable QC × Sea/Air) matches what the client actually wants to launch with, since templates are configuration but the initial default set should be right the first time. | Before start / Week 3 |

**The two things most likely to quietly eat the schedule if not flagged immediately (do not wait for the weekly check-in):**
- The Word chart injection taking more than a day.
- The letterhead not matching pixel-for-pixel in Word.
- Any of the sample report's historical numbers failing to reproduce exactly through the new arithmetic engine.

---

## 21. Weekly Check-in Protocol

At the end of each week, report:
- What is done and demoable.
- What slipped, and why.
- Anything in the risk register (§16) or critical rules that had to be worked around.

Report **immediately**, not at week end, if:
- The Word chart is taking more than a day.
- The letterhead won't match.
- Any sample report's numbers won't reproduce.

---

## Appendix A — Corpus Inventory Reference (what each sample file established)

| File | Established |
|---|---|
| Handwritten tally photo | Real difficulty of tally transcription: blank printed header fields, strikethroughs, ambiguous count codes, stray decimals, highlighter, skew, facing-page bleed, handwritten column headers |
| Tally spreadsheet (e.g. "16 Boxes.xlsx") | Percentages hardcoded not formulas; all arithmetic verified; source of the real §11.2 binding error |
| Grapes summary spreadsheet | Kg measurement to 3 dp; separate GRAPH sheet feeding the Word chart; live `=SUM()` formulas |
| Combined documents PDF (invoice + B/L) | Invoice and B/L have no text layer; B/L watermarked; DD/MM vs MM/DD date conflict; invoice arithmetic verified |
| Temperature recorder PDFs (annexures) | Page-1 machine-readable summary; alarm limits blank; both maxima fall in the final logging interval; per-file unit ordering differs |
| Grapes QC sample report | Kg-based, 3 categories, native Word chart, sequential captions; totals verified |
| Orange QC sample report | 5 categories incl. green patch, pieces-based, no caption text; inconsistent rounding |
| Mandarin QC sample report | Different 5 categories, no captions; totals verified |
| Kiwi survey report (legacy .doc) | Two dataloggers; penetrometer ranges per count per condition; verbal setpoint; 170 photos; the real §11.2 binding error |
| Zeeco survey report | 7-insurer panel; contiguous exhaustive photo ranges 1–70; field tests; no-loss/no-claim closure; IRDAI licence line |
| M-71 mis-declaration report | 3 photo series (84/26/300) with distinct provenance; 3 weighing events with 3 tare formulas; 18 annexures; 69-page body inside a 157-page merged file; EXIF as evidence; all arithmetic verified |
| M-244 machinery report | 9 containers, 22 packages, nested part-level damage inventory with part numbers; header/running-header mismatch (says PRELIMINARY vs FINAL) |

*The corpus available for review is one slice of the practice — mostly reefer perishables plus a few container/project-cargo cases. The 15-block model is designed for the full breadth of marine cargo surveying (§4) and must be validated against the client's full ~100-report archive during Phase 0 (Week 1, Day 1) before the six templates' default contents are finalised.*
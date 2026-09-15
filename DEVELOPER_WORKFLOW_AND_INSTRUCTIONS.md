# Marine Cargo Survey & QC Platform — Developer Workflow & Architecture Guide

**Purpose:** Clarify client input workflows, tally sheet standardization, narrative clause generation, chart/table requirements, domain terminology (e.g., fruit grades and counts).

> [!IMPORTANT]
> ### Immediate Priority Tasks for Developer:
> 1. **Analyze the General Cargo Archive (Gladstone Word Files):**
>    * Link: [Gladstone General Cargo Dropbox](https://www.dropbox.com/scl/fo/4xv879o7dj9e4a7f3k2dk/AGKBhgk2Waoc6LTVLBabTkA?rlkey=t8qcmxdklfzf9ght23oim34oe&dl=0)
>    * Analyze what text paragraphs and section structures actually exist in General Cargo reports. We need to figure out whether they follow the same categories (*Cause of Loss*, *Next Step*, *Documentation*) or use distinct headings, so we can build a system for the client to easily select, add, and edit these sections for General Cargo reports as well.
>    * Extract the recurring sentence patterns and block sequences from this archive so we can expand our Clause Library to cover general cargo damage (steel rust, impact, rough weather, water ingress).
> 2. **Investigate the 35-Report Gap in the Fruit Archive:**
>    * The Perishable Fruits folder contains **469 reports**, but our current `inventory.csv` only captured **434 reports** (35 missing).
>    * Please check why those 35 reports were omitted — were they legacy formats, parsing errors, or subdirectories? We need complete coverage across all available reports.
> 3. **Tally Sheet Workflow & Domain Decoders:**
>    * Read Sections 3 & 4 for critical domain knowledge (what `30 XF` and `33 PR` mean, why multiple rows exist for the same count, and how to structure the side-by-side Verification Workbench).

---

## 0. Project Data Sources & Reference Links

Please use the following shared resources as the primary data sources for training, mining, and testing:

| Dataset | Link | Contents & Role |
| :--- | :--- | :--- |
| **Perishable Fruits Reports (469 Reports)** | [Dropbox Link](https://www.dropbox.com/scl/fo/jztatx34b6at9gb2ngjgr/ALa0c3FKZvtOrtosHdADIkY?rlkey=1jji73igxtj760oofk7ywwjjg&dl=0) | 469 Word/PDF reports for fruit QC & surveys (Apple, Kiwi, Citrus, Grapes). Used to mine `perishable_fruits_output`. |
| **General Cargo Reports (Gladstone Word Files)** | [Dropbox Link](https://www.dropbox.com/scl/fo/4xv879o7dj9e4a7f3k2dk/AGKBhgk2Waoc6LTVLBabTkA?rlkey=t8qcmxdklfzf9ght23oim34oe&dl=0) | Container damage, steel coils, machinery, project cargo, heavy weather, shortages. **Must be mined next.** |
| **Tally Sheets & Field Sheets** | [Google Drive Link](https://drive.google.com/drive/folders/1KamSsXIbYoapTYW3JKijYtJRsU-T4CsY) | Real-world handwritten tally sheet scans and photos used to test and refine the Tally Verification Workbench. |

---

## 1. What We Ask From the Client (Input Breakdown)

The surveyor collects five categories of information during an inspection. The application must ingest these smoothly without requiring the surveyor to re-type existing data:

### A. Survey Photographs
* **Format:** JPEG / PNG from mobile phones or digital cameras.
* **Volume:** Typically 30 to 150+ images per report; up to 300+ in multi-container general cargo cases.
* **Metadata:** Contains critical EXIF timestamps and camera metadata (which serve as legal evidence in cargo dispute claims). **Never recompress or strip EXIF.**
* **Multiple Series:** Often contains photos from different sources (e.g., *Our Survey Photos*, *Consignee's CHA Photos*, *Shipper's Load Port Photos*). Each series must maintain its own independent numbering domain.

### B. Tabular Cargo Data (Tally)
* **Primary Path:** Excel (`.xlsx`) or `.csv` files prepared by the cold storage or surveyor. Contains carton counts, weight figures, and defect counts.
* **Fallback Path:** Photographs of handwritten spiral-notebook tally sheets taken on-site inside cold stores or CFS yards. *(Note: Tally sheets exist for perishable fruit surveys; general cargo relies on weighbridge slips and B/L packing lists).*

### C. Scanned Shipping Documents
* **Format:** Scanned PDFs or images.
* **Sea Shipments:** Bill of Lading (B/L), Commercial Invoice, Packing List.
* **Air Shipments:** Air Waybill (AWB - Master/House), Commercial Invoice, Packing List.

### D. Temperature Logger Data (Reefer Cargo)
* **Format:** PDF or CSV export from portable dataloggers (e.g., DeltaTrak FlashLink, Escavox, Sensitech).
* **Contents:** Page 1 summary statistics (trip number, duration, max/min/avg/MKT temperatures) + multi-thousand time-series temperature points.

### E. Surveyor Field Inputs (The Web Form)
* Facts no document provides:
  * Who instructed the survey and date/channel of instruction.
  * Attendance register (names, designations, parties represented).
  * Milestones & dates (discharge, destuffing, inspection).
  * Verbal statements made by parties on site.
  * Physical measurements: pulp temperature (°C), Brix (sugar content %), penetrometer firmness (LBS).
  * Observations on container condition, door seals, and packaging.

---

## 2. Where & How We Use Client Inputs (Data Flow)

| Client Input | Ingestion Method | Where It Goes in `block_state` | Output in Finished Report |
| :--- | :--- | :--- | :--- |
| **B/L / AWB Scan** | Classical OCR (Tesseract/PaddleOCR) + regex key-value extraction | `particulars` block (B/L no., vessel, voyage, container nos., seal nos., declared weights, ports) | Report Header & Particulars Table |
| **Commercial Invoice** | Classical OCR + regex pattern | `particulars` block (Invoice no., date, commercial value, currency) | Particulars Table |
| **Excel / CSV Tally** | `pandas` / `openpyxl` with column mapping | `table` block (categories: sound, soft, rotten, etc.) | Defect Breakdown Table + Defect Bar Chart |
| **Handwritten Tally** | Tally Verification Workbench | `table` block | Defect Breakdown Table + Defect Bar Chart |
| **Logger PDF** | Text extraction (`pdfplumber`) / regex on Page 1 | `instrument` block (trip no., logger model, min/max/avg stats, timeseries points) | Datalogger Summary Table + Temperature Line Graph |
| **Photos** | Bulk uploader, SHA-256 hash, EXIF preservation | `photo_plate` block (grouped into observation sets) | 2-Column Photo Plates with dynamic caption numbers |
| **Surveyor Selections**| Dynamic Form (dropdowns & structured pickers) | `narrative` blocks (`cause_of_loss`, `next_step`), `timeline`, `attendance` | Legal narrative paragraphs, timeline, signature block |

> [!IMPORTANT]
> **Pre-Fill Assist Rule:** OCR on shipping documents (B/L, Invoices) is strictly a **pre-fill assist**, never autonomous truth. The UI must show extracted values with a preview crop for quick surveyor confirmation. If OCR is disabled, manual typing of these 6–8 fields takes under 2 minutes.

---

## 3. Domain Knowledge: Fruit Tally Sheets, Calibers, & Grades

When reviewing handwritten tally sheets (e.g., `WhatsApp Image 2026-08-25 at 6.27.49 PM.jpeg` or the samples in the Google Drive folder), you will encounter notations that look confusing at first glance:

```text
Row 1: | 30 XF | Sound: 72 | Soft: 20 | Skin Disorder: 12 | Rotten: 7 | Butterfly: 0 |
Row 2: | 30 XF | Sound: 73 | Soft:  0 | Skin Disorder: 17 | Rotten: 5 | Butterfly: 0 |
Row 3: | 33 XF | Sound: 84 | Soft:  5 | Skin Disorder:  4 | Rotten: 1 | Butterfly: 10 |
...
Row 9: | 33 PR | Sound: 89 | Soft:  9 | Skin Disorder:  4 | Rotten: 0 | Butterfly: 1 |
```

### What These Codes Mean:
1. **The Numbers (30, 33, 36, 49):**
   * This is the **Fruit Count** (Caliber/Size). In the fruit trade, "Count" is the number of fruits packed per standard carton/tray.
   * **Lower count = Larger fruits** (Count 30 has 30 large pieces per box).
   * **Higher count = Smaller fruits** (Count 49 has 49 smaller pieces per box).
2. **The Letters (`XF`, `PR`):**
   * These are international **Quality Grades**:
     * **`XF` = Extra Fancy** (highest export grade).
     * **`PR` = Premium** (or Producer/Standard grade).
   * Therefore, `30 XF` = *Count 30 fruit of Extra Fancy quality*.
3. **Why are there multiple rows for the same count (e.g., two rows of `30 XF`)?**
   * When inspecting a container of 2,400 cartons, surveyors pull a sample (e.g., 16 cartons total).
   * **Each row represents ONE physical sample box opened and inspected!**
   * Row 1 is Box #1 of Count 30 XF; Row 2 is Box #2 of Count 30 XF.
   * In the final report (as seen in `16 Boxes.xlsx`), these sample boxes are aggregated under `"Count 30: 2 boxes opened, Total Sound: 145, Total Soft: 20..."`.
   * **This is not a duplicate or OCR glitch.** The data model must expect multiple rows with the same count/grade identifier.

---

## 4. Handling Non-Standardized Tally Sheets & The Verification Workbench

### The Core Principle:
**We cannot just dump a raw tally photo into an OCR engine and expect an autonomous final table.**
* Surveyors write in spiral notebooks with skew, shadows, and ink bleed.
* Overwritten numbers (e.g. `7-20`), strikethroughs, and abbreviations will cause even high-accuracy OCR to generate wrong numbers.
* In an insurance survey, a single wrong digit changes the financial loss calculation.

### The Solution:

#### 1. Define the Table First (Commodity Archetypes)
Instead of asking OCR to guess table headers, the system loads the columns based on the selected commodity from `tools/perishable_fruits_output/template_archetypes.json`:
* **Apples:** Sound, Russet, Bruised, Damage, Shriveled, Rotten Spot.
* **Kiwi:** Sound, Soft, Skin Disorder, Rotten, Butterfly.
* **Citrus:** Sound, Soft, Green Patch, Puffed Fruit, Rotten.
* **Grapes:** Sound, Soft, Rotten, Stem Crack (in **Kg**, not pieces).

If the tally contains additional defects (e.g., *Butterfly* or *Skin Disorder*), the surveyor can either retain them or map them to the core claim categories (*Sound*, *Soft*, *Rotten*) via a quick dropdown.

#### 2. The Verification Workbench UI (Side-by-Side Review)
The user interface must present a **Verification Workbench**:
* **Left Pane:** The high-resolution image of the tally sheet.
* **Right Pane:** The editable table grid.
* **Synchronized Cell Cropping:** When the surveyor focuses on a specific cell (e.g. Row 2, Rotten), the left pane automatically zooms in and highlights the cropped bounding box of the handwriting for that cell.
* **Live Row Checksums:** The table validates `Sound + Soft + Rotten + Defects = Stated Row Total`. If the numbers do not add up, the row highlights in red, making validation take 1 to 2 minutes with zero errors.

#### 3. The Hybrid Transcription Approach
```
[Handwritten Tally Photo]
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│ Candidate Extractor (Local OCR / Vision Model Draft)        │
│ Proposes initial candidate numbers and cell bounding boxes  │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                 VERIFICATION WORKBENCH UI                   │
│                                                             │
│   [Cropped Handwriting Snippet]  ◄──►  [Editable Cell]      │
│   (Zoomed into focused cell)           (Live Row Checksum)  │
└─────────────────────────────────────────────────────────────┘
          │ (Surveyor confirms/corrects in 1-2 minutes)
          ▼
   [Block State] (100% Verified Legal Data)
```

> [!NOTE]
> **Scope for Developer Discussion:**
> * We are open to exploring a **Hybrid Approach**: using an assistive multimodal model (such as a free-tier Gemini Vision call or local TrOCR) solely to generate the initial candidate numbers and bounding boxes for the workbench.
> * If you have an alternative or better idea for table detection, cell cropping, or grid alignment, please propose it so we can discuss and finalize the approach together.

---

## 5. Analyzing General Cargo & Mining Legal Narratives

### How General Cargo Compares to Perishables
General Cargo removes the two hardest challenges in the project:
1. **NO Handwritten Fruit Tally Sheets:** Nobody opens a container of steel coils or industrial machinery to count sound vs. rotten fruits. Instead, General Cargo uses a **Weight Slip** (computerized weighbridge printout showing: *Gross Weight − Tare Weight = Found Net vs. B/L Weight*) or a **Part Damage List**. That is a straightforward 4-row math comparison.
2. **NO Temperature Dataloggers:** Steel, coils, and machinery travel in dry containers, not reefers. There are no logger PDFs, no 4-minute time intervals, and no temperature graphs.
3. **ZERO Charts:** General cargo reports contain no bar charts or pie charts (`M-66` and `M-71` have zero charts). Damage is documented strictly with photographs and weight reconciliation tables.

**What Inputs Does General Cargo Take?**
* **Survey Photographs:** Same photo uploader and 2-column numbered photo plates as fruits.
* **Shipping Documents:** Bill of Lading, Commercial Invoice, Packing List (same as fruits).
* **Weight Slips or Part Damage Lists:** Computerized weighbridge slips instead of fruit tallies.
* **Field Inspection Observations:** Container condition, door seals, lashing, and cargo discrepancy notes.

### The Clear Mindmap: One Engine Composed of Blocks
The architecture uses a **Block Model** so that we never build two separate systems:

```text
Perishable Fruit Survey:
[Particulars] ➔ [Attendance] ➔ [Timeline] ➔ [Fruit Tally Table] ➔ [Temp Logger] ➔ [Photos] ➔ [Cause/Next Step]

General Cargo Survey:
[Particulars] ➔ [Attendance] ➔ [Timeline] ➔ [Weight Reconciliation] ➔ [Photos] ➔ [Cause/Next Step]
```
It is the **exact same engine**. When the surveyor clicks "General Cargo", the template simply hides the Fruit Tally & Logger blocks and loads the Weight Reconciliation block!

---

### Action Item: Detailed Analysis & Extraction of the Gladstone General Cargo Archive
We need a thorough analysis and extraction of the Gladstone General Cargo archive:
* Dataset: [Gladstone Word Files Dropbox](https://www.dropbox.com/scl/fo/4xv879o7dj9e4a7f3k2dk/AGKBhgk2Waoc6LTVLBabTkA?rlkey=t8qcmxdklfzf9ght23oim34oe&dl=0)

#### Questions & Objectives for the Developer:
1. **Analyze the Document Sections & Text Patterns:**
   * In Perishable Fruits, reports contain dense text primarily inside **"Cause of Loss"**, **"Next Step"**, and **"Documentation"** (along with standard particulars and defect observations).
   * **What kind of text and sections actually appear in General Cargo reports?**
     * Are they categorized under the same headings (*Cause of Loss*, *Next Step*, *Documentation*)?
     * Or do they use distinct section headings (e.g., *SURVEY FINDINGS*, *CONDITION OF CONTAINERS*, *EXTENT OF DAMAGE*, *CARGO DISCHARGE & STOWAGE*, *REMARKS / RECOMMENDATIONS*)?
2. **Determine Report Classifications for General Cargo:**
   * Does General Cargo also fall into **Preliminary Survey vs. Final Survey vs. QC Report**?
   * Or does General Cargo have specific survey forms (e.g., *Damage Survey Report*, *Certificate of Survey*, *Lashing & Securing Survey*, *Container Condition Survey*)?
   * How should the report selection workflow accommodate a surveyor creating a General Cargo case?
3. **Extract Sentence Frequencies & Block Sequences:**
   * Extract the recurring sentence patterns and block sequences from the Gladstone archive so we can build a **Clause Library for General Cargo** (covering steel coils, machinery breakage, sea water ingress, container rain/condensation, lashing failures, and shortages), just as we did for Perishable Fruits.
4. **Investigate the 35-Report Gap in Perishable Fruits (469 vs. 434):**
   * The Perishable Fruits Dropbox folder contains **469 reports**, but the current `inventory.csv` only lists **434 reports** (35 reports were omitted).
   * Please investigate why those 35 reports were not processed — were they skipped due to parsing errors, unhandled formats (e.g., legacy `.doc` vs. `.docx`), corrupted files, aggressive de-duplication, or subdirectories? We need complete coverage across all available reports.

---

### Report Types & Configurations:

The UI must allow the surveyor to select the report structure at the start:

```
Report Creation Options:
├── Report Family:
│   ├── QC Report (In-House Quality Inspection — consignee-facing, defect data only, no liability)
│   └── Survey Report (Insurance & legal claim report)
│       ├── State: Preliminary Survey Report (Issued immediately; reservation clause)
│       └── State: Final Survey Report (Complete cause & liability analysis)
└── Transport Mode:
    ├── Sea Shipment (B/L, containers, vessel/voyage, port timeline)
    └── Air Shipment (AWB, ULD/pallets, flight/date, airport timeline)
```

### How "Cause of Loss" & "Next Step" are Generated:

Our mining shows that **80% to 98% of narrative text is identical legal boilerplate**. Narrative is therefore powered by a **Clause Library with structured pickers**:

1. **"Cause of Loss":**
   * The surveyor selects from standardized industry cause patterns:
     * *Perishables:* Physiological breakdown / senescence; temperature excursion; pre-harvest disease.
     * *General Cargo:* Sea water ingress; condensation / container rain; rough weather / lashing failure; forklift / handling impact.
   * Selecting a cause populates the canonical legal wording into the block.
   * **In-Place Editing:** The surveyor can edit the text directly in the HTML preview (via TipTap), and an **"Additional Observations"** escape hatch allows custom notes to be inserted verbatim.
2. **"Next Step":**
   * Surveyor selects standard procedural checkboxes (e.g., *Notice of claim to carrier within statutory period*, *Segregation of damaged cargo*, *Joint survey held with P&I surveyor*).
   * Inserts the standard legal advice text.
3. **"Documentation" (Annexure Schedule):**
   * Automatically compiled from uploaded annexures (B/L, Invoice, Logger Report, Photo Plates).

---

## 6. Audit of Charts & Reference Tables

### Scripting Instruction:
Please run a quick audit script across both archives (Perishables and Gladstone) to verify all chart and table types present in the past reports.

### Architecture Clarification:
Our analysis indicates that survey reports use a **closed, finite set of tables and charts**:

#### The 4 Tables:
1. **Particulars Table:** Key-value pairs (Vessel, B/L, Containers, Cargo, Consignee, Values).
2. **Defect Breakdown Table:** Grid of counts/sizes vs. defect categories with computed totals and percentages.
3. **Weight Reconciliation Table:** Formula comparison (Declared Gross vs. Weighbridge Gross minus Tare = Difference / Shortage).
4. **Damage Inventory Table:** Hierarchical item damage listing (Package → Item → Part No. → Damage Qty & Nature) for machinery and project cargo (e.g., M-244).

#### The 2 Charts:
1. **Defect Percentage Chart (Bar/Column):** Visualizes the Defect Table row totals (% Sound vs. % Defects).
2. **Temperature Logger Graph (Line Chart):** Visualizes time-series temperatures from the logger file.
3. *General cargo reports contain no charts.*

**Rule:** Charts and tables are pre-wired to their respective blocks (`table` block gets Defect Chart, `instrument` block gets Logger Graph). There is no need for an open-ended custom chart builder.

---

## 7. Developer Action Checklist

1. [ ] **Analyze & Extract Gladstone General Cargo:** Inspect the Gladstone archive to identify sections, narrative categories, and report formats for general cargo, and extract sentence frequencies and block sequences.
2. [ ] **Investigate 35-Report Gap in Fruits Archive:** Determine why 35 reports were omitted from the 469 Perishable Fruits folder (434 in current inventory) and ensure full coverage.
3. [ ] **Build Verification Workbench UI:** Implement the side-by-side verification interface with synchronized cell-crop zooming and live row checksum validation.
4. [ ] **Incorporate Fruit Calibers & Grades:** Update tally parsing models to handle counts (`30`, `33`, etc.) and grades (`XF`, `PR`) as multiple sample-box rows.
5. [ ] **Evaluate Hybrid Tally OCR:** Review the trade-offs of using an assistive vision model draft pass vs. pure local OCR within the Verification Workbench, and discuss.
6. [ ] **Wire Report Types in UI:** Ensure creation flow supports Family (`QC_REPORT` vs `SURVEY_REPORT`), State (`PRELIMINARY` vs `FINAL`), and Mode (`SEA` vs `AIR`).


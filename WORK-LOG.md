# Zyrodev Engineering Work-Log & Incident Diagnostics

## Date: 2026-10-06
## Task: Paragraph 3 (Cause of Loss & Temperature Recorders) Integration Testing

---

### 1. Incident Overview (Report M-1-2026 Apple)
During local acceptance testing on an Apple survey report (`M-1-2026`), the surveyor identified three critical issues:
1. **Temperature Graph Dimensions:** The chart image below the vertical recorder table is excessively small (shrunk to a tiny thumbnail) instead of having a readable width matching the condition found chart ("THE CONDITION FOUND OF <Fruit name> FRUITS").
2. **Missing Preamble in A4 HTML Preview:** The preamble (Carriage Instructions & Recorder Intake) visible in the Form Editor does not appear in the A4 HTML Preview tab.
3. **Missing Temperature Table & Graphs in A4 HTML Preview:** Neither the 2-column parameter/value table nor the temperature graphs appear in the A4 HTML Preview tab.

---

### 2. Root Cause Analysis

#### A. Issue 1: Graph Sized Too Small in Form Editor Card
- **File:** `frontend/src/components/preview/blocks/RecordersBlock.tsx` (Lines 124–130)
- **Mechanism:**
  - The chart `<img>` element was assigned:
    ```tsx
    className="max-h-[250px] w-auto max-w-full object-contain border border-slate-300 rounded bg-white shadow-xs"
    ```
    inside a container wrapped in `max-w-xl mx-auto flex justify-center`.
  - The extracted PDF datalogger graph images have vertical margins and an aspect ratio close to 4:3.
  - Constraining the height strictly to `max-h-[250px]` forces the browser's aspect-ratio calculation to shrink the width to ~300px.
  - In a card where the summary table spans the full container width (~1000px in the Form Editor), a 300px wide graph appears as an unreadable thumbnail.
- **Reference Standard:**
  - `FindingsChart.tsx` (Survey findings in graph) renders with:
    ```tsx
    style={{ maxWidth: '16cm', height: 'auto', display: 'block' }}
    ```
    This spans a comfortable 600px–650px (matching standard A4 margins), making grid lines and timestamps clear and legible.
- **Identified Remedy (Pending CTO Confirmation):**
  - Adjust `RecordersBlock.tsx` image container to match the Findings chart width (`max-w-[650px]` or `max-w-[16cm]` with `w-full h-auto`), removing the restrictive 250px height cap.

---

#### B. Issues 2 & 3: Preamble and Temperature Recorders Missing in A4 HTML Preview
- **Files:**
  - `frontend/src/pages/ReportForm.tsx` (Line 374)
  - `frontend/src/components/preview/ReportPreview.tsx` (Lines 374–384 & 422–430)
  - `frontend/src/components/preview/blocks/NarrativeBlock.tsx` (Lines 630, 723, and 812–856)
- **Mechanism:**
  1. In `ReportForm.tsx`, clicking the **A4 HTML Preview** tab switches `activeTab` to `'preview'`, which renders `<ReportPreview editable={true} onBlockChange={handleBlockChange} />`.
  2. In `ReportPreview.tsx`:
     - Paragraph 3 narrative block is rendered as:
       ```tsx
       <NarrativeBlock
         block={b}
         onChange={onBlockChange}
         editable={editable} /* evaluates to true */
         clauseContext={clauseContext}
         isFormEditor={false}
         recordersBlock={recordersBlock}
         reportId={report?.id}
       />
       ```
     - Standalone `temperature_recorders` block is suppressed when Cause of Loss is present:
       ```tsx
       if (hasCauseOfLoss) return null;
       ```
  3. In `NarrativeBlock.tsx`:
     - Line 630 evaluates: `if (editable && onChange)` -> **TRUE** (since `ReportPreview` allows inline editing).
     - Line 723 checks:
       ```tsx
       {isFormEditor && isCauseFruit && isCauseOfLoss && currentCondition !== 'no_recorder_data' ? (
       ```
     - Because `isFormEditor` is **FALSE** in `ReportPreview`, this check fails!
     - As a result, execution falls through to line 812:
       ```tsx
       /* Standard single textarea editor (used for other sections or when no recorder data) */
       ```
     - This fallback renders **only** `<textarea value={text} />` (which is `additional_text` / liability assessment).
     - It completely omits the `preamble` section.
     - It completely omits the embedded `RecordersBlock` (summary table and graph).
  4. In the bottom "Preview Mode" branch (Line 899: `/* Preview Mode */`), embedding logic exists:
     ```tsx
     {preamble && <p className="whitespace-pre-line">{renderFormattedText(preamble)}</p>}
     {recordersBlock && <RecordersBlock block={recordersBlock} reportId={reportId} hideTitle={true} />}
     ```
     However, this branch is unreachable when `editable={true}` is passed by `ReportPreview`.
- **Status of Backend DOCX / HTML Generation:**
  - In `backend/app/render/docx/engine.py` and `backend/app/render/html/engine.py`, the backend engines already have the logic to render `preamble`, embed `recorders_block`, and render `additional_text` when `block_state` is saved.
  - However, because the surveyor tests and verifies via the in-browser A4 HTML Preview canvas first, the disappearance of these elements on screen makes the preview incomplete.
- **Identified Remedy (Pending CTO Confirmation):**
  - Refactor `NarrativeBlock.tsx` so that when rendering Paragraph 3 Cause of Loss for curated fruits:
    - **In Form Editor (`isFormEditor={true}`):** Render the interactive dual-textarea with pill switches and format buttons.
    - **In A4 HTML Preview (`isFormEditor={false}`):** Render the full document flow:
      1. Section Heading: `PARAGRAPH 3: CAUSE OF LOSS`
      2. Preamble paragraph (with inline edit capability or styled text)
      3. Embedded Temperature Recorders (2-column vertical table + wide chart)
      4. Cause of loss and liability assessment paragraphs (with inline edit capability)

---

### 3. Resolution & Implementation (Completed)
- [x] **Graph Sizing Fix:** Updated `RecordersBlock.tsx` image container to `style={{ maxWidth: '16cm' }}` with `w-full h-auto` and removed the restrictive `max-h-[250px]` cap. Now matches `FindingsChart.tsx` standard.
- [x] **DOCX & Server HTML Alignment:** Updated `backend/app/render/docx/engine.py` (width `15.0cm`) and `backend/app/render/html/engine.py` (`.chart-container img, .recorder-chart img` with `max-width: 16cm; height: auto`).
- [x] **A4 HTML Preview Synchronization:** Refactored `NarrativeBlock.tsx` so that when `isFormEditor={false}` (A4 HTML Preview mode), it renders:
  1. Preamble paragraph (with borderless in-place editing)
  2. Embedded `RecordersBlock` (authentic 2-column parameter/value summary table + wide temperature graph)
  3. Post-graph cause of loss and liability assessment paragraphs (with borderless in-place editing)
- [x] **Prop Propagation:** Passed `onRecordersChange={onBlockChange}` to `NarrativeBlock` in `ReportPreview.tsx`.
- [x] **Temperature Graph Checkbox Scoping:** Added `isFormEditor` prop to `RecordersBlock.tsx` (default `false`). The checkbox *"Include temperature graphs paired with container summary in the report"* is now rendered strictly inside the Form Editor (`isFormEditor={true}`) and is completely hidden in A4 HTML Preview, Print, and PDF views.
- [x] **Verification:**
  - `npm run build` in `frontend/` succeeds with 0 errors.
  - Python test suite (`.venv\Scripts\python.exe -m pytest`) passes 100% (46 passed, 0 failed).

---

## 4. Architectural Plan: Paragraph 4 (Next Step) Correlation

### A. Problem Statement & Empirical Grounding
Survey reports in `Ltst rprts` (M-160 to M-168) exhibit an exact correlation between the **Cause Condition in Paragraph 3** and the **existence and content of Paragraph 4**:
1. **`no_recorder_data` (M-161, M-162, M-163, M-164):** 100% of reports have an explicit `PARAGRAPH 4: NEXT STEP` recommending immediate salvage sale and advising consignees to pursue responsible parties directly.
2. **`cold_chain_complied` (M-165, M-166):** 100% of reports omit the standalone `PARAGRAPH 4` heading, because the loss mitigation advice is already woven into the concluding sentence of Paragraph 3's *Proximate Cause* assessment.
3. **`carrier_breach` (M-160, M-167, M-168):** 100% of reports have `PARAGRAPH 4: NEXT STEP`, bifurcated between:
   - *Commercial Salvage / Prompt Sale* (M-167, M-168 Grapes)
   - *Total Loss / Supervised Bio-Destruction* with APMC disposal certificate (M-160 Plum)

### B. Correlation Decision Matrix
| Paragraph 3 Condition | Paragraph 4 Status (`included`) | Action Default | Standard Verbiage |
| :--- | :---: | :--- | :--- |
| **`no_recorder_data`** | `true` (Visible) | `prompt_sale` | *"To mitigate losses from the damaged [Fruit] fruits, we advised the Consignees to sell them immediately. Consignees are requested to pursue any claims-related matter directly with the responsible parties."* |
| **`cold_chain_complied`** | `false` (Omitted by default) | `integrated_p3` | Omitted as standalone heading (mitigation sentence is in Paragraph 3). If surveyor manually toggles `included: true`, populates with: *"As an act to mitigate the loss, we advised the consignees to sell the cargo as soon as possible to avoid further damages to [Fruit] fruits."* |
| **`carrier_breach`** | `true` (Visible) | `prompt_sale` (Default) or `bio_destruction` | **Option A (Prompt Sale):** *"As an act to mitigate the loss, we advised the consignees to sell the cargo as soon as possible to avoid further damages to [Fruit] fruits."*<br>**Option B (Bio-Destruction):** *"As the entire consignment is severely decayed, mold-infested, completely unfit for human consumption, and devoid of any commercial salvage value, the Consignees are requested to arrange for supervised bio-destruction and submit the official Municipal/APMC Disposal Certificate along with comprehensive photographic and video evidence for our perusal and file records."* |

### C. Component & Code Changes (Plan Only)

#### 1. Template Layer: `frontend/src/utils/clauseContext.ts`
- Implement `buildParagraph4NextStep(clauseContext: ClauseContext, condition: CauseCondition, action: 'prompt_sale' | 'bio_destruction'): string`:
  - Returns the exact fruit-capitalized client template based on selected action.
  - Exposes helper `detectNextStepAction(text: string): 'prompt_sale' | 'bio_destruction'`.

#### 2. Cross-Block Synchronization: `frontend/src/pages/ReportForm.tsx`
- When switching the condition in Paragraph 3 (`b_cause`):
  - If switched to `cold_chain_complied`: Automatically set `b_next_step.included = false` (unless the surveyor has explicitly edited custom text into it).
  - If switched to `carrier_breach` or `no_recorder_data`: Automatically set `b_next_step.included = true`. If `b_next_step.additional_text` is empty or matches an unedited default, update it with the matching template.

#### 3. Form Editor UI: `frontend/src/components/preview/blocks/NarrativeBlock.tsx`
- For blocks where `sectionSlug === 'next_step'` or `block.id === 'b_next_step'`:
  - When in Form Editor (`isFormEditor={true}`):
    - Render a 2-button segmented pill selector:
      - `[ ⚡ Prompt Sale / Loss Mitigation ]`
      - `[ 🗑️ Total Loss / Supervised Bio-Destruction ]`
    - Clicking the pill cleanly replaces the template text without losing custom edits if confirmed.
  - When in A4 HTML Preview (`isFormEditor={false}`):
    - If `included !== false` and text is present: renders cleanly as a formatted paragraph (with in-place editing).
    - If `included === false`: completely suppressed from the A4 canvas and printable output.

#### 4. Backend Defaults: `backend/app/seeds/defaults.py`
- Pre-populate `b_next_step` on report creation with the default prompt-sale text so newly generated reports start fully coherent.

#### 5. Backend DOCX & HTML Engines (`docx/engine.py` & `html/engine.py`)
- Verify that `is_included(b_next_step)` correctly suppresses the heading when `included: false`, preventing any empty orphan headers in generated Word or HTML documents.

### D. Verification Criteria
1. Switching to `Cold-Chain Complied` turns off Paragraph 4 in preview and export, matching M-165 & M-166.
2. Switching to `Carrier Breach` enables Paragraph 4 with the Prompt Sale / Bio-Destruction toggle.
3. Switching to `No Recorder Data` enables Paragraph 4 with the 2-sentence prompt-sale and claims-direction clause.
4. `vite build` succeeds with 0 errors.
5. All backend pytest suites pass with 0 regressions.

---

## 5. Implementation & Verification Complete (2026-10-06)

### A. Summary of Delivered Work
1. **Paragraph 4 Template Builders & Detection (`frontend/src/utils/clauseContext.ts`):**
   - Added `NextStepAction` (`'prompt_sale' | 'bio_destruction'`).
   - Implemented `buildParagraph4NextStep(clauseContext, condition, action)`:
     - Apple & Pear: 2-sentence prompt sale + responsible party claims guidance.
     - Grapes, Plum, Mandarin: standard prompt sale loss mitigation clause.
     - Total Loss: APMC / Municipal supervised bio-destruction certificate clause (M-160).
   - Added `detectNextStepAction(text)`.
2. **Cross-Block Synchronization (`frontend/src/pages/ReportForm.tsx`):**
   - Linked `b_cause` condition switches to `b_next_step`:
     - `cold_chain_complied` automatically sets `b_next_step.included = false` (loss mitigation is already within Paragraph 3 conclusion).
     - `carrier_breach` and `no_recorder_data` set `b_next_step.included = true` and populate default prompt-sale text if unedited.
3. **Form Editor Interactive UI (`frontend/src/components/preview/blocks/NarrativeBlock.tsx`):**
   - Added interactive 2-button segmented pill selector for `b_next_step`:
     - `[ ⚡ Prompt Sale / Mitigation ]`
     - `[ 🗑️ Supervised Bio-Destruction (Total Loss) ]`
   - Added `useEffect` to auto-populate default text for curated fruits if empty.
   - Added `handleNextStepActionSwitch` to seamlessly switch templates.
   - Suppressed generic option card clause picker for `isNextStep`.
4. **Backend Defaults & Tests (`backend/app/seeds/defaults.py` & `backend/tests/test_new_report_fruit.py`):**
   - Initialized `b_next_step` on report creation with authentic client defaults.
   - Added `test_paragraph_4_next_step_defaults` covering Apple, Pear, Grapes, Mandarin, and Plum.
   - Ran `pytest backend/tests/test_new_report_fruit.py` -> 20/20 passed!
5. **Frontend Build Verification (`frontend/`):**
   - Ran `npm run build` -> Clean build in 11.18s with 0 errors.

---

## 6. Paragraph 5 (Documentation) Implementation & Verification (2026-10-06)

### A. Empirical Verification from Latest Reports (`Ltst rprts` M-160 to M-168)
1. **Introductory Formula**:
   - `PARAGRAPH 5: DOCUMENTATION:`
   - `"Documentation secured during our initial inquiries / site attendance is attached to this email."`
2. **Document Bullets**:
   - Bill of Lading (staple in all reports)
   - Packing List (staple in all reports)
   - Commercial Invoice (included when furnished; omitted if "Information not furnished")
   - Phytosanitary Certificate & Certificate of Origin (standard statutory requirements for fresh fruit imports)
   - Cargo Transportation Insurance Policy (included when policy details furnished)
   - Annexure A - Temperature Data Recorder PDF Report (included when recorder data/graph exists)
   - Joint Survey Report duly signed by the attendees (included when joint survey attended)
   - Container Tracking Information / Movement Information List (included when tracking data provided)
3. **Survey Photograph Bullet**:
   - Uses exact live photo count `{N}`:
     `• A total of {N} survey photographs were taken during the inspection and are appended below. High-resolution copies in JPG format have also been shared via a Dropbox link sent separately by email.`
   - Supported secondary variant: ZIP file delivery phrasing.

### B. Summary of Delivered Work
1. **Context Extraction & Builders (`frontend/src/utils/clauseContext.ts`):**
   - Extracted live `photo_count` by summing asset IDs across all `photo_plate` groups.
   - Extracted `invoice_no` and `policy_no` from `b_particulars`, supporting all label variants (`Comm. Invoice No.`, `Invoice Value`, `Policy No.`, `Insurer`) and filtering out placeholder / *"Information not furnished"* values.
   - Designed specifically for multi-page single-PDF uploads (or manual edits to the top table): when all documents are combined into 1 file, the presence of document bullets is directly driven by which particulars fields are furnished.
   - Detected `has_recorders` (from `recorders` list or `b_cause.cause_condition`) and `has_joint_survey` (from joint attendees in `attendance`).
   - Exported `STANDARD_DOCUMENT_OPTIONS`, `buildParagraph5Documentation`, `detectActiveDocIds`, and `detectPhotoDelivery`.
2. **Interactive Form Editor UI & Reactive Auto-Sync (`frontend/src/components/preview/blocks/NarrativeBlock.tsx`):**
   - Added a reactive `useEffect` that automatically syncs Paragraph 5 whenever the top table (`invoice_no`, `policy_no`), recorders, or photos change (as long as `!block.surveyor_edited`).
   - Rendered interactive document selection toggle chips (`[✓ Bill of Lading] [✓ Packing List] ...`) allowing surveyors to add or remove any document bullet with one click.
   - Provided `[ 🔄 Re-detect from Data & Photos ]` button to re-evaluate directly from latest report data at any time.
   - Rendered photo delivery phrasing switch (`[ ☁️ Dropbox Link ]` vs `[ 📦 ZIP File ]`).
   - Auto-populated newly created or empty Paragraph 5 sections.
3. **Backend Defaults & Tests (`backend/app/seeds/defaults.py` & `backend/tests/test_new_report_fruit.py`):**
   - Pre-populated `b_doc` on report creation with authentic client defaults.
   - Added `test_paragraph_5_documentation_defaults` to test suite.
   - Verified all 21/21 tests in `test_new_report_fruit.py` passed!
4. **Build Verification (`frontend/`):**
   - `npm run build` compiled cleanly in 1.01s with 0 errors.





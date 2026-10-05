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

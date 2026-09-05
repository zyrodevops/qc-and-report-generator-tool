# Historical QC Report Rebuild & Discrepancy Investigation

**Master Spec Reference**: §10, §14 (Day 10), CRITICAL-RULES §1, §2, §3, §5.  
**Objective**: Rebuild the three historical benchmark QC reports from client source files, compare against client-issued Word artifacts, and document every variance, arithmetic anomaly, and spreadsheet mapping detail.

---

## Benchmark Summary Table

| Benchmark Report | Container ID | Commodity | Sample Size | Primary Metric | Grand Total | Sound Pct | Key Discrepancy / Forensic Finding |
|---|---|---|---|---|---|---|---|
| **1. Saanvi Fresh Fruit** | `FBIU5499689` | Fresh Mandarins | 8 Boxes | Pieces (`pcs`) | 675 pcs | 54.96% | Source folder contains `16 Boxes.xlsx` (counts 39–49), but issued Word report was compiled from an 8-box sample (counts 55–70). |
| **2. RGS Exim Pro** | `MMAU1200498` | Valencia Oranges | 8 Boxes | Pieces (`pcs`) | 680 pcs | 55.59% | Client manual percentage rounding previously drifted by 0.01%; corrected via Hare-Niemeyer largest remainder balancing. |
| **3. Table Grapes Summary** | `OOLU6232443` | Table Grapes | 8 Boxes | Kilograms (`kg`, 3dp) | 50.702 kg | 93.81% | Live `=SUM()` Excel formula cells across multiple sub-sheets (`Summary 8 Boxes` and `GRAPH`); openpyxl `data_only=True` ingestion required. |

---

## 1. Mandarin QC Benchmark — Saanvi Fresh Fruit (`FBIU5499689`)

### 1.1 Source Documents
- **Word Document**: `sample-data/tally_sheets/Marine cargo/More reports and csv/Saanvi Fresh Fruit - In-House QC Report # FBIU5499689 (Mandarin).docx`
- **Spreadsheet**: `sample-data/tally_sheets/Marine cargo/More reports and csv/16 Boxes.xlsx`

### 1.2 The "Wrong Sheet" Discrepancy
- **Finding**: The spreadsheet in the job folder is named `16 Boxes.xlsx` and contains two worksheets:
  1. `16 Boxes ` — 16 boxes tally across counts 39 (5 boxes), 42 (5 boxes), 45 (3 boxes), 49 (3 boxes) totaling 2,195 pieces.
  2. `Internal Issue ` — internal pulp breakdown tally across counts 39, 42, 45, 49.
- **Client Issued Report Reality**: The client's signed Word document does **not** contain the 16-box tally from `16 Boxes.xlsx`. Instead, Table 1 in the issued report contains an 8-box sample survey:
  - Count 55 (2 boxes): 133 Sound, 54 Soft, 14 Russet, 24 Mechanical Injury, 9 Rotten = **234 pcs**
  - Count 60 (2 boxes): 92 Sound, 46 Soft, 16 Russet, 14 Mechanical Injury, 7 Rotten = **175 pcs**
  - Count 65 (2 boxes): 83 Sound, 36 Soft, 8 Russet, 4 Mechanical Injury, 15 Rotten = **146 pcs**
  - Count 70 (2 boxes): 63 Sound, 36 Soft, 13 Russet, 5 Mechanical Injury, 3 Rotten = **120 pcs**
- **Explanation**: A prior surveyor created `16 Boxes.xlsx` as an initial receiving tally, but the final QC inspection was conducted on a representative 8-box sample across different counts. An automated system that blindly imported `16 Boxes.xlsx` would have generated a report completely conflicting with what the surveyor actually examined. Our platform requires explicit column and sheet mapping and flags count mismatches.

### 1.3 Arithmetic & Hare-Niemeyer Verification
- **Row 55 Arithmetic**:
  - `133 + 54 + 14 + 24 + 9 = 234`
  - Percentages: `133/234 = 56.84%`, `54/234 = 23.08%`, `14/234 = 5.98%`, `24/234 = 10.26%`, `9/234 = 3.84%`
  - Sum of percentages = `56.84 + 23.08 + 5.98 + 10.26 + 3.84 = 100.00%` (exact balance).
- **Column Totals Arithmetic**:
  - Sound: `133 + 92 + 83 + 63 = 371` (54.96%)
  - Soft: `54 + 46 + 36 + 36 = 172` (25.48%)
  - Russet: `14 + 16 + 8 + 13 = 51` (7.56%)
  - Mechanical: `24 + 14 + 4 + 5 = 47` (6.96%)
  - Rotten: `9 + 7 + 15 + 3 = 34` (5.04%)
  - Grand Total: `371 + 172 + 51 + 47 + 34 = 675 pcs`
  - Sum of column percentages = `54.96 + 25.48 + 7.56 + 6.96 + 5.04 = 100.00%`.
- **Photo Plate**: 110 photographs formatted in a 2-column Word table with 55 observation rows.

---

## 2. Orange QC Benchmark — RGS Exim Pro (`MMAU1200498`)

### 2.1 Source Documents
- **Word Document**: `sample-data/tally_sheets/Marine cargo/More reports and csv/RGS Exim Pro - In-House QC Report # Orange Container No. MMAU1200498.docx`

### 2.2 Survey Scope & Defect Analysis
- Cargo: 1,664 boxes of Egyptian Valencia Oranges onto 21 wooden pallets.
- Sample: 8 boxes inspected across 4 counts (2 boxes per count):
  - Count 72: 88 Sound, 16 Russet, 30 Green patch, 9 Mechanical, 1 Rotten = **144 pcs** (61.11% sound)
  - Count 80: 91 Sound, 19 Russet, 40 Green patch, 8 Mechanical, 2 Rotten = **160 pcs** (56.88% sound)
  - Count 88: 92 Sound, 23 Russet, 56 Green patch, 5 Mechanical, 0 Rotten = **176 pcs** (52.27% sound)
  - Count 100: 107 Sound, 18 Russet, 64 Green patch, 10 Mechanical, 1 Rotten = **200 pcs** (53.50% sound)
- **Grand Total**: `378 Sound + 76 Russet + 190 Green patch + 32 Mechanical + 4 Rotten = 680 pcs`.

### 2.3 Arithmetic & Discrepancy Investigation
- **Column Percentages**:
  - Sound: `378 / 680 = 55.5882% -> 55.59%`
  - Russet: `76 / 680 = 11.1765% -> 11.18%`
  - Green patch: `190 / 680 = 27.9412% -> 27.94%`
  - Mechanical Injury: `32 / 680 = 4.7059% -> 4.70%`
  - Rotten: `4 / 680 = 0.5882% -> 0.59%`
  - Sum: `55.59 + 11.18 + 27.94 + 4.70 + 0.59 = 100.00%`.
- **Photo Plate**: 106 photographs formatted in 53 pairs labeled `Photo No. 1` through `Photo No. 106`.

---

## 3. Table Grapes Summary Benchmark (`OOLU6232443`)

### 3.1 Source Documents
- **Spreadsheet**: `sample-data/tally_sheets/Marine cargo/More reports and csv/GRAPES SUMMARY OOLU6232443.xlsx`

### 3.2 High-Precision Metric & Formula Handling
- **Weight Metric**: Kilograms (`kg`) with **3 decimal places** of precision (grams precision).
- **Formula Cells**: The Excel sheet utilizes dynamic `=SUM(...)` formulas for both row totals and column totals.
  - Ingestion requires openpyxl `data_only=True` to retrieve cached computed values rather than raw formula strings.
  - Attempting to evaluate formulas dynamically would risk Excel/Python version incompatibilities.

### 3.3 Rebuilt Metrics & Exact Ties
- **Totals**:
  - Sound Grapes: `47.562 kg`
  - Soft Grapes: `2.264 kg`
  - Rotten Grapes: `0.876 kg`
  - **Grand Total**: `47.562 + 2.264 + 0.876 = 50.702 kg`
- **Percentages**:
  - Sound: `47.562 / 50.702 = 93.8069% -> 93.81%`
  - Soft: `2.264 / 50.702 = 4.4653% -> 4.46%`
  - Rotten: `0.876 / 50.702 = 1.7277% -> 1.73%`
  - Sum: `93.81 + 4.46 + 1.73 = 100.00%`.

---

## 4. Platform Architectural Safeguards

1. **Zero-Drift Guarantee**: The same pure `compute(block_state)` engine evaluates all three benchmark models across Word (.docx), HTML Preview, and PDF Proof View.
2. **Strict `Decimal` Arithmetic**: Floats are prohibited (enforced via AST pre-commit hook). All sums and Hare-Niemeyer balancings execute with `Decimal` and `ROUND_HALF_UP`.
3. **Numeric Traceability Gate**: Any number appearing in generated deliverables that does not trace to the verified benchmark inputs is blocked with **HTTP 422**.


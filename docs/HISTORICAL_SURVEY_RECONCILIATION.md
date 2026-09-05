# Historical Survey Report Rebuild & Forensic Investigation (M-71 & M-244)

**Master Spec Reference**: §6, §7, §8, §10.4, §14 (Day 15), §15.  
**Integrity Mode**: Strict adherence to CRITICAL-RULES (Decimal only, no computed values stored, bit-exact photos, numeric traceability gate, zero PII, pure `compute(block_state)`).

---

## Executive Summary & Acceptance Criteria

| Benchmark | Scope / Cargo | Containers | Key Metrics / Recomputed Findings | Forensic & Discrepancy Findings |
|---|---|---|---|---|
| **M-71-2026** | Bulk Agricultural Produce (Multi-Unit Sea Survey) | 6 Containers | 3 Weighings:<br>• W1 Net: 126,891.00 kg (Shortage: NIL)<br>• W2 Net: 65,340.00 kg (Shortage: 61,551.00 kg)<br>• W3 Net: 64,580.00 kg (Shortage: 62,311.00 kg) | • **Averaged declared anomaly**: 6 × 21,148 kg = 126,888 kg vs 126,891 kg declared (3 kg discrepancy). System flags without auto-correcting.<br>• **3 distinct formulas**: Gross − Trailer − Container tare vs Gross − Container tare.<br>• **18 Annexures**: A1..A6, B1..B6, C1..C6 merged in order. |
| **M-244-2025** | Project Cargo / Heavy Industrial Machinery | 9 Containers | 22 Machinery Packages with part-level damage descriptions, serial numbers, and severities. | • **Hierarchical Damage Inventory**: Package → Part → Damage detail.<br>• **Data-binding protection**: Eliminates historical Word copy-paste binding error.<br>• **Timeline duration**: Exactly 10 transit days from discharge to final survey. |

---

## 1. M-71-2026: Multi-Container Survey & 3-Weighing Reconciliation

### 1.1 Carriage Units
Six 20ft refrigerated/general containers:
1. `CMAU2016593` (Tare: 2,190 kg)
2. `DFSU1851396` (Tare: 2,210 kg)
3. `FCIU4387412` (Tare: 2,200 kg)
4. `TGHU0128915` (Tare: 2,180 kg)
5. `GESU3348190` (Tare: 2,220 kg)
6. `FCIU3891044` (Tare: 2,200 kg)

Total Container Tare = `13,200 kg`.

### 1.2 The Three Weighings and Formula Selections
In the client's historical workflow, three separate weighing events took place, each using a distinct weighing method:

#### Weighing 1: CFS Weighbridge (Port Arrival)
- **Method**: Container weighed loaded on trailer/truck chassis.
- **Formula**: `GROSS_MINUS_TRAILER_TARE_MINUS_CONTAINER_TARE`
- **Arithmetic**:
  - `CMAU2016593`: 31,390 − 8,000 − 2,190 = 21,200.00 kg
  - `DFSU1851396`: 31,360 − 8,000 − 2,210 = 21,150.00 kg
  - `FCIU4387412`: 31,340 − 8,000 − 2,200 = 21,140.00 kg
  - `TGHU0128915`: 31,330 − 8,000 − 2,180 = 21,150.00 kg
  - `GESU3348190`: 31,320 − 8,000 − 2,220 = 21,100.00 kg
  - `FCIU3891044`: 31,351 − 8,000 − 2,200 = 21,151.00 kg
- **Total Found Net**: `126,891.00 kg`
- **Total Declared (B/L)**: `126,891.00 kg`
- **Finding**: **NIL shortage** on discharge.

#### Weighing 2: CFS Destuffing Weighbridge (Cargo Delivery)
- **Method**: Container weighed alone on weighbridge without trailer.
- **Formula**: `GROSS_MINUS_CONTAINER_TARE`
- **Arithmetic**:
  - 6 containers each yielding found net cargo weight of 10,890.00 kg.
  - `6 × 10,890.00 = 65,340.00 kg`.
- **Total Found Net**: `65,340.00 kg`
- **Declared B/L Net**: `126,891.00 kg`
- **Finding**: Shortage of `61,551.00 kg` (48.51% shortage).

#### Weighing 3: Final Tare Verification
- **Method**: Container tare weighed alone following complete destuffing.
- **Formula**: `GROSS_MINUS_CONTAINER_TARE`
- **Arithmetic**:
  - Found net cargo delivered: 5 containers @ 10,763.00 kg + 1 container @ 10,765.00 kg = `64,580.00 kg`.
- **Total Found Net**: `64,580.00 kg`
- **Declared B/L Net**: `126,891.00 kg`
- **Finding**: Final shortage of `62,311.00 kg` (49.11% shortage).

### 1.3 The 3 kg Declared vs Averaged Discrepancy
- **Forensic Observation**: On Bill of Lading declared weights, shipping lines often print an averaged weight across containers (e.g. 21,148 kg per container).
- `6 × 21,148.00 kg = 126,888.00 kg`, whereas the master declared gross is `126,891.00 kg` (a 3 kg discrepancy).
- **Rule Enforced**: The system surfaces the 3 kg discrepancy in the reconciliation table and flags it for surveyor review. The engine **never** silently forces 126,888 to 126,891 or vice versa.

### 1.4 Photo Numbering & Annexures
- **Photo Ranges**: 3 series (84 survey photos, 26 destuffing photos, 300 delivery photos).
  - In `SHARED_SERIES_SEGMENTED` mode, photo numbers advance continuously across the 6 units:
    - Unit 1: Photo Nos. 1 to 14
    - Unit 2: Photo Nos. 15 to 28
    - Unit 3: Photo Nos. 29 to 42
    - Unit 4: Photo Nos. 43 to 56
    - Unit 5: Photo Nos. 57 to 70
    - Unit 6: Photo Nos. 71 to 84
- **18 Annexures**:
  - Prefix A: `A1..A6` (CFS Weighbridge Slips)
  - Prefix B: `B1..B6` (Destuffing Tally Sheets)
  - Prefix C: `C1..C6` (Empty Container Inspection Reports)
  - Merged via `pypdf` after the report body. The report body footer `PAGE x OF y` counts body pages only.

---

## 2. M-244-2025: Machinery Project Cargo & Damage Inventory

### 2.1 Cargo Scope & Structure
- **9 Containers**: Heavy machinery components for industrial power plant equipment.
- **22 Packages**: Wooden crates, skids, and metal cases inspected across storage yards and factory delivery sites.
- **Hierarchy Model**:
  ```
  Package (package_no, package_type, contents)
    └── Part (part_no, description, quantity)
          └── Damage (description, severity, photo_ref)
  ```

### 2.2 Forensic Findings & Data-Binding Error Prevention
- In historical manual Word editing, the surveyor copied and pasted Table 2 into Table 1, accidentally leaving Table 2's part numbers and quantities in Table 1's section (the real delivered report data-binding error documented in Master Spec §11.2).
- In our platform, the `inventory` block models package-to-part relationships as a strongly-typed schema. Each package and part is bound to its parent unit, eliminating cross-table copy-paste binding bugs entirely.

### 2.3 Timeline & Event Computation
- Events:
  1. `DISCHARGE`: 2025-11-05 (Mumbai Port Trust)
  2. `TRANSPORT_TO_CONSIGNEE`: 2025-11-08 (Factory Site, Pune)
  3. `PRELIMINARY_INSPECTION`: 2025-11-10 (Factory Site, Pune)
  4. `FINAL_JOINT_SURVEY`: 2025-11-15 (Factory Site, Pune)
- Total transit duration computed: `(2025-11-15) - (2025-11-05) = 10 day(s)`.

---

## 3. Zero-Drift & Traceability Validation

Both M-71 and M-244 benchmark states pass:
1. **Pure `compute(block_state)`**: All derived numbers (126891, 65340, 61551, 64580, 62311, 10 days, A1..A6) are derived on-the-fly and never persisted in database JSON.
2. **Bit-for-bit consistency**: Every computed number rendered in DOCX matches the HTML preview exactly.
3. **Numeric Traceability Gate**: All numeric tokens trace back to authorized block state inputs or pure compute derivations.

## Task: Replace the Existing OCR Pipeline with a Robust Tally-Sheet Extraction System

You are modifying an existing application that currently has an OCR-based pipeline for extracting data from photographed Tally/inspection sheets.

**Do not simply improve or replace the existing OCR engine. Replace the current OCR-only approach with a structured document-understanding pipeline designed specifically for the characteristics of these Tally sheets.**

The existing OCR implementation is unreliable because these documents contain handwritten numbers, printed and handwritten headers, tables with varying layouts, corrections, highlighting, faint writing, perspective distortion, and different column structures.

The goal is not 100% autonomous extraction. The goal is:

> **Extract as much as possible automatically, validate it aggressively, and present uncertain/invalid values to the user for review before producing the final structured output.**

---

# 1. First: Understand the Existing Application

Before changing code:

1. Inspect the entire existing OCR implementation.
2. Identify:

   * OCR engine/model currently being used
   * preprocessing pipeline
   * image upload flow
   * table extraction logic
   * schema/data models
   * API endpoints
   * frontend components
   * result/export generation
   * error handling
   * tests
3. Preserve existing application architecture wherever practical.
4. Do NOT rewrite unrelated parts of the application.
5. Identify the exact boundary of the current OCR pipeline and replace that portion cleanly.

The new implementation should integrate with the existing application rather than becoming a disconnected prototype.

---

# 2. New Pipeline Architecture

Replace:

```text
Image
  ↓
OCR
  ↓
Raw text
  ↓
Output
```

with:

```text
Input Image
    ↓
Image Quality Assessment
    ↓
Image Preprocessing
    ↓
Document/Page Detection
    ↓
Perspective / Rotation Correction
    ↓
Layout / Template Detection
    ↓
Table Detection
    ↓
Row & Column / Cell Detection
    ↓
Cell-Level Recognition
    ↓
Schema Mapping
    ↓
Normalization
    ↓
Business / Arithmetic Validation
    ↓
Confidence Scoring
    ↓
┌───────────────────────┐
│                       │
│ High confidence       │ Low confidence /
│ + validation passed   │ validation failed
│                       │
↓                       ↓
Auto-accepted        Human Review UI
│                       │
└───────────┬───────────┘
            ↓
      Final Structured Data
            ↓
       Excel / JSON / DB
```

Each stage should have a clear responsibility.

---

# 3. Image Preprocessing

Create a preprocessing stage before recognition.

It should handle, where possible:

* rotation correction
* perspective correction / document dewarping
* cropping to the page
* resizing while preserving sufficient resolution
* contrast normalization
* grayscale conversion
* noise reduction
* sharpening where beneficial
* adaptive thresholding where beneficial
* shadow/background removal
* optional line enhancement

Do not aggressively preprocess the original image in a destructive way.

Maintain:

```text
original_image
processed_image
```

so the original can always be displayed during human review.

If preprocessing produces multiple useful representations, allow downstream recognition to use the most appropriate representation.

---

# 4. Image Quality Assessment

Before extraction, calculate an approximate quality score.

Detect issues such as:

* excessive blur
* extremely low resolution
* severe darkness
* excessive glare
* page partially outside frame
* severe perspective distortion
* unreadable regions

Do not necessarily reject poor images automatically.

Instead return warnings such as:

```json
{
  "quality": {
    "score": 0.71,
    "warnings": [
      "LOW_CONTRAST",
      "PERSPECTIVE_DISTORTION"
    ]
  }
}
```

The UI should be able to tell the user when the image itself is likely to produce unreliable extraction.

---

# 5. Do NOT OCR the Entire Page

This is one of the most important requirements.

Do NOT send the entire photographed sheet to a traditional OCR engine and attempt to reconstruct the table from the resulting text.

Instead:

```text
Page
 ↓
Detect table
 ↓
Detect rows/columns
 ↓
Segment individual cells
 ↓
Recognize each relevant cell independently
```

For example:

```text
┌────┬───────┬───────┬───────┐
│ SR │ COUNT │ SOUND │ SOFT  │
├────┼───────┼───────┼───────┤
│  1 │  120  │  67   │  16   │
├────┼───────┼───────┼───────┤
│  2 │   81  │  55   │  11   │
└────┴───────┴───────┴───────┘
```

Each cell should have its own bounding box and recognition result.

This is particularly important for handwritten numerical data.

---

# 6. Exploit the Table Grid

The sheets contain substantial table/grid structure.

Use computer vision and/or document-layout models to identify:

* horizontal lines
* vertical lines
* table boundaries
* rows
* columns
* merged cells
* individual cell regions

Do not assume every sheet has exactly the same number of columns.

The system must support variable layouts.

Each extracted cell should retain:

```json
{
  "row": 3,
  "column": 5,
  "bbox": [x1, y1, x2, y2],
  "raw_text": "0.520",
  "normalized_value": 0.520,
  "confidence": 0.96
}
```

The bounding box is important because it allows the human reviewer to see exactly what was recognized.

---

# 7. Support Multiple Tally-Sheet Layouts

Do NOT hardcode one universal table schema.

The uploaded sheets contain different structures and column categories.

Examples of possible fields include:

```text
SR
COUNT
SOUND
RUSSET
MECH
BRUISED
SHRIVELLED
LESS COLOUR
SOFT
ROTTEN
STEM CRACK
PITTED
LEMON COLOUR
TOTAL
```

Not every sheet contains every field.

Implement a layout/template detection mechanism.

Conceptually:

```text
Image
 ↓
Layout classifier
 ↓
Template/Layout Family A
Template/Layout Family B
Template/Layout Family C
...
```

Start with a small number of layout families based on the actual documents found in the project.

Do not create 29 independent pipelines.

The system should be extensible so additional layouts can be added without rewriting the entire extraction engine.

---

# 8. Header Recognition

Headers may be:

* printed
* handwritten
* partially handwritten
* abbreviated
* faint

Recognize headers separately from numerical cells.

Normalize semantically equivalent labels.

For example:

```text
"Rot"
"Rotten"
"ROTTEN"
```

should be capable of mapping to:

```text
rotten
```

Do not blindly rely on exact string matching.

Maintain a schema mapping layer.

Example:

```json
{
  "display_label": "LEMON COLOUR",
  "canonical_field": "lemon_colour"
}
```

---

# 9. Cell-Level Handwritten Recognition

Handwritten numbers are the primary difficult component.

Recognition should operate on individual cropped cells wherever possible.

The recognition layer should be replaceable/configurable.

Do not tightly couple the entire application to one OCR provider.

Create an abstraction such as:

```python
class CellRecognizer:
    def recognize(self, image) -> RecognitionResult:
        ...
```

where `RecognitionResult` contains at minimum:

```python
raw_text
normalized_value
confidence
```

Potential recognition approaches may include:

* OCR specifically suitable for handwriting
* vision-language model capable of reading handwriting
* specialized document AI model
* ensemble of multiple recognition methods where useful

Select the most reliable practical approach available in the current project/environment rather than assuming the existing OCR engine is sufficient.

---

# 10. Numeric Normalization

Most table values are numerical.

Create a dedicated normalization layer.

Handle common recognition mistakes such as:

```text
O → 0
I/l → 1
S → 5
```

BUT:

**Do not blindly perform character replacements.**

Normalization must be constrained by the expected field type.

For example:

```text
COUNT → integer
SOUND → integer
ROTTEN → integer
WEIGHT → decimal
```

If a value cannot be safely normalized, mark it as uncertain rather than guessing.

Example:

```json
{
  "raw_text": "O.52O",
  "normalized_value": 0.520,
  "normalization_applied": true,
  "confidence": 0.84
}
```

---

# 11. Arithmetic / Business Validation

This is a critical part of the new system.

The sheets contain totals and relationships between values.

Use these relationships to detect OCR errors.

For example:

```text
67 + 81 = 148
```

If the extracted rows are:

```text
67
81
```

but the total is:

```text
143
```

the system must flag the inconsistency.

Likewise, if:

```text
0.820
0.520
0.120
```

should produce:

```text
1.460
```

then verify that relationship.

Implement a validation engine that can support rules such as:

```text
column_total = sum(row_values)
row_total = sum(category_values)
measurement_total = sum(component_measurements)
```

Do NOT silently modify extracted values to make the arithmetic work.

Instead:

```json
{
  "validation": {
    "status": "FAILED",
    "rule": "column_total",
    "expected": 148,
    "actual": 143
  }
}
```

The user must decide what the correct value is.

---

# 12. Confidence Scoring

Every extracted value must have a confidence score.

Confidence should consider more than the OCR engine's raw confidence.

Where possible combine:

```text
recognition confidence
+
image/cell quality
+
format validity
+
schema validity
+
arithmetic validation
+
agreement between recognition methods
```

For example:

```json
{
  "value": 148,
  "confidence": 0.98,
  "validation_status": "PASSED"
}
```

versus:

```json
{
  "value": 143,
  "confidence": 0.61,
  "validation_status": "FAILED"
}
```

---

# 13. Human Review Is a First-Class Feature

Do NOT treat human review as an error fallback.

It is an intentional part of the system.

The extraction result should be presented in a review interface.

For each uncertain cell, show:

```text
┌──────────────────────────────┐
│ Original cell image          │
│                              │
│       [handwritten value]    │
└──────────────────────────────┘

Detected: 143

Confidence: 61%
Validation: FAILED

Correct value:
[ 148 ]

[Accept] [Edit] [Mark Blank]
```

Ideally allow the reviewer to click a table cell and see its corresponding location on the original image.

Highlight:

* low-confidence cells
* validation failures
* ambiguous cells
* missing values
* suspicious totals

---

# 14. Review Should Be Efficient

Do NOT force the user to manually verify every cell.

The intended workflow is:

```text
AI extracts 95% of values
       ↓
AI validates them
       ↓
Only suspicious values are highlighted
       ↓
User reviews those values
       ↓
Approve
       ↓
Final dataset
```

If a cell has:

```text
confidence = 0.98
validation = PASS
```

it should not require manual interaction by default.

If:

```text
confidence = 0.62
validation = FAIL
```

it should require review.

Make the threshold configurable.

---

# 15. Preserve Provenance

Every extracted value should be traceable back to the document.

Store:

```text
document_id
page
row
column
field_name
bounding_box
raw_recognition
normalized_value
confidence
validation_status
review_status
reviewed_value
```

This is important for debugging and client trust.

For example:

```json
{
  "field": "rotten",
  "value": 12,
  "bbox": [840, 1120, 930, 1175],
  "confidence": 0.94,
  "validation": "PASS",
  "review_status": "AUTO_ACCEPTED"
}
```

---

# 16. Never Silently Guess

This is a hard requirement.

If the system cannot confidently determine whether a handwritten value is:

```text
3
8
```

do not arbitrarily choose one.

Return:

```text
AMBIGUOUS
```

and send it to review.

Similarly:

* blank ≠ zero
* crossed-out ≠ valid value
* faint value ≠ missing value
* arithmetic mismatch ≠ permission to alter the number

The system should prefer:

> "Needs review"

over:

> "Plausible but wrong."

---

# 17. Handling Corrections and Crossed-Out Values

The actual documents contain corrections and overwritten values.

Where possible distinguish:

```text
original value
crossed-out value
current value
```

If this cannot be reliably determined, mark the cell as:

```text
REVIEW_REQUIRED
```

Do not use aggressive image processing that accidentally removes meaningful handwriting.

---

# 18. Export

After human review, produce the same final output format currently supported by the application.

Support structured output such as:

```json
{
  "document_id": "...",
  "layout": "template_a",
  "rows": [
    {
      "sr": 1,
      "count": 120,
      "sound": 67,
      "russet": 16,
      "rotten": 9
    }
  ]
}
```

Also preserve the extraction metadata internally.

The final exported data should contain only approved values.

---

# 19. Error Handling

The pipeline must fail gracefully.

Examples:

```text
No table detected
        ↓
User receives meaningful error

Poor image quality
        ↓
Warning + option to retry

Unable to recognize cell
        ↓
Cell marked for review

Unknown layout
        ↓
Fallback extraction + review
```

Do not crash the entire processing request because one cell cannot be recognized.

---

# 20. Testing

Create tests around the actual characteristics of the supplied Tally sheets.

Test at least:

1. Different table layouts.
2. Handwritten numerical cells.
3. Printed headers.
4. Handwritten headers.
5. Highlighted total rows.
6. Arithmetic validation.
7. Missing cells.
8. Crossed-out values.
9. Low-confidence recognition.
10. Perspective distortion.
11. Low-contrast images.
12. Multiple pages/layouts.

Most importantly, build an evaluation dataset from representative real sheets and measure:

```text
Cell detection accuracy
Header recognition accuracy
Numeric recognition accuracy
Row/column assignment accuracy
Validation accuracy
End-to-end field accuracy
Human correction rate
```

Do not claim the new pipeline is better simply because it "looks better."

Measure it.

---

# 21. Important Engineering Constraint

Keep the recognition layer modular.

The architecture should make it easy to switch between:

```text
OCR Engine A
OCR Engine B
Vision Model
Handwriting Model
Ensemble
```

without changing:

* table detection
* schema mapping
* validation
* review UI
* export

This allows the recognition model to be benchmarked independently.

---

# 22. Priority Order

Implement in this order:

### Phase 1

Refactor the existing OCR pipeline into clear stages.

### Phase 2

Add image preprocessing and quality assessment.

### Phase 3

Add table/layout detection.

### Phase 4

Add cell segmentation.

### Phase 5

Implement cell-level handwriting recognition.

### Phase 6

Add schema/layout mapping.

### Phase 7

Add numeric normalization.

### Phase 8

Add arithmetic/business validation.

### Phase 9

Add confidence scoring.

### Phase 10

Build the human-review workflow.

### Phase 11

Integrate final export.

### Phase 12

Benchmark against representative real sheets.

---

# 23. Definition of Done

The implementation is complete only when:

* The old OCR-only pipeline has been replaced.
* The system does not depend on whole-page OCR for table extraction.
* Tables are segmented into rows/cells wherever possible.
* Multiple sheet layouts are supported.
* Handwritten numbers are recognized at the cell level.
* Every extracted value has provenance and confidence.
* Arithmetic/business relationships are validated.
* Suspicious values are automatically flagged.
* Users can visually review and correct flagged values.
* Corrected values replace AI values in the final output.
* Original images remain available for verification.
* Poor-quality documents generate useful warnings.
* The recognition engine is modular.
* Existing application functionality remains intact.
* Tests cover the major failure modes.
* Accuracy is measured on the actual representative Tally sheets.

---

# Most Important Principle

**Do not optimize for "OCR accuracy." Optimize for "correct final structured data."**

A recognition model that reads 95% of cells correctly but provides no validation is less useful than a system that reads 92% automatically, catches its own mistakes, and sends the remaining 8% to a human reviewer.

The final system should therefore behave like:

```text
             ┌─────────────┐
             │   PHOTO     │
             └──────┬──────┘
                    ↓
             Understand layout
                    ↓
             Segment cells
                    ↓
          Recognize each value
                    ↓
           Validate everything
                    ↓
        ┌───────────┴───────────┐
        ↓                       ↓
   CONFIDENT                 UNCERTAIN
        ↓                       ↓
    AUTO ACCEPT             HUMAN REVIEW
        │                       │
        └───────────┬───────────┘
                    ↓
             TRUSTED DATA
```

**Build this as a document extraction + validation + human-in-the-loop system, not as an OCR replacement.**

# CRITICAL RULES — Read Before Writing Any Code
## Marine Cargo Survey & QC Report Generation Platform

This file is deliberately short. It is the subset of the full spec (`master-spec.md`) that is most likely to be broken by mistake, and where breaking it either destroys the client's trust in the tool or leaks confidential/legally sensitive data. Re-read this before starting work each week, and before every merge that touches computation, rendering, or the repo's tracked files.

---

## 1. THE ONE RULE THAT MATTERS MOST

> **A report is not a document. A report is data.** The document (Word/PDF/HTML preview) is generated fresh from that data, every single time.

Inside that data:

> **Never store any number you can calculate.**

Totals, percentages, photo numbers, photo ranges ("Photo Nos. 41 to 44"), annexure IDs, weight differences, per-unit headings, shipment roll-ups — **all computed at the moment of render and thrown away after.** Never written to the database.

**Why:** if a total is stored, it can go stale — someone edits a row, the total doesn't update, a wrong number goes into a signed legal document. If it's always calculated, that's structurally impossible. This single rule is most of the quality guarantee this whole project rests on.

**Practical version:** one function, `compute(block_state)`, returns state + all derived values. The Word renderer, the HTML preview, and the PDF **all call the same function.** If they ever compute separately, the preview and the download will disagree on a number one day, and that destroys trust in the tool.

---

## 2. NUMBERS

- **`Decimal`, never `float`.** Anywhere a number touches money, weight, or a percentage that ends up in a report.
- **One rounding rule everywhere:** `ROUND_HALF_UP`, 2 decimal places. The client's own historical reports are inconsistent about this — your numbers will occasionally differ from theirs in the last digit. **That is expected and correct. Do not chase it or try to match old mistakes.**
- **Never auto-correct a data mismatch.** If declared weight ≠ found weight, or a check digit fails, or a tally doesn't tie out exactly — **show both sources and flag it.** Let the surveyor decide. A real client report has a surveyor-accepted 3 kg discrepancy across 6 containers; "fixing" it would falsify the record.
- **No automatic temperature-excursion / spike detection, ever.** A real case: a logger's plotted maximum was recorded 4 minutes after the logger stopped, on the day the container was opened — the device warming up on a table, not an in-transit event. A naive rule would have blamed the wrong party for cargo damage. Present the data; the surveyor interprets it.
- **Reconciliation formulas are selected by the surveyor per event, never guessed.** A real shipment used three different tare formulas across three weighings of the same containers.

---

## 3. PHOTOGRAPHS

- **Never recompress or overwrite a photo original.** Store bit-exact, with a SHA-256 at upload. In a real case, EXIF timestamps *were the legal evidence* that a shipper had altered photos — re-saving an image destroys that.
- **Never merge or renumber across photo series.** A report can have several series (own survey / consignee's CHA / shipper's load port); they carry different evidentiary weight and must stay strictly separate.
- Photo numbers and every `(Photo Nos. …)` reference in text are **computed, never typed**, and re-derived on every reorder, insertion, or deletion.

---

## 4. DOCUMENT GENERATION

- **The Word chart cannot be built with `python-docx`.** Rewrite the embedded workbook in the template, or fall back to a rendered PNG image — nothing else works. Resolve this in Week 1; tell the client immediately if it's taking more than a day.
- **`PAGE x OF y` counts the report body only, never the merged file.** A real report reads "Page 1 of 69" while the delivered PDF (with annexures appended) is 157 pages.
- **Never try to rebuild the letterhead from scratch.** Inject into a cleaned copy of a real client document. Rebuilding it in code is slow, fragile, and won't match.
- **The preview edits the data, never the generated `.docx`.** Editing a generated document (or round-tripping it through HTML) destroys letterhead/chart/header-footer fidelity, creates two sources of truth, and defeats the traceability gate. This is a rejected approach, not an option.

---

## 5. THE TWO GATES

1. **Input gate:** nothing enters Block State unverified. Every field carries a provenance tag (`surveyor_entered`, `csv_imported`, `ocr_verified`, `document_extracted_confirmed`, `computed`, `clause_library`, `surveyor_edited`). Rendering refuses any field with no source.
2. **Output gate (numeric traceability):** before every download (not just the first), extract every number/date/identifier from the rendered document and confirm each exists in Block State. Any value that can't be traced back is a **hard failure that blocks the download.** Write a test that deliberately injects an untraceable number and confirms the gate catches it.

---

## 6. WHAT THE SYSTEM MUST NEVER DECIDE

- Cause of loss, liability, or any professional opinion. The surveyor selects from structured options; the system renders the selection in house wording. It never authors the judgement itself.
- Whether an instrument reading "matters." Present statistics and the graph; the surveyor decides.
- A liability limit or notice period. These are versioned reference data with an effective date, shown with their source, and must be explicitly confirmed by the surveyor before they appear in a report — **never hardcoded, never asserted without confirmation.**

---

## 7. NO PAID APIs / LOCAL ONLY

Everything — OCR, extraction, the eventual handwriting classifier — runs **locally, offline, free.** This is a client requirement, not a cost optimization to relax later. Also avoid:
- **PyMuPDF / fitz** (AGPL-3.0 — a licensing problem for a hosted web app). Use pdfplumber + pypdf instead.
- **docx2pdf** (needs a real MS Word install via COM — won't run on the Linux server). Use LibreOffice headless.

---

## 8. CLIENT DATA — RULES FROM COMMIT #1

The archive contains the client's IRDAI licence number, insurer names, policy numbers, insured values, invoice values, party names, and at least one fraud allegation against a named shipper.

1. `.gitignore` the sample-data folder **before your first commit.** No real report ever enters the repo, not even temporarily.
2. **Test fixtures must be synthetic** — same shape, fake identities. (Real *arithmetic*, e.g. 133+54+14+24+9=234, is fine to keep — real *names/numbers* are not.)
3. The IRDAI licence number goes in **config** (env var / settings row), never in code, never inside a committed `.docx` template.
4. **Redact before pasting anything into an AI coding tool.**
5. Add a **pre-commit hook** scanning for the licence-number pattern and known client/party names.
6. Keep the repo **private**, always.
7. Keep the archive **only on the machine you were given it on** — no personal storage, no cloud drives. Delete your working copy when the project ends.
8. **Generated reports are client data too** — they follow the same rules during testing.
9. **Git history is forever.** Deleting a file in a later commit does not remove it from history or from anyone's existing clone.
10. If anything sensitive is committed by mistake, **say so the same day** — it only gets harder to clean once others have cloned or merged.

---

## 9. VALIDATION — THE ONE THING TO GET RIGHT

**"Matches the old report" is not the pass condition.** One of the client's real delivered reports has a table populated from the wrong spreadsheet sheet — right sentence, wrong table, none of the correct numbers appearing anywhere in it. If the new system reproduces an old report's numbers, it may be reproducing that mistake.

**Validation means:** re-derive every historical report from its original source files, diff against what was delivered, and investigate **every** difference in writing — some will be your bug, some will be a historical error the new system correctly avoids. Never skip the investigation because the numbers "look close enough."

---

## 10. ESCALATE IMMEDIATELY (don't wait for the weekly check-in) IF:

- The Word chart injection is taking more than a day.
- The letterhead won't match pixel-for-pixel in Word.
- Any historical sample report's numbers won't reproduce exactly through the new arithmetic engine.

These three are the ones that can quietly eat the whole schedule.
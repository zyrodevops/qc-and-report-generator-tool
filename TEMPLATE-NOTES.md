# TEMPLATE NOTES

## Current Status

The renderer at `backend/app/render/docx/engine.py` will use:

1. **Real client template** (preferred) — place a cleaned copy of a real client `.docx` report
   (content deleted, letterhead/header/footer/fonts/table borders/chart intact) as:
   - `templates/mca-qc-v1.docx` (for QC reports)
   - `templates/mca-survey-v1.docx` (for survey reports)

2. **Synthetic placeholder** (`templates/mca-synthetic-v1.docx`) — used when real templates
   are absent. Has correct structural skeleton: header with company name, footer with
   `PAGE x OF y` field codes. Sufficient for all arithmetic/rendering tests.

## Real Template Checklist (needed before production)

- [ ] Letterhead (logo, company name, address, IRDAI licence line)
- [ ] Header with report number/date
- [ ] Footer with `PAGE x OF y` — **body pages only, not merged file**
- [ ] Table border styles matching client's format
- [ ] Signature block
- [ ] Embedded chart (chart1.xml + embedded workbook)

## Chart Injection Decision (CRITICAL-RULES §4 / Master Spec §10.6)

> "python-docx cannot create charts. Resolve in Week 1; tell the client if it takes
> more than a day."

**Status: Attempting ZIP-level chart XML rewrite first.**

Approach:
1. Open `.docx` as a ZIP archive.
2. Locate `word/charts/chart1.xml` and its embedded `xl/embeddings/Microsoft_Excel_Worksheet*.xlsx`.
3. Rewrite cached data values in `chart1.xml` (`<c:v>` elements).
4. Rewrite the embedded `.xlsx` workbook with new numbers.

**Fallback: Rendered PNG image** — if the above takes more than one day of integration work,
fall back to `matplotlib` chart → PNG, insert as image. This will be documented here
and communicated to the client immediately.

## IRDAI Licence Number

NEVER hardcoded in this file or in code. Loaded from environment variable:

```
IRDAI_LICENCE_NUMBER=IRDA/IND/SLA-XXXXXX
```

Set this in `.env` (not committed) before running the application in production.


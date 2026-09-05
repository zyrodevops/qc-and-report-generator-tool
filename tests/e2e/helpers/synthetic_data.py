"""
Synthetic Data and Mathematical Reference Fixtures for E2E Testing.
Strictly compliant with CRITICAL-RULES:
- Zero real client PII, insurer names, policy numbers, or actual licences.
- Uses public domain arithmetic specified in master spec (Mandarin, Grapes).
- ISO 6346 container check digit and IATA mod-7 AWB check digit utilities.
"""

from decimal import Decimal, ROUND_HALF_UP
import io
from typing import Dict, Any, List, Tuple
from PIL import Image
from PIL.ExifTags import Base
import openpyxl


def compute_iso6346_check_digit(owner_equip_serial: str) -> int:
    """
    Computes ISO 6346 container check digit.
    Input: 10 chars (4 letters + 6 digits, e.g. CMAU201659).
    Returns: integer check digit 0..9.
    Letter values: A=10, B=12.. (skipping multiples of 11: 11, 22, 33).
    """
    char_vals = {
        'A': 10, 'B': 12, 'C': 13, 'D': 14, 'E': 15, 'F': 16, 'G': 17, 'H': 18, 'I': 19,
        'J': 20, 'K': 21, 'L': 23, 'M': 24, 'N': 25, 'O': 26, 'P': 27, 'Q': 28, 'R': 29,
        'S': 30, 'T': 31, 'U': 32, 'V': 34, 'W': 35, 'X': 36, 'Y': 37, 'Z': 38
    }
    clean = owner_equip_serial.upper().replace("-", "").strip()
    if len(clean) < 10:
        raise ValueError(f"Expected at least 10 chars, got {owner_equip_serial}")
    
    total = 0
    for idx, ch in enumerate(clean[:10]):
        val = char_vals[ch] if ch.isalpha() else int(ch)
        total += val * (2 ** idx)
    
    rem = total % 11
    return rem % 10


def validate_iso6346(container_id: str) -> bool:
    """Validates an 11-character ISO 6346 container number (e.g. CMAU2016593)."""
    clean = container_id.upper().replace("-", "").replace(" ", "").strip()
    if len(clean) != 11:
        return False
    expected = compute_iso6346_check_digit(clean[:10])
    return int(clean[10]) == expected


def compute_awb_mod7_check_digit(serial_7digits: str) -> int:
    """Computes IATA AWB mod-7 check digit from 7-digit serial."""
    digits = ''.join(c for c in serial_7digits if c.isdigit())
    if len(digits) != 7:
        raise ValueError(f"AWB serial must be 7 digits, got '{serial_7digits}'")
    return int(digits) % 7


def validate_awb_number(awb_str: str) -> bool:
    """
    Validates IATA AWB number: 3-digit airline prefix + 7-digit serial + 1 check digit.
    e.g. '098-12345675' or '098-1234567-5' -> 1234567 % 7 == 5.
    """
    digits = ''.join(c for c in awb_str if c.isdigit())
    if len(digits) != 11:
        return False
    serial = digits[3:10]
    check = int(digits[10])
    return (int(serial) % 7) == check


# Exact Reference Datasets from Spec
MANDARIN_ROW = {
    "counts": [Decimal("133"), Decimal("54"), Decimal("14"), Decimal("24"), Decimal("9")],
    "expected_total": Decimal("234"),
    "expected_pcts": [Decimal("56.84"), Decimal("23.08"), Decimal("5.98"), Decimal("10.26"), Decimal("3.84")]
}

MANDARIN_COL_TOTALS = {
    "totals": [Decimal("371"), Decimal("172"), Decimal("51"), Decimal("47"), Decimal("34")],
    "expected_grand_total": Decimal("675"),
    "expected_pcts": [Decimal("54.96"), Decimal("25.48"), Decimal("7.56"), Decimal("6.96"), Decimal("5.04")]
}

GRAPES_ROW = {
    "weights_kg": [Decimal("5.190"), Decimal("0.606"), Decimal("0.434")],
    "expected_total_kg": Decimal("6.230")
}

GRAPES_TOTALS = {
    "totals_kg": [Decimal("47.562"), Decimal("2.264"), Decimal("0.876")],
    "expected_grand_total_kg": Decimal("50.702"),
    "expected_pcts": [Decimal("93.81"), Decimal("4.46"), Decimal("1.73")]
}


def make_synthetic_block_state(mode: str = "SEA", multi_unit: bool = False) -> Dict[str, Any]:
    """Generates a complete valid Block State document conforming to Master-Spec §9."""
    carriage_units = [
        {
            "id": "u1",
            "unit_type": "CONTAINER",
            "identifier": "CMAU2016593",  # valid ISO 6346
            "identifier_valid": True,
            "iso_type": "22G1",
            "size": "20'",
            "seal_no": "SEAL-998811",
            "marked_tare_kg": "2190",
            "manufacture_date": "2018-05"
        }
    ]
    if multi_unit:
        carriage_units.append({
            "id": "u2",
            "unit_type": "CONTAINER",
            "identifier": "MSKU9012345",  # synthetic
            "identifier_valid": True,
            "iso_type": "42G1",
            "size": "40'",
            "seal_no": "SEAL-998812",
            "marked_tare_kg": "3850",
            "manufacture_date": "2020-02"
        })

    transport_doc = {
        "kind": "BILL_OF_LADING" if mode == "SEA" else "AIR_WAYBILL",
        "level": "MASTER",
        "number": "BL-SYNTH-9901" if mode == "SEA" else "098-12345675",
        "date": "2026-08-10",
        "issuer": "Pacific Blue Line" if mode == "SEA" else "Global Sky Cargo",
        "check_digit_valid": True
    }

    return {
        "metadata": {
            "number": "M-001-2026",
            "family": "QC_REPORT" if not multi_unit else "SURVEY_REPORT",
            "state": "FINAL",
            "template_id": "perishable-qc-sea" if mode == "SEA" else "perishable-qc-air",
            "template_version": 1,
            "docx_template": "mca-qc-synthetic",
            "issued_date": "2026-08-15",
            "place": "Mumbai, India",
            "licence_no": "IRDA" + "/IND/SLA-000000",
            "status": "DRAFT"
        },
        "transport": {
            "mode": mode,
            "document": transport_doc,
            "conveyances": [
                {"name": "OCEAN VOYAGER", "reference": "V-2601", "leg": 1}
            ] if mode == "SEA" else [
                {"name": "FLIGHT PA-101", "reference": "LEG-1", "leg": 1}
            ],
            "origin": {"node": "Manzanillo Port, Mexico" if mode == "SEA" else "Heathrow Airport, UK", "code": None},
            "destination": {"node": "Nhava Sheva Port, India" if mode == "SEA" else "Mumbai Airport, India", "code": None},
            "liability_regime": {
                "instrument": "Hague-Visby / COGSA" if mode == "SEA" else "Montreal Convention 1999",
                "limit_basis": "package_or_kg" if mode == "SEA" else "per_kg",
                "notice_period_days": 3 if mode == "SEA" else 14,
                "reference_version": "regimes@2026-01",
                "confirmed_by": "surveyor",
                "confirmed_at": "2026-08-15T10:00:00Z"
            }
        },
        "carriage_units": carriage_units,
        "weights": {
            "gross_kg": "24500.00",
            "net_kg": "22310.00",
            "volumetric_kg": None if mode == "SEA" else "18500.00",
            "chargeable_kg": None if mode == "SEA" else "24500.00",
            "vgm_kg": "24500.00" if mode == "SEA" else None
        },
        "blocks": [
            {
                "id": "b1",
                "type": "particulars",
                "rows": [
                    {"label": "Applicant", "value": ["Pacific Trading Co."]},
                    {"label": "Invoice Value", "value": [{"amount": "45000.00", "currency": "USD"}]},
                    {"label": "Declared Commodity", "value": ["Fresh Citrus / Mandarins"]}
                ]
            },
            {
                "id": "b2",
                "type": "narrative",
                "section": "ATTENDANCE & CIRCUMSTANCES",
                "clause": "attendance.standard@v1",
                "slots": {"vessel": "OCEAN VOYAGER", "location": "CFS Cold Store 1"},
                "additional_text": "Survey conducted under normal ambient conditions.",
                "source": "surveyor_entered"
            },
            {
                "id": "b3",
                "type": "measurements",
                "unit_system": "metric",
                "rows": [
                    {"subject": "pulp temperature", "method": "digital probe", "min": "1.2", "max": "1.8", "unit": "C"},
                    {"subject": "brix level", "method": "refractometer", "min": "10.5", "max": "11.2", "unit": "pct"}
                ]
            },
            {
                "id": "b4",
                "type": "table",
                "title": "Mandarin Quality Defect Breakdown",
                "unit": "pcs",
                "grouping_label": "Count / Box Size",
                "source": {"kind": "manual", "file": None, "sheet": None, "column_map": {}},
                "categories": [
                    {"key": "sound", "label": "Sound"},
                    {"key": "soft", "label": "Soft"},
                    {"key": "decay", "label": "Decay"},
                    {"key": "bruised", "label": "Bruised"},
                    {"key": "stem_end_rot", "label": "Stem End Rot"}
                ],
                "rows": [
                    {
                        "group": "Box Count 55",
                        "boxes_opened": 1,
                        "values": {
                            "sound": 133,
                            "soft": 54,
                            "decay": 14,
                            "bruised": 24,
                            "stem_end_rot": 9
                        }
                    }
                ]
            },
            {
                "id": "b5",
                "type": "photo_plate",
                "series_id": "survey",
                "label": "Survey Inspection Photos",
                "provenance": "own_survey",
                "columns": 2,
                "groups": [
                    {"id": "pg1", "observation": "External container doors and intact customs seal", "asset_ids": ["a1", "a2"]}
                ]
            },
            {
                "id": "b6",
                "type": "fixed_text",
                "key": "disclaimer@v1",
                "content": "Report issued without prejudice, subject to terms of carriage."
            }
        ],
        "assets": {
            "a1": {"kind": "photo", "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "original_path": "photos/a1.jpg"},
            "a2": {"kind": "photo", "sha256": "ca978112ca1bbdcafac231b39a23dc4da786081496a090b852924b17a1027170", "original_path": "photos/a2.jpg"}
        },
        "provenance": {
            "blocks.b4.rows[0].values.sound": {"source": "surveyor_entered", "confirmed_by": "surveyor"}
        }
    }


def create_synthetic_excel_with_formulas() -> bytes:
    """Creates an in-memory openpyxl workbook containing live =SUM() formulas."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Grapes QC"
    
    # Headers
    ws.append(["Sample No", "Sound (kg)", "Waterberry (kg)", "Decay (kg)", "Total (kg)"])
    
    # Row 1: 5.190, 0.606, 0.434 -> Sum = 6.230
    ws.append(["Sample 1", 5.190, 0.606, 0.434, "=SUM(B2:D2)"])
    # Row 2: 42.372, 1.658, 0.442 -> Sum = 44.472
    ws.append(["Sample 2", 42.372, 1.658, 0.442, "=SUM(B3:D3)"])
    # Row 3 (Totals): =SUM(B2:B3), =SUM(C2:C3), =SUM(D2:D3), =SUM(E2:E3)
    ws.append(["Grand Total", "=SUM(B2:B3)", "=SUM(C2:C3)", "=SUM(D2:D3)", "=SUM(E2:E3)"])
    
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def create_synthetic_image_with_exif(width: int = 1200, height: int = 900, camera_model: str = "SyntheticCam X1") -> bytes:
    """Creates an in-memory JPEG with embedded EXIF tags."""
    img = Image.new("RGB", (width, height), color=(73, 109, 137))
    exif = img.getexif()
    # 0x010F = Make, 0x0110 = Model, 0x0131 = Software, 0x9003 = DateTimeOriginal
    exif[0x010F] = "Synthetic Labs"
    exif[0x0110] = camera_model
    exif[0x0131] = "Marine Survey Firmware v1.0"
    exif[0x9003] = "2026:08:15 11:30:00"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif, quality=95)
    return buf.getvalue()

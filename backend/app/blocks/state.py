"""
Block State Pydantic Models — Master Spec §9.
Represents the complete JSON structure stored in reports.block_state JSONB.

CRITICAL RULES:
- No computed fields stored here; computed= fields in blocks are documentation only.
- Every block type is Optional (any block can be absent from a given report).
- transport.mode drives field-set selection at render time, not separate code paths.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class TransportMode(str, Enum):
    SEA = "SEA"
    AIR = "AIR"


class DocumentKind(str, Enum):
    BILL_OF_LADING = "BILL_OF_LADING"
    AIR_WAYBILL = "AIR_WAYBILL"


class UnitType(str, Enum):
    CONTAINER = "CONTAINER"
    ULD = "ULD"
    PALLET = "PALLET"
    LOOSE = "LOOSE"


class ReportFamily(str, Enum):
    SURVEY_REPORT = "SURVEY_REPORT"
    QC_REPORT = "QC_REPORT"


class ReportStatus(str, Enum):
    DRAFT = "DRAFT"
    FINAL = "FINAL"


class ProvenanceTag(str, Enum):
    SURVEYOR_ENTERED = "surveyor_entered"
    CSV_IMPORTED = "csv_imported"
    OCR_VERIFIED = "ocr_verified"
    DOCUMENT_EXTRACTED_CONFIRMED = "document_extracted_confirmed"
    COMPUTED = "computed"
    CLAUSE_LIBRARY = "clause_library"
    SURVEYOR_EDITED = "surveyor_edited"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class ReportMetadata(BaseModel):
    number: str                            # e.g. "M-102-2026"
    family: ReportFamily
    state: str = "DRAFT"
    template_id: str
    template_version: int = 1
    docx_template: str
    issued_date: Optional[str] = None      # ISO date
    place: Optional[str] = None
    licence_no: Optional[str] = None       # from env, not code
    status: ReportStatus = ReportStatus.DRAFT


class TransportDocument(BaseModel):
    kind: DocumentKind
    level: str = "MASTER"                  # MASTER / HOUSE
    number: str
    date: Optional[str] = None
    issuer: Optional[str] = None
    check_digit_valid: Optional[bool] = None   # computed, never auto-corrected


class Conveyance(BaseModel):
    name: str
    reference: str
    leg: int = 1
    transhipment_at: Optional[str] = None


class GeoNode(BaseModel):
    node: str
    code: Optional[str] = None             # IATA code for air


class LiabilityRegime(BaseModel):
    instrument: str
    limit_basis: str
    notice_period_days: Optional[int] = None
    reference_version: str
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[str] = None


class Transport(BaseModel):
    mode: TransportMode
    document: TransportDocument
    conveyances: List[Conveyance] = Field(default_factory=list)
    origin: Optional[GeoNode] = None
    destination: Optional[GeoNode] = None
    liability_regime: Optional[LiabilityRegime] = None


class CarriageUnit(BaseModel):
    id: str
    unit_type: UnitType
    identifier: Optional[str] = None
    identifier_valid: Optional[bool] = None   # computed check digit result
    iso_type: Optional[str] = None
    size: Optional[str] = None
    seal_no: Optional[str] = None
    marked_tare_kg: Optional[str] = None
    manufacture_date: Optional[str] = None
    # ULD-specific
    uld_type: Optional[str] = None
    owner_code: Optional[str] = None
    # LOOSE-specific
    pieces: Optional[int] = None


class Weights(BaseModel):
    gross_kg: Optional[str] = None
    net_kg: Optional[str] = None
    volumetric_kg: Optional[str] = None   # AIR only; "COMPUTED" means derive from dims
    chargeable_kg: Optional[str] = None   # AIR only; "COMPUTED"
    vgm_kg: Optional[str] = None          # SEA only


# ---------------------------------------------------------------------------
# Block models — one per block type
# ---------------------------------------------------------------------------

class ParticularsRow(BaseModel):
    label: str
    value: List[Any]                       # scalar, list, or money dict
    note: Optional[str] = None


class ParticularsBlock(BaseModel):
    id: str
    type: str = "particulars"
    scope: str = "SHIPMENT"
    rows: List[ParticularsRow] = Field(default_factory=list)


class NarrativeBlock(BaseModel):
    id: str
    type: str = "narrative"
    section: Optional[str] = None
    clause: Optional[str] = None          # clause library key@version
    slots: Dict[str, Any] = Field(default_factory=dict)
    additional_text: Optional[str] = None
    source: str = "surveyor_entered"
    surveyor_edited: bool = False


class MeasurementRow(BaseModel):
    subject: str
    qualifier: Optional[str] = None
    method: Optional[str] = None
    min: Optional[str] = None
    max: Optional[str] = None
    value: Optional[str] = None
    unit: str
    photo_group: Optional[str] = None


class MeasurementsBlock(BaseModel):
    id: str
    type: str = "measurements"
    unit_system: str = "metric"
    rows: List[MeasurementRow] = Field(default_factory=list)


class TableCategory(BaseModel):
    key: str
    label: str


class TableRow(BaseModel):
    group: str
    boxes_opened: Optional[int] = None
    values: Dict[str, Any]                 # category_key -> numeric (stored as-is; Decimal at compute time)
    container: Optional[str] = None        # printed only when the table's Container column is on


class TableSource(BaseModel):
    kind: str = "manual"                   # "manual" | "csv" | "xlsx"
    file: Optional[str] = None
    sheet: Optional[str] = None
    column_map: Dict[str, str] = Field(default_factory=dict)


class TableBlock(BaseModel):
    id: str
    type: str = "table"
    title: Optional[str] = None
    unit: str = "pcs"                      # pcs | kg | mt
    grouping_label: Optional[str] = None
    commodity: Optional[str] = None        # the fruit this table counts; one table per fruit
    show_container: bool = False           # print a Container column after the count column
    chart_title: Optional[str] = None      # under the graph; default by unit (render/findings.py)
    summary: Dict[str, Any] = Field(default_factory=dict)  # FINAL SUMMARY: {show, by: container|group, title}
    source: TableSource = Field(default_factory=TableSource)
    categories: List[TableCategory] = Field(default_factory=list)
    rows: List[TableRow] = Field(default_factory=list)
    # computed= fields are documentation; never stored
    source_mapping: Dict[str, Any] = Field(default_factory=dict)


class PhotoGroup(BaseModel):
    id: str
    observation: str
    asset_ids: List[str] = Field(default_factory=list)


class PhotoPlateBlock(BaseModel):
    id: str
    type: str = "photo_plate"
    series_id: str
    label: str
    provenance: str = "own_survey"         # own_survey | consignee_cha | shipper_load_port
    columns: int = 2
    groups: List[PhotoGroup] = Field(default_factory=list)


class FixedTextBlock(BaseModel):
    id: str
    type: str = "fixed_text"
    key: str                               # e.g. "disclaimer@v2"
    content: Optional[str] = None         # actual text fetched from clauses table at render


# ---------------------------------------------------------------------------
# Week 3 Block Models — Master Spec §7, §8, §9, §14
# ---------------------------------------------------------------------------

class PartiesRow(BaseModel):
    role: str                              # "Insurers", "Insured", "Consignees", etc.
    name: str
    details: Optional[str] = None


class PartiesBlock(BaseModel):
    id: str
    type: str = "parties"
    scope: str = "SHIPMENT"
    rows: List[PartiesRow] = Field(default_factory=list)


class AttendanceRow(BaseModel):
    name: str
    designation: str
    representing: str


class AttendanceBlock(BaseModel):
    id: str
    type: str = "attendance"
    scope: str = "SHIPMENT"
    rows: List[AttendanceRow] = Field(default_factory=list)


class TimelineRow(BaseModel):
    event: str                             # "DISCHARGE", "SURVEY", "FLIGHT_ARRIVAL", etc.
    date: str                              # ISO format "YYYY-MM-DD"
    location: Optional[str] = None
    basis: Optional[str] = "as reported"


class TimelineBlock(BaseModel):
    id: str
    type: str = "timeline"
    scope: str = "SHIPMENT"
    rows: List[TimelineRow] = Field(default_factory=list)


class ReconciliationRow(BaseModel):
    subject: str                           # Container number or description
    slip_no: Optional[str] = None
    slip_date: Optional[str] = None
    gross: Optional[str] = None            # Gross weighbridge weight
    container_tare: Optional[str] = None   # Tare weight
    trailer_tare: Optional[str] = None     # Trailer tare weight
    reference: Optional[str] = None        # Declared weight (e.g. B/L gross)
    note: Optional[str] = None


class ReconciliationBlock(BaseModel):
    id: str
    type: str = "reconciliation"
    title: Optional[str] = "Weight Reconciliation"
    formula: str = "GROSS_MINUS_CONTAINER_TARE"
    reference_label: Optional[str] = "Gross weight of cargo as per Bill of Lading"
    annexure_prefix: Optional[str] = None
    scope: str = "SHIPMENT"               # "SHIPMENT" or "UNIT"
    rolls_up_from: Optional[str] = None   # ID of per-unit reconciliation block to aggregate
    rows: List[ReconciliationRow] = Field(default_factory=list)


class UnitGroupBlock(BaseModel):
    id: str
    type: str = "unit_group"
    repeat_for: str = "carriage_units"
    heading_template: str = "{index}) CONDITION OF CONTAINER NO. {identifier} & CARGO: (SEE {photo_ref})"
    photo_numbering: str = "SHARED_SERIES_SEGMENTED"  # "SHARED_SERIES_SEGMENTED" | "SERIES_PER_UNIT"
    blocks: List[Dict[str, Any]] = Field(default_factory=list)


class AnnexureRow(BaseModel):
    prefix: str = "A"                      # Series prefix (A, B, C...)
    title: str
    asset_id: Optional[str] = None
    file_path: Optional[str] = None
    sub_id: Optional[str] = None           # Computed: A1, A2, etc.


class AnnexuresBlock(BaseModel):
    id: str
    type: str = "annexures"
    scope: str = "SHIPMENT"
    rows: List[AnnexureRow] = Field(default_factory=list)


class InventoryDamage(BaseModel):
    description: str
    severity: Optional[str] = None        # "CRUSHED", "BENT", "BROKEN", etc.
    photo_ref: Optional[str] = None


class InventoryPart(BaseModel):
    part_no: Optional[str] = None
    description: str
    quantity: int = 1
    damages: List[InventoryDamage] = Field(default_factory=list)


class InventoryPackage(BaseModel):
    package_no: str
    package_type: str                     # "WOODEN_CRATE", "CASE", "PALLET", etc.
    contents: str
    parts: List[InventoryPart] = Field(default_factory=list)


class InventoryBlock(BaseModel):
    id: str
    type: str = "inventory"
    scope: str = "SHIPMENT"
    packages: List[InventoryPackage] = Field(default_factory=list)


# Union of all supported block types
AnyBlock = Union[
    ParticularsBlock,
    NarrativeBlock,
    MeasurementsBlock,
    TableBlock,
    PhotoPlateBlock,
    FixedTextBlock,
    PartiesBlock,
    AttendanceBlock,
    TimelineBlock,
    ReconciliationBlock,
    UnitGroupBlock,
    AnnexuresBlock,
    InventoryBlock,
]


class AssetRecord(BaseModel):
    kind: str                              # photo | pdf | xlsx
    sha256: str
    original_path: str
    derived: Dict[str, str] = Field(default_factory=dict)
    exif: Dict[str, Any] = Field(default_factory=dict)
    exif_integrity: str = "INTACT"


class ProvenanceRecord(BaseModel):
    source: ProvenanceTag
    confidence: Optional[float] = None
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[str] = None


class AuditEntry(BaseModel):
    at: str
    actor: str
    action: str
    path: str
    before: Optional[Any] = None
    after: Optional[Any] = None


# ---------------------------------------------------------------------------
# Root Block State
# ---------------------------------------------------------------------------

class BlockState(BaseModel):
    """
    The single source of truth for a report. Stored as JSONB in reports.block_state.
    Everything in the generated document derives from this at render time.
    CRITICAL RULE: Never store computed values here.
    """
    metadata: ReportMetadata
    transport: Transport
    carriage_units: List[CarriageUnit] = Field(default_factory=list)
    weights: Weights = Field(default_factory=Weights)
    blocks: List[Dict[str, Any]] = Field(default_factory=list)  # raw dicts; typed at compute time
    assets: Dict[str, AssetRecord] = Field(default_factory=dict)
    provenance: Dict[str, ProvenanceRecord] = Field(default_factory=dict)
    audit: List[AuditEntry] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


"""
E2E Test Suite Fixtures and Configuration.
Provides synthetic fixtures, data payloads, and test runners for progressive testability.
"""

import pytest
from decimal import Decimal
from tests.e2e.helpers.synthetic_data import (
    make_synthetic_block_state,
    create_synthetic_excel_with_formulas,
    create_synthetic_image_with_exif,
    MANDARIN_ROW,
    MANDARIN_COL_TOTALS,
    GRAPES_ROW,
    GRAPES_TOTALS
)
from tests.e2e.helpers.api_client import E2EApiClient


@pytest.fixture(scope="session")
def api_client():
    """Provides an instance of E2EApiClient."""
    return E2EApiClient()


@pytest.fixture
def synthetic_state_sea():
    """Returns a valid SEA mode BlockState dict."""
    return make_synthetic_block_state(mode="SEA", multi_unit=False)


@pytest.fixture
def synthetic_state_air():
    """Returns a valid AIR mode BlockState dict."""
    return make_synthetic_block_state(mode="AIR", multi_unit=False)


@pytest.fixture
def synthetic_state_multi_unit():
    """Returns a valid SEA multi-unit BlockState dict."""
    return make_synthetic_block_state(mode="SEA", multi_unit=True)


@pytest.fixture
def excel_with_sum_formulas():
    """Returns raw bytes of an Excel workbook containing live =SUM() formulas."""
    return create_synthetic_excel_with_formulas()


@pytest.fixture
def sample_photo_jpeg():
    """Returns raw bytes of a test JPEG with EXIF metadata."""
    return create_synthetic_image_with_exif(1200, 900)


@pytest.fixture
def mandarin_data():
    """Returns exact reference datasets for Mandarin calculations."""
    return {
        "row": MANDARIN_ROW,
        "col_totals": MANDARIN_COL_TOTALS
    }


@pytest.fixture
def grapes_data():
    """Returns exact reference datasets for Grapes calculations."""
    return {
        "row": GRAPES_ROW,
        "totals": GRAPES_TOTALS
    }

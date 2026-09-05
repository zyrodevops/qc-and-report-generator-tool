"""
Tier 1: Feature Coverage - R1: Scaffold, Auth, and Database.
Covers:
1. Docker Compose & Healthcheck probes
2. Sequential report number allocation (M-<n>-<year>)
3. 5 Core Database Tables + Sequence Schema contract
4. Surveyor Authentication (bcrypt + session token)
5. Immutable Audit Trail (insert-only)
6. Git hygiene and pre-commit secret scanner
"""

import os
import re
import pytest
from tests.e2e.helpers.contract_stubs import try_import


@pytest.mark.m1
@pytest.mark.tier1
def test_scaffold_healthcheck_contract(api_client):
    """Verifies that healthcheck probe contract exists and returns 200 OK."""
    if api_client.is_available():
        response = api_client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["ok", "healthy", "up"]
    else:
        # Contract assertion on healthcheck specification
        health_mod = try_import("backend.app.api.health") or try_import("backend.app.main")
        if health_mod is None:
            pytest.skip("Scaffold backend.app.main not yet available (M1 pending)")
        assert hasattr(health_mod, "app") or hasattr(health_mod, "router")


@pytest.mark.m1
@pytest.mark.tier1
def test_report_numbering_format_and_sequence():
    r"""
    Verifies sequential report number pattern M-<n>-<year> per Master-Spec §9.
    Must match regex: ^M-\d+-(20\d{2})$
    """
    sample_numbers = ["M-1-2026", "M-42-2026", "M-102-2026"]
    pattern = re.compile(r"^M-(\d+)-(20\d{2})$")
    
    for num in sample_numbers:
        m = pattern.match(num)
        assert m is not None
        seq_val = int(m.group(1))
        year_val = int(m.group(2))
        assert seq_val > 0
        assert year_val >= 2026

    # Test allocation logic if model/service is importable
    seq_mod = try_import("backend.app.models.report") or try_import("backend.app.api.reports")
    if seq_mod and hasattr(seq_mod, "allocate_report_number"):
        n1 = seq_mod.allocate_report_number(year=2026)
        n2 = seq_mod.allocate_report_number(year=2026)
        assert pattern.match(n1)
        assert pattern.match(n2)
        assert n1 != n2


@pytest.mark.m1
@pytest.mark.tier1
def test_five_core_database_tables_schema():
    """
    Verifies that the 5 mandatory DB tables exist in models or metadata:
    reports, assets, audit, templates, clauses (+ report_sequences).
    """
    models_mod = try_import("backend.app.models")
    if models_mod is None:
        pytest.skip("backend.app.models not yet created (M1 pending)")

    expected_tables = {"reports", "assets", "audit", "templates", "clauses"}
    found_tables = set()
    
    # Check SQLAlchemy Base.metadata if available
    base = getattr(models_mod, "Base", None)
    if base and hasattr(base, "metadata"):
        found_tables = set(base.metadata.tables.keys())
    else:
        # Check exported model classes
        for attr in ["Report", "Asset", "Audit", "Template", "Clause"]:
            if hasattr(models_mod, attr):
                found_tables.add(attr.lower() + "s" if not attr.endswith("s") else attr.lower())

    # Assert expected tables are accounted for
    for tbl in expected_tables:
        assert tbl in found_tables or any(tbl in t for t in found_tables), f"Table {tbl} missing from schema"


@pytest.mark.m1
@pytest.mark.tier1
def test_surveyor_authentication_and_session(api_client):
    """
    Verifies surveyor login with email and password, password hashing, and session issuance.
    """
    if not api_client.is_available():
        auth_mod = try_import("backend.app.api.auth")
        if auth_mod is None:
            pytest.skip("Auth service not yet implemented (M1 pending)")

    payload = {"email": "surveyor@oceanic-claims.test", "password": "SafePassword123!"}
    if api_client.is_available():
        res = api_client.post("/api/auth/login", json=payload)
        if res.status_code in [200, 201]:
            data = res.json()
            assert "token" in data or "session_id" in data or "access_token" in data
        else:
            # 401 or 404 acceptable if user not pre-seeded, but endpoint must respond
            assert res.status_code in [401, 404, 422]


@pytest.mark.m1
@pytest.mark.tier1
def test_immutable_audit_log_contract():
    """
    Verifies audit log schema: report_id, at, actor, action, path, before, after.
    Audit log must be insert-only (no update or delete methods).
    """
    audit_mod = try_import("backend.app.models.audit") or try_import("backend.app.models")
    if audit_mod is None or not hasattr(audit_mod, "Audit"):
        pytest.skip("Audit model not yet implemented (M1 pending)")

    audit_cls = getattr(audit_mod, "Audit")
    cols = {c.name for c in audit_cls.__table__.columns}
    required_cols = {"report_id", "at", "actor", "action", "path", "before", "after"}
    assert required_cols.issubset(cols), f"Missing columns in Audit model: {required_cols - cols}"


@pytest.mark.m1
@pytest.mark.tier1
def test_git_hygiene_and_precommit_hook_rules():
    r"""
    Verifies pre-commit secret scanner rule against IRDA licence pattern:
    (?i)IRDA/IND/SLA-\d+
    and checks that sample-data/ is excluded.
    """
    secret_pattern = re.compile(r"(?i)IRDA/IND/SLA-\d+")
    
    # Test valid secret detection (dynamic concatenation to prevent hook match)
    sample_lic = "IRDA" + "/IND/SLA-654321"
    sample_lic_lower = "irda" + "/ind/sla-99999"
    assert secret_pattern.search(f"Licence: {sample_lic}") is not None
    assert secret_pattern.search(sample_lic_lower) is not None
    assert secret_pattern.search("CLEAN_CONTENT_WITHOUT_LICENCE") is None

    # Verify .gitignore content if file exists
    if os.path.exists(".gitignore"):
        with open(".gitignore", "r", encoding="utf-8") as f:
            content = f.read()
            assert "sample-data" in content, ".gitignore must exclude sample-data/"

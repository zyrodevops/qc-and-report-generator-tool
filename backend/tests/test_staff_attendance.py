import docx
import pytest
from app.seeds.staff_lookup import lookup_consignee_staff, get_default_attendance
from app.render.docx.engine import render_narrative
from app.render.html.engine import render_narrative_html

def test_lookup_consignee_staff():
    # 1. Hari Agro Products
    hari = lookup_consignee_staff("Hari Agro Products")
    assert len(hari) >= 1
    assert any("Rajendra Ambre" in m["name"] for m in hari)

    # 2. Reliance Retail Ltd
    reliance = lookup_consignee_staff("M/s Reliance Retail Limited, Navi Mumbai")
    assert len(reliance) == 2
    assert any("Yogi Pokal" in m["name"] for m in reliance)
    assert any("Chetan Khatre" in m["name"] for m in reliance)

    # 3. NGK Trading
    ngk = lookup_consignee_staff("NGK Trading Company Pvt. Ltd")
    assert len(ngk) >= 1
    assert any("Ramesh Kadam" in m["name"] for m in ngk)

    # 4. RK & Co
    rk = lookup_consignee_staff("RK & Co.")
    assert len(rk) >= 1
    assert any("Rajesh Mishra" in m["name"] for m in rk)

    # 5. Firangi Fresh
    firangi = lookup_consignee_staff("Firangi Fresh")
    assert len(firangi) >= 1
    assert any("Rajesh Kumar" in m["name"] for m in firangi)

def test_get_default_attendance():
    # Without consignee: has MCA surveyor
    att_default = get_default_attendance("")
    assert len(att_default) == 1
    assert "Baburao Bhosale" in att_default[0]["name"]
    assert "Marine Cargo Agencies" in att_default[0]["representing"]

    # With consignee: has client staff + MCA surveyor
    att_hari = get_default_attendance("Hari Agro Products")
    assert len(att_hari) == 2
    assert "Rajendra Ambre" in att_hari[0]["name"]
    assert "Baburao Bhosale" in att_hari[1]["name"]

def test_render_narrative_docx_and_html():
    block = {
        "id": "b_para1",
        "type": "narrative",
        "section": "PARAGRAPH 1: APPLICATION",
        "additional_text": "Pursuant to the Consignee's request and subsequent appointment...",
        "attendance_intro": "The following persons attended the survey:",
        "attendance": [
            {
                "name": "Mr. Rajendra Ambre",
                "designation": "Sales Manager",
                "representing": "Hari Agro Products - (Consignees)",
            },
            {
                "name": "Mr. Baburao Bhosale",
                "designation": "Surveyor",
                "representing": "Marine Cargo Agencies Pvt.Ltd (On behalf of Consignees)",
            },
        ],
    }

    # DOCX
    doc = docx.Document()
    render_narrative(doc, block)
    assert len(doc.tables) == 1
    table = doc.tables[0]
    assert len(table.rows) == 3
    headers = [c.text for c in table.rows[0].cells]
    assert headers == ["Name", "Designation", "Representing"]
    row1 = [c.text for c in table.rows[1].cells]
    assert "Rajendra Ambre" in row1[0]
    assert "Sales Manager" in row1[1]

    # HTML
    html = render_narrative_html(block)
    assert "PARAGRAPH 1: APPLICATION" in html
    assert "The following persons attended the survey:" in html
    assert "preview-table" in html
    assert "Rajendra Ambre" in html
    assert "Baburao Bhosale" in html

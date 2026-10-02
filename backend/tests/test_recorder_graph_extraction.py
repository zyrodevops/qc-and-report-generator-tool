import io
from pathlib import Path
from PIL import Image
from docx import Document
import pytest

from app.render.recorder_chart import extract_recorder_graph, chart_for
from app.render.docx.engine import render_recorders
from app.render.html.engine import render_recorders_html


def _create_sample_graph_pdf() -> bytes:
    """Create a sample PDF containing a visual temperature recorder graph."""
    # Create an image simulating a recorder page with summary and chart
    im = Image.new("RGB", (600, 800), color="white")
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    # Header & summary
    d.text((30, 20), "Data Report Data Logger", fill="black")
    d.text((30, 50), "Logging Summary", fill="black")
    d.rectangle([30, 70, 570, 180], outline="black", width=1)
    d.text((40, 80), "Device ID: 260179540H", fill="black")
    d.text((40, 100), "Highest Temperature: 6.5 C", fill="black")
    
    # Visual chart section (below summary)
    d.text((30, 240), "Temperature[C]", fill="black")
    d.rectangle([50, 260, 550, 680], outline="black", width=2)
    # Grid lines
    for y in range(300, 680, 50):
        d.line([50, y, 550, y], fill="gray", width=1)
    # Waveform curve
    pts = [(50 + i * 5, 450 + int(30 * ((i % 5) - 2))) for i in range(100)]
    d.line(pts, fill="blue", width=2)
    # Alarm threshold line
    d.line([50, 350, 550, 350], fill="red", width=1)
    d.text((555, 345), "8.0 C", fill="red")
    # Dates
    d.text((50, 690), "05/08/26 11:07:53", fill="black")
    d.text((450, 690), "07/24/26 05:57:53", fill="black")
    # Footer
    d.line([30, 750, 570, 750], fill="black", width=1)
    d.text((280, 760), "1/1", fill="black")

    buf = io.BytesIO()
    im.save(buf, format="PDF", resolution=150.0)
    return buf.getvalue()


def test_extract_recorder_graph_success():
    pdf_bytes = _create_sample_graph_pdf()
    extracted = extract_recorder_graph(pdf_bytes)
    assert extracted is not None
    assert extracted.startswith(bytes([0x89]) + b"PNG")

    # Verify extracted image has sensible dimensions (chart only, cropped cleanly)
    im = Image.open(io.BytesIO(extracted))
    w, h = im.size
    assert w > 300
    assert h > 200


def test_extract_recorder_graph_ignores_non_graph_pdf():
    # Pure text PDF without visual graph curves
    im = Image.new("RGB", (600, 800), color="white")
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    d.text((30, 20), "Just plain text invoice", fill="black")
    buf = io.BytesIO()
    im.save(buf, format="PDF")
    
    extracted = extract_recorder_graph(buf.getvalue())
    assert extracted is None


def test_chart_for_with_authentic_extracted_graph(tmp_path, monkeypatch):
    import app.render.recorder_chart as rc
    monkeypatch.setattr(rc.settings, "UPLOAD_DIR", tmp_path)

    doc_dir = tmp_path / "rep1" / "documents"
    doc_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_bytes = _create_sample_graph_pdf()
    pdf_path = doc_dir / "abc12345.pdf"
    pdf_path.write_bytes(pdf_bytes)

    readings_file = "rep1/documents/abc12345.readings.json"
    (doc_dir / "abc12345.readings.json").write_text("[]", encoding="utf-8")

    rec = {
        "device_id": "260179540H",
        "container": "CONT1234567",
        "readings_file": readings_file,
    }

    # Calling chart_for should extract and return the authentic graph from sibling pdf
    chart_bytes = chart_for(rec, set_point="0")
    assert chart_bytes is not None
    assert chart_bytes.startswith(bytes([0x89]) + b"PNG")

    # It should have cached abc12345.graph.png
    cached_graph = doc_dir / "abc12345.graph.png"
    assert cached_graph.exists()
    assert cached_graph.read_bytes() == chart_bytes

    # Second call uses the cached graph directly
    chart_bytes_cached = chart_for(rec, set_point="0")
    assert chart_bytes_cached == chart_bytes


def test_docx_and_html_render_with_authentic_graph(tmp_path, monkeypatch):
    import app.render.recorder_chart as rc
    monkeypatch.setattr(rc.settings, "UPLOAD_DIR", tmp_path)

    doc_dir = tmp_path / "rep2" / "documents"
    doc_dir.mkdir(parents=True, exist_ok=True)
    
    # Save authentic graph png directly as graph_file
    sample_img = Image.new("RGB", (400, 200), color="blue")
    buf = io.BytesIO()
    sample_img.save(buf, format="PNG")
    graph_bytes = buf.getvalue()
    (doc_dir / "test_rec.graph.png").write_bytes(graph_bytes)

    block = {
        "type": "temperature_recorders",
        "title": "TEMPERATURE RECORDER SUMMARY",
        "show_chart": True,
        "included": True,
        "set_point_c": "0",
        "recorders": [{
            "device_id": "REC999",
            "container": "MEDU1234567",
            "graph_file": "rep2/documents/test_rec.graph.png",
            "highest_c": "5.0",
            "lowest_c": "0.0",
        }],
    }

    # DOCX engine embeds picture
    doc = Document()
    render_recorders(doc, block)
    assert len(doc.inline_shapes) == 1

    # HTML engine embeds base64 image
    html_out = render_recorders_html(block)
    assert "data:image/png;base64," in html_out
    assert "TEMPERATURE RECORDER SUMMARY" in html_out

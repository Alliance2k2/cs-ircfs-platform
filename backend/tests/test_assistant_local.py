import io
from types import SimpleNamespace
import asyncio
import zipfile

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.services import assistant
from app.services.rag.citations import attribute_quotations
from app.services.rag.extraction_worker import extract_isolated


def test_missing_citation_is_attributed_only_to_exact_authorized_text():
    sources = [{"id": "guide", "text": "Use main-menu option 0 to change language."}]
    assert attribute_quotations(sources[0]["text"], sources).endswith("[guide]")
    for text in ["Use option 9 to change language.", "Use main-menu option 0 to change language. [forged]", "Use main-menu option 0 to change language. This is institutionally approved."]:
        with pytest.raises(ValueError):
            attribute_quotations(text, sources)


@pytest.mark.parametrize("name,data", [("guide.txt", b"Synthetic maintenance procedure."), ("guide.md", b"# Synthetic guide\n\nInspect the isolation checklist.")])
def test_actual_bounded_worker_preserves_text(name, data):
    result = extract_isolated(name, data)
    assert "Synthetic" in result.pages[0]
    assert len(result.digest) == 64


def test_actual_bounded_worker_pdf_docx_and_bad_input():
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
    writer = PdfWriter()
    page = writer.add_blank_page(width=600, height=800)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 50 750 Td (Synthetic maintenance procedure.) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    pdf = io.BytesIO()
    writer.write(pdf)
    assert "Synthetic" in extract_isolated("synthetic.pdf", pdf.getvalue()).pages[0]
    docx = io.BytesIO()
    with zipfile.ZipFile(docx, "w") as package:
        package.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>Synthetic document.</w:t></w:r></w:p></w:document>')
    assert "Synthetic" in extract_isolated("synthetic.docx", docx.getvalue()).pages[0]
    for name, data in [("bad.pdf", b"invalid"), ("bad.docx", b"not zip"), ("bad.exe", b"not supported")]:
        with pytest.raises(ValueError):
            extract_isolated(name, data)
    with pytest.raises(ValueError, match="resource limits"):
        extract_isolated("slow.txt", b"Synthetic procedure.", timeout=0.001)


def test_library_selection_cannot_disclose_unavailable_sources(client):
    library = client.get("/api/v1/assistant/sources").json()
    assert len(library) == 6 and all("text" not in row for row in library)
    response = client.post("/api/v1/assistant/ask", json={"question": "pump inspection", "selected_references": ["knowledge:unauthorized"]})
    assert response.status_code == 403
    selected = next(row["reference"] for row in library if "language" in row["title"])
    answer = client.post("/api/v1/assistant/ask", json={"question": "How do I change USSD language?", "selected_references": [selected]}).json()
    assert answer["sources"] and all(f"packaged:{row['id']}" == selected for row in answer["sources"])


def test_local_generation_can_use_reviewed_documents_without_external_provider(monkeypatch):
    settings = Settings(_env_file=None, assistant_generation_enabled=True, assistant_provider="llamacpp", assistant_model="fixture", assistant_local_api_key=SecretStr("synthetic-local-key"))
    monkeypatch.setattr(assistant, "get_settings", lambda: settings)
    actual_client = httpx.AsyncClient

    def transport(request):
        assert str(request.url) == "http://127.0.0.1:11435/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer synthetic-local-key"
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": "Record the isolation checklist before synthetic maintenance."}}], "usage": {"completion_tokens": 10}})

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: actual_client(transport=httpx.MockTransport(transport), **kw))
    source = dict(id="fixture", title="Synthetic maintenance", text="Record the isolation checklist before synthetic maintenance.", reference="knowledge:fixture", document_id="fixture", revision="abc")
    result = asyncio.run(assistant.respond("isolation checklist", additional_sources=[source], selected_references=[source["reference"]]))
    assert result["mode"] == "generated" and "[fixture]" in result["answer"]


def test_local_status_reports_unavailable_instead_of_ready(client, monkeypatch):
    import app.api.routes.assistant as route
    monkeypatch.setattr(route, "get_settings", lambda: Settings(_env_file=None, assistant_generation_enabled=True, assistant_provider="llamacpp", assistant_model="fixture"))
    actual_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: actual_client(transport=httpx.MockTransport(lambda request: httpx.Response(503)), **kw))
    result = client.get("/api/v1/assistant/config").json()
    assert result["generation_ready"] is False and result["generation_status"] == "offline"

import io
import zipfile

import pytest

from app.services.rag.chunking import chunk_pages
from app.services.rag.ingestion import MAX_BYTES, extract


@pytest.mark.parametrize("name,data", [("x.txt", b"Hello\r\nworld"), ("x.md", b"# Title\n\nBody"), ("x.csv", b"crop,value\nmaize,12"), ("x.json", b'{"crop":"maize"}')])
def test_text_extraction_hash_is_stable_and_formats_supported(name, data):
    result = extract(name, data)
    assert result == extract(name, data)
    assert len(result.digest) == 64
    assert result.pages


@pytest.mark.parametrize("name,data", [("x.exe", b"abc"), ("x.txt", b""), ("x.txt", b"x" * (MAX_BYTES + 1)), ("x.json", b"{bad"), ("x.txt", b"\xff"), ("x.pdf", b"not pdf"), ("x.docx", b"bad zip")], ids=["type", "empty", "size", "json", "utf8", "pdf", "docx"])
def test_bad_files_fail_closed(name, data):
    with pytest.raises(ValueError):
        extract(name, data)


def docx(xml):
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w") as archive:
        archive.writestr("word/document.xml", xml)
    return result.getvalue()


def test_docx_extraction_and_entity_refusal():
    xml = b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>Rainfall procedure</w:t></w:r></w:p></w:document>'
    assert extract("guide.docx", docx(xml)).pages == ("Rainfall procedure",)
    with pytest.raises(ValueError):
        extract("bad.docx", docx(b'<!DOCTYPE x [<!ENTITY y "poison">]><x>&y;</x>'))


@pytest.mark.parametrize("strategy", ["fixed", "recursive", "paragraph", "heading", "token"])
def test_chunking_has_bounded_overlap_and_page_provenance(strategy):
    chunks = chunk_pages([" ".join(f"word{i}" for i in range(100)), "page two"], size=32, overlap=4, strategy=strategy)
    assert all(len(chunk.text.split()) <= 32 for chunk in chunks)
    assert chunks[-1].page == 2
    first, second = chunks[:2]
    assert first.text.split()[-4:] == second.text.split()[:4]
    assert [chunk.ordinal for chunk in chunks] == list(range(len(chunks)))


def test_invalid_chunk_parameters_and_heading():
    with pytest.raises(ValueError):
        chunk_pages(["text"], size=32, overlap=32)
    chunks = chunk_pages(["# Irrigation\n\nApproved engineering notes"], strategy="heading")
    assert chunks[0].heading == "Irrigation"


def test_real_pdf_extraction_page_references_encryption_and_empty_scans():
    pypdf = pytest.importorskip("pypdf", reason="Optional PDF extraction requirements not installed")
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
    writer = pypdf.PdfWriter()
    for text in ("Synthetic pump procedure", "Second page evidence"):
        page = writer.add_blank_page(width=600, height=800)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
    data = io.BytesIO()
    writer.write(data)
    result = extract("fixture.pdf", data.getvalue())
    assert len(result.pages) == 2 and "Second page" in result.pages[1]
    assert chunk_pages(result.pages)[-1].page == 2
    writer.encrypt("synthetic-only")
    encrypted = io.BytesIO()
    writer.write(encrypted)
    with pytest.raises(ValueError):
        extract("encrypted.pdf", encrypted.getvalue())
    blank = pypdf.PdfWriter()
    blank.add_blank_page(width=600, height=800)
    empty = io.BytesIO()
    blank.write(empty)
    with pytest.raises(ValueError, match="No readable text"):
        extract("scanned.pdf", empty.getvalue())

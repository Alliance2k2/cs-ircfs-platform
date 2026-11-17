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

"""Bounded text extraction; never executes macros, links, HTML or embedded files."""
import csv
import hashlib
import io
import json
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import PurePath
from xml.etree import ElementTree

MAX_BYTES = 5 * 1024 * 1024
MAX_TEXT = 1_000_000
MAX_PAGES = 200
EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv", ".json"}


@dataclass(frozen=True)
class Extracted:
    digest: str
    pages: tuple[str, ...]
    extension: str


def clean(text):
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(re.sub(r"[^\S\n]+", " ", line).strip() for line in text.splitlines()
                     if not any(unicodedata.category(c) == "Cs" for c in line)).replace("\x00", "").strip()


def extract(filename: str, data: bytes) -> Extracted:
    extension = PurePath(filename).suffix.lower()
    if extension not in EXTENSIONS or not data or len(data) > MAX_BYTES:
        raise ValueError("Unsupported file type or file exceeds 5 MiB")
    if extension == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise ValueError("Invalid PDF signature")
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError("PDF parser unavailable; install optional RAG extraction requirements") from exc
        try:
            reader = PdfReader(io.BytesIO(data), strict=True)
            if reader.is_encrypted or len(reader.pages) > MAX_PAGES:
                raise ValueError("Encrypted or excessive-page PDF refused")
            pages = []
            total = 0
            for page in reader.pages:
                # pypdf itself is not a CPU/memory sandbox. Run public/untrusted PDF
                # extraction in a constrained worker before allowing public uploads.
                content = page.extract_text() or ""
                total += len(content)
                if total > MAX_TEXT:
                    raise ValueError("Extracted text too large")
                pages.append(content)
        except Exception as exc:
            raise ValueError("PDF extraction failed or exceeded limits") from exc
    elif extension == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entries = archive.infolist()
                if len(entries) > 2000 or sum(e.file_size for e in entries) > 20 * MAX_BYTES:
                    raise ValueError("Excessive archive expansion")
                if any(e.flag_bits & 1 or "vbaproject" in e.filename.lower() for e in entries):
                    raise ValueError("Encrypted/macro archive refused")
                info = archive.getinfo("word/document.xml")
                if info.file_size > 4 * MAX_TEXT:
                    raise ValueError("Document XML too large")
                xml = archive.read(info)
                if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
                    raise ValueError("XML declarations refused")
                root = ElementTree.fromstring(xml)
                ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
                pages = ["\n".join("".join(node.itertext()) for node in root.iter(ns + "p"))]
        except (zipfile.BadZipFile, KeyError, ElementTree.ParseError, RuntimeError) as exc:
            raise ValueError("Invalid DOCX") from exc
    else:
        try:
            text = data.decode("utf-8-sig")
            if extension == ".json":
                text = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
            elif extension == ".csv":
                # Bound field size without changing csv's global process setting.
                text = "\n".join(" | ".join(row) for row in csv.reader(io.StringIO(text)))
            pages = [text]
        except (UnicodeError, ValueError, RecursionError, csv.Error) as exc:
            raise ValueError("Invalid UTF-8 structured document") from exc
    if sum(len(page) for page in pages) > MAX_TEXT:
        raise ValueError("Extracted text too large")
    pages = tuple(clean(page) for page in pages)
    if not any(pages):
        raise ValueError("No readable text; OCR is not provided")
    return Extracted(hashlib.sha256(data).hexdigest(), pages, extension)

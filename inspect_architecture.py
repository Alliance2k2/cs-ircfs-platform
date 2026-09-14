"""Print readable Word paragraphs and table rows for review."""
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import sys

sys.stdout.reconfigure(encoding="utf-8")

DOC = Path(__file__).with_name("cs-ircfs-platform-architecture.docx")
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def text(element):
    return "".join(node.text or "" for node in element.findall(".//w:t", NS)).strip()


with ZipFile(DOC) as archive:
    document = ET.fromstring(archive.read("word/document.xml"))
    body = document.find("w:body", NS)
    for child in body:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            value = text(child)
            if value:
                style = child.find("w:pPr/w:pStyle", NS)
                label = style.get(f"{{{NS['w']}}}val") if style is not None else "text"
                print(f"[{label}] {value}")
        elif tag == "tbl":
            print("[TABLE]")
            for row in child.findall("w:tr", NS):
                print(" | ".join(text(cell) for cell in row.findall("w:tc", NS)))

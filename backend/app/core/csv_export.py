"""CSV downloads that are safe to open in a spreadsheet.

Two problems this solves:

* **Formula injection.** Excel and LibreOffice execute a cell that begins with ``=``, ``+``,
  ``-``, ``@``, a tab or a carriage return. Report text (pest names, grievance-free fields,
  scheme names) is user-supplied, so a prefix apostrophe is added to keep it text.
* **Kinyarwanda mojibake.** Excel assumes the system code page for a CSV without a byte-order
  mark, so UTF-8 text arrives garbled. The BOM is written first.

Use :func:`csv_download` for every export so both rules are applied in one place.
"""
import csv
import io

from fastapi.responses import StreamingResponse

BOM = "\ufeff"
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value: object) -> str:
    """One CSV cell as text, with spreadsheet formulas neutralised."""
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    return "'" + text if text.startswith(FORMULA_PREFIXES) else text


def csv_download(filename: str, header: list[str], rows) -> StreamingResponse:
    """A UTF-8 CSV attachment built from ``header`` and an iterable of rows."""
    buffer = io.StringIO()
    buffer.write(BOM)
    writer = csv.writer(buffer)
    writer.writerow(header)
    for row in rows:
        writer.writerow([safe_cell(cell) for cell in row])
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

"""Validate foreign keys supplied in request bodies before any write."""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import Cell, FieldUser, IrrigationScheme


def require_if_provided(db: Session, model, value: int | None, field_name: str) -> None:
    if value is not None and not db.get(model, value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} does not reference an existing record",
        )


def validate_report_references(db: Session, reporter_id: int | None, scheme_id: int | None, cell_id: int | None) -> None:
    require_if_provided(db, FieldUser, reporter_id, "reporter_id")
    require_if_provided(db, Cell, cell_id, "cell_id")
    require_if_provided(db, IrrigationScheme, scheme_id, "scheme_id")

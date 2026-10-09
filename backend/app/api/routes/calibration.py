"""Editable calibration reference data (WP7): grievance categories and scheme assets.

These two lists drive the USSD menus (options 5 and 4). They move from code
constants into tables so the district can edit them without a deployment.
Reads are open to district staff; writes are for administrators, like schemes.
"""
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.models import (
    CommunityFeedback,
    GrievanceCategory,
    IrrigationClimateLog,
    IrrigationScheme,
    SchemeAsset,
    UserRole,
)
from app.db.session import get_db
from app.schemas import (
    GrievanceCategoryCreate,
    GrievanceCategoryRead,
    GrievanceCategoryUpdate,
    SchemeAssetCreate,
    SchemeAssetRead,
    SchemeAssetUpdate,
)
from app.services.references import require_if_provided

router = APIRouter(prefix="/api/v1", tags=["calibration"])
reader = Depends(require_roles(UserRole.district_officer, UserRole.district_planner, UserRole.administrator))
writer = Depends(require_roles(UserRole.administrator))


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40] or "category"


# ---------- Grievance categories (USSD option 5) ----------


@router.get("/grievance-categories", response_model=list[GrievanceCategoryRead], dependencies=[reader])
def list_grievance_categories(db: Session = Depends(get_db)) -> list[GrievanceCategory]:
    return list(db.scalars(select(GrievanceCategory).order_by(GrievanceCategory.sort_order, GrievanceCategory.id)))


@router.post("/grievance-categories", response_model=GrievanceCategoryRead, status_code=status.HTTP_201_CREATED, dependencies=[writer])
def create_grievance_category(payload: GrievanceCategoryCreate, db: Session = Depends(get_db)) -> GrievanceCategory:
    clash = db.scalar(select(GrievanceCategory).where(GrievanceCategory.label_en == payload.label_en))
    if clash:
        raise HTTPException(status_code=409, detail="A grievance category with this English label already exists")
    values = payload.model_dump()
    if not values.get("code"):
        values["code"] = _slug(payload.label_en)
    if db.scalar(select(GrievanceCategory).where(GrievanceCategory.code == values["code"])):
        raise HTTPException(status_code=409, detail="A grievance category with this code already exists")
    category = GrievanceCategory(**values)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/grievance-categories/{category_id}", response_model=GrievanceCategoryRead, dependencies=[writer])
def update_grievance_category(category_id: int, payload: GrievanceCategoryUpdate, db: Session = Depends(get_db)) -> GrievanceCategory:
    category = db.get(GrievanceCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Grievance category not found")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("label_en") and db.scalar(
        select(GrievanceCategory).where(GrievanceCategory.label_en == changes["label_en"], GrievanceCategory.id != category_id)
    ):
        raise HTTPException(status_code=409, detail="A grievance category with this English label already exists")
    for field, value in changes.items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/grievance-categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[writer])
def delete_grievance_category(category_id: int, db: Session = Depends(get_db)) -> None:
    category = db.get(GrievanceCategory, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Grievance category not found")
    in_use = db.scalar(select(CommunityFeedback.id).where(CommunityFeedback.category == category.label_en).limit(1))
    if in_use:
        raise HTTPException(status_code=409, detail="Grievances already use this category. Deactivate it instead.")
    db.delete(category)
    db.commit()


# ---------- Scheme assets (USSD option 4) ----------


@router.get("/scheme-assets", response_model=list[SchemeAssetRead], dependencies=[reader])
def list_scheme_assets(db: Session = Depends(get_db)) -> list[SchemeAsset]:
    return list(db.scalars(select(SchemeAsset).order_by(SchemeAsset.id)))


@router.post("/scheme-assets", response_model=SchemeAssetRead, status_code=status.HTTP_201_CREATED, dependencies=[writer])
def create_scheme_asset(payload: SchemeAssetCreate, db: Session = Depends(get_db)) -> SchemeAsset:
    clash = db.scalar(select(SchemeAsset).where(SchemeAsset.name_en == payload.name_en))
    if clash:
        raise HTTPException(status_code=409, detail="An asset with this English name already exists")
    require_if_provided(db, IrrigationScheme, payload.scheme_id, "scheme_id")
    asset = SchemeAsset(**payload.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.patch("/scheme-assets/{asset_id}", response_model=SchemeAssetRead, dependencies=[writer])
def update_scheme_asset(asset_id: int, payload: SchemeAssetUpdate, db: Session = Depends(get_db)) -> SchemeAsset:
    asset = db.get(SchemeAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Scheme asset not found")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("name_en") and db.scalar(
        select(SchemeAsset).where(SchemeAsset.name_en == changes["name_en"], SchemeAsset.id != asset_id)
    ):
        raise HTTPException(status_code=409, detail="An asset with this English name already exists")
    if "scheme_id" in changes:
        require_if_provided(db, IrrigationScheme, changes["scheme_id"], "scheme_id")
    for field, value in changes.items():
        setattr(asset, field, value)
    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/scheme-assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[writer])
def delete_scheme_asset(asset_id: int, db: Session = Depends(get_db)) -> None:
    asset = db.get(SchemeAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Scheme asset not found")
    in_use = db.scalar(select(IrrigationClimateLog.id).where(IrrigationClimateLog.infrastructure_name == asset.name_en).limit(1))
    if in_use:
        raise HTTPException(status_code=409, detail="Reports already reference this asset. Deactivate it instead.")
    db.delete(asset)
    db.commit()

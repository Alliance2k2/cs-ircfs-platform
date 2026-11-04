"""Import district-supplied reference lists atomically; preview by default."""
import argparse
import json
import re
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.db.models import Cell,GrievanceCategory,IrrigationScheme,SchemeAsset,UserRole
from app.db.session import SessionLocal
from app.core.security import Principal
from app.schemas.calibration import GrievanceCategoryCreate,SchemeAssetCreate
from app.services.audit import record
from app.services.references import require_if_provided, validate_asset_area


def prepare(db,manifest):
    source=str(manifest.get("source_reference","")).strip()
    if len(source)<5:raise ValueError("The inventory needs a district document reference")
    categories=[GrievanceCategoryCreate.model_validate(row).model_dump() for row in manifest.get("categories",[])]
    assets=[SchemeAssetCreate.model_validate(row).model_dump() for row in manifest.get("assets",[])]
    codes=set(db.scalars(select(GrievanceCategory.code)));labels=set(db.scalars(select(GrievanceCategory.label_en)))
    names=set(db.scalars(select(SchemeAsset.name_en)))
    for row in categories:
        row["code"]=row["code"] or re.sub(r"[^a-z0-9]+","_",row["label_en"].lower()).strip("_")[:40] or "category"
        if row["code"] in codes or row["label_en"] in labels:raise ValueError("Category already exists or is duplicated in the manifest")
        codes.add(row["code"]);labels.add(row["label_en"])
    for row in assets:
        if row["name_en"] in names:raise ValueError("Asset already exists or is duplicated in the manifest")
        names.add(row["name_en"])
        require_if_provided(db,IrrigationScheme,row["scheme_id"],"scheme_id")
        require_if_provided(db,Cell,row["cell_id"],"cell_id")
        validate_asset_area(db,row["scheme_id"],row["cell_id"])
    return source,categories,assets


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest",type=Path)
    parser.add_argument("--apply",action="store_true")
    parser.add_argument("--confirm-database")
    args=parser.parse_args()
    with SessionLocal() as db:
        source,categories,assets=prepare(db,json.loads(args.manifest.read_text(encoding="utf-8-sig")))
        if args.apply:
            if args.confirm_database != Path(db.bind.url.database or "").name:parser.error("Confirm the selected database name with --confirm-database")
            db.add_all([GrievanceCategory(**row) for row in categories]+[SchemeAsset(**row) for row in assets])
            record(db,Principal(name="reference-importer",role=UserRole.administrator),"reference.import","reference_inventory",
                source_reference=source,categories=len(categories),assets=len(assets))
            db.commit()
        print(json.dumps({"mode":"applied" if args.apply else "preview","categories":len(categories),"assets":len(assets)}))

if __name__=="__main__":main()

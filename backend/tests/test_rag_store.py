from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.security import Principal
from app.db.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeVersion
from app.db.models import UserRole
from app.services.rag.store import approve, authorized_sources, ingest, remove

ADMIN = Principal(name="fixture", role=UserRole.administrator, account_id=1)


def upload(db, data=b"Approved procedure for synthetic pump inspections", **kwargs):
    return ingest(db, filename="guide.txt", data=data, title="Pump procedure", **kwargs)


def test_approval_duplicate_version_update_and_delete(db):
    version, duplicate = upload(db)
    assert not duplicate and version.status == "pending"
    assert authorized_sources(db, ADMIN) == []
    approve(db, version.id, ADMIN, "synthetic review A")
    assert authorized_sources(db, ADMIN)[0]["page"] == 1
    retry, duplicate = upload(db, document_id=version.document_id)
    assert retry.id == version.id and duplicate
    newer, _ = upload(db, b"Revised approved procedure", document_id=version.document_id)
    assert authorized_sources(db, ADMIN)[0]["version_id"] == version.id
    approve(db, newer.id, ADMIN, "synthetic review B")
    assert db.get(KnowledgeVersion, version.id).status == "superseded"
    assert authorized_sources(db, ADMIN)[0]["version_id"] == newer.id
    remove(db, version.document_id)
    assert authorized_sources(db, ADMIN) == []
    assert not list(db.scalars(select(KnowledgeChunk)))
    assert db.get(KnowledgeDocument, version.document_id).deleted


def test_permission_filters_run_before_text_selection(db):
    version, _ = upload(db, roles=["district_planner"], sector_ids=[2])
    approve(db, version.id, ADMIN, "fixture approval")
    planner = Principal(name="planner", role=UserRole.district_planner, sector_ids=frozenset({1}))
    assert authorized_sources(db, planner) == []
    assert authorized_sources(db, ADMIN) == []  # administrator is not an ACL bypass
    planner = Principal(name="planner", role=UserRole.district_planner, sector_ids=frozenset({2}))
    assert len(authorized_sources(db, planner)) == 1
    monitor = Principal(name="monitor", role=UserRole.citizen_science_monitor)
    assert authorized_sources(db, monitor) == []


def test_invalid_approval_and_duplicates_are_refused(db):
    version, _ = upload(db)
    with pytest.raises(ValueError, match="Duplicate"):
        upload(db)
    with pytest.raises(ValueError, match="signed-in"):
        approve(db, version.id, SimpleNamespace(role=UserRole.administrator, account_id=None), "fixture")
    with pytest.raises(ValueError, match="reference"):
        approve(db, version.id, ADMIN, " ")
    with pytest.raises(ValueError, match="metadata"):
        ingest(db, filename="x.txt", data=b"abc", title="Different title", document_id=version.document_id)

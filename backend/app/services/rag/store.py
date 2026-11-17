"""Transactional source lifecycle. Authorization precedes chunk selection."""
from uuid import uuid4

from sqlalchemy import delete, func, select, update

from app.db.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeEmbedding, KnowledgeJob, KnowledgeVersion
from app.services.rag.chunking import chunk_pages
from app.services.rag.ingestion import extract

STAFF_ROLES = {"administrator", "district_officer", "district_planner"}


def identifier():
    return str(uuid4())


def ingest(db, *, filename, data, title, language="en", classification="engineering", roles=None, sector_ids=None, document_id=None, size=512, overlap=64, strategy="recursive"):
    roles = sorted(set(roles or STAFF_ROLES))
    sector_ids = sorted(set(sector_ids or []))
    if not title.strip() or len(title) > 200 or language not in {"en", "rw", "fr"} or classification not in {"engineering", "institutional", "demonstration"}:
        raise ValueError("Invalid document metadata")
    if not set(roles) <= STAFF_ROLES or not roles or any(not isinstance(i, int) or i <= 0 for i in sector_ids):
        raise ValueError("Invalid document permissions")
    extracted = extract(filename, data)
    chunks = chunk_pages(extracted.pages, size, overlap, strategy)
    document = db.get(KnowledgeDocument, document_id) if document_id else None
    if document_id and (document is None or document.deleted):
        raise ValueError("Document unavailable")
    if document:
        # Access policy is immutable across versions; narrowing/widening must not
        # silently change access to already approved text.
        if (document.title, document.language, document.classification, document.roles, document.sector_ids) != (title, language, classification, roles, sector_ids):
            raise ValueError("Version metadata must match original document")
        duplicate = db.scalar(select(KnowledgeVersion).where(KnowledgeVersion.document_id == document.id, KnowledgeVersion.digest == extracted.digest))
        if duplicate:
            return duplicate, True
    else:
        duplicate = db.scalar(select(KnowledgeVersion).join(KnowledgeDocument).where(
            KnowledgeVersion.digest == extracted.digest, KnowledgeDocument.deleted.is_(False)))
        if duplicate:
            raise ValueError("Duplicate content; update the existing document")
        document = KnowledgeDocument(id=identifier(), title=title, language=language, classification=classification, roles=roles, sector_ids=sector_ids)
        db.add(document)
        db.flush()
    revision = (db.scalar(select(func.max(KnowledgeVersion.revision)).where(KnowledgeVersion.document_id == document.id)) or 0) + 1
    version = KnowledgeVersion(id=identifier(), document_id=document.id, digest=extracted.digest, revision=revision, status="pending")
    db.add(version)
    db.flush()
    db.add_all([KnowledgeChunk(id=identifier(), version_id=version.id, ordinal=chunk.ordinal, page=chunk.page, heading=chunk.heading, text=chunk.text) for chunk in chunks])
    db.add(KnowledgeJob(id=identifier(), version_id=version.id, status="indexed", chunk_count=len(chunks), detail="Extracted and chunked locally; approval pending"))
    db.flush()
    return version, False


def approve(db, version_id, principal, reference):
    if principal.role.value != "administrator" or principal.account_id is None:
        raise ValueError("Approval requires a signed-in administrator account")
    if not reference.strip() or len(reference) > 200:
        raise ValueError("Provide a reviewed approval reference")
    version = db.get(KnowledgeVersion, version_id)
    if not version or db.get(KnowledgeDocument, version.document_id).deleted:
        raise ValueError("Version unavailable")
    # Serialize sibling approvals per document; repeated approval is idempotent.
    db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.id == version.document_id).with_for_update())
    db.refresh(version, with_for_update=True)
    if version.status == "approved":
        return version
    if version.status != "pending":
        raise ValueError("Only pending versions can be approved")
    db.execute(update(KnowledgeVersion).where(KnowledgeVersion.document_id == version.document_id, KnowledgeVersion.status == "approved").values(status="superseded"))
    version.status = "approved"
    version.approved_by = principal.account_id
    version.approval_reference = reference.strip()
    db.flush()
    return version


def remove(db, document_id):
    document = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.id == document_id).with_for_update())
    if not document:
        raise ValueError("Document unavailable")
    versions = select(KnowledgeVersion.id).where(KnowledgeVersion.document_id == document_id)
    chunks = select(KnowledgeChunk.id).where(KnowledgeChunk.version_id.in_(versions))
    db.execute(delete(KnowledgeEmbedding).where(KnowledgeEmbedding.chunk_id.in_(chunks)))
    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.version_id.in_(versions)))
    db.execute(update(KnowledgeVersion).where(KnowledgeVersion.document_id == document_id).values(status="rejected"))
    document.deleted = True
    db.flush()


def authorized_sources(db, principal, limit=2000):
    # Only metadata is inspected before permission checks. Never load restricted
    # chunk text and then filter a ranked/result set.
    if principal.role.value not in STAFF_ROLES:
        return []
    documents = db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.deleted.is_(False)))
    allowed = []
    for doc in documents:
        if principal.role.value not in doc.roles:
            continue
        if doc.sector_ids and principal.sector_ids is not None and not set(doc.sector_ids) <= principal.sector_ids:
            continue
        allowed.append(doc.id)
    if not allowed:
        return []
    rows = db.execute(select(KnowledgeChunk, KnowledgeVersion, KnowledgeDocument).join(
        KnowledgeVersion, KnowledgeChunk.version_id == KnowledgeVersion.id).join(
        KnowledgeDocument, KnowledgeVersion.document_id == KnowledgeDocument.id).where(
        KnowledgeDocument.id.in_(allowed), KnowledgeVersion.status == "approved").order_by(KnowledgeChunk.id).limit(limit + 1)).all()
    if len(rows) > limit:
        raise ValueError("Local corpus exceeds candidate limit; use a scoped database index")
    return [dict(id=chunk.id, title=doc.title, text=chunk.text, reference=f"knowledge:{doc.id}",
                 revision=version.digest[:12], document_id=doc.id, version_id=version.id,
                 page=chunk.page, heading=chunk.heading, language=doc.language,
                 classification=doc.classification) for chunk, version, doc in rows]

"""Staff-only, stateless, read-only document assistant."""
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Literal
from sqlalchemy.orm import Session

from app.core.ratelimit import limiter
from app.core.security import Principal, require_roles
from app.db.models import UserRole
from app.db.session import get_db
from app.services.rag.store import authorized_sources
from app.services.rag.store import ingest, approve, remove
from app.services.rag.ingestion import MAX_BYTES
from app.db.knowledge import KnowledgeDocument, KnowledgeVersion, KnowledgeChunk
from app.core.config import get_settings
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool
import logging
from app.services.assistant import respond
from app.services.rag.observability import record

class AssistantRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()
        async def bounded(request: Request):
            if request.method == "POST" and not request.url.path.endswith("/documents"):
                receive = request.receive
                consumed = 0
                async def limited_receive():
                    nonlocal consumed
                    message = await receive()
                    consumed += len(message.get("body", b""))
                    if consumed > 64 * 1024:
                        raise HTTPException(413, "Assistant request exceeds 64 KiB")
                    return message
                request = Request(request.scope, receive=limited_receive)
            return await original(request)
        return bounded


router = APIRouter(prefix="/api/v1/assistant", tags=["document assistant"], route_class=AssistantRoute)
staff = Depends(require_roles(UserRole.district_officer, UserRole.district_planner, UserRole.administrator))
admin = Depends(require_roles(UserRole.administrator))
logger = logging.getLogger(__name__)


def same_origin(request: Request):
    # Cookie-authenticated raw uploads otherwise admit cross-origin text/plain
    # requests without a preflight. CORS alone is not a CSRF defense.
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Cross-origin knowledge mutations are refused")


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=1200)
    language: Literal["auto", "en", "rw"] = "auto"
    history: list[str] = Field(default_factory=list, max_length=3)

    @field_validator("history")
    @classmethod
    def bounded_history(cls, values):
        if any(not 3 <= len(value.strip()) <= 1200 for value in values):
            raise ValueError("History questions must contain 3 to 1200 characters")
        return [value.strip() for value in values]

    @field_validator("question")
    @classmethod
    def clean(cls, value):
        if len(value.strip()) < 3:
            raise ValueError("Enter a question")
        return value.strip()


@router.post("/ask")
@limiter.limit("10/minute")
async def ask(payload: Question, request: Request, principal: Principal = staff, db: Session = Depends(get_db)):
    try:
        sources = await run_in_threadpool(authorized_sources, db, principal)
    except ValueError as exc:
        raise HTTPException(503, "Knowledge corpus exceeds local retrieval capacity") from exc
    return await respond(payload.question, additional_sources=sources, language=payload.language, history=payload.history)


@router.get("/documents")
def list_documents(_: Principal = admin, db: Session = Depends(get_db)):
    rows = db.execute(select(KnowledgeDocument, KnowledgeVersion).join(KnowledgeVersion).where(KnowledgeDocument.deleted.is_(False)).order_by(KnowledgeVersion.created_at.desc()).limit(200))
    return [{"document_id": doc.id, "version_id": version.id, "title": doc.title, "language": doc.language,
             "classification": doc.classification, "roles": doc.roles, "sector_ids": doc.sector_ids,
             "status": version.status, "revision": version.revision, "digest": version.digest,
             "approval_reference": version.approval_reference} for doc, version in rows]


@router.get("/documents/{version_id}/preview")
def preview_document(version_id: str, _: Principal = admin, db: Session = Depends(get_db)):
    return [{"page": chunk.page, "heading": chunk.heading, "text": chunk.text} for chunk in db.scalars(
        select(KnowledgeChunk).join(KnowledgeVersion).join(KnowledgeDocument).where(
            KnowledgeVersion.id == version_id, KnowledgeDocument.deleted.is_(False)).order_by(KnowledgeChunk.ordinal).limit(100))]


@router.post("/documents")
@limiter.limit("5/minute")
async def upload_document(request: Request, filename: str = Query(max_length=200), title: str = Query(min_length=1, max_length=200),
                          language: Literal["en", "rw", "fr"] = "en", classification: Literal["engineering", "institutional", "demonstration"] = "engineering",
                          roles: str = Query(default="administrator,district_officer,district_planner", max_length=100),
                          sectors: str = Query(default="", max_length=500), document_id: str | None = Query(default=None, max_length=36),
                          _: Principal = admin, db: Session = Depends(get_db)):
    same_origin(request)
    if not get_settings().assistant_ingestion_enabled:
        raise HTTPException(503, "Knowledge uploads are disabled until the extraction environment is approved")
    data = bytearray()
    async for part in request.stream():
        data.extend(part)
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "Document exceeds 5 MiB")
    try:
        version, duplicate = await run_in_threadpool(ingest, db, filename=filename, data=bytes(data), title=title, language=language,
            classification=classification, roles=roles.split(","), sector_ids=[int(value) for value in sectors.split(",") if value], document_id=document_id)
        db.commit()
        record("ingestion_indexed")
        return {"document_id": version.document_id, "version_id": version.id, "status": version.status, "duplicate": duplicate}
    except (ValueError, IntegrityError) as exc:
        db.rollback()
        raise HTTPException(422, str(exc) if isinstance(exc, ValueError) else "Concurrent or duplicate ingestion; reload and retry") from exc


class Approval(BaseModel):
    reference: str = Field(min_length=1, max_length=200)


@router.post("/documents/{version_id}/approve")
def approve_document(version_id: str, payload: Approval, request: Request, principal: Principal = admin, db: Session = Depends(get_db)):
    same_origin(request)
    try:
        version = approve(db, version_id, principal, payload.reference)
        db.commit()
        record("source_approved")
        return {"status": version.status}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc


@router.delete("/documents/{document_id}")
def delete_document(document_id: str, request: Request, _: Principal = admin, db: Session = Depends(get_db)):
    same_origin(request)
    try:
        remove(db, document_id)
        db.commit()
        record("source_deleted")
        return {"status": "deleted"}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(404, str(exc)) from exc


class Feedback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vote: Literal["helpful", "unhelpful"]


@router.post("/feedback")
@limiter.limit("10/minute")
def feedback(payload: Feedback, request: Request, _: Principal = staff):
    same_origin(request)
    # Aggregate trend input only: no question, answer, account or source contents.
    logger.info("assistant_feedback vote=%s", payload.vote)
    record("feedback_" + payload.vote)
    return {"status": "recorded"}

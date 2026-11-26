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
from app.db.knowledge import KnowledgeDocument, KnowledgeVersion, KnowledgeChunk, KnowledgeJob, KnowledgeEmbedding
from app.core.config import get_settings
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool
import logging
from app.services.assistant import respond, documents
from app.services.rag.observability import record
from app.services.audit import record as audit

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
    selected_references: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("selected_references")
    @classmethod
    def bounded_references(cls, values):
        if any(not value or len(value) > 200 for value in values):
            raise ValueError("Invalid document selection")
        return list(dict.fromkeys(values))

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
    allowed = {row["reference"] for row in sources} | {f"packaged:{row['id']}" for row in documents()}
    if not set(payload.selected_references) <= allowed:
        raise HTTPException(403, "A selected source is not available to this account")
    return await respond(payload.question, additional_sources=sources, language=payload.language, history=payload.history,
                         selected_references=payload.selected_references)


@router.get("/sources")
def source_library(principal: Principal = staff, db: Session = Depends(get_db)):
    try:
        permitted = authorized_sources(db, principal)
    except ValueError as exc:
        raise HTTPException(503, "Knowledge corpus exceeds local retrieval capacity") from exc
    library = {f"packaged:{row['id']}": {"reference": f"packaged:{row['id']}", "title": row["title"], "status": "packaged", "language": "en"} for row in documents()}
    for row in permitted:
        library[row["reference"]] = {"reference": row["reference"], "title": row["title"], "status": "approved", "language": row["language"]}
    return list(library.values())


@router.get("/documents")
def list_documents(q: str = Query(default="", max_length=200), status: Literal["all", "pending", "approved", "superseded", "rejected"] = "all",
                   _: Principal = admin, db: Session = Depends(get_db)):
    statement = select(KnowledgeDocument, KnowledgeVersion).join(KnowledgeVersion).where(KnowledgeDocument.deleted.is_(False))
    if q.strip():
        statement = statement.where(KnowledgeDocument.title.icontains(q.strip(), autoescape=True))
    if status != "all":
        statement = statement.where(KnowledgeVersion.status == status)
    rows = db.execute(statement.order_by(KnowledgeVersion.created_at.desc(), KnowledgeVersion.id).limit(200)).all()
    version_ids = [version.id for _, version in rows]
    counts = dict(db.execute(select(KnowledgeChunk.version_id, func.count()).where(
        KnowledgeChunk.version_id.in_(version_ids)).group_by(KnowledgeChunk.version_id)).all())
    vectors = dict(db.execute(select(KnowledgeChunk.version_id, func.count()).join(
        KnowledgeEmbedding, KnowledgeEmbedding.chunk_id == KnowledgeChunk.id).where(
        KnowledgeChunk.version_id.in_(version_ids)).group_by(KnowledgeChunk.version_id)).all())
    jobs = {job.version_id: job for job in db.scalars(select(KnowledgeJob).where(KnowledgeJob.version_id.in_(version_ids)))}
    return [{"document_id": doc.id, "version_id": version.id, "title": doc.title, "language": doc.language,
             "classification": doc.classification, "roles": doc.roles, "sector_ids": doc.sector_ids,
             "status": version.status, "revision": version.revision, "digest": version.digest,
             "approval_reference": version.approval_reference, "chunk_count": counts.get(version.id, 0),
             "embedding_count": vectors.get(version.id, 0),
             "processing_status": jobs[version.id].status if version.id in jobs else "unknown",
             "processing_detail": jobs[version.id].detail if version.id in jobs else "No processing record"} for doc, version in rows]


@router.get("/config")
async def assistant_config(principal: Principal = staff):
    settings = get_settings()
    import httpx
    ready = False
    state = "disabled"
    provider = settings.assistant_provider
    if settings.assistant_generation_enabled:
        state = "not_configured"
        if settings.assistant_model.strip():
            if provider == "openai":
                ready = bool(settings.assistant_openai_api_key.get_secret_value())
                state = "configured" if ready else "not_configured"
            else:
                try:
                    url = "http://127.0.0.1:11435/v1/models" if provider == "llamacpp" else "http://127.0.0.1:11434/api/tags"
                    async with httpx.AsyncClient(timeout=2, trust_env=False, follow_redirects=False) as client:
                        headers = {"Authorization": f"Bearer {settings.assistant_local_api_key.get_secret_value()}"} if provider == "llamacpp" else {}
                        response = await client.get(url, headers=headers)
                        response.raise_for_status()
                        data = response.json()
                    ready = any(row.get("id") == settings.assistant_model for row in data.get("data", [])) if provider == "llamacpp" else any(row.get("name") == settings.assistant_model for row in data.get("models", []))
                    state = "ready" if ready else "offline"
                except (httpx.HTTPError, ValueError, TypeError):
                    state = "offline"
    return {"generation_enabled": settings.assistant_generation_enabled,
            "generation_ready": ready, "generation_status": state, "local_provider": provider in {"ollama", "llamacpp"},
            "retrieval_mode": settings.assistant_retrieval_mode,
            "uploads_enabled": principal.role == UserRole.administrator and settings.assistant_ingestion_enabled,
            "embedding_configured": bool(settings.assistant_embedding_path and settings.assistant_embedding_revision)}


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
                          principal: Principal = admin, db: Session = Depends(get_db)):
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
            classification=classification, roles=roles.split(","), sector_ids=[int(value) for value in sectors.split(",") if value], document_id=document_id, isolated=True)
        audit(db, principal, "knowledge.upload", "knowledge_document", document_id=version.document_id,
              version_id=version.id, revision=version.revision, duplicate=duplicate)
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
        audit(db, principal, "knowledge.approve", "knowledge_document", document_id=version.document_id,
              version_id=version.id, revision=version.revision)
        db.commit()
        record("source_approved")
        return {"status": version.status}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc


@router.delete("/documents/{document_id}")
def delete_document(document_id: str, request: Request, principal: Principal = admin, db: Session = Depends(get_db)):
    same_origin(request)
    try:
        remove(db, document_id)
        audit(db, principal, "knowledge.remove", "knowledge_document", document_id=document_id)
        db.commit()
        record("source_deleted")
        return {"status": "deleted"}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(404, str(exc)) from exc


@router.post("/documents/{version_id}/reindex")
@limiter.limit("5/minute")
async def reindex_document(version_id: str, request: Request, principal: Principal = admin, db: Session = Depends(get_db)):
    same_origin(request)
    from app.services.rag.management import reindex
    from app.services.rag.embeddings import local_provider
    settings = get_settings()
    provider_factory = None
    if settings.assistant_embedding_path or settings.assistant_embedding_revision:
        provider_factory = lambda: local_provider(settings.assistant_embedding_path, settings.assistant_embedding_revision)
    try:
        result = await run_in_threadpool(reindex, db, version_id, provider_factory=provider_factory)
        audit(db, principal, "knowledge.reindex", "knowledge_version", version_id=version_id, status=result["status"])
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    if result["status"] == "failed":
        record("index_failed")
        raise HTTPException(503, result["detail"])
    record("index_checked")
    return result


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

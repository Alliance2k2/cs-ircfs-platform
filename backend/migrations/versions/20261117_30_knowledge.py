"""Portable knowledge lifecycle; does not install extensions or touch field data."""
from alembic import op
import sqlalchemy as sa

revision = "20261117_30"
down_revision = "20261113_29"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("knowledge_documents", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False), sa.Column("classification", sa.String(24), nullable=False),
        sa.Column("language", sa.String(2), nullable=False), sa.Column("roles", sa.JSON, nullable=False),
        sa.Column("sector_ids", sa.JSON, nullable=False), sa.Column("deleted", sa.Boolean, nullable=False),
        sa.CheckConstraint("classification IN ('engineering', 'institutional', 'demonstration')", name="ck_knowledge_classification"))
    op.create_table("knowledge_versions", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("knowledge_documents.id"), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False), sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("status", sa.String(16), nullable=False), sa.Column("approval_reference", sa.String(200), nullable=False),
        sa.Column("approved_by", sa.Integer, nullable=True), sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("document_id", "digest", name="uq_knowledge_version_digest"),
        sa.UniqueConstraint("document_id", "revision", name="uq_knowledge_version_number"),
        sa.CheckConstraint("status IN ('pending', 'approved', 'superseded', 'rejected')", name="ck_knowledge_version_status"))
    op.create_index("ix_knowledge_versions_document_id", "knowledge_versions", ["document_id"])
    op.create_table("knowledge_chunks", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version_id", sa.String(36), sa.ForeignKey("knowledge_versions.id"), nullable=False),
        sa.Column("ordinal", sa.Integer, nullable=False), sa.Column("page", sa.Integer, nullable=False),
        sa.Column("heading", sa.String(200), nullable=False), sa.Column("text", sa.Text, nullable=False),
        sa.UniqueConstraint("version_id", "ordinal", name="uq_knowledge_chunk_ordinal"))
    op.create_index("ix_knowledge_chunks_version_id", "knowledge_chunks", ["version_id"])
    op.create_table("knowledge_embeddings", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("chunk_id", sa.String(36), sa.ForeignKey("knowledge_chunks.id"), nullable=False),
        sa.Column("model", sa.String(200), nullable=False), sa.Column("dimensions", sa.Integer, nullable=False),
        sa.Column("vector", sa.JSON, nullable=False), sa.UniqueConstraint("chunk_id", "model", name="uq_knowledge_embedding_model"))
    op.create_index("ix_knowledge_embeddings_chunk_id", "knowledge_embeddings", ["chunk_id"])
    op.create_table("knowledge_jobs", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version_id", sa.String(36), sa.ForeignKey("knowledge_versions.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False), sa.Column("chunk_count", sa.Integer, nullable=False),
        sa.Column("detail", sa.String(200), nullable=False))
    op.create_index("ix_knowledge_jobs_version_id", "knowledge_jobs", ["version_id"])
    op.create_table("knowledge_evaluations", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dataset_hash", sa.String(64), nullable=False), sa.Column("corpus_hash", sa.String(64), nullable=False),
        sa.Column("retriever", sa.String(200), nullable=False), sa.Column("metrics", sa.JSON, nullable=False))


def downgrade():
    for table in ("knowledge_evaluations", "knowledge_jobs", "knowledge_embeddings", "knowledge_chunks", "knowledge_versions", "knowledge_documents"):
        op.drop_table(table)

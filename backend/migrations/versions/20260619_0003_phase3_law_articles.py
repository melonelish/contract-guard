"""phase3 law_articles table for RAG"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260619_0003"
down_revision = "20260618_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "law_articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("law_name", sa.String(length=200), nullable=False),
        sa.Column("article_number", sa.String(length=50), nullable=False),
        sa.Column("article_title", sa.String(length=300), nullable=True),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column("keywords", sa.Text(), nullable=True),
        sa.Column("chapter", sa.String(length=100), nullable=True),
        sa.Column("section", sa.String(length=100), nullable=True),
        sa.Column("effective_date", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="现行有效"),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
    )
    op.create_index("idx_law_name_number", "law_articles", ["law_name", "article_number"], unique=True)
    op.create_index("idx_law_search_vector", "law_articles", ["search_vector"], postgresql_using="gin")

    # 创建触发器：自动更新 search_vector
    op.execute("""
        CREATE OR REPLACE FUNCTION law_articles_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('simple', coalesce(NEW.law_name, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(NEW.article_number, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(NEW.article_title, '')), 'B') ||
                setweight(to_tsvector('simple', coalesce(NEW.full_text, '')), 'C') ||
                setweight(to_tsvector('simple', coalesce(NEW.keywords, '')), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_law_articles_search_vector
        BEFORE INSERT OR UPDATE ON law_articles
        FOR EACH ROW EXECUTE FUNCTION law_articles_search_vector_update();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_law_articles_search_vector ON law_articles")
    op.execute("DROP FUNCTION IF EXISTS law_articles_search_vector_update()")
    op.drop_index("idx_law_search_vector", table_name="law_articles")
    op.drop_index("idx_law_name_number", table_name="law_articles")
    op.drop_table("law_articles")

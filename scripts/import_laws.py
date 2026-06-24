"""Import law corpus into the law_articles table.

Usage:
    cd backend && python ../scripts/import_laws.py
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import get_settings
from sqlalchemy import create_engine, text


def main() -> None:
    settings = get_settings()
    # Use sync URL for the import script
    engine = create_engine(settings.database_sync_url)

    corpus_path = Path(__file__).parent / "law_corpus.json"
    with open(corpus_path, encoding="utf-8") as f:
        articles = json.load(f)

    print(f"Loading {len(articles)} law articles...")

    with engine.begin() as conn:
        # Clear existing data
        conn.execute(text("DELETE FROM law_articles"))
        print("Cleared existing law_articles.")

        for article in articles:
            conn.execute(
                text("""
                    INSERT INTO law_articles
                        (id, law_name, article_number, article_title, full_text,
                         keywords, chapter, section, effective_date, status)
                    VALUES
                        (:id, :law_name, :article_number, :article_title,
                         :full_text, :keywords, :chapter, :section, :effective_date, :status)
                """),
                {
                    "id": str(uuid.uuid4()),
                    "law_name": article["law_name"],
                    "article_number": article["article_number"],
                    "article_title": article.get("article_title", ""),
                    "full_text": article["full_text"],
                    "keywords": article.get("keywords", ""),
                    "chapter": article.get("chapter", ""),
                    "section": article.get("section", ""),
                    "effective_date": article.get("effective_date", ""),
                    "status": article.get("status", "现行有效"),
                },
            )

        # Verify
        result = conn.execute(text("SELECT count(*) FROM law_articles"))
        count = result.scalar()
        print(f"Imported {count} law articles successfully.")

        # Test full-text search
        result = conn.execute(
            text("""
                SELECT law_name, article_number, article_title
                FROM law_articles
                WHERE search_vector @@ plainto_tsquery('simple', '违约金')
                LIMIT 5
            """)
        )
        rows = result.fetchall()
        print(f"\nTest search for '违约金' — found {len(rows)} results:")
        for row in rows:
            print(f"  {row[0]} {row[1]}: {row[2]}")


if __name__ == "__main__":
    main()

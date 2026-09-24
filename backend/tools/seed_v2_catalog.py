"""Idempotent V2 catalog importer (does not run migrations or alter existing rows)."""
from app.db import SessionLocal, init_db
from app.v2_catalog import seed_v2_catalog

if __name__ == "__main__":
    init_db()
    with SessionLocal() as session:
        result = seed_v2_catalog(session)
        session.commit()
    print(result)

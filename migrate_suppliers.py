import sqlite3
from pathlib import Path

from app import create_app
from database import get_db


def migrate_suppliers():
    app = create_app()

    with app.app_context():
        database_path = Path(app.config["DATABASE"])

        if not database_path.is_file():
            raise FileNotFoundError(
                f"Database not found: {database_path}"
            )

        db = get_db()

        # Confirm the existing database has a products table.
        products_table = db.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name = 'products'"
        ).fetchone()

        if products_table is None:
            raise RuntimeError("Existing products table not found")

        # Back up the existing database before modifying it.
        backup_path = database_path.with_name(
            database_path.name + ".before_suppliers.bak"
        )

        if not backup_path.exists():
            with sqlite3.connect(str(backup_path)) as backup:
                db.backup(backup)
            print(f"Backup created: {backup_path}")

        try:
            db.execute("BEGIN")

            # Create the suppliers table if it does not exist.
            db.execute("""
                CREATE TABLE IF NOT EXISTS suppliers (
                    supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    supplier_name TEXT NOT NULL UNIQUE,
                    contact_email TEXT,
                    contact_phone TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Check existing product columns before adding new ones.
            columns = {
                row["name"]
                for row in db.execute("PRAGMA table_info(products)")
            }

            if "supplier_id" not in columns:
                db.execute("""
                    ALTER TABLE products
                    ADD COLUMN supplier_id INTEGER
                    REFERENCES suppliers(supplier_id)
                    ON DELETE SET NULL
                """)

            if "supplier_sku" not in columns:
                db.execute("""
                    ALTER TABLE products
                    ADD COLUMN supplier_sku TEXT
                """)

            db.execute("""
                CREATE INDEX IF NOT EXISTS idx_products_supplier_id
                ON products(supplier_id)
            """)

            db.commit()
            print("Supplier migration completed successfully.")

        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    migrate_suppliers()

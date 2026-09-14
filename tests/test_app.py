from app import create_app
from database import get_db, init_db


# Verify that the app can build the SQLite schema into a temporary database file.
def test_app_initializes_database(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app({"TESTING": True, "DATABASE": str(database_path)})

    with app.app_context():
        init_db()
        database = get_db()
        tables = database.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()

    # These are the core tables required for the inventory system.
    assert "products" in {row[0] for row in tables}
    assert "inventory" in {row[0] for row in tables}

import json

from app import create_app
from database import init_db


def test_app_initializes_database_and_creates_product(tmp_path):
    database_path = tmp_path / "inventory.db"
    app = create_app({"TESTING": True, "DATABASE": str(database_path)})

    with app.app_context():
        init_db()

    client = app.test_client()
    health_response = client.get("/api/health")
    assert health_response.status_code == 200
    assert health_response.json["status"] == "ok"

    product_response = client.post(
        "/api/products",
        data=json.dumps(
            {
                "name": "Starter Dice Set",
                "category": "dice",
                "quantity_in_stock": 12,
                "reorder_threshold": 3,
                "reorder_quantity": 10,
            }
        ),
        content_type="application/json",
    )
    assert product_response.status_code == 201
    assert product_response.json["status"] == "active"

    products_response = client.get("/api/products?category=dice")
    assert products_response.status_code == 200
    assert products_response.json[0]["name"] == "Starter Dice Set"

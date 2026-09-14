import os

from flask import Flask, jsonify, request

from database import close_db, get_db, init_db


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, "inventory.db"),
    )

    if test_config is None:
        app.config.from_prefixed_env()
    else:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command():
        init_db()
        print("Initialized the inventory database.")

    @app.get("/api/health")
    def health():
        database = get_db()
        database.execute("SELECT 1").fetchone()
        return jsonify({"status": "ok", "service": "inventory-management-system"})

    @app.get("/api/products")
    def list_products():
        category = request.args.get("category")
        query = """
             SELECT p.product_id AS id, p.name, p.description, p.price, p.category,
                 i.quantity AS quantity_in_stock,
                 i.low_stock_threshold AS reorder_threshold,
                 i.reorder_amount AS reorder_quantity,
                 p.status, p.created_at, p.updated_at
             FROM products AS p
             JOIN inventory AS i ON i.product_id = p.product_id
        """
        parameters = []
        if category:
            query += " WHERE category = ?"
            parameters.append(category)
        query += " ORDER BY name"
        products = get_db().execute(query, parameters).fetchall()
        return jsonify([dict(product) for product in products])

    @app.post("/api/products")
    def create_product():
        product = request.get_json(silent=True) or {}
        required_fields = ("name", "category", "quantity_in_stock")
        missing_fields = [field for field in required_fields if field not in product]
        if missing_fields:
            return jsonify({"error": "Missing fields", "fields": missing_fields}), 400

        try:
            quantity_in_stock = int(product["quantity_in_stock"])
            reorder_threshold = int(product.get("reorder_threshold", 0))
            reorder_quantity = int(product.get("reorder_quantity", 0))
        except (TypeError, ValueError):
            return jsonify({"error": "Inventory quantities must be integers"}), 400

        if min(quantity_in_stock, reorder_threshold, reorder_quantity) < 0:
            return jsonify({"error": "Inventory quantities cannot be negative"}), 400

        database = get_db()
        try:
            cursor = database.execute(
                """
                INSERT INTO products
                    (name, description, price, category)
                VALUES (?, ?, ?, ?)
                """,
                (
                    product["name"].strip(),
                    product.get("description", "").strip(),
                    float(product.get("price", 0)),
                    product["category"].strip(),
                ),
            )
            product_id = cursor.lastrowid
            database.execute(
                """
                INSERT INTO inventory
                    (product_id, quantity, low_stock_threshold, reorder_amount)
                VALUES (?, ?, ?, ?)
                """,
                (product_id, quantity_in_stock, reorder_threshold, reorder_quantity),
            )
            database.commit()
        except database.IntegrityError:
            return jsonify({"error": "A product with that name already exists"}), 409

        created_product = database.execute(
            """
            SELECT p.product_id AS id, p.name, p.description, p.price, p.category,
                   i.quantity AS quantity_in_stock,
                   i.low_stock_threshold AS reorder_threshold,
                   i.reorder_amount AS reorder_quantity,
                   p.status, p.created_at, p.updated_at
            FROM products AS p
            JOIN inventory AS i ON i.product_id = p.product_id
            WHERE p.product_id = ?
            """,
            (product_id,),
        ).fetchone()
        return jsonify(dict(created_product)), 201

    @app.get("/api/inventory-events")
    def list_inventory_events():
        events = (
            get_db()
            .execute(
                """
            SELECT transaction_id AS id, product_id, transaction_type AS event_type,
                   quantity_change, NULL AS notes, date_time AS created_at
            FROM inventory_transactions
            ORDER BY date_time DESC, transaction_id DESC
            """
            )
            .fetchall()
        )
        return jsonify([dict(event) for event in events])

    return app


app = create_app()


if __name__ == "__main__":
    app.run()

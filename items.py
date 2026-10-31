from database import get_db, log_event


def add_item(
    name,
    category,
    description=None,
    price=0,
    quantity=0,
    low_stock_threshold=0,
    reorder_amount=0,
    user_id=None,
    supplier_name=None,
    contact_email=None,
    contact_phone=None,
    supplier_sku=None,
    supplier_id=None,
):
    """Add a product and its inventory record, returning the product ID."""
    database = get_db()
    try:
        supplier_name = (supplier_name or "").strip()
        contact_email = (contact_email or "").strip() or None
        contact_phone = (contact_phone or "").strip() or None
        supplier_sku = (supplier_sku or "").strip() or None

        # Item creation may reference a managed supplier selected on the Add Item page.
        if supplier_id is not None:
            supplier = database.execute(
                "SELECT supplier_id FROM suppliers WHERE supplier_id = ?",
                (supplier_id,),
            ).fetchone()
            if supplier is None:
                raise ValueError("Select a valid supplier")
        # Keep direct callers compatible by resolving or creating a legacy supplier name.
        elif supplier_name:
            supplier = database.execute(
                "SELECT supplier_id FROM suppliers WHERE supplier_name = ? COLLATE NOCASE",
                (supplier_name,),
            ).fetchone()
            if supplier:
                supplier_id = supplier["supplier_id"]
            else:
                cursor = database.execute(
                    """
                    INSERT INTO suppliers
                    (supplier_name, contact_email, contact_phone)
                    VALUES (?, ?, ?)
                    """,
                    (supplier_name, contact_email, contact_phone),
                )
                supplier_id = cursor.lastrowid
        elif contact_email or contact_phone or supplier_sku:
            raise ValueError("Supplier name is required for supplier details")

        # Store catalog details first so the inventory row can reference the new ID.
        product = database.execute(
            """
            INSERT INTO products
            (name, description, price, category, supplier_id, supplier_sku)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                description,
                price,
                category,
                supplier_id,
                supplier_sku,
            ),
        )
        product_id = product.lastrowid
        database.execute(
            """
            INSERT INTO inventory (
                product_id, quantity, low_stock_threshold, reorder_amount
            )
            VALUES (?, ?, ?, ?)
            """,
            (product_id, quantity, low_stock_threshold, reorder_amount),
        )
        # Audit entry is written in the same transaction, so it rolls back if the inserts fail.
        log_event("item_added", f"Added product {product_id} ({name})")
        # Keep the product and inventory records in the same transaction.
        database.commit()
    except Exception:
        database.rollback()
        raise

    return product_id


def add_supplier(supplier_name, contact_email, contact_phone):
    """Create a supplier and return its ID."""
    database = get_db()
    supplier_name = supplier_name.strip()
    contact_email = contact_email.strip()
    contact_phone = contact_phone.strip()
    try:
        cursor = database.execute(
            """
            INSERT INTO suppliers (supplier_name, contact_email, contact_phone)
            VALUES (?, ?, ?)
            """,
            (supplier_name, contact_email, contact_phone),
        )
        database.commit()
    except Exception:
        database.rollback()
        raise
    return cursor.lastrowid


def remove_supplier(supplier_id):
    """Remove a supplier and leave associated products without a supplier."""
    database = get_db()
    # Foreign-key behavior clears supplier references from associated products.
    result = database.execute(
        "DELETE FROM suppliers WHERE supplier_id = ?", (supplier_id,)
    )
    if result.rowcount == 0:
        raise ValueError(f"No supplier found with ID {supplier_id}")
    database.commit()


def remove_item(product_id):
    """Remove a product and its related inventory records."""
    database = get_db()
    # The schema's foreign-key cascade removes related inventory records.
    result = database.execute(
        "DELETE FROM products WHERE product_id = ?",
        (product_id,),
    )
    if result.rowcount == 0:
        raise ValueError(f"No item found with product ID {product_id}")

    log_event("item_removed", f"Removed product {product_id}")
    database.commit()


def update_quantity(product_id, quantity, user_id=None):
    """Set an item's inventory quantity."""
    if quantity < 0:
        raise ValueError("Quantity cannot be negative")

    database = get_db()
    database.execute("BEGIN IMMEDIATE")
    try:
        previous = database.execute(
            "SELECT quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchone()
        if previous is None:
            raise ValueError(f"No item found with product ID {product_id}")

        database.execute(
            "UPDATE inventory SET quantity = ? WHERE product_id = ?",
            (quantity, product_id),
        )
        queue_low_stock_reorder(
            product_id, user_id, previous_quantity=previous["quantity"]
        )
        log_event(
            "quantity_updated",
            f"Set product {product_id} quantity to {quantity}",
            user_id=user_id,
        )
        database.commit()
    except Exception:
        database.rollback()
        raise


def adjust_quantity(product_id, quantity_change, user_id=None):
    """Add or remove units without allowing stock to become negative."""
    if not isinstance(quantity_change, int) or quantity_change == 0:
        raise ValueError("Quantity change must be a nonzero integer")

    database = get_db()
    database.execute("BEGIN IMMEDIATE")
    try:
        previous = database.execute(
            "SELECT quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchone()
        if previous is None:
            raise ValueError(f"No item found with product ID {product_id}")

        result = database.execute(
            """
            UPDATE inventory
            SET quantity = quantity + ?
            WHERE product_id = ? AND quantity + ? >= 0
            """,
            (quantity_change, product_id, quantity_change),
        )
        if result.rowcount == 0:
            raise ValueError("Stock cannot be negative")

        queue_low_stock_reorder(
            product_id, user_id, previous_quantity=previous["quantity"]
        )
        log_event(
            "quantity_adjusted",
            f"Adjusted product {product_id} quantity by {quantity_change}",
            user_id=user_id,
        )
        database.commit()
    except Exception:
        database.rollback()
        raise


def queue_low_stock_reorder(product_id, user_id=None, previous_quantity=None):
    """Queue only when a quantity decrease crosses into the low-stock range."""
    database = get_db()
    item = database.execute(
        """
        SELECT products.name, inventory.quantity, inventory.low_stock_threshold,
               inventory.reorder_amount
        FROM products
        JOIN inventory ON inventory.product_id = products.product_id
        WHERE products.product_id = ? AND products.status = 'active'
        """,
        (product_id,),
    ).fetchone()
    if (
        item is None
        or previous_quantity is None
        or previous_quantity <= item["low_stock_threshold"]
        or item["quantity"] > item["low_stock_threshold"]
        or item["reorder_amount"] <= 0
    ):
        return False

    active_order = database.execute(
        """SELECT 1 FROM reorders
        WHERE product_id = ? AND status IN ('pending', 'ordered')""",
        (product_id,),
    ).fetchone()
    if active_order is not None:
        return False

    result = database.execute(
        """
        INSERT OR IGNORE INTO reorders (product_id, quantity_ordered, status)
        VALUES (?, ?, 'pending')
        """,
        (product_id, item["reorder_amount"]),
    )
    if result.rowcount == 0:
        return False

    log_event(
        "reorder_queued",
        f"Automatically queued reorder for {item['name']} "
        f"({item['reorder_amount']} units)",
        user_id=user_id,
    )
    return True

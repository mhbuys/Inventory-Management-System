# Inventory Management System Functions

This document describes the current item-management functions and where readers can find their implementation.

## `query_db`

- **Location:** `database.py` (`query_db`)
- **Purpose:** Executes a parameterized read query and returns all matching rows.
- **Parameters:**
  - `query`: SQL query string using `?` placeholders for values.
  - `parameters`: Values bound to the query placeholders. Defaults to an empty tuple.
- **Returns:** A list of `sqlite3.Row` objects.
- **Database behavior:** Uses the current Flask application's database connection.

## `add_item`

- **Location:** `items.py`, line 4 (`add_item`)
- **Date added:** 2026-09-14
- **Purpose:** Adds a new product to the `products` table and creates its matching inventory record in the `inventory` table.
- **Parameters:**
  - `name`: Product name.
  - `category`: Product category, such as `board_game`, `card_game`, `dice`, or `miniature`.
  - `description`: Optional product description.
  - `price`: Product price. Defaults to `0`.
  - `quantity`: Starting inventory quantity. Defaults to `0`.
  - `low_stock_threshold`: Quantity at which the item is considered low in stock. Defaults to `0`.
  - `reorder_amount`: Quantity to order when restocking. Defaults to `0`. This remains
    available to application code, but the Add Item page now configures it from the
    reorder workflow instead of collecting it during item creation.
- **Returns:** The new product ID.
- **Database behavior:** The product and inventory records are committed together. If either insert fails, the transaction is rolled back.

## `remove_item`

- **Location:** `items.py`, line 42 (`remove_item`)
- **Date added:** 2026-09-14
- **Purpose:** Removes a product from the `products` table using its product ID.
- **Parameters:**
  - `product_id`: ID of the product to remove.
- **Returns:** Nothing after a successful deletion.
- **Database behavior:** The database schema's foreign-key cascade also removes the product's related inventory record.
- **Errors:** Raises `ValueError` when no product exists with the supplied ID.

## `update_quantity`

- **Location:** `items.py` (`update_quantity`)
- **Purpose:** Replaces an item's current inventory quantity using its product ID.
- **Parameters:**
  - `product_id`: ID of the product to update.
  - `quantity`: New nonnegative inventory quantity.
- **Returns:** Nothing after a successful update.
- **Database behavior:** The updated inventory record is committed immediately.
- **Errors:** Raises `ValueError` for a missing product or negative quantity.

## `adjust_quantity`

- **Location:** `items.py` (`adjust_quantity`)
- **Date added:** 2026-09-26
- **Purpose:** Adds or removes a requested number of units from an item's current inventory quantity.
- **Parameters:**
  - `product_id`: ID of the product to adjust.
  - `quantity_change`: Nonzero integer amount to add. Use a positive value to add stock and a negative value to remove stock.
- **Returns:** Nothing after a successful update.
- **Database behavior:** Updates the quantity atomically and commits the change immediately.
- **Errors:** Raises `ValueError` for a missing product, a zero or non-integer change, or an adjustment that would make stock negative.

## `inventory_page`

- **Location:** `app.py` (`inventory_page`)
- **Purpose:** Displays all active inventory items and their current stock levels.
- **Low-stock behavior:** Items at or below `low_stock_threshold` display a bold red
  low-stock alert. Selecting the alert opens the reorder workflow for that product.
- **Access:** Requires an authenticated user.

## `reorder_page`

- **Location:** `app.py` (`reorder_page`)
- **Purpose:** Displays active queued orders and, when a low-stock product is selected,
  displays the order form for that product.
- **Parameters:**
  - `product_id`: Optional query-string product ID. When supplied, the product must
    be active and at or below its low-stock threshold.
- **Order choices:** The user can enter a custom order quantity or select the automatic
  reorder option. The queued-order page includes a back button that returns to the
  queue without the selected product form.
- **Access:** Requires an authenticated user.

## `queue_reorder`

- **Location:** `app.py` (`queue_reorder`)
- **Purpose:** Creates a pending record in the `reorders` table for a low-stock product.
- **Parameters:**
  - `product_id`: ID of the active low-stock product.
  - `quantity_ordered`: Custom positive integer quantity.
  - `automatic_amount`: Checkbox value of `1` when automatic ordering is selected.
  - `automatic_reorder_amount`: Positive integer saved as the product's automatic
    reorder amount and used for the new order when automatic ordering is selected.
- **Database behavior:** Saves the automatic amount to `inventory.reorder_amount`,
  creates the pending reorder, and records a reorder event in `event_logs`.
- **Errors:** Returns a client error for an invalid product, a product that is no
  longer low in stock, an invalid or non-positive quantity, or an existing pending
  or ordered reorder for the same product.
- **Access:** Requires an authenticated user.

## `cancel_reorder`

- **Location:** `app.py` (`cancel_reorder`)
- **Purpose:** Cancels an active queued order without deleting its history.
- **Parameters:**
  - `reorder_id`: ID of the pending or ordered reorder to cancel.
- **Database behavior:** Changes the reorder status to `cancelled` and records a
  cancellation event in `event_logs`.
- **Errors:** Returns `404` when the reorder does not exist or is already completed,
  cancelled, or otherwise inactive.
- **Access:** Requires an authenticated user.

## Automatic quantity synchronization

- **Location:** `template/reorders.html`
- **Purpose:** Keeps the custom order quantity field synchronized with the automatic
  reorder amount when the automatic checkbox is selected.
- **Behavior:** Checking the option copies the automatic amount into the custom
  quantity field. Editing the automatic amount updates the custom quantity live.
  Unchecking the option restores the user's previous custom quantity.

## How To Find The Functions

1. Open `items.py` in the project root.
2. Open `app.py` to locate the inventory and reorder route functions.
3. Open `template/reorders.html` to locate the automatic quantity synchronization.
4. Use your code editor's search feature to locate a function by name (e.g.,
   `add_item`, `reorder_page`, or `cancel_reorder`).

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
  - `supplier_id`: Optional ID of an existing supplier from the supplier-management
    page. The web form uses this value instead of collecting supplier details while
    an item is being added.
- **Returns:** The new product ID.
- **Database behavior:** The product and inventory records are committed together. If either insert fails, the transaction is rolled back.

## `add_supplier`

- **Location:** `items.py`, line 91 (`add_supplier`)
- **Purpose:** Creates a supplier record in the `suppliers` table.
- **Parameters:**
  - `supplier_name`: Required supplier name.
  - `contact_email`: Required supplier email address.
  - `contact_phone`: Required supplier phone number.
- **Returns:** The new supplier ID.
- **Database behavior:** The supplier is committed as one transaction. Database
  errors roll back the insert.
- **Duplicate behavior:** The `manage_suppliers_page` route checks supplier name,
  email, and phone before calling this helper and reports duplicate information to
  the user.

## `remove_supplier`

- **Location:** `items.py`, line 112 (`remove_supplier`)
- **Purpose:** Removes a supplier by ID.
- **Parameters:**
  - `supplier_id`: ID of the supplier to remove.
- **Returns:** Nothing after a successful deletion.
- **Database behavior:** Products assigned to the supplier retain their inventory
  records and have their supplier reference cleared by the schema's
  `ON DELETE SET NULL` rule.
- **Errors:** Raises `ValueError` when no supplier exists with the supplied ID.

## `remove_item`

- **Location:** `items.py`, line 42 (`remove_item`)
- **Date added:** 2026-09-14
- **Purpose:** Removes a product from the `products` table using its product ID.
- **Parameters:**
  - `product_id`: ID of the product to remove.
- **Returns:** Nothing after a successful deletion.
- **Database behavior:** The database schema's foreign-key cascade also removes the product's related inventory record.
- **Errors:** Raises `ValueError` when no product exists with the supplied ID.

## `add_item_page`

- **Location:** `app.py` (`add_item_page`)
- **Purpose:** Displays the Add Item form and creates a product and inventory record
  when the form is submitted.
- **Methods:** Accepts `GET` to display the form and `POST` to add an item.
- **Access:** Requires an authenticated administrator or manager.
- **Successful submission:** Displays the confirmation message
  `Item added to the inventory.` and redirects back to `/add-item`, keeping the
  user on the Add Item page for additional entries.
- **Failure behavior:** Keeps the user on the Add Item page, returns HTTP 400,
  and displays an error confirmation when submitted values are invalid.
- **Database behavior:** Uses `add_item` to commit the product and inventory
  records together.

## `manage_suppliers_page`

- **Location:** `app.py` (`manage_suppliers_page`)
- **Purpose:** Provides the Manage suppliers page for creating and removing supplier
  records.
- **Methods:** Accepts `GET` to display suppliers and `POST` to add or remove one.
- **Access:** Requires an authenticated administrator or manager.
- **Add behavior:** Requires a supplier name, email, and phone. Supplier names,
  email addresses, and phone numbers are checked against existing records so
  repeated supplier information produces an error instead of another record.
- **Remove behavior:** Presents existing suppliers in a dropdown and removes the
  selected supplier through `remove_supplier`.
- **Routes:** Available at `/manage-suppliers` and the shorter `/suppliers` alias.
- **Failure behavior:** Displays a flash error and redirects back to the supplier
  management page without changing the database.

## `remove_item_page`

- **Location:** `app.py` (`remove_item_page`)
- **Purpose:** Displays the removal form with all active inventory items available
  for selection.
- **Methods:** Accepts `GET` only.
- **Access:** Requires an authenticated administrator.
- **Successful removal behavior:** The corresponding `remove_item_action` route
  redirects back to `/remove-item` and displays the confirmation message
  `Item removed from the inventory.`.

## `remove_item_action`

- **Location:** `app.py` (`remove_item_action`)
- **Purpose:** Removes the selected active inventory item from the database.
- **Methods:** Accepts `POST` from the Remove Item form.
- **Parameters:**
  - `product_id`: ID of the product selected for removal.
- **Access:** Requires an authenticated administrator.
- **Successful submission:** Displays the confirmation message
  `Item removed from the inventory.` and redirects back to `/remove-item`, keeping
  the user on the Remove Item page.
- **Failure behavior:** Keeps the user on the Remove Item page, returns HTTP 400,
  and displays an error confirmation when the product ID is invalid or the item
  cannot be found.

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

## Automatic low-stock reorders

- **Location:** `items.py` (`queue_low_stock_reorder`)
- **Purpose:** Automatically creates a pending reorder when an active item's quantity
  decreases from above its low-stock threshold to at or below the threshold.
- **Trigger points:** A quantity decrease that crosses the threshold. Creating an item,
  changing its reorder settings, or making further quantity changes while it remains low
  does not automatically queue another order.
- **Order quantity:** Uses the item's configured `reorder_amount`. Items configured
  with an amount of `0` are never automatically ordered.
- **Duplicate prevention:** An existing pending or ordered reorder prevents another
  automatic order for the same item. After stock rises above the threshold, a later
  downward crossing can queue a new order. The order and audit event are saved in the
  same transaction as the quantity change.

## `inventory_page`

- **Location:** `app.py` (`inventory_page`)
- **Purpose:** Displays all active inventory items and their current stock levels.
- **Low-stock behavior:** Items at or below `low_stock_threshold` display a bold red
  low-stock alert. Selecting the alert opens the reorder workflow for that product.
  When a quantity decrease crosses into low stock, a pending order is automatically
  queued if its configured reorder amount is greater than zero.
- **Pending-order behavior:** Items with a pending reorder display the pending order
  quantity in place of the low-stock reorder link.
- **Access:** Requires an authenticated user.

## `users_page`

- **Location:** `app.py` (`users_page`)
- **Purpose:** Lists user accounts and lets administrators create accounts, assign
  roles, and remove accounts from one management page.
- **Methods:** Accepts `GET` to display the account list and `POST` to create an account.
- **Parameters for account creation:**
  - `username`: Required user name, trimmed of surrounding spaces and limited to 80
    characters.
  - `role`: Required role selected from the supported roles.
- **Temporary password:** Generates a random 12-character temporary password after
  validating the user name. The password is displayed once on the successful response
  and is not stored in plaintext.
- **Database behavior:** Stores a password hash, assigns the requested role, and logs
  account creation. New accounts have `must_change_password = 1`.
- **Access:** Administrator only. Role updates and account deletion are handled by
  separate administrator-only POST routes; the last administrator and the signed-in
  administrator cannot be removed.

## `login`

- **Location:** `app.py` (`login`)
- **Purpose:** Authenticates an existing user with a user name and password.
- **Temporary-account behavior:** A valid temporary password starts a session with the
  required-password-change flag. The existing `change_password` route then prevents
  access to inventory pages until the temporary password is replaced.
- **Access:** Available without authentication.

## `reorder_page`

- **Location:** `app.py` (`reorder_page`)
- **Purpose:** Displays active queued orders and the available reorder forms.
- **Parameters:**
  - `product_id`: Optional query-string product ID. In the low-stock workflow, the
    product must be active and at or below its low-stock threshold. In manual mode,
    it may be any active product.
  - `manual`: Set to `1` to display the manual-order form and all active inventory
    items in the product selector.
- **Order choices:** The low-stock workflow accepts a custom quantity for the selected
  item. The page also provides a **Manual order** button that opens a selector for any
  active item, including items that are not low in stock.
- **Access:** Requires an authenticated administrator or manager.

## `queue_reorder`

- **Location:** `app.py` (`queue_reorder`)
- **Purpose:** Creates a pending record in the `reorders` table for an active product.
- **Parameters:**
  - `product_id`: ID of the active product to order.
  - `quantity_ordered`: Positive integer quantity for a custom or manual order.
  - `automatic_amount`: Checkbox value of `1` when automatic ordering is selected.
  - `automatic_reorder_amount`: Positive integer saved as the product's automatic
    reorder amount and used for the new order when automatic ordering is selected.
- **Manual-order behavior:** Manual orders intentionally bypass the low-stock check,
  allowing an administrator or manager to order any active inventory item.
- **Database behavior:** Saves the automatic amount to `inventory.reorder_amount`,
  creates the pending reorder, and records a reorder event in `event_logs`.
- **Errors:** Returns a client error for an invalid or inactive product, an invalid
  or non-positive quantity, or an existing pending or ordered reorder for the same
  product.
- **Access:** Requires an authenticated administrator or manager.

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

## Manual order form

- **Location:** `template/reorders.html`
- **Purpose:** Provides the queue page's manual-order user interface.
- **Behavior:** The form lists every active inventory item, displays its current
  quantity, accepts a positive order quantity, and submits to `queue_reorder`.
  Server-side validation remains authoritative for the selected item, quantity,
  duplicate active orders, and authorization.

## Automatic ordering

- **Location:** `items.py` (`queue_low_stock_reorder`) and
  `app.py` (`queue_reorder`)
- **Purpose:** Automatically creates a pending reorder when an active item's quantity
  crosses from above its low-stock threshold to at or below that threshold.
- **Order quantity:** Uses the item's configured `reorder_amount`. An amount of `0`
  disables automatic ordering for that item.
- **Duplicate prevention:** An existing pending or ordered reorder prevents another
  active order for the same item. After stock rises above the threshold, a later
  downward crossing can queue a new automatic order.
- **Manual-order relationship:** Manual ordering is an additional option and does not
  replace automatic low-stock ordering. Manual orders may be placed for any active
  item, while automatic orders continue to be triggered by low-stock threshold
  crossings.

## How To Find The Functions

1. Open `items.py` in the project root.
2. Open `app.py` to locate the inventory and reorder route functions.
3. Open `template/users.html` to locate the user-management page and account dialogs.
4. Open `template/reorders.html` to locate the low-stock and manual-order forms.
5. Use your code editor's search feature to locate a function by name (e.g.,
   `add_item`, `users_page`, `reorder_page`, or `cancel_reorder`).

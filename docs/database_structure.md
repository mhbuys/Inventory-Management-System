# Inventory Management System - Database Structure

The Inventory Management System stores its data in a SQLite database that supports catalog management, inventory tracking, user authentication, authorization, audit logging, and secure two-factor authentication.

## Core design goals

- Track products, suppliers, and current stock levels.
- Support low-stock alerts and reorder workflows.
- Log inventory changes and system activity for auditing.
- Manage users and role-based permissions.
- Support self-service 2FA and recovery backup codes.

## Database schema

### 1. suppliers

Stores supplier information used for restocking and ordering.

| Column | Type | Description |
|---|---|---|
| supplier_id | INTEGER PK | Unique supplier identifier |
| supplier_name | TEXT | Supplier name; must be unique |
| contact_email | TEXT | Optional supplier contact email |
| contact_phone | TEXT | Optional supplier phone number |
| created_at | TEXT | Timestamp when the supplier record was created |

### 2. products

Stores the product catalog for the game store.

| Column | Type | Description |
|---|---|---|
| product_id | INTEGER PK | Unique product identifier |
| name | TEXT | Product name; must be unique |
| description | TEXT | Product description or notes |
| price | REAL | Product price; must be greater than or equal to 0 |
| category | TEXT | Product category; allowed values: `board_game`, `card_game`, `dice`, `miniature` |
| status | TEXT | Active/inactive state; allowed values: `active`, `discontinued` |
| supplier_id | INTEGER FK | Supplier associated with the product |
| supplier_sku | TEXT | Optional supplier-managed SKU or item code |
| created_at | TEXT | Timestamp when the product was created |
| updated_at | TEXT | Timestamp of the last product update |

### 3. inventory

Stores current stock totals and reordering settings for each product.

| Column | Type | Description |
|---|---|---|
| inventory_id | INTEGER PK | Unique inventory record identifier |
| product_id | INTEGER FK | Product associated with the inventory row |
| quantity | INTEGER | Current on-hand quantity; cannot be negative |
| low_stock_threshold | INTEGER | Quantity threshold for low-stock alerts |
| reorder_amount | INTEGER | Quantity to reorder when the stock falls below threshold |

### 4. users

Stores application users and authentication state.

| Column | Type | Description |
|---|---|---|
| user_id | INTEGER PK | Unique user identifier |
| username | TEXT | Login username; must be unique |
| password_hash | TEXT | Hashed password value |
| must_change_password | INTEGER | Whether the user must reset their password before continuing |

### 5. user_2fa

Stores per-user two-factor authentication settings.

| Column | Type | Description |
|---|---|---|
| user_id | INTEGER PK/FK | User associated with the 2FA settings |
| secret_key | TEXT | Secret used to generate TOTP codes |
| is_enabled | INTEGER | Whether 2FA is enabled for the account |
| confirmed_at | TEXT | Timestamp when 2FA was confirmed |
| updated_at | TEXT | Last time the 2FA settings were updated |

### 6. user_backup_codes

Stores hash-based one-time recovery codes for users who lose access to their authenticator app.

| Column | Type | Description |
|---|---|---|
| backup_code_id | INTEGER PK | Unique backup code record identifier |
| user_id | INTEGER FK | User the backup code belongs to |
| code_hash | TEXT | Hashed backup code |
| used_at | TEXT | Timestamp when a code was redeemed; null until used |
| created_at | TEXT | Timestamp when the code was generated |

### 7. roles

Stores the distinct permission groups available in the application.

| Column | Type | Description |
|---|---|---|
| role_id | INTEGER PK | Unique role identifier |
| role_name | TEXT | Role name; must be unique |

### 8. user_roles

Link table connecting users to one or more roles.

| Column | Type | Description |
|---|---|---|
| user_id | INTEGER FK | User assigned to the role |
| role_id | INTEGER FK | Role assigned to the user |

The composite primary key is (`user_id`, `role_id`).

### 9. inventory_transactions

Stores changes in stock quantities and the associated reason for the transaction.

| Column | Type | Description |
|---|---|---|
| transaction_id | INTEGER PK | Unique transaction identifier |
| product_id | INTEGER FK | Product affected by the transaction |
| user_id | INTEGER FK | User responsible for the change, if known |
| quantity_change | INTEGER | Positive or negative change in quantity |
| transaction_type | TEXT | Type of change: `purchase`, `sale`, `adjustment`, `alert`, or `reorder` |
| date_time | TEXT | Timestamp of the transaction |

### 10. reorders

Tracks purchase orders created to replenish inventory.

| Column | Type | Description |
|---|---|---|
| reorder_id | INTEGER PK | Unique reorder record identifier |
| product_id | INTEGER FK | Product being reordered |
| quantity_ordered | INTEGER | Quantity requested for the reorder |
| reorder_date | TEXT | Timestamp when the reorder was created |
| status | TEXT | Reorder state: `pending`, `ordered`, `received`, or `cancelled` |

### 11. event_logs

Captures system and user activity for auditing and debugging.

| Column | Type | Description |
|---|---|---|
| log_id | INTEGER PK | Unique event log identifier |
| user_id | INTEGER FK | User associated with the event, if applicable |
| event_type | TEXT | Event category or name |
| description | TEXT | Human-readable event description |
| date_time | TEXT | Timestamp when the event was recorded |

## Relationship summary

- `suppliers` has a one-to-many relationship with `products` via `supplier_id`.
- `products` has a one-to-one relationship with `inventory` via `product_id`.
- `products` has many `inventory_transactions` records.
- `products` has many `reorders` records.
- `users` has many `inventory_transactions` and `event_logs` records.
- `users` and `roles` are connected through the `user_roles` link table.
- `users` has a one-to-one relationship with `user_2fa` via `user_id`.
- `users` has many `user_backup_codes` records.

## Referential integrity and constraints

The schema enforces foreign key relationships and validations to preserve data integrity:

- `products.supplier_id` references `suppliers.supplier_id` with `ON DELETE SET NULL`.
- `inventory.product_id` references `products.product_id` with `ON DELETE CASCADE`.
- `user_2fa.user_id` references `users.user_id` with `ON DELETE CASCADE`.
- `user_backup_codes.user_id` references `users.user_id` with `ON DELETE CASCADE`.
- `user_roles.user_id` and `user_roles.role_id` reference the corresponding parent tables with `ON DELETE CASCADE`.
- `inventory_transactions.product_id` references `products.product_id` with `ON DELETE CASCADE`.
- `reorders.product_id` references `products.product_id` with `ON DELETE CASCADE`.
- `event_logs.user_id` references `users.user_id` with `ON DELETE SET NULL`.

## Indexes and performance notes

The schema includes indexes to optimize common queries and joins:

- `idx_products_category` on `products(category)`
- `idx_products_status` on `products(status)`
- `idx_inventory_transactions_product_id` on `inventory_transactions(product_id)`
- `idx_inventory_transactions_user_id` on `inventory_transactions(user_id)`
- `idx_reorders_product_id` on `reorders(product_id)`
- `idx_active_reorder_per_product` to enforce one active reorder per product where status is `pending` or `ordered`
- `idx_event_logs_user_id` on `event_logs(user_id)`
- `idx_user_backup_codes_user_id` on `user_backup_codes(user_id)`
- `idx_products_supplier_id` on `products(supplier_id)`

## Summary

This schema is designed to support a small but robust operational inventory application. Product data is normalized, inventory updates are recorded with an audit trail, authorization is handled through roles, and user security is strengthened with two-factor authentication and backup code management.

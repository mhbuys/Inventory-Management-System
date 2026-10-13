# Sprint 3 - User Roles and Permissions Planning

---

## 1. Proposed User Roles

### Administrator

The Administrator has full access to the system.

Responsibilities:
- View, add, edit, and delete inventory items.
- Manage product information and prices.
- Update inventory quantities.
- Configure stock thresholds and reorder amounts.
- Place and manage restocking orders.
- Create and manage user accounts.
- Assign and update user permission levels.
- View inventory transaction history.
- View system event logs.
- Manage account security settings.

### Manager

The Manager can handle most inventory operations but cannot manage user permissions.

Responsibilities:
- View inventory and product information.
- Add new products and edit existing products.
- Update product prices.
- Adjust inventory quantities.
- Configure low-stock thresholds.
- Place restocking orders.
- Receive inventory deliveries.
- View inventory transaction history.

Restrictions:
- Cannot create or delete user accounts.
- Cannot assign administrator permissions.
- Cannot access administrative event logs.

### Inventory Employee

Inventory Employees handle daily inventory operations.

Responsibilities:
- View products and inventory information.
- Update stock quantities.
- Record inventory changes.
- Receive deliveries and update received quantities.
- View low-stock alerts.

Restrictions:
- Cannot create new product types.
- Cannot change product prices.
- Cannot place restocking orders.
- Cannot modify reorder thresholds.
- Cannot manage user accounts or permissions.

### Viewer

Viewers have read-only access to inventory information.

Responsibilities:
- View available products.
- Check inventory quantities.
- View low-stock alerts.
- Search inventory records.

Restrictions:
- Cannot add, edit, or delete products.
- Cannot modify inventory quantities.
- Cannot place orders.
- Cannot manage users or permissions.

---

## 2. Proposed Permission Table

The following table outlines which functions each role should be allowed to access.

| Function | Admin | Manager | Employee | Viewer |
|---|---|---|---|---|
| View inventory | Yes | Yes | Yes | Yes |
| Add new products | Yes | Yes | No | No |
| Edit product information | Yes | Yes | No | No |
| Delete products | Yes | No | No | No |
| Change product prices | Yes | Yes | No | No |
| Update stock quantities | Yes | Yes | Yes | No |
| View low-stock alerts | Yes | Yes | Yes | Yes |
| Change reorder thresholds | Yes | Yes | No | No |
| Place restocking orders | Yes | Yes | No | No |
| Receive inventory deliveries | Yes | Yes | Yes | No |
| View inventory transaction history | Yes | Yes | No | No |
| View system event logs | Yes | No | No | No |
| Create new users | Yes | No | No | No |
| Edit user accounts | Yes | No | No | No |
| Delete user accounts | Yes | No | No | No |
| Assign user permission levels | Yes | No | No | No |
| Manage own password and 2FA | Yes | Yes | Yes | Yes |

---

## 3. Website Page Access

### Administrator Pages

Administrators should have access to:
- Inventory Dashboard
- Add Item Page
- Edit Item Page
- Stock Planning Page
- Reorder Management Page
- Inventory History Page
- User Creation Page
- User Management Page
- System Event Logs
- Account Settings

### Manager Pages

Managers should have access to:
- Inventory Dashboard
- Add Item Page
- Edit Item Page
- Stock Planning Page
- Reorder Management Page
- Inventory History Page
- Account Settings

### Inventory Employee Pages

Inventory Employees should have access to:
- Inventory Dashboard
- Stock Quantity Updates
- Receive Inventory Page
- Low-Stock Alerts
- Account Settings

### Viewer Pages

Viewers should have access to:
- Inventory Dashboard
- Product Information
- Low-Stock Alerts
- Account Settings

---

## 4. Permission Restrictions

- Only Administrators should be able to create new users.
- Administrators and Managers should be able to add new products.
- Inventory Employees should be able to update stock quantities but not product prices.
- Viewers should only be able to view inventory information.
- Only Administrators should be able to change another user's permission level.

---

## 5. Database Considerations

Future implementation should consider:

- Assigning a role to each user account.
- Checking user permissions when accessing restricted functions.
- Preventing unauthorized inventory modifications.
- Restricting user creation and account management.
- Recording important actions through the event logging system.
- Applying appropriate permissions to newly created users.

User accounts should receive only the permissions necessary for their responsibilities.

---

## 6. Future Implementation

Future development can include:

1. Finalizing the list of user roles.
2. Assigning permissions to each role.
3. Connecting user accounts to assigned roles.
4. Restricting website pages based on permissions.
5. Adding server-side permission checks.
6. Testing unauthorized access attempts.
7. Recording permission-related events in system logs.


---

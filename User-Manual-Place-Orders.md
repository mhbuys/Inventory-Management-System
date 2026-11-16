# User Manual: Placing Orders and Automatic Reordering

This guide explains how administrators and managers can create orders, configure
automatic reordering, and manage the reorder queue.

## Who can place orders?

Administrators and managers can open **Stock Planning** and **Reorder queue**.
Employees can adjust inventory quantities; a stock decrease by any user can
trigger an automatic reorder when the item meets the rules below.

## Place an order manually

You can manually order any active inventory item, whether or not it is low in
stock.

1. Sign in as an administrator or manager.
2. Select **Reorder queue** in the navigation bar.
3. Select **Add order**.
4. Choose an **Inventory item** and enter a whole-number **Quantity to order**
   greater than zero.
5. Select **Queue manual order**.

The order appears in **Queued orders** with its quantity, queue date, status, and
supplier details when those details are available. If an active order already
exists for the selected item, the system will not create a duplicate. Cancel the
existing order before creating another one.

### Order an item shown as low stock

On the **Inventory** page, an administrator or manager can select an item's
**LOW STOCK** alert to open its order form. Enter a positive whole-number custom
quantity and select **Queue order**. This creates a manual order; it does not
change the item's saved automatic reorder amount.

## Configure automatic reordering

Automatic reordering uses two settings for each item:

- **Low-stock threshold**: the stock level that defines low stock.
- **Reorder amount**: how many units to put in an automatic order. An amount of
  `0` disables automatic orders for that item.

To set or change these values:

1. Select **Stock Planning**.
2. Choose the inventory item.
3. Enter a whole number of zero or more for **Low-stock threshold** and
   **Reorder amount**.
4. Select **Save settings**.

Saving settings does not create an order by itself, even if the item's current
quantity is already at or below its threshold.

## When an automatic order is created

The system automatically adds an order to the queue when all of the following
are true:

1. The item is active and its stock quantity is decreased.
2. Its quantity moves from **above** the low-stock threshold to **at or below**
   that threshold.
3. Its reorder amount is greater than zero.
4. It has no existing active order.

For example, if the threshold is `5`, decreasing stock from `6` to `5` triggers
an order for the configured reorder amount. The order appears in **Queued
orders**.

An item already at or below its threshold will not automatically generate an
order from further decreases. To trigger a later automatic order, stock must
first be raised above the threshold and then decreased to or below it again.
There can be only one active order per item at a time.

## Review, export, or cancel queued orders

Open **Reorder queue** to review active orders. The queue currently displays an
order status. In the planned queue interface, status labels will be removed and
a **Complete order** action will be available instead. Select **Export to
Excel** to download queued orders, including available supplier contact details.

To cancel an active order, select **Cancel order** on its row. Cancellation
removes it from the active queue; it does not delete the order history.

## Complete an order (planned)

The **Complete order** action is planned for the reorder queue. Once the ordered
items have arrived, select **Complete order** on the matching row. Completing an
order will remove it from the queue and add the ordered quantity to that item's
inventory.

Do not complete an order before it arrives. After completion, do not adjust
inventory again for the same delivery, or the received quantity will be counted
twice. This action is not available in the current version.

## Important: queueing is not supplier submission

An order in this system is a record in the internal reorder queue. The system
does not email a supplier or submit a purchase order. Use the supplier details
in the queue or the Excel export to complete purchasing through your normal
supplier process. The planned **Complete order** action records receipt by
removing the queued order and increasing inventory; it does not contact the
supplier.

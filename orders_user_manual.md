# User Manual: Placing Orders and Automatic Reordering

This guide covers the Reorder Queue and Stock Planning features. Orders in this
system are internal records: the system does **not** send purchase orders to
suppliers. Contact the supplier separately, using the supplier details shown
with the queued order if available.

## Who can place and manage orders?

Administrators and Managers can configure stock planning, add or cancel queued
orders, export the queue, and record received orders. Employees can adjust
stock; a stock adjustment can therefore trigger an automatic reorder. Employees
cannot place or manage orders from the Reorder Queue.

## Place a manual order

Use a manual order when you want to order any active inventory item, whether or
not it is low in stock.

1. Open **Reorder queue** from the Inventory page.
2. Select **Add order**.
3. Choose an inventory item and enter the quantity to order. The quantity must
   be a whole number greater than zero.
4. Select **Queue manual order**.
5. Confirm the item and quantity appear in **Queued orders**.

You can also select the **reorder** link beside an item marked **LOW STOCK** on
the Inventory page. Enter the custom order quantity and select **Queue order**.
The suggested quantity is prefilled from Stock Planning when it is greater than
zero, but you can change it.

Only one active order can exist for an item at a time. If an order for that item
is already pending or ordered, cancel or complete it before creating another.

## Configure automatic reordering

Administrators and Managers can set the low-stock trigger and the quantity
automatically added to the queue:

1. Open **Stock Planning**.
2. Select an inventory item.
3. Enter a **Low-stock threshold** and **Reorder amount**. Both must be
   nonnegative whole numbers.
4. Select **Save settings**.

The threshold is the stock level that triggers an automatic reorder. The reorder
amount is the number of units added to that order. Set the reorder amount to
**0** to disable automatic reordering for that item.

### When an automatic order is queued

An automatic order is queued when all of the following are true:

- A stock adjustment decreases the item's quantity from **above** its
  low-stock threshold to **at or below** that threshold.
- Its reorder amount is greater than zero.
- It has no other active order.

For example, with a threshold of 10 and a reorder amount of 25, decreasing stock
from 11 to 10 queues an order for 25 units. Decreasing stock from 10 to 9 does
not create another order. Increasing stock above 10 and later decreasing it to
10 or below can trigger a new order, provided there is no active order.

The system does not create an order simply because the threshold is changed
while stock is already at or below it. Use a manual order if you need to reorder
in that situation.

## Review, export, cancel, or receive orders

The **Queued orders** list shows active orders, including the item, quantity,
queue date, and supplier contact details when a supplier is linked to the item.

- **Export to Excel** downloads the active queue as `reorders.xlsx`, which you
  can use when placing supplier orders outside the system.
- **Cancel order** removes an order from the active queue. Use this if the
  order should not be fulfilled or if you need to create a replacement.
- **Complete Order** records that the order has been received. Select it only
  after the delivery arrives: the system adds the full ordered quantity to
  inventory and removes the order from the active queue.

The queue is not a supplier-ordering or shipment-tracking service. Completing
an order updates inventory; it does not contact the supplier or verify a
delivery.

## Troubleshooting

- **No automatic order appeared:** Confirm the reorder amount is greater than
  zero, then check whether stock decreased across the threshold (from above it
  to at or below it). An existing active order also prevents a duplicate.
- **Cannot add another order:** Find the existing order in the queue and either
  cancel it or complete it after the delivery is received.
- **Item is low but there is no order:** Low stock by itself does not create an
  order. If stock was already at or below the threshold before settings were
  saved, or if automatic reordering is disabled, use **Add order** to queue one
  manually.

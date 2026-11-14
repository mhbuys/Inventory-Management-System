# Inventory Management System User Manual (Add and Remove Items)

## Adding an item

Use the **Add Item** page to create a new inventory item. The Administrators and managers roles can add items.

### Steps

1.  Sign in to the Inventory Management System.

2.  Click **Add item** from the navigation bar.

3.  Enter the item information:

    - **Item Name**; type down the name of the item

    - **Category**: select Board Game, Card Game, Dice, or Miniatures

    - **Supplier**: Select a supplier that is available or No supplier

    - **Description**: Write an option description of the item

    - **Price:** type down the price of item. Such as, \$15.99

    - **Quantity:** Typed down the stock of the item

    - **Low-Stock Threshold:** Type down the threshold of when a warning message is display for when the stock is getting low.

4.  Select **Add Item**.

After the item is saved, the message **Item added to the inventory.** appears. The Add Item page remains open so another item can be entered. To leave without saving, select **Cancel** or one of the buttons in the navigator bar.

### Add-item errors

If a required value is missing or a value is invalid, the message “**Unable to add the item. Check the entered values and try again.”** appears. Correct the error and submit the form again.

## Deleting an item

The application labels this action **Remove Item**. Removing an item deletes the item from the inventory, including its related inventory record. Only administrators can remove items.

**Caution:** Removing an item changes the inventory database. Confirm that the correct item is selected before submitting the form.

### Steps

1.  Sign in as a user with the **Administrator** role.

2.  Select **Remove item** from the navigation bar.

3.  Open the **Item** list and select the item to delete.

4.  Select **Remove**.

After the item is deleted, the message **Item removed from the inventory.** appears and the Remove Item page is displayed again. The item no longer appears in the active inventory list.

To leave without deleting an item, select **Cancel** or one of the buttons in the navigator bar.

### Delete-item errors

If the selected item is invalid or cannot be found, the message **Unable to remove the item. Select a valid inventory item and try again.** appears. Select an available item and submit the form again.

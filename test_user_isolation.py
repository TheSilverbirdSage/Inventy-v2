import os
import sys
import mongomock
from dotenv import load_dotenv

load_dotenv()

from db_manager import DatabaseManager

def run_tests():
    print("Initializing DatabaseManager with mongomock...")
    mock_client = mongomock.MongoClient()
    db = DatabaseManager(client=mock_client)

    USER_A = 999001
    USER_B = 999002

    print("\n--- Test 1: Insert Items for distinct users ---")
    item_a_data = {
        "category": "Smartphone",
        "model": "iPhone 14 Pro",
        "specs": {"storage": "128GB", "color": "Deep Purple"},
        "purchase_price": 500.0,
        "notes": "User A personal stock"
    }
    item_a_id = db.insert_item(item_a_data, user_id=USER_A)
    assert item_a_id, "Item A insertion failed"
    print(f"✅ User A inserted item: {item_a_id}")

    item_b_data = {
        "category": "Laptop",
        "model": "MacBook Air M2",
        "specs": {"storage": "256GB", "ram": "8GB"},
        "purchase_price": 850.0,
        "notes": "User B personal stock"
    }
    item_b_id = db.insert_item(item_b_data, user_id=USER_B)
    assert item_b_id, "Item B insertion failed"
    print(f"✅ User B inserted item: {item_b_id}")

    print("\n--- Test 2: Query Isolation ---")
    items_a = db.find_items({}, user_id=USER_A)
    assert len(items_a) == 1, f"Expected 1 item for User A, found {len(items_a)}"
    assert items_a[0]["model"] == "iPhone 14 Pro"
    assert items_a[0]["user_id"] == USER_A
    print("✅ User A only sees User A's item")

    items_b = db.find_items({}, user_id=USER_B)
    assert len(items_b) == 1, f"Expected 1 item for User B, found {len(items_b)}"
    assert items_b[0]["model"] == "MacBook Air M2"
    assert items_b[0]["user_id"] == USER_B
    print("✅ User B only sees User B's item")

    print("\n--- Test 3: Cross-User Find by ID Prevention ---")
    cross_find = db.find_item_by_id(item_a_id, user_id=USER_B)
    assert cross_find is None, "Security failure: User B was able to fetch User A's item by ID"
    print("✅ User B cannot find User A's item by ID")

    print("\n--- Test 4: Cross-User Update Prevention ---")
    update_res = db.update_item(item_a_id, {"notes": "Tampered by User B"}, user_id=USER_B)
    assert update_res is False, "Security failure: User B was able to update User A's item"
    # Verify original note is intact
    item_a_check = db.find_item_by_id(item_a_id, user_id=USER_A)
    assert item_a_check["notes"] == "User A personal stock"
    print("✅ User B cannot modify User A's item notes")

    print("\n--- Test 5: Cross-User Add Repair Cost Prevention ---")
    repair_res = db.add_repair_cost(item_a_id, 100.0, user_id=USER_B)
    assert repair_res is False, "Security failure: User B was able to add repair cost to User A's item"
    item_a_check = db.find_item_by_id(item_a_id, user_id=USER_A)
    assert item_a_check["financials"]["repair_costs"] == 0
    print("✅ User B cannot add repair cost to User A's item")

    print("\n--- Test 6: Cross-User Sell Item Prevention ---")
    cross_sell_profit = db.mark_as_sold(item_a_id, sale_price=800.0, user_id=USER_B)
    assert cross_sell_profit is None, "Security failure: User B was able to mark User A's item as sold"
    item_a_check = db.find_item_by_id(item_a_id, user_id=USER_A)
    assert item_a_check["status"] == "In Stock"
    print("✅ User B cannot mark User A's item as sold")

    print("\n--- Test 7: Authorized Owner Operations ---")
    # User A adds repair cost
    auth_repair = db.add_repair_cost(item_a_id, 50.0, user_id=USER_A)
    assert auth_repair is True
    # User A sells item
    # Purchase = 500, Repairs = 50, Sale = 750 -> Profit = 200
    profit = db.mark_as_sold(item_a_id, sale_price=750.0, user_id=USER_A)
    assert profit == 200.0, f"Expected profit 200.0, got {profit}"
    item_a_sold = db.find_item_by_id(item_a_id, user_id=USER_A)
    assert item_a_sold["status"] == "Sold"
    assert item_a_sold["financials"]["profit"] == 200.0
    print("✅ User A successfully updated and sold their own item with exact profit calculation")

    print("\n🎉 All 7 user isolation tests PASSED successfully!")

if __name__ == "__main__":
    run_tests()

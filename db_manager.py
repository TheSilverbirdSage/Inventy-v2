import os
from pymongo import MongoClient
from datetime import datetime

class DatabaseManager:
    def __init__(self, mongodb_uri=None, client=None):
        if client is not None:
            self.client = client
        else:
            self.client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        self.db = self.client['inventy_db']
        self.collection = self.db['inventory']
        self.ensure_indexes()

    def ensure_indexes(self):
        """Creates indexes for user-scoped queries and performance."""
        try:
            self.collection.create_index([("user_id", 1)])
            self.collection.create_index([("user_id", 1), ("status", 1)])
        except Exception:
            # Avoid crashing if read-only, offline, or index already exists
            pass

    def insert_item(self, item_data, user_id):
        """Inserts a new item into the inventory for a specific user."""
        item_data['user_id'] = user_id
        item_data['status'] = 'In Stock'
        item_data['created_at'] = datetime.utcnow()
        item_data['financials'] = {
            'purchase_price': item_data.get('purchase_price', 0),
            'repair_costs': 0,
            'sale_price': 0,
            'profit': 0
        }
        result = self.collection.insert_one(item_data)
        return str(result.inserted_id)

    def find_items(self, query, user_id):
        """Finds items based on a query dictionary, scoped to a user."""
        filter_query = dict(query) if query else {}
        filter_query['user_id'] = user_id
        return list(self.collection.find(filter_query))

    def find_item_by_id(self, item_id, user_id):
        """Finds a single item by its MongoDB ID and user ID."""
        from bson.objectid import ObjectId
        return self.collection.find_one({"_id": ObjectId(item_id), "user_id": user_id})

    def update_item(self, item_id, update_data, user_id):
        """Updates specific fields of an item, scoped to a user."""
        from bson.objectid import ObjectId
        result = self.collection.update_one(
            {"_id": ObjectId(item_id), "user_id": user_id},
            {"$set": update_data}
        )
        return result.modified_count > 0

    def add_repair_cost(self, item_id, cost, user_id):
        """Increments repair costs for an item, scoped to a user."""
        from bson.objectid import ObjectId
        result = self.collection.update_one(
            {"_id": ObjectId(item_id), "user_id": user_id},
            {"$inc": {"financials.repair_costs": cost}}
        )
        return result.modified_count > 0

    def mark_as_sold(self, item_id, sale_price, user_id):
        """Marks item as sold and calculates profit, strictly scoped to a user."""
        from bson.objectid import ObjectId
        item = self.find_item_by_id(item_id, user_id)
        if not item:
            return None

        purchase = item.get('financials', {}).get('purchase_price', 0)
        repairs = item.get('financials', {}).get('repair_costs', 0)
        profit = sale_price - (purchase + repairs)

        result = self.collection.update_one(
            {"_id": ObjectId(item_id), "user_id": user_id},
            {"$set": {
                "status": "Sold",
                "financials.sale_price": sale_price,
                "financials.profit": profit
            }}
        )
        return profit if result.modified_count > 0 else None


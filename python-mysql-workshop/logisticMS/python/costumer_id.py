import random
from database import get_db_connection


def _generate_id(table, column, min_val, max_val):
    """Keep generating a random ID until we find one not already in the DB."""
    conn = get_db_connection()
    cursor = conn.cursor()
    while True:
        new_id = str(random.randint(min_val, max_val))
        cursor.execute(f"SELECT 1 FROM {table} WHERE {column} = %s", (new_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return new_id


def generate_unique_customer_id():
    return _generate_id("customer", "Customer_ID", 100000, 999999)

def generate_unique_order_id():
    return _generate_id("c_order", "Order_ID", 10000, 99999)

def generate_unique_order_item_id():
    return _generate_id("order_item", "Order_Item_ID", 1000000, 9999999)

def generate_unique_shipment_id():
    return _generate_id("shipment", "Shipment_ID", 1000, 9999)

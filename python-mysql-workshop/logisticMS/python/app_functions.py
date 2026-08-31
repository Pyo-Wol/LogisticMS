import os
import re
from datetime import date

COMPLETED_STATUSES = ('Delivered',)

SHIPMENT_STATUSES = ('Preparing', 'In-Transit', 'Delivered')

REGION_CARRIERS = {
    "SWEDEN": 2, "NORWAY": 2, "DENMARK": 2,
    "USA": 672, "MEXICO": 672, "CANADA": 672,
    "NIGERIA": 101, "SOUTH AFRICA": 101, "EGYPT": 101,
}

CHART_COLORS = ['#C2643C', '#C79A3E', '#7E9968', '#A64B2A', '#B99B6B', '#7B7466']

ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "admin123"


def admin_login_is_valid(email, password):
    return email == ADMIN_EMAIL and password == ADMIN_PASSWORD


def find_customer(cursor, email, password):
    cursor.execute(
        "SELECT * FROM customer WHERE email=%s AND loginPassword=%s",
        (email, password)
    )
    return cursor.fetchone()


def email_is_taken(cursor, email):
    cursor.execute("SELECT 1 FROM customer WHERE email = %s", (email,))
    return cursor.fetchone() is not None


def signup_error(cursor, name, email, password, address):
    if email_is_taken(cursor, email):
        return "Account already exists"
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return "Invalid email format"
    if not name.strip() or not password:
        return "Please fill all fields"
    if address.upper() not in REGION_CARRIERS:
        return "We do not deliver to that country yet"
    return None


def create_customer(cursor, name, email, password, address):
    cursor.execute(
        "INSERT INTO customer (Fname, Email, Created_date, loginPassword, address) "
        "VALUES (%s, %s, %s, %s, %s)",
        (name, email, date.today().strftime("%Y-%m-%d"), password, address)
    )


def get_products(cursor):
    cursor.execute(
        "SELECT Product_ID, P_name, Category, Price, Stock_quantity "
        "FROM product ORDER BY Category, P_name"
    )
    return cursor.fetchall()


def stock_by_name(products):
    return {product["P_name"]: product["Stock_quantity"] for product in products}


def price_by_name(products):
    return {product["P_name"]: product["Price"] for product in products}


def group_by_category(products):
    grouped = {}
    for product in products:
        grouped.setdefault(product["Category"], []).append(product)
    return grouped


def get_customer_order_rows(cursor, customer_id):
    cursor.execute(
        "SELECT o.Order_ID, o.Order_date, o.Order_status, "
        "p.P_name, oi.Quantity, oi.Unit_price "
        "FROM c_order o "
        "JOIN order_item oi ON o.Order_ID = oi.Order_ID "
        "JOIN product p ON oi.Product_ID = p.Product_ID "
        "WHERE o.Customer_ID = %s "
        "ORDER BY o.Order_date DESC",
        (customer_id,)
    )
    return cursor.fetchall()


def new_customer_order(row):
    return {
        'id': row['Order_ID'],
        'date': row['Order_date'],
        'status': row['Order_status'],
        'order_items': [],
        'total': 0,
    }


def new_customer_order_item(row):
    return {
        'name': row['P_name'],
        'qty': row['Quantity'],
        'price': row['Unit_price'],
    }


def group_customer_orders(rows):
    orders = {}
    for row in rows:
        order = orders.setdefault(row['Order_ID'], new_customer_order(row))
        order['order_items'].append(new_customer_order_item(row))
        order['total'] += row['Quantity'] * row['Unit_price']
    return list(orders.values())


def split_orders_by_status(orders):
    ongoing = [order for order in orders if order['status'] not in COMPLETED_STATUSES]
    past = [order for order in orders if order['status'] in COMPLETED_STATUSES]
    return ongoing, past


def get_stock_and_weight_lookups(cursor):
    cursor.execute("SELECT Product_ID, Stock_quantity, Weight_kg FROM product")
    products = cursor.fetchall()
    stocks = {}
    weights = {}
    for product in products:
        product_id = str(product['Product_ID'])
        stocks[product_id] = product['Stock_quantity']
        weights[product_id] = float(product['Weight_kg'] or 0)
    return stocks, weights


def get_carrier_rates(cursor, customer_id):
    cursor.execute(
        "SELECT "
        "  get_base_rate((SELECT address FROM customer WHERE Customer_ID = %s))   AS base_rate, "
        "  get_rate_per_kg((SELECT address FROM customer WHERE Customer_ID = %s)) AS rate_per_kg",
        (customer_id, customer_id)
    )
    row = cursor.fetchone()
    return {
        'base_rate': float(row['base_rate'] or 0),
        'rate_per_kg': float(row['rate_per_kg'] or 0),
    }


def current_month_start():
    return date.today().strftime("%Y-%m") + "-01"


def restock_product(cursor, product_id, quantity):
    cursor.execute(
        "UPDATE product SET Stock_quantity = Stock_quantity + %s WHERE Product_ID = %s",
        (quantity, product_id)
    )


def get_low_stock_products(cursor):
    cursor.execute(
        "SELECT Product_ID, P_name, Price, Stock_quantity FROM product "
        "WHERE Stock_quantity <= Reorder_level"
    )
    return cursor.fetchall()


def completed_status_placeholders():
    return ", ".join(["%s"] * len(COMPLETED_STATUSES))


def get_delivered_revenue(cursor):
    cursor.execute(
        "SELECT COALESCE(SUM(oi.Quantity * oi.Unit_price), 0) AS total "
        "FROM order_item oi JOIN c_order o ON oi.Order_ID = o.Order_ID "
        "WHERE o.Order_status IN (" + completed_status_placeholders() + ")",
        COMPLETED_STATUSES
    )
    return cursor.fetchone()['total']


def get_delivered_revenue_since(cursor, month_start):
    cursor.execute(
        "SELECT COALESCE(SUM(oi.Unit_price * oi.Quantity), 0) AS total "
        "FROM order_item oi JOIN c_order o ON oi.Order_ID = o.Order_ID "
        "WHERE o.Order_status IN (" + completed_status_placeholders() + ") AND o.Order_date >= %s",
        COMPLETED_STATUSES + (month_start,)
    )
    return cursor.fetchone()['total']


def count_new_customers(cursor, month_start):
    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM customer WHERE Created_date >= %s",
        (month_start,)
    )
    return cursor.fetchone()['cnt']


def get_category_totals(cursor, month_start):
    cursor.execute(
        "SELECT p.Category, SUM(oi.Quantity) AS total "
        "FROM order_item oi JOIN c_order o ON oi.Order_ID = o.Order_ID "
        "JOIN product p ON oi.Product_ID = p.Product_ID "
        "WHERE o.Order_date >= %s GROUP BY p.Category",
        (month_start,)
    )
    totals = {}
    for row in cursor.fetchall():
        totals[row['Category']] = int(row['total'] or 0)
    return totals


def get_quantity_sold_per_product(cursor, month_start):
    cursor.execute(
        "SELECT p.Category, p.P_name, COALESCE(SUM(oi.Quantity), 0) AS sold "
        "FROM order_item oi JOIN c_order o ON oi.Order_ID = o.Order_ID "
        "JOIN product p ON oi.Product_ID = p.Product_ID "
        "WHERE o.Order_date >= %s GROUP BY p.Category, p.P_name",
        (month_start,)
    )
    sold = {}
    for row in cursor.fetchall():
        sold[(row['Category'], row['P_name'])] = int(row['sold'] or 0)
    return sold


def get_product_categories(cursor):
    cursor.execute("SELECT Category, P_name FROM product")
    return cursor.fetchall()


def build_category_charts(cursor, month_start):
    category_totals = get_category_totals(cursor, month_start)
    sold_per_product = get_quantity_sold_per_product(cursor, month_start)
    charts = {}
    for row in get_product_categories(cursor):
        category = row['Category']
        product_name = row['P_name']
        sold = sold_per_product.get((category, product_name), 0)
        category_total = category_totals.get(category, 0)
        percent = int(sold / category_total * 100) if category_total else 0
        charts.setdefault(category, []).append({
            'name': product_name,
            'sold': sold,
            'pct': percent,
        })
    return category_totals, charts


def build_pie_chart(category_totals):
    total_sold = sum(category_totals.values())
    pieces = []
    legend = []
    start = 0.0
    for index, category in enumerate(sorted(category_totals)):
        sold = category_totals[category]
        color = CHART_COLORS[index % len(CHART_COLORS)]
        percent = int(sold / total_sold * 100) if total_sold else 0
        end = start + (sold / total_sold * 100) if total_sold else 100
        pieces.append(f"{color} {int(start)}% {int(end)}%")
        legend.append({'category': category, 'percent': percent, 'color': color})
        start = end
    if pieces:
        gradient = ','.join(pieces)
    else:
        gradient = f"{CHART_COLORS[-1]} 0% 100%"
    return gradient, legend


def carrier_countries(carrier_id):
    countries = [
        country.title()
        for country, cid in REGION_CARRIERS.items()
        if cid == carrier_id
    ]
    return ' · '.join(sorted(countries))


def get_carriers(cursor):
    cursor.execute("SELECT Carrier_ID, Carrier_Name FROM carrier ORDER BY Carrier_ID")
    carriers = {}
    for row in cursor.fetchall():
        carriers[row['Carrier_ID']] = {
            'name': row['Carrier_Name'],
            'countries': carrier_countries(row['Carrier_ID']),
            'shipments': {},
        }
    return carriers


def get_shipment_rows(cursor):
    cursor.execute(
        "SELECT s.Shipment_ID, s.Carrier_ID, s.Shipment_status, s.Ship_date, "
        " s.Tracking_number, s.Shipping_cost, "
        " o.Order_ID, c.Fname, p.P_name, oi.Quantity, oi.Unit_price "
        "FROM shipment s "
        "JOIN c_order o ON o.Shipment_ID = s.Shipment_ID "
        "JOIN customer c ON o.Customer_ID = c.Customer_ID "
        "JOIN order_item oi ON oi.Order_ID = o.Order_ID "
        "JOIN product p ON p.Product_ID   = oi.Product_ID "
        "ORDER BY s.Carrier_ID, s.Shipment_ID, o.Order_ID"
    )
    return cursor.fetchall()


def new_shipment(row):
    return {
        'id': row['Shipment_ID'],
        'status': row['Shipment_status'],
        'date': row['Ship_date'],
        'tracking': row['Tracking_number'],
        'cost': float(row['Shipping_cost'] or 0),
        'orders': {},
    }


def new_shipment_order(row):
    return {
        'id': row['Order_ID'],
        'customer': row['Fname'],
        'items': [],
    }


def new_shipment_item(row):
    return {
        'name': row['P_name'],
        'qty': row['Quantity'],
        'price': float(row['Unit_price']),
    }


def build_carriers_data(cursor):
    carriers = get_carriers(cursor)
    for row in get_shipment_rows(cursor):
        carrier = carriers.get(row['Carrier_ID'])
        if carrier is None:
            continue
        shipment = carrier['shipments'].setdefault(row['Shipment_ID'], new_shipment(row))
        order = shipment['orders'].setdefault(row['Order_ID'], new_shipment_order(row))
        order['items'].append(new_shipment_item(row))
    for carrier in carriers.values():
        for shipment in carrier['shipments'].values():
            shipment['orders'] = list(shipment['orders'].values())
    return carriers


def get_shipment_status(cursor, shipment_id):
    cursor.execute(
        "SELECT Shipment_status FROM shipment WHERE Shipment_ID = %s",
        (shipment_id,)
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    return None


def set_shipment_status(cursor, shipment_id, new_status):
    cursor.execute(
        "UPDATE shipment SET Shipment_status = %s WHERE Shipment_ID = %s",
        (new_status, shipment_id)
    )
    cursor.execute(
        "UPDATE c_order SET Order_status = %s WHERE Shipment_ID = %s",
        (new_status, shipment_id)
    )


def validate_basket(cursor, basket):
    items = []
    for entry in basket:
        try:
            product_id = int(entry['id'])
            quantity = int(entry['quantity'])
        except (KeyError, TypeError, ValueError):
            return [], "Malformed basket item"
        if quantity <= 0:
            return [], "Quantity must be at least 1"
        cursor.execute(
            "SELECT Price, Stock_quantity FROM product WHERE Product_ID = %s",
            (product_id,)
        )
        row = cursor.fetchone()
        if not row:
            return [], f"Unknown product {product_id}"
        price, stock = row
        if stock < quantity:
            return [], f"Insufficient stock for product {product_id}"
        items.append({
            'product_id': product_id,
            'quantity': quantity,
            'price': price,
        })
    return items, None


def create_order(cursor, customer_id):
    cursor.execute(
        "INSERT INTO c_order (Customer_ID, Order_status) VALUES (%s, %s)",
        (customer_id, 'Pending')
    )
    return cursor.lastrowid


def add_order_items(cursor, order_id, items):
    for item in items:
        cursor.execute(
            "INSERT INTO order_item (Order_ID, Product_ID, Quantity, Unit_price) "
            "VALUES (%s, %s, %s, %s)",
            (order_id, item['product_id'], item['quantity'], item['price'])
        )
        cursor.execute(
            "UPDATE product SET Stock_quantity = Stock_quantity - %s WHERE Product_ID = %s",
            (item['quantity'], item['product_id'])
        )


def get_customer_country(cursor, customer_id):
    cursor.execute(
        "SELECT address FROM customer WHERE Customer_ID = %s",
        (customer_id,)
    )
    row = cursor.fetchone()
    if row and row[0]:
        return row[0].upper()
    return ""


def calculate_shipping_cost(cursor, country, order_id):
    cursor.execute("SELECT calc_shipping_cost(%s, %s)", (country, order_id))
    return cursor.fetchone()[0] or 0


def find_open_shipment(cursor, carrier_id):
    cursor.execute(
        "SELECT Shipment_ID FROM shipment "
        "WHERE Carrier_ID = %s AND Shipment_status = 'Preparing' "
        "LIMIT 1",
        (carrier_id,)
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    return None


def add_cost_to_shipment(cursor, shipment_id, shipping_cost):
    cursor.execute(
        "UPDATE shipment SET Shipping_cost = Shipping_cost + %s "
        "WHERE Shipment_ID = %s",
        (float(shipping_cost), shipment_id)
    )


def new_tracking_number():
    return os.urandom(6).hex().upper()


def create_shipment(cursor, carrier_id, shipping_cost):
    cursor.execute(
        "INSERT INTO shipment "
        "(Carrier_ID, Tracking_number, Ship_date, Shipment_status, Shipping_cost) "
        "VALUES (%s, %s, CURDATE(), 'Preparing', %s)",
        (carrier_id, new_tracking_number(), float(shipping_cost))
    )
    return cursor.lastrowid


def link_order_to_shipment(cursor, order_id, shipment_id):
    cursor.execute(
        "UPDATE c_order SET Shipment_ID = %s, Order_status = 'Preparing' WHERE Order_ID = %s",
        (shipment_id, order_id)
    )


def assign_order_to_shipment(cursor, order_id, country, shipping_cost):
    carrier_id = REGION_CARRIERS.get(country)
    if not carrier_id:
        return
    shipment_id = find_open_shipment(cursor, carrier_id)
    if shipment_id:
        add_cost_to_shipment(cursor, shipment_id, shipping_cost)
    else:
        shipment_id = create_shipment(cursor, carrier_id, shipping_cost)
    link_order_to_shipment(cursor, order_id, shipment_id)


def delete_customer(cursor, customer_id):
    cursor.execute(
        "SELECT Order_ID FROM c_order WHERE Customer_ID = %s",
        (customer_id,)
    )
    order_ids = [row[0] for row in cursor.fetchall()]
    for order_id in order_ids:
        cursor.execute("DELETE FROM order_item WHERE Order_ID = %s", (order_id,))
    cursor.execute(
        "UPDATE c_order SET Shipment_ID = NULL WHERE Customer_ID = %s",
        (customer_id,)
    )
    cursor.execute("DELETE FROM c_order WHERE Customer_ID = %s", (customer_id,))
    cursor.execute("DELETE FROM customer WHERE Customer_ID = %s", (customer_id,))

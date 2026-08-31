# Inventory & Order Management System

A web application for a small online store: it tracks products and stock, takes customer orders, calculates shipping cost from the customer's region and the weight of their basket, and groups orders into shipments handled by a carrier.

Built with Flask and MySQL. **No ORM** — every query is written by hand and executed as a parameterised statement.

Course project for DV1703 (Databasteknik), Blekinge Institute of Technology.

---

## Contents

- [What it does](#what-it-does)
- [Tech stack](#tech-stack)
- [Setup](#setup)
- [Database design](#database-design)
- [Key SQL](#key-sql)
- [Project structure](#project-structure)
- [Design notes](#design-notes)

---

## What it does

**For customers**

- Browse products by category with live stock levels; low stock is highlighted
- Add items to a basket that survives a page reload (kept in `localStorage`)
- See shipping cost calculated from their country and the total weight of the basket
- Place an order, with stock re-checked server-side inside a transaction
- View order history, split into ongoing and past orders

**For store managers**

- Restock panel listing every product at or below its own reorder level
- Shipments grouped by carrier and region, with status moved through Preparing → In-Transit → Delivered
- A short countdown after marking a shipment delivered, so a misclick can be undone
- Dashboard charts: total revenue from delivered orders, new customers this month, sales per category, and category share

**Shipping rates**

Each carrier serves a region and charges a base rate plus a rate per kilo:

| Region | Carrier | Base rate | Per kg |
|---|---|---|---|
| Scandinavia | Unville Croft | 75 kr | 18 kr |
| Americas | Hellsborn | 20 kr | 12 kr |
| Africa | Frieght Dorman | 39 kr | 5 kr |

These figures are invented, but sit in roughly the same range as real freight pricing.

---

## Tech stack

| Layer | Used |
|---|---|
| Backend | Python 3.8+, Flask |
| Database | MySQL 8.0+ (works on MariaDB) |
| DB driver | `mysql-connector-python` (no ORM) |
| Config | `python-dotenv` |
| Frontend | Jinja2 templates, vanilla JavaScript, CSS |

---

## Setup

### 1. Requirements

Python 3.8 or higher and MySQL 8.0 or higher.

```bash
git clone https://github.com/Pyo-Wol/LogisticMS.git
cd LogisticMS/python-mysql-workshop
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Create the database

```bash
cd logisticMS/database
mysql -u root -p < Create_Database_Tables.sql
mysql -u root -p < calc_shipping_cost.sql
```

The first script creates the database `Logistic_MS`, the six tables and the sample product and carrier data. The second creates the stored functions and the triggers.

### 3. Create a database user

Don't run the app as `root`. On Linux the `root` account usually authenticates through the `unix_socket` plugin, which rejects password logins from the application and produces `ERROR 1698`.

```sql
CREATE USER 'logistic_app'@'localhost' IDENTIFIED BY 'your_password';
CREATE USER 'logistic_app'@'127.0.0.1' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON Logistic_MS.* TO 'logistic_app'@'localhost';
GRANT ALL PRIVILEGES ON Logistic_MS.* TO 'logistic_app'@'127.0.0.1';
FLUSH PRIVILEGES;
```

### 4. Configure `.env`

Create `python-mysql-workshop/.env`:

```
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=logistic_app
DB_PASSWORD=your_password
DB_NAME=Logistic_MS
SECRET_KEY=any_long_random_string
```

> **On Linux, `DB_NAME` is case-sensitive.** The schema creates `Logistic_MS`, so `logistic_ms` will fail with `Unknown database`. This file is gitignored and must never be committed.

### 5. Run

```bash
cd logisticMS/python
python main.py
```

Open <http://localhost:5000>.

To try the admin dashboard, use the demo administrator login hardcoded in `main.py`: `admin@gmail.com` / `admin123`. Customer accounts are created through the sign-up page. Sign-up only accepts countries that a carrier serves — Sweden, Norway, Denmark, USA, Mexico, Canada, Nigeria, South Africa or Egypt.

---

## Database design

The E/R diagram is drawn in **Chen notation**: rectangles are entities, diamonds are relationships, ovals are attributes, and underlined attributes are primary keys.

![E/R diagram](python-mysql-workshop/logisticMS/database/er_diagram.drawio.png)

### Tables

| Table | Holds |
|---|---|
| `customer` | Name, email, address, created date, password. The address drives the shipping calculation. |
| `product` | Name, category, price, stock quantity, reorder level (default 5) and weight in kg. |
| `carrier` | Shipping company, contact info, base rate and rate per kg. |
| `c_order` | One customer order: status, date and a total amount maintained by triggers. |
| `order_item` | The line items of an order — which product, how many, and the price *at the time of purchase*, so an old order still shows what the customer actually paid. |
| `shipment` | Carrier, tracking number, ship date, status and shipping cost. One shipment groups several orders going to the same region. |

### Relationships

- **Customer places c_order** — one to many. `Customer_ID` is a foreign key in `c_order`.
- **C_order contains order_item** — one to many. `Order_ID` is a foreign key in `order_item`.
- **Order_item refers to product** — many to one. `order_item` implements the M:N relationship between orders and products, and carries its own attributes (`Quantity`, `Unit_price`).
- **Shipment groups c_order** — one to many. Implemented with a *single* foreign key: `c_order` holds a `Shipment_ID`. The shipment does not store order IDs in return, because storing the link on both sides would create a circular reference.
- **Carrier handles shipment** — one to many. `Carrier_ID` is a foreign key in `shipment`.

### Keys and constraints

| Table | Primary key | Foreign keys | Other constraints |
|---|---|---|---|
| `customer` | `Customer_ID` (AUTO_INCREMENT) | — | `Email` UNIQUE (candidate key, used to log in) |
| `product` | `Product_ID` (AUTO_INCREMENT) | — | `P_name` UNIQUE; CHECK on price, stock and weight |
| `carrier` | `Carrier_ID` (AUTO_INCREMENT) | — | CHECK on both rates |
| `shipment` | `Shipment_ID` (AUTO_INCREMENT) | `Carrier_ID` | `Tracking_number` UNIQUE |
| `c_order` | `Order_ID` (AUTO_INCREMENT) | `Customer_ID`, `Shipment_ID` | `Total_amount` maintained by triggers |
| `order_item` | `Order_ID`, `Product_ID` (composite) | `Order_ID`, `Product_ID` | CHECK `Quantity > 0`, `Unit_price >= 0` |

The composite key on `order_item` is what stops the same product being added twice to one order.

---

## Key SQL

### 1. Customer order history

Joins three tables to return every order for one customer along with its items.

```sql
SELECT o.Order_ID, o.Order_date, o.Order_status,
       p.P_name, oi.Quantity, oi.Unit_price
FROM c_order o
JOIN order_item oi ON o.Order_ID = oi.Order_ID
JOIN product p     ON oi.Product_ID = p.Product_ID
WHERE o.Customer_ID = %s
ORDER BY o.Order_date DESC;
```

The rows are grouped by order ID in Python so each order can be shown with its list of items.

### 2. Low stock products

Compares each product's stock against its **own** `Reorder_level`, so different products can have different restock points without touching the code.

```sql
SELECT Product_ID, P_name, Price, Stock_quantity
FROM product
WHERE Stock_quantity <= Reorder_level;
```

### 3. Total revenue from delivered orders

Aggregation over a join; `COALESCE` returns 0 rather than NULL when there are no orders.

```sql
SELECT COALESCE(SUM(oi.Quantity * oi.Unit_price), 0) AS total
FROM order_item oi
JOIN c_order o ON oi.Order_ID = o.Order_ID
WHERE o.Order_status IN ('Delivered');
```

### 4. Sales by category this month

```sql
SELECT p.Category, SUM(oi.Quantity) AS total
FROM order_item oi
JOIN c_order o ON oi.Order_ID = o.Order_ID
JOIN product p ON oi.Product_ID = p.Product_ID
WHERE o.Order_date >= %s
GROUP BY p.Category;
```

`%s` is the first day of the current month, e.g. `2026-08-01`.

### 5. Stored function — shipping cost

Finds the carrier for the customer's country, sums the weight of the order lines, and returns base rate + rate per kg × weight.

```sql
CREATE FUNCTION calc_shipping_cost(p_country VARCHAR(100), p_order_id INT)
RETURNS DECIMAL(10,2)
NOT DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_base_rate DECIMAL(10,2);
    DECLARE v_rate_per_kg DECIMAL(10,2);
    DECLARE v_total_weight DECIMAL(10,3);
    SET v_base_rate = get_base_rate(p_country);
    SET v_rate_per_kg = get_rate_per_kg(p_country);
    SELECT COALESCE(SUM(p.Weight_kg * oi.Quantity), 0) INTO v_total_weight
    FROM order_item oi
    JOIN product p ON oi.Product_ID = p.Product_ID
    WHERE oi.Order_ID = p_order_id;

    RETURN v_base_rate + (v_rate_per_kg * v_total_weight);
END$$
```

It is declared `NOT DETERMINISTIC READS SQL DATA` because it reads tables that change. Marking it `DETERMINISTIC` would let MySQL reuse stale results, and omitting `READS SQL DATA` makes the function fail to create when binary logging is enabled. Two helper functions, `get_base_rate` and `get_rate_per_kg`, look up the carrier for a country.

### 6. Triggers — keeping the order total correct

`c_order.Total_amount` is never written by the application. It is recalculated from the order lines by three triggers on `order_item`:

```sql
CREATE TRIGGER update_order_total_after_insert
AFTER INSERT ON order_item
FOR EACH ROW
BEGIN
    UPDATE c_order
    SET Total_amount = (SELECT COALESCE(SUM(Quantity * Unit_price), 0)
                        FROM order_item WHERE Order_ID = NEW.Order_ID)
    WHERE Order_ID = NEW.Order_ID;
END$$
```

`AFTER UPDATE` and `AFTER DELETE` versions do the same; the delete trigger reads `OLD.Order_ID`.

Storing the total is deliberate denormalisation — it trades a little write performance for faster reads.

### 7. Full shipment view — five-table join

The most complex query in the project. It returns every shipment, the orders inside it, and who ordered what, in a single database call.

```sql
SELECT s.Shipment_ID, s.Carrier_ID, s.Shipment_status, s.Ship_date,
       s.Tracking_number, s.Shipping_cost,
       o.Order_ID, c.Fname, p.P_name, oi.Quantity, oi.Unit_price
FROM shipment s
JOIN c_order o    ON o.Shipment_ID = s.Shipment_ID
JOIN customer c   ON o.Customer_ID = c.Customer_ID
JOIN order_item oi ON oi.Order_ID = o.Order_ID
JOIN product p    ON p.Product_ID = oi.Product_ID
ORDER BY s.Carrier_ID, s.Shipment_ID, o.Order_ID;
```

It returns one row per product per order, so the rows are regrouped in Python. That is still preferable to running one query per shipment.

---

## Project structure

```
python-mysql-workshop/
├── requirements.txt
├── .env                        (not in git)
└── logisticMS/
    ├── database/
    │   ├── Create_Database_Tables.sql   schema + sample data
    │   ├── calc_shipping_cost.sql       functions + triggers
    │   └── er_diagram.drawio.png
    └── python/
        ├── main.py             Flask routes
        ├── functions.py        queries and data shaping
        ├── database.py         connection helper
        ├── templates/          Jinja2 templates
        └── static/             CSS and images
```

`main.py` holds only the routes; every query and all the data shaping live in `functions.py`.

---

## Design notes

**Circular references.** Foreign keys originally pointed in both directions between `c_order` and `shipment`, which meant neither row could be inserted without the other. Keeping the link in one direction — the order pointing at the shipment — removed the problem entirely.

**AUTO_INCREMENT over generated IDs.** An earlier version generated random IDs in the application. That works until two people sign up in the same instant and collide. `AUTO_INCREMENT` makes it the database's problem.

**Concurrent purchases.** The purchase route re-checks stock server-side and runs the whole insert inside a transaction, so a failure rolls everything back. The CHECK constraint on `Stock_quantity` is the backstop: even if the application check loses a race, the database refuses to let stock go negative.

**SQL injection.** No ORM is used. Every query is written out and executed as a parameterised statement, so user input is never concatenated into SQL.

**Table name casing.** All tables are created in lowercase. MySQL table names are case-sensitive on Linux, so mixed-case names in the schema with lowercase names in queries will break as soon as the project leaves Windows.

---

## Author

Bate Macjohn Bate Manjoh — DV1703 Databasteknik, BTH.

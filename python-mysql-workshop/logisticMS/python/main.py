import os
import costumer_id
from datetime import date
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, session, url_for
from database import get_db_connection
import re

app = Flask(__name__)
load_dotenv()
app.secret_key = os.getenv("SECRET_KEY", "change-this-in-production")


@app.route('/')
def start():
    return render_template('loginOptions.html')

@app.route('/admin-login', methods=['GET', 'POST'])
def adminlogin():
    msg = ""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if email == "admin@gmail.com" and password == "admin123":
            session['loggedinAdmin'] = True
            session['id'] = 0
            session['name'] = "Admin"
            return redirect("/admin-page")
        msg = "Incorrect admin credentials"
    return render_template("adminloginpage.html", msg=msg)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('loggedin'):
        return redirect('/main')
    msg = ""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM customer WHERE email=%s AND loginPassword=%s", (email, password))
        account = cursor.fetchone()
        cursor.close()
        conn.close()
        if account:
            session['loggedin'] = True
            session['id'] = account['Customer_ID']
            session['name'] = account['Fname']
            return redirect("/loading?mode=loading&next=/main")
        msg = "Incorrect email or password"
    return render_template('login.html', msg=msg)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    msg = ''
    if request.method == 'POST':
        name = request.form['fName'] + " " + request.form['lName']
        email = request.form['email']
        password = request.form['password']
        address = request.form['address']
        today_date = date.today().strftime("%Y-%m-%d")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT 1 FROM customer WHERE email = %s", (email,))
        if cursor.fetchone():
            msg = "Account already exists"
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            msg = "Invalid email format"
        elif not name or not password:
            msg = "Please fill all fields"
        else:
            customer_id = costumer_id.generate_unique_customer_id()
            cursor.execute(
                "INSERT INTO customer (Customer_ID, Fname, Email, Created_date, loginPassword, address) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (customer_id, name, email, today_date, password, address)
            )
            conn.commit()
            msg = "Account created successfully"
        cursor.close()
        conn.close()
    return render_template('signup.html', msg=msg)


@app.route('/main')
def main():
    if not session.get('loggedin'):
        return redirect('/login')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT Product_ID, P_name, Price, Stock_quantity FROM product")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    stocks = {}
    prices = {}
    for row in result:
        stocks[row["P_name"]] = row["Stock_quantity"]
        prices[row["P_name"]] = row["Price"]
    return render_template('index.html', data=result, stocks=stocks, prices=prices, name=session['name'])

@app.route('/user-page', methods=['GET', 'POST'])
def user():
    if not session.get('loggedin'):
        return redirect('/login')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT o.Order_ID, o.Order_date, o.Order_status, "
        "p.P_name, oi.Quantity, oi.Unit_price "
        "FROM c_order o "
        "JOIN order_item oi ON o.Order_ID = oi.Order_ID "
        "JOIN product p ON oi.Product_ID = p.Product_ID "
        "WHERE o.Customer_ID = %s "
        "ORDER BY o.Order_date DESC",
        (session['id'],)
    )
    orders = {}
    for r in cursor.fetchall():
        oid = r['Order_ID']
        if oid not in orders:
            orders[oid] = {
                'id': oid,
                'date': r['Order_date'],
                'status': r['Order_status'],
                'order_items': [],
                'total': 0,
            }
        orders[oid]['order_items'].append({'name': r['P_name'], 'qty': r['Quantity'], 'price': r['Unit_price']})
        orders[oid]['total'] += r['Quantity'] * r['Unit_price']
    all_orders = list(orders.values())
    ongoing_orders = []
    past_orders = []
    for o in all_orders:
        if o['status'] in ('Delivered', 'Completed'):
            past_orders.append(o)
        else:
            ongoing_orders.append(o)
    cursor.execute("SELECT Product_ID, Stock_quantity, Weight_kg FROM product")
    products = cursor.fetchall()
    stock_data = {}
    weight_data = {}
    for r in products:
        pid = str(r['Product_ID'])
        stock_data[pid] = r['Stock_quantity']
        weight_data[pid] = float(r['Weight_kg'] or 0)
    cursor.execute(
        "SELECT "
        "  get_base_rate((SELECT address FROM customer WHERE Customer_ID = %s))   AS base_rate, "
        "  get_rate_per_kg((SELECT address FROM customer WHERE Customer_ID = %s)) AS rate_per_kg",
        (session['id'], session['id'])
    )
    row = cursor.fetchone()
    carrier = {
        'base_rate': float(row['base_rate'] or 0),
        'rate_per_kg': float(row['rate_per_kg'] or 0),
    }
    cursor.close()
    conn.close()
    return render_template('user.html', ongoing_orders=ongoing_orders, past_orders=past_orders,
        stocks=stock_data, weights=weight_data, carrier=carrier)


@app.route('/admin-page', methods=['GET', 'POST'])
def admin():
    if not session.get('loggedinAdmin'):
        return redirect('/admin-login')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        quantity = request.form.get('quantity', 1, type=int)
        if product_id and quantity > 0:
            cursor.execute(
                "UPDATE product SET Stock_quantity = Stock_quantity + %s WHERE Product_ID = %s",
                (quantity, product_id)
            )
            conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('admin'))
    month_start = date.today().strftime("%Y-%m") + "-01"
    try:
        cursor.execute("SELECT Product_ID, P_name, Price, Stock_quantity FROM product WHERE Stock_quantity <= 5")
        low_stock_products = cursor.fetchall()
        cursor.execute(
            "SELECT COALESCE(SUM(oi.Quantity * oi.Unit_price), 0) AS total "
            "FROM order_item oi JOIN c_order o ON oi.Order_ID = o.Order_ID "
            "WHERE o.Order_status IN ('Delivered', 'Completed')"
        )
        total_profit = cursor.fetchone()['total']
        cursor.execute(
            "SELECT COALESCE(SUM(oi.Unit_price * oi.Quantity), 0) AS total "
            "FROM order_item oi JOIN c_order o ON oi.Order_ID = o.Order_ID "
            "WHERE o.Order_status IN ('Delivered', 'Completed') AND o.Order_date >= %s",
            (month_start,)
        )
        total_revenue = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) AS cnt FROM customer WHERE Created_date >= %s", (month_start,))
        new_customers = cursor.fetchone()['cnt']
        
        cursor.execute(
            "SELECT p.Category, SUM(oi.Quantity) AS total "
            "FROM order_item oi JOIN c_order o ON oi.Order_ID = o.Order_ID "
            "JOIN product p ON oi.Product_ID = p.Product_ID "
            "WHERE o.Order_date >= %s GROUP BY p.Category",
            (month_start,)
        )
        product_totals = {}
        for r in cursor.fetchall():
            product_totals[r['Category']] = int(r['total'] or 0)
        cursor.execute(
            "SELECT p.Category, p.P_name, COALESCE(SUM(oi.Quantity), 0) AS sold "
            "FROM order_item oi JOIN c_order o ON oi.Order_ID = o.Order_ID "
            "JOIN product p ON oi.Product_ID = p.Product_ID "
            "WHERE o.Order_date >= %s GROUP BY p.Category, p.P_name",
            (month_start,)
        )
        sold_this_month = {}
        for r in cursor.fetchall():
            sold_this_month[(r['Category'], r['P_name'])] = int(r['sold'] or 0)
        cursor.execute("SELECT Category, P_name FROM product")
        category_charts = {}
        for r in cursor.fetchall():
            cat, name = r['Category'], r['P_name']
            sold = sold_this_month.get((cat, name), 0)
            cat_total = product_totals.get(cat, 0)
            pct = int(sold / cat_total * 100) if cat_total else 0
            category_charts.setdefault(cat, []).append({'name': name, 'sold': sold, 'pct': pct})

        colors = ['#ff6384', '#36a2eb', '#ffce56', '#4bc0c0', '#ff9f40', '#c9cbcf']
        total_sold = sum(product_totals.values()) or 0
        pie_pieces = []
        pie_legend = []
        start = 0.0
        for i, cat in enumerate(sorted(product_totals)):
            sold = product_totals[cat]
            pct = int(sold / total_sold * 100) if total_sold else 0
            end = start + (sold / total_sold * 100) if total_sold else 100
            color = colors[i % len(colors)]
            pie_pieces.append(color + " " + str(int(start)) + "% " + str(int(end)) + "%")
            pie_legend.append({'category': cat, 'percent': pct, 'color': color})
            start = end
        if pie_pieces:
            pie_gradient = ','.join(pie_pieces)
        else:
            pie_gradient = colors[-1] + " 0% 100%"
        carriers_data = {
            2: {'name': 'Unville Croft', 'countries': 'Sweden · Norway · Denmark', 'shipments': {}},
            672: {'name': 'Hellsborn', 'countries': 'USA · Mexico · Canada', 'shipments': {}},
            101: {'name': 'Frieght Dorman','countries': 'Nigeria · South Africa · Egypt', 'shipments': {}},
        }
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
        for r in cursor.fetchall():
            cid = r['Carrier_ID']
            sid = r['Shipment_ID']
            if cid not in carriers_data:
                continue
            shipments = carriers_data[cid]['shipments']
            if sid not in shipments:
                shipments[sid] = {
                    'id': sid,
                    'status': r['Shipment_status'],
                    'date': r['Ship_date'],
                    'tracking': r['Tracking_number'],
                    'cost': float(r['Shipping_cost'] or 0),
                    'orders': {},
                }
            orders_map = shipments[sid]['orders']
            oid = r['Order_ID']
            if oid not in orders_map:
                orders_map[oid] = {'id': oid, 'customer': r['Fname'], 'items': []}
            orders_map[oid]['items'].append({
                'name': r['P_name'],
                'qty': r['Quantity'],
                'price': float(r['Unit_price']),
            })
        for cid in carriers_data:
            for sid in carriers_data[cid]['shipments']:
                s = carriers_data[cid]['shipments'][sid]
                s['orders'] = list(s['orders'].values())

    except Exception as e:
        cursor.close()
        conn.close()
        return "Admin page DB error: " + str(e), 500

    cursor.close()
    conn.close()

    return render_template(
        'admin.html',
        name=session.get('name', 'Admin'),
        stock_level=low_stock_products,
        total_profit=total_profit,
        total_revenue=total_revenue,
        new_customers=new_customers,
        product_totals=product_totals,
        category_charts=category_charts,
        pie_gradient=pie_gradient,
        pie_legend=pie_legend,
        carriers_data=carriers_data,
    )


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/admin/shipment-status', methods=['POST'])
def update_shipment_status():
    if not session.get('loggedinAdmin'):
        return {"message": "Unauthorized"}, 401
    shipment_id = request.form.get('shipment_id')
    new_status = request.form.get('status')
    if new_status not in ('Preparing', 'In-Transit', 'Delivered'):
        return {"message": "Invalid status"}, 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE shipment SET Shipment_status = %s WHERE Shipment_ID = %s",
        (new_status, shipment_id)
    )
    if new_status == 'Delivered':
        cursor.execute(
            "UPDATE c_order SET Order_status = 'Delivered' "
            "WHERE Shipment_ID = %s",
            (shipment_id,)
        )
    if new_status == 'In-Transit':
        cursor.execute(
            "UPDATE c_order SET Order_status = 'In-Transit' "
            "WHERE Shipment_ID = %s AND Order_status = 'Delivered'",
            (shipment_id,)
        )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('admin'))


@app.route('/loading')
def loading():
    mode = request.args.get("mode", "loading")
    next_page = request.args.get("next", "/")
    return render_template("loading.html", mode=mode, next_page=next_page)


@app.route('/purchase', methods=['POST'])
def purchase():
    if not session.get('loggedin'):
        return {"message": "Not logged in"}, 401

    body = request.get_json()
    if not body:
        return {"message": "Empty request"}, 400

    basket = body.get('items', [])
    if not basket:
        return {"message": "Empty basket"}, 400

    try:
        order_id = costumer_id.generate_unique_order_id()
    except Exception as e:
        return {"message": "Failed to generate order ID: " + str(e)}, 500

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for item in basket:
            cursor.execute("SELECT Stock_quantity FROM product WHERE Product_ID = %s", (item['id'],))
            stock = cursor.fetchone()
            if not stock or stock[0] < item['quantity']:
                return {"message": "Insufficient stock for product " + str(item['id'])}, 400

        cursor.execute("INSERT INTO c_order (Customer_ID, Order_ID, Order_status) VALUES (%s, %s, %s)", (session['id'], order_id, 'Pending'))
        for item in basket:
            order_item_id = costumer_id.generate_unique_order_item_id()
            cursor.execute(
                "INSERT INTO order_item (Order_item_id, Order_ID, Product_ID, Quantity, Unit_price) VALUES (%s, %s, %s, %s, %s)",
                (order_item_id, order_id, item['id'], item['quantity'], item['price'])
            )
            cursor.execute(
                "UPDATE product SET Stock_quantity = Stock_quantity - %s WHERE Product_ID = %s",
                (item['quantity'], item['id'])
            )


        cursor.execute("SELECT address FROM customer WHERE Customer_ID = %s", (session['id'],))
        row = cursor.fetchone()
        country = row[0].upper() if row else ""
        cursor.execute("SELECT calc_shipping_cost(%s, %s)", (country, order_id))
        shipping_cost = cursor.fetchone()[0] or 0

        REGION_CARRIERS = {
            "SWEDEN": 2, "NORWAY": 2, "DENMARK": 2,
            "USA": 672, "MEXICO": 672, "CANADA": 672,
            "NIGERIA": 101, "SOUTH AFRICA": 101, "EGYPT": 101,
        }
        carrier_id = REGION_CARRIERS.get(country)

        if carrier_id:
            cursor.execute(
                "SELECT Shipment_ID FROM shipment "
                "WHERE Carrier_ID = %s AND Shipment_status = 'Preparing' "
                "LIMIT 1",
                (carrier_id,)
            )
            existing = cursor.fetchone()

            if existing:
                shipment_id = existing[0]
            else:
                shipment_id = costumer_id.generate_unique_shipment_id()
                tracking_number = costumer_id.generate_unique_shipment_id()
                cursor.execute(
                    "INSERT INTO shipment "
                    "(Shipment_ID, Order_ID, Carrier_ID, Tracking_number, "
                    " Ship_date, Shipment_status, Shipping_cost) "
                    "VALUES (%s, %s, %s, %s, CURDATE(), 'Preparing', %s)",
                    (shipment_id, order_id, carrier_id, tracking_number, float(shipping_cost))
                )
            cursor.execute(
                "UPDATE c_order SET Shipment_ID = %s, Order_status = 'Preparing' WHERE Order_ID = %s",
                (shipment_id, order_id)
            )
        conn.commit()
        return {"message": "Purchase successful", "shipping_cost": float(shipping_cost)}
    except Exception as e:
        conn.rollback()
        return {"message": "Database error: " + str(e)}, 500
    finally:
        cursor.close()
        conn.close()


@app.route('/delete-account', methods=['POST', 'GET'])
def delete_account():
    if not session.get('loggedin'):
        return redirect('/login')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM order_item WHERE Order_ID IN (SELECT Order_ID FROM c_order WHERE Customer_ID = %s)", (session['id'],))
        cursor.execute("UPDATE c_order SET Shipment_ID = NULL WHERE Customer_ID = %s", (session['id'],))
        cursor.execute("DELETE FROM shipment WHERE Order_ID IN (SELECT Order_ID FROM c_order WHERE Customer_ID = %s)", (session['id'],))
        cursor.execute("DELETE FROM c_order WHERE Customer_ID = %s", (session['id'],))
        cursor.execute("DELETE FROM customer WHERE Customer_ID = %s", (session['id'],))
        conn.commit()
        session.clear()
        return redirect('/')
    except Exception as error:
        conn.rollback()
        return {"message": "Database error: " + str(error)}, 500
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    app.run(debug=True)

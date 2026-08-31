import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, session, url_for
from database import get_db_connection
import mysql.connector
import functions

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
        if functions.admin_login_is_valid(email, password):
            session.clear()
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
        try:
            account = functions.find_customer(cursor, email, password)
        finally:
            cursor.close()
            conn.close()
        if account:
            session.clear()
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
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            msg = functions.signup_error(cursor, name, email, password, address)
            if not msg:
                try:
                    functions.create_customer(cursor, name, email, password, address)
                    conn.commit()
                    msg = "Account created successfully"
                except mysql.connector.IntegrityError:
                    conn.rollback()
                    msg = "Account already exists"
        finally:
            cursor.close()
            conn.close()
    return render_template('signup.html', msg=msg)


@app.route('/main')
def main():
    if not session.get('loggedin'):
        return redirect('/login')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        products = functions.get_products(cursor)
    finally:
        cursor.close()
        conn.close()
    return render_template('index.html',
                        data=products,
                        stocks=functions.stock_by_name(products),
                        prices=functions.price_by_name(products),
                        categories=functions.group_by_category(products),
                        name=session['name'])


@app.route('/user-page', methods=['GET', 'POST'])
def user():
    if not session.get('loggedin'):
        return redirect('/login')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        order_rows = functions.get_customer_order_rows(cursor, session['id'])
        orders = functions.group_customer_orders(order_rows)
        ongoing_orders, past_orders = functions.split_orders_by_status(orders)
        stocks, weights = functions.get_stock_and_weight_lookups(cursor)
        carrier = functions.get_carrier_rates(cursor, session['id'])
    finally:
        cursor.close()
        conn.close()
    return render_template('user.html',
        ongoing_orders=ongoing_orders,
        past_orders=past_orders,
        stocks=stocks,
        weights=weights,
        carrier=carrier)


@app.route('/admin-page', methods=['GET', 'POST'])
def admin():
    if not session.get('loggedinAdmin'):
        return redirect('/admin-login')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == 'POST':
            product_id = request.form.get('product_id')
            quantity = request.form.get('quantity', 1, type=int)
            if product_id and quantity > 0:
                functions.restock_product(cursor, product_id, quantity)
                conn.commit()
            return redirect(url_for('admin'))

        month_start = functions.current_month_start()
        low_stock_products = functions.get_low_stock_products(cursor)
        total_profit = functions.get_delivered_revenue(cursor)
        total_revenue = functions.get_delivered_revenue_since(cursor, month_start)
        new_customers = functions.count_new_customers(cursor, month_start)
        product_totals, category_charts = functions.build_category_charts(cursor, month_start)
        pie_gradient, pie_legend = functions.build_pie_chart(product_totals)
        carriers_data = functions.build_carriers_data(cursor)
    except Exception as e:
        return "Admin page DB error: " + str(e), 500
    finally:
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
    if new_status not in functions.SHIPMENT_STATUSES:
        return {"message": "Invalid status"}, 400
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if functions.get_shipment_status(cursor, shipment_id) == 'Delivered':
            return redirect(url_for('admin'))
        functions.set_shipment_status(cursor, shipment_id, new_status)
        conn.commit()
    finally:
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

    body = request.get_json(silent=True)
    if not body:
        return {"message": "Empty request"}, 400

    basket = body.get('items', [])
    if not basket:
        return {"message": "Empty basket"}, 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        items, error = functions.validate_basket(cursor, basket)
        if error:
            return {"message": error}, 400

        order_id = functions.create_order(cursor, session['id'])
        functions.add_order_items(cursor, order_id, items)

        country = functions.get_customer_country(cursor, session['id'])
        shipping_cost = functions.calculate_shipping_cost(cursor, country, order_id)
        functions.assign_order_to_shipment(cursor, order_id, country, shipping_cost)

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
        functions.delete_customer(cursor, session['id'])
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

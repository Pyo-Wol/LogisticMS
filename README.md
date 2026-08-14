##Final Project Report (solo project) 
#By: Bate Macjohn Bate Manjoh - bamn25@student.bth.se  
#Course: DV 1703 (Databasteknik) 
#Submitted: 2026-05-14 
###Inventory & Order Management System 
#Introduction 
To be honest,  I didn't know anything about logistics or inventory systems before this project. 
Like at all. While searching for project ideas, I came across a short video that explained how 
logistics and inventory systems work. The topic was new to me, but the video made the 
concepts surprisingly accessible and interesting. That inspired me to explore the subject 
further by building a simplified system of my own for this course. The whole idea is pretty 
simple when you break it down. A store has products. People buy them. Someone needs to 
keep track of what's left in stock so you don't sell products you don't have. And when 
someone buys something, you have to ship it to them, which means figuring out which 
shipping company to use and how much to charge. Doing all that manually, would lead to 
catastrophe. So I thought okay, let's build a system that does this automatically. Nothing too 
crazy, just something that works. 
#So who is this for? 
I needed a project that showed I could design a database and actually use it in a real 
application. But if I had to name actual users, there are two types: 
Customers: they just want to see products, add products to a cart and buy it. They also 
want to check where their order is after they’ve bought it. Is it still being packed? Is it on the 
way? Did it get delivered? 
Store managers/ admin:  these are the people running things behind the scenes. They 
need to see when products are running low so they can order more. They want to update 
shipment statuses. They probably want to see some numbers, like  how much money came 
in and what's selling well. 
#What does it actually do? 
It shows products with prices and stock levels. If something's low, it's marked in red. 
Customers can add products to a basket. I used localStorage so the basket stays even if you 
close the browser and come back later. When someone checks out, the system checks if 
everything's actually in stock, then subtracts those quantities so nobody else buys the same 
item.  
It calculates shipping costs based on the customer's country and how heavy their items are. 
Different carriers have different rates. For Scandinavia it's 75 kr + 18 kr per kg, for 
Americans it's 20 kr + 12 kr per kg and  for Africa it's 39 kr + 5 kr per kg. I just made those 
numbers up but they seem reasonable. Orders get grouped into shipments and assigned to 
the right carrier automatically. 
For the manager, there is an admin dashboard that shows: Products with stock at 5 or less , 
so they know what needs restocking. A form to add more stock Buttons to update shipment 
status like “ Preparing”, “In-Transit”, “Delivered”. I added this little countdown thing when you 
mark something as delivered, giving you a few seconds to undo it if you clicked by accident( 
that happened to me). Some simple charts like  total profit, new customers this month, sales 
by category and a pie chart for most-viewed categories. 
Customers can log in and see their order history,  both ongoing orders and past ones. 
Where does the data come from? 
I just made up some sample products. Wireless headphones, smart watch, Bluetooth 
speaker, USB hub, t-shirts, jeans, hoodie, a few books. I gave them prices and weights and 
stock quantities. Three carriers with different rates based on regions. Then as people sign up 
and place orders, all of that gets saved. So it's a mix of fake data to start with and then real 
data once someone actually uses it. 
Logical model 
This is how I created the database. I created six tables and here’s what's in each one: 
Customers: Just the basics name, email, address (I mostly need the country for shipping), 
when they joined and a password. I thought about adding phone number but never actually 
used it anywhere so I left it out. 
Products: Each product has an ID, name, category (Electronics, Clothing, Books), price, 
how many are in stock, a reorder level (I set it to 5 by default) and weight in kilograms. The 
reorder level is just a threshold,  when stock drops to 5 or below, it shows up on the admin 
dashboard so the manager knows to order more. And weight matters for shipping costs. 
Carriers: These are the shipping companies. They have an ID, name, contact info, a base 
rate and a rate per kilogram. Both rates are stored as DECIMAL so they handle decimal 
values properly. Base rate is a flat fee you always pay. Rate per kg is exactly what it sounds 
like. For Scandinavia it's 75 + 18 per kg, Americas is 20 + 12 and Africa is 39 + 5.  
C_Orders(Customer orders):  When someone buys a product, it creates an order. The 
primary key is just Order_ID. That's the only identifier. Customer_ID and Shipment_ID are 
foreign keys, they point to other tables, they're not identifiers for the order itself. And 
Total_amount is calculated from the items so it can't be a primary key either, it changes 
every time you add something. The order also has a status and a date.  
Order Items: This connects orders to products. One order can have lots of items and each 
item remembers which product, the quantity and what the price was at that moment. This 
way if the price changes later, the order still shows what the customer actually paid. The 
primary key here is a composite of (Order_ID, Product_ID). That pair is unique on its own so 
there's no need for a separate surrogate ID. It also stops the same product from being added 
twice to the same order.  
Shipments:  This is where delivery info lives. Each shipment has an ID, which carrier is 
handling it, a tracking number, a ship date, a status and the shipping cost which gets 
calculated using a stored function. Status can be Preparing, In-Transit or Delivered. One 
shipment can group multiple orders going to the same region, so the link goes from the order 
side: each order holds a Shipment_ID pointing to which shipment it belongs to.  
How do they connect? 
A customer can have lots of orders. One customer, many orders. An order can have lots of 
order items. One order, many items. Each order item links one product to one order, and a 
product can show up in many different orders. Each order belongs to one shipment, and one 
shipment groups many orders from the same region. Each shipment is handled by one 
carrier, and one carrier handles many shipments. 
I know that's not how you're supposed to do it. But here's why I did it that way. 
When I first built this, I wanted to be able to look at an order and immediately see its 
shipment and look at a shipment and immediately see its order. Having the link in both 
directions made that really easy. The downside is that when a new order comes in, I have to 
do an extra step. First I create the order. Then I create the shipment using that order ID. 
Then I go back and update the order table(c_order table) with the new shipment ID. It works, 
it's just not elegant. I thought about fixing it later but once it was working I didn't want to risk 
breaking things. If I was starting over, I'd probably just put the shipment ID in the order and 
call it a day. But for now, it's fine. Each shipment is handled by one carrier and a carrier can 
handle lots of shipments. So that's one carrier to many shipments. 
Why did I do it this way?  
Because it made sense to me at the time and I just kept going.The weight in products was 
for shipping cost. The reorder level is  just a simple way to flag low stock for the admin. The 
separate order items table seemed like the right way to keep a record of what was bought 
and for how much, especially if prices change. You can look at an order and see its shipment 
info or you can look at a shipment and see what order it's for. The whole database is just 
meant to store stuff and keep it connected. Nothing fancy, just functional. Is it the best 
design? Probably not. But it works and I learned a lot building it. 
Relationships 
The relationship between the entities became foreign keys in the table. Each relation was 
implemented like this: 
Customer places Orders(c_order): This is a one to many relationship because one 
customer can have many orders. I added customer_ID as a foreign key in the c_order table. 
This means each order points back to the customer who made it. 
Order(c_order) contains Order items: Another one to many relationships. This is because 
one order can have multiple order items. I put order_ID as a foreign key in the order_item 
table so each order item belongs to one order 
Order item refers to the Product. A many to one relationship, meaning  many order items can 
reference the same product. I used Product_ID as a foreign key in the order_item. And each 
order item points to one product. 
C_Order linked to Shipment = one shipment can group many orders from the same carrier 
region. So it's a one-to-many from Shipment to C_Order. I implemented it with a single 
foreign key: C_Order has a Shipment_ID that points to the Shipment table. Just one 
direction. The shipment doesn't need to store the order ID because you can always query it 
the other way.  
The shipment is handled by the Carrier=  this a one to many relationship because one 
carrier can handle many shipments and i added carrier_ID as a foreign key in the shipment 
table. Each shipment points to the carrier that delivers it. 
The Diagram:
SQL Queries 
Getting the customer's order history 
When a user logs in and goes to their profile they would want to see what they have bought 
before and what is still on the way. This query pulls everything. I'm talking about the orders, 
items, products names, prices and sticks them all together. 
Query: 
SELECT o.Order_ID, o.Order_date, o.Order_status, p.P_name, oi.Quantity, oi.Unit_price 
FROM c_order o 
JOIN order_item oi ON o.Order_ID = oi.Order_ID 
JOIN product p ON oi.Product_ID = p.Product_ID 
WHERE o.Customer_ID = %s 
ORDER BY o.Order_date DESC; 
This one joins c_order, order_item and product table. Used the WHERE clause to pick 
orders for a certain customer. Then I looped through the results in python and grouped them 
by order ID. That way I can show each order with its list of items. 
Finding low stock products 
For the admin dashboard, I needed a quick way to show which products are running low in 
stocks. I set a threshold of 5 units and if the stock is 5 or less, it shows up in the "Need 
Restock" section. 
Query: 
SELECT Product_ID, P_name, Price, Stock_quantity 
FROM product 
WHERE Stock_quantity <= 5; 
Nothing much here, just a simple filter. It's only one table but its essential for the admin to 
know what needs reordering. 
Total profit from completed orders 
The admin dashboard also shows total profit. That's all of the money from orders. I used 
COALESCE to make sure that I get 0 instead of null if there are no orders yet. 
Query: 
SELECT COALESCE(SUM(oi.Quantity * oi.Unit_price), 0) AS total 
FROM order_item oi 
JOIN c_order o ON oi.Order_ID = o.Order_ID 
WHERE o.Order_status IN ('Delivered'); 
This one uses a JOIN between order_item and c_order to only count items from the orders 
that are delivered or completed and SUM does the aggregation by adding up all of those line 
totals. 
Sales by category for current month 
The bar charts on the admin page need to show how many items sold in each category this 
month. So I grab all orders from the first day of the month onwards and then group them by 
category and count the total quantity sold. 
Query: 
 
SELECT p.Category, SUM(oi.Quantity) AS total 
FROM order_item oi 
JOIN c_order o ON oi.Order_ID = o.Order_ID 
JOIN product p ON oi.Product_ID = p.Product_ID 
WHERE o.Order_date >= %s 
GROUP BY p.Category; 
 
The “%s” gets replaced with something like "2025-03-01". This query has two joins and uses 
GROUP BY with sum. 
 
Using a stored function to calculate shipping cost 
One of the requirements was to use a function or trigger. I created a MySQL function that 
calculates the total shipping cost for an order based on the customer's country and the total 
weight of the items. This function calls two helper functions that look up the carrier's rates. 
 
Query: 
SELECT calc_shipping_cost( 
    (SELECT address FROM customer WHERE Customer_ID = %s), 
    %s 
) AS shipping_cost; 
The function is defined as: 
sql 
CREATE FUNCTION calc_shipping_cost(p_country VARCHAR(100), p_order_id INT) 
RETURNS DECIMAL(10,2) 
DETERMINISTIC 
BEGIN 
    DECLARE v_base_rate DECIMAL(10,2); 
    DECLARE v_rate_per_kg DECIMAL(10,2); 
    DECLARE v_total_weight DECIMAL(10,2); 
     
    SET v_base_rate = get_base_rate(p_country); 
    SET v_rate_per_kg = get_rate_per_kg(p_country); 
     
    SELECT SUM(p.Weight_kg * oi.Quantity) INTO v_total_weight 
    FROM order_item oi 
    JOIN product p ON oi.Product_ID = p.Product_ID 
    WHERE oi.Order_ID = p_order_id; 
     
    RETURN v_base_rate + (v_rate_per_kg * v_total_weight); 
END; 
 
This function uses the two functions get_base_rate and get_rate_per_kg, which map the 
country to a carrier and get the right rates from the carrier table. 
 
Trigger to automatically update order total 
I also created a trigger that runs after each insert on the order_item table. It recalculates the 
total amount for the order and updates the c_order table. This ensures the total is always 
correct without needing manual updates. 
 
 
Query: 
CREATE TRIGGER update_order_total_after_insert 
AFTER INSERT ON order_item 
FOR EACH ROW 
BEGIN 
    DECLARE new_total DECIMAL(10,2); 
     
    SELECT SUM(Quantity * Unit_price) INTO new_total 
    FROM order_item 
    WHERE Order_ID = NEW.Order_ID; 
     
    UPDATE c_order 
    SET Total_amount = new_total 
    WHERE Order_ID = NEW.Order_ID; 
END; 
 
All shipment details for the admin panel 
This right here took me almost 2 days to figure out how to make this work. I'll say it's 
probably the most difficult thing I have in my python main.py. When the admin looks at the 
carrier sections, they need to see every shipment, what orders are in it, who the customer is 
and what product they have bought (I'll probably remove what the customer has bought to 
make it less detailed). That means joining five tables: shipment, c_order, customer, 
order_item and product. 
 
Query: 
SELECT s.Shipment_ID, s.Carrier_ID, s.Shipment_status, s.Ship_date, 
       s.Tracking_number, s.Shipping_cost, 
       o.Order_ID, c.Fname, p.P_name, oi.Quantity, oi.Unit_price 
FROM shipment s 
JOIN c_order o ON o.Shipment_ID = s.Shipment_ID 
JOIN customer c ON o.Customer_ID = c.Customer_ID 
JOIN order_item oi ON o.Order_ID = oi.Order_ID 
JOIN product p ON p.Product_ID = oi.Product_ID 
ORDER BY s.Carrier_ID, s.Shipment_ID, o.Order_ID; 
 
This query returns one row per product in each order which means I have to do some 
grouping in python to rebuild the structure. But it gives me everything I need in one go. It's 
the best example that shows the use of multiple JOINS. 
 
Discussion and Resources 
 
One thing I had to fix was the order-shipment relationship. I originally had foreign keys 
pointing in both directions, which created a circular reference. It worked but it was messy 
and honestly just wrong. The clean way is to keep it one direction: the order holds the 
Shipment_ID, done. I also added AUTO_INCREMENT to all primary keys which got rid of 
the random ID generator I had before. That thing worked but it was fragile. If two people 
signed up at the exact same moment it could theoretically generate the same ID. 
AUTO_INCREMENT handles all of that at the database level so I don't have to think about it.  
Another challenge was the complex query for the admin panel. Joining five tables gave me a 
lot of duplicate rows because each product in an order appears separately. And i had to do 
some extra work in python to group them properly. But the query it self is efficient in my 
opinion for it gives me all the data in one database call. 
I also had to think of about conditions for when multiple people try to buy the last item at the 
same time. In the purchase route, i check stock levels before inserting anything and i use 
transactions so that if something fails everything rolls back. That way i dont ended up with 
orders that can’t be fulfilled. 
Installation 
To run it you need: 
1. Python 3.8 or higher 
2. Mysql 8.0 or higher 
3. Python packages listed in the requirement.txt : flask, mysql-connector-python, 
python-dotenv…etc. 
Set up: 
1. Clone repo from github 
2. Create a .env with database credentials and a secret key 
3. Run the Create_Database_Tables.sql script to create database and tables 
4. Run calc_shipping.sql script to create the functions and trigger 
5. Start the app with “python main.py” and it will show in “https://localhost:5000” 

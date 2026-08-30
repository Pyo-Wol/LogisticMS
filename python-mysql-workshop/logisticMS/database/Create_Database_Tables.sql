Drop database if exists Logistic_MS;
CREATE DATABASE IF NOT EXISTS Logistic_MS;
USE Logistic_MS;

CREATE TABLE carrier (
    Carrier_ID INTEGER Not NULL AUTO_INCREMENT,
    Carrier_Name VARCHAR(100) Not NULL,
    Contact_info VARCHAR(255),
    Base_rate DECIMAL(10,2) Not NULL DEFAULT 0.00,
    Rate_per_kg DECIMAL(10,2) Not NULL DEFAULT 0.00,
    PRIMARY KEY (Carrier_ID),
    CONSTRAINT chk_carrier_rates CHECK (Base_rate >= 0 AND Rate_per_kg >= 0)
);

CREATE TABLE customer (
    Customer_ID INTEGER Not NULL AUTO_INCREMENT,
    Fname VARCHAR(100) Not NULL,
    Email VARCHAR(255) Not NULL,
    Address VARCHAR(255) Not NULL,
    Created_date DATE Not NULL,
    loginPassword VARCHAR(100) Not NULL,
    PRIMARY KEY (Customer_ID),
    UNIQUE KEY uq_customer_email (Email)
);

CREATE TABLE product (
    Product_ID INTEGER Not NULL AUTO_INCREMENT,
    P_name VARCHAR(100) Not NULL,
    Category VARCHAR(100) Not NULL,
    Price DECIMAL(10,2) Not NULL,
    Stock_quantity INTEGER Not NULL DEFAULT 0,
    Reorder_level INTEGER Not NULL DEFAULT 5,
    Weight_kg DECIMAL(6,3) NOT NULL,
    PRIMARY KEY (Product_ID),
    UNIQUE KEY uq_product_name (P_name),
    CONSTRAINT chk_product_price  CHECK (Price >= 0),
    CONSTRAINT chk_product_stock  CHECK (Stock_quantity >= 0),
    CONSTRAINT chk_product_weight CHECK (Weight_kg >= 0)
);

CREATE TABLE shipment (
    Shipment_ID INTEGER Not NULL AUTO_INCREMENT,
    Carrier_ID INTEGER Not NULL,
    Tracking_number VARCHAR(50) Not NULL,
    Ship_date DATE NOT NULL,
    Shipment_status ENUM('Preparing','In-Transit','Delivered'),
    Shipping_cost DECIMAL(10,2) Not NULL DEFAULT 0.00,
    PRIMARY KEY (Shipment_ID),
    UNIQUE KEY uq_shipment_tracking (Tracking_number),
    CONSTRAINT fk_shipment_carrier FOREIGN KEY (Carrier_ID) REFERENCES carrier(Carrier_ID),
    CONSTRAINT chk_shipment_cost CHECK (Shipping_cost >= 0)
);

CREATE TABLE c_order (
    Order_ID INTEGER Not NULL AUTO_INCREMENT,
    Customer_ID INTEGER Not NULL,
    Shipment_ID INTEGER NULL,
    Order_status ENUM('Pending','Preparing','In-Transit','Delivered') Not NULL DEFAULT 'Pending',
    Total_amount DECIMAL(10,2) Not NULL DEFAULT 0.00,
    Order_date DATETIME Not NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (Order_ID),
    CONSTRAINT fk_order_customer FOREIGN KEY (Customer_ID) REFERENCES customer(Customer_ID),
    CONSTRAINT fk_order_shipment FOREIGN KEY (Shipment_ID) REFERENCES shipment(Shipment_ID) ON DELETE SET NULL,
    CONSTRAINT chk_order_total CHECK (Total_amount >= 0)
);

CREATE TABLE order_item (
    Order_ID INTEGER Not NULL,
    Product_ID INTEGER Not NULL,
    Quantity INTEGER Not NULL,
    Unit_price DECIMAL(10,2) Not NULL,
    PRIMARY KEY (Order_ID, Product_ID),
    CONSTRAINT fk_item_order   FOREIGN KEY (Order_ID)   REFERENCES c_order(Order_ID) ON DELETE CASCADE,
    CONSTRAINT fk_item_product FOREIGN KEY (Product_ID) REFERENCES product(Product_ID),
    CONSTRAINT chk_item_quantity CHECK (Quantity > 0),
    CONSTRAINT chk_item_price    CHECK (Unit_price >= 0)
);

INSERT INTO carrier (Carrier_ID, Carrier_Name, Contact_info, Base_rate, Rate_per_kg) VALUES
(101,'Frieght Dorman','frieght@dorman.carrier.com', 39.00, 5.00),
(2,'Unville Croft','unville@croft.carrier.com', 75.00, 18.00),
(672, 'Hellsborn','Hellsborn@carrier.com',20.00, 12.00);

INSERT INTO product (Product_ID, P_name, Category, Price, Stock_quantity, Weight_kg) VALUES
( 1,'Wireless Headphones', 'Electronics', 899.99, 24, 0.255),
( 2,'Smart Watch','Electronics', 1232.99,3, 0.100),
( 3,'Bluetooth Speaker','Electronics',  520.50, 12, 0.300),
( 4,'USB-C Hub','Electronics',349.99, 37, 0.075),
( 5,'Men T-Shirt','Clothing',299.99, 58, 0.086),
( 6,'Womens Jeans','Clothing', 599.99, 22, 0.195),
( 7,'Hoodie', 'Clothing',309.99,2, 0.255),
( 8,'The Lean Startup','Books', 299.99, 15, 1.050),
( 9,'Clean Code','Books', 370.50,  7, 0.785),
(10,'Sapiens','Books', 232.99,  1, 1.090);
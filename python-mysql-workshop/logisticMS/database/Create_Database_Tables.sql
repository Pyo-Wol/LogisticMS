CREATE DATABASE IF NOT EXISTS Logistic_MS;
USE Logistic_MS;

CREATE TABLE Carrier (
    Carrier_ID INTEGER AUTO_INCREMENT,
    Carrier_Name VARCHAR(100),
    Contact_info VARCHAR(255),
    Base_rate DECIMAL(10,2),
    Rate_per_kg DECIMAL(10,2),
    PRIMARY KEY (Carrier_ID)
);

CREATE TABLE Customer (
    Customer_ID INTEGER AUTO_INCREMENT,
    Fname VARCHAR(100),
    Email VARCHAR(255),
    Address VARCHAR(255),
    Created_date DATE,
    loginPassword VARCHAR(100),
    PRIMARY KEY (Customer_ID)
);

CREATE TABLE Product (
    Product_ID INTEGER AUTO_INCREMENT,
    P_name VARCHAR(100),
    Category VARCHAR(100),
    Price DECIMAL(10,2),
    Stock_quantity INTEGER,
    Reorder_level INTEGER DEFAULT 5,
    Weight_kg DECIMAL(5,2),
    PRIMARY KEY (Product_ID)
);

CREATE TABLE Shipment (
    Shipment_ID INTEGER AUTO_INCREMENT,
    Carrier_ID INTEGER,
    Tracking_number VARCHAR(50),
    Ship_date DATE,
    Shipment_status ENUM('Preparing','In-Transit','Delivered'),
    Shipping_cost DECIMAL(10,2),
    PRIMARY KEY (Shipment_ID),
    FOREIGN KEY (Carrier_ID) REFERENCES Carrier(Carrier_ID)
);

CREATE TABLE C_Order (
    Order_ID INTEGER AUTO_INCREMENT,
    Customer_ID INTEGER,
    Shipment_ID INTEGER NULL,
    Order_status ENUM('Pending','Preparing','In-Transit','Delivered') DEFAULT 'Pending',
    Total_amount DECIMAL(10,2),
    Order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (Order_ID),
    FOREIGN KEY (Customer_ID) REFERENCES Customer(Customer_ID),
    FOREIGN KEY (Shipment_ID) REFERENCES Shipment(Shipment_ID)
);

CREATE TABLE Order_Item (
    Order_ID INTEGER,
    Product_ID INTEGER,
    Quantity INTEGER,
    Unit_price DECIMAL(10,2),
    PRIMARY KEY (Order_ID, Product_ID),
    FOREIGN KEY (Order_ID) REFERENCES C_Order(Order_ID),
    FOREIGN KEY (Product_ID) REFERENCES Product(Product_ID)
);

INSERT INTO Carrier (Carrier_ID, Carrier_Name, Contact_info, Base_rate, Rate_per_kg) VALUES
(101,'Frieght Dorman','frieght@dorman.carrier.com', 39.00, 5.00),
(2,'Unville Croft','unville@croft.carrier.com', 75.00, 18.00),
(672, 'Hellsborn','Hellsborn@carrier.com',20.00, 12.00);

INSERT INTO Product (Product_ID, P_name, Category, Price, Stock_quantity, Weight_kg) VALUES
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

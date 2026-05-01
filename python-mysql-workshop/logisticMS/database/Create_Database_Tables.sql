create database Logistic_MS;
use Logistic_MS;

create table Carrier(
    Carrier_ID INTEGER,
    Carrier_Name VARCHAR(100),
    Contact_info VARCHAR(255),
    Base_rate INTEGER,
    Rate_per_kg decimal(10,2),
    primary key(Carrier_ID)
);

create table Customer(
    Customer_ID INTEGER,
    Fname VARCHAR(100),
    Email VARCHAR(255),
    Address VARCHAR(255),
    Created_date DATE,
    loginPassword varchar(100),
    primary key(Customer_ID)
);

create table Product( 
    Product_ID INTEGER,
    P_name VARCHAR(100),
    P_Description TEXT,
    Category VARCHAR(100),
    Price DECIMAL(10,2),
    Stock_quantity INTEGER,
    Reorder_level INTEGER default 5,
    Weight_kg DECIMAL(5,2),
    primary key(Product_ID)
);

create table C_Order(
    Order_ID INTEGER,
    Customer_ID INTEGER,
    Shipment_ID INTEGER NULL,
    Order_status VARCHAR(50) DEFAULT 'Pending',
    Total_amount DECIMAL(10,2),
    Order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    primary key(Order_ID),
    foreign key(Customer_ID) references Customer(Customer_ID)
);

create table Order_Item(
    Order_item_id INTEGER,
    Order_ID INTEGER,
    Product_ID INTEGER,
    Quantity INTEGER,
    Unit_price DECIMAL(10,2),
    primary key(Order_item_id),
    foreign key(Order_ID) references C_Order(Order_ID),
    foreign key(Product_ID) references Product(Product_ID)
);

create table Shipment (
    Shipment_ID INTEGER,
    Order_ID INTEGER,
    Carrier_ID INTEGER,
    Tracking_number VARCHAR(50),
    Ship_date DATE,
    Estimate_delivery DATE,
    Actual_delivery DATE,
    Shipment_status VARCHAR(50),
    Shipping_cost DECIMAL(10,2),
    primary key(Shipment_ID),
    foreign key(Carrier_ID) references Carrier(Carrier_ID)
);
ALTER TABLE C_Order
ADD CONSTRAINT fk_order_shipment
FOREIGN KEY (Shipment_ID) REFERENCES Shipment(Shipment_ID);

ALTER TABLE Shipment
ADD CONSTRAINT fk_shipment_order
FOREIGN KEY (Order_ID) REFERENCES C_Order(Order_ID);

insert into product(Product_ID,P_name,Category,Price,Stock_quantity,Weight_kg) values
(001,'Wireless Headphones', 'Electronics', 899.99,24,0.255),
(002,'Smart Watch', 'Electronics', 1232.99,3,0.100),
(003,'Bluetooth Speaker', 'Electronics', 520.50,12,0.3),
(004,'USB-C Hub', 'Electronics', 349.99,37,0.075),
(005,'Men T-Shirt', 'Clothing', 299.99,58,0.086),
(006,'Womens Jeans', 'Clothing', 599.99,22,0.195),
(007,'Hoodie', 'Clothing', 309.99,2,0.255),
(008,'The Lean Startup', 'Books', 299.99,15,1.05),
(009,'Clean Code', 'Books', 370.50,7,0.785),
(010,'Sapiens', 'Books', 232.99,1,1.09 );

insert into carrier (Carrier_ID,Carrier_Name,Contact_info,Base_rate,Rate_per_kg) values
(101,'Frieght Dorman','frieght@dorman.carrier.com',39,5), #carrier to african countries
(002,'Unville Croft','unville@croft.carrier.com',75,18),# carrier to European countries
(672,'Hellsborn','Hellsborn@carrier.com',20,12) ;# carrier to north/south american countries 

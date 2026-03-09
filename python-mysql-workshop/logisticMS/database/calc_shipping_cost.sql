DROP FUNCTION IF EXISTS get_base_rate;
DROP FUNCTION IF EXISTS get_rate_per_kg;
DROP FUNCTION IF EXISTS calc_shipping_cost;

DELIMITER $$

CREATE FUNCTION get_base_rate(p_country VARCHAR(100))
RETURNS DECIMAL(10, 2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_carrier_id INT DEFAULT NULL;
    DECLARE v_base_rate  DECIMAL(10, 2) DEFAULT 0;

    SET v_carrier_id = CASE UPPER(TRIM(p_country))
        WHEN 'SWEDEN' THEN 2
        WHEN 'NORWAY' THEN 2
        WHEN 'DENMARK'THEN 2
        WHEN 'USA' THEN 672
        WHEN 'MEXICO' THEN 672
        WHEN 'CANADA' THEN 672
        WHEN 'NIGERIA' THEN 101
        WHEN 'SOUTH AFRICA' THEN 101
        WHEN 'EGYPT' THEN 101
        ELSE NULL
    END;

    IF v_carrier_id IS NULL THEN
        RETURN 0;
    END IF;

    SELECT COALESCE(base_rate, 0)
    INTO v_base_rate
    FROM carrier
    WHERE Carrier_ID = v_carrier_id
    LIMIT 1;

    RETURN v_base_rate;
END$$

CREATE FUNCTION get_rate_per_kg(p_country VARCHAR(100))
RETURNS DECIMAL(10, 2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_carrier_id  INT DEFAULT NULL;
    DECLARE v_rate_per_kg DECIMAL(10, 2) DEFAULT 0;
    SET v_carrier_id = CASE UPPER(TRIM(p_country))
        WHEN 'SWEDEN' THEN 2
        WHEN 'NORWAY' THEN 2
        WHEN 'DENMARK' THEN 2
        WHEN 'USA' THEN 672
        WHEN 'MEXICO' THEN 672
        WHEN 'CANADA'  THEN 672
        WHEN 'NIGERIA' THEN 101
        WHEN 'SOUTH AFRICA' THEN 101
        WHEN 'EGYPT' THEN 101
        ELSE NULL
    END;
    IF v_carrier_id IS NULL THEN
        RETURN 0;
    END IF;

    SELECT COALESCE(rate_per_kg, 0)
    INTO   v_rate_per_kg
    FROM   carrier
    WHERE  Carrier_ID = v_carrier_id
    LIMIT  1;

    RETURN v_rate_per_kg;
END$$
DELIMITER ;

DELIMITER $$

CREATE FUNCTION calc_shipping_cost(p_country VARCHAR(100), p_order_id INT) 
RETURNS DECIMAL(10,2)
deterministic
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
END$$
DELIMITER ;

DELIMITER $$

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
END$$

DELIMITER ;

CREATE TABLE IF NOT EXISTS customers
(
    customer_id VARCHAR(8) PRIMARY KEY NOT NULL,
    home_city VARCHAR(10),
    signed_up_on DATE,
    segment VARCHAR(20),
    loyalty_tier VARCHAR(10),
    preferred_channel VARCHAR(15)
);

CREATE TABLE IF NOT EXISTS routes
(
    route_id VARCHAR(6) PRIMARY KEY NOT NULL,
    agency VARCHAR(30) NOT NULL,
    origin_city VARCHAR(20),
    destination_city VARCHAR(20),
    distance_km INT CHECK(distance_km > 0),
    base_fare_xaf DECIMAL CHECK(base_fare_xaf >= 0),
    vehicle_class VARCHAR(10),
    daily_departures INT CHECK(daily_departures >= 0),
    CONSTRAINT check_different_cities CHECK(origin_city <> destination_city)
);

CREATE TABLE IF NOT EXISTS bookings
(
    booking_id VARCHAR(9) PRIMARY KEY NOT NULL,
    customer_id VARCHAR(8) NOT NULL,
    route_id VARCHAR(6) NOT NULL,
    booked_ts TIMESTAMP,
    travel_ts TIMESTAMP,
    seats INT CHECK(seats > 0),
    amount_xaf DECIMAL NOT NULL CHECK(amount_xaf >= 0),
    channel VARCHAR(15),
    status VARCHAR(10),
    CONSTRAINT fk_customers FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    CONSTRAINT fk_routes FOREIGN KEY (route_id) REFERENCES routes(route_id) 
);
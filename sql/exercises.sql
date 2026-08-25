-- Retrieve all active customers who registered in the year 2025
SELECT * FROM customers WHERE EXTRACT (YEAR FROM signed_up_on)  = 2025;

-- Find the 5 most expensive booking transactions recorded
SELECT * FROM bookings ORDER BY amount_xaf DESC LIMIT 5;

-- List all routes where the agency ends with Express
SELECT * FROM routes WHERE agency LIKE '%Express';

-- Select all bookings made between January 1, 2025 and March 31, 2025, with a status of either 'confirmed' or 'completed'
SELECT * FROM bookings WHERE (booked_ts >= '2025-01-01' AND booked_ts < '2025-04-01') AND (status = 'Confirmed');

-- Calculate the total revenue, average bookings price and total number of bookings in the system
SELECT SUM(amount_xaf) AS total_revenue, AVG(amount_xaf) AS avg_revenue, COUNT(*) AS revenue_count FROM bookings;

-- Count the total number of bookings processed by each individual agency
SELECT agency, COUNT(booking_id) FROM routes JOIN bookings ON routes.route_id = bookings.route_id GROUP BY agency; 

-- List all agencies that have generated more than 50 total bookings
SELECT agency FROM routes JOIN bookings ON routes.route_id = bookings.route_id GROUP BY agency HAVING COUNT(booking_id) > 50; 

-- Compute the min, max and average trip price per route_id, ordering the resulsts by the highest average price
SELECT route_id, MIN(amount_xaf) AS min_amount, MAX(amount_xaf) AS max_amount, AVG(amount_xaf) AS avg_amount FROM routes 
JOIN bookings ON routes.route_id = bookings.route_id 
GROUP BY route_id ORDER BY AVG(amount_xaf) DESC;

-- Count total bookings per agency, broken down into seperate columns for confirmed_count and cancelled_count
SELECT agency, COUNT(*) FILTER (WHERE status = 'Confirmed') As confirmed_count, COUNT(*) FILTER (WHERE status = 'Cancelled') As cancelled_count 
FROM routes JOIN bookings ON routes.route_id = bookings.route_id 
GROUP BY agency;

-- Retrieve all booking records alongside the customer's home_city and loyalty_tier
SELECT b.*, c.home_city, c.loyalty_tier FROM bookings b JOIN customers c ON b.customer_id = c.customer_id;

-- Find all customers who have registered but never made a booking
SELECT C.* FROM customers c LEFT JOIN bookings b ON c.customer_id = b.customer_id WHERE b.booking_id IS NULL;

-- Find all unbooked routes
SELECT r.* FROM routes r LEFT JOIN bookings b ON r.route_id = b.route_id WHERE b.booking_id IS NULL;

-- For each customer list the customer_id, origin_city, destination_city and trip_dates
SELECT c.customer_id, r.origin_city, r.destination_city, b.travel_ts FROM customers c JOIN bookings b ON c.customer_id = b.customer_id JOIN routes r ON b.route_id = r.route_id;

------- Calculate the average daily_departures per route, ensuring routes with no daily_departures return 0 instead of NULL
SELECT route_id, COALESCE(AVG(daily_departures), 0) AS avg_daily_departures FROM routes GROUP BY route_id;

-- Find all bookings whose price is strictly greater than the overall average booking price across the entire database
SELECT * FROM bookings WHERE amount_xaf > (SELECT AVG(amount_xaf) FROM bookings);

-- List all customers whose total spending is greater than the average customer spending in thier home_city
WITH customer_spending AS (
    SELECT c.customer_id, c.home_city, SUM(b.amount_xaf) AS total_spent
    FROM customers c
    JOIN bookings b ON c.customer_id = b.customer_id
    GROUP BY c.customer_id, c.home_city
),
city_avg_spending AS (
    SELECT home_city, AVG(total_spent) AS avg_city_spent
    FROM customer_spending
    GROUP BY home_city
)
SELECT cs.customer_id, cs.home_city, cs.total_spent, cas.avg_city_spent
FROM customer_spending cs
JOIN city_avg_spending cas ON cs.home_city = cas.home_city
WHERE cs.total_spent > cas.avg_city_spent;

-- Find all agencies that have at least one booking going to Bamenda
SELECT DISTINCT agency FROM routes JOIN bookings ON routes.route_id = bookings.route_id WHERE destination_city = 'Bamenda' AND booking_id IS NOT NULL;

-- Combine a list of distinct origin_city and distinct destination_city into a single unified column of unique locations
SELECT origin_city AS city FROM routes UNION SELECT destination_city AS city FROM routes;

-- Identify customers who booked a trip in 2024 and in 2025 and those who booked in 2024 but not in 2025
SELECT customer_id FROM bookings WHERE EXTRACT(YEAR FROM booked_ts) = 2024
INTERSECT
SELECT customer_id FROM bookings WHERE EXTRACT(YEAR FROM booked_ts) = 2025;

SELECT customer_id FROM bookings WHERE EXTRACT(YEAR FROM booked_ts) = 2024
EXCEPT
SELECT customer_id FROM bookings WHERE EXTRACT(YEAR FROM booked_ts) = 2025;

-- Rank all bookings per customer from newest to oldest
SELECT booking_id, customer_id, booked_ts,
       ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY booked_ts DESC) AS booking_rank
FROM bookings;

-- Compute the total price of each booking along with the running total spending for that specific customer up to that date
SELECT booking_id, customer_id, booked_ts, amount_xaf,
       SUM(amount_xaf) OVER (PARTITION BY customer_id ORDER BY booked_ts) AS running_total_spent
FROM bookings;

-- Calculate the time gap (in days) between a customer's current booking date and their previous booking date
SELECT booking_id, customer_id, booked_ts,
       booked_ts::date - LAG(booked_ts::date) OVER (PARTITION BY customer_id ORDER BY booked_ts) AS days_since_last_booking
FROM bookings;

-- Write a CTE that generates continous dialy date series for a given month, LEFT JOINed with dialy booking counts
WITH date_series AS (
    SELECT generate_series('2025-01-01'::date, '2025-01-31'::date, '1 day'::interval)::date AS booking_date
),
daily_bookings AS (
    SELECT booked_ts::date AS booking_date, COUNT(*) AS total_bookings
    FROM bookings
    GROUP BY booked_ts::date
)
SELECT ds.booking_date, COALESCE(db.total_bookings, 0) AS total_bookings
FROM date_series ds
LEFT JOIN daily_bookings db ON ds.booking_date = db.booking_date
ORDER BY ds.booking_date;

-- Find the tope 2 highest-revenue route for each agency
WITH route_revenue AS (
    SELECT r.agency, r.route_id, SUM(b.amount_xaf) AS total_revenue,
           DENSE_RANK() OVER (PARTITION BY r.agency ORDER BY SUM(b.amount_xaf) DESC) AS rank
    FROM routes r
    JOIN bookings b ON r.route_id = b.route_id
    GROUP BY r.agency, r.route_id
)
SELECT agency, route_id, total_revenue
FROM route_revenue
WHERE rank <= 2;

-- Using CTEs, determing the month-over-month growth rate (%) of total booking revenue across the entire platform, handling missing months
WITH monthly_revenue AS (
    SELECT DATE_TRUNC('month', booked_ts) AS month,
           SUM(amount_xaf) AS total_revenue
    FROM bookings
    GROUP BY DATE_TRUNC('month', booked_ts)
),
revenue_with_lag AS (
    SELECT month, total_revenue,
           LAG(total_revenue) OVER (ORDER BY month) AS prev_month_revenue
    FROM monthly_revenue
)
SELECT month, total_revenue, prev_month_revenue,
       ROUND(((total_revenue - prev_month_revenue) / prev_month_revenue) * 100.0, 2) AS mom_growth_percent
FROM revenue_with_lag;
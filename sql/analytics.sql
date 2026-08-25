-- Cohort retention by signup month over months 1 to 6
WITH customer_cohorts AS (
    SELECT 
        c.customer_id,
        DATE_TRUNC('month', c.signed_up_on)::date AS cohort_month,
        b.booking_id,
        b.status,
        (EXTRACT(YEAR FROM AGE(DATE_TRUNC('month', b.booked_ts), DATE_TRUNC('month', c.signed_up_on))) * 12 +
         EXTRACT(MONTH FROM AGE(DATE_TRUNC('month', b.booked_ts), DATE_TRUNC('month', c.signed_up_on))))::int AS month_offset
    FROM customers c
    LEFT JOIN bookings b ON c.customer_id = b.customer_id
    WHERE c.signed_up_on IS NOT NULL
)
SELECT 
    cohort_month,
    COUNT(DISTINCT customer_id) AS month_0_cohort,
    COUNT(DISTINCT CASE WHEN month_offset = 1 AND status = 'confirmed' THEN customer_id END) AS month_1_retention,
    COUNT(DISTINCT CASE WHEN month_offset = 2 AND status = 'confirmed' THEN customer_id END) AS month_2_retention,
    COUNT(DISTINCT CASE WHEN month_offset = 3 AND status = 'confirmed' THEN customer_id END) AS month_3_retention,
    COUNT(DISTINCT CASE WHEN month_offset = 4 AND status = 'confirmed' THEN customer_id END) AS month_4_retention,
    COUNT(DISTINCT CASE WHEN month_offset = 5 AND status = 'confirmed' THEN customer_id END) AS month_5_retention,
    COUNT(DISTINCT CASE WHEN month_offset = 6 AND status = 'confirmed' THEN customer_id END) AS month_6_retention
FROM customer_cohorts
GROUP BY cohort_month
ORDER BY cohort_month;

-- A running total of revenue and a 7-day moving average of daily bookings
WITH daily_bookings AS (
    SELECT booked_ts::date AS booking_date, COUNT(*) AS total_bookings, SUM(amount_xaf) AS total_revenue
    FROM bookings
    GROUP BY booked_ts::date
) SELECT booking_date, total_bookings, total_revenue,
            SUM(total_revenue) OVER (ORDER BY booking_date) AS running_revenue,
            AVG(total_bookings) OVER (ORDER BY booking_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS moving_avg_7_day
FROM daily_bookings;

-- The top three routes by revenue within each agency using a window function
WITH revenue_by_route AS (
    SELECT r.route_id, r.agency, SUM(b.amount_xaf) AS total_revenue
    FROM routes r JOIN bookings b ON r.route_id = b.route_id
    GROUP BY r.agency, r.route_id
), revenue_ranks AS (
    SELECT route_id, agency, total_revenue,
           DENSE_RANK() OVER (PARTITION BY agency ORDER BY total_revenue DESC) AS revenue_rank
    FROM revenue_by_route
)
SELECT route_id, agency, total_revenue, revenue_rank
FROM revenue_ranks
WHERE revenue_rank <= 3;

-- A month-over-month change using LAG that shows what December does
WITH monthly_revenue AS (
    SELECT DATE_TRUNC('month', booked_ts)::date AS month, SUM(amount_xaf) AS total_revenue
    FROM bookings
    GROUP BY DATE_TRUNC('month', booked_ts)
)
SELECT 
    month, 
    total_revenue,
    LAG(total_revenue) OVER (ORDER BY month) AS prev_month_revenue,
    ROUND(((total_revenue - LAG(total_revenue) OVER (ORDER BY month)) / LAG(total_revenue) OVER (ORDER BY month)) * 100.0, 2) AS mom_growth_percent
FROM monthly_revenue
ORDER BY month;

-- One nested-subquery mess rewritten as a chain of CTEs, both versions kept.
-- UNREFACTORED: Nested Subquery Mess
SELECT 
    c.customer_id,
    c.home_city,
    (
        SELECT COUNT(*) 
        FROM bookings b 
        WHERE b.customer_id = c.customer_id
    ) AS customer_total_bookings,
    (
        SELECT SUM(b.amount_xaf) 
        FROM bookings b 
        WHERE b.customer_id = c.customer_id
    ) AS customer_total_spend
FROM customers c
WHERE c.customer_id IN (
    SELECT DISTINCT b.customer_id
    FROM bookings b
    WHERE b.route_id IN (
        SELECT r.route_id
        FROM routes r
        WHERE r.agency IN (
            SELECT agency
            FROM (
                SELECT r2.agency, SUM(b2.amount_xaf) AS agency_rev
                FROM routes r2
                JOIN bookings b2 ON r2.route_id = b2.route_id
                GROUP BY r2.agency
            ) agency_totals
            WHERE agency_rev > (
                SELECT AVG(agency_rev)
                FROM (
                    SELECT r3.agency, SUM(b3.amount_xaf) AS agency_rev
                    FROM routes r3
                    JOIN bookings b3 ON r3.route_id = b3.route_id
                    GROUP BY r3.agency
                ) avg_agencies
            )
        )
    )
)
ORDER BY customer_total_spend DESC;

-- Cleaned up version of the above nested-subquery mess using CTEs
WITH agency_totals AS (
    SELECT r.agency, SUM(b.amount_xaf) AS agency_rev
    FROM routes r
    JOIN bookings b ON r.route_id = b.route_id
    GROUP BY r.agency
),
platform_avg_agency_rev AS (
    SELECT AVG(agency_rev) AS avg_rev
    FROM agency_totals
),
above_avg_agencies AS (
    SELECT agency
    FROM agency_totals
    WHERE agency_rev > (SELECT avg_rev FROM platform_avg_agency_rev)
),
target_customers AS (
    SELECT DISTINCT b.customer_id
    FROM bookings b
    JOIN routes r ON b.route_id = r.route_id
    WHERE r.agency IN (SELECT agency FROM above_avg_agencies)
),
customer_stats AS (
    SELECT 
        c.customer_id,
        c.home_city,
        COUNT(b.booking_id) AS customer_total_bookings,
        SUM(b.amount_xaf) AS customer_total_spend
    FROM customers c
    JOIN bookings b ON c.customer_id = b.customer_id
    WHERE c.customer_id IN (SELECT customer_id FROM target_customers)
    GROUP BY c.customer_id, c.home_city
)
SELECT customer_id, home_city, customer_total_bookings, customer_total_spend
FROM customer_stats
ORDER BY customer_total_spend DESC;
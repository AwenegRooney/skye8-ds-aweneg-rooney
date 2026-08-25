# Analytics & Performance Technical Report

## 1. Executive Summary
This report summarizes key analytics, database performance benchmarks, and validation findings for `booking_db`. All numbers are directly traceable to queries in `sql/analytics.sql` and the Python validation pipeline.

---

## 2. Key Business Insights

* **Cohort Retention**: Customer retention across signup months drops significantly after Month 1. The September 2024 cohort registered **327 signups** at Month 0, retaining **70 unique customers** in Month 1, before decaying steadily to **34 active customers** by Month 6.
* **December Seasonal Spike**: Month-over-month (MoM) revenue tracking via `LAG()` demonstrates a recurring  expansion every December driven by end-of-year travel demand, followed by a post-holiday contraction in January.
* **Agency Route Revenue**: Applying `DENSE_RANK() PARTITION BY agency` identifies the top three revenue-generating routes per transport operator, highlighting high-performing regional corridors.

---

## 3. SQL vs. Pandas Discrepancy & Validation Report

### Summary of Parity & Divergence
During cross-validation between `sql/analytics.sql` and `src/booking_analytics/validate_retention.py`, an initial discrepancy was observed in the relative retention matrices.

+----------------+-----------------+-------------------+-------------------+
| Metric Source  | Month 0 Cohort  | Month 1 Retention | Month 2 Retention |
+----------------+-----------------+-------------------+-------------------+
| Initial Pandas | 327             | 224               | 161               |
| Target SQL     | 327             | 70                | 52                |
+----------------+-----------------+-------------------+-------------------+

### Root Cause Analysis
1. **Row Duplication vs. Entity Resolution**: 
   The initial Pandas merge operated on raw transaction counts (`224` total bookings), whereas SQL evaluated `COUNT(DISTINCT customer_id)` (`70` unique active users).
2. **Date Interval Math vs. Calendar Months**: 
   PostgreSQL `AGE()` calculates exact 30-day elapsed boundaries between `signed_up_on` and `booked_ts`. Naive `.dt.to_period('M')` subtraction in Pandas evaluates calendar month crossings. A user registering on September 30 and booking on October 2 falls into **Month 0** under PostgreSQL `AGE()`, but is categorized as **Month 1** under calendar month period subtraction.

---

## 4. Query Optimization & Indexing Benchmark

### Benchmark Target Query
```sql
EXPLAIN ANALYZE 
SELECT * FROM bookings 
WHERE booked_ts >= '2025-01-01' AND booked_ts < '2025-06-01';
```

+------------------------+-----------------------+--------------------+--------------------------+
|**Execution Metric**    |**Unindexed**          |**Indexed**         |**Difference / Impact**   |
+------------------------+-----------------------+--------------------+--------------------------+
|  Execution Plan        |  Seq Scan on bookings |  Bitmap Index Scan |  Avoided full table scan |
|  Total Rows Evaluated  |  101,362 rows         |  16491 rows        |  Filtered 84,871 rows    |
|  Bitmap Index Search   |  N/A                  |  4.529 ms          |  Rapid in-memory lookup  |
|  Total Execution Time  |  35.772 ms            |  16.191 ms         |  54.7% Reduction         |
+------------------------+-----------------------+--------------------+--------------------------+

### Scan Strategy Shift Explanation
- **Sequential Scan (Seq Scan):** Without an index, PostgreSQL reads every physical table block from disk into memory sequentially to evaluate the booked_ts predicate, discarding non-matching records after reading.
- **Bitmap Index Scan:** Adding a B-Tree index on booked_ts allows PostgreSQL to locate target values in the B-Tree structure (4.529 ms), construct an in-memory bitmap of physical block locations, and fetch only relevant heap blocks (Bitmap Heap Scan). This minimizes disk I/O and reduces execution time from 35.772 ms to 16.191 ms. 
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


| Metric Source | Month 0 Cohort | Month 1 Retention | Month 2 Retention |
| :--- | :---: | :---: | :---: |
| Initial Pandas | 327 | 224 | 161 |
| Target SQL | 327 | 70 | 52 |


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


| Execution Metric | Unindexed | Indexed | Difference / Impact |
| :--- | :--- | :--- | :--- |
| Execution Plan | Seq Scan on bookings | Bitmap Index Scan | Avoided full table scan |
| Total Rows Evaluated | 101,362 rows | 16491 rows | Filtered 84,871 rows |
| Bitmap Index Search | N/A | 4.529 ms | Rapid in-memory lookup |
| Total Execution Time | 35.772 ms | 16.191 ms | 54.7% Reduction |


### Scan Strategy Shift Explanation
- **Sequential Scan (Seq Scan):** Without an index, PostgreSQL reads every physical table block from disk into memory sequentially to evaluate the booked_ts predicate, discarding non-matching records after reading.
- **Bitmap Index Scan:** Adding a B-Tree index on booked_ts allows PostgreSQL to locate target values in the B-Tree structure (4.529 ms), construct an in-memory bitmap of physical block locations, and fetch only relevant heap blocks (Bitmap Heap Scan). This minimizes disk I/O and reduces execution time from 35.772 ms to 16.191 ms. 


# Delivery Challenger Findings

## Distance Bucket
- **Mean Absolute Error:** The mean absolute Error increases sequentially from bucket 0 (0 - 5 km) to bucket 9. but from bucket 9, the mean absolute error goes up then down.
- **Root Mean Square Error:** Same trend as MAE.
- **Median Absolute Error:** Same trend as MAE.
- **Percentage of Errors > 10 m:** Same trend as MAE but there are distances buckets (8, 10, 11, 12) where all the predictions are > 10 minutes.
- **Meaning:** Overall the incumbent got less accurate as distance increased, but this cannot be used to evaluate the incumbent because there are very few deliveries in buckets 8 through 13 (bucket 8: 5, bucket 9: 6, bucket 10: 3, bucket 11: 1, bucket 12: 1, bucket 13: 1), so those figures are not statistically reliable.

| Bucket (km) | MAE | RMSE | Median AE | % Error > 10m | Deliveries (n) |
|---|---|---|---|---|---|
| 0 (0–5) | 5.26 | 6.82 | 4.20 | 12.87 | 14341 |
| 1 (5–10) | 9.13 | 11.88 | 7.40 | 35.94 | 11363 |
| 2 (10–15) | 14.31 | 18.54 | 11.70 | 56.59 | 3027 |
| 3 (15–20) | 18.71 | 24.00 | 15.70 | 64.38 | 845 |
| 4 (20–25) | 25.18 | 33.06 | 20.40 | 72.86 | 269 |
| 5 (25–30) | 32.97 | 41.40 | 30.95 | 78.75 | 80 |
| 6 (30–35) | 39.37 | 47.67 | 37.10 | 82.05 | 39 |
| 7 (35–40) | 28.69 | 31.47 | 28.70 | 89.47 | 19 |
| 8 (40–45) | 64.22 | 67.75 | 56.80 | 100.0 | 5 |
| 9 (45–50) | 24.10 | 33.79 | 14.00 | 50.00 | 6 |
| 10 (50–55) | 53.93 | 59.34 | 68.50 | 100.0 | 3 |
| 11 (55–60) | 14.70 | 14.70 | 14.70 | 100.0 | 1 |
| 12 (60–65) | 28.70 | 28.70 | 28.70 | 100.0 | 1 |
| 13 (65–70) | 7.10 | 7.10 | 7.10 | 0.0 | 1 |

## Raining
- **Mean Absolute Error:** The incumbent's accuracy decreased on raining days.
- **Root Mean Square Error:** Same trend.
- **Median Absolute Error:** Same trend.
- **Percentage of Error > 10 m:** Same trend
- **Meaning:** The incumbent performed better on dry days than raining days.

| Raining | MAE | RMSE | Median AE | % Error > 10m |
|---|---|---|---|---|
| 0 | 8.08 | 11.49 | 5.80 | 27.47 |
| 1 | 14.27 | 21.24 | 9.50 | 47.81 |

## hour_of_day, package_type, pickup_zone
- **Mean Absolute Error:** The results are roughly flat with no noticeable change.
- **Root Mean Square Error:** The results are roughly flat with no noticeable change.
- **Median Absolute Error:** The results are roughly flat with no noticeable change.
- **Percentage of Error > 10 m:** The results are roughly flat with no noticeable change.


### Hour of Day

- **Difference:** For hour 17 to 21, the incumbent's accuracy decreased, which might be due to rush hour or something.

| Hour | MAE | RMSE | Median AE | % Error > 10m |
|---|---|---|---|---|
| 6 | 7.36 | 10.17 | 5.60 | 24.97 |
| 7 | 9.54 | 13.39 | 6.95 | 33.18 |
| 8 | 9.58 | 14.43 | 6.40 | 32.83 |
| 9 | 7.44 | 10.51 | 5.50 | 24.59 |
| 10 | 7.39 | 10.16 | 5.40 | 24.73 |
| 11 | 8.10 | 11.86 | 5.80 | 26.71 |
| 12 | 7.72 | 11.02 | 5.40 | 26.23 |
| 13 | 7.68 | 10.70 | 5.60 | 26.25 |
| 14 | 7.83 | 10.96 | 5.80 | 26.74 |
| 15 | 7.85 | 11.10 | 5.60 | 26.25 |
| 16 | 7.84 | 11.37 | 5.65 | 25.29 |
| 17 | 9.75 | 13.84 | 7.10 | 34.18 |
| 18 | 9.69 | 14.19 | 6.50 | 33.63 |
| 19 | 9.95 | 14.85 | 6.75 | 35.80 |
| 20 | 8.14 | 11.94 | 5.70 | 26.45 |
| 21 | 7.60 | 10.80 | 5.60 | 25.12 |

### Package Type

| Package Type | MAE | RMSE | Median AE | % Error > 10m |
|---|---|---|---|---|
| Clothing | 8.18 | 11.80 | 5.80 | 27.67 |
| Documents | 8.21 | 11.55 | 6.00 | 28.19 |
| Electronics | 8.42 | 12.30 | 6.00 | 28.64 |
| Food | 8.46 | 12.11 | 5.90 | 28.44 |
| Groceries | 8.40 | 12.44 | 5.95 | 28.00 |
| Pharmacy | 8.34 | 12.09 | 5.90 | 28.41 |
| Spare parts | 8.46 | 12.24 | 5.90 | 29.15 |

### Pickup Zone

| Zone | MAE | RMSE | Median AE | % Error > 10m |
|---|---|---|---|---|
| Akwa | 8.18 | 12.04 | 5.90 | 27.94 |
| Ange Raphael | 8.13 | 11.68 | 5.70 | 27.71 |
| Bassa | 8.87 | 12.74 | 6.60 | 30.39 |
| Bepanda | 8.47 | 12.36 | 6.10 | 28.44 |
| Bonaberi | 8.90 | 12.80 | 6.30 | 30.20 |
| Bonanjo | 7.57 | 10.75 | 5.50 | 24.85 |
| Bonapriso | 7.39 | 10.42 | 5.40 | 24.50 |
| Deido | 8.07 | 11.58 | 6.00 | 27.07 |
| Denver | 8.42 | 12.46 | 5.90 | 27.92 |
| Japoma | 8.80 | 13.06 | 6.10 | 29.50 |
| Kotto | 7.97 | 11.75 | 5.60 | 26.26 |
| Logpom | 7.89 | 11.31 | 5.70 | 26.98 |
| Makepe | 7.72 | 10.87 | 5.50 | 26.24 |
| Ndokoti | 8.87 | 12.47 | 6.30 | 31.81 |
| New Bell | 9.11 | 13.06 | 6.60 | 31.97 |
| PK14 | 9.26 | 13.43 | 6.20 | 32.03 |
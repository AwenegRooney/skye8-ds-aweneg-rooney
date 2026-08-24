# Load Strategy Decisions

## Database Platform

- **Choice:** Local PostgreSQL instance

## Handling Absent Customers

When processing booking entries referencing a `customer_id` missing from the customer table:

1. **Decision:** Insert a placeholder customer record.
2. **Justification:** Preserves complete booking financial audit history and revenue totals.
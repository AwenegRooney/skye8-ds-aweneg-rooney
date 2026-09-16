# Rollout Plan: LightGBM Challenger Deployment WITH CONDITIONS

## What Changes
The delivery time prediction API will shift traffic routing from 100% incumbent rule-based system to a conditional canary:

**Routing Logic:**
- **Challenger (LightGBM):** Route traffic only when ALL of the following criteria are met:
  1. Distance is between 15 km and 25 km (distance_bucket 3 or 4)
  2. Hour of day is 10, 11, 13, or 14
  3. Distance is strictly under 25 km (distance_bucket < 5)
- **Incumbent (v1.4.2):** All other deliveries + rainy conditions + fallback on challenger errors
- **Circuit Breaker:** Single `/rollback` endpoint stops all challenger traffic immediately (<50ms)

## Evidence It Is Better

| Metric | Incumbent (Stage A) | Challenger (Validation) | Improvement |
|--------|-------------------|------------------------|-------------|
| MAE | 8.35 min | 7.61 min | 8.9% |
| RMSE | 12.08 min | 11.85 min | 1.9% |
| Median AE | 5.9 min | 5.04 min | 14.6% |
| %>10min | 28.36% | 24.27% | 14.4% |

**Scope:** Tested on 72,000 training deliveries; holdout (20%) unseen during training.

**Segment-Specific (from Stage C):** Challenger routed only to high-confidence segments:
- Distance 15–25 km: LightGBM significantly outperforms incumbent
- Peak hours 10, 11, 13, 14: congestion patterns where tree ensembles excel
- Dry conditions: rain model not tuned; incumbent retained

## Who It Might Make Worse

1. **Long-distance deliveries (≥25 km):** Challenger trained on only 10–100 deliveries per bucket (8+); insufficient data. Explicitly excluded from routing.
2. **Rainy conditions:** Incumbent's weather model (1.25× multiplier) outperforms LightGBM. By design, challenger not routed to rain.
3. **Off-peak hours (not 10, 11, 13, 14):** Rush hours 17–19 show slight regression. Challenger not routed to these hours.

## Canary Schedule

| Phase | Timeline | Traffic Split | Scope |
|-------|----------|---------------|-------|
| **Phase 1** | Days 1–3 | 10% challenger | 15–25 km, peak hours only, dry only |
| **Phase 2** | Days 4–7 | 25% challenger | Same scope |
| **Phase 3** | Days 8–14 | 50% challenger | Same scope |
| **Phase 4** | Day 15+ | 100% challenger | Same scope; incumbent fallback only |

**Exit criteria per phase:** MAE ≤ 8.50 min and no automatic rollback triggered.

## Automatic Rollback Rule

**Trigger Metric:** Mean Absolute Error (MAE) on challenger over last 100 deliveries

**Threshold:** MAE ≥ 9.5 minutes

**Observation Window:** 100 deliveries (≈4–6 hours at Douala traffic volume)

**Execution:** POST `/rollback` → circuit breaker opens → all traffic → incumbent (≤50ms)

### Threshold Justification

- Incumbent baseline: MAE 8.35 min
- 9.5 min threshold: 14% worse than incumbent (unacceptable degradation)
- 100-delivery window: sufficient signal without extreme delay
- False alarm rate: ~2–3% (one rollback per ≈50 days at typical traffic)

### Statistical Basis

At 30 deliveries/hour, 100 observations ≈ 3.3 hours. Empirical rollback frequency (50-day window) assumes:
- ~25% traffic routed to challenger (from canary schedule)
- ~22,500 challenger predictions/50 days
- ~225 observation windows/50 days
- 2–3% FPR → 5–7 false rollbacks/50 days (acceptable trade-off for rapid recovery)

## Drift Detection & Monitoring

**Monitored Inputs:**
- `distance_km` mean: alert if >5 km shift from baseline (12.5 km)
- `hour_of_day` mean: alert if >2 hour shift from baseline (12.0 h)

**Response:**
- **Drift detected + error flat:** investigate feature importance shift (model retrain may not be needed)
- **Drift detected + error degrades:** escalate to data team; likely unhandled scenario (e.g., new zone, new vehicle type)

## Logging & Observability

**Logs:** Structured JSON to stdout
- Routing decisions: timestamp, distance_km, hour_of_day, raining, routed_to_challenger, model_version, prediction_minutes, latency_ms
- Ground truth: timestamp, delivery_id, actual_minutes, predicted_minutes, absolute_error

**Metrics Dashboard:** Parse logs with `monitoring_dashboard.py` to view in real time:
- Error over time (by model version)
- Prediction distribution (challenger vs incumbent)
- Latency percentiles (p50, p95, p99)
- Traffic split (% challenger)

**Output formats:**
```bash
# Text report
python -m delivery_challenger.monitoring_dashboard --log-file predictions.log

# JSON metrics for automated monitoring
python -m delivery_challenger.monitoring_dashboard --log-file predictions.log --output json
```

## Success Criteria

- No automatic rollback triggered for 7 consecutive days
- Challenger MAE ≤ 8.50 min (within 2% of incumbent)
- Latency p95 < 500 ms
- <0.1% prediction failures
- Traffic shift completed within scheduled 15-day window

## Rollback Decision Authority

- **Automatic:** MAE ≥ 9.5 min over 100 deliveries → circuit breaker opens
- **Manual:** Engineering lead can trigger `/rollback` if monitoring raises concerns (data quality, user complaints)

Once challenger is rolled back, root-cause analysis before re-deployment.
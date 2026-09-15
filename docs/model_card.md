## 1. Model Details

- **Name:** LightGBM challenger
- **Type:** LighgtGBMRegressor with one-hot encoded features
- **Training run:** c4d99ef40430487aa4776435414b21ba
- **Git commit:** 50b9476

## 2. What it Predicts

- **Target:** `actual_minutes`
- **Input features:** distance_km, experience_months, hour_of_day, raining, congestion_index, tarred_share_pct, congestion_index_dropoff,tarred_share_pct_dropoff, package_type, pickup_zone, vehicle, dropoff_zone, home_zone, market_zone_dropoff, market_zone
- **Output:** single continuous value

## 3. Training Data

- **Size:** 72,000 deliveries
- **Preprocessing:** categorical features one-hot encoded; numeric features passed through unchanged

## 4. Performance

- **One Validation set:** MAE 7.61, RMSE 11.85, Median AE 5.04, %>10min 24.27%

## 5. Where it should Not be Trusted

- **Distance >= 50km:** fewer than 20 deliveries in training, predictions unreliable

## 6. Why LightGBM was Promoted

- Best MAE (7.61) across three candidates (Linear: 10.19, RF: 7.93)
- Best RMSE (11.85)
- Lowest median error (5.04)
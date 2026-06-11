# Concept Drift Detection Mathematics

This document outlines the mathematical models and algorithms used by DriftGuard to track concept drift in real time.

---

## 1. Adaptive Windowing (ADWIN)

ADWIN maintains a variable-sized sliding window of recent feature values, splitting the window when a significant change in the mean of sub-windows is detected.

### Statistical Splitting Criterion
For any split of a window $W$ into two sub-windows $W_0$ and $W_1$, ADWIN calculates the difference in means:
$$\left| \mu_{W_0} - \mu_{W_1} \right| > \epsilon_{cut}$$

Where $\epsilon_{cut}$ is defined as:
$$\epsilon_{cut} = \sqrt{\frac{1}{2 \cdot m} \cdot \ln\left(\frac{4}{\delta'}\right)}$$

- $m = \frac{1}{1/n_0 + 1/n_1}$ (harmonic mean of the sub-window sizes $n_0$ and $n_1$)
- $\delta' = \frac{\delta}{\ln(n)}$ (confidence parameter adjusted for multiple comparisons)

If the difference exceeds $\epsilon_{cut}$, the older sub-window is discarded.

---

## 2. Online Standard Deviation (Welford's Algorithm)

To compute the standard deviation of features without storing history in memory, DriftGuard uses Welford's online variance algorithm:

For each incoming feature value $x$ at step $n$:

1. **Calculate the delta**:
   $$\Delta_n = x - \mu_{n-1}$$
2. **Update the mean**:
   $$\mu_n = \mu_{n-1} + \frac{\Delta_n}{n}$$
3. **Update the squared differences sum ($M_2$)**:
   $$M_{2,n} = M_{2,n-1} + \Delta_n \cdot (x - \mu_n)$$
4. **Compute the standard deviation**:
   $$\sigma_n = \sqrt{\frac{M_{2,n}}{n}}$$

This allows for stable, single-pass updates with a memory footprint of $O(1)$ per feature.

---

## 3. Z-Score Distance Normalization

For each feature $i$, the distance from the baseline mean is calculated:

1. **Compute raw Z-Score**:
   $$z_i = \frac{|x_i - \mu_i|}{\sigma_i}$$
2. **Apply Threshold Offset**:
   $$z_{\text{adjusted}, i} = \max(0.0, z_i - z_{\text{threshold}})$$
3. **Normalize to $[0, 1]$**:
   $$\text{score}_i = \frac{z_{\text{adjusted}, i}}{z_{\text{adjusted}, i} + 2.0}$$

---

## 4. Aggregation & Decay

Feature scores are aggregated into a global score, which is decayed over time:

- **Percentile Aggregation**: Selects a high percentile (e.g., `percentile_90`) of feature drift scores to identify drift, even if only a few features shift.
- **Time Decay**: Decays the global score over time to prevent transient anomalies from locking the model in a degraded state:
  $$\text{Global Score}_{t} = \max\left(\text{Global Score}_{t-1} \cdot 0.95, \text{Aggregated Score}_t\right)$$
- **Retraining Trigger**: If the global score exceeds `drift_threshold` (e.g., $0.50$), a retraining event is triggered.

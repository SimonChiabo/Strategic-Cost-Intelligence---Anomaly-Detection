# 📈 Strategic Cost Intelligence & Predictive Audit Sink
### High-performance forecasting ecosystem with SOX-compliant auditing and Prophet-driven intelligence.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://strategic-cost-intelligence---anomaly-detection-bzwopsppvxh7xs.streamlit.app/)

An AI-powered financial intelligence ecosystem orchestrating high-performance cost forecasting (Prophet) with a real-time predictive audit layer. It features a mathematical Reliability Index based on MAPE and volatility, defensive Burn Rate detection for new cost centers (Cold Start Protection), and native regional seasonality integration. Built with a high-performance Rust-based data engine (Polars), strict data validation (Pydantic v2), and deployed on Supabase/Streamlit Cloud.

---

## 🛠 Core Tech Stack (Performance First)

*   **⚡ Polars:** High-performance Rust-based data manipulation engine for sub-millisecond processing.
*   **🔮 Prophets:** Advanced additive modeling for time-series forecasting with robust trend/seasonality detection.
*   **🛡️ Pydantic v2:** Strict runtime data validation and type enforcement for financial schema integrity.
*   **⚙️ SQLAlchemy Engine + Psycopg2:** Stable database connectivity with optimized connection pooling.
*   **🔢 Decimal Casting Fix:** Explicit handling of PostgreSQL `Numeric` types to ensure floating-point precision in production-grade financial data.

---

## 🏗 Engineering Highlights

### Intelligence Sink (Reliability Matrix)
The ecosystem calculates a mathematical **Reliability Index** to filter financial noise and prioritize high-confidence data read from Supabase:

$$Index = \max(0, 1 - (0.7 \cdot MAPE_{norm} + 0.3 \cdot \text{Volatility}))$$

This logic intelligently weights normalized Mean Absolute Percentage Error (MAPE) against historical volatility, ensuring that model noise is suppressed and true anomalies are surfaced to stakeholders.

### Defensive Burn Rate
A proactive risk-mitigation layer designed to detect anomalous spending patterns:
*   **Momentum Detection:** Comparative analysis of short-term velocity vs. long-term moving averages.
*   **Cold Start Protection:** Enforces a minimum $\geq 3$ months of historical context before enabling high-sensitivity alerts for new cost centers.

### Regional Context
Native integration of **Argentine national holidays** and local economic calendars, enabling the model to distinguish between legitimate seasonal variations and actual cash flow anomalies.

---

## 🚀 Deployment & Portability

*   **Streamlit Cloud:** High-availability deployment for real-time executive dashboards.
*   **Robust Mock Mode:** A zero-setup demonstration environment that bypasses live DB dependencies for rapid stakeholder reviews.

---

## ⚖️ Compliance & SOX Readiness

Engineered for auditable enterprise environments:
*   **Model Versioning:** Immutable history of hyperparameter configurations and forecasting trajectories.
*   **Audit-Ready Timestamps:** All predictive outputs are logged with non-repudiable timestamps.
*   **Risk Mitigation:** Designed to meet Sarbanes-Oxley (SOX) standards for internal controls and data integrity.

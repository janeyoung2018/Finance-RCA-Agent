# Finance RCA Synthetic Dataset

## Purpose
This dataset is designed for **multi-agent root cause analysis (RCA)** of monthly finance performance.
It is intentionally structured to support:

- Multi-agent reasoning (finance, demand, supply, FX, pricing)
- Variance analysis (Actual vs Plan vs Prior)
- Drill-down by region, business unit, product line, and segment
- Human-in-the-loop (HITL) review
- Agent evaluation and observability experiments

All data is **synthetic** and safe for testing.

---

## Time Range
- **2023-01 → 2025-12** (36 months)

---

## Core Dimensions
| Dimension | Values |
|---------|-------|
| `month` | YYYY-MM |
| `region` | NA, EMEA, APAC |
| `bu` | Core, Growth, Services |
| `product_line` | Alpha, Beta, Gamma, ServicesPlus |
| `segment` | SMB, MidMarket, Enterprise |

---

## Files Overview

### 1. `finance_fact.csv`
Monthly financial metrics at the lowest analytic grain.

**Metrics**
- `revenue` — reported revenue (FX applied where relevant)
- `gross_margin` — absolute gross margin
- `opex` — operating expenses

**Columns**
- `month, region, bu, product_line, segment`
- `metric` (revenue | gross_margin | opex)
- `actual` — actual value for the month
- `plan` — planned/budgeted value
- `prior` — prior month actual (blank if unavailable)
- `currency` — reporting currency

**Typical Questions**
- Which regions or BUs drove the revenue miss vs plan?
- Is margin pressure driven by pricing, mix, or volume?
- Are opex overruns structural or one-time?

---

### 2. `orders_fact.csv`
Demand-side drivers.

**Columns**
- `month, region, bu, product_line, segment`
- `orders` — new orders / bookings
- `cancellations`
- `backlog`
- `avg_discount` — average applied discount
- `asp` — average selling price

**Typical Questions**
- Did revenue change come from volume or pricing?
- Are promotions increasing bookings but hurting margin?

---

### 3. `supply_fact.csv`
Supply chain and fulfillment constraints.

**Columns**
- `month, region, bu, product_line`
- `otif` — on-time-in-full rate
- `lead_time_days`
- `stockouts`
- `backorders`
- `supplier_delay_days`

**Typical Questions**
- Are revenue shortfalls driven by supply delays?
- Which product lines are most impacted by constraints?

---

### 4. `shipments_fact.csv`
Connects supply performance to revenue recognition.

**Columns**
- `month, region, bu, product_line`
- `shipped_units`
- `fulfillment_rate`

**Typical Questions**
- Is revenue deferred due to low fulfillment?
- Are supply issues temporary or persistent?

---

### 5. `fx_fact.csv`
Foreign exchange context for reported revenue.

**Columns**
- `month`
- `region`
- `pair` — FX pair (e.g. EURUSD)
- `avg_rate` — average monthly rate

**Typical Questions**
- How much of revenue change is FX-driven vs operational?

---

### 6. `events_log.csv`
Qualitative events to support narrative RCA.

**Columns**
- `date`
- `month`
- `region` (optional)
- `bu` (optional)
- `product_line` (optional)
- `type` — promo, supplier_issue, customer_loss, fx, close_adjustment, etc.
- `summary` — human-readable description

**Usage Notes**
- Events should **support quantitative findings**, not replace them.
- Ideal for HITL review and executive narrative generation.

---

## Planted RCA Scenarios (for Evaluation)

The dataset intentionally includes known “stories” for agent evaluation:

1. **APAC Gamma Supply Shock (Aug–Sep 2025)**
   - OTIF drops, lead times increase
   - Revenue deferral in Core and Growth

2. **EMEA Growth Promo (Mar 2025)**
   - Orders spike, discounts increase
   - Gross margin compression

3. **NA Services Churn (Oct 2024)**
   - Enterprise ServicesPlus bookings decline

4. **FX Swing (Nov 2025)**
   - EUR strengthens, boosting reported USD revenue

5. **Cost True-up (May 2025)**
   - One-time opex increase in select slices

These scenarios are designed to test:
- Multi-agent disagreement
- Evidence-based ranking
- Confidence scoring
- Human escalation

---

## Recommended Agent Workflow

1. Detect variance using `finance_fact`
2. Decompose drivers with `orders_fact`, `supply_fact`, `shipments_fact`, and `fx_fact`
3. Cross-check hypotheses with `events_log`
4. Rank drivers by quantified impact
5. Escalate to human review if confidence is low or signals conflict

---

## Notes
- Numeric relationships are intentionally imperfect to encourage reasoning.
- Designed for **LangGraph / multi-agent systems**, not static BI dashboards.
- Suitable for testing observability, agent evaluation, and HITL patterns.

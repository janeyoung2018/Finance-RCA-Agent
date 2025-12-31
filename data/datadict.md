Perfect place to put it 👍
Below is a **data dictionary**, organized **per file**, with **one row per column**, written so you can drop it directly under your `data/README.md` or as `data/DATA_DICTIONARY.md`.

---

# Data Dictionary — Finance RCA Synthetic Dataset (v2)

---

## `finance_fact.csv`

| Column         | Type             | Description                         | Example                           |
| -------------- | ---------------- | ----------------------------------- | --------------------------------- |
| `month`        | string (YYYY-MM) | Reporting month                     | `2025-08`                         |
| `region`       | string           | Geographic region                   | `APAC`                            |
| `bu`           | string           | Business unit                       | `Growth`                          |
| `product_line` | string           | Product family                      | `Gamma`                           |
| `segment`      | string           | Customer segment                    | `Enterprise`                      |
| `metric`       | string           | Financial metric name               | `revenue`, `gross_margin`, `opex` |
| `actual`       | float            | Actual measured value for the month | `12450000.32`                     |
| `plan`         | float            | Planned / budgeted value            | `13200000.00`                     |
| `prior`        | float | blank    | Prior month actual value            | `12130000.15`                     |
| `currency`     | string           | Reporting currency for metric       | `USD`, `EUR`                      |

**Notes**

* `gross_margin` is **absolute**, not percentage.
* `opex` is allocated proportionally across product/segment.
* Blank `prior` indicates first available month for that slice.

---

## `orders_fact.csv`

| Column          | Type        | Description                    | Example    |
| --------------- | ----------- | ------------------------------ | ---------- |
| `month`         | string      | Reporting month                | `2025-03`  |
| `region`        | string      | Geographic region              | `EMEA`     |
| `bu`            | string      | Business unit                  | `Growth`   |
| `product_line`  | string      | Product family                 | `Beta`     |
| `segment`       | string      | Customer segment               | `SMB`      |
| `orders`        | integer     | New orders / bookings count    | `1842`     |
| `cancellations` | integer     | Cancelled orders count         | `132`      |
| `backlog`       | integer     | Open orders not yet fulfilled  | `921`      |
| `avg_discount`  | float (0–1) | Average applied discount rate  | `0.28`     |
| `asp`           | float       | Average selling price per unit | `18450.75` |

**Notes**

* Used primarily by **Demand Agent**.
* High `orders` + high `avg_discount` typically drives margin RCA.
* `orders` ≠ `shipped_units` (see shipments).

---

## `supply_fact.csv`

| Column                | Type        | Description                   | Example   |
| --------------------- | ----------- | ----------------------------- | --------- |
| `month`               | string      | Reporting month               | `2025-08` |
| `region`              | string      | Geographic region             | `APAC`    |
| `bu`                  | string      | Business unit                 | `Core`    |
| `product_line`        | string      | Product family                | `Gamma`   |
| `otif`                | float (0–1) | On-time-in-full delivery rate | `0.74`    |
| `lead_time_days`      | integer     | Average delivery lead time    | `31`      |
| `stockouts`           | integer     | Count of stockout events      | `8`       |
| `backorders`          | integer     | Unfulfilled confirmed orders  | `19`      |
| `supplier_delay_days` | float       | Avg supplier-caused delay     | `7.4`     |

**Notes**

* Used by **Supply Agent**.
* Declining `otif` + rising `lead_time_days` → revenue deferral risk.

---

## `shipments_fact.csv`

| Column             | Type        | Description            | Example   |
| ------------------ | ----------- | ---------------------- | --------- |
| `month`            | string      | Reporting month        | `2025-08` |
| `region`           | string      | Geographic region      | `APAC`    |
| `bu`               | string      | Business unit          | `Growth`  |
| `product_line`     | string      | Product family         | `Gamma`   |
| `shipped_units`    | integer     | Units actually shipped | `642`     |
| `fulfillment_rate` | float (0–1) | % of demand fulfilled  | `0.71`    |

**Notes**

* Bridges **supply → revenue recognition**.
* Low `fulfillment_rate` with healthy orders indicates deferral, not demand loss.

---

## `fx_fact.csv`

| Column     | Type   | Description             | Example   |
| ---------- | ------ | ----------------------- | --------- |
| `month`    | string | Reporting month         | `2025-11` |
| `region`   | string | Region affected by FX   | `EMEA`    |
| `pair`     | string | FX pair vs USD          | `EURUSD`  |
| `avg_rate` | float  | Average monthly FX rate | `1.1423`  |

**Notes**

* Used by **Pricing / FX Agent**.
* FX impacts *reported* revenue, not local operational performance.

---

## `events_log.csv`

| Column         | Type                | Description                | Example                                |
| -------------- | ------------------- | -------------------------- | -------------------------------------- |
| `date`         | string (YYYY-MM-DD) | Event occurrence date      | `2025-08-06`                           |
| `month`        | string              | Reporting month affected   | `2025-08`                              |
| `region`       | string | blank      | Region impacted            | `APAC`                                 |
| `bu`           | string | blank      | Business unit impacted     | `Growth`                               |
| `product_line` | string | blank      | Product line impacted      | `Gamma`                                |
| `type`         | string              | Event category             | `supplier_issue`                       |
| `summary`      | string              | Human-readable description | `Supplier delays increased lead times` |

**Notes**

* Intended as **supporting context only**.
* Should never override quantitative evidence.
* Useful for HITL explanations and executive summaries.

---

## Modeling & Agent Design Notes (important)

* **Primary RCA axis**:
  `finance_fact.metric = revenue | gross_margin | opex`
* **Drivers**:

  * Demand → `orders_fact`
  * Supply → `supply_fact` + `shipments_fact`
  * Pricing → `avg_discount`, `asp`
  * FX → `fx_fact`
  * One-time effects → `events_log`
* **Correct RCA answers often require joining 3–4 tables**.

-

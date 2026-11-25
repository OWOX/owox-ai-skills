# Forecast method

How the page turns OWOX values into a 12-month unit-economics forecast. `config.md` (section Forecast) has the config keys; this file says what they mean.

## Who computes what

| Kind | What it is | Where it comes from |
|---|---|---|
| **Fact** | A value OWOX returned: a field, or a series summed over months | `field`, `series` baselines |
| **Assumption** | A baseline the page computes from Facts by a fixed rule the engine implements | `ratio`, `cohort_curve`, `seasonality` baselines; each carries `suggest`, the calculated field that would make it a Fact |
| **Your input** | A number the user gave in their own words | `input` baselines, with `quote` |
| **Estimate** | The forecast itself, computed in the page from the baselines and the levers | the model below |

You never put a number into the config, except the user's own figure in an `input`. You may recompute a baseline yourself once while probing, to sanity-check it and to compare it with a calculated field later; that number never goes into the config.

This is a narrow exception to the dashboard rule "never divide two queries in the page": it applies to baselines only, each such baseline is labelled Assumption with a `!` next to it, and each carries the calculated field that would replace it. Prefer a calculated field whenever one exists: then the baseline is a `field` and a Fact.

## Window and anchor

- **Anchor**: the last complete day of the revenue Data Mart (`MAX` of its date; a day from today on is still being written).
- **Window**: the last 12 full months before the anchor's month, cut to the last full month of the *earliest* source in `source_dates` (ad spend often lags orders by days). Every baseline reads the same window.
- The anchor's own month is partial: left out of every baseline, shown on the chart as hatched Fact.
- **Horizon**: from the month after the anchor's month; 12 months, or through December of next year.

Queries: `trailing` (24 months to the anchor for series, so seasonality has two years and the anchor month shows; `months: 12` for a total over the window itself) and `cohort` (36 months to the anchor on both the acquisition and the order date, about 666 cells, under the 1,000-row limit).

## Baselines

| Baseline | Fact when | Otherwise |
|---|---|---|
| Revenue by month | a revenue field (required) | — |
| Ad spend by month | a spend field | no spend: the forecast covers existing customers only, no budget or CAC lever |
| New customers by month | a count by a valid acquisition date | no fallback: without a valid date the curve falls back (below) |
| Blended CAC | a CAC field | `ratio`: Σ spend ÷ Σ new customers over the window. Blended: organic customers are priced in |
| Revenue curve per new customer | a cohort Data Mart | `cohort_curve` |
| Seasonality of spend, of revenue | — | `seasonality` |
| Gross margin | a margin field (check its description: a margin already net of marketing is not usable, since spend is subtracted separately) | `ratio` of profit to revenue fields, or Your input |
| Fixed costs per month | — | Your input, or left out (operating profit is then contribution) |

### Acquisition date

A cohort curve is only as good as its acquisition date. A registration date often is not one: customers registered in 2026 with orders from 2024. While probing, run the cohort query and reject the field if any cohort has revenue in a month before its acquisition month. The page repeats the check on every load. When no field passes, the curve falls back to `no_curve`, and step 7 suggests a "First Order Date" (a SQL Data Mart with each customer's first order, joined to the orders Data Mart on the customer id).

### `cohort_curve`

- Cohort sizes come from the new-customers series; it must count by the same acquisition field as the cohort query.
- Development factors: cumulative revenue per customer at age k+1 ÷ at age k, over the cohorts seen at both ages, weighted by size. Ages only old cohorts reach no longer skew the curve.
- Ages after the last one seen by 3 or more cohorts take the mean of the last three measured ages (1+).
- Customers acquired inside the loaded range follow the curve at their age. Customers acquired before it keep their window revenue times their own ratio of the window to the 12 months before it. The partial anchor-month cohort is scaled to a full month.
- A cohort query that hits 1,000 rows falls back to `no_curve`.

### `no_curve`

First month = average order value (an `aov` field baseline). Later months = (window revenue − new customers × average order value) ÷ 12 ÷ customers with an order in the window (a `customer_base` field baseline). Existing customers keep the window's repeat revenue, times revenue seasonality.

### `seasonality`

Each calendar month's value over the 24 months to the window's end ÷ its centred 12-month moving average, normalised to mean 1. Fewer than 24 months: every month weighs the same, and the page says so.

## The model (Estimate)

For each horizon month t = 1…H:

- budget_t = B × s_spend(t) ÷ Σ s_spend. B is the budget lever: the horizon's total.
- CAC_t moves in a straight line from the baseline at t = 1 to the lever's target at t = H. So do first-month revenue, gross margin and fixed costs. Repeat revenue (per new customer, months 2–12, in money) and existing customers' monthly revenue are set in money and act as multipliers on the curve's ages 1+ and on existing customers' revenue, ramping from 1.
- N_t = budget_t ÷ CAC_t new customers.
- newRev_t = Σ_{j ≤ t} N_j × r(t − j).
- revenue_t = existing customers' revenue_t + newRev_t; gross profit = revenue × margin.
- operating profit_t = gross profit − budget − fixed costs; cumulative cash is its running sum; peak cash need = max(0, −lowest cumulative cash).

Scenarios: a viewer saves the current lever targets under a name; they are stored in the page's shared storage (`scenarios/<their id>`), visible to everyone who can open the page, and applying one sets the levers (clamped to today's ranges). Download writes the levers, the monthly forecast and the baselines to a CSV. Neither goes into OWOX.

Lever ranges are the engine's own: half to double the baseline; margin 0–100%; fixed costs from 0 to double (or to half of existing customers' monthly revenue when the user left them out, so the lever is there to try). Positions stay in each viewer's browser; Reset returns to the baselines. The config never sets a target or a range.

Blended CAC overstates how new customers scale with budget: at zero budget the model wins no one. Say so in the notes.

## Calculated fields (step 7)

Offer one table, one row per Assumption: Data Mart, field name, formula, description, level (`metric` for a ratio). On the user's yes, per field:

1. `get_data_mart_setup` on that Data Mart.
2. `update_data_mart_schema` with the **complete** schema plus the new field (`calculated: { formula, level }`; refer to fields as `{{ref field="x"}}`, to joined fields as `{{ref path="alias" field="x"}}`). The call replaces the whole schema: never send only the new field.
3. `validate_data_mart`.
4. Query the new field over the window and compare it with your probe value. Within 1%: go on. Otherwise stop and explain the gap (usually a join that fans out).
5. Switch the baseline to `field`, rebuild, republish to the same artifact.

A ratio across two Data Marts (CAC: spend and customers) usually needs a SQL Data Mart that reads both by month; propose it, and create it only on the user's yes. When the user cannot edit the Data Mart, hand them the text for its Data Owner.

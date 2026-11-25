# Config reference

`scripts/build_page.py` validates this shape and injects it into the engine. `examples/demo-ecommerce.json` is a complete, working example.

## Top level

| Key | Required | What |
|---|---|---|
| `title` | yes | The page name: a short noun phrase ("Sales plan vs fact"), no explanation after a dash. |
| `kicker`, `lede` | no | Small line above the title; one sentence under it. |
| `connector` | yes | The OWOX connector's display name exactly as the user's client shows it. |
| `project` | yes | `{ "id", "title" }` from `get_project_context`. The page warns a viewer whose connector is signed in to another project. |
| `app_url` | no | Default `https://app.owox.com`. |
| `currency`, `locale`, `time_zone` | no | Defaults `USD`, `en-US`, `UTC`. Freshness times are shown in `time_zone`. |
| `periods` | no | `{ "default": "ytd" }`. Leave `options` out to get the full switcher from `method.md`; set it only when the user asks for fewer periods. `compare`: `previous` (the period before: the month before, the quarter before, the 28 days before) or `last_year` (the same period last year); leave it out for each period's own comparison. The page also has a **Compare with** switch next to the period. |
| `primary_metric` | recommended | The metric the business is run by (from the Project description). Drivers of it say so; other metrics convert to it only through `to_primary`. |
| `summary_metrics` | no | Metric ids for the sentence summary at the top. |
| `anchor` | when any query has a date (`range` or `window`) | `{ "query": <static query id>, "value": <column with the max date, e.g. "order_date \| MAX"> }`. |
| `queries` | yes | Map of query id → query (below). |
| `metrics` | yes | Map of metric id → metric (below). |
| `pages` | yes | `[{ "title", "components": [...] }]`. More than one page shows tabs. |
| `improvements` | no | What the project could add to get more from this dashboard: sentences, or `{ text, data_mart_id, field }` with a link into OWOX. Shown under About these numbers. |
| `theme` | no | Colors, fonts and `logo` (`{ file, alt, scale }` or `false`; default the OWOX app icon). See `design.md`. |
| `cache_hours` | no | Default 12. Opens within this time show the viewer's own copy of the last load (browser storage, that viewer only) instead of querying; Refresh data always reads OWOX. `0` queries on every open. |
| `export` | no | Default on, and keep it on: every scorecard and chart block gets an **Export to Google Sheets** icon (on hover) that exports the queries behind it, with the period on screen, as OWOX Reports, one spreadsheet per block and one tab per query. With no Google Sheets destination the page offers to connect one (`add_destination` → the viewer signs in to Google on OWOX's page → Done). Set `false` only when the user asks; `"export": false` on a component removes it there. |
| `max_parallel_queries` | no | Default 4. The page sends at most this many OWOX calls at once and queues the rest; claude.ai rejects a burst of 20+ parallel connector calls from one viewer with `upstream_error`. Refresh re-runs every query through the same queue. After a failed call the queue pauses about 4 s, goes on two at a time and widens again after a few answers; a failed read is sent once more, 5–8 s later. Only a second failure shows on the block, as a one-line note with Retry (failed queries only). |

## Query

```json
"rev_daily": {
  "label": "Settled revenue by order day · Purchases + Orders",
  "data_mart_id": "…",
  "scope": "range",
  "date_field": "orders_e_commerce__order_date",
  "input": { "fields": [...], "aggregations": [...], "date_buckets": [...], "sort": [...], "limit": 1000 }
}
```

- `input` is exactly the `query_data_mart` arguments **without** `data_mart_id` and without the period filter; the page adds `{ field: date_field, operator: "between", value: { from, to } }` to `filters`.
- `date_field` may be a joined field (filters apply after the join).
- `label` is shown in the run log; name the Data Marts it reads.
- `as_of: true` (window queries only): the page filters both periods to their last day, so OWOX returns a level as it stood then. Required for a `snapshot` metric's `window` and for breakdowns of a snapshot.

## Metric

```json
"conversion": {
  "label": "Conversion rate", "short": "Conversion",
  "format": "percent", "kind": "ratio", "direction": "up",
  "about": "One or two plain sentences: what it counts and how.",
  "window": { "query": "sessions_window", "value": "conversion_rate" },
  "series": { "query": "sessions_monthly", "date": "date", "value": "conversion_rate" },
  "plan":   { "query": "plan_product", "date": "date", "numerator": ["orders"], "denominator": ["sessions"] },
  "target": { "value": 0.028, "horizon": "period", "label": "Product context" },
  "sources": [
    { "role": "Fact", "data_mart_id": "…", "title": "Sessions", "fields": [{ "name": "conversion_rate", "label": "Conversion Rate" }] },
    { "role": "Date · joined", "data_mart_id": "…", "title": "Orders", "via": "joined to Purchases on order_id", "fields": [...] },
    { "role": "Target", "text": "Product context: 2.8% of sessions ending in an order." }
  ]
}
```

- `to_primary` (optional): `{ "multiply": [metric ids] }`: a driver's change times those metrics' current values, shown as an Estimate in the key metric's unit. Only for a formula that is plain arithmetic of the business (paid sessions × conversion × order value); otherwise leave it out.
- `kind`: `additive` (default; adds up over days), `ratio` (OWOX computes it per period) or `snapshot` (a level at a date: ARR, active customers; `window` on an `as_of` query, `series` by `DAY` for the trend; never summed, no forecast).
- `format`: `currency`, `number`, `percent` (a fraction: 0.028 → 2.8%), `ratio` (two decimals), `decimal`.
- Additive metrics need `series` (a `range` query by `DAY`). Ratios need `window` and usually `series` (by `MONTH`). A project without dates uses `static: { query, value }`: one value, no comparison.
- `value` and `date` are column names as `column_metadata[].name` returns them; an aggregated column is `field | SUM`, and a `COUNT_DISTINCT` comes back as `field | COUNTUNIQUE`.
- `plan`: a `static` query on the plan Data Mart (no filter, `limit` 1000), `date` its date column (text `YYYY-MM-DD` is fine), and either `value` (additive: summed over the period's days) or `numerator` and `denominator` (lists of columns summed over the period, `"-col"` subtracts; e.g. completion = `["orders", "-cancelled_orders", "-returned_orders"]` ÷ `["orders"]`). `grain: "month"` for a plan with one row per month. `cumulative: true` for a running-total plan (one row per day, additive metrics only): a period's plan is the value on its last day less the value the day before it starts. A `snapshot` metric's plan has `value` only: the planned level, read on the period's last day.
- `sources[].fields[].name` is the field's name **in its own Data Mart** (for a joined field, the part after the last `__`), so its link opens the right field: `app.owox.com/ui/<project>/data-marts/<id>/data-setup?field=<name>`.

## Components

Every component takes `id` (needed when another component refers to it), `title`, `span` (2, 3, 4 or 6 of a six-column grid; default 6), `description` (one line) and `tags` (`Fact`, `Estimate`, `AI calc`, `Hypothesis`). Every block shows a collapsed **Source** with its Data Marts, fields and join paths, and a link to the run that loaded it.

| `type` | Keys | Shows |
|---|---|---|
| `scorecards` | `metrics: [ids]` | One card per metric: fact, change, plan and variance, target and gap, forecast, sparkline, status border. |
| `plan_vs_fact` | `metric`, `mode`: `monthly` or `cumulative` | This year by month against plan (dashed), last year (muted) and the month or full-year forecast. Bars for additive metrics, lines for ratios. |
| `trend` | `metric` | A ratio by month over the loaded range, with its target. |
| `breakdown` | `query` (window; `static` for a snapshot without dates), `dimension`, `dimension_label`, `value`, `metric`, `top`, `sources`; `ratio: true` for a rate (never ranked or bridged); `target_value` for a per-value target column (drawn as a dashed tick) | Bars by dimension value: this period and the comparison, change in %. Several breakdowns may share one query (e.g. spend and clicks by platform). |
| `waterfall` | `from` (a breakdown id), `top` | Comparison total → each value's change → this period's total. |
| `drivers` | `from: [breakdown ids]`, `top`, `code`, `playbook` (optional) | The values that moved the metric most, as collapsible cards, whose "What to do" and "What to check" Claude writes from the live numbers (set top-level `"ask_claude": false` to use only the playbook). `playbook[<breakdown id>].up/down = { do: [..], check: [..] }`. |
| `table` | `from` (a breakdown id) | Sortable table: this period, comparison, change, change %, share. |
| `notes` | `items: [text]` | Plain rules and data-quality notes, shown in the `data` block (or under About these numbers when there is none). |
| `data` | — | The Data tab: Data Marts per tab (from every block's Source), freshness of what has loaded, notes, and `improvements`. |

## Forecast

Used by the `owox-forecast` skill; a dashboard config has no `forecast` section. `references/forecast.md` in that skill explains the method.

```json
"forecast": {
  "horizon": "next_12_months",
  "source_dates": [{ "query": "spend_last", "value": "date | MAX" }],
  "baselines": {
    "revenue":       { "op": "series", "label": "Net revenue", "query": "revenue_monthly", "date": "orders__order_date", "value": "line_net_revenue | SUM" },
    "spend":         { "op": "series", "label": "Ad spend", "query": "spend_monthly", "date": "date", "value": "spend | SUM" },
    "new_customers": { "op": "series", "label": "New customers", "query": "new_customers_monthly", "date": "first_order_date", "value": "customer_key | COUNT" },
    "cac":           { "op": "ratio", "label": "Blended CAC", "numerator": "spend", "denominator": "new_customers", "suggest": { "data_mart_id": "…", "name": "…", "formula": "…", "description": "…" } },
    "curve":         { "op": "cohort_curve", "label": "Revenue per new customer by month", "query": "cohort_revenue", "sizes": "new_customers", "suggest": { … } },
    "season_spend":  { "op": "seasonality", "label": "Spend seasonality", "of": "spend" },
    "margin":        { "op": "input", "label": "Gross margin", "value": 0.4, "source": "user answer", "quote": "our gross margin is about 40%" },
    "fixed_costs":   { "op": "input", "label": "Fixed costs per month", "value": null, "source": "user answer", "quote": "" }
  },
  "levers": ["budget", "cac", "first_month_revenue", "repeat", "existing", "margin", "fixed_costs"]
}
```

| Key | What |
|---|---|
| `horizon` | `next_12_months` or `through_next_december`, counted from the month after the anchor. |
| `source_dates` | Static `MAX` queries of each source whose data may end before the anchor (ad spend). The window ends at the earliest source's last full month. |
| `baselines` | Each `{ op, label, format?, … }` (`format` as for metrics; the page knows the usual keys, set it for any other field). `op`: `series` (a 24-month `trailing` query by `MONTH`: `date`, `value`), `field` (one value: `query`, `value`), `ratio` (`numerator` ÷ `denominator`, two baseline keys), `cohort_curve` (a `cohort` query; `sizes` names the new-customers series, counted by the same acquisition field), `seasonality` (`of`: a series), `input` (`value` a number or null, `source: "user answer"`, `quote`: the user's words). `ratio` and `cohort_curve` need `suggest`: the calculated field that would make them a Fact. Keys the page reads: `revenue` (required), `spend`, `new_customers`, `cac`, `margin`, `fixed_costs`, `aov` and `customer_base` (first order value and customer base when there is no valid acquisition date). |
| `levers` | Which levers the page shows, in this order: `budget` (the horizon's total), `cac`, `first_month_revenue`, `repeat` (revenue per new customer over months 2–12, in money), `existing` (monthly revenue from customers you already have), `margin`, `fixed_costs` (shown from 0 when the user left them out). Their ranges come from the engine, never from the config. |

Queries: `scope: "trailing"` takes `date_field` and `months` (24, a monthly series to the anchor; 12, the window itself). `scope: "cohort"` takes `acquired_field` and `ordered_field`, both bucketed by `MONTH`, `limit: 1000`. The page adds the date filters; a forecast query's own filters carry business rules only, never a number or a date.

`build_page.py` rejects a number in a baseline (other than an `input`'s value), a number or date in a forecast query's filter, and any key that sets a lever target or range; it warns about figures quoted in prose.

Components: `forecast_levers`, `forecast_cards`, `forecast_chart`, `forecast_assumptions`. Their Source lists the Data Marts the baselines read. Tags: `Assumption` (computed in the page from OWOX values by a fixed rule; a calculated field would make it a Fact) and `Your input` (a value the user gave; OWOX does not hold it), next to `Fact` and `Estimate`.

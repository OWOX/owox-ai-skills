# Method: how numbers become a dashboard

These rules come from dashboards built with OWOX customers. The engine already implements the arithmetic; your job is to give it the right queries and to label everything honestly.

## Periods and the anchor

- **Anchor**: the last complete day with rows in the primary Data Mart. The config names a `static` query that returns the `MAX` of that date; the page treats a max of today (or later) as partial and reads through yesterday.
- **Periods** (the page's switcher; each has its comparison):
  - `ytd` — Jan 1 → anchor vs Jan 1 last year → the same date last year (default).
  - `last_365_days` — anchor−364 → anchor vs the 365 days before.
  - `last_28_days`, `last_7_days` — vs the 28 or 7 days before.
  - `last_week` — the last full Mon–Sun week vs the week before it.
  - `last_month`, `last_quarter` — the last full calendar month or quarter vs the same one last year.
  - `last_year` — the last full calendar year vs the year before.
  - **Compare with** (a second switch next to the period): *the period before* (the month before, the quarter before, the 28 days before) or *the same period last year*, for every period except year to date, which always compares with last year. Set the opening choice with `periods.compare` when the user asks for it (e.g. "last month vs the month before").
  - Month to date is not a switcher option: it drives the month forecast only (`mtd` stays available if a user asks for it).
- The page loads daily rows from Jan 1 two years before the anchor's year, one call per calendar year (a daily range passes the 1,000-row limit otherwise), so every period and its comparison come from the same few calls.

## Query shapes (the config's `scope`)

| Scope | What it is | Date filter | Use for |
|---|---|---|---|
| `static` | Runs as written | none | anchor (`MAX` of the date), plan Data Marts |
| `range` | A time series over the loaded range | the page adds `between` [range start, anchor] on `date_field` | additive metrics by `DAY` (sums per period in the page); ratios by `MONTH` (trend lines, sparklines) |
| `window` | One answer per period | the page adds `between` for the period, then again for the comparison | ratios over the whole period; breakdowns by a dimension |
| `window` with `as_of: true` | The value on the period's last day | the page adds `between` [last day, last day] for the period and for the comparison | snapshots (ARR, active customers) and their breakdowns |

## When the model is thin

Build from what exists; never guess what is missing.

| Missing | Build | Tell the user (step 6) |
|---|---|---|
| Project description, contexts | Metrics the user picks from the Data Marts' own fields | Write a description and a context per team |
| Plan | Status against the comparison period; no plan lines | A plan Data Mart named in a context |
| Joins | Breakdowns only by the Data Mart's own fields | The join and its key |
| Calculated field for a ratio | Leave the ratio out (never divide two queries in the page) | The calculated field |
| Field or Data Mart descriptions | Labels from field names, said in the notes | Descriptions |
| How a metric adds up over time (a level, a running-total plan): allowed aggregations cover rows, not days | Ask the user; build with the answer | Describe it on the field: "ARR: level on the date, never summed over days" |
| Any date field | A snapshot: `static` queries, scorecards with `static` metrics, breakdowns on `static` queries, no anchor, no periods, no trends | The date field |

## Metric rules

- A metric exists only if a Data Mart defines it or this method tells you how to derive it. Never invent one.
- **Additive** (`kind: "additive"`): sums, counts of entities that fall in exactly one day (orders by order date). The page sums the daily OWOX values for each period; label such totals "OWOX values, summed in the page".
- **Ratio** (`kind: "ratio"`): rates, ROAS, CPC, margins, averages. Read with a `window` query so OWOX computes it over the whole period, and with a monthly `range` query for the trend. Never sum or average a ratio across buckets.
- **Snapshot** (`kind: "snapshot"`): a level at a date: ARR, MRR, active customers, a balance, stock. Never summed over days. The scorecard reads a `window` query with `as_of: true`, so OWOX returns the value on the period's last day (and on the comparison's last day); a daily `range` query gives the trend, where each month shows its last loaded day. Its breakdowns use `as_of` window queries too. No forecast. Which metrics are snapshots is the data model's to say. A field's allowed aggregations cover aggregation across rows (ARR may be summed across customers), not across days, so read the field's description; when it does not say, ask, and put the missing description into `improvements` (e.g. "ARR: the level on the date; sum across customers, never across days").
- Prefer a calculated metric field over rebuilding it from parts. Pass on its `usage` caveat (e.g. "reads Orders through a join") in the block's description or the notes.
- Use `COUNT_DISTINCT` or a Data Mart's own Unique Count field for unique entities; never count raw rows yourself.
- `direction`: `up` unless the target says lower is better (CPC, cost, churn, returns).

## Plan, targets and status

- **Plan**: only from a Data Mart a context or the Project description names as the plan, usually one row per day (or per month). A period's plan sums the plan's days in it (monthly plans are pro-rated by days). A ratio's plan is numerator ÷ denominator of planned sums, exactly as the plan Data Mart's description says; a daily planned rate is never summed or averaged. A plan stored as a running total (`plan.cumulative: true`, one row per day) is read, not summed: a period's plan is its value on the last day less its value the day before the period starts (0 before the plan begins). A snapshot's plan is the planned level on the period's last day.
- **Target**: a constant taken from a context's text, with the context named in `sources` (`{ "role": "Target", "text": "…" }`). `horizon: "period"` when the target applies to any period (a rate), `"year"` when it is an annual total. Never infer a horizon the text does not state.
- **Variance** = fact − plan. **Change** = this period − comparison. **Gap** = target − fact (annual: target − full-year forecast).
- **Status**, one rule everywhere: against plan if there is one, else against a period target, else against the comparison. Green at or above it (in the metric's direction), amber under it by less than 20%, red 20% or more, grey when not measurable.
- **Forecasts** (labelled Estimate): full year = YTD + last year's remaining days × (YTD ÷ YTD last year); month = month to date ÷ days elapsed × days in month.

## Breakdowns and drivers

- One dimension per breakdown, from the base Data Mart or a joined one. Blank values show as "Unattributed".
- Two to four breakdowns per tab; each costs two calls when its tab is first opened.
- **Drivers** appear on the Overview (for the key metric) and on every context tab (for that tab's breakdowns). Only additive breakdowns drive them; a rate breakdown (`ratio: true`) is shown but never ranked or bridged, because rates do not add up across values. They rank the dimension values whose metric moved most, in the metric's own unit, across the listed breakdowns. Each card's body has four parts: **What happened** (Fact: the value in both periods), **Why it matters** (Estimate: its share of the period's change, the metric against plan for the period, the full-year forecast against the year's plan), **What to do** (two recommendations) and **What to check** (two hypotheses). The first two are computed from the same numbers; the last two Claude writes, below. Nothing is typed into the page, so nothing goes stale.
- **Dig deeper**: each driver card has a magnifier that copies a ready prompt (the finding, both periods, the Data Marts and joins behind it, and the task: split the change into volume, rate and value, go one dimension deeper, explain 80% of it, test the hypotheses with numbers). The viewer pastes it into a Claude chat with the OWOX connector, which can query further than the page.
- **Recommendations and checks** (default, `sample` capability): when the drivers tab has its data, the page sends one request to Claude with every driver's numbers, the headline numbers and each breakdown's biggest moves, and fills "What to do" and "What to check" for all cards, tagged Hypothesis. A new period, a refresh or a new data day changes the numbers and so the request: the text is rewritten, never stored. The viewer's claude.ai asks once to allow Claude for the page; it runs on the viewer's own Claude usage.
- **Playbook** (optional, for clients without `sample`): "What to do" / "What to check" text per breakdown and direction, two items each, tagged Hypothesis. Base it on the project's description and contexts; never on numbers you saw while building.

## Sparklines and status

- A sparkline shows the metric by month over the loaded range, the plan dashed. Its colour says where the line itself is heading: the last three full months against the three before, green in the metric's good direction, red against it, grey when it moved under 1%.
- A scorecard's status (On track, Slightly behind, Behind, No comparison) is a coloured stripe on top of the card.

## Data quality

- If a query comes back `truncated`, raise `limit` or narrow it before publishing.
- Tracking breaks, partial days, excluded rows and join caveats named in descriptions go into the `notes` block, in plain words.
- A target whose metric no Data Mart holds is "not measurable": leave it out of scorecards and say so in the notes. Never show a proxy as the metric.

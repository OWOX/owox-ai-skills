---
name: owox-dashboard
description: Build a live, refreshable dashboard over the user's OWOX Data Marts — plan vs fact, KPI scorecards, trends, drivers — that colleagues can open and refresh with their own OWOX access. Use when someone connected to OWOX asks for a dashboard, scorecard, KPI page, plan vs fact, business review, morning review of sales or marketing, or wants "a page I can refresh" from their OWOX data. Asks up to four questions first, discovers the project's data model through the OWOX MCP server, and publishes a claude.ai artifact whose numbers are re-read through the viewer's own connector on every open and on Refresh.
---

# OWOX dashboard

You build a dashboard page that reads OWOX Data Marts live. The page is a fixed engine (`assets/dashboard.html`) plus a JSON config you write. You never hand-write chart code and never paste numbers into the page: every number comes from a `query_data_mart` call the page makes on the viewer's own OWOX connector.

Work in this order. Do not skip the questions, and do not publish a query you have not run once yourself.

**Any OWOX project qualifies.** Many have no Project description, no contexts, no plan, no field descriptions, or Data Marts that are not joined. Build the best dashboard the project's data allows, say plainly what that leaves out, and show the user what to add to get more (step 6). Never refuse because the model is thin, and never fill a gap with guesses.

## 1. Read the project (no questions yet)

Use the OWOX tools on the connector the user means (if several OWOX connectors are connected, ask which project).

1. `get_project_context` — project id and title, the Project description: business, key metrics, currency, rules, and whether it names a **design system** (a link, a brand guide, colors or fonts). An empty description is fine: note it as a gap.
2. `list_contexts` — each context's goal, its **plan** (a plan Data Mart and the critical number and leading metrics it plans) or, failing that, a **target** written as text (value, horizon, the fields it is measured on), and the Data Marts it links. No contexts is fine: note it as a gap and work from the Data Marts.
3. `get_relevant_data_marts_by_prompt` with the user's request (and the context ids, when there are contexts). With no contexts or a vague request, `summarize_data_catalog` shows what the project holds; `list_data_marts` only to browse.
4. Keep a short list of **model gaps** as you read: no Project description; no contexts; no plan; Data Marts without descriptions or with undescribed fields; Data Marts that should be joined but are not (two Data Marts sharing a key such as `order_id` or `customer_id`, with no join between them); ratios the business needs that exist only as two raw fields (no calculated field); no date field on a Data Mart that tracks activity; a level (ARR, active customers, a balance) or a running-total plan whose description does not say so. Step 6 turns it into advice.
5. Note the OWOX connector's **display name** exactly as claude.ai shows it in Settings → Connectors. The page addresses the connector by that name, and a published page can only reach claude.ai connectors. In Claude Code the plugin's own `owox-data-marts` server answers in chat, but the page must name the claude.ai connector: load the `artifact-capabilities` skill, whose connector list maps each `mcp__<id>__` prefix to its claude.ai name (load `artifact-design` too before publishing). If the user has OWOX only in Claude Code, ask them to add OWOX in claude.ai Settings → Connectors first.

## 2. Ask up to four questions in one message

Ask them together, each with concrete options taken from what you just read, at most four options each (the client's question tool takes four questions of four options; when there are more contexts than options, group related ones, such as "Marketing + Advertising"). Keep each to one line plus options.

1. **What should this dashboard help you decide?** Offer the contexts with their critical number and plan (e.g. "Sales: revenue vs its plan", "Marketing: ROAS vs its plan"), a text target when a context has no plan; with no contexts, offer the main metrics the Data Marts hold (e.g. "Revenue and orders from Orders", "Spend and clicks from Ads"). Always add **"Not sure: build a business review"**: many users do not know which question to ask, and this option means you take the project's key metric from the Project description (or the most central Data Mart) and every context that has a plan, without asking further. Multi-select.
2. **What should it make you notice?** The breakdowns the data allows (channel, category, country, segment: native fields, or joined ones when joins exist), thresholds, anything to leave out (e.g. "exclude test orders"). Multi-select.
3. **Which period opens by default?** Year to date vs last year (recommended), last 28 days vs the 28 before, last full month vs the same month last year, last full quarter. Every other period stays in the page's switcher. Say what plan data you found: "plan from Data Mart X", "targets only, from the contexts", or "no plan found".
4. **Design.** If the Project description names a design system, use it and ask only to confirm: "I'll use <name>; OK?". Otherwise ask for the company website, never for a design system: "What's your company website? I'll take your colors, fonts and logo from it. Or reply *default* for the OWOX look." No answer, or *default*: the OWOX look with the OWOX app icon.

Who will open it (only the user, or colleagues) is a fifth question only when the request does not say; otherwise assume colleagues and explain access in the hand-over. If the user answers only some, use the defaults for the rest and say so in one line.

**Rules the user states are model knowledge.** When an answer contains a business rule ("don't count test orders", "take ROAS from the advertising Data Mart, never recompute it"), apply it in the queries and offer once: "This rule belongs in the Project description or the field's description, so every answer follows it. Want me to draft the text for your Data Owner?" Never edit project settings yourself.

## 3. Lay out the tabs, then choose the data

**Tabs:** **Overview** first (the key metric and each chosen context's critical number as scorecards, the key metric's plan vs fact, and the Top 5 drivers of the key metric); then **one tab per chosen context** (its critical number and leading metrics as scorecards, its plan vs fact and trends, its breakdowns, and its own top drivers); **Data** last (a `data` block: which Data Marts feed each tab, freshness, notes, and "Get more from this dashboard"). Without contexts, make one tab per topic the Data Marts cover (sales, marketing, product). Each tab's queries run only when a viewer first opens it, so tabs cost nothing until used.

**Key metric:** set `primary_metric` to the number the business is run by (the Project description's key metric, else the first one the user picked). Drivers of it say so; drivers of other metrics stay in their own unit, and convert to the key metric only through an explicit, unambiguous `to_primary` formula (e.g. change in paid sessions × conversion × order value), shown as an Estimate. When no such formula is plain, do not convert.

## 3b. Choose the data — reuse the data model

Read `references/method.md` before this step. In short:

- `get_data_mart_details_by_id` for every Data Mart you use; `detail_level: with_joined_fields` when a dimension or date lives in a joined Data Mart. Copy field names exactly.
- **Reuse joins the Data Owner defined.** Slice the base Data Mart by joined fields (channel through Sessions → Traffic Sources, category through Products → Product Category) instead of querying separate Data Marts and matching them yourself. Name the join path in each block's Source.
- **How each metric behaves over time is the data model's to say, not yours.** Every query encodes it: summing a field over a period assumes it adds up over days. Read it from the model: every field's `allowedAggregations` (from `get_data_mart_details_by_id`) and the field's and the Data Mart's descriptions. Never request an aggregation a field does not allow, and never sum a field in the page whose `allowedAggregations` has no SUM. Allowed aggregations say how a field may be aggregated across rows, not across days: ARR is summed across customers on one day but never across days, so a description has to say that. A level at a date (ARR, MRR, active customers, a balance, stock) is a `snapshot`: OWOX reads it on the period's last day, never summed over days. A plan stored as a running total ("cumulative from Oct 1") is `cumulative`. When the descriptions do not say, ask the user in one line ("Does ARR add up over days, or is it the level on a date?"), write the answer into the config, and add the missing description to the model gaps. Never decide it from the field's name alone.
- **Prefer calculated metric fields** (`calculated.level = "metric"`): select them as they are. Ratios (rates, ROAS, CPC, margins) are always read per period from OWOX, never averaged across months or rebuilt from parts.
- **Plan** comes only from a Data Mart a context or the description names as the plan (often one row per day). An additive plan sums its days, a cumulative plan is read at the period's ends, a snapshot's plan is the planned level on the period's last day; a ratio's plan is the ratio of planned sums the plan Data Mart's description gives (planned orders ÷ planned sessions), never a sum or mean of daily rates. **Targets** written only as text in a context become constants with their source quoted. Never invent a target or its horizon.
- **Budget.** A tab's queries run when it is first opened (a query shared with an opened tab runs once). A daily series costs 3 calls (one per calendar year), a monthly series 1, a window query 2 (period and comparison), a plan Data Mart 1, a breakdown 2; the first open adds the anchor and 1 project check. Keep the Overview near 30 calls and each other tab under about 10; `build_page.py` prints the count per tab. Each call is a billed MCP Query Run, and the page sends four at a time (claude.ai rejects bigger bursts), so more calls also mean a slower first paint. When the user picks more than fits, keep their choice, say what it costs, and offer the trim.
- **A ratio across two Data Marts** (average order value from Purchases ÷ Orders) has no OWOX field to read: leave it out, say so in the notes, and suggest the Data Owner add it as a calculated field. Never divide two queries in the page and call it the metric.

## 4. Probe, then write the config

1. Run every query once with `query_data_mart`, with the same input the page will send, at most three or four at a time (bigger bursts fail with "server isn't responding"). Add the date filter the page would add, for a small sample: a daily `range` query over the last full month; a monthly `range` query over its full range; a `window` query over year to date; a plan query with `limit: 31` (read `totals` for the whole plan). Check the column names in `column_metadata` (an aggregated field is named `field | SUM`), the row count against `limit`, and that the numbers are plausible. Fix and re-run anything wrong.
   Then check how far back each daily Data Mart goes: one `MIN` of its date field. The page loads from Jan 1 two years back; a Data Mart that starts later shows no comparison for the oldest periods, which belongs in the notes.
2. Find the anchor: `MAX` of the primary Data Mart's date field (a `static` query). The page reads through the last complete day. A Data Mart whose data ends earlier (ad spend loaded weekly) undercounts the last days against the anchor: say so in the notes.
3. Write the config by `references/config.md`. **Every chart gets Export to Google Sheets**: scorecards, plan vs fact, trends, breakdowns, waterfalls, tables and drivers all carry the icon by default; never set `export: false` unless the user asks for it. Start from `examples/demo-ecommerce.json`; change everything project-specific. Save it where the user can find it again (a folder `owox-dashboards/<project>-<slug>/` inside the current working folder; the logo file, if any, goes into the same folder) and say where in the hand-over: later changes start from that file. Every block gets: a title, a one-line description with Fact / Estimate / AI calc / Hypothesis tags, and `sources` listing each Data Mart with its fields and the join path (`via`).
4. Apply the design: `references/design.md` (default tokens, or tokens taken from the user's design system or website).

## 5. Build and publish

1. `python3 scripts/build_page.py config.json dashboard.html` — validates the config and prints the capabilities declaration. Fix every reported problem.
2. Publish `dashboard.html` as an artifact with exactly the printed `capabilities` (connector display name; tools `query_data_mart` and `get_project_context`, plus `list_destinations`, `add_destination`, `add_report`, `update_report`, `run_report` and `get_report_run_status` for each block's **Export to Google Sheets**; `db` for the shared run log, `user` for names in it, `sample` when the page has drivers: Claude writes each driver's two recommendations and two checks from the numbers on screen whenever they change, on the viewer's own Claude usage). In Claude Code / the Claude app: the Artifact tool with `file_path`, `icon: "chart"` and those `capabilities`. In claude.ai chat: Code execution and file creation must be on; run the script in the sandbox and publish the built file as the artifact, declaring the same connector tools. If the chat cannot publish the page with its connector tools, say so and ask the user to build it from the Claude desktop app or Claude Code with this plugin; never paste a page without them, because it would show no data.
3. Do not render-loop. Tell the user, in plain words:
   - what the page shows and which period it opens on;
   - that the first open loads only the first tab (N query runs, from the build output's `calls_when_a_tab_is_first_opened`), each other tab loads when first opened, and **Refresh data** re-reads the tabs already opened, with a counter under the button (`6 s (3/14 runs)`), all through *their own* connector; later opens within 12 hours show the viewer's own copy from their browser, marked with its time, until they press Refresh data;
   - that the Google Sheets icon on every chart (on hover) exports the data behind it as OWOX Reports into one spreadsheet, through the viewer's own Google Sheets destination; a viewer without one connects their Google account from the page in two clicks (OWOX's "Connect Google Sheets" page, then Done); the reports stay in the project and the next export of that block updates them. If claude.ai blocks it, the viewer sets `add_destination`, `add_report` and `update_report` to **Always allow** for the OWOX connector;
   - what they assumed or could not measure;
   - how to share it: Share → **General access: Anyone at <organization>** (or add people) with the role **Contributor**. Every role reads the data through the viewer's own OWOX connector, Viewer included; Contributor also lets their opens and refreshes join the shared run log (a Viewer's runs stay in their own browser). Never Editor: an Editor can republish the page. A colleague needs the OWOX connector **with the same name**, signed in to the **same project**, and access to the Data Marts listed under each block's Source; blocks they cannot read show why, the rest still render. People outside the organization see no live data, and pages that read connectors cannot use "Anyone with the link";
   - if a viewer sees "needs your approval": set `query_data_mart` to **Always allow** for the OWOX connector in claude.ai Settings → Connectors, because claude.ai does not let artifacts call tools that ask for approval on every call.

## 6. Show the user how to get more

Close the hand-over with **"Get more from this dashboard"**: at most five concrete steps from your model-gap list, each naming the Data Mart or context, what to add, and what it unlocks on this dashboard. For example:

- "Write a plan for revenue (a Data Mart with a date and a planned value per day or month) and name it in a context: the cards then show plan vs fact and on-track status."
- "Join Orders to Sessions on `session_id`: revenue can then be broken down by channel."
- "Add a calculated field ROAS (revenue ÷ spend) to the advertising Data Mart: the page then reads it for any period instead of leaving it out."
- "Describe the fields of Leads and write a Project description (what the business sells, the number it is run by, its currency): every answer, not only this page, gets better."
- "Add a context per team with its goal: the next dashboard asks fewer questions and picks the right Data Marts."

Put the same list into the config's `improvements` (each `{ "text", "data_mart_id", "field" }`, the link optional): the page shows it under **About these numbers → Get more from this dashboard**, where Data Owners find it. These steps are done in OWOX by a Data Owner; offer to draft the descriptions or the plan layout, and never change the project yourself.

## Changing a dashboard later

Open the saved config, edit, rebuild, publish to the same artifact (same file path, or its `url`). Re-run any query you changed. Keep the title and icon.

## Never

- Paste rows or numbers from your own calls into the page or the config.
- Query Data Marts outside the user's request, or personal fields (emails, names) nobody asked for.
- Show a ratio averaged across months, a level (snapshot) summed over days, a metric no Data Mart defines, or a target nobody wrote.
- Shorten "Data Mart" to "mart" in anything the user reads.

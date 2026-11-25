---
name: owox-forecast
description: Build a live unit-economics forecast over the user's OWOX Data Marts — next year's revenue, new customers, CAC, operating profit and the cash growth needs — with levers the reader moves on the page. Use when someone connected to OWOX asks for a forecast, unit economics, CAC payback, next year's ad budget, how much cash growth needs, or "what happens if we spend more on ads". Asks up to four questions, reads the project's data model through the OWOX MCP server, and publishes a claude.ai artifact that reads OWOX live through the viewer's own connector; every baseline is a Fact from OWOX or a labelled Assumption the page computes, never a number the model typed.
---

# OWOX forecast

You build a forecast page that reads OWOX Data Marts live. The page is the same engine as `owox-dashboard` (`assets/dashboard.html`) plus a JSON config with a `forecast` section. You never hand-write chart code and never type a number into the page: baselines are OWOX fields or fixed operations on them, the forecast is computed in the page from those baselines and the levers.

Read `references/forecast.md` before step 1: windows, baselines, the model, the labels. Work in this order. Do not skip the questions, and do not publish a query you have not run once yourself.

## 0. Check the plugin is complete

This skill's folder must hold `assets/dashboard.html` and `scripts/build_page.py`. If either is missing, stop and tell the user how to update the plugin:

- **claude.ai**: Customize → Plugins → OWOX → **Update** (an organization's plugin: its Owner uploads the current version from https://github.com/OWOX/owox-ai-skills).
- **Claude Code**: `/plugin update owox@owox`, then start a new session.

Never offer to build the page by hand.

## 1. Read the project, as an analyst

1. `get_project_context`, `list_contexts`.
2. `get_relevant_data_marts_by_prompt` for each input: revenue (orders, order lines), ad spend, new customers (a first-order or acquisition date), margin (profit, cost of goods), average order value. `get_data_mart_details_by_id` for every Data Mart you use, `with_joined_fields` when a date lives in a joined Data Mart. Copy field names exactly.
3. Map each baseline of `references/forecast.md` to a **Fact** (a field, ideally a calculated field) or an **Assumption** (a fixed operation on Facts). You choose which field counts as "new customer" and "spend" — ad spend and acquisition counts are trusted inputs; do not ask the user, show the choice in step 5.
4. Note the gaps: no valid acquisition date, no margin field, no spend, ratios that exist only as two raw fields.
5. Note the OWOX connector's display name exactly as claude.ai shows it (Settings → Connectors). In Claude Code, load the `artifact-capabilities` skill to map the `mcp__<id>__` prefix to that name.

## 2. Ask up to four questions, the first one alone

Ask question 1 and wait. Then ask the rest together. Plain words, no abbreviations in options.

1. **What should this forecast help you decide?** "Next year's ad budget", "Whether new customers pay back what they cost", "How much cash growth needs before it pays off", "Not sure: full unit economics". It sets the summary's lead and the chart's default line.
2. **Horizon**: "Next 12 months" or "Through December <next year>".
3. **Costs OWOX does not hold**: gross margin, only when no usable margin field exists; fixed costs per month ("Leave fixed costs out", "I'll type them"). Never offer a made-up figure. A figure the user types becomes an `input` with their words in `quote`.
4. **Design**: as `owox-dashboard` — the Project description's design system, else the company website, else *default* for the OWOX look (`references/design.md`).

If spend and revenue are in different currencies, stop and ask which one to use. Never convert.

## 3. Probe

Run every query once with `query_data_mart`, with the filters the page will add (three or four at a time): the anchor and each source's `MAX` date; each `trailing` query over its 24 months (12 for a window total); the `cohort` query over 36 months on both dates. Check:

- column names (`field | SUM` for an aggregate) and that no answer is truncated;
- the acquisition date: no cohort has revenue before its acquisition month (`references/forecast.md`);
- currencies, and the margin field's description (a margin net of marketing is not usable);
- the baselines are plausible: recompute CAC, margin and first-month revenue yourself once. Keep these numbers for step 7; never write them into the config.

## 4. Write, build, publish

1. Write the config by `references/config.md` (section Forecast), starting from `examples/demo-stand-forecast.json`. One Forecast tab (levers, cards, chart, assumptions) and the Data tab. Every Assumption baseline carries `suggest`. Tell the user in one line where you save it: `./owox-forecasts/<project>-<slug>/config.json`, inside the current working folder.
2. `python3 scripts/build_page.py config.json forecast.html`. Fix every reported problem; reword any prose the build warns about (the page shows numbers, the text does not repeat them).
3. Publish `forecast.html` as an artifact with exactly the printed `capabilities` (`icon: "chart"`). In claude.ai chat, Code execution must be on. If the chat cannot publish with connector tools, say so; never paste a page without them.

## 5. Present it as an analyst

In plain words:

- what the page shows and for which horizon; the first open costs N query runs (`calls_when_a_tab_is_first_opened`), each a billed MCP Query Run on the viewer's own connector;
- which baselines are Facts, which are Assumptions and how each is computed (the `!` next to it says the same), which fields you chose as "new customer" and "spend", and the mode (cohort curve, or first order value plus repeat revenue and why);
- what the levers do and that their positions stay in each viewer's browser;
- sharing, as `owox-dashboard`: Share → Anyone at <organization> with the role Contributor; viewers need the same OWOX connector signed in to the same project; set `query_data_mart` to Always allow.

## 6. Iterate

Change the config, rebuild, publish to the same artifact. Re-run any query you changed.

## 7. When the user is satisfied: make the Assumptions Facts

Offer the calculated fields in one table: Data Mart, field name, formula, description, level. Write nothing without an explicit yes. On yes, follow `references/forecast.md` (Calculated fields): read the setup, update the complete schema, validate, compare with your step 3 value within 1%, switch the baseline to `field`, rebuild, republish. A field that spans two Data Marts usually needs a SQL Data Mart: propose it, create it only on yes. If the user cannot edit that Data Mart, give them the text for its Data Owner.

## Never

- Build the page without `assets/dashboard.html`, or write chart code yourself.
- Put a number into a baseline. Only an `input` holds a figure, and only the user's, with their words.
- Divide two queries outside a declared baseline, or show a baseline without its Fact / Assumption / Your input label.
- Set lever targets or ranges in the config.
- Write a calculated field, change a schema or create a Data Mart without the user's yes.
- Shorten "Data Mart" to "mart" in anything the user reads.

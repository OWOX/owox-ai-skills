"""Build an OWOX dashboard page from a JSON config.

Usage:
    python3 build_page.py config.json out.html

Checks the config against the engine's contract, injects it into assets/dashboard.html,
and prints the capabilities declaration the page needs when it is published as an artifact.
Exits 1 and lists every problem when the config is not valid.
"""
import base64
import html
import json
import re
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent / "assets" / "dashboard.html"
DEFAULT_LOGO = Path(__file__).resolve().parent.parent / "assets" / "owox-app-icon.svg"
LOGO_TYPES = {".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif"}
UNSAFE_SVG = re.compile(r"<script|<foreignObject|\son[a-z]+\s*=|javascript:", re.I)
# The engine links its default font stylesheet and preconnects to the font host first; a theme may link
# another stylesheet from that same host.
FONTS_LINK = re.compile(r'<link rel="stylesheet" href="[^"]*">')
FONT_HOST = re.search(r'<link rel="preconnect" href="([^"]+)">', ENGINE.read_text()).group(1)
SCOPES = {"static", "range", "window", "trailing", "cohort"}
FORECAST_TYPES = {"forecast_levers", "forecast_cards", "forecast_chart", "forecast_assumptions"}
COMPONENT_TYPES = {"scorecards", "plan_vs_fact", "trend", "breakdown", "waterfall", "drivers", "table", "notes", "data"} | FORECAST_TYPES
BASELINE_OPS = {"field", "series", "ratio", "cohort_curve", "seasonality", "input"}
LEVERS = {"budget", "cac", "first_month_revenue", "repeat", "existing", "margin", "fixed_costs"}
HORIZONS = {"next_12_months", "through_next_december"}
FORECAST_KEYS = {"horizon", "source_dates", "baselines", "levers"}
DATE_LITERAL = re.compile(r"^\d{4}-\d{2}(-\d{2})?")
PROSE_FIGURE = re.compile(r"[$€£]\s?\d|\d+(\.\d+)?\s?%")
FORMATS = {"currency", "number", "percent", "ratio", "decimal"}
PERIODS = {"ytd", "mtd", "last_7_days", "last_28_days", "last_365_days", "last_week", "last_month", "last_quarter", "last_year"}
# owox.com reading mode, used only when a dashboard opts in to follow the viewer's light theme.
OWOX_LIGHT = {
    "--bg-page": "#f5f7fb", "--bg-elevated": "#ffffff", "--bg-surface": "#ffffff", "--bg-nested": "#edf1f8",
    "--border-quiet": "#e2e8f1", "--border-default": "#d1d9e6", "--border-strong": "#b4bfd1", "--border-hover": "#b4bfd1",
    "--text-primary": "#1a1f2e", "--text-secondary": "#42506b", "--text-muted": "#5e6b85", "--text-decor": "#7c8aa3",
    "--text-link": "#0b63b8", "--key-figure": "#0b63b8", "--focus-ring": "#0b63b8",
    "--metric": "#0b63b8", "--metric-2": "#8929e3", "--plan": "#1a1f2e", "--prior": "#b4bfd1", "--grid-line": "rgba(209,217,230,.6)",
    "--ok": "#14713c", "--warn": "#7c5e03", "--bad": "#c60e0e", "--idle": "#7c8aa3",
    "--cta-fill": "#0b63b8", "--cta-ink": "#ffffff",
}
TOKEN = re.compile(r"^--[a-z0-9-]+$")
CSS_VALUE = re.compile(r"^[#(),.%\w\s\"'-]+$")


CONFIG_DIR = Path(".")


def logo_path(name):
    """A logo file sits in the config's own folder; any other location is refused."""
    path = (CONFIG_DIR / Path(name).name).resolve()
    return path if Path(name).name == name else None


def validate(cfg):
    errs = []
    need = lambda cond, msg: cond or errs.append(msg)
    need(cfg.get("connector"), "connector: the OWOX connector's display name is required")
    proj = cfg.get("project") or {}
    need(proj.get("id") and proj.get("title"), "project: id and title from get_project_context are required")
    queries = cfg.get("queries") or {}
    metrics = cfg.get("metrics") or {}
    need(queries, "queries: at least one query is required")
    for qid, q in queries.items():
        need(q.get("data_mart_id"), f"queries.{qid}: data_mart_id is required")
        inp = q.get("input") or {}
        need(inp.get("fields"), f"queries.{qid}: input.fields is required")
        need("data_mart_id" not in inp, f"queries.{qid}: put data_mart_id next to input, not inside it")
        scope = q.get("scope", "static")
        need(scope in SCOPES, f"queries.{qid}: scope must be one of {sorted(SCOPES)}")
        if scope in ("range", "window", "trailing"):
            need(q.get("date_field"), f"queries.{qid}: scope {scope} needs date_field (the field the page filters by period)")
        month_bucket = lambda f: any(b.get("field") == f and b.get("unit") == "MONTH" for b in (inp.get("date_buckets") or []))
        if scope == "trailing":
            need(q.get("months", 24) in (12, 24), f"queries.{qid}: a trailing query reads 12 or 24 full months (months: 12 | 24)")
            if q.get("months", 24) == 24:
                need(month_bucket(q.get("date_field")), f"queries.{qid}: a 24-month trailing query is a monthly series: bucket date_field by MONTH")
        if scope == "cohort":
            for k in ("acquired_field", "ordered_field"):
                need(q.get(k) and month_bucket(q.get(k)), f"queries.{qid}: a cohort query needs {k}, bucketed by MONTH")
            need(inp.get("limit") == 1000, f"queries.{qid}: a cohort query reads up to 36 × 36 cells; set limit to 1000")
        need(not q.get("as_of") or scope == "window", f"queries.{qid}: as_of (read the period's last day only) applies to window queries")
        if scope == "range":
            buckets = inp.get("date_buckets") or []
            need(buckets, f"queries.{qid}: a range query is a time series: bucket its date field by DAY (additive) or MONTH (ratio)")
        lim = inp.get("limit", 20)
        need(isinstance(lim, int) and 1 <= lim <= 1000, f"queries.{qid}: limit must be 1-1000 (default 20 is usually too low)")
        daily = any(b.get("unit") == "DAY" for b in (inp.get("date_buckets") or []))
        if scope == "range" and daily and lim < 366:
            errs.append(f"queries.{qid}: a daily range is read one calendar year per call; set limit to 1000")
    anchor = cfg.get("anchor") or {}
    dated = any(q.get("scope", "static") in ("range", "window", "trailing", "cohort") for q in queries.values())
    if dated or anchor:
        need(anchor.get("query") in queries, "anchor.query must name a query (the MAX of the primary Data Mart's date); a dashboard without dates uses static queries only")
    if anchor.get("query") in queries:
        need(queries[anchor["query"]].get("scope", "static") == "static", "anchor query must be static")
        need(anchor.get("value"), "anchor.value: the column holding the max date, e.g. 'order_date | MAX'")

    def check_ref(where, ref, scopes):
        if not ref:
            return
        q = queries.get(ref.get("query"))
        if not q:
            errs.append(f"{where}.query '{ref.get('query')}' is not a query")
            return
        need(q.get("scope", "static") in scopes, f"{where}: query '{ref['query']}' must have scope in {scopes}")

    for mid, m in metrics.items():
        need(m.get("label"), f"metrics.{mid}: label is required")
        need(m.get("format", "number") in FORMATS, f"metrics.{mid}: format must be one of {sorted(FORMATS)}")
        kind = m.get("kind", "additive")
        need(kind in ("additive", "ratio", "snapshot"), f"metrics.{mid}: kind is additive, ratio or snapshot (a level at a date: ARR, customers, a balance)")
        need(m.get("direction", "up") in ("up", "down"), f"metrics.{mid}: direction is up or down")
        need(m.get("series") or m.get("window") or m.get("static"), f"metrics.{mid}: needs series (range query), window (window query) or static (one value, no dates)")
        check_ref(f"metrics.{mid}.static", m.get("static"), ["static"])
        if m.get("kind") == "ratio" and not m.get("static"):
            need(m.get("window"), f"metrics.{mid}: a ratio needs a window query so OWOX computes it over the whole period")
        if kind == "snapshot" and m.get("window"):
            wq = queries.get(m["window"].get("query")) or {}
            need(wq.get("as_of"), f"metrics.{mid}: a snapshot's window query needs \"as_of\": true, so OWOX returns the value on the period's last day instead of a sum over its days")
        check_ref(f"metrics.{mid}.series", m.get("series"), ["range"])
        check_ref(f"metrics.{mid}.window", m.get("window"), ["window"])
        check_ref(f"metrics.{mid}.plan", m.get("plan"), ["static", "range"])
        pl = m.get("plan")
        if pl:
            need(pl.get("date"), f"metrics.{mid}.plan.date is required")
            need(pl.get("value") or (pl.get("numerator") and pl.get("denominator")), f"metrics.{mid}.plan needs value, or numerator and denominator (lists of fields)")
            if kind == "ratio":
                need(pl.get("numerator"), f"metrics.{mid}.plan: a ratio's plan is numerator ÷ denominator of planned sums, never a sum of daily rates")
                need(not pl.get("cumulative"), f"metrics.{mid}.plan: cumulative applies to additive metrics")
            if kind == "snapshot":
                need(pl.get("value") and not pl.get("numerator"), f"metrics.{mid}.plan: a snapshot's plan is the planned level (value) on each date")
                need(not pl.get("cumulative"), f"metrics.{mid}.plan: a snapshot's plan is already read at the period's last day; drop cumulative")
            if pl.get("cumulative"):
                need(pl.get("grain", "day") == "day", f"metrics.{mid}.plan: a cumulative plan needs one row per day (grain day)")
        t = m.get("target")
        if t:
            need(isinstance(t.get("value"), (int, float)), f"metrics.{mid}.target.value must be a number")
            need(t.get("horizon", "period") in ("period", "year"), f"metrics.{mid}.target.horizon is period or year")
        need(m.get("sources"), f"metrics.{mid}: sources (Data Marts and fields behind it) are required")
    need(not cfg.get("primary_metric") or cfg["primary_metric"] in metrics, "primary_metric must name a metric (the project's key metric)")
    for mid, m in metrics.items():
        for f in ((m.get("to_primary") or {}).get("multiply") or []):
            need(f in metrics, f"metrics.{mid}.to_primary.multiply: '{f}' is not a metric")
    for x in cfg.get("improvements", []):
        need(isinstance(x, (str, dict)) and (isinstance(x, str) or x.get("text")), "improvements: each item is a sentence, or { text, data_mart_id?, field? }")
    for s in cfg.get("summary_metrics", []):
        need(s in metrics, f"summary_metrics: '{s}' is not a metric")
    opts = (cfg.get("periods") or {}).get("options") or []
    for p in opts:
        need(p in PERIODS, f"periods.options: unknown period '{p}'")
    cmp = (cfg.get("periods") or {}).get("compare")
    need(cmp in (None, "previous", "last_year"), "periods.compare: previous (the period before) or last_year (the same period last year); leave it out for each period's own comparison")
    pages = cfg.get("pages") or []
    need(pages, "pages: at least one page is required")
    ids = {}
    for pi, p in enumerate(pages):
        for ci, c in enumerate(p.get("components") or []):
            cid = c.get("id") or f"{p.get('id') or p.get('title')}-{ci}"
            ids[cid] = c
    for cid, c in ids.items():
        t = c.get("type")
        need(t in COMPONENT_TYPES, f"component {cid}: type must be one of {sorted(COMPONENT_TYPES)}")
        if t == "scorecards":
            for mid in c.get("metrics") or []:
                need(mid in metrics, f"component {cid}: metric '{mid}' is not defined")
        if t in ("plan_vs_fact", "trend"):
            need(c.get("metric") in metrics, f"component {cid}: metric is required")
        if t == "breakdown":
            q = queries.get(c.get("query"))
            need(q and q.get("scope", "static") in ("window", "static"), f"component {cid}: breakdown needs a window query (or a static one when no Data Mart has a date)")
            need(c.get("dimension") and c.get("value"), f"component {cid}: dimension and value (column names) are required")
            need(c.get("metric") in metrics or c.get("format"), f"component {cid}: metric or format is required")
            if (metrics.get(c.get("metric")) or {}).get("kind") == "snapshot" and q and q.get("scope") == "window":
                need(q.get("as_of"), f"component {cid}: a breakdown of a snapshot metric needs an as_of window query, or it adds the level up over the period's days")
            need(c.get("sources"), f"component {cid}: sources are required")
        if t in ("waterfall", "table"):
            need(ids.get(c.get("from"), {}).get("type") == "breakdown", f"component {cid}: from must name a breakdown component id")
        if t == "waterfall":
            need(not ids.get(c.get("from"), {}).get("ratio"), f"component {cid}: a rate breakdown has no bridge; use an additive one")
        if t == "drivers":
            for b in c.get("from") or []:
                need(ids.get(b, {}).get("type") == "breakdown", f"component {cid}: '{b}' is not a breakdown component id")
    errs += validate_forecast(cfg, queries, ids)
    theme = cfg.get("theme") or {}
    for mode in ("dark", "light"):
        for k, v in ((theme.get("tokens") or {}).get(mode) or {}).items():
            need(TOKEN.match(k) and CSS_VALUE.match(str(v)), f"theme.tokens.{mode}: bad token {k}: {v}")
    logo = theme.get("logo")
    if isinstance(logo, dict):
        f = logo.get("file")
        lp = logo_path(f) if f else None
        need(lp and lp.is_file(), f"theme.logo.file: '{f}' is not a file in the config's folder; download the logo there first")
        need(not f or Path(f).suffix.lower() in LOGO_TYPES, f"theme.logo.file must be one of {sorted(LOGO_TYPES)}")
        if lp and lp.is_file():
            need(lp.stat().st_size <= 300_000, "theme.logo.file is over 300 KB; use an SVG or a smaller PNG")
            if lp.suffix.lower() == ".svg":
                need(not UNSAFE_SVG.search(lp.read_text(errors="ignore")), "theme.logo.file: the SVG holds scripts or event handlers; use a clean SVG or a PNG")
    else:
        need(logo in (None, False), "theme.logo is an object { file, alt, scale } or false")
    fonts = theme.get("fonts_css")
    need(not fonts or fonts.startswith(FONT_HOST + "/"), "theme.fonts_css must be a Google Fonts stylesheet URL")
    return errs


def forecast_queries(cfg):
    """Every query a forecast section reads: the baselines' queries and the source dates."""
    fc = cfg.get("forecast") or {}
    out = {b.get("query") for b in (fc.get("baselines") or {}).values() if isinstance(b, dict) and b.get("query")}
    out |= {s.get("query") for s in (fc.get("source_dates") or []) if isinstance(s, dict) and s.get("query")}
    return out


def validate_forecast(cfg, queries, comps):
    """The forecast section: operations and field names only, never a number the model computed."""
    errs = []
    need = lambda cond, msg: cond or errs.append(msg)
    fc = cfg.get("forecast")
    blocks = [cid for cid, c in comps.items() if c.get("type") in FORECAST_TYPES]
    if not fc:
        need(not blocks, f"components {blocks}: forecast blocks need a top-level forecast section")
        return errs
    need(blocks, "forecast: the section needs at least one forecast block (forecast_levers, forecast_cards, forecast_chart, forecast_assumptions)")
    for k in fc:
        need(k in FORECAST_KEYS, f"forecast.{k}: not a forecast key; lever targets and bounds are never set in the config (the page derives them from the baselines)")
    need(fc.get("horizon") in HORIZONS, f"forecast.horizon must be one of {sorted(HORIZONS)}")
    for s in fc.get("source_dates") or []:
        q = queries.get((s or {}).get("query"))
        need(q and q.get("scope", "static") == "static" and s.get("value"), "forecast.source_dates: each item is { query: <static MAX query>, value: <its column> }")
    bl = fc.get("baselines") or {}

    def numbers(v, path):
        if isinstance(v, bool):
            return
        if isinstance(v, (int, float)):
            errs.append(f"forecast.baselines.{path}: a number in a baseline; the page computes baselines from OWOX values, only an input holds a user's number")
        elif isinstance(v, dict):
            for k, x in v.items():
                numbers(x, f"{path}.{k}")
        elif isinstance(v, list):
            for i, x in enumerate(v):
                numbers(x, f"{path}[{i}]")

    def q_of(key, b, scopes):
        q = queries.get(b.get("query"))
        need(q, f"forecast.baselines.{key}.query '{b.get('query')}' is not a query")
        if q:
            need(q.get("scope", "static") in scopes, f"forecast.baselines.{key}: query '{b['query']}' must have scope in {scopes}")
        return q or {}

    def suggest(key, b):
        sg = b.get("suggest") or {}
        need(all(sg.get(k) for k in ("data_mart_id", "name", "formula", "description")),
             f"forecast.baselines.{key}: an Assumption needs suggest {{ data_mart_id, name, formula, description }}: the calculated field that would replace it")

    for key, b in bl.items():
        if not isinstance(b, dict):
            errs.append(f"forecast.baselines.{key}: must be an object")
            continue
        op = b.get("op")
        need(op in BASELINE_OPS, f"forecast.baselines.{key}: op must be one of {sorted(BASELINE_OPS)}")
        need(b.get("label"), f"forecast.baselines.{key}: label is required")
        need(b.get("format") in (None, *FORMATS), f"forecast.baselines.{key}: format must be one of {sorted(FORMATS)}")
        if op == "input":
            v = b.get("value")
            need(v is None or (isinstance(v, (int, float)) and not isinstance(v, bool)), f"forecast.baselines.{key}: input value is a number or null")
            need(b.get("source") == "user answer", f"forecast.baselines.{key}: an input's source is \"user answer\"; the model never supplies one")
            need(v is None or str(b.get("quote") or "").strip(), f"forecast.baselines.{key}: an input with a value needs the user's own words in quote")
            numbers({k: x for k, x in b.items() if k != "value"}, key)
            continue
        numbers(b, key)
        if op == "field":
            q = q_of(key, b, ["trailing"])
            need(not q or q.get("months") == 12, f"forecast.baselines.{key}: a field is read over the window: its query is trailing with months: 12 (a 24-month query's first row is the oldest month)")
            need(b.get("value"), f"forecast.baselines.{key}: value (the column) is required")
        elif op == "series":
            q = q_of(key, b, ["trailing"])
            need(q.get("months", 24) == 24, f"forecast.baselines.{key}: a series reads a 24-month trailing query")
            need(b.get("date") and b.get("value"), f"forecast.baselines.{key}: date and value (columns) are required")
            need(not q or b.get("date") in ((q.get("input") or {}).get("fields") or []), f"forecast.baselines.{key}: date '{b.get('date')}' is not a field of its query")
        elif op == "ratio":
            for k in ("numerator", "denominator"):
                need((bl.get(b.get(k)) or {}).get("op") in ("series", "field"), f"forecast.baselines.{key}.{k} must name a series or field baseline")
            suggest(key, b)
        elif op == "cohort_curve":
            q = q_of(key, b, ["cohort"])
            sizes = bl.get(b.get("sizes")) or {}
            need(sizes.get("op") == "series", f"forecast.baselines.{key}.sizes must name the new-customers series baseline")
            base = lambda f: str(f or "").split("__")[-1]
            need(not q or not sizes or base(q.get("acquired_field")) == base(sizes.get("date")),
                 f"forecast.baselines.{key}: the cohort query's acquired_field '{q.get('acquired_field')}' and the new-customers date '{sizes.get('date')}' must be the same acquisition field")
            suggest(key, b)
        elif op == "seasonality":
            need((bl.get(b.get("of")) or {}).get("op") == "series", f"forecast.baselines.{key}.of must name a series baseline")
    need((bl.get("revenue") or {}).get("op") == "series", "forecast.baselines.revenue: a revenue series is required")
    if any(isinstance(b, dict) and b.get("op") == "cohort_curve" for b in bl.values()):
        need((bl.get("aov") or {}).get("op") in ("field", "ratio") and (bl.get("customer_base") or {}).get("op") == "field",
             "forecast.baselines: a cohort_curve needs aov (average order value) and customer_base (customers with an order in the window) for the page to fall back on when the acquisition date fails")
    levers = fc.get("levers") or []
    if not (isinstance(levers, list) and all(isinstance(x, str) for x in levers)):
        errs.append(f"forecast.levers: a list of lever names {sorted(LEVERS)}; targets and ranges are never set in the config")
        levers = []
    for lv in levers:
        need(lv in LEVERS, f"forecast.levers: unknown lever '{lv}' (one of {sorted(LEVERS)})")
    for qid in forecast_queries(cfg):
        for f in ((queries.get(qid) or {}).get("input") or {}).get("filters") or []:
            vals = f.get("value")
            vals = list(vals.values()) if isinstance(vals, dict) else (vals if isinstance(vals, list) else [vals])
            bad = [v for v in vals if (isinstance(v, (int, float)) and not isinstance(v, bool)) or (isinstance(v, str) and DATE_LITERAL.match(v))]
            need(not bad, f"queries.{qid}: a filter with a number or date literal ({bad}); the page sets the window, filters keep only business rules")
    return errs


def warnings(cfg):
    """Prose that quotes a figure: the page's numbers come from OWOX, the text should not repeat them.
    Forecast configs only: a dashboard's notes legitimately quote thresholds."""
    if not cfg.get("forecast"):
        return []
    texts = [("lede", cfg.get("lede"))]
    for p in cfg.get("pages") or []:
        for c in p.get("components") or []:
            texts.append((f"component {c.get('title') or c.get('type')}.description", c.get("description")))
            texts += [(f"component {c.get('title') or c.get('type')}.items", t) for t in c.get("items") or []]
    texts += [("improvements", x.get("text") if isinstance(x, dict) else x) for x in cfg.get("improvements") or []]
    return [f"{where}: quotes a figure ('{t}'); let the page show numbers" for where, t in texts if isinstance(t, str) and PROSE_FIGURE.search(t)]


def theme_css(theme):
    out = []
    tokens = theme.get("tokens") or {}
    fam = theme.get("font_body"), theme.get("font_mono")
    base = dict(tokens.get("dark") or {})
    if fam[0]:
        base["--font-body"] = f'"{fam[0]}", system-ui, -apple-system, "Segoe UI", sans-serif'
    if fam[1]:
        base["--font-mono"] = f'"{fam[1]}", ui-monospace, SFMono-Regular, Menlo, monospace'
    if theme.get("color_scheme") in ("light", "dark"):
        base["color-scheme"] = theme["color_scheme"]
    if "radius" in theme:
        base["--radius"] = f"{int(theme['radius'])}px"
    if base:
        out.append(":root { " + " ".join(f"{k}: {v};" for k, v in base.items()) + " }")
    if theme.get("follow_viewer"):
        light = dict(OWOX_LIGHT)
        light.update(tokens.get("light") or {})
        decl = " ".join(f"{k}: {v};" for k, v in light.items()) + " color-scheme: light;"
        out.append('@media (prefers-color-scheme: light) { :root:not([data-theme="dark"]) { ' + decl + " } }")
        out.append(':root[data-theme="light"] { ' + decl + " }")
    return "\n".join(out)


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    global CONFIG_DIR
    CONFIG_DIR = Path(sys.argv[1]).resolve().parent
    cfg = json.loads(Path(sys.argv[1]).read_text())
    errs = validate(cfg)
    if errs:
        print("Config is not valid:")
        for e in errs:
            print(" -", e)
        sys.exit(1)
    for w in warnings(cfg):
        print("warning:", w, file=sys.stderr)
    theme = cfg.get("theme") or {}
    logo = theme.get("logo")
    if logo is not False:
        spec = logo if isinstance(logo, dict) else {"alt": "OWOX"}
        path = logo_path(spec["file"]) if isinstance(logo, dict) else DEFAULT_LOGO
        cfg["_logo"] = {"src": f"data:{LOGO_TYPES[path.suffix.lower()]};base64," + base64.b64encode(path.read_bytes()).decode(),
                        "alt": spec.get("alt", ""), "scale": spec.get("scale", 1)}
    page = ENGINE.read_text()
    if theme.get("fonts_css"):
        page = FONTS_LINK.sub(lambda _: f'<link rel="stylesheet" href="{html.escape(theme["fonts_css"])}">', page, count=1)
    blob = json.dumps(cfg, ensure_ascii=False, indent=1).replace("</", "<\\/")
    page = (page.replace("__TITLE__", html.escape(cfg.get("title") or "Dashboard"))
                .replace("__THEME_CSS__", theme_css(theme))
                .replace("__CONFIG__", blob))
    Path(sys.argv[2]).write_text(page)
    caps = {
        "mcp": {"servers": [{"server": cfg["connector"], "tools": ["query_data_mart", "get_project_context"] + ([] if cfg.get("export") is False else ["list_destinations", "add_destination", "add_report", "update_report", "run_report", "get_report_run_status"])}]},
        "db": {"rules": [{"path": "runs", "read": "view", "write": "interact"}]},
        "user": {"scopes": ["profile"]},
    }
    if any(c.get("type") == "drivers" for p in cfg["pages"] for c in p.get("components") or []) and cfg.get("ask_claude", True):
        caps["sample"] = {}
    def n_calls(q):
        if q.get("scope") == "window":
            return 2
        if q.get("scope") in ("trailing", "cohort"):
            return 1
        if q.get("scope") == "range" and any(b.get("unit") == "DAY" for b in (q.get("input") or {}).get("date_buckets") or []):
            return 3  # one call per calendar year: two years back plus this year
        return 1
    calls = sum(n_calls(q) for q in cfg["queries"].values()) + 1
    breakdown = {}
    for q in cfg["queries"].values():
        kind = q.get("scope", "static")
        if kind == "range":
            kind = "daily range" if n_calls(q) == 3 else "monthly range"
        breakdown[kind] = breakdown.get(kind, 0) + n_calls(q)
    breakdown["project check"] = 1
    # Tabs load lazily: what each tab adds when the viewer first opens it (the anchor runs with the first one).
    comps = {}
    for pg in cfg["pages"]:
        for i, c in enumerate(pg.get("components") or []):
            comps[c.get("id") or f"{pg.get('id') or pg.get('title')}-{i}"] = c
    def metric_q(mid, out):
        m = cfg["metrics"].get(mid) or {}
        for r in ("series", "window", "plan", "static"):
            if m.get(r):
                out.add(m[r]["query"])
        for f in ((m.get("to_primary") or {}).get("multiply") or []):
            metric_q(f, out)
    def page_q(pg):
        out = set()
        for c in pg.get("components") or []:
            for mid in c.get("metrics") or []:
                metric_q(mid, out)
            if c.get("metric"):
                metric_q(c["metric"], out)
            bs = [c] if c.get("type") == "breakdown" else [comps.get(x, {}) for x in ([c.get("from")] if isinstance(c.get("from"), str) else (c.get("from") or []))]
            for b in bs:
                if b.get("query"):
                    out.add(b["query"])
                if b.get("metric"):
                    metric_q(b["metric"], out)
        if cfg.get("primary_metric"):
            metric_q(cfg["primary_metric"], out)
        if any(c.get("type") in FORECAST_TYPES for c in pg.get("components") or []):
            out |= forecast_queries(cfg)
        return out
    seen, per_tab = set(), {}
    if cfg.get("anchor"):
        seen.add(cfg["anchor"]["query"])
    first = True
    for pg in cfg["pages"]:
        new = page_q(pg) - seen
        n = sum(n_calls(cfg["queries"][x]) for x in new if x in cfg["queries"])
        if first:
            n += (1 if cfg.get("anchor") else 0) + 1
            first = False
        per_tab[pg.get("title")] = n
        seen |= new
    breakdown["first open (first tab)"] = per_tab[cfg["pages"][0].get("title")]
    print(json.dumps({"page": sys.argv[2], "bytes": len(page.encode()), "query_calls_all_tabs": calls, "calls_by_kind": breakdown, "calls_when_a_tab_is_first_opened": per_tab, "capabilities": caps}, indent=1))


if __name__ == "__main__":
    main()

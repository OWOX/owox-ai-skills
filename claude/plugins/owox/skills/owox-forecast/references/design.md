# Design

The engine ships the owox.com look: dark, Roboto for text, Space Mono for numbers and labels, square corners, 1px lines instead of shadows, a faint cell grid behind the page, Signal Yellow only on the Refresh button. The page stays dark in every viewer theme unless the config sets `"follow_viewer": true`, which adds the owox.com light reading mode. Use the default unless the user gives a design system or a website.

## Where the design comes from, in order

1. The user's own words in this conversation.
2. A design system the Project description names (a link, a brand guide, tokens, colors or fonts written in it).
3. The company website the user gives when you ask. Ask for the website, not for a design system: most users have none, and every user knows their site.
4. The default (no `theme` key at all): the owox.com look with the OWOX app icon.

## Taking a look from a design system or website

1. Read the source: the design system the Project description names, or the website's home page and its main stylesheet (fetch the page, then one CSS file it links), plus its logo file. Do not follow further links.
2. Pick, from what is actually used:
   - **accent**: the main button or link color → `--metric`, `--key-figure`, `--text-link`, `--focus-ring`, `--cta-fill` (and `--cta-ink`: white or black, whichever reads on it);
   - **page and surfaces**: the site's background and card colors → `--bg-page`, `--bg-surface`, `--bg-nested`; borders → `--border-quiet`, `--border-default`, `--border-hover`;
   - **text**: body and secondary text colors → `--text-primary`, `--text-secondary`, `--text-muted`, `--text-decor`;
   - **second series color** → `--metric-2`; muted last-year bars → `--prior`; plan lines → `--plan`;
   - **fonts**: the heading/body family and, if any, a mono or numeric family. Only Google Fonts load in the page: use the family when it is on Google Fonts, otherwise the closest Google font, and say which you substituted;
   - **corner radius** of buttons and cards (`theme.radius`, in px).
3. Write the look the site has. A dark site: `tokens.dark` only. A light site: put its colors in `tokens.dark` anyway (they are the base layer) and add `"color_scheme": "light"`; or keep the base dark and set `"follow_viewer": true` with `tokens.light`, so the page follows the viewer's theme.
4. Check contrast: body text against its background at least 4.5:1, numbers and labels at least 3:1. Keep status colors (`--ok`, `--warn`, `--bad`) clearly green, amber and red in both themes; they are not brand colors.
5. Tell the user in one line which colors and fonts you took from where.

## Logo

The page shows a logo top left, next to the title. Default: the OWOX app icon (`assets/owox-app-icon.svg`, from owox.com/company/logo-signs).

- **The user's logo** comes from where the user points, from the design system, or from their website: the `<link rel="icon">` / `apple-touch-icon` for a square mark, or the header's logo `<img>` or inline `<svg>` for a wordmark. Download that one file into the config's folder (an SVG or a PNG under 300 KB; prefer the version that reads on the page's background) and set `theme.logo = { "file": "<file name>", "alt": "<Company>" }`. `build_page.py` inlines it as a `data:` URI, because artifacts load no images from other hosts, and refuses an SVG that holds scripts or event handlers.
- The logo sits on the title's line, centred on it, as tall as the title's letters; a wide wordmark is capped at about four and a half letters' width. `scale` (0.5–1.5, default 1) makes it smaller or larger.
- `theme.logo: false` shows no logo.
- If you cannot find a logo the user would recognise, keep the default and say so; never draw or approximate one.

## The `theme` key

```json
"theme": {
  "grid": false,
  "logo": { "file": "acme-logo.svg", "alt": "Acme", "scale": 1 },
  "follow_viewer": true,
  "radius": 8,
  "fonts_css": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&family=JetBrains+Mono:wght@400;700&display=swap",
  "font_body": "Inter",
  "font_mono": "JetBrains Mono",
  "tokens": {
    "dark":  { "--bg-page": "#10131a", "--metric": "#4f8cff", "--cta-fill": "#2f6bff" },
    "light": { "--bg-page": "#ffffff", "--metric": "#2457d6", "--cta-fill": "#2457d6" }
  }
}
```

Only the tokens you set change; the rest keep the OWOX defaults. Token values are plain CSS colors (`#hex`, `rgb()`, `rgba()`).

## Layout defaults

- Tabs: **Overview** · one per context · **Data**. Name each context tab after the context.
- On every tab: scorecards first, then plan vs fact (full width) and trends (half width), then the tab's drivers, then its breakdowns with a waterfall and a table.
- The Data tab holds one `data` block; notes and "Get more from this dashboard" appear there.
- Bars for absolute values, lines for ratios. One dimension per chart.

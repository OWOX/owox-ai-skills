# OWOX for Claude

Connects Claude to [OWOX Data Marts](https://www.owox.com) and adds skills that work on top of your published Data Marts. Every number comes from your OWOX project, read as you and within your access.

## What it includes

- **OWOX connector** (`https://mcp.owox.com/mcp`). You sign in to your OWOX project with OAuth. Claude reads your project description, contexts and Data Marts, and runs queries on them.
- **`owox-dashboard` skill.** Asks up to four questions, reads your project's data model, and builds a live dashboard as a claude.ai artifact: scorecards, plan vs fact, trends, breakdowns and top drivers. It works on any project and lists what to add to the project to get more from it.

## Install

Claude Code:

```bash
/plugin install owox --marketplace OWOX/owox-ai-skills
```

claude.ai (web and desktop): Customize → Plugins → Add → Add marketplace → `OWOX/owox-ai-skills`.

## What runs, and what is sent where

- **While building**, Claude runs queries on your Data Marts through the connector, writes a config file, and runs the bundled `scripts/build_page.py` locally or in Claude's code sandbox. The script validates the config and assembles one HTML page. It makes no network calls.
- **The published page** holds no numbers. When a viewer opens it, presses **Refresh data**, or opens a tab, it runs the dashboard's queries through **that viewer's own** OWOX connector. The viewer's browser keeps a copy for 12 hours.
- **Export to Google Sheets** on a chart creates OWOX Reports in your project and runs them through the Google Sheets Destination the viewer picks on every export. A viewer without one connects their own Google Sheets Destination on an OWOX page.
- **Run log.** The page keeps a shared log of who refreshed it and when (claude.ai artifact storage, visible to people who can open the page).
- **Recommendations.** For drivers, Claude writes what to do and what to check from the numbers on screen, on the viewer's own Claude usage.
- The page loads fonts from Google Fonts and nothing else from outside claude.ai.

## Requirements

- A paid Claude plan (Pro, Max, Team or Enterprise) for artifacts that read connectors.
- The OWOX connector in claude.ai Settings → Connectors, signed in to the OWOX project. Set its tools to **Always allow**: claude.ai does not let artifacts call tools that ask for approval on every call.
- In claude.ai chat, turn on **Code execution and file creation**.

Each query is an MCP Query Run on your OWOX project; a dashboard usually runs 20–30 on first open. More: [github.com/OWOX/owox-ai-skills](https://github.com/OWOX/owox-ai-skills).

## License

MIT

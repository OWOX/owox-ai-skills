# OWOX AI skills

Skills for AI assistants that work on top of [OWOX Data Marts](https://www.owox.com) through the OWOX MCP connector (`https://mcp.owox.com/mcp`). Every number they show is read from your published Data Marts, as you, within your access.

| Assistant | Folder | Status |
|---|---|---|
| Claude (claude.ai, Claude desktop, Claude Code) | [`claude/`](claude/) | Available |
| ChatGPT and Codex | `chatgpt/` | Planned |

The assistants run pages and skills differently, so each one gets its own folder.

## Claude: `owox` plugin

The plugin connects Claude to OWOX and adds these skills:

| Skill | What it does |
|---|---|
| [`owox-dashboard`](claude/plugins/owox/skills/owox-dashboard/SKILL.md) | Asks up to four questions, reads your project's data model, and builds a live dashboard: scorecards, plan vs fact, trends, breakdowns, top drivers. Every chart exports to Google Sheets. Colleagues open it and refresh it with their own OWOX access. Works on any project, and tells you what to add to the project to get more. |

### Install

**Claude Code**

```bash
/plugin marketplace add OWOX/owox-ai-skills
/plugin install owox@owox
```

**Claude on the web and desktop (paid plans):** Customize → Plugins → add `OWOX/owox-ai-skills` as a marketplace, or upload `claude/plugins/owox` as a zip. Then add the OWOX connector in Settings → Connectors and sign in to your OWOX project.

### Where it runs

| Where | Builds a dashboard | Opens and refreshes one |
|---|---|---|
| Claude Code, Claude desktop app | Yes, verified | — |
| claude.ai (web, desktop chat) | Not yet verified; needs Code execution and file creation on | Yes, verified with a second account |
| ChatGPT, Codex | Not yet: Claude artifacts do not exist there | No |

A link to this repo alone does not install anything: add it as a plugin marketplace (above), or upload the plugin folder as a zip.

### What a dashboard needs

- The OWOX connector in claude.ai (Settings → Connectors), signed in to the OWOX project. Dashboards are claude.ai artifacts and read data only through claude.ai connectors.
- Published Data Marts in that project. A plan, contexts, joins and descriptions make the dashboard richer; the skill builds without them and says what to add.

### Sharing a dashboard

Share it with your organization as **Contributor**. Each viewer reads the data through their own OWOX connector, so a colleague needs:

- the OWOX connector **under the same name** as yours, signed in to the same project;
- access to the Data Marts each block lists under **Source**: a block they cannot read says so, and the rest still works.

Never give Editor access: an Editor can republish the page. People outside your organization see no live data, and these pages cannot be shared by public link.

### What it costs

The first open and every **Refresh data** click run the dashboard's queries (MCP Query Runs on your OWOX project, usually 20–30 per dashboard). Later opens within 12 hours show your own copy from your browser until you refresh. Exporting a chart creates OWOX Reports and runs them once (Report Runs).

If claude.ai blocks a call with "needs your approval", set the OWOX connector's tools to **Always allow** in Settings → Connectors: claude.ai does not let artifacts call tools that ask for approval on every call.

## License

[MIT](LICENSE)

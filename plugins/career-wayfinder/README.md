# career-wayfinder

A Claude Cowork plugin: a proactive career guide for recent grads who don't know what they want yet. Adapted from Wayfinder (map, fog, one question at a time, the human's answers stay the human's) and from the AI Safety Atlas outreach approach (map a field, find the people, draft outreach in your own voice, send by hand).

Version 0.1.0 · Finn Gane

## What it does

```
setup (folder, Gmail, Exa, documents, head-start file)
  → about-me (stories → signals)  ─┐
  → role rounds / industry rounds ─┼─▶ signals register ─▶ pulls & pushes (3-signal rule)
       (incl. the guide's wildcards)┘
  → scout agents (orgs per industry + wildcard discovery) ─▶ map
  → people-finder agents (early-career people, public sources) ─▶ map
  → reach-out (her template, per-person drafts: Gmail drafts / LinkedIn notes) ─▶ she sends
  → log-it (replies, conversations, referrals, postings) ─▶ signals + map
  → whats-next (the guide's agenda and leverage order) ─▶ next 20 minutes
```

- **A named guide in one long chat.** She names it at setup (default "<her name>'s Career Guide"; a head-start file can set a different default). Its voice is an encouraging, educational career coach (`references/voice.md`). Because she stays in one chat, the files are the memory: every new sitting re-reads `status`, her compass and the voice guide, then reorients her to her goals.
- **Her goals, kept alive.** 2–4 tangible, dated goals she chooses (`workflows/goals.md`, `/my-goals`), progress computed from the map, pace flagged, weekly check-ins. The guide connects activities back to goals without railroading tangents.
- **Onboarding checklist.** 16 steps (plus one optional) that teach one command each, in order. Most tick themselves off from the map. The guide names the next step and its command at every sitting; the map's Home tab shows it.
- **Proactive by design.** Every session opens with the dashboard (`status`) and one recommended move, and closes with an agenda update. The guide keeps its own agenda: wildcards to test, hunches to check, coverage gaps, one question for her.
- **Breadth over depth.** Shotgun targets (15 industries and 15 roles reacted to, 8 scouted, 40 orgs, 30 people, 5 conversations) bias every choice toward breadth until met.
- **Evidence, not guesses.** Every reaction becomes a tagged signal; a quality becomes a known pull or push only at three signals in one direction.
- **Drafts only.** Never sends, connects, applies or books. Public professional information only, every org and person sourced, no constructed emails, no LinkedIn scraping.

## Layout

```
career-wayfinder/
├── .claude-plugin/plugin.json
├── README.md, START-HERE.md
├── agents/
│   ├── scout.md              sonnet; one industry or a wildcard discovery run → finds JSON + report
│   └── people-finder.md      sonnet; 3–4 orgs → early-career people with sources
└── skills/
    ├── career-wayfinder/     engine: SKILL.md (rules, tools, session shape, the guide's agenda)
    │   ├── workflows/        setup, about-me, explore-roles, explore-industries, scout, find-people,
    │   │                     reach-out, log-it, my-map, whats-next
    │   ├── references/       data-model, question-bank, role-universe, industry-universe, wildcards,
    │   │                     research-rules, outreach-guide, connectors
    │   └── scripts/wayfinder.py   stdlib-only store, dashboard, importer, renderer, self-test
    └── start-here, about-me, explore-roles, explore-industries, my-goals, scout, find-people,
        reach-out, log-it, my-map, whats-next   (entry points → engine workflows)
```

Her folder (`Career Wayfinder/`): `START HERE.md`, `Career Map.html` (Home: checklist, to-dos with copyable drafts, goals, the guide's agenda · Map: industries ring, new items glow, growth replay · Organisations: search and filters · People: pipeline · About you) + `My Map.md` (rendered), `About Me/` (documents, profile.md, compass.md), `Outreach/` (template.md, drafts/, linkedin-notes.md), `Conversations/`, `Research/` (reports, finds/), `.wayfinder/map.json` (the store; only the script writes it).

## Engine

`python3 skills/career-wayfinder/scripts/wayfinder.py --help`. Python 3.9+, standard library only. Commands: `init`, `add`, `update`, `signal`, `import`, `find`, `show`, `status`, `session`, `check`, `render`, `export`, `selftest`. Every command except `init` and `selftest` takes `--ws` because Cowork's shell keeps no state.

## Install

Cowork: **Customize › Plugins › Add marketplace**, paste `https://github.com/finn755/career-wayfinder`, then install **Career Wayfinder**. Or upload `career-wayfinder.plugin`.

Claude Code: `/plugin marketplace add finn755/career-wayfinder`, then `/plugin install career-wayfinder@career-wayfinder`. (Built for Cowork; in Claude Code the engine needs `python3` on the machine.)

## Connectors

**Exa** is bundled in `.mcp.json` (`https://mcp.exa.ai/mcp`, keyless and rate-limited); the user clicks Connect on the plugin's Connectors tab, and can later add the signed-in Exa directory connector for higher limits. **Gmail** (drafts only) is added by the user in Settings › Connectors. Without them the guide uses built-in web search and saves email drafts as files. Details in `skills/career-wayfinder/references/connectors.md`.

## Known limits (0.1.0)

- Plugin agents (`scout`, `people-finder`) are untested in a real Cowork session; the workflows fall back to in-session research.
- Multiple-choice reaction rounds assume Cowork's question tool; otherwise one-line replies.
- Scheduled scouting relies on Cowork's `/schedule`, which runs only while the computer is awake and the app is open.
- LinkedIn's connection-note limit (200 characters for many free accounts) may change.

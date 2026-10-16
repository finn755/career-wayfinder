# Scout

Background research that fills the map with organisations. Wide and shallow: many organisations per industry, one line and a source each. Runs while she does something else.

## Pick targets

Run `status`. Choose up to five targets, in this order:

1. Industries rated *drawn* or *curious* that aren't scouted yet.
2. One wildcard discovery run (always include one when the run has room): find industries not yet on the map that hire her skills (see `references/wildcards.md`, "Discovery runs").
3. Agenda items of kind `scout`.
4. Industries attached to roles she rated *drawn*.

Tell her in one line what you're about to explore and roughly how long it takes (a few minutes per industry). In an unattended scheduled run, don't ask; follow **Scheduled runs** below.

## Brief and launch

Read `references/research-rules.md`. For each target, start a **scout** agent (one industry per agent, at most three at once; the scouts run on a small, fast model to save her usage). Each brief must include:

- the industry (name, id, blurb) or "wildcard discovery";
- her conditions from `About Me/compass.md` (location, setting, don't-wants) and her profile in three lines (degree, core skills), with no other personal details;
- organisations already on the map in that industry (`show org --filter industries=<id>`), so the scout skips them;
- the finds path: `<WS>/Research/finds/<today>-<industry-slug>.json`, and the report path `<WS>/Research/<today>-<industry-slug>.md`;
- which search tools exist in this session (Exa tools if connected, else built-in web search).

If agents aren't available, scout in this session one industry at a time with the same rules, and tell her it will take a little longer.

## Import and check

When the scouts finish, import each finds file and mark the industry scouted:

```bash
python3 "<S>" import --ws "<WS>" "<WS>/Research/finds/<file>.json"
python3 "<S>" update industry "<industry>" --ws "<WS>" --set status=scouted
python3 "<S>" check --ws "<WS>"
```

Fix anything `check` reports (usually a missing source: drop the item rather than invent one). Spot-check two organisations per file by opening their source URL; if a scout's facts don't hold up, drop its unverified items and say so.

## Report back

Lead with the count and the best of it, in her terms: "I found 26 organisations across four industries. Six have programmes for new grads. Three are within an hour of you." Then a quick reaction round on the most interesting 6–10 organisations (multiple choice: **Shortlist**, **Maybe later**, **Not for me**), one line each: what they do, why her, where, any new-grad route.

```bash
python3 "<S>" update org "<org>" --ws "<WS>" --set status=shortlisted --set interest=drawn
python3 "<S>" signal --ws "<WS>" --about "<org>" --lift <..> --tags "<qualities: company size, mission, setting...>" --source "org card"
```

Wildcard discovery results come back as new industries (`origin: wildcard`, `interest: unrated`): give her the best two as cards in the next industry round, or now if she's keen.

## Close

Add agenda items: find people at each shortlisted organisation; scout anything the run surfaced but didn't cover. Run `session --note "scout: <industries>, <n> orgs"` (this re-renders the map). Offer the map file: "Your map has filled in. Want to see it?"

## Scheduled runs

She may set up a weekly scheduled task (see `workflows/whats-next.md`). An unattended run:

- runs `status`, picks at most two targets from the order above plus one wildcard discovery run;
- scouts, imports, checks, marks scouted;
- **never** rates anything for her, never shortlists, never finds people's contact routes, never drafts outreach;
- writes `Research/<today>-weekly-digest.md`: what was explored, the five most interesting finds with one line each, wildcards waiting for her reaction, and the one move it recommends for her next session;
- runs `session --note "scheduled scout"`.

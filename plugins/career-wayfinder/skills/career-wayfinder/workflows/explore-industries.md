# Explore industries

Same mechanics as role rounds, aimed at sectors. The guide's main chance to show her parts of the world she didn't know were hiring people like her.

## Build the deck (8 cards)

Run `status` and `show industry`. Never repeat a rated industry. Draw on `references/industry-universe.md`, her profile, industries attached to roles she liked, and starter ideas from a head-start file:

- **3 adjacent**: industries her skills obviously transfer to, spread across very different kinds of employer (big company, government, startup, non-profit).
- **2 from her signals**: industries where her known pulls or hunches are central (if "explaining" pulls, science communication or technical training).
- **2 wildcards** (`references/wildcards.md`): sectors that hire her skills but that she has almost certainly never pictured herself in. Research one fresh each round rather than always using the list: search job postings for her core skills and note which sectors they come from.
- **1 contrast**: a sector deliberately far from everything rated so far.

Card, five lines:

```
**Water treatment and environmental technology**
What it is: companies and utilities that clean, test and monitor water; consultancies that design the systems.
Why you'd be hired: your lab work in water chemistry and measurement is the core of how treatment plants test and clean water.
Entry roles: process chemist, lab analyst, junior technologist, environmental scientist.
Examples to check: <two or three real organisations, named as "examples to verify">
```

Example organisations come from your knowledge and are marked unverified; scouting confirms them with sources.

## Ask and log

Ask exactly as in role rounds (one multiple-choice question per card, or one-line replies; why for at most three). Then for every card:

```bash
python3 "<S>" add industry --ws "<WS>" --json '{"name":"Water treatment and environmental technology","blurb":"<what it is>","why_her":"<why you would be hired>","origin":"guide|wildcard|friend","interest":"drawn|curious|meh|no","status":"to-scout"}'
python3 "<S>" signal --ws "<WS>" --about "Water treatment and environmental technology" --lift <2|1|-1|-2> --tags "<qualities: mission, setting, pace...>" --why "<her words>" --source "industry card"
```

Set `status: to-scout` for *drawn* and *curious*; `fog` for unrated; `parked` for *no*.

## Close

Read back in two lines what changed (`status`). If a wildcard landed, say so with some delight; it's the point of the guide having its own agenda. Add agenda items: scout each new *drawn*/*curious* industry; one fresh wildcard idea for next time. `session --note "industry round: ..."`. Offer to go scouting now ("I can go find organisations in those while you do something else").

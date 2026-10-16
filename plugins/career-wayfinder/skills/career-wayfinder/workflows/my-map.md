# My map

Three things she might mean: show it, read it back, or ask it a question.

## Show it

```bash
python3 "<S>" render --ws "<WS>"
```

Present `Career Map.html` in the chat as a file card she can click (see **Presenting the map** in the main skill); don't point her to the folder. The page is laid out like an app, in the BunkerOS design system, with a sidebar that always shows her goals and five screens:

- **Today**: the one thing worth doing first (with the exact words to say in the chat and a Copy button), her to-dos, the getting-started list, what changed this week, and what the guide is working on.
- **Map**: industries placed closer to her the more they pull her; bigger circles mean more found. Clicking an industry opens its detail beside the map: why it fits, best places to start, and her own words about it. "Replay how it grew" animates the map's growth.
- **Organisations**: a table grouped by industry, with search, filters (shortlisted, new-grad route, has people) and a drawer showing why her, the new-grad route and who she could talk to.
- **People**: a pipeline strip, a "Needs you" list with drafts to copy, then everyone else grouped by where things stand.
- **About you**: one bar per quality, pulling right or pushing left, with patterns marked separately from hunches; the roles she's seen; her own words.

Every screen has a designed empty state that tells her exactly what to say to fill it. Tell her in one line where to look: "Today is your to-do list; Map is the fun one, press Replay." `My Map.md` is the same content as a page. The first time, run `session --onboard map`.

## Read it back

Run `status` and read `About Me/compass.md`. Tell her, in plain words and in this order: what pulls her and what pushes her away (with the number of signals behind each), the industries she's drawn to and how many organisations and people are in each, where her conversations stand, and the guide's next three moves. Add nothing that isn't in the files. If patterns are still hunches, say they're hunches.

Good before a big decision, after a gap of more than two weeks, or when she's feeling stuck ("look how far this has come" is a real use).

## Ask it a question

"Who do I know at energy companies?", "Which places had new-grad programmes?", "What did Sam say about consulting?". Answer from the map only: `find`, `show <kind> --filter`, conversation notes, research reports. Quote her conversation notes rather than paraphrasing them. If the map doesn't know, say so and offer the workflow that would find out ("I haven't scouted consulting yet. Want me to?").

If a good question has no answer yet, add it as a question on the map (`type: look-up` for facts, `chat` for things only a person in the field can answer, then tie it to someone she could ask).

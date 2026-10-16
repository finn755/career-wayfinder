# My map

Three things she might mean: show it, read it back, or ask it a question.

## Show it

```bash
python3 "<S>" render --ws "<WS>"
```

Present `Career Map.html` in the chat as a file card she can click (see **Presenting the map** in the main skill); don't point her to the folder. Tabs: **Home** (getting-started list, her to-dos with copyable drafts, goals, what the guide is working on), **Map** (industries coloured by her reactions, organisations around them, new things glowing, and a "Replay how your map grew" button), **Organisations** (searchable, filterable by new-grad route, shortlist, industry), **People** (where every conversation stands), **About you** (what pulls and pushes her, roles seen). Tell her in one line where to start: "Home is your to-do list; Map is the fun one: press Replay." `My Map.md` is the same content as a page. The first time, run `session --onboard map` and point out the Home tab: her to-dos, goals and getting-started list live there.

## Read it back

Run `status` and read `About Me/compass.md`. Tell her, in plain words and in this order: what pulls her and what pushes her away (with the number of signals behind each), the industries she's drawn to and how many organisations and people are in each, where her conversations stand, and the guide's next three moves. Add nothing that isn't in the files. If patterns are still hunches, say they're hunches.

Good before a big decision, after a gap of more than two weeks, or when she's feeling stuck ("look how far this has come" is a real use).

## Ask it a question

"Who do I know at energy companies?", "Which places had new-grad programmes?", "What did Sam say about consulting?". Answer from the map only: `find`, `show <kind> --filter`, conversation notes, research reports. Quote her conversation notes rather than paraphrasing them. If the map doesn't know, say so and offer the workflow that would find out ("I haven't scouted consulting yet. Want me to?").

If a good question has no answer yet, add it as a question on the map (`type: look-up` for facts, `chat` for things only a person in the field can answer, then tie it to someone she could ask).

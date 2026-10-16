# Explore roles

Someone who doesn't know what she wants can't answer "what job do you want?". She can react to a concrete picture of a Tuesday. So this is a round of cards: she reacts fast, the guide asks why only about the strongest reactions, and every reaction becomes evidence.

## Build the deck (8 cards)

Run `status` and `show role` first; never repeat a card she has rated. Pick from `references/role-universe.md`, and research beyond it when her background suggests roles it lacks:

- **4 cards that use her skills in different ways.** Spread them across the work-quality axes (bench vs desk vs people vs field; making vs checking vs explaining vs selling vs deciding). Never four lab jobs.
- **2 wildcards** from `references/wildcards.md`: roles a person with her background gets hired into that rarely appear on careers-fair lists.
- **1 hunch test**: a card that isolates one quality from her hunches (if "explaining" is a hunch, a role that is mostly explaining and has no lab).
- **1 contrast card**: something deliberately unlike what she has liked so far. A "no" is just as informative.

Each card, in five short lines:

```
**Application Scientist** (instrument companies)
What it is: the scientist who shows customers how an instrument solves their problem.
A Tuesday: run a demo on a customer's samples in the morning, a video call with a lab in Montréal, write up why their spectra look odd.
What you'd bring: your hands-on spectroscopy and the fact you've debugged a fussy set-up.
Way in: "Applications Specialist" or "Field Application Scientist" postings; M.Sc. is the usual bar.
```

Keep every line concrete. If you're not sure a detail is true of the role in her country, leave it out.

## Ask

Present the eight cards, then collect reactions. If a multiple-choice question tool is available, ask one question per card (up to four per call) with the options **Drawn to it**, **Curious**, **Meh**, **Not for me**. Otherwise ask her to reply in one line, for example "1 drawn, 2 meh, 3 no...".

Then ask why about at most three cards: the strongest yes, the strongest no, and any surprise (a wildcard she liked, or a "should" role she rejected). One question each: "What about it?" Take one-word answers happily.

## Log

For every card:

```bash
python3 "<S>" add role --ws "<WS>" --json '{"name":"Application Scientist","blurb":"<what it is>","day_in_life":"<the Tuesday>","origin":"guide|wildcard","interest":"drawn|curious|meh|no","industries":["<industry names if known>"]}'
python3 "<S>" signal --ws "<WS>" --about "Application Scientist" --lift <2|1|-1|-2> --tags "<qualities of the role>" --why "<her words, or 'no reason given'>" --source "role card"
```

Lift: drawn = 2, curious = 1, meh = −1, not for me = −2. Tag the role's *qualities* (from the vocabulary in `references/data-model.md`), not its name, so a pattern can form across different roles. Where she gave a why, tag what the why was about, not everything on the card.

Industries a liked role lives in: add them (`origin: guide`, `interest: unrated`) so the next industry round includes them.

## Close

Tell her what the round showed in one or two lines, using `status` (a pattern formed, a hunch strengthened, a wildcard landed). Add agenda items: a deeper look at any *drawn* role (which industries hire it, so the next scouting run covers them) and a hunch test for the next round. `session --note "role round: <n> cards, <drawn names>"`. Offer the next move: another round (if fewer than 15 rated), an industry round, or scouting.

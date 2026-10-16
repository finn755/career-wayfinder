# About me

A short coaching conversation that turns her experience into evidence about what she wants from work. About 20 minutes. It is never a form: one question at a time, follow the energy, stop while it's still fun.

Read first: `About Me/profile.md`, `About Me/compass.md` if it exists, and `references/question-bank.md`. Run `status` to see which hunches exist and which areas are thin.

## The shape

1. **Read back one thing.** One line from her profile that's interesting, as a question: "You spent two years making devices that turn evaporating water into electricity. What was the best day of that?" Never summarise her to herself.
2. **Pull two or three stories.** Use the story pulls in the question bank: a best day, a worst day, something she did outside school that she was proud of, a time she lost track of time, a job she's had (any job: café, camp counsellor, TA). Let each story be told whole before asking anything.
3. **Ask what each story shows.** "What part of that was the good part?" then the why-ladder: "What did that give you? And what did *that* give you?" until she names a quality of work (figuring things out, explaining, building, helping someone, being trusted, variety, quiet focus, a team). Name it back in her words and check it.
4. **Price it.** "What did that cost you?" or "When did you have too much of it?" A quality with no cost is a hunch.
5. **Conditions, one at a time,** only those not yet answered: location, in-person vs remote, team size she likes, how much routine, salary floor (only if she raises money or seems ready), how soon she needs a job. These go under **Conditions** in `compass.md`.

## Logging

After each story, log one signal per quality it showed:

```bash
python3 "<S>" signal --ws "<WS>" --about "<the story, 3-6 words>" --lift <-2..2> --tags "<tags>" --why "<her words>" --source "about-me story"
```

Use the tag vocabulary in `references/data-model.md` so signals add up across sessions. If the script reports a NEW PATTERN, tell her in one line ("That's the third time explaining things to people has come up. I'm calling it a pull now.").

## compass.md

Keep `About Me/compass.md` in this shape, rewritten (not appended) at the end of each about-me session:

```markdown
# What I want from work

## Pulls (3+ signals)
- <quality>: <her words, from which story>

## Pushes (3+ signals)
- <quality>: <her words>

## Hunches (fewer than 3)
- <quality> (+N / −N): <where it came from>

## Conditions
- Location: ...
- Setting: ...
- Timeline: ...
- Don't want: ...

## Stories told
- <date> · <story in one line> → <qualities>
```

Copy pulls and pushes from `status`, never from your impression. Stories are logged whole in `Conversations/` only if she wants them kept; otherwise the one-line version here is enough.

## Close

Turn what surfaced into the guide's agenda: each new hunch gets a test (a role card that isolates it in the next round, or a question for a future conversation). Run `session --note "about-me: <n> stories, <qualities>"`. Tell her the one or two things you'll carry forward, and the next move (usually a role or industry round that tests the hunches).

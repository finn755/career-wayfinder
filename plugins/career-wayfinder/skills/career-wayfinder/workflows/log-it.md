# Log it

She tells the guide what happened; the guide updates the map, learns from it, and drafts whatever comes next. Work out which kind of event it is, then follow that section. Several at once is common ("Maya replied and I'm talking to Sam Thursday").

## A reply

```bash
python3 "<S>" update person "<name>" --ws "<WS>" --set status=replied --set next_step="<book a time | answer their question>"
```

Ask to see the reply if she wants help answering (pasted text or the Gmail thread if Gmail is connected). Draft a short answer in her voice: thank them, offer two or three times or ask for theirs, nothing more. Gmail draft or text to copy. She sends.

Celebrate it. A reply is the hardest-won thing in the process.

## A conversation she had

This is the richest evidence the map gets. Ask four questions, one at a time, and keep her words:

1. "What surprised you?"
2. "What does their ordinary Tuesday actually look like?"
3. "Did any part of it make you lean in, or lean back?"
4. "Did they suggest anyone else to talk to, or anything to do next?"

Write `Conversations/<date>-<person-slug>.md`: who, where they work, her answers in her words, what they suggested. Then:

```bash
python3 "<S>" update person "<name>" --ws "<WS>" --set status=chatted --set next_step="send a thank-you"
python3 "<S>" signal --ws "<WS>" --about "<role or org>" --lift <..> --tags "<qualities she leaned toward or away from>" --why "<her words>" --source "conversation with <name>"
```

- Referrals: add each named person with `origin` noted in `why` ("suggested by <name> on <date>") and `sources: ["conversation:<file name>"]`. Mark `to-draft`, and note that a warm intro beats a cold note: the next step is to ask <name> to introduce her, or to mention <name> in the message.
- Roles or industries the conversation revealed: add them `unrated` for the next round.
- If an open question on the map was answered, resolve it:
  ```bash
  python3 "<S>" update question <id> --ws "<WS>" --set status=resolved --json '{"resolution":{"learned":"<her words>","changes":"<what it changes on the map>","next_step":"<one small step, with a date>","date":"<today>"}}'
  ```
- Draft a thank-you (three lines; mention one specific thing they said). After she sends it: `status=thanked`.

## A job posting she saw

Ask what caught her eye or put her off; log a signal with tags from her answer (`--source "posting"`). If the organisation isn't on the map, add it with the posting URL as its source. If she wants to apply, note it on the organisation (`next_step`), and suggest finding one person there first: a name to mention in the application helps. The guide never applies for her.

## Something she noticed about herself

"I hated that webinar", "I keep reading about batteries": log it as a signal with her words. If it's a want she can't phrase yet, add a question (`type: think-it`) so it isn't lost.

## Close

Run `session --note "<what was logged>"`. If the log produced a pattern (the script says NEW PATTERN), tell her. Point to the next move in one line.

# Find people

Find people at the organisations she likes who started recently: new grads, early-career scientists, people a year or three ahead of her. They remember the job search, they reply more often than senior people, and they can tell her what the work is really like.

## Pick organisations

Run `status`. Targets, in order: shortlisted organisations with nobody found yet; organisations rated *drawn*; then *curious*. Up to 12 organisations per run. Confirm the list with her in one line unless she asked for specific ones ("Find people at Hatch").

## Brief and launch

Read `references/research-rules.md` (the early-career evidence rules and the privacy line are there). Start **people-finder** agents in parallel, three or four organisations each, at most three agents at once (they run on a small, fast model to save her usage). Each brief includes:

- the organisations (name, id, url, location) and the roles she's interested in there;
- her school, degree and field (so the finder can spot alumni and similar backgrounds, which make the warmest first contacts);
- the target: 2–4 people per organisation, early-career first, at most one senior person per organisation (a hiring manager or team lead in a role she likes);
- the finds path: `<WS>/Research/finds/<today>-people-<n>.json`;
- the search tools available.

If agents aren't available, do it in this session, a few organisations at a time.

## Import, check, present

```bash
python3 "<S>" import --ws "<WS>" "<finds file>"
python3 "<S>" check --ws "<WS>"
```

Drop anyone `check` flags without a source. Then spot-check before presenting: open the source for two people per finds file and confirm the name, organisation and early-career evidence are really there. If one doesn't hold up, re-check every person from that file the same way and drop what fails. Treat "title only" evidence as weak and say so. Present the people in a short list grouped by organisation: name, title, the early-career evidence in a few words ("joined 2025 after a B.Sc. at Waterloo"), why them, and any shared background (same school, same field). Ask which she'd like to reach out to (multiple choice per organisation if the tool is available). Set those to `to-draft`:

```bash
python3 "<S>" update person "<name>" --ws "<WS>" --set status=to-draft
```

If she knows someone already, or a friend can introduce her, that beats any cold message: note it as `next_step: "ask <friend> for an intro"`.

## Close

Agenda items: draft messages for the to-draft people; for organisations where nobody early-career turned up, one alternative route (the careers page's recruiter, a university alumni contact). `session --note "people: <n> found at <orgs>"`. Present the map in the chat (the new people are on the People tab), then offer to draft the messages now.

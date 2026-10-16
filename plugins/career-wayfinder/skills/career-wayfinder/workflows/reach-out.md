# Reach out

Make sending easy and keep it honest. The template is hers, built from her own words; each draft adds one true, specific line about the person. She sends everything.

Read `references/outreach-guide.md` first.

## 1. The template (first time only)

If `Outreach/template.md` doesn't exist, build it with her. Never write it from scratch for her: messages written by AI read as AI to the people receiving them, and replies drop.

1. Ask her to say, as if leaving a voice note for a friend of a friend: who she is, why she's reaching out, and what she'd love to ask. Rambling is fine.
2. Trim her words, don't replace them, into two versions (rules and limits in the outreach guide): an email of about 100 words or fewer, and a LinkedIn connection note of 200 characters or fewer. Keep her phrases; cut, don't polish.
3. Show both. Ask: "Does this sound like you?" Edit until she says yes. Save `Outreach/template.md` with both versions and a dated line for each change.

## 2. Draft for each person

Take the people with status `to-draft` (at most 10 per sitting; suggest 5). For each:

- Read their entry and its sources. Write **one** specific line that's true and that they'd recognise: their path ("You went from a chemistry M.Sc. to applications work at Horiba"), something they published or posted, a shared school. Never flatter; never mention anything personal.
- Choose the route: **email** only if a published address is on the person's entry; otherwise a **LinkedIn note** (she sends a connection request with the note).
- Write the draft from the template plus that line. Same length limits.

**Email:** if the Gmail connector is available, create a Gmail draft (never send). Tell her: "It's in your Gmail drafts." Also save a copy as `Outreach/drafts/<today>-<person-slug>.md`.

**LinkedIn:** append to `Outreach/linkedin-notes.md`:

```markdown
### <Name> · <title> at <org>
Profile: <profile_url>
> <the note, ≤200 characters>
(<n> characters) · drafted <today>
```

Then save the message text on the person too (it shows on her map with a Copy button):

```bash
python3 "<S>" update person "<name>" --ws "<WS>" --json '{"draft": "<the message text>"}'
python3 "<S>" update person "<name>" --ws "<WS>" --set status=drafted --set next_step="send the <email|LinkedIn note>"
```

Show her the drafts together, short. Ask if any need changing. If she edits one, take the edit as a signal about her voice and offer to fold it into the template.

## 3. When she sends

She'll say something like "sent the first three". Mark each:

```bash
python3 "<S>" update person "<name>" --ws "<WS>" --set status=sent --set next_step="wait for a reply; follow up after a week"
```

`last_contact` is set to today automatically. Celebrate a little: sending is the hard part.

## 4. Follow-ups

`status` lists anyone sent at least seven days ago with no reply. Offer one follow-up per person, ever: two lines, no guilt, same route ("Hi <name>, just floating this back up in case it got buried. No worries at all if now's not a good time."). Draft it the same way; set `next_step: "follow-up drafted"`. After a follow-up with no reply in another two weeks, suggest parking them kindly (`status=parked`) and moving on. It's never about her.

## 5. Replies

When she says someone replied, switch to `workflows/log-it.md`.

## Pacing

Suggest 5–10 new messages a week at most. LinkedIn limits connection requests for new and free accounts; a steady trickle keeps her account safe and her follow-ups manageable.

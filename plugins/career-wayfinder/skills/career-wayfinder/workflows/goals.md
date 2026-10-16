# Goals

Set two to four tangible goals with her, then keep them alive by reorienting to them every sitting. The goals are hers: the guide suggests shapes and realistic numbers and explains why, but she chooses, words, sizes and dates each one, and can change them any time.

## When

- She asks ("let's set some goals", "what am I working toward?").
- `status` says "No goals yet" and there's enough context: setup is done and she has had at least an about-me sitting or one round of cards. Before that, goals are guesses.
- A weekly check-in is due (`status` says so), or a goal is reached, past due, or clearly no longer fits.

## Coach's note to start

Before setting goals the first time, explain in a few sentences why and how:

> Here's the trick with job-search goals: set them on things you control (conversations, messages, exploring) rather than things you don't (offers, replies). You can't make someone hire you by November, but you can have five conversations by November, and those conversations are what lead to the right job. Small, specific and dated beats big and vague.

## 1. North star (one sentence, hers)

Ask: "Picture it's <a date about three months out>, and this went really well. What's true?" Help her trim the answer into one sentence in her words, for example "By February I know the two or three directions I want, and I've started applying to them." Save it:

```bash
python3 "<S>" session --ws "<WS>" --destination "<her sentence>"
```

## 2. Pick goal shapes

Offer these shapes as a menu (multiple choice if available, more than one allowed), with one line each on what it's for. She picks two to four. Don't push any shape; a goal she didn't choose won't pull her.

| Shape | Example | Measured by |
|---|---|---|
| **Explore widely** | React to 30 roles and industries by Nov 15 | `industries_reacted` or `roles_reacted` (one goal per measure) |
| **Map the territory** | Shortlist 10 organisations by Nov 30 | `orgs_shortlisted` |
| **Reach out** | Send 15 messages by Nov 30 | `messages_sent` |
| **Learn from people** | Have 5 conversations by Dec 15 | `conversations` |
| **Narrow down** | Name the 3 industries I'd bet on by Jan 15 | `manual` |
| **Try it** | Go to 2 industry events or webinars by Dec 1 | `manual` |
| **Apply** | Apply to 3 roles I'm genuinely excited about by Jan 31 | `manual` |

She can also invent her own; pick the nearest measure, or `manual`.

## 3. Size it together

For each goal, propose a realistic number sized to her pace (`meta.pace` in `status`), explain the reasoning in a sentence, and let her adjust. Useful arithmetic to share:

- Cold messages get roughly 20–30% replies, and most replies become a chat. So five conversations takes about 15–25 messages.
- About 20 minutes a few times a week gives roughly two rounds of cards a week (16 reactions), or 5–10 messages a week.

Then ask for the date ("When would feel ambitious but doable?"), why it matters to her in a few words, and the very first step (sized to one sitting). Read the goal back in her words; adjust until she says yes.

```bash
python3 "<S>" add goal --ws "<WS>" --json '{"text":"Have 5 conversations with people in different industries","measure":"conversations","target":5,"due":"2026-12-15","why":"<her words>","next_step":"<first small step>"}'
```

Keep at most four active goals. If she wants a fifth, ask which one to pause.

## 4. Close

Read back the north star and the goals as a short list. Tell her how they'll show up: "Each time we talk I'll tell you where you are against these, and I'll connect what we're doing to them. They're yours: if one stops fitting, we change it, no guilt." Run `session --goals-checked --note "goals set"`. Offer the map file (goals now sit at the top).

## Check-ins (weekly, or when status flags one)

Keep it to about five minutes, inside whatever sitting it's due in:

1. Read progress from `status`, warmly and specifically ("3 of 5 conversations, and you're ahead of pace").
2. Ask one question: "How are these feeling? Still the right ones?"
3. Adjust only if she wants: change the number, date or wording (`update goal <id> --set ...`), pause (`status=paused`), or drop (`status=dropped`) with a kind word. Behind isn't failing; it usually means the goal was sized before she knew how long things take.
4. Update each goal's `next_step`.
5. Run `session --goals-checked`.

When a goal is reached, celebrate properly, mark it `status=done`, and ask whether she wants a next goal in its place or a breather.

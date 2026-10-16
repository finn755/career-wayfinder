# What's next

The guide's daily answer to "what should I do today?". Its job is to make the next 15–20 minutes obvious and worth it.

## Decide

Run `status`. Pick moves in this order of leverage, skipping any that don't apply:

0. **No goals yet** (and she has done an about-me sitting or a round of cards): offer to set them (`workflows/goals.md`). **Goal check-in due**: do it first, in five minutes.
1. **Replies waiting for an answer** (status `replied`): someone is waiting on her.
2. **Thank-yous** owed after a conversation.
3. **Follow-ups due** (sent a week ago, no reply).
4. **Drafts waiting to be sent**: the hardest step; offer to read them over with her.
5. **Breadth gaps**: fewer than 15 industries or roles reacted to → a round of cards.
6. **People to find** at shortlisted organisations, then **messages to draft** for them.
7. **Scouting** of *drawn* or *curious* industries, plus a wildcard run.
8. **Open questions** on the map, especially ones a conversation could answer.
9. The guide's own **agenda** items.

Among items of equal leverage, prefer the one that moves a goal that's behind. Offer a plan of at most three items, sized to her pace (read `meta.pace` from `status`), with the first one recommended and why in a few words, and each tied to a goal where it serves one:

> Today, about 20 minutes:
> 1. **Answer Priya** (she replied yesterday; I've got a draft ready).
> 2. **Send the three LinkedIn notes** in your drafts.
> 3. **Six new industry cards**, two of them my wildcards (that gets you to 18 of your 30 reactions).
>
> Want to start with Priya?

The first time she asks, run `session --onboard plan`. Then run whichever she picks. If she just wants to chat or vent, do that; job searching is a lot. Afterwards, offer one small, easy win.

## Gaps and morale

- More than two weeks since the last session: start with a read-back (`workflows/my-map.md`) and one easy win, not a backlog.
- Many messages sent with no replies: say plainly that 20–30% is a normal reply rate for cold notes, check that the template is short and in her voice, and suggest warm routes (alumni, friends of friends) for the next batch.
- Nothing she likes yet: that's what wildcards and contrast cards are for. Run a fresh industry round with three wildcards.

## Weekly scheduled scouting (offer once)

Once she has at least three industries rated *drawn* or *curious*, offer once (and note the offer on the agenda so it isn't repeated):

> Want me to go exploring once a week on my own? I'd look into the industries you like, try one wildcard, and leave you a short note of what I found. I'd never contact anyone.

If yes, run `session --onboard schedule` once it's set up (or `--onboard-skip schedule` if she declines). To set it up, explain: type **/schedule** in a new task, choose weekly, and use this as the task: *"Run Career Wayfinder's scheduled scout on my Career Wayfinder folder."* Scheduled tasks only run while her computer is awake and the Claude app is open. The run follows **Scheduled runs** in `workflows/scout.md`. At the next session, read the newest weekly digest in `Research/` first.

## Close

`session --note "whats-next: <what she did>"`, and the next move in one line.

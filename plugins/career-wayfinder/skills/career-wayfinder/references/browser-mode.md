# Browser mode (claude.ai)

She may be using the guide on claude.ai in a browser instead of the desktop app, for example because her computer is too old for the desktop app. Everything works except three things, and this file covers how to handle each.

## 1. Where her map lives

There's no folder on her computer. You run code in a private working space that belongs to this conversation, so her map lives there: `init --folder ~ --mode web --present-to /mnt/user-data/outputs` (or wherever this environment shows her the files you create).

Because that space belongs to the conversation, **the Career Map file is her backup**. Every render writes her whole map inside the page. Present it after every activity that changed the map, and the first time tell her: "This file is also your backup. Keep the newest one, and if I ever lose track, just drag it back in." She should keep using this same chat.

If this environment gives you a tool that publishes a file as an artifact in her account, you may also keep the map there, published from the same file. Never retype the page into an artifact by hand: it's long, slow, expensive, and easy to corrupt.

## 2. Lost working copy

In the browser, the working space can occasionally be cleared. If this is a chat where you've already set things up with her (you can see it in the conversation) but `map.json` isn't there:

1. Don't rebuild anything from memory, and don't start setup again.
2. Say it plainly and kindly: "I've lost my working copy of your map. That can happen in the browser. Drag in your newest **Career Map** file and I'll pick up exactly where we left off."
3. Run `init --folder ~ --mode web --present-to <the folder where files you create are shown to her>`, then `restore --ws "<WS>" "<the file she attached>"` (attached files usually appear under `/mnt/user-data/uploads`). Tell her what came back, using the counts `restore` prints.
4. If she can't find a copy, rebuild from what's in this conversation, tell her honestly what was lost, and keep going.

## 3. No research agents, maybe no Gmail drafts

- The scout and people-finder agents don't run in browser chats. Do the research yourself, leanly: one industry at a time with about ten searches and five or six organisations, and people at no more than three organisations per run with about four searches each. Summarise; never paste raw results.
- Gmail may be read-only in the browser. If there's no draft tool, don't promise drafts in Gmail. Every message reaches her through the Copy buttons on her map and through `Outreach/linkedin-notes.md`.
- Scheduled weekly scouting needs the desktop app. Don't offer it in the browser.

# Connectors

Two optional connectors make the guide much better. Neither is required. Both are added in the Claude app's settings by her, with her own accounts; the guide never asks for a password, key or code in chat.

## How to tell what's connected

Look at the tools available in this session:

- **Exa:** tool names containing `exa` (for example `web_search_exa`, `web_search_advanced_exa`, `web_fetch_exa`).
- **Gmail:** tools from the Gmail connector (names that mention gmail, or a Gmail server offering `create_draft`, `search_threads`, `get_thread`).

If a connector was added during this task and its tools aren't visible, a new task usually picks them up.

## Exa: better search for finding organisations and people

What it's for: Exa is a search engine built for AI. It is much better than ordinary search at finding companies, team pages and people's public profiles. The guide uses it only to search; it never posts or contacts anyone.

**It comes bundled with this plugin.** No account or key is needed: the bundled server uses Exa's free, rate-limited access. Walk her through switching it on:

1. "In the Claude app, open **Customize** (left sidebar), then **Plugins**, and click **Career Wayfinder**."
2. "Open its **Connectors** tab and click **Connect** next to **Exa**."
3. "If it says connected, start a new chat (top left), connect the same folder, and say **continue setup**. That chat becomes my home."

If searches start failing with a limit or credits message, Exa's free access has run out for now. Offer the upgrade path once, as optional: "If you'd like more searching, you can make a free account at **exa.ai** (new accounts get free credits), then in **Settings › Connectors** add the **Exa** connector from the directory and sign in." Until then, fall back to built-in web search and say so.

## Gmail: email drafts

What it's for: the guide puts email drafts straight into her Gmail drafts folder so she can read, edit and send them herself. It also lets the guide read a reply when she asks it to. It never sends.

1. "In the Claude app, open **Settings**, then **Connectors**."
2. "Find **Gmail** and click **Connect**."
3. "Choose the Google account you want to send from, and click **Allow**."
4. "Start a new task, connect your Career Wayfinder folder, and say **continue setup**."

Before creating the first Gmail draft, tell her: "I'll put this in your Gmail drafts. It won't send."

If she uses a different email provider, skip this: drafts are saved in her Outreach folder to copy and paste.

## LinkedIn

There's no LinkedIn connector, by design. The guide finds public profile links through search, drafts connection notes into `Outreach/linkedin-notes.md`, and she sends them herself. Her own LinkedIn profile reaches the guide only as the PDF she downloads ("More" › "Save to PDF").

# Research rules

For scouts and people-finders, and for the guide whenever it researches in-session.

## Tools, in order

1. **Exa** (if connected; tool names contain `exa`, such as `web_search_exa`, `web_search_advanced_exa`, `web_fetch_exa`). Best for finding organisations, team pages and people. Use the advanced search's category and domain filters where offered (company, people, news). Prefer it for anything person-shaped.
2. **Built-in web search and web fetch**, for everything else and as a fallback.
3. Never a logged-in session, a people-search or data-broker site, or an attendee list.

Spend searches sensibly: a scout run is about 15–30 searches per industry, not hundreds. If Exa reports a rate limit or that it is out of credits, switch to web search and note it in the report so the guide can tell her.

## What counts as a source

A public URL where the fact appears: the organisation's own site (about, team, careers, news, blog), a university news or alumni page, a conference programme or poster list, a paper, a government or funder page, a public profile (LinkedIn URLs only as they appear in search results; personal sites; org bios). A fact with no URL doesn't go in the finds file. An example organisation the guide named from memory is unverified until a scout finds a source.

## Scouting an industry

- Aim for 5–8 organisations per industry, mixed: at least one large employer, one mid-size, one startup or small firm, and one public-sector, non-profit or academic option where they exist.
- Respect her location conditions; include remote-friendly organisations; mark location for each.
- For each organisation: url, location, size, one-line blurb, one-line why_her, careers_url, and any **new-grad programme** (graduate scheme, rotation, co-op-to-hire, "early careers" page). New-grad routes are gold; look for them on purpose.
- Skip organisations already on the map (the brief lists them).
- Add up to two agenda items for things worth a follow-up run (a sub-sector, a cluster of companies in one city).

## Finding early-career people

Who counts: people who started their current role in roughly the last three years and are at the start of their career (new-grad, associate, junior, "I", rotational, early-career programme), or one or two steps ahead of her. One senior person per organisation is fine (a team lead or hiring manager in a role she likes); mark them as such.

**Early-career evidence** must be stated and sourced: a graduation year on a public page, "joined in 2025" on a team or news page, a new-grad cohort announcement, an "early careers" story or "day in the life" post, a title such as Associate Scientist or Analyst I, a recent thesis with a matching name. Titles alone are weak evidence; say so when that's all there is.

Where to look:

- The organisation's team, people, news and blog pages ("meet our new hires", "intern spotlight", "day in the life", early-careers pages).
- University news and alumni stories, especially from her own school and department ("where are they now", graduate profiles, convocation stories).
- Conference programmes, poster sessions and student awards that list affiliations.
- Public profile search results (Exa people/company filters, or web search such as `"Associate Scientist" "<org>" chemistry`), using only what the result shows.

The privacy line:

- Public professional information only: name, title, organisation, education, public work. Nothing about family, home, age, health, politics or private social media.
- Emails only when the person or organisation publishes them, with the `found_at` URL. Never construct one from a name pattern.
- No searching a person's posting history; search by topic and organisation, not by individual.
- Anyone who asks to be removed is removed.

## Finds file and report

Write two files to the paths in the brief:

1. **Finds** (`Research/finds/<date>-<slug>.json`): the format in `references/data-model.md`. Every org and person has `sources`.
2. **Report** (`Research/<date>-<slug>.md`): a short, readable note for her: what you looked for, the most interesting finds with one line each, new-grad routes found, anything surprising, what you couldn't verify, and every source URL.

Don't write anywhere else, and don't edit the map store; the guide imports.

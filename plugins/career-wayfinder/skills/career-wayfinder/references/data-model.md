# Data model

Everything structured lives in `.wayfinder/map.json`, written only by `wayfinder.py`. Words she says live in markdown files (`About Me/`, `Conversations/`, `Outreach/`). Pass objects to `add` as JSON; refer to industries, roles and organisations by **name** (the script converts names to ids and merges duplicates by name, URL or profile link).

## Kinds

### industry
| field | notes |
|---|---|
| `name` | required. Plain words: "Battery materials and energy storage" |
| `blurb` | one line: what the industry does |
| `why_her` | one line: why someone with her background gets hired there |
| `origin` | `her` · `profile` · `guide` · `wildcard` · `friend` · `conversation` |
| `interest` | `unrated` · `drawn` · `curious` · `meh` · `no` |
| `status` | `fog` (named, not explored) · `to-scout` · `scouted` · `parked` |

### role
`name` (required), `blurb`, `day_in_life`, `skills_used` (list), `industries` (list of names), `origin`, `interest`.

### org
| field | notes |
|---|---|
| `name`, `sources` | required. `sources` = list of public URLs the facts came from |
| `url` | homepage |
| `industries`, `roles` | lists of names |
| `location` | city/region of the relevant site(s); "remote" if so |
| `size` | `startup` · `small` · `mid` · `large` · `public sector` · `non-profit` (free text allowed) |
| `blurb` | one line: what they do |
| `why_her` | one line |
| `new_grad_program` | name + URL of a graduate, rotation or co-op-to-hire programme, if one exists |
| `careers_url` | careers page |
| `interest`, `status` | `status`: `found` · `shortlisted` · `parked` |

### person
| field | notes |
|---|---|
| `name`, `org`, `sources` | required. `org` = organisation name or id; must already be on the map (import adds orgs before people) |
| `title` | as published |
| `early_career_evidence` | the fact that makes them early-career, with its date: "joined 2025 after B.Sc. Waterloo (team page)" |
| `school` | where they studied, if published |
| `profile_url` | their public profile (LinkedIn URL from search results, personal site, org bio) |
| `contact_routes` | list of `{ "kind": "email" \| "linkedin" \| "form" \| "other", "value": "...", "found_at": "<URL where it is published>" }`. Never a guessed email |
| `why` | one line: why she'd want to talk to them |
| `shared` | shared background (same school, same field), if any |
| `status` | `found` · `to-draft` · `drafted` · `sent` · `replied` · `chatted` · `thanked` · `parked` |
| `draft` | the latest drafted message text (shown on her map with a Copy button) |
| `last_contact`, `next_step` | set by `update`; `last_contact` auto-fills on sent/replied/chatted/thanked |

### question
`text` (required), `type` (required: `chat` = only a person in the field can answer · `look-up` = researchable · `try-it` = a small experiment, like a webinar, a sample task or one application · `think-it` = a reflection she does alone), `about` (list of names/ids), `with` (a person, for chats), `status` (`open` · `resolved` · `dropped`), `resolution` (`{learned, changes, next_step, date}`).

### agenda
The guide's own to-do list. `text` (required), `kind` (required: `scout` · `wildcard` · `people` · `outreach` · `follow-up` · `question` · `ask-her` · `setup`), `why`, `status` (`planned` · `doing` · `done` · `dropped`).

### goal
Hers, set together (`workflows/goals.md`). `text` (required, her words), `measure` (required: `industries_reacted` · `roles_reacted` · `industries_scouted` · `orgs_found` · `orgs_shortlisted` · `people_found` · `messages_sent` · `replies` · `conversations` · `manual`), `target` (required, a whole number), `due` (required, YYYY-MM-DD), `why` (her words), `next_step`, `status` (`active` · `done` · `paused` · `dropped`), `progress` (only for `manual`; update it as she reports). Progress for every other measure is computed from the map, and `status` shows pace (on track, behind, reached, past due).

### meta (via `session`)
`name` (what she likes to be called), `guide_name` (what she calls the guide), `destination` (her north star sentence), `pace`, `last_session`, `goals_checked`. A head-start file may carry `meta.name` and `meta.guide_name_default`.

### signal (via the `signal` command)
`about` (a thing on the map or free text), `lift` (−2..2), `tags`, `why` (her words), `source` (role card, industry card, org card, posting, conversation with X, about-me story, setup), `date`.

## Tag vocabulary

Signals only add up if tags repeat. Use these where they fit; coin a new tag only when none fits, in the same lower-case, few-words style.

- **Kind of work:** hands-on lab · building things · analysing data · figuring things out · checking and testing · writing · explaining · teaching · persuading · selling · advising · organising · deciding · creating · caring for people
- **Setting:** in a lab · at a desk · out in the field · travel · client-facing · remote · big organisation · small team · startup · public sector · non-profit · academic
- **Pace and shape:** variety · routine · deep focus · fast-paced · long projects · clear process · ambiguity · independence · close teamwork · mentorship · visible impact
- **Mission and content:** climate and energy · health · environment · materials · consumer products · safety and regulation · public good · technology · money and business · education · science itself
- **Conditions:** pay · stability · growth path · location · hours · prestige · learning curve

## Finds file (what scouts and people-finders write)

One JSON object; every key optional; same fields as above:

```json
{
  "industries": [{"name": "...", "blurb": "...", "why_her": "...", "origin": "wildcard", "status": "fog"}],
  "orgs": [{"name": "...", "url": "...", "industries": ["..."], "location": "...", "size": "...", "blurb": "...", "why_her": "...", "new_grad_program": "...", "careers_url": "...", "sources": ["https://..."]}],
  "people": [{"name": "...", "org": "...", "title": "...", "early_career_evidence": "...", "school": "...", "profile_url": "...", "why": "...", "shared": "...", "sources": ["https://..."]}],
  "agenda": [{"text": "...", "kind": "scout", "why": "..."}]
}
```

Import adds industries, then roles, then orgs, then people, so a person's `org` can name an organisation from the same file.

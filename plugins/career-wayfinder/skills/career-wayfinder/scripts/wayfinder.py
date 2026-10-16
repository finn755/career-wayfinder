#!/usr/bin/env python3
"""Career Wayfinder engine: the map store, the guide's dashboard, and the map renderer.

Standard library only. All state lives in the user's folder:
  <ws>/.wayfinder/map.json   the map (industries, roles, orgs, people, questions, signals, agenda, log)
  <ws>/Career Map.html       rendered view (open in a browser)
  <ws>/My Map.md             rendered readable summary

Cowork's shell keeps no variables or working directory between calls, so every command takes --ws.
Run `wayfinder.py --help` or `wayfinder.py <command> --help`.
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import sys
import tempfile

VERSION = "0.1.0"
WS_NAME = "Career Wayfinder"

KINDS = {
    "industry": "industries",
    "role": "roles",
    "org": "orgs",
    "person": "people",
    "question": "questions",
    "agenda": "agenda",
    "goal": "goals",
}

INTEREST = ["unrated", "drawn", "curious", "meh", "no"]
ENUMS = {
    "industry": {
        "interest": INTEREST,
        "status": ["fog", "to-scout", "scouted", "parked"],
        "origin": ["her", "profile", "guide", "wildcard", "friend", "conversation"],
    },
    "role": {
        "interest": INTEREST,
        "origin": ["her", "profile", "guide", "wildcard", "friend", "conversation"],
    },
    "org": {
        "interest": INTEREST,
        "status": ["found", "shortlisted", "parked"],
    },
    "person": {
        "status": ["found", "to-draft", "drafted", "sent", "replied", "chatted", "thanked", "parked"],
    },
    "question": {
        "type": ["chat", "look-up", "try-it", "think-it"],
        "status": ["open", "resolved", "dropped"],
    },
    "agenda": {
        "kind": ["scout", "wildcard", "people", "outreach", "follow-up", "question", "ask-her", "setup", "goal"],
        "status": ["planned", "doing", "done", "dropped"],
    },
    "goal": {
        "measure": ["industries_reacted", "roles_reacted", "industries_scouted", "orgs_found", "orgs_shortlisted",
                    "people_found", "messages_sent", "replies", "conversations", "manual"],
        "status": ["active", "done", "paused", "dropped"],
    },
}
REQUIRED = {
    "industry": ["name"],
    "role": ["name"],
    "org": ["name", "sources"],
    "person": ["name", "org", "sources"],
    "question": ["text", "type"],
    "agenda": ["text", "kind"],
    "goal": ["text", "measure", "target", "due"],
}
LISTS = {"industries", "roles", "sources", "about", "skills_used", "contact_routes", "tags"}
PIPELINE = ENUMS["person"]["status"]

# Breadth targets: the shotgun rule, in numbers. The guide pushes until these are met before narrowing.
TARGETS = {
    "industries_reacted": 15,
    "roles_reacted": 15,
    "industries_scouted": 8,
    "orgs_found": 40,
    "people_found": 30,
    "conversations": 5,
}
FOLLOW_UP_DAYS = 7


def today():
    return dt.date.today().isoformat()


def slug(text):
    s = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return s[:60] or "item"


def die(msg, code=1):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(code)


# ---------------------------------------------------------------- store

def store_path(ws):
    return os.path.join(ws, ".wayfinder", "map.json")


def empty_map(name=""):
    return {
        "version": VERSION,
        "meta": {"name": name, "guide_name": "", "created": today(), "last_session": "", "destination": "",
                 "pace": "", "goals_checked": ""},
        "industries": [], "roles": [], "orgs": [], "people": [], "questions": [], "goals": [],
        "signals": [], "agenda": [], "log": [],
    }


def load(ws):
    p = store_path(ws)
    if not os.path.exists(p):
        die(f"No map found in {ws}. Run: wayfinder.py init --folder <connected folder>")
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        die(f"map.json is damaged ({e}). A backup is in .wayfinder/map.backup.json")
    base = empty_map()
    for k, v in base.items():
        data.setdefault(k, v)
    for k, v in base["meta"].items():
        data["meta"].setdefault(k, v)
    return data


def save(ws, data):
    p = store_path(ws)
    if os.path.exists(p):
        shutil.copyfile(p, os.path.join(ws, ".wayfinder", "map.backup.json"))
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    os.replace(tmp, p)


def find_item(data, kind, key):
    """Find by id, then by case-insensitive name."""
    coll = data[KINDS[kind]]
    for it in coll:
        if it.get("id") == key:
            return it
    k = str(key).strip().lower()
    for it in coll:
        if str(it.get("name", it.get("text", ""))).strip().lower() == k:
            return it
    return None


def all_ids(data):
    ids = {}
    for kind, coll in KINDS.items():
        for it in data[coll]:
            ids[it["id"]] = kind
    return ids


def normalise(kind, obj):
    obj = dict(obj)
    for k in list(obj):
        if k in LISTS and isinstance(obj[k], str):
            obj[k] = [x.strip() for x in obj[k].split(",") if x.strip()] if k != "sources" else [obj[k]]
    for k in ("target", "progress"):
        if k in obj and obj[k] not in (None, ""):
            try:
                obj[k] = int(obj[k])
            except (TypeError, ValueError):
                raise ValueError(f"{kind} {k} must be a whole number (got {obj[k]!r})")
    if kind == "goal" and obj.get("due"):
        try:
            dt.date.fromisoformat(str(obj["due"]))
        except ValueError:
            raise ValueError(f"goal due must be a date like 2026-11-30 (got {obj['due']!r})")
    for field, allowed in ENUMS.get(kind, {}).items():
        if field in obj and obj[field] not in allowed:
            raise ValueError(f"{kind} {field} must be one of {', '.join(allowed)} (got {obj[field]!r})")
    return obj


def make_id(data, kind, obj):
    prefix = {"industry": "ind", "role": "role", "org": "org", "person": "p", "question": "q", "agenda": "a", "goal": "g"}[kind]
    if kind in ("question", "agenda", "goal"):
        n = 1 + max([int(re.sub(r"\D", "", i["id"]) or 0) for i in data[KINDS[kind]]] or [0])
        return f"{prefix}{n}"
    base = f"{prefix}:{slug(obj['name'])}"
    if kind == "person" and obj.get("org"):
        base = f"{prefix}:{slug(obj['name'])}"
    ids = all_ids(data)
    cand, n = base, 2
    while cand in ids:
        cand = f"{base}-{n}"
        n += 1
    return cand


def dedupe_match(data, kind, obj):
    coll = data[KINDS[kind]]
    if obj.get("id"):
        for it in coll:
            if it["id"] == obj["id"]:
                return it
    if kind == "org" and obj.get("url"):
        # full URL, not just the host: different orgs can share a host (linkedin.com/company/..., parent domains)
        def norm(u):
            return re.sub(r"^https?://(www\.)?", "", u.strip().lower()).rstrip("/")
        for it in coll:
            if it.get("url") and norm(it["url"]) == norm(obj["url"]):
                return it
    if kind == "person":
        for it in coll:
            if it["name"].lower() == obj["name"].lower() and it.get("org") == obj.get("org"):
                return it
            if obj.get("profile_url") and it.get("profile_url") == obj.get("profile_url"):
                return it
    if kind in ("industry", "role", "org"):
        for it in coll:
            if it["name"].strip().lower() == obj["name"].strip().lower():
                return it
    if kind in ("question", "agenda", "goal"):
        for it in coll:
            if it.get("text", "").strip().lower() == obj.get("text", "").strip().lower():
                return it
    return None


def resolve_refs(data, kind, obj):
    """Let callers refer to industries, roles and orgs by name; store ids."""
    def to_id(k, v):
        it = find_item(data, k, v)
        return it["id"] if it else v
    if "industries" in obj:
        obj["industries"] = [to_id("industry", v) for v in obj["industries"]]
    if "roles" in obj:
        obj["roles"] = [to_id("role", v) for v in obj["roles"]]
    if kind == "person" and obj.get("org"):
        obj["org"] = to_id("org", obj["org"])
    return obj


def upsert(data, kind, obj):
    obj = resolve_refs(data, kind, normalise(kind, obj))
    hit = dedupe_match(data, kind, obj)
    if hit:
        for k, v in obj.items():
            if k == "id":
                continue
            if k in LISTS and isinstance(v, list):
                merged = list(hit.get(k, []))
                for x in v:
                    if x not in merged:
                        merged.append(x)
                hit[k] = merged
            elif v not in (None, "", []):
                hit[k] = v
        hit["modified"] = today()
        return hit["id"], "updated"
    missing = [f for f in REQUIRED[kind] if not obj.get(f)]
    if missing:
        raise ValueError(f"{kind} {obj.get('name', obj.get('text', '?'))!r} is missing {', '.join(missing)}")
    if kind == "person" and not find_item(data, "org", obj["org"]):
        raise ValueError(f"person {obj['name']!r}: organisation {obj['org']!r} isn't on the map; add it first")
    obj["id"] = make_id(data, kind, obj)
    obj.setdefault("created", today())
    defaults = {
        "industry": {"interest": "unrated", "status": "fog", "origin": "guide"},
        "role": {"interest": "unrated", "origin": "guide"},
        "org": {"interest": "unrated", "status": "found"},
        "person": {"status": "found"},
        "question": {"status": "open"},
        "agenda": {"status": "planned"},
        "goal": {"status": "active", "progress": 0},
    }[kind]
    for k, v in defaults.items():
        obj.setdefault(k, v)
    data[KINDS[kind]].append(obj)
    return obj["id"], "added"


def parse_json_arg(text):
    if text.startswith("@"):
        with open(text[1:], encoding="utf-8") as f:
            text = f.read()
    try:
        val = json.loads(text)
    except json.JSONDecodeError as e:
        die(f"That isn't valid JSON: {e}")
    return val if isinstance(val, list) else [val]


# ---------------------------------------------------------------- derived views

def derive_pulls(data):
    """The signals register's ranking: a tag becomes a known pull or push at three signals in one direction."""
    tags = {}
    for s in data["signals"]:
        for t in s.get("tags", []) or []:
            d = tags.setdefault(t, {"tag": t, "pos": 0, "neg": 0, "sum": 0, "n": 0, "last": ""})
            lift = int(s.get("lift", 0))
            d["n"] += 1
            d["sum"] += lift
            d["pos"] += lift > 0
            d["neg"] += lift < 0
            d["last"] = max(d["last"], s.get("date", ""))
    pulls, pushes, hunches = [], [], []
    for d in tags.values():
        if d["pos"] >= 3 and d["sum"] > 0:
            pulls.append(d)
        elif d["neg"] >= 3 and d["sum"] < 0:
            pushes.append(d)
        else:
            hunches.append(d)
    pulls.sort(key=lambda d: (-d["pos"], -d["sum"]))
    pushes.sort(key=lambda d: (-d["neg"], d["sum"]))
    hunches.sort(key=lambda d: (-d["n"], -abs(d["sum"])))
    return pulls, pushes, hunches


def breadth(data):
    ind = data["industries"]
    roles = data["roles"]
    people = data["people"]
    return {
        "industries_reacted": sum(1 for i in ind if i.get("interest") != "unrated"),
        "roles_reacted": sum(1 for r in roles if r.get("interest") != "unrated"),
        "industries_scouted": sum(1 for i in ind if i.get("status") == "scouted"),
        "orgs_found": len(data["orgs"]),
        "people_found": len(people),
        "conversations": sum(1 for p in people if p.get("status") in ("chatted", "thanked")),
    }


def guide_name(data):
    m = data["meta"]
    return (m.get("guide_name") or m.get("guide_name_default")
            or (f"{m['name']}'s Career Guide" if m.get("name") else "Your Career Guide"))


def metrics(data):
    m = breadth(data)
    people = data["people"]
    m["orgs_shortlisted"] = sum(1 for o in data["orgs"] if o.get("status") == "shortlisted")
    m["messages_sent"] = sum(1 for p in people if p.get("status") in ("sent", "replied", "chatted", "thanked"))
    m["replies"] = sum(1 for p in people if p.get("status") in ("replied", "chatted", "thanked"))
    return m


def goal_progress(data, g, m=None):
    """Progress, percent, days left, and whether the goal is on pace (linear from its creation date)."""
    m = m or metrics(data)
    have = int(g.get("progress", 0)) if g.get("measure") == "manual" else m.get(g.get("measure"), 0)
    target = max(1, int(g.get("target", 1)))
    pct = min(100, round(100 * have / target))
    left = None
    pace = "no date"
    try:
        due = dt.date.fromisoformat(str(g["due"]))
        start = dt.date.fromisoformat(str(g.get("created", today()))[:10])
        left = (due - dt.date.today()).days
        span = max(1, (due - start).days)
        expected = min(1.0, max(0.0, (dt.date.today() - start).days / span))
        if have >= target:
            pace = "reached"
        elif left < 0:
            pace = "past due"
        elif have / target + 0.15 >= expected:
            pace = "on track"
        else:
            pace = "behind"
    except (KeyError, ValueError, TypeError):
        pass
    return {"have": have, "target": target, "pct": pct, "days_left": left, "pace": pace}


def days_since(date):
    try:
        return (dt.date.today() - dt.date.fromisoformat(date[:10])).days
    except (ValueError, TypeError):
        return None


def follow_ups(data):
    out = []
    for p in data["people"]:
        if p.get("status") == "sent":
            d = days_since(p.get("last_contact", ""))
            if d is not None and d >= FOLLOW_UP_DAYS:
                out.append((p, d))
    return out


def org_name(data, oid):
    o = find_item(data, "org", oid)
    return o["name"] if o else oid


def names(data, kind, ids):
    out = []
    for i in ids or []:
        it = find_item(data, kind, i)
        out.append(it["name"] if it else i)
    return out



# The onboarding checklist: the order she learns the guide in, each step taught through its command.
# Most steps complete themselves from the map; the rest are marked with `session --onboard <key>`.
ONBOARDING = [
    ("folder", "Set up your Career Wayfinder folder", "/start-here", False),
    ("names", "Tell me your name, and give your guide one", "/start-here", False),
    ("exa", "Connect Exa so I can search better", "/start-here", False),
    ("gmail", "Connect Gmail so I can leave email drafts", "/start-here", False),
    ("documents", "Share your CV or LinkedIn PDF", "/start-here", False),
    ("about_me", "Get to know each other", "/about-me", False),
    ("roles", "React to your first round of roles", "/explore-roles", False),
    ("industries", "React to your first round of industries", "/explore-industries", False),
    ("goals", "Set your goals together", "/my-goals", False),
    ("scout", "Send your guide exploring", "/scout", False),
    ("map", "Open your career map", "/my-map", False),
    ("people", "Find your first people to talk to", "/find-people", False),
    ("template", "Build your message template", "/reach-out", False),
    ("first_send", "Send your first messages", "/reach-out", False),
    ("plan", "Ask for a plan for the day", "/whats-next", False),
    ("log", "Log your first reply or conversation", "/log-it", False),
    ("schedule", "Weekly exploring on a schedule", "/whats-next", True),
]


def onboarding(data, ws=None):
    m = metrics(data)
    marks = data["meta"].get("onboarding", {}) or {}
    docs = False
    tmpl = False
    if ws:
        d = os.path.join(ws, "About Me", "documents")
        docs = (os.path.isdir(d) and any(not f.startswith(".") for f in os.listdir(d))) \
            or os.path.exists(os.path.join(ws, "About Me", "profile.md"))
        tmpl = os.path.exists(os.path.join(ws, "Outreach", "template.md"))
    srcs = [str(s.get("source", "")) for s in data["signals"]]
    auto = {
        "folder": True,
        "names": bool(data["meta"].get("name") and data["meta"].get("guide_name")),
        "documents": docs,
        "about_me": any(s.startswith("about-me") for s in srcs),
        "roles": m["roles_reacted"] >= 5,
        "industries": m["industries_reacted"] >= 5,
        "goals": any(g.get("status") in ("active", "done") for g in data["goals"]),
        "scout": m["industries_scouted"] >= 1,
        "people": m["people_found"] >= 1,
        "template": tmpl,
        "first_send": m["messages_sent"] >= 1,
        "log": m["replies"] >= 1 or any(s.startswith("conversation") for s in srcs),
    }
    steps = []
    for key, label, cmd, optional in ONBOARDING:
        state = "done" if auto.get(key) else marks.get(key, "todo")
        steps.append({"key": key, "label": label, "command": cmd, "optional": optional, "state": state})
    return steps


def todos(data):
    """Her to-do list, computed: what a person is waiting on first."""
    out = []
    for p in data["people"]:
        on = org_name(data, p.get("org"))
        if p.get("status") == "replied":
            out.append({"kind": "reply", "text": f"Answer {p['name']} ({on})", "person": p["id"]})
    for p in data["people"]:
        if p.get("status") == "chatted":
            out.append({"kind": "thanks", "text": f"Send {p['name']} a thank-you", "person": p["id"]})
    for p, d in follow_ups(data):
        out.append({"kind": "follow-up", "text": f"Follow up with {p['name']} (sent {d} days ago)", "person": p["id"]})
    for p in data["people"]:
        if p.get("status") == "drafted":
            out.append({"kind": "send", "text": f"Send your message to {p['name']} ({org_name(data, p.get('org'))})",
                        "person": p["id"]})
    n = sum(1 for p in data["people"] if p.get("status") == "to-draft")
    if n:
        out.append({"kind": "draft", "text": f"Ask your guide to draft messages for {n} {'person' if n == 1 else 'people'}"})
    w = [i["name"] for i in data["industries"] if i.get("origin") == "wildcard" and i.get("interest") == "unrated"]
    if w:
        out.append({"kind": "react", "text": f"React to {len(w)} wildcard industr{'y' if len(w) == 1 else 'ies'}: " + ", ".join(w[:3])})
    for q in data["questions"]:
        if q.get("status") == "open" and q.get("type") in ("try-it", "think-it"):
            out.append({"kind": q["type"], "text": q["text"]})
    return out


def growth(data, days=7):
    """What was added in the last `days` days, for the 'your map grew' line."""
    cut = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    def n(coll):
        return sum(1 for x in coll if str(x.get("created", ""))[:10] >= cut)
    return {"industries": n(data["industries"]), "roles": n(data["roles"]), "orgs": n(data["orgs"]),
            "people": n(data["people"]), "reactions": sum(1 for s in data["signals"] if str(s.get("date", "")) >= cut)}


# ---------------------------------------------------------------- commands

START_HERE = """# Career Wayfinder

This folder is your career map. Claude keeps it up to date; you never need to edit anything in here.

- **Career Map.html**: your map (your guide also shows it to you in the chat whenever it changes): industries, organisations, people, and where each conversation stands.
- **My Map.md**: the same map as a page you can read.
- **About Me**: your CV, thesis and anything else you add, plus the notes Claude keeps about what you want from work.
- **Outreach**: your message template and every draft. LinkedIn notes to copy and paste are in *linkedin-notes.md*.
- **Conversations**: notes from each chat you have, in your words.
- **Research**: what Claude found each time it went exploring.

Things to say to Claude any time:

- "What should I do today?"
- "Show me some roles" / "Show me some industries"
- "Go explore" (Claude researches in the background)
- "Find people at <organisation>"
- "Help me reach out"
- "I talked to <name>" / "<name> replied"
- "Show me my map"

Claude never sends a message, applies to a job, or connects with anyone for you. It drafts; you send.
"""


def cmd_init(a):
    folder = os.path.abspath(os.path.expanduser(a.folder))
    if not os.path.isdir(folder):
        die(f"Folder not found: {folder}")
    ws = folder if os.path.basename(folder) == WS_NAME else os.path.join(folder, WS_NAME)
    created = []
    for sub in ["", ".wayfinder", "About Me", "About Me/documents", "Outreach", "Outreach/drafts",
                "Conversations", "Research", "Research/finds"]:
        p = os.path.join(ws, sub)
        if not os.path.isdir(p):
            os.makedirs(p)
            created.append(sub or WS_NAME)
    sh = os.path.join(ws, "START HERE.md")
    if not os.path.exists(sh):
        with open(sh, "w", encoding="utf-8") as f:
            f.write(START_HERE)
        created.append("START HERE.md")
    if not os.path.exists(store_path(ws)):
        save(ws, empty_map(a.name or ""))
        created.append(".wayfinder/map.json")
    elif a.name:
        data = load(ws)
        data["meta"]["name"] = a.name
        save(ws, data)
    # write test
    probe = os.path.join(ws, ".wayfinder", ".write-test")
    try:
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
    except OSError as e:
        die(f"Can't write to {ws} ({e}). Reconnect the folder with edit access.")
    render(ws, load(ws), quiet=True)
    print(f"WS={ws}")
    print("Created: " + (", ".join(created) if created else "nothing new (already set up)"))
    print("All checks passed.")


def cmd_add(a):
    data = load(a.ws)
    if a.kind not in KINDS:
        die(f"kind must be one of {', '.join(KINDS)}")
    results = []
    for obj in parse_json_arg(a.json):
        try:
            results.append((obj.get("name", obj.get("text", "?")),) + upsert(data, a.kind, obj))
        except ValueError as e:
            results.append((obj.get("name", obj.get("text", "?")), None, str(e)))
    save(a.ws, data)
    for name, iid, what in results:
        print(f"{what:8} {iid:28} {name}" if iid else f"skipped  {what}")


def cmd_update(a):
    data = load(a.ws)
    it = find_item(data, a.kind, a.id)
    if not it:
        die(f"No {a.kind} called {a.id!r}. Try: wayfinder.py find --ws ... {a.id}")
    changes = {}
    for kv in a.set or []:
        if "=" not in kv:
            die(f"--set needs key=value (got {kv!r})")
        k, v = kv.split("=", 1)
        changes[k.strip()] = v.strip()
    if a.json:
        changes.update(parse_json_arg(a.json)[0])
    try:
        changes = resolve_refs(data, a.kind, normalise(a.kind, changes))
    except ValueError as e:
        die(str(e))
    for k, v in changes.items():
        if k in LISTS and isinstance(v, list) and not a.replace:
            merged = list(it.get(k, []))
            merged += [x for x in v if x not in merged]
            it[k] = merged
        else:
            it[k] = v
    if a.kind == "person" and "status" in changes and changes["status"] in ("sent", "replied", "chatted", "thanked"):
        it["last_contact"] = changes.get("last_contact", today())
    it["modified"] = today()
    save(a.ws, data)
    print(f"updated  {it['id']}  " + ", ".join(f"{k}={v}" for k, v in changes.items()))


def cmd_signal(a):
    data = load(a.ws)
    tags = [t.strip().lower() for t in (a.tags or "").split(",") if t.strip()]
    lift = int(a.lift)
    if lift < -2 or lift > 2:
        die("--lift must be -2, -1, 0, 1 or 2")
    about = a.about
    ref = None
    for kind in ("industry", "role", "org", "person"):
        it = find_item(data, kind, about)
        if it:
            ref = it["id"]
            break
    sig = {"date": a.date or today(), "about": ref or about, "lift": lift, "why": a.why or "",
           "tags": tags, "source": a.source or ""}
    data["signals"].append(sig)
    save(a.ws, data)
    pulls, pushes, _ = derive_pulls(data)
    print(f"logged   {sig['about']}  lift {lift:+d}  tags: {', '.join(tags) or '-'}")
    newly = [d["tag"] for d in pulls + pushes if d["tag"] in tags and (d["pos"] == 3 or d["neg"] == 3)]
    if newly:
        print("NEW PATTERN (third signal): " + ", ".join(newly) + "  → tell her, in one line")


def cmd_import(a):
    data = load(a.ws)
    with open(a.file, encoding="utf-8") as f:
        try:
            finds = json.load(f)
        except json.JSONDecodeError as e:
            die(f"{a.file} isn't valid JSON: {e}")
    order = [("industries", "industry"), ("roles", "role"), ("orgs", "org"), ("people", "person"),
             ("questions", "question"), ("agenda", "agenda"), ("goals", "goal")]
    fm = finds.get("meta", {}) or {}
    if fm.get("name") and not data["meta"].get("name"):
        data["meta"]["name"] = fm["name"]
    if fm.get("guide_name_default"):
        data["meta"]["guide_name_default"] = fm["guide_name_default"]
    counts = {}
    problems = []
    for coll, kind in order:
        for obj in finds.get(coll, []) or []:
            try:
                _, what = upsert(data, kind, obj)
                counts[(coll, what)] = counts.get((coll, what), 0) + 1
            except ValueError as e:
                problems.append(str(e))
    data["log"].append({"date": today(), "text": f"imported {os.path.basename(a.file)}"})
    save(a.ws, data)
    print("Imported: " + (", ".join(f"{n} {c} {w}" for (c, w), n in counts.items()) or "nothing"))
    for p in problems:
        print(f"  skipped: {p}")


def cmd_find(a):
    data = load(a.ws)
    q = a.text.lower()
    hits = 0
    for kind, coll in KINDS.items():
        for it in data[coll]:
            blob = json.dumps(it, ensure_ascii=False).lower()
            if q in blob:
                hits += 1
                label = it.get("name") or it.get("text")
                extra = ""
                if kind == "person":
                    extra = f" @ {org_name(data, it.get('org'))} [{it.get('status')}]"
                elif kind in ("industry", "role", "org"):
                    extra = f" [{it.get('interest', '')}{'/' + it['status'] if it.get('status') else ''}]"
                print(f"{kind:9} {it['id']:28} {label}{extra}")
    if not hits:
        print("No matches.")


def cmd_show(a):
    data = load(a.ws)
    if a.kind not in KINDS and a.kind != "signals":
        die(f"kind must be one of {', '.join(list(KINDS) + ['signals'])}")
    coll = data["signals"] if a.kind == "signals" else data[KINDS[a.kind]]
    filt = dict(kv.split("=", 1) for kv in (a.filter or []))
    rows = [it for it in coll if all(str(it.get(k)) == v or (isinstance(it.get(k), list) and v in it.get(k))
                                      for k, v in filt.items())]
    if a.full:
        print(json.dumps(rows, indent=1, ensure_ascii=False))
        return
    for it in rows:
        if a.kind == "signals":
            print(f"{it['date']}  {it['lift']:+d}  {it['about']}  ({', '.join(it.get('tags', []))})  {it.get('why', '')}")
        elif a.kind == "person":
            print(f"{it['id']:28} {it['name']} — {it.get('title', '')} @ {org_name(data, it.get('org'))} [{it['status']}]")
        elif a.kind == "org":
            print(f"{it['id']:28} {it['name']} [{it.get('interest')}/{it.get('status')}] {', '.join(names(data, 'industry', it.get('industries')))}")
        elif a.kind in ("industry", "role"):
            print(f"{it['id']:28} {it['name']} [{it.get('interest')}{'/' + it['status'] if it.get('status') else ''}] origin={it.get('origin')}")
        elif a.kind == "goal":
            gp = goal_progress(data, it)
            print(f"{it['id']:5} [{it.get('status')}] {gp['have']}/{gp['target']} by {it.get('due')} ({gp['pace']}) {it.get('text')}")
        else:
            print(f"{it['id']:5} [{it.get('status')}] ({it.get('type', it.get('kind'))}) {it.get('text')}")
    print(f"— {len(rows)} {a.kind}")


def cmd_status(a):
    data = load(a.ws)
    m = data["meta"]
    b = breadth(data)
    gap = days_since(m.get("last_session") or m.get("created"))
    guide = guide_name(data)
    print(f"{guide.upper()} · for {m.get('name') or '(name not set)'} · today {today()}")
    if not m.get("guide_name"):
        print("Guide name not chosen yet: ask her what she'd like to call you (default: " + guide + ")")
    print(f"Last session: {m.get('last_session') or 'never'}" + (f" ({gap} days ago)" if gap else "")
          + ("  → NEW SITTING: open with the reorientation" if m.get("last_session") != today() else ""))
    if m.get("destination"):
        print(f"North star: {m['destination']}")
    mets = metrics(data)
    active = [g for g in data["goals"] if g.get("status") == "active"]
    print("\nGOALS (hers; reorient to these)")
    if not active:
        print("  none yet: offer to set goals together (workflows/goals.md)")
    for g in active:
        gp = goal_progress(data, g, mets)
        bar = "█" * (gp["pct"] // 10) + "·" * (10 - gp["pct"] // 10)
        left = f"{gp['days_left']} days left" if gp["days_left"] is not None and gp["days_left"] >= 0 else "due date passed"
        print(f"  {g['id']:4} {bar} {gp['have']}/{gp['target']} · {gp['pace']} · {left} · {g['text']}")
        if g.get("next_step"):
            print(f"       next step: {g['next_step']}")
    chk = days_since(m.get("goals_checked") or (active[0]["created"] if active else ""))
    if active and chk is not None and chk >= 7:
        print(f"  Goal check-in due (last {chk} days ago): ask how they feel, adjust if she wants")
    steps = onboarding(data, a.ws)
    req = [s for s in steps if not s["optional"]]
    done_n = sum(1 for s in req if s["state"] in ("done", "skipped"))
    nxt = next((s for s in steps if s["state"] == "todo"), None)
    if done_n < len(req):
        print(f"\nGETTING STARTED {done_n}/{len(req)} · next: {nxt['label']} → teach her {nxt['command']}")
        print("  " + " · ".join(("✓ " if s["state"] == "done" else "– " if s["state"] == "skipped" else "◻ ") + s["key"]
                               for s in steps))
    print("\nBREADTH (the shotgun targets)")
    for k, target in TARGETS.items():
        v = b[k]
        bar = "█" * min(10, round(10 * v / target)) + "·" * (10 - min(10, round(10 * v / target)))
        print(f"  {k.replace('_', ' '):20} {bar} {v}/{target}")
    pulls, pushes, hunches = derive_pulls(data)
    print("\nWHAT PULLS HER (3+ signals): " + (", ".join(d["tag"] for d in pulls) or "none yet"))
    print("WHAT PUSHES HER AWAY: " + (", ".join(d["tag"] for d in pushes) or "none yet"))
    if hunches:
        print("Hunches (fewer than 3 signals): " + ", ".join(f"{d['tag']}({d['sum']:+d})" for d in hunches[:8]))
    ind = data["industries"]
    print("\nINDUSTRIES")
    for lvl in ["drawn", "curious", "unrated", "meh", "no"]:
        group = [i["name"] for i in ind if i.get("interest") == lvl]
        if group:
            print(f"  {lvl:8} " + "; ".join(group))
    to_scout = [i["name"] for i in ind if i.get("interest") in ("drawn", "curious") and i.get("status") != "scouted"]
    wild = [i["name"] for i in ind if i.get("origin") == "wildcard" and i.get("interest") == "unrated"]
    pipe = {s: 0 for s in PIPELINE}
    for p in data["people"]:
        pipe[p.get("status", "found")] = pipe.get(p.get("status", "found"), 0) + 1
    print("\nPEOPLE PIPELINE  " + " · ".join(f"{s} {n}" for s, n in pipe.items() if n))
    fu = follow_ups(data)
    shortlisted_no_people = [o["name"] for o in data["orgs"]
                             if o.get("interest") in ("drawn", "curious") or o.get("status") == "shortlisted"]
    shortlisted_no_people = [n for n in shortlisted_no_people
                             if not any(org_name(data, p.get("org")) == n for p in data["people"])]
    openq = [q for q in data["questions"] if q.get("status") == "open"]
    agenda = [x for x in data["agenda"] if x.get("status") in ("planned", "doing")]
    print("\nSUGGESTED MOVES (the guide's sensors; pick at most three to offer)")
    moves = []
    if nxt and done_n < len(req):
        moves.append(f"Onboarding: {nxt['label']} ({nxt['command']}).")
    if not data["industries"] and not data["roles"]:
        moves.append("Nothing on the map yet: start with about-me, then explore-roles.")
    if not active and (data["signals"] or data["industries"]):
        moves.append("No goals yet: set two to four tangible goals together (workflows/goals.md).")
    behind = [g for g in active if goal_progress(data, g, mets)["pace"] in ("behind", "past due")]
    if behind:
        moves.append("Goals needing attention: " + "; ".join(f"{g['id']} {g['text']}" for g in behind))
    if fu:
        moves.append("Follow up (sent ≥7 days, no reply): " + ", ".join(f"{p['name']} ({d}d)" for p, d in fu[:5]))
    ready = [p["name"] for p in data["people"] if p.get("status") == "to-draft"]
    if ready:
        moves.append(f"Draft messages for {len(ready)} people marked to-draft: " + ", ".join(ready[:5]))
    drafted = [p["name"] for p in data["people"] if p.get("status") == "drafted"]
    if drafted:
        moves.append(f"{len(drafted)} drafts waiting for her to send: " + ", ".join(drafted[:5]))
    if b["industries_reacted"] < TARGETS["industries_reacted"]:
        moves.append(f"Breadth: only {b['industries_reacted']} industries reacted to; run an industry round.")
    if b["roles_reacted"] < TARGETS["roles_reacted"]:
        moves.append(f"Breadth: only {b['roles_reacted']} roles reacted to; run a role round.")
    if to_scout:
        moves.append("Scout (drawn/curious, not yet scouted): " + "; ".join(to_scout[:5]))
    if wild:
        moves.append("Wildcards waiting for her reaction: " + "; ".join(wild[:5]))
    if shortlisted_no_people:
        moves.append("Find people at: " + "; ".join(shortlisted_no_people[:5]))
    if openq:
        moves.append("Open questions: " + " | ".join(f"{q['id']} {q['text']}" for q in openq[:3]))
    for x in agenda[:3]:
        moves.append(f"Agenda {x['id']} ({x['kind']}): {x['text']}")
    for i, mv in enumerate(moves, 1):
        print(f"  {i}. {mv}")
    if not moves:
        print("  Map is healthy. Offer a wildcard round or a read-back.")


def cmd_session(a):
    data = load(a.ws)
    data["meta"]["last_session"] = today()
    if a.note:
        data["log"].append({"date": today(), "text": a.note})
    if a.destination:
        data["meta"]["destination"] = a.destination
    if a.pace:
        data["meta"]["pace"] = a.pace
    if a.guide_name:
        data["meta"]["guide_name"] = a.guide_name
    if a.her_name:
        data["meta"]["name"] = a.her_name
    if a.goals_checked:
        data["meta"]["goals_checked"] = today()
    keys = [k for k, *_ in ONBOARDING]
    for k, state in [(k, "done") for k in a.onboard or []] + [(k, "skipped") for k in a.onboard_skip or []]:
        if k not in keys:
            die(f"--onboard key must be one of {', '.join(keys)}")
        data["meta"].setdefault("onboarding", {})[k] = state
    save(a.ws, data)
    render(a.ws, data, quiet=True)
    print("Session recorded; map re-rendered.")


def cmd_check(a):
    data = load(a.ws)
    ids = all_ids(data)
    problems = []
    for o in data["orgs"]:
        if not o.get("sources"):
            problems.append(f"org {o['name']}: no source URL")
        for i in o.get("industries", []):
            if i not in ids:
                problems.append(f"org {o['name']}: industry {i!r} isn't on the map")
    for p in data["people"]:
        if not p.get("sources"):
            problems.append(f"person {p['name']}: no source URL")
        if p.get("org") not in ids:
            problems.append(f"person {p['name']}: org {p.get('org')!r} isn't on the map")
        for r in p.get("contact_routes", []) or []:
            if isinstance(r, dict) and r.get("kind") == "email" and not r.get("found_at"):
                problems.append(f"person {p['name']}: email with no found_at (never guess emails)")
    for q in data["questions"]:
        if q.get("status") == "resolved" and not (q.get("resolution") or {}).get("next_step"):
            problems.append(f"question {q['id']}: resolved with no next step")
    if problems:
        for p in problems:
            print(f"✗ {p}")
        sys.exit(1)
    print("✓ Map is consistent.")


def cmd_render(a):
    data = load(a.ws)
    render(a.ws, data)


def cmd_export(a):
    import csv
    data = load(a.ws)
    out = os.path.join(a.ws, "people.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "title", "organisation", "status", "last contact", "next step", "profile", "why"])
        for p in data["people"]:
            w.writerow([p["name"], p.get("title", ""), org_name(data, p.get("org")), p.get("status"),
                        p.get("last_contact", ""), p.get("next_step", ""), p.get("profile_url", ""), p.get("why", "")])
    print(f"Wrote {out}")


# ---------------------------------------------------------------- rendering

def render(ws, data, quiet=False):
    with open(os.path.join(ws, "My Map.md"), "w", encoding="utf-8") as f:
        f.write(render_md(data))
    payload = json.dumps(view_model(data, ws), ensure_ascii=False).replace("</", "<\\/")
    page = HTML.replace("__DATA__", payload).replace("__TITLE__", html.escape(
        (data["meta"].get("name") + "'s " if data["meta"].get("name") else "") + "Career Map"))
    with open(os.path.join(ws, "Career Map.html"), "w", encoding="utf-8") as f:
        f.write(page)
    if not quiet:
        print(f"Wrote {os.path.join(ws, 'Career Map.html')} and My Map.md")


def view_model(data, ws=None):
    pulls, pushes, hunches = derive_pulls(data)
    return {
        "meta": data["meta"], "breadth": breadth(data), "targets": TARGETS,
        "industries": data["industries"], "roles": data["roles"], "orgs": data["orgs"],
        "people": data["people"], "questions": data["questions"],
        "agenda": [x for x in data["agenda"] if x.get("status") in ("planned", "doing")],
        "pulls": pulls, "pushes": pushes, "hunches": hunches[:12],
        "followups": [p["id"] for p, _ in follow_ups(data)],
        "goals": [dict(g, **goal_progress(data, g)) for g in data["goals"] if g.get("status") in ("active", "done")],
        "guide": guide_name(data),
        "onboarding": onboarding(data, ws), "todos": todos(data), "growth": growth(data),
        "signals_n": len(data["signals"]),
        "tags": sorted([dict(d, pattern=True) for d in pulls + pushes] + [dict(d, pattern=False) for d in hunches],
                       key=lambda d: -abs(d["sum"])),
        "quotes": [{"about": s.get("about"), "why": s.get("why"), "date": s.get("date"), "source": s.get("source", "")}
                   for s in reversed(data["signals"]) if (s.get("why") or "").strip()
                   and s.get("why") != "no reason given"][:12],
        "generated": today(),
    }


def render_md(data):
    m = data["meta"]
    pulls, pushes, hunches = derive_pulls(data)
    L = [f"# {m.get('name') + '’s ' if m.get('name') else ''}Career Map", "",
         f"*Updated {today()}. Claude rewrites this page; open Career Map.html for the interactive version.*", ""]
    if m.get("destination"):
        L += ["## Where this is heading", "", m["destination"], ""]
    goals = [g for g in data["goals"] if g.get("status") in ("active", "done")]
    if goals:
        L += ["## Your goals", ""]
        for g in goals:
            gp = goal_progress(data, g)
            L.append(f"- {'✅' if gp['pace'] == 'reached' or g.get('status') == 'done' else '◻️'} **{g['text']}** · {gp['have']}/{gp['target']} by {g['due']} ({gp['pace']})"
                     + (f"\n  - Why: {g['why']}" if g.get("why") else "") + (f"\n  - Next step: {g['next_step']}" if g.get("next_step") else ""))
        L.append("")
    L += ["## What pulls you", ""]
    L += [f"- **{d['tag']}** ({d['pos']} signals)" for d in pulls] or ["- Not enough signals yet. Three reactions in the same direction make a pattern."]
    L += ["", "## What pushes you away", ""]
    L += [f"- **{d['tag']}** ({d['neg']} signals)" for d in pushes] or ["- Nothing clear yet."]
    if hunches:
        L += ["", "Hunches so far: " + ", ".join(d["tag"] for d in hunches[:10])]
    L += ["", "## Industries", ""]
    order = {k: i for i, k in enumerate(["drawn", "curious", "unrated", "meh", "no"])}
    for i in sorted(data["industries"], key=lambda x: (order.get(x.get("interest"), 9), x["name"])):
        orgs = [o for o in data["orgs"] if i["id"] in o.get("industries", [])]
        star = " ✦ wildcard" if i.get("origin") == "wildcard" else ""
        L.append(f"### {i['name']} · {i.get('interest')}{star}")
        if i.get("blurb"):
            L.append(i["blurb"])
        if i.get("why_her"):
            L.append(f"*Why it might fit:* {i['why_her']}")
        for o in orgs:
            ppl = [p for p in data["people"] if p.get("org") == o["id"]]
            link = f"[{o['name']}]({o['url']})" if o.get("url") else o["name"]
            L.append(f"- {link}" + (f" ({o['location']})" if o.get("location") else "") +
                     (f": {o['blurb']}" if o.get("blurb") else "") +
                     (f" · people: " + ", ".join(f"{p['name']} [{p['status']}]" for p in ppl) if ppl else ""))
        L.append("")
    if data["roles"]:
        L += ["## Roles", ""]
        for r in sorted(data["roles"], key=lambda x: (order.get(x.get("interest"), 9), x["name"])):
            L.append(f"- **{r['name']}** · {r.get('interest')}" + (f": {r['blurb']}" if r.get("blurb") else ""))
        L.append("")
    if data["people"]:
        L += ["## People", ""]
        for s in PIPELINE:
            grp = [p for p in data["people"] if p.get("status") == s]
            if grp:
                L.append(f"**{s}**: " + "; ".join(f"{p['name']} ({org_name(data, p.get('org'))})" for p in grp))
        L.append("")
    openq = [q for q in data["questions"] if q.get("status") == "open"]
    done = [q for q in data["questions"] if q.get("status") == "resolved"]
    if openq or done:
        L += ["## Questions", ""]
        L += [f"- [ ] {q['text']} ({q['type']})" for q in openq]
        L += [f"- [x] {q['text']}: {(q.get('resolution') or {}).get('learned', '')}" for q in done]
        L.append("")
    return "\n".join(L) + "\n"


HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=IBM+Plex+Serif:ital,wght@0,400;1,400&family=Geist+Mono:wght@400;500&display=swap">
<style>
/* BunkerOS design system (Paper: "BunkerOS — Design System and Demo Screens"), light only by design.
   Layout: 240px sidebar with her goals pinned + one white surface per view (Today, Map, Organisations, People, About you). */
:root{
  --bg:#F5F6F8; --surface:#FFFFFF; --panel:#FAFBFC; --s2:#EFF0F1; --s3:#E4E5E7;
  --text:#080A0F; --muted:#616368; --faint:#A8A9AC; --line:#EFF0F1; --ring:rgb(8 10 15 / 8%);
  --accent:#3B83F6; --accent-ink:#2A78D6; --accent-soft:#E9F1FD; --accent-line:#D0E2FE;
  --ai:#8658E1; --ai-soft:#F3EEFC; --ai-ink:#5B3BB0;
  --done:#00983A; --done-soft:#E6F2EB; --done-ink:#006B29;
  --await:#C78200; --await-soft:#FFF4DB; --await-ink:#9A6400;
  --block:#DF202E; --block-soft:#FDECEC; --block-ink:#B4141F; --push:#E34948; --star:#EDA100;
  --sans:Inter,system-ui,-apple-system,"Segoe UI",sans-serif; --serif:"IBM Plex Serif",Georgia,serif; --mono:"Geist Mono",ui-monospace,Menlo,monospace;
  color-scheme:light;
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 var(--sans);-webkit-font-smoothing:antialiased}
button{font:inherit;color:inherit;cursor:pointer;background:none;border:0;padding:0}
a{color:var(--accent-ink);text-decoration:none}a:hover{text-decoration:underline}
.app{display:grid;grid-template-columns:240px minmax(0,1fr);min-height:100%}
/* sidebar */
.side{display:flex;flex-direction:column;gap:18px;padding:12px;position:sticky;top:0;height:100vh}
.brand{display:flex;align-items:center;gap:8px;padding:6px 6px 0;font-weight:600;letter-spacing:-.01em}
.brand i{width:22px;height:22px;border-radius:6px;background:var(--text);display:grid;place-items:center}.brand i:after{content:"";width:8px;height:8px;border-radius:50%;background:var(--accent)}
.card{background:var(--surface);border-radius:10px;box-shadow:0 1px 2px rgb(0 0 0 / 5%),0 0 0 1px var(--ring)}
.persona{display:flex;align-items:center;gap:10px;padding:8px}
.av{flex:none;width:28px;height:28px;border-radius:50%;display:grid;place-items:center;font-size:11px;font-weight:600;background:var(--accent-soft);color:var(--accent-ink)}
.av.lg{width:32px;height:32px}
.persona b{display:block;font-size:13px;font-weight:500}.persona small{display:block;font-size:11px;color:var(--muted)}
.nav{display:flex;flex-direction:column;gap:2px}
.nav button{display:flex;align-items:center;gap:10px;height:30px;padding:0 8px;border-radius:8px;font-size:13px;text-align:left}
.nav button:hover{background:var(--s2)}.nav button.on{background:var(--s3);font-weight:500}
.nav svg{flex:none;width:16px;height:16px}.nav span{flex:1}
.nav em{font-style:normal;font:11px var(--mono);color:var(--muted)}
.nav .badge{flex:none;font:600 11px/16px var(--sans);color:#fff;background:var(--accent);border-radius:999px;padding:0 6px}
.goals{margin-top:auto;padding:14px;display:flex;flex-direction:column;gap:12px}
.lbl{font:10.5px/16px var(--mono);letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}
.goal{display:flex;flex-direction:column;gap:6px;font-size:12px;line-height:16px}
.bar{flex:1;height:5px;border-radius:999px;background:var(--s2);overflow:hidden}.bar i{display:block;height:100%;border-radius:999px;background:var(--accent)}
.goal .r{display:flex;align-items:center;gap:8px}.goal .r em{font:11px var(--mono);font-style:normal;color:var(--muted)}
/* main */
.main{padding:8px 8px 8px 0;min-width:0}
.surface{background:var(--surface);border-radius:10px;box-shadow:0 0 1px rgb(0 0 0 / 30%);min-height:calc(100vh - 16px);padding:36px 40px 32px 48px;display:flex;flex-direction:column;gap:22px}
.head{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;flex-wrap:wrap}
.head h1{font:400 30px/36px var(--serif);letter-spacing:-.02em;margin:0;text-wrap:balance}
.head p{margin:6px 0 0;color:var(--muted);font-size:14px;max-width:70ch}
.acts{display:flex;gap:8px;flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;gap:6px;height:30px;padding:0 12px;border-radius:8px;background:var(--surface);box-shadow:0 0 0 1px var(--ring);font-size:12px;font-weight:500;white-space:nowrap}
.btn:hover{background:var(--panel)}.btn.pri{background:var(--accent);color:#fff;box-shadow:none}.btn.pri:hover{background:#2F74E4}
.btn:focus-visible,.nav button:focus-visible,.row:focus-visible,g.ind:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.pill{display:inline-flex;align-items:center;gap:5px;padding:2px 8px;border-radius:999px;font-size:11px;line-height:16px;font-weight:500;white-space:nowrap}
.pill.accent{background:var(--accent-soft);color:var(--accent-ink)}.pill.done{background:var(--done-soft);color:var(--done)}.pill.ai{background:var(--ai-soft);color:var(--ai-ink)}
.pill.await{background:var(--await-soft);color:var(--await-ink)}.pill.block{background:var(--block-soft);color:var(--block-ink)}.pill.grey{background:var(--s2);color:var(--muted)}
.pill.dark{background:var(--text);color:#fff}.pill.line{box-shadow:0 0 0 1px rgb(0 0 0 / 12%);color:var(--muted)}
.pill .d{width:6px;height:6px;border-radius:50%;background:currentColor}.tr .pill{max-width:100%;overflow:hidden;text-overflow:ellipsis}
.h2{font-size:15px;line-height:20px;font-weight:600;margin:0}
.muted{color:var(--muted)}.small{font-size:12px;line-height:16px}
.cols{display:grid;gap:24px;align-items:start}
.empty{color:var(--muted);font-size:13px;padding:12px 0}
.estate{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;padding:48px 24px;border-radius:12px;border:1.5px dashed rgb(0 0 0 / 9%);text-align:center;min-height:420px}
.estate .ic{width:44px;height:44px;border-radius:12px;background:var(--accent-soft);display:grid;place-items:center;color:var(--accent-ink)}
.estate h2{font:400 22px/28px var(--serif);margin:0}.estate p{margin:0;max-width:440px;color:var(--muted);font-size:14px;line-height:21px}
.dashbox{padding:16px;border-radius:10px;border:1.5px dashed rgb(0 0 0 / 9%);display:flex;flex-direction:column;gap:10px}
.softbox{padding:16px;border-radius:10px;background:#F2F7FE;box-shadow:0 0 0 1px var(--accent-line);display:flex;flex-direction:column;gap:10px}
.next.ok{background:#F1F8F3;box-shadow:0 0 0 1px #CFE6D8}.next.ok .k{color:var(--done-ink)}
.why{display:block;font-size:11px;color:var(--done-ink)}
.mono{font-family:var(--mono)}
/* Today */
.next{padding:18px 20px;border-radius:10px;background:#F2F7FE;box-shadow:0 0 0 1px var(--accent-line);display:flex;flex-direction:column;gap:10px}
.next .k{font-size:11px;font-weight:500;color:var(--accent-ink)}.next h2{font:400 22px/28px var(--serif);margin:0}
.say{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.say code{font:12px var(--mono);background:#fff;border-radius:6px;padding:4px 8px;box-shadow:0 0 0 1px var(--ring)}
.list{border-radius:10px;box-shadow:0 0 0 1px var(--ring);overflow:hidden;background:#fff}
.li{display:flex;align-items:center;gap:12px;padding:12px 14px;border-bottom:1px solid var(--line)}.li:last-child{border-bottom:0}
.li .box{flex:none;width:16px;height:16px;border-radius:5px;box-shadow:inset 0 0 0 1.5px rgb(0 0 0 / 20%)}
.li .t{flex:1;min-width:0}.li .t b{display:block;font-size:13px;font-weight:500}.li .t small{display:block;font-size:12px;color:var(--muted)}
.step{display:flex;align-items:center;gap:10px;min-height:30px;font-size:13px}.step .c{flex:none;width:18px;height:18px;border-radius:50%;box-shadow:inset 0 0 0 1.5px rgb(0 0 0 / 16%)}
.step .c.nx{box-shadow:inset 0 0 0 2px var(--accent)}.step .c.done{background:var(--done);box-shadow:none;display:grid;place-items:center}
.step span{flex:1}.step span.c{flex:none}.step code{font:11px var(--mono);color:var(--muted);background:var(--s2);border-radius:5px;padding:1px 6px}
.mets{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--s2);border-radius:10px;overflow:hidden;box-shadow:0 0 0 1px var(--ring)}
.mets div{background:#fff;padding:10px 12px}.mets b{font-size:20px;line-height:24px;font-weight:600}.mets em{font-style:normal;font-size:11px;font-weight:600;color:var(--done);margin-left:6px}.mets small{display:block;font-size:11px;color:var(--muted)}
.ag{display:flex;gap:10px;padding:8px 0}.ag i{flex:none;width:7px;height:7px;border-radius:50%;background:var(--ai);margin-top:6px}.ag small{display:block;color:var(--muted);font-size:12px}
/* Map */
.mapwrap{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:24px;align-items:start}
.canvas{border-radius:10px;background:var(--panel);box-shadow:0 0 0 1px var(--ring);padding:8px;position:relative}
.canvas svg{width:100%;height:auto;display:block}
g.ind{cursor:pointer;transition:opacity .35s ease,transform .35s ease}g.ind:hover circle.n{stroke-width:2.5}
.hide{opacity:0}
.legend{display:flex;flex-wrap:wrap;gap:14px;padding:6px 8px 4px;font-size:12px;color:var(--muted)}.legend i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px;vertical-align:-1px}
.panel{display:flex;flex-direction:column;gap:18px}
.panel h2{font:400 22px/28px var(--serif);margin:0}
.trio{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--s2);border-radius:10px;overflow:hidden;box-shadow:0 0 0 1px var(--ring)}
.trio div{background:#fff;padding:10px 12px}.trio b{display:block;font-size:20px;line-height:24px;font-weight:600}.trio small{font-size:11px;color:var(--muted)}
.orow{display:flex;align-items:center;gap:10px;padding:10px 0;border-top:1px solid var(--line)}
.logo{flex:none;width:28px;height:28px;border-radius:6px;background:var(--s2);display:grid;place-items:center;font-size:11px;font-weight:600;color:var(--muted)}
.orow .t{flex:1;min-width:0}.orow b{display:block;font-size:13px;font-weight:500}.orow small{display:block;font-size:12px;color:var(--muted)}
.quote{padding:12px 14px;border-radius:10px;background:var(--panel);border-left:2px solid var(--accent)}
.quote q{display:block;font:italic 14px/21px var(--serif);quotes:"“" "”"}.quote small{display:block;margin-top:4px;font-size:11px;color:var(--muted)}
/* Organisations */
.filters{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.search{display:flex;align-items:center;gap:8px;height:32px;padding:0 10px;border-radius:8px;box-shadow:0 0 0 1px rgb(0 0 0 / 10%);background:#fff;width:200px}
.search input{border:0;outline:0;font:13px var(--sans);width:100%;background:transparent;color:var(--text)}
.seg{display:flex;gap:2px;padding:3px;border-radius:8px;background:var(--s2)}
.seg button{display:flex;align-items:center;gap:5px;padding:4px 10px;border-radius:6px;font-size:12px;color:var(--muted);white-space:nowrap}
.seg button em{font:11px var(--mono);font-style:normal;color:var(--faint)}.seg button.on{background:#fff;color:var(--text);font-weight:500;box-shadow:0 1px 2px rgb(0 0 0 / 5%)}
select{font:12px var(--sans);height:32px;padding:0 8px;border-radius:8px;border:0;box-shadow:0 0 0 1px rgb(0 0 0 / 10%);background:#fff;color:var(--text)}
.orgwrap{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:20px;align-items:start}
.table{border-radius:10px;box-shadow:0 0 0 1px var(--ring);overflow:hidden;background:#fff}
.tr{display:grid;grid-template-columns:minmax(0,1fr) 104px 70px 120px 56px 24px;gap:12px;align-items:center;padding:8px 14px;border-bottom:1px solid var(--line)}
.th{height:34px;padding-block:0;background:var(--panel)}.th div{font:10.5px/16px var(--mono);letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}
.grp{display:flex;align-items:center;gap:8px;height:36px;padding:0 14px;background:var(--panel);border-bottom:1px solid var(--line);font-size:12px;font-weight:600}
.grp i{width:7px;height:7px;border-radius:50%}.grp em{font:11px var(--mono);font-style:normal;color:var(--faint);font-weight:400}
.row{min-height:54px;cursor:pointer;font-size:12px}.row:hover{background:#FAFCFF}.row.sel{background:#F4F8FE;box-shadow:inset 2px 0 0 var(--accent)}
.row .n b{display:block;font-size:13px;font-weight:500;line-height:18px}.row .n small{display:block;color:var(--muted);line-height:16px}
.dash{color:var(--faint)}
.star{display:grid;place-items:center}
.drawer{padding:18px;display:flex;flex-direction:column;gap:16px;position:sticky;top:16px;box-shadow:0 1px 2px rgb(0 0 0 / 5%),0 0 0 1px var(--ring),0 8px 24px rgb(0 0 0 / 6%)}
.drawer h2{font:400 20px/26px var(--serif);margin:0}
.route{padding:12px;border-radius:10px;background:var(--done-soft);display:flex;flex-direction:column;gap:6px;font-size:12px;line-height:18px;color:#1F4D2E}
.route b{color:var(--done-ink);font-weight:600}
/* People */
.pipe{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));border-radius:10px;box-shadow:0 0 0 1px var(--ring);overflow:hidden}
.pipe div{padding:12px 16px;border-right:1px solid var(--line)}.pipe div:last-child{border:0}.pipe b{display:block;font-size:22px;line-height:28px;font-weight:600}.pipe small{font-size:12px;color:var(--muted)}
.pipe .acc{background:#F4F8FE;color:var(--accent-ink)}.pipe .aw{background:#FFFAEE;color:var(--await-ink)}.pipe .dn{color:var(--done)}.pipe .acc small,.pipe .aw small,.pipe .dn small{color:inherit;font-weight:500}
.act{padding:14px;display:flex;flex-direction:column;gap:10px}
.act .top{display:flex;align-items:center;gap:10px}.act .top .t{flex:1;min-width:0}.act .top b{display:block;font-size:13px;font-weight:600}.act .top small{display:block;font-size:12px;color:var(--muted)}
.msg{padding:10px 12px;border-radius:8px;background:var(--panel);font-size:13px;line-height:19px;white-space:pre-wrap}.msg .lbl{font-size:10px;line-height:14px}
.sec{height:28px;display:flex;align-items:center;padding:0 12px;background:var(--panel);border-bottom:1px solid var(--line);font:10px var(--mono);letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}
.prow{display:flex;align-items:center;gap:10px;padding:10px 12px;border-bottom:1px solid var(--line)}.prow .t{flex:1;min-width:0}.prow b{display:block;font-size:13px;font-weight:500}.prow small{display:block;font-size:12px;color:var(--muted)}
.prow .r{display:flex;flex-direction:column;align-items:flex-end;gap:3px;font-size:11px;color:var(--muted);text-align:right}
/* About */
.bars{padding:18px 20px;display:flex;flex-direction:column;gap:6px}
.brow{display:grid;grid-template-columns:150px minmax(0,1fr) 78px 64px;gap:12px;align-items:center;min-height:32px;font-size:13px}
.track{display:grid;grid-template-columns:1fr 1px 1fr;align-items:center;height:32px}.track .ax{height:32px;background:#D9DADC}
.track .l{display:flex;justify-content:flex-end}.track i{display:block;height:12px}
.brow .cnt{font:11px var(--mono);color:var(--muted);text-align:right;white-space:nowrap}
.chips{display:flex;flex-wrap:wrap;gap:6px}.chip{padding:4px 10px;border-radius:8px;background:#fff;box-shadow:0 0 0 1px var(--ring);font-size:12px}
.rg{display:flex;flex-direction:column;gap:6px}.rg .h{display:flex;align-items:center;gap:6px;font-size:12px;font-weight:600}.rg .h i{width:7px;height:7px;border-radius:50%}.rg .h em{font:11px var(--mono);font-style:normal;color:var(--faint);font-weight:400}
/* responsive */
@media (max-width:1180px){.mapwrap,.orgwrap{grid-template-columns:1fr}.drawer{position:static}}
@media (max-width:820px){
  .app{grid-template-columns:1fr}.side{position:static;height:auto;gap:10px;padding:12px 16px}
  .nav{flex-direction:row;overflow-x:auto}.nav button{flex:none}.persona,.goals{display:none}
  .main{padding:0 8px 8px}.surface{padding:24px 16px;min-height:0}
  .cols{grid-template-columns:1fr!important}.pipe{grid-template-columns:repeat(3,1fr)}.mets{grid-template-columns:repeat(2,1fr)}
  .tr{grid-template-columns:minmax(0,1fr) 92px 24px}.tr>:nth-child(2),.tr>:nth-child(3),.tr>:nth-child(5){display:none}
  .brow{grid-template-columns:110px minmax(0,1fr) 56px}.brow .cnt{display:none}
}
@media (prefers-reduced-motion:reduce){g.ind{transition:none}}
</style></head><body>
<div class="app"><aside class="side" id="side"></aside><main class="main"><div class="surface" id="view"></div></main></div>
<script>
const D=__DATA__;
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const orgById=Object.fromEntries(D.orgs.map(o=>[o.id,o])),indById=Object.fromEntries(D.industries.map(i=>[i.id,i]));
const LEVEL={drawn:0,curious:1,unrated:2,meh:3,no:4};
const REACT={drawn:['Drawn to','accent'],curious:['Curious','accent'],unrated:['Not yet rated','grey'],meh:['Meh','await'],no:['Not for me','block']};
const first=n=>String(n||'').split(' ')[0];
const initials=n=>String(n||'?').split(/\s+/).filter(w=>/^[A-Za-z0-9]/.test(w)).slice(0,2).map(w=>w[0]).join('').toUpperCase()||'?';
const link=(u,t)=>/^https?:/.test(u||'')?`<a href="${esc(u)}" target="_blank" rel="noopener">${esc(t)}</a>`:esc(t);
const peopleAt=id=>D.people.filter(p=>p.org===id);
const orgsIn=id=>D.orgs.filter(o=>(o.industries||[]).includes(id));
const pill=(t,k)=>`<span class="pill ${k}">${esc(t)}</span>`;
const STAR='<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="m8 2.2 1.8 3.7 4 .6-2.9 2.8.7 4L8 11.4l-3.6 1.9.7-4-2.9-2.8 4-.6L8 2.2Z" fill="var(--star)"/></svg>';
const STAR0='<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="m8 2.2 1.8 3.7 4 .6-2.9 2.8.7 4L8 11.4l-3.6 1.9.7-4-2.9-2.8 4-.6L8 2.2Z" stroke="#C9CACD" stroke-width="1.1" stroke-linejoin="round"/></svg>';
const name=D.meta.name||'You';
let view='today',selInd=null,selOrg=null,ofilter='all',oq='',osort='close';
try{const h=location.hash.replace('#','');if(['today','map','orgs','people','you'].includes(h))view=h}catch(e){}

/* ---------- shell ---------- */
const ICON={today:'<path d="M3 7.5 8 3l5 4.5V13H3V7.5Z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/>',
 map:'<circle cx="8" cy="8" r="5.5" stroke="currentColor" stroke-width="1.3"/><circle cx="8" cy="8" r="2" fill="currentColor"/>',
 orgs:'<rect x="3" y="2.5" width="10" height="11" rx="1.5" stroke="currentColor" stroke-width="1.3"/><path d="M6 6h1M9 6h1M6 9h1M9 9h1" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>',
 people:'<circle cx="6" cy="6" r="2.3" stroke="currentColor" stroke-width="1.3"/><path d="M2 13c.5-2.2 2-3.3 4-3.3s3.5 1.1 4 3.3M10.5 3.8a2.2 2.2 0 0 1 0 4.4M12 9.9c1 .5 1.7 1.5 2 3.1" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>',
 you:'<path d="M8 13.5S2.5 10.3 2.5 6.4A2.9 2.9 0 0 1 8 4.8a2.9 2.9 0 0 1 5.5 1.6c0 3.9-5.5 7.1-5.5 7.1Z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/>'};
function side(){
  const nav=[['today','Today',D.todos.length?`<span class="badge">${D.todos.length}</span>`:''],['map','Map',`<em>${D.industries.length}</em>`],['orgs','Organisations',`<em>${D.orgs.length}</em>`],['people','People',`<em>${D.people.length}</em>`],['you','About you','']];
  const goals=D.goals.filter(g=>g.status==='active');
  const worst=goals.some(g=>g.pace==='past due')?['Needs a look','var(--block-ink)']:goals.some(g=>g.pace==='behind')?['A bit behind','var(--await-ink)']:['On track','var(--done)'];
  $('#side').innerHTML=`<div class="brand"><i></i>Career Wayfinder</div>
  <div class="card persona"><span class="av">${esc(initials(name))}</span><div><b>${esc(name)}'s map</b><small>Kept by ${esc(D.guide)}</small></div></div>
  <nav class="nav">${nav.map(([k,l,x])=>`<button class="${k===view?'on':''}" data-v="${k}" aria-current="${k===view?'page':'false'}"><svg viewBox="0 0 16 16" fill="none" style="color:${k===view?'var(--text)':'var(--muted)'}">${ICON[k]}</svg><span>${l}</span>${x}</button>`).join('')}</nav>
  ${goals.length?`<div class="card goals"><div style="display:flex;justify-content:space-between"><span class="lbl">Your goals</span><span class="small" style="color:${worst[1]};font-weight:500">${worst[0]}</span></div>
   ${goals.map(g=>`<div class="goal"><div>${esc(g.text)}</div><div class="r"><div class="bar"><i style="width:${Math.max(g.pct,g.have?0:4)}%;background:${g.pace==='behind'||g.pace==='past due'?'var(--await)':'var(--accent)'}"></i></div><em>${g.have}/${g.target}</em></div></div>`).join('')}</div>`
   :`<div class="card goals" style="gap:8px"><span class="lbl">Your goals</span><div class="small">No goals yet. Once you've explored a little, you'll set two to four small ones together.</div><div><code class="mono" style="font-size:11px;color:var(--muted);background:var(--s2);border-radius:5px;padding:1px 6px">/my-goals</code></div></div>`}`;
  document.querySelectorAll('.nav button').forEach(b=>b.onclick=()=>go(b.dataset.v));
}
function go(v,opts){view=v;Object.assign(window,{});if(opts&&opts.industry)oind=opts.industry;try{history.replaceState(null,'','#'+v)}catch(e){}draw();window.scrollTo(0,0)}
let oind='';
function head(title,sub,acts){return `<div class="head"><div><h1>${esc(title)}</h1><p>${esc(sub)}</p></div><div class="acts">${acts||''}</div></div>`}
function say(phrase,lead){return `<div class="say"><span class="small muted">${esc(lead||'In your chat, say')}</span><code>${esc(phrase)}</code>${copyBtn(phrase,'Copy')}</div>`}
function estate(icon,title,body,phrase){return `<div class="estate"><span class="ic"><svg width="22" height="22" viewBox="0 0 16 16" fill="none">${ICON[icon]}</svg></span><h2>${esc(title)}</h2><p>${esc(body)}</p>${say(phrase)}</div>`}
function copyBtn(text,label,cls){return `<button class="btn ${cls||''}" data-copy="${esc(text)}">${esc(label||'Copy')}</button>`}

/* ---------- Today ---------- */
function todayView(){
  const h=new Date().getHours(),greet=!D.signals_n&&!D.orgs.length?'Welcome':h<12?'Good morning':h<18?'Good afternoon':'Good evening';
  const t=D.todos,top=t[0],rest=t.slice(1,4);
  const nx=D.onboarding.find(s=>s.state==='todo'&&!s.optional);
  let next;
  if(top){const p=top.person&&D.people.find(x=>x.id===top.person);const ask={reply:`help me answer ${first(p&&p.name)}`,thanks:`help me thank ${first(p&&p.name)}`,'follow-up':`draft a follow-up for ${first(p&&p.name)}`,send:`I sent my note to ${first(p&&p.name)}`,draft:'help me reach out',react:'show me some industries'}[top.kind]||'what should I do today?';
    const why={reply:'They replied. A quick, friendly answer keeps the conversation going.',thanks:'A short thank-you within a day is what people remember.','follow-up':"It's been a week. One gentle nudge is normal and polite.",send:'Your message is drafted and waiting. Sending is the hardest step, and it takes a minute.',draft:'Your guide is ready to draft notes for the people you picked.',react:'These are industries your guide thinks you might not have considered.'}[top.kind]||'';
    next={k:'Do this next',title:top.text,why,ask,draft:p&&top.kind==='send'?p.draft:''};}
  else if(nx){next={k:'Next on your getting-started list',title:nx.label,why:`Type ${nx.command} in your chat with ${D.guide}, or just say what you want to do.`,ask:nx.command}}
  else next={k:'You\'re all caught up',title:'Nothing is waiting on you',why:'Messages are out and nothing needs an answer. Want something new while you wait?',ask:'what should I do today?',ok:true};
  const req=D.onboarding.filter(s=>!s.optional),done=req.filter(s=>s.state!=='todo').length;
  const steps=D.onboarding.filter(s=>s.state==='todo').slice(0,4),lastDone=D.onboarding.filter(s=>s.state==='done').slice(-1);
  const G=D.growth,mets=[[D.industries.length,'industries',G.industries],[D.orgs.length,'organisations',G.orgs],[D.people.length,'people',G.people],[D.people.filter(p=>['replied','chatted','thanked'].includes(p.status)).length,'replies',0]];
  return head(`${greet}, ${name}`,greet==='Welcome'?"Your guide is setting things up with you. Here's the first step.":t.length?"Here's where you are, and the one thing worth doing first.":"Nothing is waiting on you. Here's where things stand.")+
  `<div class="cols" style="grid-template-columns:minmax(0,1.35fr) minmax(0,1fr)"><div style="display:flex;flex-direction:column;gap:22px">
   <section class="next ${next.ok?'ok':''}"><span class="k">${esc(next.k)}</span><h2>${esc(next.title)}</h2><div class="muted">${esc(next.why)}</div>
    ${next.draft?`<div class="msg">${esc(next.draft)}</div>`:''}
    <div class="say">${next.draft?copyBtn(next.draft,'Copy message','pri'):''}<span class="small muted">In your chat, say</span><code>${esc(next.ask)}</code>${copyBtn(next.ask,'Copy')}</div></section>
   <section style="display:flex;flex-direction:column;gap:8px"><div style="display:flex;justify-content:space-between"><h3 class="h2">Your to-dos</h3><span class="small muted">${t.length>4?(t.length-4)+' more after these':''}</span></div>
    ${rest.length?`<div class="list">${rest.map(x=>`<div class="li"><span class="box"></span><div class="t"><b>${esc(x.text)}</b><small>${esc({reply:'They replied',thanks:'After your conversation','follow-up':'No reply yet',send:'Message ready to copy',draft:'Picked, not yet drafted',react:'Wildcards from your guide','try-it':'Something to try','think-it':'Something to think about'}[x.kind]||'')}</small></div>${pill({reply:'Replied',thanks:'Thank-you','follow-up':'Follow-up',send:'Ready to send',draft:'To draft',react:'Wildcards'}[x.kind]||x.kind,{reply:'await',thanks:'done','follow-up':'block',send:'accent',draft:'grey',react:'ai'}[x.kind]||'grey')}</div>`).join('')}</div>`:`<div class="dashbox muted" style="font-size:13px">${t.length?'Nothing else waiting on you. Nice.':'Nothing waiting on you yet. As your map grows, replies to answer and messages to send show up here.'}</div>`}</section></div>
  <div style="display:flex;flex-direction:column;gap:22px">
   ${done<req.length?`<section class="card" style="padding:16px 18px;display:flex;flex-direction:column;gap:8px"><div style="display:flex;justify-content:space-between"><b style="font-size:14px">Getting started</b><span class="mono small muted">${done} of ${req.length}</span></div><div class="bar" style="flex:none"><i style="width:${100*done/req.length}%;background:var(--done)"></i></div>
    <div>${lastDone.map(s=>`<div class="step"><span class="c done"><svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="m2.2 5.2 1.8 1.8 3.8-4" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></span><span class="muted">${esc(s.label)}</span><code>${esc(s.command)}</code></div>`).join('')}
    ${steps.map((s,i)=>`<div class="step"><span class="c ${i===0?'nx':''}"></span><span style="${i===0?'font-weight:500':''}">${esc(s.label)}${s.optional?' <span class="muted small">(optional)</span>':''}</span><code>${esc(s.command)}</code></div>`).join('')}</div></section>`:''}
   <section style="display:flex;flex-direction:column;gap:8px"><span class="lbl">Your map this week</span><div class="mets">${mets.map(([n,l,g])=>`<div><b>${n}</b>${g?`<em>+${g}</em>`:''}<small>${l}</small></div>`).join('')}</div></section>
   <section><span class="lbl">What ${esc(D.guide)} is working on</span>${D.agenda.length?D.agenda.slice(0,4).map(a=>`<div class="ag"><i></i><div>${esc(a.text)}${a.why?`<small>${esc(a.why)}</small>`:''}</div></div>`).join(''):'<p class="empty">Nothing queued. Ask what to do next.</p>'}</section>
  </div></div>`;
}

/* ---------- Map ---------- */
function wrap(s,n){const w=String(s).split(' '),L=[];let c='';for(const x of w){if((c+' '+x).trim().length>n&&c){L.push(c);c=x}else c=(c+' '+x).trim()}L.push(c);return L.slice(0,3)}
function mapSvg(){
  const W=920,H=680,cx=W/2,cy=H/2,R={0:110,1:200,2:282};
  const shown=D.industries.filter(i=>i.interest!=='no'||orgsIn(i.id).length);
  const ring=i=>i.interest==='drawn'?0:i.interest==='curious'?1:2;
  /* every industry gets its own angle; rings interleave evenly so labels never stack (same rule as the Paper mockups) */
  const N=shown.length,stepA=360/Math.max(1,N),keyed=[];
  [0,1,2].forEach(r=>{const g=shown.filter(i=>ring(i)===r);g.forEach((ind,k)=>keyed.push([(k+.5)*N/g.length+r*.01,ind.id]))});
  keyed.sort((x,y)=>x[0]-y[0]);const pos={};keyed.forEach(([_,id],slot)=>pos[id]=-90+stepA/2+slot*stepA);
  let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Your map: industries placed closer to you the more they pull you">`;
  [0,1,2].forEach(r=>s+=`<circle cx="${cx}" cy="${cy}" r="${R[r]}" fill="none" stroke="#E4E5E7" ${r?'stroke-dasharray="3 5"':''}/>`);
  let seq=0;
  shown.slice().sort((a,b)=>String(a.created||'').localeCompare(String(b.created||''))).forEach(ind=>{
    const r=ring(ind),a=pos[ind.id]*Math.PI/180,x=cx+R[r]*Math.cos(a),y=cy+R[r]*Math.sin(a),n=orgsIn(ind.id).length,nr=n?Math.min(30,7+n*2.1):6;
    const lv=ind.interest,sel=ind.id===selInd;
    const fill=lv==='drawn'?'#3B83F6':lv==='curious'?'#E9F1FD':lv==='meh'?'#FBF3E2':lv==='no'?'#FDECEC':'#FFFFFF';
    const stroke=lv==='drawn'||lv==='curious'?'#3B83F6':lv==='meh'?'#C78200':lv==='no'?'#E34948':'#A8A9AC';
    const tc=lv==='drawn'?'#FFFFFF':lv==='curious'?'#2A78D6':'#616368';
    const c=Math.cos(a),anc=c>.3?'start':c<-.3?'end':'middle';
    const L=wrap(ind.name,20);let lx=x+(nr+12)*c,ly;
    if(anc==='middle'){ly=Math.sin(a)>0?y+nr+16:y-nr-8-(L.length-1)*14}else ly=y+4-(L.length-1)*7;
    s+=`<g class="ind" data-id="${esc(ind.id)}" data-seq="${seq++}" tabindex="0" role="button" aria-label="${esc(ind.name)}, ${esc(REACT[lv]?REACT[lv][0]:lv)}, ${n} organisations">
      <line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="${lv==='drawn'?'#3B83F6':'#E4E5E7'}" stroke-opacity="${lv==='drawn'?.35:1}" stroke-width="${lv==='drawn'?1.5:1}"/>
      ${sel?`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${nr+7}" fill="#3B83F6" fill-opacity=".16"/>`:''}
      <circle class="n" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${nr.toFixed(1)}" fill="${fill}" stroke="${stroke}" stroke-width="${sel?2.5:1.5}"/>
      ${n&&nr>=11?`<text x="${x.toFixed(1)}" y="${(y+4).toFixed(1)}" text-anchor="middle" font-family="Inter, sans-serif" font-size="11" font-weight="600" fill="${tc}">${n}</text>`:''}
      <text x="${lx.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="${anc}" font-family="Inter, sans-serif" font-size="12" font-weight="${lv==='drawn'||sel?600:400}" fill="${lv==='drawn'||lv==='curious'||sel?'#080A0F':'#616368'}">${L.map((t,i)=>`<tspan x="${lx.toFixed(1)}" dy="${i?14:0}">${esc(t)}</tspan>`).join('')}</text>
      ${ind.origin==='wildcard'?`<circle cx="${(x+nr*.75).toFixed(1)}" cy="${(y-nr*.75).toFixed(1)}" r="6" fill="#8658E1"/><path d="M${(x+nr*.75).toFixed(1)} ${(y-nr*.75-3.5).toFixed(1)}l1 2.5 2.5 1-2.5 1-1 2.5-1-2.5-2.5-1 2.5-1z" fill="#fff"/>`:''}
    </g>`});
  s+=`<circle cx="${cx}" cy="${cy}" r="30" fill="#080A0F"/><text x="${cx}" y="${cy+5}" text-anchor="middle" font-family="IBM Plex Serif, serif" font-size="${name.length>8?12:15}" fill="#fff">${esc(name)}</text></svg>`;
  return s;
}
function indPanel(ind){
  if(!ind)return '';
  const os=orgsIn(ind.id),routes=os.filter(o=>o.new_grad_program).length,ppl=os.reduce((n,o)=>n+peopleAt(o.id).length,0);
  const top=os.slice().sort((a,b)=>(b.status==='shortlisted')-(a.status==='shortlisted')||(!!b.new_grad_program)-(!!a.new_grad_program)||peopleAt(b.id).length-peopleAt(a.id).length).slice(0,3);
  const q=D.quotes.find(x=>x.about===ind.id||x.about===ind.name);
  const r=REACT[ind.interest]||['',''];
  return `<div style="display:flex;flex-direction:column;gap:10px"><div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap"><span class="pill ${r[1]}"><span class="d"></span>${esc(r[0])}</span>${ind.origin==='wildcard'?pill('✦ Your guide’s wildcard','ai'):''}<span class="small muted">${ind.created?'Added '+esc(ind.created):''}</span></div>
   <h2>${esc(ind.name)}</h2><div class="muted" style="font-size:13px;line-height:20px">${esc(ind.why_her||ind.blurb||'')}</div></div>
   <div class="trio"><div><b>${os.length}</b><small>organisations</small></div><div><b style="color:var(--done)">${routes}</b><small>new-grad routes</small></div><div><b>${ppl}</b><small>people found</small></div></div>
   ${ind.interest==='unrated'&&!os.length?`<div class="softbox"><b style="font-size:13px;font-weight:500">How does this one feel?</b><div class="small muted" style="line-height:18px">React in your chat and it moves closer to you, or drifts away. Nothing is decided yet.</div>${say('show me some industries')}</div>`:
     !os.length?`<div class="dashbox"><b style="font-size:13px;font-weight:500">Nothing found here yet</b><div class="small muted" style="line-height:18px">Your guide hasn't explored this industry yet. It takes a few minutes and you can do something else meanwhile.</div>${say('go explore '+ind.name)}</div>`:''}
   ${os.length?`<div><span class="lbl">Best places to start</span>${top.map(o=>`<div class="orow"><span class="logo">${esc(initials(o.name))}</span><div class="t"><b>${esc(o.name)}</b><small>${esc([o.location,o.size].filter(Boolean).join(' · '))}</small></div>${o.new_grad_program?pill('New-grad route','done'):peopleAt(o.id).length?pill(peopleAt(o.id).length+' people','grey'):''}</div>`).join('')}
   <div style="display:flex;gap:8px;padding-top:12px"><button class="btn pri" data-goind="${esc(ind.id)}" style="flex:1;justify-content:center">See all ${os.length} organisations</button>${copyBtn('find people in '+ind.name,'Find people')}</div></div>`:''}
   ${q?`<div class="quote"><q>${esc(q.why)}</q><small>You, ${esc(q.source||'reacting')} · ${esc(q.date)}</small></div>`:''}`;
}
function mapView(){
  if(!D.industries.length)return head('Your map','The closer an industry sits to you, the more it pulls you. Bigger circles mean more has been found there.')+estate('map','Your map starts here',"Each industry you react to lands here. The ones you're drawn to sit closest to you, and your guide adds a few wildcards you'd never think to search for.",'show me some industries');
  if(!selInd){const d=D.industries.filter(i=>i.interest==='drawn').sort((a,b)=>orgsIn(b.id).length-orgsIn(a.id).length)[0]||D.industries[0];selInd=d&&d.id}
  const wild=D.industries.filter(i=>i.origin==='wildcard'&&i.interest==='unrated').length,unr=D.industries.filter(i=>i.interest==='unrated').length,allUnrated=unr===D.industries.length;
  return head('Your map','The closer an industry sits to you, the more it pulls you. Bigger circles mean more has been found there.',
    (allUnrated?`<span class="pill ai" style="height:30px;border-radius:8px;padding:0 10px"><span class="d"></span>${unr} ideas waiting for your reaction</span>`:wild?`<span class="pill ai" style="height:30px;border-radius:8px;padding:0 10px"><span class="d"></span>${wild} wildcard${wild>1?'s':''} waiting for you</span>`:'')+(allUnrated?'':`<button class="btn" id="replay"><svg width="12" height="12" viewBox="0 0 12 12"><path d="M3 2v8l7-4-7-4Z" fill="currentColor"/></svg>Replay how it grew</button>`))+
  `<div class="mapwrap"><div class="canvas">${mapSvg()}<div class="legend"><span><i style="background:#3B83F6"></i>Drawn to</span><span><i style="background:#E9F1FD;box-shadow:inset 0 0 0 1.5px #3B83F6"></i>Curious</span><span><i style="background:#fff;box-shadow:inset 0 0 0 1.5px #A8A9AC"></i>Not yet rated</span><span><i style="background:#FBF3E2;box-shadow:inset 0 0 0 1.5px #C78200"></i>Meh</span><span><i style="background:#8658E1"></i>Your guide’s wildcard</span><span id="replaylabel"></span></div></div>
   <div class="panel" id="panel">${indPanel(indById[selInd])}</div></div>`;
}
function replay(){const b=$('#replay');if(b){b.textContent='Replaying…';b.style.background='var(--accent-soft)'}const els=[...document.querySelectorAll('g.ind')].sort((a,b)=>a.dataset.seq-b.dataset.seq);els.forEach(e=>e.classList.add('hide'));const lab=$('#replaylabel');let i=0;const step=Math.max(90,Math.min(400,3500/els.length));
  (function t(){if(i>=els.length){lab.textContent='';if(b){b.innerHTML='<svg width="12" height="12" viewBox="0 0 12 12"><path d="M3 2v8l7-4-7-4Z" fill="currentColor"/></svg>Replay how it grew';b.style.background=''}return}els[i].classList.remove('hide');lab.innerHTML=`<b style="color:var(--accent-ink);font-weight:500">Growing… ${i+1} of ${els.length}</b>`;i++;setTimeout(t,step)})()}

/* ---------- Organisations ---------- */
function orgRows(){
  const q=oq.toLowerCase();
  let list=D.orgs.filter(o=>{if(ofilter==='short'&&o.status!=='shortlisted')return false;if(ofilter==='grad'&&!o.new_grad_program)return false;if(ofilter==='people'&&!peopleAt(o.id).length)return false;if(oind&&!(o.industries||[]).includes(oind))return false;if(q&&!JSON.stringify(o).toLowerCase().includes(q))return false;return true});
  return list;
}
function orgsView(){
  if(!D.orgs.length)return head('Organisations','Places your guide finds in the industries you like will show up here.')+estate('orgs','No organisations yet',"When you're drawn to an industry, your guide goes exploring and brings back five to eight places in it, with any programmes for new grads.",'go explore');
  const list=orgRows();
  if(!selOrg||!list.find(o=>o.id===selOrg)){const s=list.find(o=>o.status==='shortlisted')||list[0];selOrg=s&&s.id}
  const C={all:D.orgs.length,short:D.orgs.filter(o=>o.status==='shortlisted').length,grad:D.orgs.filter(o=>o.new_grad_program).length,people:D.orgs.filter(o=>peopleAt(o.id).length).length};
  const groups=[];const seen=new Set();
  const inds=D.industries.slice().sort((a,b)=>(LEVEL[a.interest]??9)-(LEVEL[b.interest]??9));
  const sortFn=osort==='name'?(a,b)=>a.name.localeCompare(b.name):osort==='new'?(a,b)=>String(b.created||'').localeCompare(String(a.created||'')):(a,b)=>(b.status==='shortlisted')-(a.status==='shortlisted')||(!!b.new_grad_program)-(!!a.new_grad_program)||a.name.localeCompare(b.name);
  inds.forEach(ind=>{const os=list.filter(o=>!seen.has(o.id)&&(o.industries||[])[0]===ind.id||(!seen.has(o.id)&&(o.industries||[]).includes(ind.id)&&!(o.industries||[]).some(x=>indById[x]&&(LEVEL[indById[x].interest]??9)<(LEVEL[ind.interest]??9))));os.forEach(o=>seen.add(o.id));if(os.length)groups.push([ind,os.sort(sortFn)])});
  const other=list.filter(o=>!seen.has(o.id));if(other.length)groups.push([{name:'Other',interest:'unrated',id:''},other.sort(sortFn)]);
  const row=o=>{const p=peopleAt(o.id).length;return `<div class="tr row ${o.id===selOrg?'sel':''}" data-org="${esc(o.id)}" tabindex="0"><div class="n"><b>${esc(o.name)}</b><small>${esc(o.blurb||'')}</small></div><div>${esc(o.location||'')||'<span class="dash">—</span>'}</div><div class="muted">${esc(o.size||'')||'<span class="dash">—</span>'}</div><div>${o.new_grad_program?pill(shortRoute(o.new_grad_program),'done'):'<span class="dash">—</span>'}</div><div>${p?`<b style="font-weight:500">${p}</b>`:'<span class="dash">—</span>'}</div><div class="star">${o.status==='shortlisted'?STAR:STAR0}</div></div>`};
  const o=orgById[selOrg];
  return head('Organisations',`${D.orgs.length} places across ${new Set(D.orgs.flatMap(o=>o.industries||[])).size} industries. Shortlist the ones worth a conversation.`,copyBtn('export my organisations to a spreadsheet','Copy “export to a spreadsheet”'))+
  `<div class="filters"><label class="search"><svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="6" cy="6" r="4.2" stroke="#A8A9AC" stroke-width="1.3"/><path d="m9.2 9.2 3 3" stroke="#A8A9AC" stroke-width="1.3" stroke-linecap="round"/></svg><input id="oq" type="search" placeholder="Search name, city, anything" value="${esc(oq)}" aria-label="Search organisations"></label>
   <div class="seg">${[['all','All'],['short','Shortlisted'],['grad','New-grad route'],['people','Has people']].map(([k,l])=>`<button data-f="${k}" class="${ofilter===k?'on':''}">${l}<em>${C[k]}</em></button>`).join('')}</div>
   <select id="oind" aria-label="Industry"><option value="">All industries</option>${inds.filter(i=>orgsIn(i.id).length).map(i=>`<option value="${esc(i.id)}" ${oind===i.id?'selected':''}>${esc(i.name)}</option>`).join('')}</select>
   <select id="osort" aria-label="Sort" style="margin-left:auto"><option value="close" ${osort==='close'?'selected':''}>Sort: closest to you</option><option value="name" ${osort==='name'?'selected':''}>Sort: name</option><option value="new" ${osort==='new'?'selected':''}>Sort: newest</option></select></div>
  <div class="orgwrap"><div class="table"><div class="tr th"><div>Organisation</div><div>Where</div><div>Size</div><div>New-grad route</div><div>People</div><div></div></div>
   ${!list.length?`<div style="display:flex;flex-direction:column;align-items:center;gap:10px;padding:40px 24px;text-align:center"><b style="font-size:14px;font-weight:500">Nothing matches${oq?' “'+esc(oq)+'”':''}${ofilter!=='all'?' with this filter':''}</b><span class="muted" style="font-size:13px">Try clearing the filters, or ask your guide to look further.</span><button class="btn pri" id="clearf">Clear filters</button>${say(oq?'go explore '+oq:'go explore','Or, in your chat, say')}</div>`:''}${groups.map(([ind,os])=>`<div class="grp"><i style="background:${ind.interest==='drawn'?'var(--accent)':ind.interest==='curious'?'#9DC0F8':ind.interest==='meh'?'var(--await)':'var(--faint)'}"></i>${esc(ind.name)}${REACT[ind.interest]&&ind.id?pill(REACT[ind.interest][0],REACT[ind.interest][1]):''}${ind.origin==='wildcard'?pill('✦ Wildcard','ai'):''}<em>${os.length}</em></div>${os.map(row).join('')}`).join('')||''}</div>
   ${o&&list.length?`<aside class="card drawer">${orgDrawer(o)}</aside>`:`<aside class="dashbox" style="min-height:240px;align-items:center;justify-content:center;text-align:center"><span class="muted" style="font-size:13px">Pick an organisation to see why it might fit you, its new-grad route and who you could talk to.</span></aside>`}</div>`;
}
function shortRoute(t){t=String(t).replace(/https?:\/\/\S+/g,'').trim();let s=t.split(/[:(.;—–]| - /)[0].trim()||'Yes';if(s.length>18){s=s.slice(0,18);s=s.slice(0,s.lastIndexOf(' ')>8?s.lastIndexOf(' '):18)+'…'}return s}
function orgDrawer(o){
  const inds=(o.industries||[]).map(i=>indById[i]).filter(Boolean),ppl=peopleAt(o.id);
  const route=o.new_grad_program||'',url=(route.match(/https?:\/\/\S+/)||[])[0];
  return `<div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start"><div><h2>${esc(o.name)}</h2><div class="small muted">${esc([inds.map(i=>i.name).join(', '),o.location,o.size].filter(Boolean).join(' · '))}</div></div>${o.status==='shortlisted'?`<span class="pill await">${STAR.replace('width="16" height="16"','width="12" height="12"')}Shortlisted</span>`:`<span class="pill line">${STAR0.replace('width="16" height="16"','width="12" height="12"')}Not shortlisted</span>`}</div>
   ${o.why_her||o.blurb?`<div><span class="lbl">Why you</span><div style="font-size:13px;line-height:20px">${esc(o.why_her||o.blurb)}</div></div>`:''}
   ${route?`<div class="route"><b><span class="pill done" style="padding:0;background:none"><span class="d"></span></span>New-grad route</b><div>${esc(route.replace(url||'',''))}</div><div style="display:flex;gap:6px;flex-wrap:wrap">${url?`<a class="btn" href="${esc(url)}" target="_blank" rel="noopener">Programme page ↗</a>`:''}${o.careers_url?`<a class="btn" href="${esc(o.careers_url)}" target="_blank" rel="noopener">Careers page ↗</a>`:''}</div></div>`:`<div class="card" style="padding:12px;background:var(--panel);display:flex;flex-direction:column;gap:6px;box-shadow:0 0 0 1px var(--ring)"><b style="font-size:12px;font-weight:600">No new-grad programme found</b><span class="small muted" style="line-height:18px">Roles here are posted one at a time. A conversation with someone inside is usually the way in.</span>${o.careers_url?`<div><a class="btn" href="${esc(o.careers_url)}" target="_blank" rel="noopener">Careers page ↗</a></div>`:''}</div>`}
   <div style="display:flex;flex-direction:column;gap:8px"><span class="lbl">People here</span>${ppl.length?ppl.map(p=>`<div style="display:flex;align-items:center;gap:10px"><span class="av" style="background:var(--done-soft);color:var(--done-ink)">${esc(initials(p.name))}</span><div style="flex:1;min-width:0"><b style="display:block;font-size:13px;font-weight:500">${esc(p.name)}${p.title?' · '+esc(p.title):''}</b><small class="muted">${esc(p.early_career_evidence||p.why||'')}</small></div>${statusPill(p.status)}</div>`).join(''):`<span class="small muted">Nobody found yet.</span>${say('find people at '+o.name)}`}</div>
   <div style="padding-top:8px;border-top:1px solid var(--line);font-size:11px;color:var(--muted)">${o.url?link(o.url,'Website')+' · ':''}${(o.sources||[]).filter(s=>/^https?:/.test(s)).slice(0,3).map((s,i)=>link(s,'source '+(i+1))).join(' · ')||'No source link'}</div>`;
}
const SP={found:['Found','grey'],'to-draft':['To draft','grey'],drafted:['Ready to send','accent'],sent:['Sent','grey'],replied:['Replied','await'],chatted:['Talked','done'],thanked:['Thanked','done'],parked:['Parked','grey']};
function ago(d){const n=Math.round((Date.now()-new Date(d+'T12:00'))/864e5);return isNaN(n)?'Sent a while ago':n<=0?'Sent today':n===1?'Sent yesterday':`Sent ${n} days ago`}
const statusPill=s=>pill((SP[s]||[s])[0],(SP[s]||['','grey'])[1]);

/* ---------- People ---------- */
function peopleView(){
  if(!D.people.length)return head('People','Recent grads and early-career people at places you like. They remember the job hunt, and they reply.')+estate('people','Nobody to talk to yet',"Once you've shortlisted a few organisations, your guide finds recent grads and early-career people there from public pages, and tells you why each one is worth a message.",'find people at my shortlisted organisations');
  const P=D.people,cnt=s=>P.filter(p=>s.includes(p.status)).length;
  const pipe=[['Found',cnt(['found']),''],['To draft',cnt(['to-draft']),''],['Ready to send',cnt(['drafted']),'acc'],['Sent',cnt(['sent']),''],['Replied',cnt(['replied']),'aw'],['Talked',cnt(['chatted','thanked']),'dn']];
  const fu=new Set(D.followups);
  const waiting=P.filter(p=>p.status==='sent'&&!fu.has(p.id)),talked=P.filter(p=>p.status==='thanked'),nextUp=P.filter(p=>p.status==='to-draft'),found=P.filter(p=>p.status==='found');
  const needs=[...P.filter(p=>p.status==='replied').map(p=>['reply',p]),...P.filter(p=>p.status==='drafted').map(p=>['send',p]),...P.filter(p=>fu.has(p.id)).map(p=>['follow',p]),...P.filter(p=>p.status==='chatted').map(p=>['thanks',p])];
  const card=([k,p])=>{const o=orgById[p.org]||{};const cfg={reply:['Replied','await','var(--await)','Their reply',p.reply||'They replied. Paste their message into your chat and your guide will help you answer.',`help me answer ${first(p.name)}`,'Copy “help me answer”'],
    send:['Ready to send','accent','var(--accent)',`${p.contact_routes&&p.contact_routes.some(r=>r.kind==='email')?'Email':'LinkedIn note'}${p.draft?' · '+p.draft.length+' characters':''}`,p.draft||'Draft not saved yet. Ask your guide to draft it.',p.draft,'Copy message'],
    follow:[ago(p.last_contact),'block','var(--block)','Follow-up',p.followup_draft||`Hi ${first(p.name)}, just floating this back up in case it got buried. No worries at all if now's not a good time.`,p.followup_draft||`Hi ${first(p.name)}, just floating this back up in case it got buried. No worries at all if now's not a good time.`,'Copy follow-up'],
    thanks:['Talked','done','var(--done)','Next','Send a short thank-you within a day: thanks, one thing they said that helped, what you will do with it.',`help me thank ${first(p.name)}`,'Copy “help me thank”']}[k];
    return `<div class="card act" style="box-shadow:0 0 0 1px var(--ring),inset 3px 0 0 ${cfg[2]}"><div class="top"><span class="av lg" style="background:var(--s2);color:var(--muted)">${esc(initials(p.name))}</span><div class="t"><b>${esc(p.name)}</b><small>${esc([p.title,o.name].filter(Boolean).join(' · '))}</small></div>${pill(cfg[0],cfg[1])}</div>
     <div class="msg"><div class="lbl">${esc(cfg[3])}</div>${esc(cfg[4])}</div><div style="display:flex;gap:6px;flex-wrap:wrap">${cfg[5]?copyBtn(cfg[5],cfg[6],'pri'):''}${p.profile_url?`<a class="btn" href="${esc(p.profile_url)}" target="_blank" rel="noopener">Open profile ↗</a>`:''}</div></div>`};
  const prow=p=>{const o=orgById[p.org]||{};return `<div class="prow"><span class="av lg" style="background:var(--s2);color:var(--muted)">${esc(initials(p.name))}</span><div class="t"><b>${p.profile_url?link(p.profile_url,p.name):esc(p.name)}</b><small>${esc([p.title,o.name].filter(Boolean).join(' · '))}</small>${(p.status==='found'||p.status==='to-draft')&&(p.shared||p.why)?`<span class="why">${esc(p.shared||p.why)}</span>`:''}</div><div class="r">${statusPill(p.status)}<span>${esc(p.status==='found'||p.status==='to-draft'?'':(p.next_step||''))}</span></div></div>`};
  return head('People','Recent grads and early-career people at places you like. They remember the job hunt, and they reply.',copyBtn('find more people','Copy “find more people”'))+
  `<div class="pipe">${pipe.map(([l,n,c])=>`<div class="${n?c:''}"><b style="${n?'':'color:var(--faint)'}">${n}</b><small>${l}</small></div>`).join('')}</div>
  <div class="cols" style="grid-template-columns:minmax(0,1.25fr) minmax(0,1fr)"><section style="display:flex;flex-direction:column;gap:10px"><div style="display:flex;align-items:center;gap:8px"><h3 class="h2">Needs you</h3>${needs.length?`<span class="badge" style="font:600 11px/16px var(--sans);color:#fff;background:var(--accent);border-radius:999px;padding:0 6px">${needs.length}</span>`:''}</div>${needs.map(card).join('')||(found.length||nextUp.length?`<div class="next"><span class="k">Your next step · about 5 minutes</span><h2 style="font:400 20px/26px var(--serif);margin:0">Pick who you'd like to reach out to</h2><div class="muted" style="font-size:13px;line-height:20px">${found.length+nextUp.length} people are waiting on the right. Choose two or three; your guide drafts each message in your own words, and you send them.</div>${say('help me reach out to '+(nextUp.concat(found)).slice(0,2).map(p=>first(p.name)).join(' and '))}</div>`:'<div class="dashbox muted" style="font-size:13px">Nothing waiting on you. When someone replies or a message is ready, it shows up here.</div>')}</section>
  <section style="display:flex;flex-direction:column;gap:10px"><div style="display:flex;justify-content:space-between"><h3 class="h2">Everyone else</h3><span class="small muted">Grouped by where it stands</span></div>
   <div class="list">${waiting.length?'<div class="sec">Waiting on them</div>'+waiting.map(prow).join(''):''}${talked.length?'<div class="sec">Talked</div>'+talked.map(prow).join(''):''}${nextUp.length?'<div class="sec">Next to reach out to</div>'+nextUp.map(prow).join(''):''}${found.length?'<div class="sec">Found, not yet picked</div>'+found.slice(0,6).map(prow).join('')+(found.length>6?`<div class="prow"><span class="small muted">${found.length-6} more</span></div>`:''):''}
   ${!waiting.length&&!talked.length&&!nextUp.length&&!found.length?'<p class="empty" style="padding:12px">Nobody yet. In your chat, say “find people at” one of your shortlisted organisations.</p>':''}</div></section></div>`;
}

/* ---------- About you ---------- */
function youView(){
  if(!D.signals_n)return head('About you','What pulls you and what pushes you away will show up here as you react to roles and industries.')+estate('you','Nothing to show yet','Every time you react to a role or an industry, your guide notes what pulled you or put you off. Three reactions in the same direction make a pattern.','show me some roles');
  const tags=D.tags.slice(0,12),M=Math.max(3,...tags.map(t=>Math.abs(t.sum)));
  const bar=t=>{const w=(92*Math.abs(t.sum)/M).toFixed(1),col=t.sum>0?'var(--accent)':'var(--push)',op=t.pattern?1:.42,rad=t.sum>0?'0 3px 3px 0':'3px 0 0 3px';
    return `<div class="brow"><span style="font-weight:${t.pattern?500:400};color:${t.pattern?'var(--text)':'var(--muted)'}">${esc(t.tag)}</span><div class="track"><div class="l">${t.sum<0?`<i style="width:${w}%;background:${col};opacity:${op};border-radius:${rad}"></i>`:''}</div><div class="ax"></div><div>${t.sum>0?`<i style="width:${w}%;background:${col};opacity:${op};border-radius:${rad}"></i>`:''}</div></div><span class="cnt">${t.n} reaction${t.n===1?'':'s'}</span><span style="text-align:right">${t.pattern?pill('Pattern','dark'):pill('Hunch','line')}</span></div>`};
  const rg=(lvl,title,col)=>{const rs=D.roles.filter(r=>r.interest===lvl);return rs.length?`<div class="rg"><div class="h"><i style="background:${col}"></i>${title}<em>${rs.length}</em></div><div class="chips">${rs.map(r=>`<span class="chip" title="${esc(r.blurb||'')}">${esc(r.name)}</span>`).join('')}</div></div>`:''};
  return head('About you',`What pulls you and what pushes you away, from ${D.signals_n} reaction${D.signals_n===1?'':'s'}. Three in the same direction make a pattern.`,copyBtn('let me tell you a story','Copy “tell you a story”'))+
  `<div class="cols" style="grid-template-columns:minmax(0,1.45fr) minmax(0,1fr)"><section class="card bars"><h3 class="h2" style="padding-bottom:6px">What pulls you, what pushes you away</h3>
   ${tags.length?`<div class="brow" style="min-height:0"><span></span><div style="display:flex;justify-content:space-between"><span class="mono" style="font-size:10px;color:var(--block-ink)">← PUSHES AWAY</span><span class="mono" style="font-size:10px;color:var(--accent-ink)">PULLS YOU →</span></div><span></span><span></span></div>${tags.map(bar).join('')}
   ${tags.some(t=>t.pattern)?'<p class="small muted" style="margin:10px 0 0">Faded bars are hunches: fewer than three reactions in one direction so far. Your guide tests them in the next rounds.</p>':`<div class="card" style="margin-top:10px;padding:14px;background:var(--panel);box-shadow:none;display:flex;flex-direction:column;gap:8px"><b style="font-size:13px;font-weight:500">No patterns yet, and that's normal</b><span class="small muted" style="line-height:18px">These are hunches from your first ${D.signals_n} reaction${D.signals_n===1?'':'s'}. One or two more rounds of cards and the first patterns usually appear.</span>${say('show me some roles')}</div>`}`:'<p class="empty">No reactions yet. In your chat, say “show me some roles”.</p>'}</section>
  <div style="display:flex;flex-direction:column;gap:16px"><section class="card" style="padding:18px 20px;background:var(--panel);display:flex;flex-direction:column;gap:14px"><h3 class="h2">Roles you've seen</h3>${rg('drawn','Drawn to','var(--accent)')}${rg('curious','Curious','#9DC0F8')}${rg('unrated','Not yet rated','var(--faint)')}${rg('meh','Meh','var(--await)')}${rg('no','Not for me','var(--push)')}${D.roles.length?'':'<p class="empty">No roles yet.</p>'}</section>
  ${D.quotes.length?`<section class="card" style="padding:18px 20px;display:flex;flex-direction:column;gap:10px"><span class="lbl">In your words</span>${D.quotes.slice(0,3).map(q=>`<q style="font:italic 15px/22px var(--serif);quotes:'“' '”'">${esc(q.why)}</q>`).join('')}</section>`:''}</div></div>`;
}

function draw(){
  side();
  $('#view').innerHTML={today:todayView,map:mapView,orgs:orgsView,people:peopleView,you:youView}[view]();
  document.querySelectorAll('g.ind').forEach(g=>{const pick=()=>{selInd=g.dataset.id;draw()};g.onclick=pick;g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();pick()}}});
  const rp=$('#replay');if(rp)rp.onclick=replay;
  document.querySelectorAll('[data-goind]').forEach(b=>b.onclick=()=>{oind=b.dataset.goind;ofilter='all';go('orgs')});
  document.querySelectorAll('.row[data-org]').forEach(r=>{const pick=()=>{selOrg=r.dataset.org;draw()};r.onclick=pick;r.onkeydown=e=>{if(e.key==='Enter'){pick()}}});
  document.querySelectorAll('.seg button[data-f]').forEach(b=>b.onclick=()=>{ofilter=b.dataset.f;draw()});
  const q=$('#oq');if(q){q.oninput=e=>{oq=e.target.value;draw();const n=$('#oq');n.focus();n.setSelectionRange(oq.length,oq.length)}}
  const si=$('#oind');if(si)si.onchange=e=>{oind=e.target.value;draw()};
  const cf=$('#clearf');if(cf)cf.onclick=()=>{oq='';ofilter='all';oind='';draw()};
  const so=$('#osort');if(so)so.onchange=e=>{osort=e.target.value;draw()};
  document.querySelectorAll('[data-copy]').forEach(b=>b.onclick=()=>{const t=b.dataset.copy,orig=b.textContent;
    const done=()=>{b.textContent='Copied ✓';setTimeout(()=>b.textContent=orig,1600)};
    try{navigator.clipboard.writeText(t).then(done,()=>{window.prompt?void 0:0;b.textContent='Select and copy: '+t})}catch(e){b.textContent='Select and copy: '+t}});
}
draw();
</script></body></html>
"""


# ---------------------------------------------------------------- self-test

def cmd_selftest(a):
    tmp = tempfile.mkdtemp()
    py = sys.executable
    me = os.path.abspath(__file__)

    def run(*args):
        import subprocess
        r = subprocess.run([py, me] + list(args), capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout, r.stderr)
            die(f"self-test step failed: {' '.join(args[:2])}")
        return r.stdout
    out = run("init", "--folder", tmp, "--name", "Test")
    ws = re.search(r"WS=(.*)", out).group(1).strip()
    run("add", "industry", "--ws", ws, "--json", '[{"name":"Battery materials","origin":"profile"},{"name":"Food science","origin":"wildcard"}]')
    run("add", "org", "--ws", ws, "--json", '{"name":"Example Co","url":"https://example.com","industries":["Battery materials"],"sources":["https://example.com/about"]}')
    run("add", "person", "--ws", ws, "--json", '{"name":"Sample Person","org":"Example Co","title":"Associate Scientist","sources":["https://example.com/team"]}')
    run("update", "industry", "Battery materials", "--ws", ws, "--set", "interest=drawn")
    for _ in range(3):
        run("signal", "--ws", ws, "--about", "Battery materials", "--lift", "2", "--tags", "hands-on lab")
    run("update", "person", "Sample Person", "--ws", ws, "--set", "status=sent", "--set", "last_contact=2000-01-01")
    run("add", "goal", "--ws", ws, "--json", '{"text":"Send 5 messages","measure":"messages_sent","target":5,"due":"2099-01-01","why":"test"}')
    run("session", "--ws", ws, "--guide-name", "Test Guide")
    st = run("status", "--ws", ws)
    assert "hands-on lab" in st and "Follow up" in st and "TEST GUIDE" in st and "1/5" in st, st
    run("check", "--ws", ws)
    run("render", "--ws", ws)
    assert os.path.exists(os.path.join(ws, "Career Map.html"))
    shutil.rmtree(tmp)
    print("✓ self-test passed")


# ---------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(prog="wayfinder.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def ws(p):
        p.add_argument("--ws", required=True, help="the Career Wayfinder folder (printed by init as WS=...)")

    p = sub.add_parser("init", help="create the Career Wayfinder folder (safe to re-run)")
    p.add_argument("--folder", required=True)
    p.add_argument("--name", default="")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("add", help="add or merge items: kind = industry|role|org|person|question|agenda")
    p.add_argument("kind")
    ws(p)
    p.add_argument("--json", required=True, help="an object or list, or @file.json")
    p.set_defaults(fn=cmd_add)

    p = sub.add_parser("update", help="change fields on one item (by id or name)")
    p.add_argument("kind")
    p.add_argument("id")
    ws(p)
    p.add_argument("--set", action="append", help="key=value (repeatable)")
    p.add_argument("--json", help="object of fields, e.g. a question resolution")
    p.add_argument("--replace", action="store_true", help="replace list fields instead of merging")
    p.set_defaults(fn=cmd_update)

    p = sub.add_parser("signal", help="log one reaction to the signals register")
    ws(p)
    p.add_argument("--about", required=True, help="an industry/role/org/person name or id, or free text")
    p.add_argument("--lift", required=True, help="-2..2: how strongly it pulled (+) or pushed (-)")
    p.add_argument("--tags", default="", help="comma-separated qualities, e.g. 'hands-on lab, client-facing'")
    p.add_argument("--why", default="", help="her words")
    p.add_argument("--source", default="", help="role card, industry card, posting, conversation, ...")
    p.add_argument("--date", default="")
    p.set_defaults(fn=cmd_signal)

    p = sub.add_parser("import", help="merge a finds file written by a scout or people-finder")
    ws(p)
    p.add_argument("file")
    p.set_defaults(fn=cmd_import)

    p = sub.add_parser("find", help="search everything on the map")
    ws(p)
    p.add_argument("text")
    p.set_defaults(fn=cmd_find)

    p = sub.add_parser("show", help="list items of one kind (or signals)")
    p.add_argument("kind")
    ws(p)
    p.add_argument("--filter", action="append", help="key=value")
    p.add_argument("--full", action="store_true")
    p.set_defaults(fn=cmd_show)

    p = sub.add_parser("status", help="the guide's dashboard: breadth, patterns, suggested moves")
    ws(p)
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("session", help="close a session: date it, log a line, re-render")
    ws(p)
    p.add_argument("--note", default="")
    p.add_argument("--destination", default="")
    p.add_argument("--pace", default="")
    p.add_argument("--guide-name", default="", help="what she calls the guide")
    p.add_argument("--her-name", default="", help="what she likes to be called")
    p.add_argument("--goals-checked", action="store_true", help="record a goal check-in today")
    p.add_argument("--onboard", action="append", help="mark an onboarding step done (exa, gmail, map, plan, schedule, ...)")
    p.add_argument("--onboard-skip", action="append", help="mark an onboarding step skipped")
    p.set_defaults(fn=cmd_session)

    p = sub.add_parser("check", help="consistency check (sources, links, resolutions)")
    ws(p)
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("render", help="rewrite Career Map.html and My Map.md")
    ws(p)
    p.set_defaults(fn=cmd_render)

    p = sub.add_parser("export", help="write people.csv for a spreadsheet")
    ws(p)
    p.set_defaults(fn=cmd_export)

    p = sub.add_parser("selftest", help="run an end-to-end test in a temporary folder")
    p.set_defaults(fn=cmd_selftest)

    a = ap.parse_args()
    if getattr(a, "ws", None):
        a.ws = os.path.abspath(os.path.expanduser(a.ws))
    a.fn(a)


if __name__ == "__main__":
    main()

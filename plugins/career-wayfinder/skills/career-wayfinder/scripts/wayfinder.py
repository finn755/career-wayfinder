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
<style>
:root{--bg:#f6f4ef;--card:#fff;--ink:#1f2a2e;--muted:#66727a;--line:#e3dfd6;--soft:#efece5;--accent:#1e6b5c;--on-accent:#fff;
--drawn:#1e6b5c;--curious:#3f7fbf;--unrated:#b9b4a9;--meh:#c9a25a;--no:#c76b5f;--new:#e0a526;--shadow:0 2px 10px rgba(0,0,0,.06)}
@media (prefers-color-scheme:dark){:root{--bg:#14191b;--card:#1d2427;--ink:#e8ecea;--muted:#9aa6a3;--line:#2c3538;--soft:#242c2f;
--accent:#5cc1a6;--on-accent:#0f1a17;--drawn:#5cc1a6;--curious:#7fb0e6;--unrated:#5d6567;--meh:#d9b673;--no:#e08b7f;--new:#f2c14e;--shadow:none}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:1180px;margin:auto;padding:0 16px}
header{padding:20px 0 6px}h1{font-size:24px;margin:0}header p{margin:2px 0 0;color:var(--muted)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:8px;margin:14px 0 6px}@media(max-width:520px){.stats{grid-template-columns:repeat(3,1fr)}.stat b{font-size:20px}.stat em{display:block}}
.stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:8px 12px}
.stat b{display:block;font-size:24px;line-height:1.2}.stat span{font-size:12px;color:var(--muted)}.stat em{font-style:normal;font-size:12px;color:var(--accent);font-weight:600}
nav{display:flex;gap:6px;overflow-x:auto;padding:10px 0;position:sticky;top:0;background:var(--bg);z-index:2}
nav button{flex:none;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:6px 14px;font:inherit;cursor:pointer}
nav button.on{background:var(--accent);color:var(--on-accent);border-color:var(--accent)}
main{padding:4px 0 48px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;box-shadow:var(--shadow);margin-bottom:12px}
.two{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px}@media(max-width:820px){.two{grid-template-columns:1fr}}
h2{font-size:17px;margin:2px 0 8px}h3{font-size:14px;margin:12px 0 6px}.muted{color:var(--muted)}.small{font-size:13px}
a{color:var(--accent)}
.chip{display:inline-block;border-radius:999px;padding:1px 9px;font-size:12px;border:1px solid var(--line);margin:2px 4px 2px 0;background:var(--card)}
.chip.good{border-color:var(--accent);color:var(--accent);font-weight:600}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:middle}
.bar{height:8px;background:var(--soft);border-radius:4px;overflow:hidden}.bar i{display:block;height:100%;background:var(--accent)}
.row{display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-top:1px solid var(--line)}.row:first-of-type{border-top:0}
.tick{flex:none;width:22px;height:22px;border-radius:50%;border:2px solid var(--line);display:grid;place-items:center;font-size:13px}
.tick.done{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}.tick.next{border-color:var(--accent)}
.next-step{background:var(--soft);border-radius:10px;padding:10px 12px;margin:8px 0}
code{background:var(--soft);border-radius:6px;padding:1px 6px;font-size:13px;white-space:nowrap}
.pc{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:9px 11px;margin-bottom:8px;font-size:13px}
.pc b{font-size:14px}.flag{color:var(--no);font-weight:600}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px}.col h3{text-transform:uppercase;letter-spacing:.04em;font-size:12px;color:var(--muted);margin:0 0 6px}
.grid3{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}
input[type=search]{min-width:240px;flex:1 1 240px}input[type=search],select{font:inherit;padding:7px 10px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--ink)}
.filters{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:10px}
.filters button{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:4px 11px;font:inherit;font-size:13px;cursor:pointer}
.filters button.on{border-color:var(--accent);color:var(--accent);font-weight:600}
button.copy{border:1px solid var(--accent);background:transparent;color:var(--accent);border-radius:8px;padding:2px 9px;font:inherit;font-size:12px;cursor:pointer;margin-top:4px}
blockquote{margin:6px 0;padding:6px 10px;border-left:3px solid var(--line);color:var(--ink);font-size:13px;white-space:pre-wrap}
svg{width:100%;height:auto;display:block}g.ind{cursor:pointer}
.nd{transition:opacity .45s ease,transform .45s ease}.hide{opacity:0}
@keyframes pulse{0%{stroke-opacity:.9;stroke-width:3}100%{stroke-opacity:0;stroke-width:14}}.glow{animation:pulse 1.8s ease-out infinite}
.maptools{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between;margin-bottom:6px}
.maptools button{border:1px solid var(--accent);background:var(--accent);color:var(--on-accent);border-radius:999px;padding:6px 14px;font:inherit;cursor:pointer}
.legend span{margin-right:12px;font-size:13px;white-space:nowrap}
.empty{color:var(--muted);padding:6px 0}
</style></head><body>
<div class="wrap"><header><h1 id="t"></h1><p id="sub"></p><div class="stats" id="stats"></div></header>
<nav id="tabs"></nav><main id="main"></main></div>
<script>
const D=__DATA__;
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const COL={drawn:'var(--drawn)',curious:'var(--curious)',unrated:'var(--unrated)',meh:'var(--meh)',no:'var(--no)'};
const ORDER=['drawn','curious','unrated','meh','no'];
const orgById=Object.fromEntries(D.orgs.map(o=>[o.id,o])),indById=Object.fromEntries(D.industries.map(o=>[o.id,o]));
const WEEK=new Date(Date.now()-3*864e5).toISOString().slice(0,10);
const isNew=x=>String(x.created||'')>=WEEK;
const link=(u,t)=>u?`<a href="${esc(u)}" target="_blank" rel="noopener">${esc(t||'link')}</a>`:esc(t||'');
const peopleAt=oid=>D.people.filter(p=>p.org==oid);
const src=x=>(x.sources||[]).filter(s=>/^https?:/.test(s)).slice(0,2).map((s,i)=>link(s,i?'source '+(i+1):'source')).join(' · ');
let tab='home',sel=null,ofilter='all',oq='',oind='';
document.title=document.title;$('#t').textContent=document.title;
$('#sub').textContent=(D.meta.destination?'“'+D.meta.destination+'” · ':'')+'Kept by '+D.guide+' · updated '+D.generated;
const G=D.growth,S=[['industries',D.industries.length,G.industries],['roles',D.roles.length,G.roles],['organisations',D.orgs.length,G.orgs],['people',D.people.length,G.people],['reactions',D.signals_n,G.reactions]];
$('#stats').innerHTML=S.map(([k,v,g])=>`<div class="stat"><b>${v}</b><span>${k}</span> ${g?`<em>+${g} this week</em>`:''}</div>`).join('');
const TABS={home:'Home',map:'Map',orgs:'Organisations',people:'People',you:'About you'};
function nav(){$('#tabs').innerHTML=Object.entries(TABS).map(([k,v])=>`<button class="${k==tab?'on':''}" data-t="${k}">${v}</button>`).join('');
 document.querySelectorAll('#tabs button').forEach(b=>b.onclick=()=>{tab=b.dataset.t;draw()})}

/* ---------- Home ---------- */
const PACE={'on track':'var(--drawn)','reached':'var(--drawn)','behind':'var(--meh)','past due':'var(--no)','no date':'var(--muted)'};
const KIND={scout:'exploring',wildcard:'wildcard',people:'finding people',outreach:'messages','follow-up':'follow-up',question:'question','ask-her':'for you',setup:'setup',goal:'goals'};
function goalCard(g){return `<div class="pc"><b>${esc(g.text)}</b><div class="bar" style="margin:7px 0"><i style="width:${g.pct}%"></i></div><span class="small">${g.have} of ${g.target} · by ${esc(g.due)} · <b style="font-size:13px;color:${PACE[g.pace]||'var(--muted)'}">${esc(g.pace)}</b></span>${g.why?`<div class="small muted">Why: ${esc(g.why)}</div>`:''}${g.next_step?`<div class="small">Next step: ${esc(g.next_step)}</div>`:''}</div>`}
function onboardingCard(){const st=D.onboarding,req=st.filter(s=>!s.optional),done=req.filter(s=>s.state!='todo').length;
 if(done>=req.length)return '';const nx=st.find(s=>s.state=='todo');
 return `<div class="card"><h2>Getting started · ${done} of ${req.length}</h2><div class="bar"><i style="width:${100*done/req.length}%"></i></div>
 ${nx?`<div class="next-step"><b>Next:</b> ${esc(nx.label)}<br><span class="small">In your chat with ${esc(D.guide)}, type <code>${esc(nx.command)}</code> or just say what you want to do.</span></div>`:''}
 ${st.filter(s=>s.state=='todo').map(s=>`<div class="row"><span class="tick ${s===nx?'next':''}"></span><div>${esc(s.label)}${s.optional?' <span class="muted small">(optional)</span>':''} <code>${esc(s.command)}</code></div></div>`).join('')}
 ${done?`<details><summary class="small muted" style="cursor:pointer;margin-top:6px">${done} done ✓ show them</summary>${st.filter(s=>s.state!='todo').map(s=>`<div class="row"><span class="tick ${s.state=='done'?'done':''}">${s.state=='done'?'✓':'–'}</span><div class="muted">${esc(s.label)} <code>${esc(s.command)}</code></div></div>`).join('')}</details>`:''}</div>`}
function copyBtn(p){return p&&p.draft?`<button class="copy" data-copy="${esc(p.id)}">Copy message</button>`:''}
function todoCard(){const t=D.todos;const pid=id=>D.people.find(p=>p.id==id);
 return `<div class="card"><h2>Your to-dos</h2>${t.length?t.map(x=>{const p=x.person&&pid(x.person);return `<div class="row"><span class="tick"></span><div style="flex:1">${esc(x.text)}${p&&p.profile_url&&x.kind=='send'?` · ${link(p.profile_url,'open profile')}`:''}${p&&p.draft&&x.kind=='send'?`<blockquote>${esc(p.draft)}</blockquote>${copyBtn(p)}`:''}</div></div>`}).join(''):'<p class="empty">Nothing waiting on you. Nice. Ask your guide “what should I do today?” for something new.</p>'}</div>`}
function homeView(){const a=D.goals.filter(g=>g.status=='active');
 const q=D.questions.filter(q=>q.status=='open'&&(q.type=='chat'||q.type=='look-up'));
 return onboardingCard()+`<div class="two"><div>${todoCard()}</div><div><div class="card"><h2>Your goals</h2>${a.map(goalCard).join('')||'<p class="empty">No goals yet. Type <code>/my-goals</code> when you’re ready to set a few.</p>'}</div>
 <div class="card"><h2>What ${esc(D.guide)} is working on</h2>${D.agenda.map(x=>`<div class="row"><span class="chip">${esc(KIND[x.kind]||x.kind)}</span><div>${esc(x.text)}${x.why?`<div class="small muted">${esc(x.why)}</div>`:''}</div></div>`).join('')||'<p class="empty">Nothing queued.</p>'}
 ${q.length?'<h3>Questions you’re carrying</h3>'+q.map(x=>`<div class="small">• ${esc(x.text)}</div>`).join(''):''}</div></div></div>`}

/* ---------- Map ---------- */
function wrapLabel(s,n){const w=s.split(' '),L=[];let c='';for(const x of w){if((c+' '+x).trim().length>n&&c){L.push(c);c=x}else c=(c+' '+x).trim()}L.push(c);return L.length>3?L.slice(0,2).concat([L.slice(2).join(' ').slice(0,n-1)+'…']):L}
function mapView(){
 const inds=D.industries.filter(i=>i.interest!=='no'||D.orgs.some(o=>(o.industries||[]).includes(i.id)));
 const W=1000,H=900,cx=W/2,cy=H/2,R=Math.min(300,120+inds.length*10);
 let seq=0;const nodes=[];
 let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Map of industries and organisations"><circle cx="${cx}" cy="${cy}" r="${R}" fill="none" stroke="var(--line)" stroke-dasharray="4 7"/>`;
 inds.forEach((ind,k)=>{const a=-Math.PI/2+2*Math.PI*k/Math.max(1,inds.length),x=cx+R*Math.cos(a),y=cy+R*Math.sin(a);
  const orgs=D.orgs.filter(o=>(o.industries||[]).includes(ind.id));const r=15+Math.min(26,orgs.length*3.5);
  const col=COL[ind.interest]||COL.unrated,on=sel==ind.id,strong=ind.interest=='drawn';
  nodes.push({seq:seq++,created:ind.created||''});
  s+=`<g class="nd ind" data-seq="${seq-1}" data-id="${esc(ind.id)}"><line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="${col}" stroke-opacity="${strong?.6:ind.interest=='curious'?.35:.15}" stroke-width="${strong?3.5:1.5}"/>`;
  if(isNew(ind))s+=`<circle class="glow" cx="${x}" cy="${y}" r="${r+3}" fill="none" stroke="var(--new)"/>`;
  s+=`<circle cx="${x}" cy="${y}" r="${r}" fill="${col}" fill-opacity="${on?1:.88}" stroke="${on?'var(--ink)':'var(--card)'}" stroke-width="${on?3:2}"><title>${esc(ind.name)} · ${esc(ind.interest)} · ${orgs.length} organisations</title></circle>`;
  if(orgs.length)s+=`<text x="${x}" y="${y+5}" text-anchor="middle" font-size="14" font-weight="700" fill="#fff">${orgs.length}</text>`;
  else if(ind.origin==='wildcard')s+=`<text x="${x}" y="${y+5}" text-anchor="middle" font-size="15" fill="#fff">✦</text>`;
  const lr=R+r+48,lx=cx+lr*Math.cos(a),ly=cy+lr*Math.sin(a),anc=Math.cos(a)>.25?'start':Math.cos(a)<-.25?'end':'middle';
  const L=wrapLabel(ind.name,20),y0=ly-(L.length-1)*8+4;
  s+=`<text x="${lx}" y="${y0}" text-anchor="${anc}" font-size="15" font-weight="${strong?700:400}" fill="var(--ink)">${L.map((t,i)=>`<tspan x="${lx}" dy="${i?17:0}">${esc(t)}</tspan>`).join('')}${ind.origin==='wildcard'&&orgs.length?' ✦':''}</text></g>`;
  orgs.slice(0,16).forEach((o,j)=>{const m=Math.min(orgs.length,16),b=a+(j-(m-1)/2)*.075,ox=cx+(R+r+20)*Math.cos(b),oy=cy+(R+r+20)*Math.sin(b),n=peopleAt(o.id).length;
   nodes.push({seq:seq++,created:o.created||''});
   s+=`<g class="nd" data-seq="${seq-1}"><circle cx="${ox}" cy="${oy}" r="${n?6:4}" fill="${o.status=='shortlisted'?col:'var(--muted)'}" stroke="${n?'var(--ink)':'none'}" stroke-width="1.5"><title>${esc(o.name)}${n?' · '+n+' people':''}</title></circle></g>`})});
 const me=esc(D.meta.name||'You');
 s+=`<circle cx="${cx}" cy="${cy}" r="56" fill="var(--accent)"/><text x="${cx}" y="${cy+6}" text-anchor="middle" fill="var(--on-accent)" font-size="${me.length>9?15:19}" font-weight="700">${me}</text></svg>`;
 const legend=`<div class="legend">${ORDER.map(k=>`<span><i class="dot" style="background:${COL[k]}"></i>${k}</span>`).join('')}<span>number = organisations found</span><span>✦ your guide’s wildcard</span><span><i class="dot" style="background:var(--new)"></i>new in the last few days</span></div>`;
 const panel=sel?indPanel(indById[sel]):`<div class="card"><p class="muted" style="margin:0">Each circle is an industry, coloured by how you reacted. The small dots around it are organisations your guide found (filled = shortlisted, outlined = you have people there). Click an industry to see inside it.</p></div>`;
 return `<div class="card"><div class="maptools"><h2 style="margin:0">Your map</h2><button id="replay">▶ Replay how your map grew</button></div><div id="replaylabel" class="small muted" style="min-height:20px"></div>${s}${legend}</div><div id="panel">${panel}</div>`}
function indPanel(ind){if(!ind)return '';const orgs=D.orgs.filter(o=>(o.industries||[]).includes(ind.id));
 const roles=D.roles.filter(r=>(r.industries||[]).includes(ind.id));
 return `<div class="card"><h2>${esc(ind.name)}</h2><span class="chip" style="border-color:${COL[ind.interest]}">${esc(ind.interest)}</span>${ind.origin=='wildcard'?'<span class="chip">✦ your guide’s wildcard</span>':''}${isNew(ind)?'<span class="chip">new this week</span>':''}
 ${ind.blurb?`<p>${esc(ind.blurb)}</p>`:''}${ind.why_her?`<p class="small"><b>Why it might fit you:</b> ${esc(ind.why_her)}</p>`:''}
 ${roles.length?`<p class="small"><b>Roles here:</b> ${roles.map(r=>esc(r.name)).join(', ')}</p>`:''}
 <h3>${orgs.length} organisation${orgs.length==1?'':'s'}</h3><div class="grid3">${orgs.map(orgCard).join('')}</div>${orgs.length?'':`<p class="empty">Nothing found here yet. Ask your guide to “go explore ${esc(ind.name)}”.</p>`}</div>`}
function replay(){const els=[...document.querySelectorAll('.nd')];if(!els.length)return;const order=els.map(e=>+e.dataset.seq);
 els.forEach(e=>e.classList.add('hide'));const lab=$('#replaylabel');let i=0;const step=Math.max(40,Math.min(260,4000/els.length));
 (function tick(){if(i>=els.length){lab.textContent='That’s your whole map, so far.';return}els[i].classList.remove('hide');lab.textContent='Growing… '+(i+1)+' of '+els.length;i++;setTimeout(tick,step)})()}

/* ---------- Organisations ---------- */
function orgCard(o){const ppl=peopleAt(o.id);const inds=(o.industries||[]).map(i=>indById[i]).filter(Boolean);
 return `<div class="pc"><b>${link(o.url,o.name)}</b>${o.status=='shortlisted'?' <span class="chip good">shortlisted</span>':''}${isNew(o)?' <span class="chip">new</span>':''}
 <div class="small muted">${esc([o.location,o.size].filter(Boolean).join(' · '))}</div>${o.blurb?`<div>${esc(o.blurb)}</div>`:''}${o.why_her?`<div class="small"><b>Why you:</b> ${esc(o.why_her)}</div>`:''}
 ${o.new_grad_program?`<div class="small"><span class="chip good">new-grad route</span>${/^https?:/.test(o.new_grad_program)?link(o.new_grad_program,'programme page'):esc(o.new_grad_program)}</div>`:''}
 <div class="small">${inds.map(i=>`<span class="chip">${esc(i.name)}</span>`).join('')}</div>
 ${ppl.length?`<div class="small">People: ${ppl.map(p=>esc(p.name)+' ('+esc(p.status)+')').join(', ')}</div>`:''}
 <div class="small muted">${[o.careers_url?link(o.careers_url,'careers page'):'',src(o)].filter(Boolean).join(' · ')}</div></div>`}
function orgsView(){const F={all:'All',shortlisted:'Shortlisted',liked:'Drawn or curious',grad:'Has a new-grad route',people:'Has people',fresh:'New this week'};
 const q=oq.toLowerCase();let list=D.orgs.filter(o=>{if(ofilter=='shortlisted'&&o.status!='shortlisted')return false;
  if(ofilter=='liked'&&!['drawn','curious'].includes(o.interest)&&!(o.industries||[]).some(i=>indById[i]&&['drawn','curious'].includes(indById[i].interest)))return false;
  if(ofilter=='grad'&&!o.new_grad_program)return false;if(ofilter=='people'&&!peopleAt(o.id).length)return false;if(ofilter=='fresh'&&!isNew(o))return false;
  if(oind&&!(o.industries||[]).includes(oind))return false;
  if(q&&!JSON.stringify(o).toLowerCase().includes(q))return false;return true});
 list.sort((a,b)=>(b.status=='shortlisted')-(a.status=='shortlisted')||ORDER.indexOf(a.interest)-ORDER.indexOf(b.interest)||a.name.localeCompare(b.name));
 return `<div class="card"><h2>Organisations · ${list.length} of ${D.orgs.length}</h2><div class="filters"><input type="search" id="oq" placeholder="Search name, place, anything" value="${esc(oq)}">
 <select id="oind"><option value="">All industries</option>${D.industries.filter(i=>D.orgs.some(o=>(o.industries||[]).includes(i.id))).map(i=>`<option value="${esc(i.id)}" ${oind==i.id?'selected':''}>${esc(i.name)}</option>`).join('')}</select>
 ${Object.entries(F).map(([k,v])=>`<button data-f="${k}" class="${ofilter==k?'on':''}">${v}</button>`).join('')}</div>
 <div class="grid3">${list.map(orgCard).join('')}</div>${list.length?'':'<p class="empty">Nothing matches. Try another filter, or ask your guide to go exploring.</p>'}</div>`}

/* ---------- People ---------- */
function peopleView(){const cols=[['found','Found'],['to-draft','To draft'],['drafted','Ready to send'],['sent','Sent'],['replied','Replied'],['chatted','Talked'],['thanked','Thanked'],['parked','Parked']];
 return `<div class="card"><h2>People</h2><p class="muted small">Where every conversation stands. <span class="flag">Follow up</span> means it’s been a week since you sent.</p><div class="cols">${cols.map(([c,label])=>{const ps=D.people.filter(p=>p.status==c);return `<div class="col"><h3>${label} · ${ps.length}</h3>${ps.map(p=>`<div class="pc"><b>${link(p.profile_url,p.name)}</b><div>${esc(p.title||'')}</div><div class="muted">${esc((orgById[p.org]||{}).name||p.org)}</div>${p.early_career_evidence?`<div class="small">${esc(p.early_career_evidence)}</div>`:''}${p.shared?`<div class="small"><span class="chip good">${esc(p.shared)}</span></div>`:''}${p.why?`<div class="small muted">${esc(p.why)}</div>`:''}${D.followups.includes(p.id)?'<div class="flag small">Follow up</div>':''}${p.next_step?`<div class="small">Next: ${esc(p.next_step)}</div>`:''}${c=='drafted'?copyBtn(p):''}<div class="small muted">${src(p)}</div></div>`).join('')}</div>`}).join('')}</div></div>`}

/* ---------- About you ---------- */
function youView(){const li=a=>a.length?a.map(d=>`<div class="row"><b>${esc(d.tag)}</b><span class="muted small">${d.n} reaction${d.n==1?'':'s'}</span></div>`).join(''):'<p class="empty">Not enough reactions yet. Three in the same direction make a pattern.</p>';
 const rl=D.roles.slice().sort((a,b)=>ORDER.indexOf(a.interest)-ORDER.indexOf(b.interest));
 return `<div class="two"><div class="card"><h2>What pulls you</h2>${li(D.pulls)}<h2 style="margin-top:14px">What pushes you away</h2>${li(D.pushes)}<h3>Hunches (fewer than three reactions)</h3><p>${D.hunches.map(d=>`<span class="chip">${esc(d.tag)} ${d.sum>0?'+':''}${d.sum}</span>`).join('')||'<span class="muted">none yet</span>'}</p></div>
 <div class="card"><h2>Roles you’ve seen · ${D.roles.length}</h2>${rl.map(r=>`<div class="row"><span class="dot" style="background:${COL[r.interest]};margin-top:6px"></span><div><b>${esc(r.name)}</b> <span class="muted small">${esc(r.interest)}</span>${r.blurb?`<div class="small">${esc(r.blurb)}</div>`:''}</div></div>`).join('')||'<p class="empty">No roles yet. Type <code>/explore-roles</code>.</p>'}</div></div>`}

function draw(){nav();$('#main').innerHTML={home:homeView,map:mapView,orgs:orgsView,people:peopleView,you:youView}[tab]();
 document.querySelectorAll('g.ind').forEach(g=>g.onclick=()=>{sel=sel==g.dataset.id?null:g.dataset.id;draw();const p=$('#panel');if(sel&&p)p.scrollIntoView({behavior:'smooth',block:'nearest'})});
 const r=$('#replay');if(r)r.onclick=replay;
 const q=$('#oq');if(q){q.oninput=e=>{oq=e.target.value;draw();const n=$('#oq');n.focus();n.setSelectionRange(oq.length,oq.length)}}
 const si=$('#oind');if(si)si.onchange=e=>{oind=e.target.value;draw()};
 document.querySelectorAll('.filters button').forEach(b=>b.onclick=()=>{ofilter=b.dataset.f;draw()});
 document.querySelectorAll('button.copy').forEach(b=>b.onclick=()=>{const p=D.people.find(x=>x.id==b.dataset.copy);
  try{navigator.clipboard.writeText(p.draft).then(()=>{b.textContent='Copied ✓'},()=>{b.textContent='Select and copy the text above'})}catch(e){b.textContent='Select and copy the text above'}})}
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

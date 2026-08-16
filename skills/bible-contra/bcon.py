#!/usr/bin/env python3
"""bcon - internal Bible contradiction hunter. Stdlib only.

Two sources of truth:
  ylt.json  local full Young's Literal Translation. Every quote is verified against it.
  the API   https://ver.apexlinks.org/api/search  semantic verse search, for discovery.

Run `bcon help` for commands.
"""
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

DIR = os.path.expanduser(os.environ.get("BCON_DIR", "~/i/me/bcon"))
API = "https://ver.apexlinks.org/api/search"
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
YLT_SEED = os.path.expanduser("~/i/ver/ylt.json")

P = lambda *a: os.path.join(DIR, *a)
ME = os.path.basename(sys.argv[0]) or "bcon"
CATS = ("num", "who", "when", "where", "order", "law", "claim")
MODES = ("parallel", "number", "theme", "sweep", "lead", "deepen", "attack", "tidy")
LATE_MODES = ("deepen", "attack", "parallel", "tidy", "lead", "theme")

# ---------------------------------------------------------------- yield order

SWEEP_ORDER = [
    "Genesis", "2 Samuel", "1 Chronicles", "1 Kings", "2 Kings", "2 Chronicles",
    "Matthew", "Mark", "Luke", "John", "Acts", "Exodus", "Numbers", "Deuteronomy",
    "Ezra", "Nehemiah", "1 Samuel", "Joshua", "Judges", "Galatians", "Romans",
    "James", "Leviticus", "Isaiah", "Jeremiah", "Daniel", "Psalms", "Proverbs",
    "Ecclesiastes", "Job", "Ezekiel", "Hosea", "Jonah", "Ruth", "Esther",
    "Lamentations", "Joel", "Amos", "Obadiah", "Micah", "Nahum", "Habakkuk",
    "Zephaniah", "Haggai", "Zechariah", "Malachi", "Song of Songs",
    "1 Corinthians", "2 Corinthians", "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus",
    "Philemon", "Hebrews", "1 Peter", "2 Peter", "1 John", "2 John", "3 John",
    "Jude", "Revelation",
]

# concrete diff jobs: the same event told twice. highest yield in the book.
PARALLELS = [
    ("Genesis 1", "Genesis 2", "creation: order of man, plants, animals"),
    ("Genesis 6-7", "Genesis 7-8", "flood: pairs of animals, length of the flood"),
    ("2 Samuel 24", "1 Chronicles 21", "David's census: who moved him, the count, the price"),
    ("1 Samuel 31", "2 Samuel 1", "how Saul died"),
    ("2 Samuel 5-8", "1 Chronicles 11-18", "David's wars, officers, spoils"),
    ("2 Samuel 23", "1 Chronicles 11", "David's mighty men, their names and kill counts"),
    ("1 Kings 5-8", "2 Chronicles 2-7", "temple build: measures, workers, vessels"),
    ("1 Kings 15-16", "2 Chronicles 13-16", "kings of Judah: reign lengths and ages"),
    ("2 Kings 8-16", "2 Chronicles 21-28", "kings of Judah: ages at accession"),
    ("2 Kings 18-20", "Isaiah 36-39", "Hezekiah and Sennacherib"),
    ("2 Kings 24-25", "2 Chronicles 36", "fall of Jerusalem, Jehoiachin's age"),
    ("2 Kings 25", "Jeremiah 52", "the exile: numbers carried away"),
    ("Ezra 2", "Nehemiah 7", "the returnees: family by family tallies"),
    ("Exodus 20", "Deuteronomy 5", "the ten commandments, word for word"),
    ("Exodus 12-13", "Deuteronomy 16", "passover rules"),
    ("Numbers 1", "Numbers 26", "two census counts of the same tribes"),
    ("Numbers 13-14", "Deuteronomy 1", "the spies: who sent them, what was said"),
    ("Matthew 1", "Luke 3", "genealogy of Jesus"),
    ("Matthew 1-2", "Luke 1-2", "birth of Jesus: where they lived, where they fled"),
    ("Matthew 3-4", "Mark 1", "baptism and temptation"),
    ("Matthew 8-9", "Mark 5", "the demoniacs and Jairus: how many, what town"),
    ("Matthew 10", "Mark 6", "instructions to the twelve: staff, sandals"),
    ("Matthew 21", "Mark 11", "the fig tree and the triumphal entry: how many animals, what day"),
    ("Matthew 26-27", "Mark 14-15", "trial and crucifixion: the hour, the words, the thieves"),
    ("Luke 22-23", "John 18-19", "trial and crucifixion: the day, the cross-bearer"),
    ("Matthew 28", "Mark 16", "resurrection morning: who came, who was there, what was said"),
    ("Luke 24", "John 20", "resurrection morning and the appearances"),
    ("Matthew 27", "Acts 1", "how Judas died and who bought the field"),
    ("Acts 9", "Acts 22", "Paul's conversion: what the men heard and saw"),
    ("Acts 22", "Acts 26", "Paul's conversion: who fell, what was said"),
    ("Acts 9", "Galatians 1", "where Paul went after his conversion"),
    ("Acts 15", "Galatians 2", "the Jerusalem council"),
    ("Luke 24", "Acts 1", "the ascension: when and where"),
]

# flat-denial probes: one verse says X, another says not-X as a general claim.
THEMES = [
    "does God change his mind, repent, or relent",
    "does God tempt or test anyone",
    "has any man seen God face to face and lived",
    "are children punished for the sins of their fathers",
    "is a man justified by faith apart from works",
    "should you answer a fool according to his folly",
    "does God delight in sacrifice and burnt offering",
    "does God create evil and calamity",
    "will the earth abide for ever or pass away",
    "do the dead know anything, is there thought in the grave",
    "should your good works be seen by men or done in secret",
    "can a believer fall away or is no one plucked from his hand",
    "is it right to swear an oath",
    "does God hear the prayer of the wicked",
    "is there any God besides Jehovah, are there other gods",
    "did John the Baptist recognise Jesus as the Christ",
    "is anyone righteous, is there none that doeth good",
    "did God command or forbid child sacrifice",
    "does God dwell in temples made with hands",
    "is wealth a blessing from God or a curse",
    "does wisdom bring joy or does it bring grief",
    "should a man marry or remain unmarried",
    "who bears whose burden",
    "is the law abolished or established",
    "must the gentiles be circumcised",
    "may you eat every creature or only clean ones",
    "does God show partiality or respect persons",
    "is Jesus equal to the Father or less than the Father",
    "will everyone be saved or only a few",
    "is God's anger for a moment or for ever",
    "should you honour the king or call no man master",
    "does faith come before or after works",
    "how long was Jesus in the heart of the earth",
    "who was the father of Joseph the husband of Mary",
    "does God repay the sinner in this life or the next",
    "is it lawful to kill or is killing forbidden",
    "does God want mercy or does He want offerings",
    "may a man see God, may a man hear God's voice",
    "is the Lord slow to anger or quick to destroy",
    "should you resist evil or turn the other cheek",
    "does God lie or send a lying spirit",
    "did anyone ascend to heaven before Jesus",
    "is salvation by grace or by keeping commandments",
    "should women speak in the assembly",
    "does everyone die once or do some never die",
    "is the sabbath binding or is every day alike",
    "does God know everything or does He come down to see",
    "can God be resisted or does none stay His hand",
    "is Jesus the son of David or David's Lord",
    "does the sun move or does the earth stand still",
]

# ------------------------------------------------------------------- helpers


def die(msg):
    print("bcon: " + msg, file=sys.stderr)
    sys.exit(1)


def norm(s):
    """Fold text so quotes match regardless of markup, case, or punctuation."""
    s = re.sub(r"<[Ff][Ii]>", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def clean(s):
    return re.sub(r"\s+", " ", re.sub(r"<[Ff][Ii]>", "", s)).strip()


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def plural(n, word):
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


# ---------------------------------------------------------------- ylt corpus

_YLT = None


def ylt():
    global _YLT
    if _YLT is None:
        path = P("ylt.json")
        if not os.path.exists(path):
            path = YLT_SEED
        if not os.path.exists(path):
            die("no ylt.json. run: %s init" % ME)
        raw = json.load(open(path, encoding="utf-8"))
        idx, order = {}, []
        for b in raw["books"]:
            order.append(b["name"])
            for c in b["chapters"]:
                idx[(b["name"], c["chapter"])] = [
                    (v["verse"], v["text"]) for v in c["verses"]
                ]
        _YLT = (idx, order)
    return _YLT


ALIASES = {
    "song of solomon": "Song of Songs", "canticles": "Song of Songs",
    "psalm": "Psalms", "revelations": "Revelation", "ecc": "Ecclesiastes",
    "sos": "Song of Songs", "mt": "Matthew", "mk": "Mark", "lk": "Luke",
    "jn": "John", "gen": "Genesis", "ex": "Exodus", "exod": "Exodus",
    "lev": "Leviticus", "num": "Numbers", "deut": "Deuteronomy", "dt": "Deuteronomy",
    "josh": "Joshua", "judg": "Judges", "ps": "Psalms", "prov": "Proverbs",
    "isa": "Isaiah", "jer": "Jeremiah", "ezek": "Ezekiel", "dan": "Daniel",
    "rom": "Romans", "gal": "Galatians", "eph": "Ephesians", "phil": "Philippians",
    "col": "Colossians", "heb": "Hebrews", "rev": "Revelation", "jas": "James",
}


def book(name):
    _, order = ylt()
    n = re.sub(r"\s+", " ", name.strip().lower())
    n = re.sub(r"^([123])\s*", r"\1 ", n)
    for b in order:
        if b.lower() == n:
            return b
    if n in ALIASES:
        return ALIASES[n]
    hits = [b for b in order if b.lower().startswith(n)]
    if len(hits) == 1:
        return hits[0]
    if hits:
        die("ambiguous book %r: %s" % (name, ", ".join(hits)))
    die("unknown book %r" % name)


REF_RE = re.compile(r"^\s*((?:[1-3]\s*)?[A-Za-z][A-Za-z ]*?)\s*(\d+):(\d+)(?:\s*-\s*(\d+))?\s*$")


def parse_ref(ref):
    m = REF_RE.match(ref)
    if not m:
        die("bad ref %r. want 'Book 3:16' or 'Book 3:16-18'" % ref)
    bk, ch, v1, v2 = book(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)
    return bk, ch, v1, int(v2) if v2 else v1


def verses(ref):
    bk, ch, v1, v2 = parse_ref(ref)
    idx, _ = ylt()
    if (bk, ch) not in idx:
        die("no such chapter: %s %d" % (bk, ch))
    out = [(n, t) for n, t in idx[(bk, ch)] if v1 <= n <= v2]
    if not out:
        die("no such verse: %s" % ref)
    return bk, ch, out


def canon_ref(ref):
    bk, ch, vs = verses(ref)
    return "%s %d:%d" % (bk, ch, vs[0][0]) if len(vs) == 1 else \
           "%s %d:%d-%d" % (bk, ch, vs[0][0], vs[-1][0])


# ------------------------------------------------------------------- storage


def load(fn):
    path = P(fn)
    if not os.path.exists(path):
        return []
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def save(fn, rows):
    with open(P(fn), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def state(new=None):
    path = P("state.json")
    if new is not None:
        json.dump(new, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        return new
    if not os.path.exists(path):
        die("no state.json. run: %s init" % ME)
    return json.load(open(path, encoding="utf-8"))


def all_recs():
    return load("findings.jsonl") + load("candidates.jsonl")


def get(rid):
    for fn in ("findings.jsonl", "candidates.jsonl"):
        for r in load(fn):
            if r["id"] == rid:
                return r, fn
    die("no record %r" % rid)


def put(rec, fn):
    """Write rec into fn, removing it from the other tier."""
    other = "candidates.jsonl" if fn == "findings.jsonl" else "findings.jsonl"
    save(other, [r for r in load(other) if r["id"] != rec["id"]])
    rows = [r for r in load(fn) if r["id"] != rec["id"]]
    rows.append(rec)
    save(fn, rows)


def next_id():
    n = 0
    for r in all_recs() + load("rejected.jsonl"):
        m = re.match(r"c(\d+)$", r.get("id", ""))
        if m:
            n = max(n, int(m.group(1)))
    return "c%03d" % (n + 1)


# ----------------------------------------------------------------- commands


def cmd_init(a):
    os.makedirs(DIR, exist_ok=True)
    if not os.path.exists(P("ylt.json")):
        if not os.path.exists(YLT_SEED):
            die("cannot find a YLT corpus at %s. copy one to %s" % (YLT_SEED, P("ylt.json")))
        import shutil
        shutil.copy(YLT_SEED, P("ylt.json"))
    for fn in ("findings.jsonl", "candidates.jsonl", "rejected.jsonl"):
        open(P(fn), "a").close()
    if not os.path.exists(P("state.json")):
        state({"pass": 1, "mode_cursor": 0, "theme_cursor": 0, "parallel_cursor": 0,
               "sweep_cursor": 0, "no_new_streak": 0, "new_this_pass": 0,
               "leads": [], "covered": {}, "started": now()})
    if not os.path.isdir(P(".git")):
        run(["git", "init", "-q"])
        open(P(".gitignore"), "w").write("ylt.json\n")
    cmd_render(a)
    print("bcon ready at %s" % DIR)


def run(args):
    return subprocess.run(args, cwd=DIR, capture_output=True, text=True)


def cmd_ref(a):
    for ref in a:
        bk, ch, vs = verses(ref)
        for n, t in vs:
            print("%s %d:%d  %s" % (bk, ch, n, clean(t)))


def cmd_chapter(a):
    if len(a) < 2:
        die("usage: chapter <Book> <n>")
    bk, ch = book(" ".join(a[:-1])), int(a[-1])
    idx, _ = ylt()
    if (bk, ch) not in idx:
        die("no such chapter")
    print("== %s %d ==" % (bk, ch))
    for n, t in idx[(bk, ch)]:
        print("%d  %s" % (n, clean(t)))


STOP = set("""a an the and or but if of to in on at by for with from as is are was were
be been being it its this that these those he she they them his her their you your thou
thy thee ye we us our i me my not no nor so then than there here when where who whom which
what all any both each few more most other some such only own same too very can will just
do does did doth hath have has had shall should would may might must lo unto upon into out
up down over under again further once about against between during before after above below
saith said say says""".split())


def _tok(s):
    return [w for w in re.findall(r"[a-z0-9]+", norm(s).lower()) if w not in STOP and len(w) > 1]


_IX = None


def local_index():
    """BM25 over every verse in the local corpus. Built once, in memory."""
    global _IX
    if _IX is None:
        import math
        from collections import Counter
        idx, order = ylt()
        docs, df = [], Counter()
        for b in order:
            ch = 1
            while (b, ch) in idx:
                for n, t in idx[(b, ch)]:
                    tf = Counter(_tok(t))
                    docs.append((b, ch, n, t, tf, sum(tf.values())))
                    df.update(tf.keys())
                ch += 1
        N = len(docs)
        avg = sum(d[5] for d in docs) / N
        iw = {w: math.log(1 + (N - c + 0.5) / (c + 0.5)) for w, c in df.items()}
        _IX = (docs, iw, avg)
    return _IX


def local_search(q, bk=None, ch=None, k=10):
    docs, iw, avg = local_index()
    qt = _tok(q)
    if not qt:
        return []
    out = []
    for b, c, n, t, tf, ln in docs:
        if bk and b != bk:
            continue
        if ch and c != int(ch):
            continue
        sc = 0.0
        for w in qt:
            f = tf.get(w)
            if f:
                sc += iw[w] * f * 2.5 / (f + 1.5 * (0.25 + 0.75 * ln / avg))
        if sc > 0:
            out.append((sc, b, c, n, t))
    out.sort(key=lambda r: -r[0])
    return out[:k]


def api_books(force=False):
    """Which books the live collection actually serves. Probed once, cached."""
    s = state()
    if not force and s.get("api_books"):
        return set(s["api_books"])
    _, order = ylt()
    good = []
    for b in order:
        if api_call("the word of God", b, None) :
            good.append(b)
    s["api_books"] = good
    state(s)
    return set(good)


def api_call(q, bk, ch):
    p = {"q": q, "v": ""}
    if bk:
        p["b"] = bk
    if ch:
        p["x"] = str(int(ch))
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(p), headers={
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) bcon/1", "accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read().decode()).get("r") or []
    except Exception:
        return []


def _args(a):
    bk = ch = None
    rest = []
    i = 0
    while i < len(a):
        if a[i] == "-b":
            bk = a[i + 1]; i += 2
        elif a[i] == "-x":
            ch = a[i + 1]; i += 2
        else:
            rest.append(a[i]); i += 1
    return " ".join(rest), (book(bk) if bk else None), ch


def cmd_find(a):
    q, bk, ch = _args(a)
    if not q:
        die('usage: find "<query>" [-b Book] [-x chapter]')
    served = api_books()
    rows = []
    if bk is None or bk in served:
        for h in api_call(q, bk, ch):
            rows.append(("api", h["s"], h["b"], h["c"], h["v"], h["t"]))
    if bk is not None and bk not in served:
        rows = [("local", sc, b, c, n, t) for sc, b, c, n, t in local_search(q, bk, ch)]
    elif bk is None:
        for sc, b, c, n, t in local_search(q, None, ch, k=40):
            if b not in served:
                rows.append(("local", sc, b, c, n, t))
                if sum(1 for r in rows if r[0] == "local") == 6:
                    break
    if not rows:
        print("(no hits)")
        return
    api_rows = [r for r in rows if r[0] == "api"]
    loc_rows = [r for r in rows if r[0] == "local"]
    if api_rows and loc_rows:
        api_rows = api_rows[:6]
    for eng, sc, b, c, v, t in api_rows:
        print("api   %6.3f  %s %s:%s  %s" % (sc, b, c, v, clean(t)))
    if loc_rows:
        if api_rows:
            print("-- below: keyword search over the %d books the live index does not serve"
                  % (len(ylt()[1]) - len(served)))
        for eng, sc, b, c, v, t in loc_rows:
            print("local %6.3f  %s %s:%s  %s" % (sc, b, c, v, clean(t)))


def cmd_local(a):
    q, bk, ch = _args(a)
    if not q:
        die('usage: local "<query>" [-b Book] [-x chapter]')
    hits = local_search(q, bk, ch)
    if not hits:
        print("(no hits)")
        return
    for sc, b, c, n, t in hits:
        print("%6.3f  %s %d:%d  %s" % (sc, b, c, n, clean(t)))


def cmd_coverage(a):
    """Re-probe which books the live index serves."""
    served = api_books(force=True)
    _, order = ylt()
    miss = [b for b in order if b not in served]
    print("live index serves %d of %d books" % (len(served), len(order)))
    if miss:
        print("missing: %s" % ", ".join(miss))
        print("those fall back to local keyword search automatically.")


def cmd_grep(a):
    if not a:
        die("usage: grep <regex> [-b Book]")
    bk = None
    if "-b" in a:
        i = a.index("-b"); bk = book(a[i + 1]); a = a[:i] + a[i + 2:]
    rx = re.compile(" ".join(a), re.I)
    idx, order = ylt()
    hits = 0
    for b in order:
        if bk and b != bk:
            continue
        ch = 1
        while (b, ch) in idx:
            for n, t in idx[(b, ch)]:
                c = clean(t)
                if rx.search(c):
                    hits += 1
                    if hits <= 120:
                        print("%s %d:%d  %s" % (b, ch, n, c))
            ch += 1
    print("-- %d hits%s" % (hits, " (showing 120)" if hits > 120 else ""))


def _side(ref, quote):
    bk, ch, vs = verses(ref)
    hay = norm(" ".join(t for _, t in vs))
    nq = norm(quote)
    if not nq:
        die("empty quote for %s" % ref)
    if nq not in hay:
        print("bcon: quote not found in %s" % canon_ref(ref), file=sys.stderr)
        print("  you wrote: %s" % quote, file=sys.stderr)
        for n, t in vs:
            print("  actual %d: %s" % (n, clean(t)), file=sys.stderr)
        sys.exit(1)
    return {"ref": canon_ref(ref), "q": clean(quote)}


def _kv(a):
    out, i = {}, 0
    while i < len(a):
        if a[i].startswith("--"):
            k = a[i][2:].replace("-", "_")
            if i + 1 < len(a) and not a[i + 1].startswith("--"):
                out[k] = a[i + 1]; i += 2
            else:
                out[k] = "1"; i += 1
        else:
            i += 1
    return out


def cmd_add(a):
    k = _kv(a)
    need = ("cat", "strength", "conflict", "a_ref", "a_q", "b_ref", "b_q")
    miss = [n for n in need if n not in k]
    if miss:
        die("missing " + ", ".join("--" + m.replace("_", "-") for m in miss))
    if k["cat"] not in CATS:
        die("cat must be one of: " + " ".join(CATS))
    st = int(k["strength"])
    if st < 2:
        die("strength 1 is not a finding. use: %s kill, or drop it" % ME)
    if st > 5:
        die("strength maxes at 5")
    side_a, side_b = _side(k["a_ref"], k["a_q"]), _side(k["b_ref"], k["b_q"])
    if side_a["ref"] == side_b["ref"]:
        die("both sides are the same verse")
    pair = {side_a["ref"], side_b["ref"]}
    chaps = {r.rsplit(":", 1)[0] for r in pair}
    for r in all_recs():
        ex = {r["a"]["ref"], r["b"]["ref"]}
        if ex == pair:
            die("duplicate of %s: %s" % (r["id"], r["conflict"]))
        if {x.rsplit(":", 1)[0] for x in ex} == chaps:
            print("note: %s already covers this chapter pair - %s" % (r["id"], r["conflict"]),
                  file=sys.stderr)
    s = state()
    rec = {"id": next_id(), "cat": k["cat"], "strength": st,
           "conflict": clean(k["conflict"]), "a": side_a, "b": side_b,
           "extra": [], "attacks": [], "hardened": 0,
           "first_pass": s["pass"], "last_touched": s["pass"], "notes": k.get("notes", "")}
    tier = "findings.jsonl" if st >= 4 else "candidates.jsonl"
    put(rec, tier)
    s["new_this_pass"] = s.get("new_this_pass", 0) + 1
    state(s)
    print("%s added to %s [strength %d] %s" % (rec["id"], tier.split(".")[0], st, rec["conflict"]))


def cmd_show(a):
    if not a:
        die("usage: show <id>")
    r, fn = get(a[0])
    print(json.dumps(r, indent=1, ensure_ascii=False))


def cmd_set(a):
    if not a:
        die("usage: set <id> --strength 5 --conflict '...' --cat who --notes '...'")
    r, fn = get(a[0])
    k = _kv(a[1:])
    for f in ("conflict", "notes"):
        if f in k:
            r[f] = clean(k[f])
    if "cat" in k:
        if k["cat"] not in CATS:
            die("cat must be one of: " + " ".join(CATS))
        r["cat"] = k["cat"]
    if "strength" in k:
        r["strength"] = max(2, min(5, int(k["strength"])))
    for side in ("a", "b"):
        rk, qk = side + "_ref", side + "_q"
        if rk in k or qk in k:
            r[side] = _side(k.get(rk, r[side]["ref"]), k.get(qk, r[side]["q"]))
    if "extra_ref" in k and "extra_q" in k:
        r["extra"].append(_side(k["extra_ref"], k["extra_q"]))
    s = state()
    r["last_touched"] = s["pass"]
    put(r, "findings.jsonl" if r["strength"] >= 4 else "candidates.jsonl")
    print("%s updated [strength %d] %s" % (r["id"], r["strength"], r["conflict"]))


def cmd_attack(a):
    if len(a) < 1:
        die("usage: attack <id> --harm '<the best harmonisation>' --verdict survives|demote|kill --why '...'")
    r, fn = get(a[0])
    k = _kv(a[1:])
    for f in ("harm", "verdict", "why"):
        if f not in k:
            die("missing --" + f)
    if k["verdict"] not in ("survives", "demote", "kill"):
        die("verdict must be survives, demote, or kill")
    s = state()
    r["attacks"].append({"pass": s["pass"], "harm": clean(k["harm"]),
                         "verdict": k["verdict"], "why": clean(k["why"])})
    r["last_touched"] = s["pass"]
    if k["verdict"] == "survives":
        r["hardened"] = r.get("hardened", 0) + 1
        put(r, "findings.jsonl" if r["strength"] >= 4 else "candidates.jsonl")
        print("%s survived attack %d" % (r["id"], r["hardened"]))
    elif k["verdict"] == "demote":
        r["strength"] = max(2, r["strength"] - 1)
        put(r, "findings.jsonl" if r["strength"] >= 4 else "candidates.jsonl")
        print("%s demoted to strength %d" % (r["id"], r["strength"]))
    else:
        cmd_kill([r["id"], "--why", k["why"]])


def cmd_promote(a):
    r, _ = get(a[0])
    r["strength"] = min(5, r["strength"] + 1)
    r["last_touched"] = state()["pass"]
    put(r, "findings.jsonl" if r["strength"] >= 4 else "candidates.jsonl")
    print("%s now strength %d" % (r["id"], r["strength"]))


def cmd_demote(a):
    r, _ = get(a[0])
    r["strength"] = max(2, r["strength"] - 1)
    r["last_touched"] = state()["pass"]
    put(r, "findings.jsonl" if r["strength"] >= 4 else "candidates.jsonl")
    print("%s now strength %d" % (r["id"], r["strength"]))


def cmd_kill(a):
    if not a:
        die("usage: kill <id> --why '...'")
    k = _kv(a[1:])
    if "why" not in k:
        die("--why is required. the reason stops a later pass re-raising it")
    r, fn = get(a[0])
    save(fn, [x for x in load(fn) if x["id"] != r["id"]])
    dead = load("rejected.jsonl")
    dead.append({"id": r["id"], "conflict": r["conflict"],
                 "refs": [r["a"]["ref"], r["b"]["ref"]],
                 "why": clean(k["why"]), "pass": state()["pass"]})
    save("rejected.jsonl", dead)
    print("%s killed: %s" % (r["id"], k["why"]))


def cmd_merge(a):
    if len(a) < 2:
        die("usage: merge <id> <into-id>")
    src, _ = get(a[0])
    dst, fn = get(a[1])
    dst["extra"].extend([src["a"], src["b"]] + src.get("extra", []))
    dst["strength"] = max(dst["strength"], src["strength"])
    dst["last_touched"] = state()["pass"]
    put(dst, "findings.jsonl" if dst["strength"] >= 4 else "candidates.jsonl")
    cmd_kill([src["id"], "--why", "merged into %s" % dst["id"]])


def cmd_dupes(a):
    recs = all_recs()
    seen = {}
    for r in recs:
        key = frozenset(x.rsplit(":", 1)[0] for x in (r["a"]["ref"], r["b"]["ref"]))
        seen.setdefault(key, []).append(r)
    n = 0
    for key, group in sorted(seen.items(), key=lambda kv: -len(kv[1])):
        if len(group) > 1:
            n += 1
            print("%s" % " | ".join(sorted(key)))
            for r in group:
                print("   %s [s%d] %s" % (r["id"], r["strength"], r["conflict"]))
    print("-- %d chapter pairs with more than one record" % n)


def cmd_lead(a):
    s = state()
    if not a or a[0] == "list":
        for l in s["leads"]:
            if not l["done"]:
                print("%d  %s" % (l["n"], l["text"]))
        print("-- %s" % plural(sum(1 for l in s["leads"] if not l["done"]), "open lead"))
        return
    if a[0] == "done":
        for l in s["leads"]:
            if l["n"] == int(a[1]):
                l["done"] = True
        state(s)
        print("lead %s closed" % a[1])
        return
    n = max([l["n"] for l in s["leads"]] + [0]) + 1
    s["leads"].append({"n": n, "text": clean(" ".join(a)), "added": s["pass"], "done": False})
    state(s)
    print("lead %d queued" % n)


def cmd_cover(a):
    if len(a) < 2:
        die("usage: cover <Book> <n|n-m>")
    s = state()
    bk = book(" ".join(a[:-1]))
    spec = a[-1]
    lo, _, hi = spec.partition("-")
    rng = range(int(lo), int(hi or lo) + 1)
    have = set(s["covered"].get(bk, []))
    have |= set(rng)
    s["covered"][bk] = sorted(have)
    state(s)
    print("%s: %d chapters swept" % (bk, len(have)))


def cmd_note(a):
    with open(P("log.md"), "a", encoding="utf-8") as f:
        f.write("- pass %d: %s\n" % (state()["pass"], clean(" ".join(a))))
    print("noted")


def cmd_verify(a):
    bad = 0
    for r in all_recs():
        for side in ["a", "b"] + list(range(len(r.get("extra", [])))):
            d = r[side] if isinstance(side, str) else r["extra"][side]
            try:
                bk, ch, vs = verses(d["ref"])
            except SystemExit:
                print("%s: unreadable ref %s" % (r["id"], d["ref"]))
                bad += 1
                continue
            if norm(d["q"]) not in norm(" ".join(t for _, t in vs)):
                print("%s: quote does not match %s" % (r["id"], d["ref"]))
                bad += 1
    print("-- %d bad quotes out of %d records" % (bad, len(all_recs())))
    return bad


def _block(r):
    out = ["### %s  %s" % (r["id"], r["conflict"]), ""]
    for d in [r["a"], r["b"]] + r.get("extra", []):
        out.append("- **%s** — %s" % (d["ref"], d["q"]))
    tags = "`%s` · strength %d" % (r["cat"], r["strength"])
    if r.get("hardened"):
        tags += " · survived %s" % plural(r["hardened"], "attack")
    out += ["", tags, ""]
    if r.get("notes"):
        out += [r["notes"], ""]
    return "\n".join(out)


def cmd_render(a):
    s = state()
    for fn, title, blurb in (
        ("findings.jsonl", "Bible contradictions",
         "Internal conflicts only. Both sides quoted from Young's Literal Translation "
         "and checked against the text. Nothing here needs information from outside the Bible."),
        ("candidates.jsonl", "Candidates",
         "Real conflicts that still need explaining. Not yet obvious enough for the main list."),
    ):
        rows = sorted(load(fn), key=lambda r: (-r["strength"], -r.get("hardened", 0), r["id"]))
        md = ["# %s" % title, "", blurb, "",
              "%d %s · pass %d · updated %s"
              % (len(rows), "entry" if len(rows) == 1 else "entries", s["pass"], now()), ""]
        for cat in CATS:
            grp = [r for r in rows if r["cat"] == cat]
            if grp:
                md += ["## %s (%d)" % (CAT_NAMES[cat], len(grp)), ""]
                md += [_block(r) for r in grp]
        out = "FINDINGS.md" if fn == "findings.jsonl" else "CANDIDATES.md"
        open(P(out), "w", encoding="utf-8").write("\n".join(md).rstrip() + "\n")
    print("rendered FINDINGS.md (%d) and CANDIDATES.md (%d)"
          % (len(load("findings.jsonl")), len(load("candidates.jsonl"))))


CAT_NAMES = {"num": "Numbers that differ", "who": "Different actor or object",
             "when": "Dates and ages", "where": "Different place",
             "order": "Order of events", "law": "Command against command",
             "claim": "Flat denials"}


def cmd_stats(a):
    s = state()
    f, c, d = load("findings.jsonl"), load("candidates.jsonl"), load("rejected.jsonl")
    idx, order = ylt()
    total_ch = len(idx)
    done_ch = sum(len(v) for v in s["covered"].values())
    print("pass          %d   (started %s)" % (s["pass"], s["started"]))
    print("findings      %d   (strength 5: %d, 4: %d)"
          % (len(f), sum(1 for r in f if r["strength"] == 5), sum(1 for r in f if r["strength"] == 4)))
    print("candidates    %d" % len(c))
    print("killed        %d" % len(d))
    print("hardened      %d records have survived at least one attack"
          % sum(1 for r in f if r.get("hardened")))
    print("coverage      %d/%d chapters (%.1f%%)" % (done_ch, total_ch, 100.0 * done_ch / total_ch))
    print("open leads    %d" % sum(1 for l in s["leads"] if not l["done"]))
    print("dry streak    %d passes with no new finding" % s["no_new_streak"])


def _next_sweep(s):
    idx, _ = ylt()
    for bk in SWEEP_ORDER:
        have = set(s["covered"].get(bk, []))
        ch = 1
        while (bk, ch) in idx:
            if ch not in have:
                last = ch
                while (bk, last + 1) in idx and (last + 1) not in have and last - ch < 2:
                    last += 1
                return bk, ch, last
            ch += 1
    return None


def cmd_brief(a):
    s = state()
    pool = LATE_MODES if s["no_new_streak"] >= 3 else MODES
    mode = pool[s["mode_cursor"] % len(pool)]
    open_leads = [l for l in s["leads"] if not l["done"]]
    if mode == "lead" and not open_leads:
        mode = "theme"
    recs = all_recs()
    if mode in ("deepen", "attack") and not recs:
        mode = "parallel"

    print("PASS %d   MODE %s" % (s["pass"], mode.upper()))
    print("-" * 60)
    if mode == "parallel":
        job = PARALLELS[s["parallel_cursor"] % len(PARALLELS)]
        print("Diff these two accounts of the same thing, verse by verse:")
        print("  A: %s\n  B: %s\n  what to watch: %s" % job)
        print("\nRead both with `%s chapter`, side by side. Every number, name," % ME)
        print("place, and order of events. Where they differ, that is your finding.")
    elif mode == "number":
        print("Numeric sweep. Pick a family of numbers and cross-check every one:")
        print("  reign lengths · ages at accession · census totals · army sizes")
        print("  years of famine · temple measures · returnee tallies · prices paid")
        print("\nUse `%s grep` on the local text, for example:" % ME)
        print("  %s grep 'reigned .* years' -b 2 Kings" % ME)
        print("  %s grep '(hundred|thousand) (and )?(thirty|forty|fifty)'" % ME)
    elif mode == "theme":
        th = THEMES[s["theme_cursor"] % len(THEMES)]
        print("Flat-denial probe: %s" % th)
        print("\n  %s find \"%s\"" % (ME, th))
        print("\nThen search the OPPOSITE claim. You want one verse stating it and")
        print("another denying it as a general rule, not two verses about two cases.")
    elif mode == "sweep":
        nx = _next_sweep(s)
        if not nx:
            print("Every chapter is swept. Switching to deepen.")
            mode = "deepen"
        else:
            bk, c1, c2 = nx
            print("Sweep new ground: %s %d%s" % (bk, c1, "-%d" % c2 if c2 > c1 else ""))
            print("\nRead it: %s chapter %s %d" % (ME, bk, c1))
            print("For every checkable claim (a number, a name, a place, a rule,")
            print("a general statement about God), ask what else in the Bible speaks")
            print("to it, and find that with `%s find`." % ME)
            print("\nWhen done: %s cover %s %d-%d" % (ME, bk, c1, c2))
    if mode == "lead":
        print("Chase queued leads. Open now:")
        for l in open_leads[:6]:
            print("  %d  %s" % (l["n"], l["text"]))
        print("\nClose each with: %s lead done <n>" % ME)
    elif mode == "deepen":
        stale = sorted(recs, key=lambda r: (r["last_touched"], r["id"]))[:5]
        print("Sharpen these. Tighten each to the shortest quote pair that still")
        print("shows the clash, and cut the conflict line to under 12 words.")
        for r in stale:
            print("  %s [s%d] %s" % (r["id"], r["strength"], r["conflict"]))
        print("\n  %s show <id>   then   %s set <id> --a-q '...' --conflict '...'" % (ME, ME))
    elif mode == "attack":
        soft = sorted(recs, key=lambda r: (r.get("hardened", 0), -r["strength"]))[:5]
        print("Try to break these. For each, write the best harmonisation you can.")
        print("A harmonisation only counts if the BIBLE supplies it. Outside history,")
        print("archaeology, manuscript claims, or 'the original language' do not count.")
        for r in soft:
            print("  %s [s%d, hardened %d] %s"
                  % (r["id"], r["strength"], r.get("hardened", 0), r["conflict"]))
        print("\n  %s attack <id> --harm '...' --verdict survives|demote|kill --why '...'" % ME)
    elif mode == "tidy":
        print("Housekeeping. In order:")
        print("  1. %s verify        every stored quote still matches the text" % ME)
        print("  2. %s dupes         merge anything saying the same thing" % ME)
        print("  3. review CANDIDATES.md  promote what got sharper, kill what did not")
        print("  4. %s stats" % ME)
    print("-" * 60)
    f, c = load("findings.jsonl"), load("candidates.jsonl")
    print("have: %d findings, %d candidates, %d killed, %s"
          % (len(f), len(c), len(load("rejected.jsonl")), plural(len(open_leads), "open lead")))
    if s["no_new_streak"] >= 3:
        print("dry streak %d - depth over volume this pass" % s["no_new_streak"])
    print("close the pass with: %s done" % ME)


def cmd_done(a):
    s = state()
    mode = (LATE_MODES if s["no_new_streak"] >= 3 else MODES)[s["mode_cursor"] % len(
        LATE_MODES if s["no_new_streak"] >= 3 else MODES)]
    cmd_render(a)
    new = s.get("new_this_pass", 0)
    if mode in ("parallel", "number", "theme", "sweep", "lead"):
        s["no_new_streak"] = 0 if new else s["no_new_streak"] + 1
    if mode == "theme":
        s["theme_cursor"] += 1
    if mode == "parallel":
        s["parallel_cursor"] += 1
    s["mode_cursor"] += 1
    s["pass"] += 1
    s["new_this_pass"] = 0
    state(s)
    msg = "chore(bcon): pass %d %s, +%d" % (s["pass"] - 1, mode, new)
    run(["git", "add", "-A"])
    run(["git", "commit", "-q", "-m", msg[:72]])
    print("pass %d closed (+%d). next: %s brief" % (s["pass"] - 1, new, ME))


def cmd_help(a):
    print(__doc__)
    print("""commands
  init                       set up %s
  brief                      what to do this pass. START HERE, every pass.
  done                       render, commit, advance the pass counter

read
  ref <ref>...               exact verse text, e.g. ref "2 Samuel 24:9"
  chapter <Book> <n>         a whole chapter, numbered
  find "<q>" [-b B] [-x C]   live semantic verse search (10 hits max)
  grep <regex> [-b B]        regex over the whole local YLT, offline

record
  add --cat <%s>
      --strength 2..5 --conflict "<short line>"
      --a-ref "Book c:v" --a-q "<exact words>"
      --b-ref "Book c:v" --b-q "<exact words>" [--notes "..."]
  show <id> · set <id> --field val · promote <id> · demote <id>
  attack <id> --harm "..." --verdict survives|demote|kill --why "..."
  kill <id> --why "..." · merge <id> <into> · dupes · verify

track
  lead "<idea>" · lead list · lead done <n>
  cover <Book> <n|n-m> · note "<line>" · stats · render""" % (DIR, "|".join(CATS)))


CMDS = {k[4:]: v for k, v in list(globals().items()) if k.startswith("cmd_")}

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        cmd_help([])
        sys.exit(0)
    fn = CMDS.get(args[0])
    if not fn:
        die("unknown command %r. try: %s help" % (args[0], ME))
    if args[0] != "init" and not os.path.exists(P("state.json")):
        die("not set up. run: %s init" % ME)
    fn(args[1:])

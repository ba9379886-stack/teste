#!/usr/bin/env python3
"""Check a video script written in the video-script format (French & English).
Measures timing, WPM pace, caption reading speed, hook speed, AI clichés, causality, and claims.

Usage: python3 skills/video-script/scripts/check_script.py script.md [--json]
Exit code 1 when any check FAILs.
"""
import json
import os
import re
import sys

DEFAULTS = {
    "wpm": 150,        # comfortable narration pace (~2.5 words/sec in FR & EN)
    "hook_max": {"social": 3.5, "ad": 3.5, "drama": 3.5, "demo": 5.0, "review": 5.0, "explainer": 5.0},
    "max_shot": 11,    # 4-11 s scenes hold visual retention best
    "caption_s_per_word": 0.33,  # BBC subtitle guideline: ~3 words/sec max on-screen super
}

AI_TELLS = [
    # English AI tells
    "delve", "tapestry", "testament to", "in today's fast-paced", "in today's world", "ever-evolving",
    "game-changer", "game changer", "revolutionize", "unlock the power", "unleash", "elevate your",
    "seamless", "seamlessly", "cutting-edge", "next level", "take it to the next level", "look no further",
    "whether you're", "imagine a world", "buckle up", "let's dive in", "dive into", "without further ado",
    "it's not just", "isn't just", "more than just", "the best part?", "here's the thing", "picture this",
    "say goodbye to", "say hello to", "transform the way", "embark", "journey", "realm", "landscape",
    # French AI tells
    "dans un monde où", "dans le monde actuel", "plongeons dans", "sans plus attendre",
    "révolutionner", "changer la donne", "passer au niveau supérieur", "libérez le potentiel",
    "dites adieu à", "bien plus qu'un simple", "bien plus qu'une simple", "que vous soyez",
    "il est important de noter", "en fin de compte", "véritable allié au quotidien",
]

AI_TELL_PATTERNS = [
    (
        r"\b(it's|it is|this is|that's|it isn't|this isn't)\s+(not\s+)?(just\s+|only\s+)?"
        r"(a |an |the )?[\w' -]{1,30}[.,;:\u2014\u2013-]+\s*(it's|it is|this is|that's)\b",
        "it's not X, it's Y",
    ),
    (
        r"\bce\s+n['’]est\s+pas\s+(juste|seulement|qu['’]un|qu['’]une)\s+[\w'’ -]{1,35}[.,;:\u2014\u2013-]+\s*c['’]est\b",
        "ce n'est pas juste X, c'est Y",
    ),
]

WEAK_OPENERS = [
    # English
    "hey guys", "hi guys", "welcome back", "in this video", "today we're going to", "today i'm going to",
    "have you ever wondered", "did you know", "hello everyone", "what's up",
    # French
    "salut à tous", "bonjour à tous", "bienvenue sur", "dans cette vidéo", "aujourd'hui on va voir",
    "aujourd'hui nous allons", "est-ce que tu t'es déjà demandé", "saviez-vous que", "coucou tout le monde",
]

CTA_WORDS = [
    # English
    "try", "get", "download", "sign up", "link", "shop", "order", "start", "join", "follow",
    "comment", "save", "visit", "book", "grab", "tap", "watch", "subscribe", "install", "claim",
    # French
    "clique", "cliquez", "commande", "commandez", "lien", "bio", "panier", "essaye", "essayez",
    "découvre", "découvrez", "abonne", "abonnez", "commente", "commentez", "enregistre", "enregistrez",
    "profite", "profitez", "boutique", "dis-moi", "dites-moi",
]


def parse_time(s: str) -> float:
    s = s.strip().lower().replace("s", "")
    if ":" in s:
        m, sec = s.split(":", 1)
        return int(m) * 60 + float(sec)
    return float(s)


def parse(path: str):
    text = open(path, encoding="utf-8").read()
    header, rows, cols = {}, [], None
    for line in text.splitlines():
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cols is None:
                cols = [c.lower() for c in cells]
                continue
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            rows.append(dict(zip(cols, cells)))
        elif cols is None:
            m = re.match(r"^\s*([a-z_ ]+):\s*(.+)$", line, re.I)
            if m:
                header[m.group(1).strip().lower().replace(" ", "_")] = m.group(2).strip()
    return header, rows, text


def col(row: dict, *names: str) -> str:
    for k, v in row.items():
        if any(n in k for n in names):
            return v
    return ""


def tokenize_words(s: str) -> list[str]:
    s = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", s)
    s = re.sub(r"\b[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ0-9 ]{1,20}:\s*", " ", s)
    s = s.replace("<br>", " ")
    return re.findall(r"[\w€$%][\w'’€$%.,-]*", s, flags=re.UNICODE)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    header, rows, text = parse(sys.argv[1])
    fmt = header.get("format", "social").split()[0].lower()

    def num(key, default):
        m = re.match(r"\s*([\d.]+)", header.get(key, ""))
        return float(m.group(1)) if m else float(default)

    wpm = num("wpm", DEFAULTS["wpm"])
    wps = wpm / 60.0
    hook_max = num("hook_max", DEFAULTS["hook_max"].get(fmt, 3.5))
    max_shot = num("max_shot", DEFAULTS["max_shot"])
    header["facts"] = header.get("facts", "").split("  ")[0].strip()
    res = []

    def add(level, check, msg):
        res.append({"level": level, "check": check, "msg": msg})

    if not rows:
        add("FAIL", "table", "no beat table found (| # | time | spoken | on screen | visual | sound |)")
        return finish(res)

    beats = []
    for i, r in enumerate(rows, 1):
        t = col(r, "time", "temps")
        m = re.match(r"\s*([\d:.]+)\s*s?\s*[-–—]+\s*([\d:.]+)\s*s?", t)
        if not m:
            add("FAIL", "timing", f"beat {i}: time '{t}' is not start-end (0:00-0:03)")
            continue
        a, b = parse_time(m.group(1)), parse_time(m.group(2))
        beats.append({
            "n": i,
            "a": a,
            "b": b,
            "spoken": col(r, "spoken", "vo", "dialog", "voice", "voix", "texte parlé"),
            "screen": col(r, "screen", "text", "super", "écran", "overlay"),
            "visual": col(r, "visual", "shot", "image", "visuel"),
            "sound": col(r, "sound", "audio", "sfx", "music", "son"),
        })

    if not beats:
        return finish(res)

    for x, y in zip(beats, beats[1:]):
        if abs(x["b"] - y["a"]) > 0.25:
            add("FAIL", "timing", f"gap or overlap between beat {x['n']} ({x['b']}s) and beat {y['n']} ({y['a']}s)")
    total = beats[-1]["b"] if beats else 0
    if "length" in header:
        want = parse_time(re.sub(r"[^\d:.]", "", header["length"]) or "0")
        if want and abs(total - want) > max(1.5, 0.12 * want):
            add("FAIL", "length", f"beats run {total:.1f}s, header says {want:.0f}s")

    all_words = 0
    for x in beats:
        d = max(0.1, x["b"] - x["a"])
        w = len(tokenize_words(x["spoken"]))
        all_words += w
        if w > d * wps * 1.18:
            add("FAIL", "pace", f"beat {x['n']}: {w} words in {d:.1f}s (max ~{d * wps:.0f} at {wpm:.0f} wpm); cut words or add time")
        elif w > d * wps * 1.05:
            add("WARN", "pace", f"beat {x['n']}: {w} words in {d:.1f}s is tight at {wpm:.0f} wpm")
        sw = len(tokenize_words(x["screen"]))
        if sw and sw * DEFAULTS["caption_s_per_word"] > d:
            add("WARN", "caption", f"beat {x['n']}: {sw} on-screen words need {sw * DEFAULTS['caption_s_per_word']:.1f}s to read, beat is {d:.1f}s")
        if d > max_shot:
            add("WARN", "shot", f"beat {x['n']} is {d:.1f}s, longer than max_shot ({max_shot:.0f}s); consider splitting")
        if not x["visual"].strip() or x["visual"].strip() in ("-", "—"):
            add("FAIL", "visual", f"beat {x['n']} has no visual; every beat must say what we see")

    if total:
        add("INFO", "pace", f"{all_words} spoken words in {total:.1f}s = {all_words / total * 60:.0f} wpm (budget {wpm:.0f})")

    h = beats[0]
    if h["a"] > 0.01:
        add("FAIL", "hook", "first beat does not start at 0")
    if h["b"] > hook_max:
        add("WARN", "hook", f"first beat ends at {h['b']:.1f}s; hook should land by {hook_max:.1f}s for {fmt}")
    if not (h["spoken"].strip() or h["screen"].strip()):
        add("WARN", "hook", "first beat has no words on screen or spoken")
    first = (h["spoken"] or h["screen"]).lower().strip(' "“«»')
    for p in WEAK_OPENERS:
        if first.startswith(p):
            add("WARN", "hook", f"opens with '{p}': start directly on the subject, conflict, or proof")

    spoken_all = " ".join(x["spoken"] for x in beats)
    for x in beats:
        for label_name, seg in (("spoken", x["spoken"]), ("on screen", x["screen"])):
            low = seg.lower().replace("’", "'")
            hits = [p for p in AI_TELLS if p in low]
            hits += [lbl for rx, lbl in AI_TELL_PATTERNS if re.search(rx, low, flags=re.I)]
            for p in hits:
                add("WARN", "ai-tell", f"beat {x['n']} ({label_name}): '{p}' sounds like AI copy; rewrite concretely")

    sentences = [s for s in re.split(r"[.!?]+", re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", spoken_all)) if s.strip()]
    for s in [s.strip() for s in sentences if len(tokenize_words(s)) > 22][:3]:
        add("WARN", "ear", f"long spoken sentence ({len(tokenize_words(s))} words); split for breath: '{s[:60]}...'")

    n_and_then = len(re.findall(r"\b(and then|et ensuite|puis ensuite)\b", spoken_all, re.I))
    if n_and_then >= 2:
        add("WARN", "causality", f"sequential filler x{n_and_then}: connect beats with 'mais / donc' ('but / so') instead")

    has_sources = bool(re.search(r"^#+\s*(sources|références)", text, re.I | re.M))
    facts = header.get("facts", "")
    facts_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), facts) if facts else ""
    facts_text = open(facts_path, encoding="utf-8").read() if facts and os.path.isfile(facts_path) else None
    for x in beats:
        for field in ("spoken", "screen"):
            s_ = x[field]
            if facts_text is not None:
                for m in re.finditer(r"\d[\d,.]*", s_):
                    n = m.group(0).rstrip(".,")
                    if n not in facts_text and n.replace(",", "") not in facts_text:
                        add("WARN", "claim", f"beat {x['n']}: '{n}' is not in {facts}; verify source")
            elif re.search(r"\d+(\.\d+)?\s?(%|x\b|×|percent|pourcent|million|milliard)|\$\d|€\d|\d+\s?€", s_, re.I) and "[src" not in s_ and not has_sources and not facts:
                add("WARN", "claim", f"beat {x['n']} states a figure ('{s_[:50]}') without [src: ...] or Sources section")

    cta = header.get("cta", "").lower()
    if (fmt in ("ad", "demo", "review") or (fmt == "social" and cta)) and cta.split()[:1] not in (["none"], ["aucun"]):
        tail = " ".join((x["spoken"] + " " + x["screen"]).lower() for x in beats[-2:])
        if not ((cta and any(w in tail for w in cta.split()[:3])) or any(w in tail for w in CTA_WORDS)):
            add("WARN", "ending", "no clear CTA action detected in the final two beats")

    return finish(res)


def finish(res):
    if "--json" in sys.argv:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        for r in res:
            print(f"{r['level']:5} {r['check']:9} {r['msg']}")
        n = {lvl: sum(r["level"] == lvl for r in res) for lvl in ("FAIL", "WARN")}
        print(f"\n{n['FAIL']} fail, {n['WARN']} warn")
    sys.exit(1 if any(r["level"] == "FAIL" for r in res) else 0)


if __name__ == "__main__":
    main()

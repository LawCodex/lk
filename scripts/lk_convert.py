#!/usr/bin/env python3
"""Convert the cached Parliament of Sri Lanka Act PDFs (see lk_fetch.py) into Markdown.

Usage: lk_convert.py [REPO_DIR]
"""
import csv, datetime, io, json, os, re, sys, unicodedata
sys.path.insert(0, os.path.dirname(__file__))
from lk_pdfmd import to_markdown

RAW = os.environ.get("RAW", os.path.join(os.path.dirname(__file__), "..", "..", "_raw", "lk"))
REPO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..")
RETRIEVED = os.environ.get("RETRIEVED", datetime.date.today().isoformat())
ORD = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh",
       "twelfth", "thirteenth", "fourteenth", "fifteenth", "sixteenth", "seventeenth", "eighteenth", "nineteenth",
       "twentieth", "twenty-first", "twenty-second", "twenty-third"]


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def slug(s, n=80):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return s[:n].rsplit("-", 1)[0] if len(s) > n else s


def tidy_title(t):
    t = " ".join(t.split())
    t = re.sub(r"\(\s+", "(", t)
    t = re.sub(r"\s+\)", ")", t)
    if t.isupper():
        t = t.title()
    return t


def main():
    rows = list(csv.DictReader(io.StringIO(open(f"{RAW}/list.csv", encoding="utf-8-sig").read())))
    state = json.load(open(f"{RAW}/state.json"))
    stats = {"written": 0, "scanned": 0, "no_pdf": 0, "missing": 0, "empty": []}
    seen = set()
    # Constitution (revised edition)
    cpath = f"{RAW}/constitution.pdf"
    if os.path.exists(cpath):
        body = to_markdown(cpath)
        fm = ["---", 'title: "The Constitution of the Democratic Socialist Republic of Sri Lanka"', "type: constitution",
              "jurisdiction: lk", "language: en", "date: 1978-09-07",
              'consolidation: "As amended up to 31st October 2022 (Revised Edition – 2023)"', "status: in_force",
              'source: "https://www.parliament.lk/files/pdf/constitution.pdf"', f"retrieved: {RETRIEVED}", "---"]
        md = "\n".join(fm) + "\n\n# The Constitution of the Democratic Socialist Republic of Sri Lanka\n\n" + body
        os.makedirs(f"{REPO}/constitution", exist_ok=True)
        open(f"{REPO}/constitution/constitution.md", "w", encoding="utf-8", newline="\n").write(md)
        stats["written"] += 1
    for r in rows:
        key = r["Link to Act"].rsplit("/", 1)[-1]
        st = state.get(key, {}).get("status")
        if st != "text":
            if st == "scanned":
                stats["scanned"] += 1
            elif st == "no_pdf":
                stats["no_pdf"] += 1
            else:
                stats["missing"] += 1
            continue
        path = f"{RAW}/pdf/{key}.pdf"
        if not os.path.exists(path):
            stats["missing"] += 1
            continue
        title0 = tidy_title(r["Act Title"])
        no = r["Act No."].strip()
        date = r["Endorsed Date"].strip() or None
        year = (date or "0000")[:4]
        m = re.match(r"^0*(\d+)\s*/\s*(\d{4})$", no)
        is_const = re.search(r"amendment to the constitution", title0, re.I)
        if m:
            num, year = str(int(m.group(1))), m.group(2)
            ident = f"Act, No. {num} of {year}"
            title = f"{title0} Act, No. {num} of {year}" if not title0.lower().endswith(" act") else f"{title0}, No. {num} of {year}"
        else:
            num, ident, title = None, None, title0
        body = to_markdown(path)
        if len(body) < 200:
            stats["empty"].append(key)
            continue
        if is_const:
            rel = f"constitution/amendments/{date or year}-{slug(title0)}.md"
            typ = "constitutional_amendment"
        else:
            rel = f"acts/{year}/{year}-{(num.zfill(2) + '-') if num else ''}{slug(title0)}.md"
            typ = "act"
        if rel in seen:
            rel = rel[:-3] + f"-{key.lower()}.md"
        seen.add(rel)
        fm = ["---", f"title: {q(title)}"]
        if ident:
            fm.append(f"identifier: {q(ident)}")
        fm += [f"type: {typ}", "jurisdiction: lk", "language: en"]
        if date and not date.startswith("1900"):
            fm.append(f"date: {date}")
        fm += ["version: as_enacted", "status: unknown",
               f"source: {q(r['Link to Act'])}", f"source_pdf: {q(state[key]['pdf'])}", f"retrieved: {RETRIEVED}", "---"]
        md = "\n".join(fm) + "\n\n# " + title + "\n\n" + body
        out = os.path.join(REPO, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(md)
        stats["written"] += 1
    json.dump(stats, open(f"{RAW}/convert-stats.json", "w"), indent=1)
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in stats.items()}))


if __name__ == "__main__":
    main()

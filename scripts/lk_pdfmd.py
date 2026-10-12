#!/usr/bin/env python3
"""Convert a Sri Lankan Act / Constitution PDF (Government Printer layout with marginal notes)
into Markdown.

Uses `pdftotext -bbox` word coordinates:
  * per page, the body column is found from the right edge shared by most lines; words that lie
    entirely in the outer margin (left or right of the body column) are marginal notes;
  * running heads (repeated top lines, page numbers) and printer's footers ("PL 012345 - ...")
    are dropped;
  * body lines are grouped into paragraphs on vertical gaps;
  * a paragraph that starts with a section number ("12. ...") becomes a heading
    "#### 12. <marginal note>"; other marginal notes are emitted in italics before the paragraph
    they stand beside;
  * PART / CHAPTER / SCHEDULE lines become headings.
"""
import re, subprocess, html
from collections import Counter

WORD = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>')
PAGE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', re.S)
SEC = re.compile(r"^(\d{1,3}[A-Z]{0,2})\.\s*(\(\d+\)\s*)?\S")
PART = re.compile(r"^(PART|Part)\s+[IVXLC\d]+[A-Z]?\b")
CHAP = re.compile(r"^(CHAPTER|Chapter)\s+[IVXLC\d]+[A-Z]?\b")
SCHED = re.compile(r"^((FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH)\s+)?SCHEDULE\b")


def pages_words(pdf):
    out = subprocess.run(["pdftotext", "-bbox", pdf, "-"], capture_output=True).stdout.decode("utf-8", "replace")
    pages = []
    for pm in PAGE.finditer(out):
        W, H = float(pm.group(1)), float(pm.group(2))
        words = [(float(a), float(b), float(c), float(d), html.unescape(t)) for a, b, c, d, t in WORD.findall(pm.group(3))]
        pages.append((W, H, words))
    return pages


def make_lines(words, tol=3.0):
    words = sorted(words, key=lambda w: (round(w[1]), w[0]))
    lines = []
    for w in words:
        for L in lines:
            if abs(L["y"] - w[1]) <= tol:
                L["w"].append(w)
                break
        else:
            lines.append({"y": w[1], "w": [w]})
    segs = []
    for L in lines:
        L["w"].sort(key=lambda w: w[0])
        cur = [L["w"][0]]
        for w in L["w"][1:]:
            if w[0] - cur[-1][2] > 15:
                segs.append(cur)
                cur = [w]
            else:
                cur.append(w)
        segs.append(cur)
    out = []
    for ws in segs:
        out.append({"y": min(w[1] for w in ws), "w": ws, "x0": ws[0][0], "x1": max(w[2] for w in ws),
                    "y1": max(w[3] for w in ws)})
    out.sort(key=lambda L: (L["y"], L["x0"]))
    return out


def split_columns(lines, W):
    """return body_left, body_right of the main text column.
    lines are segments (split at gaps > 15pt); the right edge is the most common segment end among
    wide segments, the left edge the smallest start among wide segments ending there."""
    wide = [L for L in lines if L["x1"] - L["x0"] > W * 0.4]
    if not wide:
        return 0, W, 0
    rights = Counter(round(L["x1"]) for L in wide)
    br = rights.most_common(1)[0][0]
    starts = [L["x0"] for L in wide if abs(round(L["x1"]) - br) <= 3]
    bl = min(starts) if starts else min(L["x0"] for L in wide)
    return bl, br, len(starts)


def text_of(ws):
    return " ".join(w[4] for w in ws)


def page_items(page, heads, cols=None, body_h=None):
    W, H, words = page
    lines = make_lines(words)
    # drop running heads & footers
    keep = []
    for L in lines:
        t = text_of(L["w"]).strip()
        norm = re.sub(r"[\d\s]+", "", t)
        if L["y"] < H * 0.13 and (norm in heads or re.fullmatch(r"[\divx]+", t)):
            continue
        if L["y"] > H * 0.88 and (re.match(r"^(PL|P\.L\.)\s*\d", t) or re.fullmatch(r"\d+", t)):
            continue
        keep.append(L)
    bl, br, n = split_columns(keep, W)
    if n < 6 and cols:
        bl, br = cols
    if body_h:
        mh = body_h
    else:
        hs = sorted(w[3] - w[1] for L in keep for w in L["w"])
        mh = hs[len(hs) // 2] if hs else 10
    small = lambda w: (w[3] - w[1]) < mh * 0.9
    # extent of the normal-size text on the page (body column)
    nx1 = sorted(w[2] for L in keep for w in L["w"] if not small(w))
    nx0 = sorted(w[0] for L in keep for w in L["w"] if not small(w))
    nbr = nx1[int(len(nx1) * 0.98)] if nx1 else br
    nbl = nx0[int(len(nx0) * 0.02)] if nx0 else bl
    body, notes = [], []
    for L in keep:
        out = lambda w: ((w[0] >= br + 1.5 or w[2] <= bl - 1.5) and (small(w) or w[0] >= br + 25 or w[2] <= bl - 25)) or \
            (small(w) and (w[0] >= nbr - 1 or w[2] <= nbl + 1))
        mw = [w for w in L["w"] if out(w)]
        bw = [w for w in L["w"] if not out(w)]
        if mw:
            notes.append({"y": min(w[1] for w in mw), "y1": max(w[3] for w in mw), "t": text_of(mw)})
        if not bw:
            continue
        y = min(w[1] for w in bw)
        if body and abs(body[-1]["y"] - y) <= 3:
            body[-1]["t"] += " " + text_of(bw)
            body[-1]["x1"] = bw[-1][2]
        else:
            body.append({"y": y, "y1": max(w[3] for w in bw), "x0": bw[0][0], "x1": bw[-1][2], "t": text_of(bw)})
    # group margin notes
    groups = []
    for n in notes:
        if groups and n["y"] - groups[-1]["y1"] < 6:
            groups[-1]["t"] += " " + n["t"]
            groups[-1]["y1"] = n["y1"]
        else:
            groups.append(dict(n))
    # group body paragraphs
    gaps = [b2["y"] - b1["y"] for b1, b2 in zip(body, body[1:]) if 0 < b2["y"] - b1["y"] < 40]
    lh = sorted(gaps)[len(gaps) // 3] if gaps else 13
    paras = []
    for b in body:
        enum = re.match(r"^[“\"]?\(([a-z]{1,2}|[ivxl]+|\d+[A-Z]?)\)\s", b["t"]) and paras and \
            re.search(r"([;:\-–—.]|\bor|\band)\s*$", paras[-1]["t"])
        if paras and b["y"] - paras[-1]["ylast"] < lh * 1.45 and not enum:
            p = paras[-1]
            t = p["t"]
            if t.endswith("-") and not t.endswith(" -") and b["t"][:1].islower():
                p["t"] = t[:-1] + b["t"]
            else:
                p["t"] = t + " " + b["t"]
            p["ylast"] = b["y"]
        else:
            paras.append({"y": b["y"], "ylast": b["y"], "t": b["t"], "x0": b["x0"]})
    # attach notes to the paragraph nearest to their top
    for g in groups:
        best = None
        for p in paras:
            d = abs(p["y"] - g["y"])
            if p["y"] - 8 <= g["y"] <= p["ylast"] + 4 or d < 10:
                if best is None or d < abs(best["y"] - g["y"]):
                    best = p
        if best is None and paras:
            best = min(paras, key=lambda p: abs(p["y"] - g["y"]))
        if best is not None:
            best.setdefault("notes", []).append(g["t"])
    return paras


def running_heads(pages):
    c = Counter()
    for W, H, words in pages:
        for L in make_lines([w for w in words if w[1] < H * 0.13]):
            c[re.sub(r"[\d\s]+", "", text_of(L["w"]))] += 1
    n = len(pages)
    return {k for k, v in c.items() if v >= 3 and v >= n * 0.25}


def to_markdown(pdf, skip_cover=True, level_base=2):
    pages = pages_words(pdf)
    heads = running_heads(pages)
    # column bounds of each page; pages with few full lines borrow those of the nearest
    # page with the same parity (margin notes alternate sides on facing pages)
    bounds = []
    for W, H, words in pages:
        segs = [L for L in make_lines(words) if H * 0.1 < L["y"] < H * 0.92]
        bounds.append(split_columns(segs, W))
    hc = Counter(round(w[3] - w[1], 1) for W, H, words in pages for w in words)
    body_h = hc.most_common(1)[0][0] if hc else None
    cols = {}
    for pi, (bl, br, n) in enumerate(bounds):
        for d in (2, -2, 4, -4, 6, -6):
            k = pi + d
            if 0 <= k < len(bounds) and bounds[k][2] >= 6:
                cols[pi] = bounds[k][:2]
                break
    out = []
    H = lambda n: "#" * min(6, level_base + n)
    for pi, page in enumerate(pages):
        allt = " ".join(w[4] for w in page[2])
        if skip_cover and pi < 2 and re.search(r"PRINTED AT THE DEPARTMENT OF GOVERNMENT PRINTING|Price\s*:\s*Rs", allt, re.I) \
                and not re.search(r"BE it enacted", allt):
            continue
        paras = page_items(page, heads, cols.get(pi), body_h)
        for k, p in enumerate(paras):
            t = " ".join(p["t"].split())
            notes = [" ".join(n.split()) for n in p.get("notes", [])]
            # continuation of the previous page's last paragraph
            if k == 0 and out and out[-1][0] == "p" and not notes and t[:1].islower():
                out[-1] = ("p", out[-1][1] + " " + t)
                continue
            if len(t) < 120 and (PART.match(t) or SCHED.match(t)):
                out.append(("h0", t))
            elif len(t) < 120 and CHAP.match(t):
                out.append(("h1", t))
            elif SEC.match(t) and notes:
                num = SEC.match(t).group(1)
                out.append(("h2", f"{num}. {notes[0]}"))
                for n in notes[1:]:
                    out.append(("note", n))
                out.append(("p", t))
            else:
                for n in notes:
                    out.append(("note", n))
                out.append(("p", t))
    md = []
    for kind, t in out:
        t = t.replace("\\", "\\\\")
        t = re.sub(r"([*_`])", r"\\\1", t)
        if kind == "h0":
            md.append(H(0) + " " + t)
        elif kind == "h1":
            md.append(H(1) + " " + t)
        elif kind == "h2":
            md.append(H(2) + " " + t)
        elif kind == "note":
            md.append("*" + t + "*")
        else:
            if t.startswith(("#", ">", "- ", "+ ")):
                t = "\\" + t
            md.append(t)
    return "\n\n".join(md).strip() + "\n"


if __name__ == "__main__":
    import sys
    print(to_markdown(sys.argv[1]))

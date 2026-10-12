#!/usr/bin/env python3
"""Fetch Sri Lankan Acts (English, as certified) from the Parliament of Sri Lanka website.

* list of all Acts: https://www.parliament.lk/en/business-of-parliament/download-acts-listing/csv
* Act PDFs: https://www.parliament.lk/uploads/acts/gbills/english/<n>.pdf (Government Bills, G<n>);
  private Acts (P<n>): PDF link taken from the act-details page when there is one
* Constitution (revised edition): https://www.parliament.lk/files/pdf/constitution.pdf

PDFs without a text layer (scans) are recorded in RAW/scanned.json and deleted to save disk.
"""
import csv, io, json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
import requests

UA = "LawCodex/1.0 (+https://github.com/LawCodex)"
RAW = os.environ.get("RAW", os.path.join(os.path.dirname(__file__), "..", "..", "_raw", "lk"))
S = requests.Session()
S.headers["User-Agent"] = UA
LIST = "https://www.parliament.lk/en/business-of-parliament/download-acts-listing/csv"
CONST = "https://www.parliament.lk/files/pdf/constitution.pdf"


def get(url, path, delay=0.5):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return open(path, "rb").read()
    for attempt in range(5):
        try:
            r = S.get(url, timeout=300)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path + ".part", "wb") as f:
                f.write(r.content)
            os.replace(path + ".part", path)
            time.sleep(delay)
            return r.content
        except Exception as e:
            print("retry", attempt, url, e, file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    return None


def has_text(path):
    out = subprocess.run(["pdftotext", "-l", "6", path, "-"], capture_output=True).stdout.decode("utf-8", "replace")
    return len(re.sub(r"\s", "", out)) > 400


def main():
    os.makedirs(RAW, exist_ok=True)
    data = get(LIST, f"{RAW}/list.csv").decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(data)))
    get(CONST, f"{RAW}/constitution.pdf")
    state_p = f"{RAW}/state.json"
    state = json.load(open(state_p)) if os.path.exists(state_p) else {}

    def one(r):
        link = r["Link to Act"]
        key = link.rsplit("/", 1)[-1]
        if key in state:
            return
        pdf_url = None
        if key.startswith("G"):
            pdf_url = f"https://www.parliament.lk/uploads/acts/gbills/english/{key[1:]}.pdf"
        else:
            h = get(link, f"{RAW}/details/{key}.html")
            if h:
                m = re.search(r"href='(https://www.parliament.lk/uploads/[^']+/english/[^']+\.pdf)'", h.decode("utf-8", "replace"))
                pdf_url = m.group(1) if m else None
        if not pdf_url:
            state[key] = {"status": "no_pdf"}
            return
        path = f"{RAW}/pdf/{key}.pdf"
        b = get(pdf_url, path)
        if not b:
            state[key] = {"status": "missing", "pdf": pdf_url}
            return
        if has_text(path):
            state[key] = {"status": "text", "pdf": pdf_url}
        else:
            state[key] = {"status": "scanned", "pdf": pdf_url}
            os.remove(path)

    with ThreadPoolExecutor(3) as ex:
        for i, _ in enumerate(ex.map(one, rows)):
            if i % 100 == 0:
                print(i, len(rows), file=sys.stderr)
                json.dump(state, open(state_p, "w"), indent=0)
    json.dump(state, open(state_p, "w"), indent=0)


if __name__ == "__main__":
    main()

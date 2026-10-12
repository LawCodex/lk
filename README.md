# LawCodex — Sri Lanka (`lk`)

Legislation of the Democratic Socialist Republic of Sri Lanka as plain Markdown: the Constitution
(revised edition, as amended up to 31 October 2022) and the Acts of Parliament **as certified**
(not consolidated), in English, from the official website of the **Parliament of Sri Lanka**.

Part of [LawCodex](https://github.com/LawCodex): the laws of every country as Markdown in git.

Retrieved: 2026-10-12. **822 files.** This is a **partial** corpus — see *Not covered*.

## Contents

| Category | Directory | Files |
|---|---|---:|
| Constitution of the Democratic Socialist Republic of Sri Lanka (Revised Edition 2023, as amended up to 31 Oct 2022) | `constitution/constitution.md` | 1 |
| Amendments to the Constitution (18th–22nd) as certified | `constitution/amendments/` | 5 |
| Acts of Parliament, as certified, 1999–2026 | `acts/<year>/` | 816 |
| **Total** | | **822** |

Parliament's list of Acts has 3,731 entries (1893–2026). Their fate here:

| | Entries |
|---|---:|
| Converted (PDF with a text layer) | 821 |
| PDF is a scanned image (no text layer) — mostly 1980–2005 | 745 |
| No English PDF linked / file missing on the server | 296 |
| Not downloaded: entries endorsed in 1981 or earlier — a sample of these and all 378 Acts of the 1980s that were downloaded were scans or missing files; some scans are several hundred MB each | 1,869 |

## Not covered

- **Consolidated texts.** Acts are published as certified by the Speaker; later amendments are
  separate Acts (also included when available). There is no official free consolidated edition
  online: LawNet (`lawnet.gov.lk`, the Ministry of Justice legal information site that carried the
  *Legislative Enactments*) was not serving content at retrieval time (only a default hosting page),
  and its Internet Archive copies are a mix of case law and statute fragments split over many posts,
  not usable as a reliable source. Hence `version: as_enacted` and `status: unknown`.
- **Acts before ~1999** — scanned images only (see table). No OCR.
- **Sinhala and Tamil texts.** Parliament also publishes Sinhala (`/gbills/sinhala/`) and Tamil
  (`/gbills/tamil/`) PDFs. Their text layer is not faithful (vowel signs duplicated or misplaced,
  e.g. `ත්‍රස්්තවාාදීන්ට`), so they are not included. Under the Constitution (art. 23), Sinhala and
  Tamil are the languages of legislation and the English text is a translation; most Acts provide that
  the Sinhala text prevails in case of inconsistency.
- Subordinate legislation (regulations, orders in the Gazette).

## Structure

```
constitution/constitution.md
constitution/amendments/<date>-<slug>.md
acts/<year>/<year>-<act-no>-<slug>.md       e.g. acts/2026/2026-18-convention-on-the-suppression-of-terrorist-financing-amendment.md
```

Front matter: `title` (`<short title> Act, No. <n> of <year>`), `identifier`, `type` (`act`,
`constitution`, `constitutional_amendment`), `jurisdiction`, `language` (`en`), `date` (date the
Act was endorsed/certified), `version: as_enacted`, `status`, `source` (Parliament act page),
`source_pdf`, `retrieved`.

Body: text extracted from the PDF with word coordinates (`pdftotext -bbox`). Sri Lankan Acts print
the section headings as **marginal notes**; these are detected (outside the text column, smaller
font) and re-attached: each section becomes `#### <n>. <marginal note>` followed by the section text.
Marginal notes beside other paragraphs (e.g. subsections) are kept as an *italic* line before the
paragraph. `PART`/`CHAPTER`/`SCHEDULE` lines become `##`/`###` headings. Running heads, page numbers,
printer's lines and the cover page are dropped. Tables are flattened to text.

## Sources

- Parliament of Sri Lanka — list of Acts (CSV export of
  <https://www.parliament.lk/en/business-of-parliament/acts-listing>:
  `/en/business-of-parliament/download-acts-listing/csv`), act pages
  (`/en/business-of-parliament/act-details/G<n>`), PDFs (`/uploads/acts/gbills/english/<n>.pdf`).
- Constitution: <https://www.parliament.lk/files/pdf/constitution.pdf> (Revised Edition – 2023,
  published by the Parliament Secretariat).
- robots.txt allows these paths; no terms restricting reuse were found. ≤ 3 parallel requests.

## Licence

Acts of Parliament are official public texts. This compilation adds no copyrightable content.

## Regenerate

```
pip install -r scripts/requirements.txt
python scripts/lk_fetch.py      # caches the list and PDFs under ../_raw/lk (scans are deleted)
python scripts/lk_convert.py .  # writes the Markdown files
```

Note: `lk_fetch.py` walks the whole list; the published corpus stopped fetching at the 1981 entries
(see above).

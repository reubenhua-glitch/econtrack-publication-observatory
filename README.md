# EconTrack · Open Publication Observatory

A researcher in a department without a development economics seminar should be able to discover a new poverty study when its authors share it. EconTrack aims to make that possible across economics, finance and management. Our starting point is the public trail a paper leaves as it moves from working paper and submission through revision, acceptance and publication. Authors decide which stages to disclose.

## Try the prototype

Python 3.10 or later and its standard library are sufficient. From the repository root, run

```sh
python tracker.py disclosures.json
python -m unittest -v
```

The example contains three dated, manually curated public observations about two papers. The command returns the source URL, the short status wording, the observation date and the normalized stage for each current claim.

| Paper and journal | What you can check | Result |
| --- | --- | --- |
| *Wages, Taxes, and Labor Supply Elasticities*, The Economic Journal | On 22 November 2026, one coauthor's page said R&R and the other said conditionally accepted. [Pinchuan Ong](https://www.pinchuanong.com/research/) · [Janjala Chirakijja](https://sites.google.com/view/janjalachirakijja/research) | `needs_review` |
| *Slowdown in Immigration, Labor Shortages, and Declining Skill Premia*, Journal of International Economics | One author listed the paper as R&R. [Francesco Zanetti](https://users.ox.ac.uk/~wadh4073/research.htm) | `single_source` |

## How reconciliation works

Each record identifies the paper, journal, source URL, short evidence excerpt and date of observation. The sample assigns paper IDs by hand. The importer appends distinct observations to SQLite. Replaying the same records is idempotent. For each paper and journal, the report compares the latest observations from each source and preserves conflicting claims for human review. Earlier observations remain in the database. An observation date tells readers when a source was checked. Editorial decision dates often remain unknown.

To retain the evidence ledger between runs, use a database file

```sh
python tracker.py disclosures.json --db econtrack.sqlite3
python tracker.py disclosures.json --db econtrack.sqlite3
```

The first run on a new file adds three observations. The second adds zero. The test suite also checks late-arriving observations, same-day disagreements, papers reported at different journals and rollback on invalid input.

## First field trial

The [JIE pilot list](pilot-jie.csv) contains 31 distinct papers in EconTrack's revision category for the *Journal of International Economics*. Its 29 distinct source URLs give a collection job a bounded starting point. The file preserves the original wording (including resubmissions) and the date each record was last checked in the index, from 26 October through 13 November 2026. These baseline entries are candidates for a fresh check.

A collection job would revisit each source once per pass, compare proposed changes with the baseline and record unavailable pages for follow-up. A researcher would review each change and its supporting evidence before updating the public index.

The longer-term plan is to resolve working-paper versions across repositories and publishers using DOI links, author identity and title history. Once the evidence is reliable across fields, public alerts and a multilingual index can help researchers and policy analysts find work on poverty, credit access and firm growth while the research is still circulating. The prototype here covers evidence ingestion and reconciliation. Web collection, cross-source identity matching and subscriptions are planned.

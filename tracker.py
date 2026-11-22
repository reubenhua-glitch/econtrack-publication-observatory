"""Reconcile dated public disclosures of journal decisions. Python 3.10+."""

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from contextlib import closing
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit


STAGES = {
    "submitted", "under_review", "revise_and_resubmit", "revision_submitted",
    "conditionally_accepted", "accepted", "forthcoming", "published",
    "rejected", "withdrawn",
}
FIELDS = ("paper_id", "title", "journal", "source", "observed_on", "stage", "evidence")


def normalize(record):
    if not isinstance(record, dict):
        raise ValueError("each observation must be an object")
    fields = {}
    for name in FIELDS:
        value = record.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a nonempty string")
        fields[name] = value.strip()
    url = urlsplit(fields["source"])
    if url.scheme not in {"http", "https"} or not url.hostname:
        raise ValueError("source must be an HTTP(S) URL")
    if url.username is not None or url.password is not None:
        raise ValueError("source URL must omit credentials")
    if fields["stage"] not in STAGES:
        raise ValueError(f"unrecognized stage: {fields['stage']}")
    observed = date.fromisoformat(fields["observed_on"])
    if observed.isoformat() != fields["observed_on"]:
        raise ValueError("observed_on must use YYYY-MM-DD")
    return fields


def import_records(db, records):
    if not isinstance(records, list):
        raise ValueError("the input file must contain a JSON array")
    rows = []
    for index, record in enumerate(records, start=1):
        try:
            rows.append(normalize(record))
        except ValueError as error:
            raise ValueError(f"observation {index}: {error}") from error

    with db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS observations (
                paper_id TEXT NOT NULL, title TEXT NOT NULL, journal TEXT NOT NULL,
                source TEXT NOT NULL, observed_on TEXT NOT NULL,
                stage TEXT NOT NULL, evidence TEXT NOT NULL,
                UNIQUE(paper_id, title, journal, source, observed_on, stage, evidence)
            )
        """)
        old_count = db.total_changes
        db.executemany("""
            INSERT INTO observations
                (paper_id, title, journal, source, observed_on, stage, evidence)
            VALUES (:paper_id, :title, :journal, :source, :observed_on, :stage, :evidence)
            ON CONFLICT DO NOTHING
        """, rows)
    return db.total_changes - old_count


def make_report(db):
    db.row_factory = sqlite3.Row
    results = defaultdict(list)
    # Keep all claims from a source's latest observation day, including contradictions.
    latest = db.execute("""
        WITH last_seen AS (
            SELECT paper_id, journal, source, MAX(observed_on) AS observed_on
            FROM observations GROUP BY paper_id, journal, source
        )
        SELECT o.* FROM observations AS o JOIN last_seen
            USING (paper_id, journal, source, observed_on)
        ORDER BY o.paper_id, o.journal, o.observed_on DESC, o.source, o.stage, o.title, o.evidence
    """)
    for row in latest:
        results[(row["paper_id"], row["journal"])].append(dict(row))
    cases = []
    for (paper_id, journal), observations in results.items():
        stages = sorted({item["stage"] for item in observations})
        if len(stages) > 1:
            result = "needs_review"
        elif len({item["source"] for item in observations}) == 1:
            result = "single_source"
        else:
            result = "sources_agree"
        cases.append({
            "paper_id": paper_id, "journal": journal, "result": result,
            "reported_stages": stages, "observations": observations,
        })
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON array of public observations")
    parser.add_argument("--db", default=":memory:", help="optional persistent SQLite file")
    args = parser.parse_args()
    try:
        records = json.loads(args.input.read_text(encoding="utf-8-sig"))
        with closing(sqlite3.connect(args.db)) as db:
            added = import_records(db, records)
            cases = make_report(db)
    except (ValueError, OSError, sqlite3.Error) as error:
        print(f"econtrack: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"added": added, "cases": cases}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

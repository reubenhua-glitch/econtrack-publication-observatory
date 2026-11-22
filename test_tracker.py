import json
import sqlite3
import unittest
from pathlib import Path

from tracker import import_records, make_report


EXAMPLES = Path(__file__).with_name("disclosures.json")


class DisclosureTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.examples = json.loads(EXAMPLES.read_text(encoding="utf-8"))
        self.ong, self.chirakijja, self.zanetti = self.examples

    def test_public_examples_keep_disagreement_visible(self):
        self.assertEqual(import_records(self.db, self.examples), 3)
        cases = {case["journal"]: case for case in make_report(self.db)}
        disputed = cases["The Economic Journal"]
        self.assertEqual(disputed["result"], "needs_review")
        self.assertEqual(disputed["reported_stages"], ["conditionally_accepted", "revise_and_resubmit"])
        self.assertEqual(len(disputed["observations"]), 2)
        self.assertEqual(cases["Journal of International Economics"]["result"], "single_source")

    def test_replaying_an_observation_leaves_report_intact(self):
        import_records(self.db, self.examples)
        before = make_report(self.db)
        self.assertEqual(import_records(self.db, list(reversed(self.examples))), 0)
        self.assertEqual(make_report(self.db), before)

    def test_latest_per_source_survives_out_of_order_import(self):
        later = dict(self.ong, observed_on="2026-11-23", stage="conditionally_accepted",
                     evidence="Illustrative test observation.")
        import_records(self.db, [later, self.ong, self.chirakijja])
        case, = make_report(self.db)
        self.assertEqual(case["result"], "sources_agree")
        self.assertEqual(case["reported_stages"], ["conditionally_accepted"])
        self.assertEqual(self.db.execute("SELECT count(*) FROM observations").fetchone()[0], 3)

    def test_same_day_conflicts_remain_visible(self):
        later_claim = dict(self.ong, stage="accepted", evidence="Illustrative test observation.")
        import_records(self.db, [later_claim, self.ong])
        case, = make_report(self.db)
        self.assertEqual(case["result"], "needs_review")

    def test_two_journals_keep_separate_histories(self):
        other_journal = dict(self.ong, journal="Example Journal", stage="submitted",
                             evidence="Illustrative test observation.")
        import_records(self.db, [self.ong, other_journal])
        cases = make_report(self.db)
        self.assertEqual(len(cases), 2)
        self.assertTrue(all(case["result"] == "single_source" for case in cases))

    def test_invalid_batch_keeps_existing_ledger_intact(self):
        import_records(self.db, [self.zanetti])
        bad = dict(self.ong, observed_on="2026-02-30")
        with self.assertRaisesRegex(ValueError, "observation 2"):
            import_records(self.db, [self.ong, bad])
        self.assertEqual(len(make_report(self.db)), 1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM observations").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()

"""Cursor only advances for fully published summit source batches."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from summit_batch_cursor_v1 import next_offset


def event(offset,selected,eligible,status="success",pipeline="cime"):
    return {"status":status,"pipeline":pipeline,
            "report":{"offset":offset,"selectedCandidates":selected,"eligible":eligible}}


class TestSummitCursor(unittest.TestCase):
    def test_initial_and_successful_batches(self):
        self.assertEqual(next_offset(None),0)
        self.assertEqual(next_offset({"events":[event(0,100,1884)]}),100)
        self.assertEqual(next_offset({"events":[event(100,100,1884)]}),200)

    def test_failed_and_other_pipeline_do_not_advance(self):
        data={"events":[event(0,100,1884),event(100,100,1884,status="failure"),event(900,100,1884,pipeline="comuni")]}
        self.assertEqual(next_offset(data),100)

    def test_last_batch_wraps(self):
        self.assertEqual(next_offset({"events":[event(1800,84,1884)]}),0)
        self.assertEqual(next_offset({"events":[event(1800,100,1900)]}),0)

    def test_bad_legacy_event_restart(self):
        self.assertEqual(next_offset({"events":[{"status":"success","pipeline":"cime","report":{}}]}),0)
        with self.assertRaises(ValueError):
            next_offset({"events":"wrong type"})
        with self.assertRaises(ValueError):
            next_offset(None,0)


if __name__=="__main__":
    unittest.main()

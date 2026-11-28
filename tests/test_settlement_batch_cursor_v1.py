"""Incremental località cursor tests: only completed successful releases advance."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from settlement_batch_cursor_v1 import next_offset

def event(run, offset=None, count=None, status="success", pipeline="localita"):
    report={}
    if offset is not None: report["offset"]=offset
    if count is not None: report["selectedCandidates"]=count
    return {"runId":str(run),"pipeline":pipeline,"status":status,"report":report}

class CursorTests(unittest.TestCase):
    def test_first_success_after_legacy_untracked_history_starts_at_zero(self):
        self.assertEqual(next_offset({"events":[event(1,count=80)]}),0)
    def test_advance_when_last_success_completed_full_batch(self):
        h={"events":[event(1,0,80),event(2,80,80)]}
        self.assertEqual(next_offset(h),160)
    def test_failure_never_advances(self):
        h={"events":[event(1,0,80),event(2,80,80,status="failure")]}
        self.assertEqual(next_offset(h),80)
    def test_final_short_batch_wraps_to_start(self):
        h={"events":[event(1,640,80),event(2,720,37)]}
        self.assertEqual(next_offset(h),0)
    def test_empty_batch_wraps_to_zero(self):
        self.assertEqual(next_offset({"events":[event(1,800,0)]}),0)
    def test_other_pipelines_ignored(self):
        h={"events":[event(1,0,80),event(2,80,80,pipeline="comuni")]}
        self.assertEqual(next_offset(h),80)
    def test_invalid_batch_size_fails(self):
        with self.assertRaises(ValueError): next_offset(None,0)

if __name__=="__main__":unittest.main()

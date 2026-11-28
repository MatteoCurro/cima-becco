"""Persistent cursor and retry fairness, not repeated stagnant first 48 towns."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from update_municipality_progress_v1 import update_progress
from enrich_municipalities_v1 import choose_candidates

def town(code,name):
    return {"name":name,"sourceIds":{"istat":code},
      "administrativeHierarchy":{"provinceAbbreviation":"BL"}}
def release(entities):
    return {"releaseChannel":"ISTAT_DAIT_MUNICIPALITIES","isPublished":True,
      "entities":[{"sourceIds":{"istat":code},"quality":{"gate":"G2"}} for code in entities]}
class ProgressTests(unittest.TestCase):
    def test_next_run_prioritises_never_attempted(self):
        es=[town("025%03d"%i,"Comune "+str(i)) for i in range(1,101)]
        crosswalk={e["sourceIds"]["istat"]:"Q"+str(i+12345) for i,e in enumerate(es)}
        first=choose_candidates(es,crosswalk,limit=48)
        self.assertEqual(len(first),48)
        doc=update_progress(None,{"selectedCodes":first},release([]),"100",now="2026-11-28")
        nxt=choose_candidates(es,crosswalk,limit=48,progress=doc)
        self.assertEqual(len(nxt),48)
        self.assertFalse(set(first)&set(nxt),"must not process same 48 failed towns again")
        doc2=update_progress(doc,{"selectedCodes":nxt},release([]),"101",now="2026-11-29")
        self.assertEqual(doc2["statistics"]["processedDistinct"],96)
        self.assertEqual(doc2["statistics"]["firstAttemptedThisRun"],48)
    def test_refresh_rotates_and_still_attempts_new(self):
        es=[town("025%03d"%i,"Comune "+str(i)) for i in range(1,100)]
        crosswalk={e["sourceIds"]["istat"]:"Q"+str(i+12345) for i,e in enumerate(es)}
        older=release(["025%03d"%i for i in range(1,18)])
        a=choose_candidates(es,crosswalk,limit=8,previous=older,
                            progress={"successfulRuns":0,"attempts":{}})
        b=choose_candidates(es,crosswalk,limit=8,previous=older,
                            progress={"successfulRuns":1,"attempts":{}})
        self.assertEqual(len(a),16)
        self.assertNotEqual(a[:8],b[:8])
    def test_no_double_commit_from_same_run(self):
        first=["025001","025002"]
        d=update_progress(None,{"selectedCodes":first},release(["025001"]),"105")
        again=update_progress(d,{"selectedCodes":first},release(["025001"]),"105")
        self.assertEqual(d,again)
        self.assertEqual(d["statistics"]["publishedG2"],1)
        self.assertEqual(d["statistics"]["pendingRevisit"],1)
    def test_fails_closed_if_invalid_codes(self):
        with self.assertRaises(ValueError):
            update_progress(None,{"selectedCodes":["Canazei"]},release([]),"1")
if __name__=="__main__":unittest.main()

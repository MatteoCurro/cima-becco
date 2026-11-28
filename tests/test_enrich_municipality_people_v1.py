"""People: exact P19 / P551 / P937, verified P106 and no inferred locality."""
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from enrich_municipality_people_v1 import build,sparql_candidates, classify

def claim_item(qid):
    return {"mainsnak":{"datavalue":{"value":{"entity-type":"item","id":qid}}},"rank":"normal"}

def municipality(code,qid,name):
    return {"id":"municipality:"+code,"name":name,"slug":name.lower(),"kind":"municipality",
      "sourceIds":{"istat":code,"wikidata":qid,"wikidataVerifiedBy":"P635"},
      "quality":{"gate":"G2"},"relations":[]}
def archive():
    return {"releaseChannel":"ISTAT_DAIT_MUNICIPALITIES","entities":[
      municipality("022039","Q258031","Canazei"), municipality("025016","Q112233","Cortina")]}

def profile(qid,occupation="Q9149093",town="Q258031",prop="P19",date_of_death=False,wiki=None):
    claims={"P31":[claim_item("Q5")],"P106":[claim_item(occupation)],prop:[claim_item(town)]}
    if date_of_death:
        claims["P570"]=[{"mainsnak":{"datavalue":{"value":{"time":"+1980-06-02T00:00:00Z"}}}}]
    result={"claims":claims,"labels":{"it":{"value":"Persona "+qid}},
            "descriptions":{"it":{"value":"Alpinista delle Dolomiti"}},"sitelinks":{}}
    if wiki:result["sitelinks"]["itwiki"]={"title":wiki}
    return result

def result_binding(person,occupation,label,prop="P19",town="Q258031"):
    return {"person":{"value":"http://www.wikidata.org/entity/"+person},
      "town":{"value":"http://www.wikidata.org/entity/"+town},
      "relation":{"value":"http://www.wikidata.org/prop/direct/"+prop},
      "occupation":{"value":"http://www.wikidata.org/entity/"+occupation},
      "occupationLabel":{"value":label}}

def source(url,params):
    if "sparql" in url:
        return {"results":{"bindings":[
          result_binding("Q101","Q9149093","mountaineer"),
          result_binding("Q102","Q49757","scrittore"),
          result_binding("Q103","Q49757","scrittore"),
          result_binding("Q104","Q819677","mountain guide","P551"),
          result_binding("Q105","Q819677","mountain guide","P551"),
          result_binding("Q106","Q819677","mountain guide","P937"),
          result_binding("Q107","Q819677","mountain guide","P19","Q112233"),
        ]}}
    return {"entities":{
        "Q101":profile("Q101"),
        "Q102":profile("Q102","Q49757",wiki="Persona Q102"),
        "Q103":profile("Q103","Q49757",wiki=None),
        "Q104":profile("Q104","Q819677",prop="P551",date_of_death=True),
        "Q105":profile("Q105","Q819677",prop="P551",date_of_death=False),
        "Q106":profile("Q106","Q819677",prop="P937"),
        "Q107":profile("Q107","Q819677",town="Q112233"),
    }}

class PeopleContract(unittest.TestCase):
    def test_query_require_qid_and_valid_limit(self):
        with self.assertRaises(ValueError):sparql_candidates(["Canazei"],getter=source)
        rows=sparql_candidates(["Q258031","Q112233"],getter=source)
        self.assertEqual(len(rows),7)
    def test_whitelist_mountain_and_culture(self):
        self.assertEqual(classify("Q9149093",""),"montagna")
        self.assertEqual(classify("Q123","scrittore"),"cultura_e_ricerca")
        self.assertIsNone(classify("Q123","football coach"))
    def test_verified_direct_links_only(self):
        release=archive()
        people,report=build(release,getter=source,checked_at="2026-11-28T00:00:00Z")
        self.assertEqual(report["municipalitiesWithPeople"],1)
        connected=release["entities"][0]["connectedPeople"]
        ids={p["qid"] for p in connected}
        self.assertTrue({"Q101","Q102","Q104","Q106"}.issubset(ids))
        self.assertNotIn("Q103",ids)
        self.assertNotIn("Q105",ids)
        self.assertNotIn("Q107",ids) # candidate claimed Cortina but item P19 points elsewhere
        self.assertTrue(all(p["sourceId"].startswith("wikidata:") for p in connected))
        self.assertTrue(all(p["quality"]=="G1" for p in connected))
        self.assertTrue(all(p["relationType"] in ("birthplace_of","historical_residence_of","workplace_of") for p in connected))
        self.assertEqual(len(release["entities"][0]["relations"]),len(connected))
        self.assertTrue(all(p["quality"]["seoIndexable"] is False for p in people["entities"]))
        self.assertFalse(release["entities"][1].get("connectedPeople"))
    def test_api_failure_keeps_previous_links(self):
        release=archive()
        release["entities"][0]["connectedPeople"]=[{"name":"Verificato","verified":True}]
        def fail(url,params):raise TimeoutError("WDQS")
        _,report=build(release,getter=fail)
        self.assertEqual(report["municipalityPeopleLinks"],1)
        self.assertEqual(len(report["errors"]),1)
        self.assertEqual(release["entities"][0]["connectedPeople"][0]["name"],"Verificato")

if __name__=="__main__":unittest.main()

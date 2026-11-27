#!/usr/bin/env python3
"""SAT official Sentiero Italia Trentino stages, factual summary table only.

Extracts no GPX and no narrative articles. Official numbers, ascent, descent,
duration, difficulty + intermediate place names; attributes © SAT / ODbL.
"""
from __future__ import annotations
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request,urlopen
import json,re
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"experiments"/"cross-domain-pilot"
URL="https://www.sat.tn.it/sentiero-italia/"
class StageTable(HTMLParser):
    def __init__(self):
        super().__init__();self.rows=[];self.intr=False;self.cell=None;self.cells=[]
    def handle_starttag(self,tag,attrs):
        if tag=="tr":self.intr=True;self.cells=[]
        elif self.intr and tag in ("td","th"):self.cell=""
        elif tag=="br" and self.cell is not None:self.cell+=" "
    def handle_data(self,data):
        if self.cell is not None:self.cell+=data
    def handle_endtag(self,tag):
        if tag in ("td","th") and self.cell is not None:
            self.cells.append(re.sub(r"\s+"," ",self.cell).strip());self.cell=None
        elif tag=="tr" and self.intr:
            if self.cells:self.rows.append(self.cells)
            self.intr=False;self.cell=None
def parse_minutes(val):
    val=val.strip()
    m=re.fullmatch(r"(\d{1,2})[.:](\d{2})",val)
    if not m:return None
    h,n=map(int,m.groups())
    return h*60+n if n<60 else None
def num(val):
    val=re.sub(r"\s|\.","",val)
    return int(val) if val.isdigit() else None
def parse(html):
    parser=StageTable();parser.feed(html)
    items={}
    for cells in parser.rows:
        if len(cells)<6:continue
        code=cells[0].strip().upper()
        if not re.fullmatch(r"SI [A-Z]\d{2}S?",code):continue
        if code in items:continue
        via=[x.strip() for x in re.split(r"\s+[–—]\s+",cells[1]) if x.strip()]
        item={"id":code.replace(" ","-").lower(),"code":code,
          "sequence":len(items)+1,"descriptionOfPlaces":cells[1],
          "startNameReported":via[0] if via else None,
          "endNameReported":via[-1] if len(via)>1 else None,
          "intermediateNamesReported":via[1:-1],
          "ascentM":num(cells[2]),"descentM":num(cells[3]),
          "durationMinutes":parse_minutes(cells[4]),
          "difficultyOriginal":cells[5],
          "source":{"url":URL,"dataLicence":"ODbL-1.0",
           "credit":"© Società degli Alpinisti Tridentini (SAT)"},
          "status":"official_stage_summary_unverified_current_access"}
        items[code]=item
    return list(items.values())
def main():
    errors=[];stages=[];diagnostics={}
    try:
        req=Request(URL,headers={"User-Agent":"CimaBecco-Research/0.1 (https://www.cimabecco.it)"})
        with urlopen(req,timeout=45) as r:html=r.read(4_000_000).decode("utf-8","replace")
        diagnostics={'htmlBytes':len(html),'hasStageCode':bool(re.search(r'SI\\s*C0?1',html)),'stageCodeIndex':html.find('SI C01'),'htmlTableTags':html.count('<tr'),'firstStageNeighborhood':html[max(0,html.find('SI C01')-120):html.find('SI C01')+350] if 'SI C01' in html else None}
        stages=parse(html)
        if not stages:errors.append("No summary table rows matched. Inspect SAT HTML structure.")
    except Exception as ex:errors.append(str(ex)[:300])
    report={"at":datetime.now(timezone.utc).isoformat(),"source":URL,
      "stages":len(stages),"withAscent":sum(s["ascentM"] is not None for s in stages),
      "withDescent":sum(s["descentM"] is not None for s in stages),
      "withDuration":sum(s["durationMinutes"] is not None for s in stages),
      "withDifficulty":sum(bool(s["difficultyOriginal"]) for s in stages),
      "chainByNamesOnly":all(stages[i]["endNameReported"]==stages[i+1]["startNameReported"]
                            for i in range(len(stages)-1)) if stages else None,
      "sourceNote":"Only official published table. Names alone do not prove footpath connection or current practicability.",
      "errors":errors,"sourceDiagnostics":diagnostics,"examples":stages[:3]}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"sat-sentiero-italia-stages.json").write_text(json.dumps({"stages":stages},ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"trek-stage-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="examples"},ensure_ascii=False,indent=2))
if __name__=="__main__":main()

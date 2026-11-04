"""Probe current and historic route names on the old read-only deployment."""
import datetime as dt
import json
from pathlib import Path
import urllib.error
import urllib.request

HERE=Path(__file__).resolve().parent
HOST="https://statarena-analytics-jumo9il0b-hlemonniers-projects.vercel.app"
ROUTES=[
 ("historical manifest","/data/dashboard-manifest.json"),
 ("new manifest","/api/dashboard/manifest"),
 ("new partition pages","/api/seasons/partition?season=2025%2F2026&league=l_3FJFUl&limit=100&format=columns"),
 ("new fixture pages","/api/fixtures?season=2025%2F2026&league=l_3FJFUl&limit=100"),
 ("new scouting routes","/api/scouting/routes?season=2025%2F2026"),
 ("new match summary","/api/matches/m_18Uw0k/summary"),
 ("historical match observation","/api/archive/matches/m_18Uw0k"),
 ("historical saved leagues","/api/pitchapi/leagues"),
 ("new archive index","/api/archives/index?kind=results"),
 ("historical archive index","/data/raw/openfootball/index.json"),
 ("new association rankings","/api/rankings/associations?year=2025"),
 ("historical association rankings","/data/raw/rankings/uefa-associations/2025.uefa.json"),
 ("new supplemental catalog","/api/supplemental"),
 ("historical supplemental catalog","/data/raw/supplemental-index.json"),
 ("new club links","/api/club-links?club=t_41iFW3"),
 ("historical club links","/data/raw/rankings/club-links.json"),
 ("new cup index","/api/cup-index?kind=worker"),
 ("historical cup index","/data/raw/cup-worker/index.json"),
]
report={"atUtc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "command":"python3 docs/verification/orion-availability-20261104/legacy_contract_probe.py",
        "setup":"Read-only GETs against old 0aaf316 deployment. Its source reads saved Neon data and does not contact football providers. Only statuses, response sizes and top-level JSON keys are saved.",
        "expected":"Determine which routes used by the current frontend exist on the old server and which historic data routes supply the same families; a 404 can also mean absent data and is interpreted with the source router.","routes":[]}
for name,path in ROUTES:
    item={"name":name,"path":path};report["routes"].append(item)
    req=urllib.request.Request(HOST+path,headers={"Accept-Encoding":"identity","User-Agent":"StatArena-legacy-contract-audit/1.0"})
    try:
        try: response=urllib.request.urlopen(req,timeout=20)
        except urllib.error.HTTPError as error: response=error
        with response:
            body=response.read()
            item.update(status=response.status,bytes=len(body),contentType=response.headers.get("Content-Type"),source=response.headers.get("X-Data-Source"))
            try:
                value=json.loads(body)
                if isinstance(value,dict):
                    item["topLevelKeys"]=sorted(value)
                    error=value.get("error")
                    if isinstance(error,dict):item["errorCode"]=error.get("code")
                    if path=="/data/dashboard-manifest.json":
                        seasons=value.get("seasons") or []
                        item["manifestShape"]={"storage":value.get("storage"),"defaultSeason":value.get("defaultSeason"),
                                               "seasonCount":len(seasons),"chunkCount":sum(len(s.get("chunks") or []) for s in seasons),
                                               "chunkKeys":sorted((seasons[0].get("chunks") or [{}])[0]) if seasons else []}
            except (ValueError,UnicodeDecodeError):pass
    except Exception as error:item["errorType"]=type(error).__name__
stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
out=HERE/("legacy-contracts-"+stamp+".json");out.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({"artifact":str(out),"statuses":[{"name":v["name"],"status":v.get("status"),"error":v.get("errorType")} for v in report["routes"]]}))

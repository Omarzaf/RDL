import json
from pathlib import Path
import subprocess
import pandas as pd


def w(p: Path, v):
    p.write_text(json.dumps(v))


def make_data(tmp: Path):
    d = tmp / 'Raw Data'; d.mkdir()
    w(d/'top-clients.json',[{"name":"ALPHA INC","totalSpending":1000,"filings":10,"issues":["TEC"],"years":[2024,2025]}])
    w(d/'industries.json',[{"name":"Technology","codes":["TEC"]}])
    w(d/'revolving-door.json',[{"name":"J DOE","positions":["SENATE"],"firms":["OMEGA"],"clients":["ALPHA INC"],"filings":3}])
    w(d/'gov-entities.json',[{"name":"Commerce, Dept of (DOC)","filings":10,"spending":100,"topIssues":[{"code":"TEC","count":3}],"topClients":[{"name":"ALPHA INC","spending":50}]}])
    w(d/'trends.json',[{"year":2024,"totalIncome":100,"filings":10},{"year":2025,"totalIncome":200,"filings":20}])
    w(d/'lobbying-vs-contracts.json',{"matches":[{"name":"ALPHA INC","federalContracts":1000,"roi":5}]})
    w(d/'text-analysis.json',{})
    w(d/'filing-activity.json',{})
    return d


def test_smoke(tmp_path):
    inp = make_data(tmp_path)
    out = tmp_path / 'processed'
    cmd = ['python3','V3_Epistemic/pipeline/build_entity_table.py','--input-dir',str(inp),'--output-dir',str(out),'--skip-embeddings']
    subprocess.run(cmd, check=True)
    nodes = pd.read_csv(out/'entity_nodes.csv')
    edges = pd.read_csv(out/'edges.csv')
    assert {'entity_id','type','year','spend','issues','gov_targets'}.issubset(nodes.columns)
    assert nodes.duplicated(subset=['entity_id','year']).sum() == 0
    assert set(edges['source_entity_id']).issubset(set(nodes['entity_id']))
    assert set(edges['target_entity_id']).issubset(set(nodes['entity_id']))

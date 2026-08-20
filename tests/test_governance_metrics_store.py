from pathlib import Path
import json, os, subprocess, sys
from ctcl_itr.governance_store import SQLiteApprovalQueue
from governance_metrics_fixtures import request, decision, grant

ROOT=Path(__file__).resolve().parents[1]

def test_restart_safe_read_lists(tmp_path:Path):
    db=tmp_path/"m.sqlite3"; rb=request("approval:b"); rec=decision(rb,"decision:b"); g=grant(rec,"auth:b"); ra=request("approval:a")
    q=SQLiteApprovalQueue(db); q.enqueue(rb); q.resolve(rec,g); q.enqueue(ra); q.close()
    q=SQLiteApprovalQueue(db); rs=q.list_requests(); assert [r["approval_id"] for r in rs]==["approval:a","approval:b"]; assert [x["decision_id"] for x in q.list_receipts()]==["decision:b"]; assert [x["authority_ref"] for x in q.list_grants()]==["auth:b"]
    rs[0]["status"]="tampered"; assert q.get_request("approval:a")["status"]=="pending"; q.close()

def test_reopened_db_cli(tmp_path:Path):
    db=tmp_path/"m.sqlite3"; req=request("approval:db",risk="high"); rec=decision(req,"decision:db"); auth=grant(rec,"auth:db")
    q=SQLiteApprovalQueue(db); q.enqueue(req); q.resolve(rec,auth); q.close()
    ev=tmp_path/"e.jsonl"; ev.write_text(json.dumps({"event_type":"human.checkpoint.resolved"})+"\n"+json.dumps({"event_type":"commit.confirmed"})+"\n")
    env=os.environ.copy(); env["PYTHONPATH"]=str(ROOT/"src")
    c=subprocess.run([sys.executable,"-m","ctcl_itr.governance_metrics","--db",str(db),"--events",str(ev),"--at","2026-08-20T08:20:00+00:00"],cwd=ROOT,env=env,capture_output=True,text=True)
    assert c.returncode==0,c.stderr
    p=json.loads(c.stdout); assert p["counts"]["approval_requests"]==1 and p["human_intervention_density"]["value"]==0.5

"""One bounded backend case; the explicit relay fee acknowledgement stays in RAM."""
import argparse,datetime,hashlib,json,pathlib
from payout_experience import Experience
from pearl_controller import ROOT,write
from compute_backend import select_compute_backend
def case_config(base,backend,minutes,fee_ack=None):
    if backend not in ("soat","krig") or not 1<=minutes<=15:raise ValueError("One comparison case must be 1..15 minutes")
    if backend=="krig" and fee_ack!=3:raise ValueError("KRig localhost route requires explicit acknowledgement of 3% developer fee")
    if backend=="soat" and fee_ack is not None:raise ValueError("Source backend has no developer-fee acknowledgement")
    cfg=dict(base);cfg.update(backend=backend,allow_krig_relay_fee=backend=="krig",default_minutes=minutes)
    return cfg
def sha(path):
    with path.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def run_case(backend,minutes,receipt,fee_ack=None):
    case_config({},backend,minutes,fee_ack)
    receipt=pathlib.Path(receipt)
    if not receipt.is_absolute() or receipt.exists():raise ValueError("Use a new absolute comparison receipt path")
    receipt.parent.mkdir(parents=True,exist_ok=True)
    config_path=ROOT/"mining-config.json";before=sha(config_path)
    state={"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"backend":backend,"minutes":minutes,"acknowledged_relay_developer_fee_percent":3 if backend=="krig" else 0,"production_config_sha256_before":before,"default_config_is_written":False,"scope":"one operator-started case, original wallet/pool/deadline; no automatic retry"}
    write(receipt,state)
    try:
        experience=Experience("mine")
        experience.cfg=case_config(experience.cfg,backend,minutes,fee_ack)
        experience.backend=select_compute_backend(experience.cfg,ROOT)
        experience.execute()
        state["status"]="finished"
    except BaseException as exc:
        state.update(status="failed",error=str(exc));raise
    finally:
        state.update(ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),production_config_sha256_after=sha(config_path))
        state["production_config_unchanged"]=state["production_config_sha256_after"]==before
        write(receipt,state)
    return state
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--backend",choices=["soat","krig"],required=True);ap.add_argument("--minutes",type=int,default=15);ap.add_argument("--accept-krig-relay-fee-percent",type=int,choices=[3]);ap.add_argument("--receipt",type=pathlib.Path,required=True);a=ap.parse_args()
    print(json.dumps(run_case(a.backend,a.minutes,a.receipt,a.accept_krig_relay_fee_percent)))
if __name__=="__main__":main()

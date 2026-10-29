# Copyright (c) 2026 toolazytoname. SPDX-License-Identifier: GPL-3.0-or-later
"""Opt-in source candidate trial: verified synthetic gate, RAM-only choice, first-share stop."""
import argparse,datetime,hashlib,json,pathlib
from compute_backend import ComputeBackend
from payout_experience import Experience
from pearl_controller import ROOT,EndSession,load,write
SOURCE_PROJECT=pathlib.Path("D:/Projects/toolazytoname/soat-miner")
STAGED_ROOT=pathlib.Path("D:/Apps/SOAT")
def sha(path):
    with pathlib.Path(path).open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def candidate_from_confirmation(path,staged_executable=None):
    result=load(pathlib.Path(path));plan=result["plan"];review=result.get("review",{})
    if result.get("phase")!="complete" or plan.get("mode")!="confirm" or review.get("comparison_valid") is not True or review.get("candidate_confirmed_improvement") is not True:raise ValueError("A material controlled confirmation is required before constructing GPU management")
    if plan.get("power_watts")!=220 or plan.get("case_seconds",0)<240 or [c["name"] for c in result["cases"]]!=["A1","B","A2"]:raise ValueError("Unexpected controlled measurement")
    if any(c["tail"].get("tail_seconds")!=180 or c["tail"].get("steady") is not True for c in result["cases"]):raise ValueError("Fixed thermal windows did not pass")
    selected=result["cases"][1];tile=selected["tile"]
    if tile!=plan["cases"][1]["tile"] or not tile.startswith("=ampere "):raise ValueError("Candidate selection differs from measured plan")
    exe=pathlib.Path(plan["executable"]).resolve()
    if exe.name!="soat-miner.exe" or not exe.is_relative_to((SOURCE_PROJECT/"build").resolve()):raise ValueError("Expected own built source miner")
    if sha(exe)!=plan["executable_sha256"]:raise ValueError("Candidate binary changed after confirmation")
    proof=load(pathlib.Path(plan["correctness_result"]))
    if proof.get("phase")!="passed" or pathlib.Path(proof["build"]).resolve()!=exe.parent:raise ValueError("Matching complete-buffer result is missing")
    variant=plan["cases"][1]["oracle_variant"];tested={c["name"]:c for c in proof["cases"]};verifier=sha(exe.parent/"test-pearl-mining-shape.exe")
    for m,n in [(256,768),(1024,1024),(4096,65536)]:
        key=f"{m}x{n}-{variant}"
        if key not in tested or tested[key]["binary_sha256"]!=verifier:raise ValueError("Current verifier did not check all required shapes")
    if staged_executable is not None:
        staged=pathlib.Path(staged_executable).resolve()
        if staged.name!="soat-miner.exe" or not staged.is_relative_to(STAGED_ROOT.resolve()) or sha(staged)!=plan["executable_sha256"]:raise ValueError("Staged candidate must be the identical binary under the versioned SOAT app directory")
        exe=staged
    return ComputeBackend("soat",exe,plan["executable_sha256"],"T MAC/s","4096x65536",tile)
class CandidateExperience(Experience):
    def check_stop(self):
        super().check_stop()
        if self.s.get("AcceptedShares",0)>0:raise EndSession("candidate_first_accepted_share")
def unconfirmed(run):
    count=0;path=pathlib.Path(run)/"selected-profile/miner.log"
    if not path.exists():return None
    for line in path.read_text(encoding="utf-8",errors="replace").splitlines():
        try:row=json.loads(line)
        except ValueError:continue
        if row.get("event")=="error" and "no reply from the pool" in row.get("msg",""):count+=1
    return count
def run_case(confirmation,minutes,receipt,staged_executable=None):
    if isinstance(minutes,bool) or not isinstance(minutes,int) or not 1<=minutes<=5:raise ValueError("Trial must be 1..5 mining minutes")
    backend=candidate_from_confirmation(confirmation,staged_executable);receipt=pathlib.Path(receipt)
    if not receipt.is_absolute() or receipt.exists():raise ValueError("Use a new absolute trial receipt")
    receipt.parent.mkdir(parents=True,exist_ok=True);config=ROOT/"mining-config.json";before=sha(config)
    state={"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"confirmation":str(confirmation),"confirmation_sha256":sha(confirmation),"entry_source_sha256":sha(pathlib.Path(__file__)),"candidate":backend.receipt(),"maximum_mining_minutes":minutes,"production_config_sha256_before":before,"default_config_is_written":False,"scope":"One source candidate, original wallet/pool/deadline and all existing guards; stop on first accepted share or earlier guard/manual stop. No automatic retry."};write(receipt,state)
    try:
        experience=CandidateExperience("mine");experience.cfg=dict(experience.cfg,default_minutes=minutes);experience.backend=backend;experience.execute();final=experience.s;missing=unconfirmed(experience.run) if experience.run else None
        state.update(status="finished",session=final,unconfirmed_submissions=missing,accepted_trial=bool(final.get("Status")=="stopped" and final.get("PowerRestored") and final.get("StopReason")=="candidate_first_accepted_share" and final.get("AcceptedShares",0)>0 and not final.get("RejectedShares",0) and not final.get("StaleShares",0) and missing==0))
    except BaseException as exc:state.update(status="failed",error=str(exc));raise
    finally:
        state.update(ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),production_config_sha256_after=sha(config));state["production_config_unchanged"]=state["production_config_sha256_after"]==before;write(receipt,state)
    return state
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--confirmation",type=pathlib.Path,required=True);ap.add_argument("--minutes",type=int,default=5);ap.add_argument("--receipt",type=pathlib.Path,required=True);ap.add_argument("--staged-executable",type=pathlib.Path);args=ap.parse_args();print(json.dumps(run_case(args.confirmation,args.minutes,args.receipt,args.staged_executable)))
if __name__=="__main__":main()

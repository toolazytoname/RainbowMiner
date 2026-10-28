"""Explicit live GPU-yield test: tiny owned CUDA context, no second heavy worker."""
import argparse,datetime,hashlib,json,pathlib,subprocess,time
from pearl_controller import RT,ROOT,load
from gpu_driver import Gpu
from gpu_clients import process_names,gpu_processes

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--helper",type=pathlib.Path,required=True);ap.add_argument("--output",type=pathlib.Path,required=True);a=ap.parse_args()
 if a.helper.name!="test-pearl-gpu-context.exe" or not a.helper.is_file():raise ValueError("Expected the compiled bounded CUDA context helper")
 a.output.mkdir(parents=True,exist_ok=True);target=a.output/"result.json"
 if target.exists():raise ValueError("Refusing to overwrite live-yield evidence")
 start=time.monotonic();session=None
 while time.monotonic()-start<240:
  session=load(RT/"session.json")
  if session["Status"]=="running" and session.get("MinerPid") and session.get("ReportedRate",session.get("HashrateTHs",0))>0:break
  time.sleep(1)
 else:raise RuntimeError("No active owned mining session became ready")
 kind=(session.get("ComputeBackend") or {}).get("Kind","krig");expected="soat-miner.exe" if kind=="soat" else "krig-miner.exe"
 if process_names().get(int(session["MinerPid"]))!=expected:raise RuntimeError("Expected owned compute process is not running")
 cfg=load(ROOT/"mining-config.json")
 if session.get("Wallet")!=cfg["wallet"] or session.get("Pool")!=cfg["pool"]:raise RuntimeError("Unexpected session identity")
 with a.helper.open("rb") as f:digest=hashlib.file_digest(f,"sha256").hexdigest()
 state={"time":datetime.datetime.now(datetime.timezone.utc).isoformat(),"session_id":session["SessionId"],"helper":str(a.helper),"helper_sha256":digest,"helper_scope":"one 8 MiB memset and 20 seconds idle; not a heavy compute workload","before":session,"passed":False};child=None
 try:
  state["backend_checks"]=[]
  checker="Test-PearlSourceLive.ps1" if kind=="soat" else "Test-KRigLive.ps1"
  for label,ps in [("ps7","D:/Apps/PowerShell/7/pwsh.exe"),("ps51","C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")]:
   check=a.output/(label+"-backend-check")
   run=subprocess.run([ps,"-NoProfile","-ExecutionPolicy","RemoteSigned","-File",str(pathlib.Path(__file__).resolve().parents[2]/("Tests/"+checker)),"-EvidenceDirectory",str(check)],capture_output=True,timeout=30)
   (a.output/(label+"-native-api.log")).write_bytes(run.stdout+run.stderr);state["backend_checks"].append({"shell":label,"exit_code":run.returncode,"result":str(check/("source-live-result.json" if kind=="soat" else "live-api-result.json"))})
   if run.returncode:raise RuntimeError("Backend live check failed: "+label)
  state["before"]=load(RT/"session.json");state["gpu_clients_before"]=gpu_processes()
  with (a.output/"context-helper.log").open("wb") as log:
   child=subprocess.Popen([str(a.helper),"20"],stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS);state["helper_pid"]=child.pid;started=time.monotonic()
   while time.monotonic()-started<16:
    current=load(RT/"session.json")
    if current["SessionId"]!=session["SessionId"]:raise RuntimeError("Session changed during yield test")
    if current["Status"]=="stopped":
     state.update(after=current,yield_seconds=round(time.monotonic()-started,3),helper_still_running=child.poll() is None,actual_gpu=Gpu().read())
     evidence=pathlib.Path(current["RunDirectory"])/"gpu-yield.json"
     state["gpu_yield_evidence"]=load(evidence) if evidence.exists() else None
     reason=current.get("StopReason");attributed=reason=="other_gpu_workload" or (reason=="user_stop" and (state["gpu_yield_evidence"] or {}).get("GpuYieldReason")=="other_gpu_workload")
     state["gpu_clients_after"]=gpu_processes()
     state["passed"]=current.get("MinerPid") is None and current.get("PowerRestored") is True and state["helper_still_running"] and attributed and child.pid in state["gpu_clients_after"]
     break
    time.sleep(1)
   state["helper_exit_code"]=child.wait(timeout=30)
   state["passed"]=state["passed"] and state["helper_exit_code"]==0
 except BaseException as exc:state["error"]=str(exc)
 finally:
  if child and child.poll() is None:child.terminate();child.wait(timeout=5)
  state["ended_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat();target.write_text(json.dumps(state,indent=2),encoding="utf-8")
 return 0 if state["passed"] else 1
if __name__=="__main__":raise SystemExit(main())

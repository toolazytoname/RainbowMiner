"""Explicit live start/stop entry test. No backend is started on import."""
import argparse,datetime,json,pathlib,subprocess,time
from pearl_controller import RT,load
from gpu_driver import Gpu

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--output",type=pathlib.Path,required=True);a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True);target=a.output/"result.json"
 if target.exists():raise ValueError("Use a fresh output directory")
 original=load(RT/"session.json");deadline=load(RT/"payout-experience.json")["MiningDeadline"];power=Gpu().read()["PowerLimit"];entry=pathlib.Path(__file__).parent/"Manage-Pearl.ps1";state={"time":datetime.datetime.now(datetime.timezone.utc).isoformat(),"original_deadline":deadline,"starting_power":power,"passed":False}
 def call(action):
  args=["D:/Apps/PowerShell/7/pwsh.exe","-NoProfile","-File",str(entry),"-Action",action]
  if action=="Start":args.extend(["-Minutes","2","-NoPanel"])
  result=subprocess.run(args,capture_output=True,timeout=30);(a.output/(action.lower()+".log")).write_bytes(result.stdout+result.stderr)
  if result.returncode:raise RuntimeError(action+" entry failed")
 try:
  if original["Status"]!="stopped":raise RuntimeError("Another session is still active")
  call("Start");end=time.monotonic()+240
  while time.monotonic()<end:
   current=load(RT/"session.json")
   if current["SessionId"]!=original["SessionId"] and current["Status"]=="running" and current.get("HashrateTHs",0)>0:break
   time.sleep(1)
  else:raise RuntimeError("Mining did not become ready")
  state["before_stop"]=current;call("Stop");started=time.monotonic()
  while time.monotonic()-started<30:
   current=load(RT/"session.json")
   if current["Status"]=="stopped":break
   time.sleep(1)
  state.update(after_stop=current,stop_seconds=round(time.monotonic()-started,3),actual_gpu=Gpu().read(),final_deadline=load(RT/"payout-experience.json")["MiningDeadline"])
  state["passed"]=current["Status"]=="stopped" and current.get("MinerPid") is None and current.get("StopReason")=="user_stop" and current.get("PowerRestored") is True and abs(state["actual_gpu"]["PowerLimit"]-power)<2 and state["final_deadline"]==deadline
 except BaseException as exc:
  state["error"]=str(exc)
  try:call("Stop")
  except BaseException:pass
 finally:state["ended_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat();target.write_text(json.dumps(state,indent=2),encoding="utf-8")
 return 0 if state["passed"] else 1
if __name__=="__main__":raise SystemExit(main())
